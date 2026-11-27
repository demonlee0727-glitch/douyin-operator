"""Polling jobs with per-source cursors and persistent cooldowns."""
import csv
import hashlib
import html
import io
import json
import os
import re
import threading
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import BadZipFile

from store import CST, db, dt, event, import_csv, profile, put_peer, snapshot, stamp, work_url

LOCK=threading.Lock()
def credentials():
    return {"官方作品统计": bool(os.getenv("DY_BUSINESS_TOKEN") and os.getenv("DY_OPEN_ID")),
            "官方搜索":bool(os.getenv("DY_SEARCH_TOKEN") and os.getenv("DY_DEVICE_ID")),
            "公开网页索引":bool(os.getenv("BRAVE_SEARCH_API_KEY"))}

def get_json(base,params,headers):
    req=Request(base+"?"+urlencode(params),headers={**headers,"Accept":"application/json"})
    try:
        with urlopen(req,timeout=12) as res:
            raw=res.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError("上游响应过大")
            obj=json.loads(raw)
    except HTTPError as e:
        raise ValueError(f"上游 HTTP {e.code}，请检查配额、权限或稍后重试") from None
    except (OSError,URLError):
        raise ValueError("上游网络不可用，请检查网络连接") from None
    if not isinstance(obj,dict):raise ValueError("上游响应格式变化")
    if obj.get("err_no",0)!=0:raise ValueError("抖音返回错误码 "+str(obj["err_no"]))
    return obj

def clean(s):
    return html.unescape(re.sub(r"<[^>]*>","",s or "")).strip()

def find_public(query,source):
    if source=="官方搜索":
        data=get_json("https://open.douyin.com/dy_open_api/v1/search/video/",
            {"keyword":query,"count":10,"cursor":0,"device_id":os.environ["DY_DEVICE_ID"],"sort_type":2,"publish_time":7},
            {"access-token":os.environ["DY_SEARCH_TOKEN"],"Content-Type":"application/json"})
        items=data["data"]["data"]["video_list"]
        for x in items:
            yield dict(url=x["link"],title=x["title"],author=x.get("nickname"),summary=(x.get("high_quality_text") or "")[:300],caption=x.get("high_quality_text"),
                       likes=(x.get("statistics") or {}).get("digg_count"),keyword=query,source=source,
                       published=datetime.fromtimestamp(x["create_time"],CST).isoformat() if x.get("create_time") else None)
    else:
        data=get_json("https://api.search.brave.com/res/v1/web/search",
           {"q":(("site:douyin.com/user " + query[3:]) if query.startswith("找账号") else ("site:douyin.com/video " + query)),"count":10,"search_lang":"zh-hans"},
           {"X-Subscription-Token":os.environ["BRAVE_SEARCH_API_KEY"]})
        for x in (data.get("web") or {}).get("results",[]):
            try:url=work_url(x.get("url"))
            except ValueError:continue
            title=clean(x.get("title")).removesuffix(" - 抖音")
            yield dict(url=url,title=title,author=title.removesuffix("的抖音").strip() if "/user/" in url else "",
                       summary=clean(x.get("description")),keyword=query,source=source)

def queries(home):
    from analysis import diagnose, observations
    with db(home) as con:
        cfg=profile(con)
        dec=diagnose(*observations(con))
        watched=[r[0] for r in con.execute("SELECT author FROM peers WHERE author<>'' AND length(author)<40 GROUP BY author ORDER BY COUNT(*) DESC LIMIT 3")]
    relevant=next((d["series"] for d in dec if d["series"]!="未分类"),None)
    picks=list(cfg["keywords"])
    if relevant and cfg["keywords"]:picks.append(relevant+" "+cfg["keywords"][0])
    picks.extend(watched)
    return list(dict.fromkeys(picks))

def search_step(home,source,cursor):
    words=queries(home)
    if source=="公开网页索引":
        words=[q for word in words for q in ("找账号"+word,word)]
    q=words[cursor%len(words)]
    found=list(find_public(q,source))
    with db(home) as con:
        before=con.execute("SELECT COUNT(*) FROM peers").fetchone()[0]
        for x in found:put_peer(con,x)
        fresh=con.execute("SELECT COUNT(*) FROM peers").fetchone()[0]-before
    return f"「{q}」命中 {len(found)} 条，新增 {fresh} 条",cursor+1

def own_step(home,cursor):
    path=home/"tracked.csv"
    if not path.is_file():raise ValueError("请先在数据目录提供 tracked.csv，见示例")
    with path.open(encoding="utf-8-sig",newline="") as f:items=list(csv.DictReader(f))
    eligible=[x for x in items if timedelta(0)<=datetime.now(CST)-dt(x["published"])<timedelta(days=30)]
    if not eligible:return "没有近 30 天的在跟作品",0
    # Rotate through the list in bounded batches. Each successful observation is independent.
    batch=[eligible[(cursor+i)%len(eligible)] for i in range(min(10,len(eligible)))]
    for x in batch:
        doc=get_json("https://open.douyin.com/api/apps/v1/item_bc/get_base/",
               {"item_id":x["item_id"],"open_id":os.environ["DY_OPEN_ID"]},
               {"access-token":os.environ["DY_BUSINESS_TOKEN"],"Content-Type":"application/json"})
        extra=doc["data"].get("extra",{})
        if extra.get("error_code",0):raise ValueError("官方数据错误码 "+str(extra["error_code"]))
        v=doc["data"]["data"]["result"]
        with db(home) as con:
            snapshot(con,{**x,"observed":stamp(),"plays":v.get("total_play"),"likes":v.get("total_like"),
                          "comments":v.get("total_comment"),"shares":v.get("total_share")},"官方统计·次日刷新")
    return f"读取 {len(batch)} 条授权作品的最新平台批次", (cursor+len(batch))%len(eligible)

def watch_files(home):
    messages=[]
    for p in sorted((home/"inbox").iterdir()):
        if not p.is_file() or p.name.startswith((".","~")) or p.suffix.lower() not in (".csv",".xlsx",".json"):continue
        try:
            if p.stat().st_size>12_000_000:raise ValueError("文件超过 12 MB")
            data=p.read_bytes()
            digest=hashlib.sha256(data).hexdigest()
            key="file:"+digest
            with db(home) as con:
                if con.execute("SELECT 1 FROM imports WHERE digest=?",(key,)).fetchone():continue
                if p.suffix.lower()==".json":
                    items=json.loads(data)
                    if not isinstance(items,list):raise ValueError("对标 JSON 需要数组")
                    for item in items:put_peer(con,item)
                    count=len(items)
                else:
                    if p.suffix.lower()==".xlsx":
                        try:from openpyxl import load_workbook
                        except ImportError:raise ValueError("读取 XLSX 需安装 openpyxl，或另存 CSV")
                        wb=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
                        try:
                            out=io.StringIO();writer=csv.writer(out)
                            for line in wb.active.values:writer.writerow(line)
                            content=out.getvalue()
                        finally:wb.close()
                    else:
                        try:content=data.decode("utf-8-sig")
                        except UnicodeDecodeError:content=data.decode("gb18030")
                    count=import_csv(con,content,p.name)
                con.execute("INSERT INTO imports VALUES(?,?,?,?)",(key,p.name,count,stamp()))
                event(con,"文件",f"{p.name} · 处理 {count} 条")
            messages.append(f"{p.name} +{count}")
        except (ValueError,KeyError,TypeError,OSError,ImportError,ArithmeticError,BadZipFile) as e:
            message=f"{p.name} · {e}"
            with db(home) as con:
                last=con.execute("SELECT message FROM events WHERE kind='文件异常' ORDER BY id DESC LIMIT 10").fetchall()
                if message not in [x[0] for x in last]:event(con,"文件异常",message)
            messages.append(message)
    return messages

def cycle(home,force=False):
    if not LOCK.acquire(blocking=False):return ["上一轮仍在执行"]
    guard=None
    try:
        # File locks are released by the OS on exit, including a crashed worker.
        guard=(home/"monitor.lock").open("a+b")
        try:
            if os.name=="nt":
                import msvcrt
                if guard.seek(0,2)==0:
                    guard.write(b"0");guard.flush()
                guard.seek(0);msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(guard.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:return ["另一个工作台正在检查此账号"]
        try:messages=watch_files(home)
        except (BadZipFile,ValueError,OSError) as e:
            with db(home) as con:event(con,"文件异常",str(e))
            messages=["文件读取异常"]
        for source,enabled in credentials().items():
            if not enabled:continue
            with db(home) as con:
                row=con.execute("SELECT * FROM clocks WHERE name=?",(source,)).fetchone()
            now=datetime.now(CST)
            if row and dt(row["next_time"])>now and (not force or row["failures"]):continue
            cursor=row["cursor"] if row else 0
            failures=0
            try:
                msg,cursor=own_step(home,cursor) if source=="官方作品统计" else search_step(home,source,cursor)
                delay=21600 if source=="官方作品统计" else 900
            except (ValueError,OSError,KeyError,TypeError,IndexError) as e:
                failures=(row["failures"] if row else 0)+1
                delay=min(7200,60*2**min(7,failures-1));msg=f"{type(e).__name__} · {str(e)[:180]}"
            with db(home) as con:
                con.execute("INSERT OR REPLACE INTO clocks VALUES(?,?,?,?)",(source,(now+timedelta(seconds=delay)).isoformat(timespec="seconds"),failures,cursor))
                event(con,"连接异常" if failures else "同步",source+" · "+msg)
            messages.append(source+" · "+msg)
        from desk import draft_from_signals
        count=draft_from_signals(home)
        if count:messages.append(f"已生成 {count} 份选题简报")
        return messages or ["本地文件已检查，暂无新数据"]
    finally:
        if guard is not None:guard.close()
        LOCK.release()

