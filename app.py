#!/usr/bin/env python3
"""Douyin Operator, local-first. Python 3.9+."""
import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from store import CST, ROOT, db, event, import_csv, setup, stamp
from desk import add_seed, change, state
from monitor import cycle

def demo(home):
    with db(home) as con:
        if con.execute("SELECT 1 FROM imports WHERE digest='demo-v1'").fetchone():return
        writer_io=io.StringIO()
        writer=csv.writer(writer_io)
        writer.writerow("work title published observed series traffic plays likes comments shares saves follows completion retention5".split())
        origin=datetime.now(CST).replace(minute=0,second=0,microsecond=0)-timedelta(days=7)
        for i,(topic,views,ret,comp,fol) in enumerate([
            ("雨伞上的水珠",1300,.52,.23,8),("车窗的倒影",1500,.50,.24,9),("盒盖的卡扣",1420,.54,.22,8),
            ("杯壁上的水滴",1800,.53,.25,12),("纸袋提手的折角",1400,.30,.14,4)]):
            pub=origin+timedelta(days=i)
            writer.writerow([f"demo-{i+1}","演示 · "+topic,pub.isoformat(),(pub+timedelta(days=1)).isoformat(),
                             "生活科普","自然",views,40+i*3,5,6,12,fol,comp,ret])
        import_csv(con,writer_io.getvalue(),"合成演示")
        con.execute("INSERT INTO imports VALUES('demo-v1','demo',5,?)",(stamp(),))
    # Populate editorial screens with explicitly synthetic activity in the isolated demo folder.
    change(home,"comment",dict(content="演示留言：为什么玻璃杯外有水，保温杯外却很干？",work="demo-4"))
    change(home,"plan",dict(title="演示 · 同一杯冰水，换个杯子为什么没有水珠？",
            due=datetime.now(CST).date().isoformat(),brief="首镜并排两只杯子，请观众先猜。保持水温与机位，核对环境湿度，只测试第一镜；观察 24 小时的 5 秒留存率。",
            url="https://www.douyin.com/video/7494578413089459493"))
    change(home,"experiment",dict(work="demo-next",series="生活科普",traffic="自然",window="24h",metric="retention5",
            hypothesis="演示 · 开场先给对照组可以改善观看留存",variable="首镜显示两只杯子",uplift=10))

def render(home,static=False,is_demo=False):
    template=(ROOT/"web"/"index.html").read_text(encoding="utf8")
    data=state(home);data.update(static=static,demo=is_demo)
    encoded=json.dumps(data,ensure_ascii=False,allow_nan=False).replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    return template.replace("/*__CSS__*/",(ROOT/"web"/"style.css").read_text(encoding="utf8")).replace(
        "/*__JS__*/",(ROOT/"web"/"desk.js").read_text(encoding="utf8")).replace("/*__STATE__*/",encoded)

def handler(home,is_demo):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,code,data,mime):
            payload=data.encode("utf8")
            self.send_response(code);self.send_header("Content-Type",mime+"; charset=utf-8")
            self.send_header("Content-Length",str(len(payload)));self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-Frame-Options","DENY");self.end_headers();self.wfile.write(payload)
        def js(self,obj,status=200):
            self.reply(status,json.dumps(obj,ensure_ascii=False,allow_nan=False),"application/json")
        def local(self):
            return self.headers.get("Host","") in ("127.0.0.1:"+str(self.server.server_port),"localhost:"+str(self.server.server_port))
        def do_GET(self):
            if not self.local():return self.js({"error":"仅接受本机访问"},403)
            if self.path=="/":return self.reply(200,render(home,is_demo=is_demo),"text/html")
            if self.path=="/api/state":return self.js(dict(state(home),static=False,demo=is_demo))
            return self.js({"error":"未知页面"},404)
        def do_POST(self):
            host=self.headers.get("Host","")
            origin=self.headers.get("Origin")
            if not self.local() or (origin and origin!="http://"+host) or self.headers.get("X-Operator-Request")!="1":
                return self.js({"error":"请从本机工作台提交"},403)
            if self.path!="/api/action":return self.js({"error":"未知操作"},404)
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=4_000_000:raise ValueError("请求须小于 4 MB")
                b=json.loads(self.rfile.read(size))
                if not isinstance(b,dict):raise ValueError("需要 JSON 对象")
                op=b["command"]
                if op=="sync":msg="；".join(cycle(home,True))
                else:msg=change(home,op,b)
                return self.js({"message":msg})
            except (KeyError,ValueError,TypeError,sqlite3.IntegrityError) as e:
                return self.js({"error":str(e)},400)
            except (OSError,sqlite3.OperationalError):
                return self.js({"error":"数据暂不可用，请检查文件与本地数据库后重试"},503)
    return Handler

def serve(home,port,launch,is_demo):
    server=ThreadingHTTPServer(("127.0.0.1",port),handler(home,is_demo))
    stop=threading.Event()
    def run():
        while not stop.is_set():
            try:cycle(home)
            except Exception as e:
                with db(home) as con:event(con,"连接异常","本轮检查中断 · "+type(e).__name__)
            stop.wait(30)
    worker=threading.Thread(target=run,daemon=True);worker.start()
    url=f"http://127.0.0.1:{server.server_port}/"
    print(f"工作台 {url}\n本地数据 {home}\n保持窗口开启以持续检查。Ctrl+C 关闭。",flush=True)
    if launch:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close()

def main():
    p=argparse.ArgumentParser(description="抖音运营工作台")
    p.add_argument("command",choices=["serve","sync","report","state","action"],nargs="?",default="serve")
    p.add_argument("--data",type=Path,help="指定账号的私有数据目录")
    p.add_argument("--demo",action="store_true",help="在独立目录使用合成演示作品")
    p.add_argument("--port",type=int,default=8765);p.add_argument("--open",action="store_true")
    p.add_argument("--out",type=Path,help="HTML 报告路径")
    args=p.parse_args()
    home=(args.data or ROOT/"data").expanduser().resolve()
    if args.demo:home=home.parent/(home.name+"-demo")
    setup(home);add_seed(home)
    if args.demo:demo(home)
    if args.command=="serve":serve(home,args.port,args.open,args.demo)
    elif args.command=="sync":print("\n".join(cycle(home,True)))
    elif args.command=="report":
        dest=args.out or home/"运营复盘.html";dest.write_text(render(home,True,args.demo),encoding="utf8");print(dest)
    elif args.command=="action":
        body=json.load(sys.stdin);print(change(home,body["command"],body))
    else:print(json.dumps(state(home),ensure_ascii=False,indent=2))
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,sqlite3.Error) as exc:
        sys.exit(f"运行失败：{exc}")

