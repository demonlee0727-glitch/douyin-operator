"""Local account, observation and editorial records."""
import csv
import hashlib
import io
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
DEFAULT = {"name": "生活科普编辑部", "audience": "对生活细节好奇的上班族",
           "keywords": ["生活科普", "日常物件原理", "职场生活", "科学实验"],
           "promise": "用三分钟讲清一个身边的问题", "weekly_capacity": 3}
METRICS = ("plays", "likes", "comments", "shares", "saves", "follows", "completion", "retention5")
LABELS = {"plays":"播放量","likes":"点赞","comments":"评论","shares":"分享","saves":"收藏",
          "follows":"新增关注","completion":"完播率","retention5":"5秒留存率"}
STAGES = ("选题","制作","待发布","已发布","已复盘")
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snaps (work TEXT, observed TEXT, title TEXT, published TEXT, series TEXT,
 traffic TEXT, metrics TEXT, origin TEXT, PRIMARY KEY(work,observed));
CREATE TABLE IF NOT EXISTS peers (url TEXT PRIMARY KEY, author TEXT, title TEXT, summary TEXT,
 source TEXT, first_seen TEXT, seen TEXT, keyword TEXT, published TEXT, likes INTEGER);
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, url TEXT NOT NULL REFERENCES peers(url),
 aspect TEXT NOT NULL, cue TEXT NOT NULL, evidence TEXT NOT NULL, pattern TEXT NOT NULL, created TEXT NOT NULL,
 UNIQUE(url,aspect,cue,evidence,pattern));
CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY, title TEXT NOT NULL, due TEXT NOT NULL,
 stage TEXT NOT NULL, brief TEXT NOT NULL, work TEXT NOT NULL DEFAULT '', updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, content TEXT NOT NULL, work TEXT NOT NULL,
 kind TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL, reply TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS tests (id INTEGER PRIMARY KEY, hypothesis TEXT, variable TEXT, work TEXT,
 metric TEXT, window TEXT, baseline REAL, goal REAL, controls TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS imports (digest TEXT PRIMARY KEY, filename TEXT, rows INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, created TEXT, kind TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS auto_plans (fingerprint TEXT PRIMARY KEY, plan_id INTEGER REFERENCES plans(id));
CREATE TABLE IF NOT EXISTS clocks (name TEXT PRIMARY KEY, next_time TEXT, failures INTEGER, cursor INTEGER);
"""
def stamp():
    return datetime.now(CST).isoformat(timespec="seconds")

def dt(value):
    raw = str(value or "").strip().replace("/", "-")
    if raw.endswith("Z"):
        raw = raw[:-1]+"+00:00"
    try:
        out = datetime.fromisoformat(raw)
    except ValueError:
        raise ValueError("日期时间需要 YYYY-MM-DD HH:MM 或 ISO 格式")
    if out.tzinfo is None:
        out = out.replace(tzinfo=CST)
    return out.astimezone(CST)

def field(value, name, limit=1500):
    v = str(value or "").strip()
    if not v or len(v)>limit:
        raise ValueError(f"{name}不能为空，最多 {limit} 字")
    return v

def setup(home):
    home.mkdir(parents=True, exist_ok=True)
    (home/"inbox").mkdir(exist_ok=True)
    with db(home) as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
        con.execute("INSERT OR IGNORE INTO settings VALUES(1,?)",(json.dumps(DEFAULT,ensure_ascii=False),))

@contextmanager
def db(home):
    con = sqlite3.connect(str(home/"operator.sqlite3"),timeout=10)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        with con:
            yield con
    finally:
        con.close()

def rows(con, sql, args=()):
    return [dict(r) for r in con.execute(sql,args)]

def profile(con):
    return json.loads(con.execute("SELECT doc FROM settings WHERE id=1").fetchone()[0])

def event(con, kind, msg):
    con.execute("INSERT INTO events(created,kind,message) VALUES(?,?,?)",(stamp(),kind,msg[:600]))

def work_url(value):
    parts=urlsplit(str(value or "").strip())
    if parts.scheme!="https" or parts.netloc.lower() not in ("www.douyin.com","douyin.com"):
        raise ValueError("请填写 www.douyin.com 的 HTTPS 作品或作者主页链接")
    if not re.fullmatch(r"/(?:video/[0-9]+|note/[0-9]+|user/[A-Za-z0-9_-]+)/?",parts.path):
        raise ValueError("支持 /video/、/note/ 和 /user/ 完整链接")
    return "https://www.douyin.com"+parts.path.rstrip("/")

def put_peer(con, item):
    if not isinstance(item,dict):raise ValueError("每条同行记录需要是对象")
    url=work_url(item.get("url"))
    title=field(item.get("title"),"作品或主页标题",600)
    author=str(item.get("author") or "").strip()[:100]
    now=stamp()
    con.execute("""INSERT INTO peers VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(url) DO UPDATE SET
      author=CASE WHEN excluded.author<>'' THEN excluded.author ELSE peers.author END,
      title=excluded.title,summary=CASE WHEN excluded.summary<>'' THEN excluded.summary ELSE peers.summary END,
      seen=excluded.seen,keyword=excluded.keyword,likes=COALESCE(excluded.likes,peers.likes),
      published=COALESCE(excluded.published,peers.published)""",
      (url,author,title,str(item.get("summary") or "")[:1500],str(item.get("source") or "人工录入")[:100],
       now,now,str(item.get("keyword") or "")[:120],dt(item["published"]).isoformat() if item.get("published") else None,number(item.get("likes"))))
    from learning import auto_read
    auto_read(con,url,title,str(item.get("caption") or "")[:12000])


ALIASES = {
 "work":("作品ID","作品id","视频ID","视频id","作品链接","视频链接"),"title":("作品标题","作品名称","视频标题","视频描述","标题"),
 "published":("发布时间","作品发布时间"),"observed":("观察时间","统计截止时间","采集时间"),
 "series":("系列","内容类型","合集"),"traffic":("流量类型","流量来源类型"),
 "plays":("播放量","播放次数"),"likes":("点赞","点赞量","点赞数"),"comments":("评论","评论量","评论数"),
 "shares":("分享","分享量","分享数"),"saves":("收藏","收藏量","收藏数"),"follows":("新增关注","涨粉量","新增粉丝","粉丝增量"),
 "completion":("完播率",),"retention5":("5秒留存率","5s完播率","5秒完播率")}
MAP={n.lower():k for k,names in ALIASES.items() for n in (k,)+names}

def number(raw, rate=False):
    if raw is None or str(raw).strip() in ("","-","--","—","暂无","N/A"):
        return None
    s=str(raw).strip().replace(",","").replace("，","")
    pct=s.endswith(("%","％"))
    if pct: s=s[:-1]
    try: x=float(s)
    except ValueError: raise ValueError(f"无效数值 {str(raw)[:40]}")
    if not math.isfinite(x) or x<0: raise ValueError("指标须为有限非负数")
    if rate:
        if pct: x/=100
        if x>1: raise ValueError("比率请写为 25% 或 0.25")
        return x
    if pct or not x.is_integer(): raise ValueError("次数须为整数")
    return int(x)

def snapshot(con, obj, origin, observed_default=""):
    r={MAP.get(str(k).strip().lower(),str(k)):v for k,v in obj.items() if k is not None}
    obs=dt(r.get("observed") or observed_default)
    pub=dt(r.get("published"))
    if obs<pub or obs>datetime.now(CST)+timedelta(minutes=10):
        raise ValueError("观察时间应在发布时间之后且不晚于当前时间")
    title=field(r.get("title"),"作品标题",600)
    work=field(r.get("work"),"作品ID或链接",250)
    if work.startswith("https://"):
        url=work_url(work)
        if "/user/" in url: raise ValueError("作品ID不能使用博主主页")
        work=url.rsplit("/",1)[-1]
    series=str(r.get("series") or "未分类").strip()
    traffic=str(r.get("traffic") or "未知").strip()
    if traffic not in ("自然","付费","混合","未知"): raise ValueError("流量类型选自然、付费、混合或未知")
    values={k:number(r.get(k),k in ("completion","retention5")) for k in METRICS}
    if all(v is None for v in values.values()): raise ValueError("至少需要一项有效指标")
    at=obs.isoformat(timespec="seconds")
    old=con.execute("SELECT metrics FROM snaps WHERE work=? AND observed=?",(work,at)).fetchone()
    if old: values={**json.loads(old[0]),**{k:v for k,v in values.items() if v is not None}}
    con.execute("INSERT OR REPLACE INTO snaps VALUES(?,?,?,?,?,?,?,?)",
                (work,at,title,pub.isoformat(timespec="seconds"),series,traffic,json.dumps(values),origin))

def import_csv(con, text, filename="网页导入", observed=""):
    digest=hashlib.sha256((text+"\x00"+observed).encode()).hexdigest()
    if con.execute("SELECT 1 FROM imports WHERE digest=?",(digest,)).fetchone(): return 0
    reader=csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    count=0
    for line,record in enumerate(reader,2):
        if not any(str(v or "").strip() for v in record.values()): continue
        try: snapshot(con,record,filename,observed)
        except (ValueError,TypeError) as e: raise ValueError(f"第 {line} 行：{e}") from e
        count+=1
    if not count: raise ValueError("未找到数据行")
    con.execute("INSERT INTO imports VALUES(?,?,?,?)",(digest,filename,count,stamp()))
    event(con,"数据",f"{filename} · 导入 {count} 条观察")
    return count

