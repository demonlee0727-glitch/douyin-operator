"""Application commands shared by the local web UI, CLI and report."""
from learning import ADAPT, auto_read, model_read
import json
from collections import Counter
from datetime import datetime, timedelta

from analysis import ASPECTS, PATTERNS, WINDOWS, diagnose, experiment_status, observations, peer_review, register_experiment
from monitor import credentials
from store import CST, ROOT, STAGES, db, dt, event, field, import_csv, profile, put_peer, rows, stamp, work_url

def add_seed(home):
    bundle=json.loads((ROOT/"examples"/"public-references.json").read_text(encoding="utf8"))
    with db(home) as con:
        if con.execute("SELECT 1 FROM imports WHERE digest='public-v1'").fetchone():return
        for p in bundle:
            put_peer(con,p)
            con.execute("INSERT OR IGNORE INTO notes(url,aspect,cue,evidence,pattern,created) VALUES(?,?,?,?,?,?)",
                (p["url"],"标题","作品页标题",p["observation"],p["pattern"],stamp()))
        con.execute("INSERT INTO imports VALUES('public-v1','初始公开索引',?,?)",(len(bundle),stamp()))

def week(con,latest,decisions,days):
    now=datetime.now(CST);since=(now-timedelta(days=days)).isoformat()
    works=[x for x in latest.values() if since<=x["published"]<=now.isoformat()]
    series=Counter(x["series"] for x in works)
    plans=con.execute("SELECT COUNT(*) FROM plans WHERE due BETWEEN ? AND ?",(since[:10],now.date().isoformat())).fetchone()[0]
    period=[d for d in decisions if since<=d["published"]<=now.isoformat()]
    actions=[d["title"]+" · "+d["label"]+"。"+d["evidence"] for d in period if d["label"] not in ("补齐可比样本","沿用本轮方案")][:3]
    short=sum(d["label"]=="补齐可比样本" for d in period)
    return dict(days=days,works=len(works),plans=plans,series=dict(series),signals=actions,insufficient=short,
       note="按发布时间统计作品；详细指标按作品观察窗口比较。")

def draft_from_signals(home):
    with db(home) as con:
        con.execute("BEGIN IMMEDIATE")
        cfg=profile(con)
        if not cfg.get("auto_plan"):return 0
        now=datetime.now(CST); day=now.date(); end=day+timedelta(days=6)
        booked=rows(con,"SELECT due FROM plans WHERE due BETWEEN ? AND ?",(day.isoformat(),end.isoformat()))
        room=cfg["weekly_capacity"]-len(booked)
        if room<=0:return 0
        candidates=[]
        for f in rows(con,"SELECT * FROM feedback WHERE kind='选题需求' AND status='待处理' ORDER BY id DESC"):
            candidates.append(("comment-"+str(f["id"]),f["content"][:160],"来源：观众问题（作品 "+(f["work"] or "未标注")+"）。先核实问题中的前提，再用自己的素材验证。"))
        for d in diagnose(*observations(con)):
            if now-dt(d["observed"])>timedelta(days=14) or d["label"] in ("补齐可比样本","沿用本轮方案"):continue
            candidates.append(("work-"+d["work"]+"-"+d["label"],d["label"]+" · "+d["title"][:130],
                               "来源："+d["work"]+"，"+d["window"]+"。"+d["evidence"]+" 只改变一项："+d["action"]))
        count=0
        for key,title,reason in candidates:
            if count>=room:break
            if con.execute("SELECT 1 FROM auto_plans WHERE fingerprint=?",(key,)).fetchone():continue
            dates=[(day+timedelta(days=n)).isoformat() for n in range(7)]
            due=min(dates,key=lambda v:sum(b["due"]==v for b in booked))
            brief=f'{reason}\n受众：{cfg["audience"]}。栏目：{cfg["promise"]}。\n编辑填写：原创场景、画面证据、资料来源、主要指标和观察窗口。'
            plan=con.execute("INSERT INTO plans(title,due,stage,brief,updated) VALUES(?,?,?,?,?)",(title,due,"选题",brief,stamp()))
            con.execute("INSERT INTO auto_plans VALUES(?,?)",(key,plan.lastrowid))
            booked.append({"due":due});count+=1
        if count:event(con,"自动排期",f"按账号表现和观众问题新增 {count} 份待编辑简报")
        return count

def state(home):
    with db(home) as con:
        cfg=profile(con); latest,slots=observations(con)
        decisions=diagnose(latest,slots)
        peers=peer_review(con,cfg)
        plans=rows(con,"SELECT * FROM plans ORDER BY due,id")
        comments=rows(con,"SELECT * FROM feedback ORDER BY id DESC")
        experiments=experiment_status(con,slots)
        todo=[]
        now=datetime.now(CST);today=now.date().isoformat()
        newest=max((x["observed"] for x in latest.values()),default="")
        def task(kind,title,detail):todo.append(dict(kind=kind,title=title,detail=detail))
        if not latest:task("数据","接入第一批作品快照","导入创作者中心导出数据，记录观察时间、系列与流量类型。")
        elif now-dt(newest)>timedelta(hours=48):task("数据","补录最新观察",f"最近数据采于 {newest[:16]}，先更新再调整排期。")
        due=[p for p in plans if p["due"]<=today and p["stage"] not in ("已发布","已复盘")]
        if due:task("排期",f"{len(due)} 条内容到期",due[0]["title"]+" · "+due[0]["stage"])
        actionable=next((d for d in decisions if d["label"] not in ("补齐可比样本","沿用本轮方案")
                        and now-dt(d["observed"])<=timedelta(days=14)),None)
        if actionable:task("诊断",actionable["label"],actionable["title"]+" · "+actionable["evidence"]+actionable["action"])
        elif decisions:task("复盘",decisions[0]["label"],decisions[0]["title"]+" · "+decisions[0]["action"])
        open_comments=[c for c in comments if c["status"]=="待处理"]
        if open_comments:
            lead=next((c for c in open_comments if c["kind"]=="事实纠错"),open_comments[0])
            task("互动",f'{len(open_comments)} 条待处理反馈',lead["kind"]+" · "+lead["content"][:95])
        if peers:task("对标",peers[0]["author"]+" · "+peers[0]["grade"],"已归档 "+str(peers[0]["works"])+" 条作品，按样本证据安排下一次观察。")
        for t in experiments:
            if t["status"] in ("达到预设目标","未达预设目标"):
                task("实验",t["status"],t["variable"]+" · "+t["result"]+" / 目标 "+t["goal_label"]);break
        end=(now.date()+timedelta(days=6)).isoformat()
        upcoming=sum(today<=p["due"]<=end for p in plans)
        if upcoming<cfg["weekly_capacity"]:task("选题","补充未来七天排期",f"计划 {cfg['weekly_capacity']} 条，已安排 {upcoming} 条。")
        return dict(profile=cfg,decisions=decisions,peers=peers,plans=plans,comments=comments,experiments=experiments,
                    today=todo,forecast=upcoming,weekly=week(con,latest,decisions,7),monthly=week(con,latest,decisions,30),
                    count=len(latest),snapshot_count=con.execute("SELECT COUNT(*) FROM snaps").fetchone()[0],
                    last_observed=newest,now=stamp(),sources=credentials(),clocks=rows(con,"SELECT * FROM clocks"),
                    events=rows(con,"SELECT * FROM events ORDER BY id DESC LIMIT 25"),
                    routines=json.loads((ROOT/"web"/"routine.json").read_text(encoding="utf8")))

def change(home,command,b):
    with db(home) as con:
        if command=="profile":
            keys=[s.strip()[:60] for s in b["keywords"].replace("，",",").split(",") if s.strip()]
            cap=int(b.get("weekly_capacity",3))
            if not 1<=len(keys)<=15 or not 1<=cap<=21:raise ValueError("填写 1–15 个搜索词和 1–21 条周产能")
            cfg={k:field(b.get(k),k,200) for k in ("name","audience","promise")}
            cfg.update(keywords=list(dict.fromkeys(keys)),weekly_capacity=cap,auto_plan=b.get("auto_plan")=="on")
            con.execute("UPDATE settings SET doc=? WHERE id=1",(json.dumps(cfg,ensure_ascii=False),))
        elif command=="metrics":
            n=import_csv(con,b["csv"],"网页导入",b.get("observed",""));return f"导入 {n} 条新观察"
        elif command=="peers":
            put_peer(con,b)
        elif command=="breakdown":
            url=work_url(b["url"])
            sample=con.execute("SELECT title FROM peers WHERE url=?",(url,)).fetchone()
            if not sample or "/user/" in url:raise ValueError("需要已归档的具体作品")
            transcript=field(b.get("transcript"),"字幕或逐段观察",12000)
            method=b.get("method","local")
            if method not in ("local","model"):raise ValueError("未知拆解方式")
            n=(model_read if method=="model" else auto_read)(con,url,sample[0],transcript)
            event(con,"拆解",f"保存 {n} 条新证据")
            return f"保存 {n} 条有文字依据的新观察；可在作品卡检查"
        elif command=="note":
            url=work_url(b["url"])
            if not con.execute("SELECT 1 FROM peers WHERE url=?",(url,)).fetchone():raise ValueError("请先保存作品")
            if "/user/" in url:raise ValueError("拆解需要具体作品链接")
            if b["aspect"] not in ASPECTS or b["pattern"] not in PATTERNS:raise ValueError("观察类别无效")
            con.execute("INSERT OR IGNORE INTO notes(url,aspect,cue,evidence,pattern,created) VALUES(?,?,?,?,?,?)",
                        (url,b["aspect"],field(b.get("cue"),"时间点或出处",150),field(b.get("evidence"),"可观察事实"),
                         b["pattern"],stamp()))
        elif command=="plan":
            title=field(b.get("title"),"原创选题",240); day=datetime.strptime(b["due"],"%Y-%m-%d").date().isoformat()
            cfg=profile(con)
            lines=[f'受众：{cfg["audience"]}',f'本期要解决：{title}',f'栏目承诺：{cfg["promise"]}']
            if b.get("url"):
                url=work_url(b["url"])
                sample=con.execute("SELECT author,title FROM peers WHERE url=?",(url,)).fetchone()
                if not sample:raise ValueError("找不到参考作品")
                if sample["title"].strip()==title:raise ValueError("请换成自己要验证的原创问题")
                notes=rows(con,"SELECT * FROM notes WHERE url=? ORDER BY id DESC LIMIT 4",(url,))
                lines.extend([f'参考作品：{sample["author"] or "作者待核对"} · {url}']+
                             [f'可借鉴手法：{n["pattern"]}（{n["cue"]}，{n["evidence"]}）' for n in notes])
                modes=list(dict.fromkeys(n["pattern"] for n in notes))
                if modes:lines.append("原创迁移实验："+ADAPT.get(modes[0],ADAPT["其他"]))
            if b.get("feedback_id"):
                f=con.execute("SELECT content FROM feedback WHERE id=?",(int(b["feedback_id"]),)).fetchone()
                if f:lines.append("观众问题："+f[0])
            lines.append(field(b.get("brief"),"本期具体实验或画面（至少一条）"))
            con.execute("INSERT INTO plans(title,due,stage,brief,updated) VALUES(?,?,?,?,?)",(title,day,"选题","\n".join(lines),stamp()))
        elif command=="edit_plan":
            day=datetime.strptime(b["due"],"%Y-%m-%d").date().isoformat()
            result=con.execute("UPDATE plans SET title=?,brief=?,due=?,updated=? WHERE id=?",
                (field(b.get("title"),"标题",240),field(b.get("brief"),"简报",12000),day,stamp(),int(b["id"])))
            if not result.rowcount:raise ValueError("找不到该排期")
        elif command=="stage":
            rec=con.execute("SELECT * FROM plans WHERE id=?",(int(b["id"]),)).fetchone()
            if not rec:raise ValueError("找不到该排期")
            stage=b["stage"]
            if stage not in STAGES:raise ValueError("阶段无效")
            work=str(b.get("work") or rec["work"]).strip()[:250]
            if stage in ("已发布","已复盘") and not work:raise ValueError("请关联真实发布作品 ID")
            if stage=="已复盘" and not con.execute("SELECT 1 FROM snaps WHERE work=?",(work,)).fetchone():
                raise ValueError("请先导入关联作品的实际观察")
            con.execute("UPDATE plans SET stage=?,work=?,updated=? WHERE id=?",(stage,work,stamp(),rec["id"]))
        elif command=="comment":
            content=field(b.get("content"),"评论内容",800)
            kind=b.get("kind") or ("事实纠错" if any(k in content for k in ("错","不准确","出处")) else
                  "选题需求" if any(k in content for k in ("为什么","想看","怎么","能不能")) else "一般反馈")
            if kind not in ("事实纠错","选题需求","一般反馈","商务咨询"):raise ValueError("反馈类别无效")
            con.execute("INSERT INTO feedback(content,work,kind,created,status) VALUES(?,?,?,?,?)",
                        (content,str(b.get("work") or "")[:250],kind,stamp(),"待处理"))
        elif command=="reply":
            result=con.execute("UPDATE feedback SET reply=?,status=? WHERE id=?",
                   (field(b.get("reply"),"处理记录"),"已记录处理",int(b["id"])))
            if not result.rowcount:raise ValueError("找不到该评论")
        elif command=="experiment":register_experiment(con,b)
        else:raise ValueError("未知操作")
        event(con,"操作",{"profile":"更新账号定位","peers":"保存同行线索","note":"新增作品观察","plan":"新增原创排期",
              "edit_plan":"修订内容简报","stage":"更新制作阶段","comment":"登记评论","reply":"保存互动处理记录","experiment":"锁定对照与实验目标"}[command])
    return "已保存"

