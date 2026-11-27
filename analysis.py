"""Evidence-based editorial decisions. All rates are fractions internally."""
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from store import CST, dt, rows, profile

WINDOWS={"2h":(2,0.5),"24h":(24,3),"72h":(72,6),"7d":(168,12)}
NAMES={"retention5":"5秒留存率","completion":"完播率","depth":"每千播放收藏与分享",
       "conversion":"每千播放新增关注","plays":"播放量"}
UNITS={"retention5":"%","completion":"%","depth":"‰","conversion":"‰","plays":"次"}
ASPECTS=("选题","标题","前三秒","结构","画面证据","节奏","互动","系列","转化")
PATTERNS=("提问","反差","先给结果","现场验证","对照实验","动作分解","故事回扣","评论答疑","系列追更","其他")
RULES={
 "retention5":("检查开头","把关键动作或问题放进第一句话，其他镜头保持一致。"),
 "completion":("检查中段","标出解释开始和答案揭晓的位置，下条只提前一次可见证据。"),
 "conversion":("检查关注理由","在同类结尾预告下一条能替观众解决的具体问题。"),
 "depth":("检查可复用价值","把观众可以照做的步骤，变成一次可见的演示。"),
 "plays":("检查分发","核对来源、发布时间、封面和搜索词，在下一篇只测试一项。")}
def display(k,x):
    if x is None:return "缺数据"
    scale=100 if UNITS[k]=="%" else 1
    return f"{x*scale:.1f}{UNITS[k]}"

def measurements(m):
    plays=m.get("plays")
    def per(*keys):
        if not plays or any(m.get(k) is None for k in keys): return None
        return sum(m[k] for k in keys)*1000/plays
    return {**{k:m.get(k) for k in ("plays","retention5","completion")},
            "depth":per("saves","shares"),"conversion":per("follows")}

def observations(con):
    latest={}
    slots={}
    for row in rows(con,"SELECT * FROM snaps ORDER BY observed"):
        row["values"]=json.loads(row.pop("metrics"))
        row["rates"]=measurements(row["values"])
        previous=latest.get(row["work"])
        row["trend"]=None
        if previous and previous["origin"]==row["origin"] and previous["values"]["plays"] is not None and row["values"]["plays"] is not None:
            diff=row["values"]["plays"]-previous["values"]["plays"]
            hours=(dt(row["observed"])-dt(previous["observed"])).total_seconds()/3600
            if diff>=0 and hours>0:
                row["trend"]={"delta":diff,"hours":round(hours,1),"from":previous["observed"]}
        latest[row["work"]]=row
        age=(dt(row["observed"])-dt(row["published"])).total_seconds()/3600
        if row["origin"].startswith("官方统计"):
            continue  # Upstream has a reporting lag; collection time is not the metric cut-off.
        for label,(target,slack) in WINDOWS.items():
            key=(row["work"],label)
            if abs(age-target)<=slack and (key not in slots or abs(age-target)<slots[key][0]):
                slots[key]=(abs(age-target),row)
    return latest,{k:v[1] for k,v in slots.items()}

def controls(slots,row,window,metric):
    if row["series"]=="未分类" or row["traffic"]=="未知":return []
    earliest=dt(row["published"])-timedelta(days=90)
    return sorted((v for (work,w),v in slots.items() if w==window and work!=row["work"]
                and v["series"]==row["series"] and v["traffic"]==row["traffic"]
                and earliest<=dt(v["published"])<dt(row["published"])
                and v["observed"]<=row["observed"] and v["rates"][metric] is not None),
                key=lambda v:v["published"],reverse=True)[:12]

def diagnose(latest,slots):
    out=[]
    for work,last in sorted(latest.items(),key=lambda x:x[1]["published"],reverse=True)[:35]:
        window=next((w for w in reversed(WINDOWS) if (work,w) in slots),None)
        row=slots.get((work,window),last)
        signals=[]
        for k in RULES:
            x=row["rates"][k]
            peers=controls(slots,row,window,k) if window else []
            med=statistics.median([v["rates"][k] for v in peers]) if len(peers)>=3 else None
            ratio=x/med if x is not None and med and med>0 else None
            signals.append(dict(key=k,name=NAMES[k],value=display(k,x),base=display(k,med),n=len(peers),ratio=ratio))
        low=next((s for s in signals if s["ratio"] is not None and s["ratio"]<0.8),None)
        strong=next((s for s in signals if s["key"] in ("depth","conversion","completion")
                     and s["ratio"] is not None and s["ratio"]>=1.2),None)
        if low:
            label,action=RULES[low["key"]]; chosen=low
        elif strong:
            label="测试同系列续集"; action="保留本次表达方法，更换一个相邻生活场景，验证能否再次出现。"; chosen=strong
        elif any(s["ratio"] is not None for s in signals):
            label="沿用本轮方案";action="继续记录同窗口数据，先保持选题与制作节奏。";chosen=None
        else:
            label="补齐可比样本";action="记录同系列、同流量类型至少三条更早作品的同窗口数据。";chosen=None
        evidence=(f'{chosen["name"]} {chosen["value"]}，历史中位数 {chosen["base"]}，{chosen["n"]} 条对照。'
                  if chosen else "可在指标表查看样本数和观察时点。")
        out.append(dict(work=work,title=row["title"],series=row["series"],traffic=row["traffic"],window=window or "窗口外",
                        observed=row["observed"],latest_observed=last["observed"],published=row["published"],origin=row["origin"],
                        latest=last["values"],trend=last["trend"],signals=signals,label=label,action=action,evidence=evidence))
    return out

def peer_review(con, cfg):
    grouped=defaultdict(list)
    notes=defaultdict(list)
    for note in rows(con,"SELECT * FROM notes ORDER BY id DESC"):notes[note["url"]].append(note)
    for item in rows(con,"SELECT * FROM peers ORDER BY seen DESC"):
        item["notes"]=notes[item["url"]]
        text=" ".join([item["title"],item["summary"],item["keyword"]])
        item["terms"]=[k for k in cfg["keywords"] if k in text]
        # Nicknames are provisional labels. A manual stable profile URL is preferable.
        grouped[item["author"] or item["url"]].append(item)
    result=[]
    for author,items in grouped.items():
        works=[i for i in items if "/user/" not in i["url"]]
        pattern=Counter(p for i in works for p in {n["pattern"] for n in i["notes"] if n["pattern"]!="其他"})
        recurring=[k for k,v in pattern.items() if v>=2]
        matched=sorted({k for i in items for k in i["terms"]})
        reviewed=sum(bool(i["notes"]) for i in works)
        title=items[0]["author"] or "作者待核对"
        score=min(3,len(matched))*2+min(3,len(works))+min(3,reviewed)*2+min(2,len(recurring))*2
        result.append(dict(author=title,works=len(works),items=items,terms=matched,reviewed=reviewed,
                           patterns=recurring,score=score,grade="可做迁移实验" if recurring else
                           ("补看第二条作品" if reviewed else "待核对内容"),
                           key=author))
    return sorted(result,key=lambda r:(-r["score"],r["author"]))

def experiment_status(con,slots):
    tests=rows(con,"SELECT * FROM tests ORDER BY id DESC")
    for t in tests:
        target=slots.get((t["work"],t["window"]))
        value=target["rates"][t["metric"]] if target else None
        expected=json.loads(t["controls"])
        valid=target and target["series"]==expected["series"] and target["traffic"]==expected["traffic"]
        if target and not valid:value=None
        chronology_ok=(target is not None and target["observed"]>=t["created"] and
                       (not expected.get("latest_control") or expected["latest_control"]<=target["published"]))
        t["status"]="等待目标窗口" if not target else ("作品分组不匹配" if not valid else
                    ("时序不符，需重新设计实验" if not chronology_ok else
                    ("缺目标指标" if value is None else ("达到预设目标" if value>=t["goal"] else "未达预设目标"))))
        t["result"]=display(t["metric"],value);t["base_label"]=display(t["metric"],t["baseline"])
        t["goal_label"]=display(t["metric"],t["goal"])
        t["controls_n"]=len(expected["works"])
    return tests

def register_experiment(con,b):
    from store import field, stamp
    metric=b["metric"]; window=b["window"]
    if metric not in NAMES or window not in WINDOWS:raise ValueError("指标或窗口无效")
    work=field(b.get("work"),"新作品ID",250)
    series=field(b.get("series"),"系列",100);traffic=b.get("traffic","自然")
    if traffic not in ("自然","付费","混合") or series=="未分类":raise ValueError("必须明确系列与流量类型")
    latest,slots=observations(con)
    if (work,window) in slots:raise ValueError("这条作品已有目标窗口结果，请选择尚未观测的新作品")
    if work in latest and (latest[work]["series"]!=series or latest[work]["traffic"]!=traffic):
        raise ValueError("该作品的流量类型或系列与实验不符")
    when=latest[work]["published"] if work in latest else stamp()
    peers=controls(slots,dict(work=work,series=series,traffic=traffic,published=when,observed=stamp()),window,metric)
    # Freeze inputs strictly before preregistration; late backfills cannot move the target.
    if len(peers)<3: raise ValueError("这个系列、流量与窗口至少需要三条历史作品")
    med=statistics.median([p["rates"][metric] for p in peers])
    uplift=float(b.get("uplift",10))
    if med<=0 or not 0<uplift<=200:raise ValueError("历史中位数须大于零，目标提升应在 0% 到 200% 之间")
    goal=med*(1+uplift/100)
    if metric in ("completion","retention5") and goal>1: raise ValueError("目标超过 100%，请调低提升幅度")
    con.execute("INSERT INTO tests(hypothesis,variable,work,metric,window,baseline,goal,controls,created) VALUES(?,?,?,?,?,?,?,?,?)",
                (field(b.get("hypothesis"),"实验假设"),field(b.get("variable"),"唯一改动"),work,metric,window,med,goal,
                 json.dumps(dict(series=series,traffic=traffic,works=[p["work"] for p in peers],
                                 latest_control=max(p["observed"] for p in peers)),ensure_ascii=False),stamp()))

