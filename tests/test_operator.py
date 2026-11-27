import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from analysis import measurements, observations
from app import demo, handler, render
from desk import add_seed, change, draft_from_signals, state
from monitor import cycle, find_public, own_step
from store import CST, db, setup, snapshot, stamp

class OperatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        setup(self.home);add_seed(self.home)
        env=patch.dict(os.environ,{},clear=True);env.start();self.addCleanup(env.stop)
    def put(self,**kw):
        change(self.home,"peers",dict(url="https://www.douyin.com/video/123456789",title="手把手对照实验",author="测试作者",**kw))
    def test_real_account_starts_empty_and_seed_is_idempotent(self):
        add_seed(self.home)
        s=state(self.home)
        self.assertEqual((s["count"],len(s["peers"]),sum(p["works"] for p in s["peers"])),(0,2,3))
    def test_missing_zero_and_ratios(self):
        self.assertIsNone(measurements({"plays":0,"shares":5,"saves":5})["depth"])
        self.assertIsNone(measurements({"plays":10,"shares":0})["depth"])
        self.assertEqual(measurements({"plays":100,"shares":0,"saves":0})["depth"],0)
    def test_import_rolls_back_and_retries(self):
        now=datetime.now(CST);pub=(now-timedelta(days=1)).isoformat()
        header="作品ID,作品标题,发布时间,观察时间,播放量,完播率\n"
        valid=f"1,示例,{pub},{now.isoformat()},32,25%\n"
        with self.assertRaises(ValueError):
            change(self.home,"metrics",dict(csv=header+valid+f"2,错,{pub},{now.isoformat()},NaN,25%\n"))
        self.assertEqual(state(self.home)["count"],0)
        for _ in range(2):change(self.home,"metrics",dict(csv=header+valid))
        self.assertEqual(state(self.home)["snapshot_count"],1)
    def test_demo_diagnosis_and_official_lag(self):
        demo(self.home)
        d=state(self.home)["decisions"][0];self.assertEqual(d["label"],"检查开头")
        with db(self.home) as c:
            snapshot(c,dict(work="delayed",observed=stamp(),published=(datetime.now(CST)-timedelta(days=1)).isoformat(),
                       series="生活科普",traffic="自然",title="延迟统计",plays=1400),"官方统计·次日刷新")
            latest,slots=observations(c)
        self.assertIn("delayed",latest);self.assertNotIn(("delayed","24h"),slots)
    def test_case_to_plan_to_review(self):
        self.put()
        url="https://www.douyin.com/video/123456789"
        change(self.home,"breakdown",dict(url=url,transcript="00:03 为什么两个杯子不同？\n00:10 我们来测一下。"))
        self.assertTrue(any("00:10" in n["cue"] for p in state(self.home)["peers"] for i in p["items"] for n in i["notes"]))
        change(self.home,"plan",dict(title="我的原创观察",due=stamp()[:10],brief="两只相同杯子并排验证。",url=url))
        plan=state(self.home)["plans"][0]
        self.assertIn(url,plan["brief"])
        change(self.home,"edit_plan",dict(id=plan["id"],due=stamp()[:10],title="改题",brief=plan["brief"]))
        with self.assertRaises(ValueError):change(self.home,"stage",dict(id=plan["id"],stage="已复盘",work="unseen"))
        demo(self.home);change(self.home,"stage",dict(id=plan["id"],stage="已复盘",work="demo-1"))
    def test_auto_scheduling_capacity_and_retries(self):
        cfg=state(self.home)["profile"]
        change(self.home,"profile",dict(cfg,keywords="生活科普",weekly_capacity=1,auto_plan="on"))
        for text in ("为什么杯底有圈？","为什么水滴不下去？"):
            change(self.home,"comment",dict(content=text))
        self.assertEqual((draft_from_signals(self.home),draft_from_signals(self.home)),(1,0))
        self.assertEqual(len(state(self.home)["plans"]),1)
    def test_experiment_frozen_and_resolves(self):
        demo(self.home)
        b=dict(work="next",metric="retention5",window="24h",series="生活科普",traffic="自然",hypothesis="展示动作能提升留存",
               variable="第一镜",uplift=10)
        change(self.home,"experiment",b)
        before=state(self.home)["experiments"][0]
        self.assertEqual(before["status"],"等待目标窗口")
        with db(self.home) as c:
            snapshot(c,dict(work="next",title="自己的新作",series="生活科普",traffic="自然",observed=stamp(),
                published=(datetime.now(CST)-timedelta(days=1)).isoformat(),retention5=".8"),"测试导入")
        after=state(self.home)["experiments"][0]
        self.assertEqual(after["baseline"],before["baseline"])
        self.assertEqual(after["status"],"达到预设目标")
        with self.assertRaises(ValueError):change(self.home,"experiment",b)
    def test_folder_import_and_invalid_link(self):
        inp=self.home/"inbox"/"peer.json"
        inp.write_text(json.dumps([dict(url="https://www.douyin.com/video/55555",title="实验",author="新同行")]))
        cycle(self.home);cycle(self.home)
        self.assertEqual(len(state(self.home)["peers"]),3)
        with self.assertRaises(ValueError):change(self.home,"peers",dict(url="https://example.com/video/555",title="不能入库"))
    def test_search_contract_retry_and_business_stats(self):
        with patch.dict(os.environ,{"DY_SEARCH_TOKEN":"test","DY_DEVICE_ID":"123"}):
            with patch("monitor.get_json",return_value={"data":{"data":{"video_list":[{"link":"https://www.douyin.com/video/555","title":"验证","nickname":"测试"}]}}}):
                self.assertEqual(next(find_public("科普","官方搜索"))["author"],"测试")
            with patch("monitor.get_json",side_effect=ValueError("权限不足")) as api:
                cycle(self.home,True);cycle(self.home,True);self.assertEqual(api.call_count,1)
        with patch.dict(os.environ,{"DY_BUSINESS_TOKEN":"test","DY_OPEN_ID":"test"}):
            pub=(datetime.now(CST)-timedelta(days=1)).isoformat()
            (self.home/"tracked.csv").write_text("work,item_id,title,published,series,traffic\n111,abc,真实格式,"+pub+",科普,自然\n")
            with patch("monitor.get_json",return_value={"err_no":0,"data":{"extra":{"error_code":0},"data":{"result":{"total_play":120,"total_like":10}}}}):
                own_step(self.home,0)
            self.assertEqual(state(self.home)["decisions"][0]["latest"]["plays"],120)
    def test_http_routes_and_snapshot(self):
        home=self.home
        class RequestPipe:
            def __init__(self,request):self.input=io.BytesIO(request);self.out=bytearray()
            def makefile(self,*args,**kwargs):return self.input
            def sendall(self,b):self.out.extend(b)
        def request(raw):
            conn=RequestPipe(raw.encode())
            handler(home,False)(conn,("127.0.0.1",1010),SimpleNamespace(server_port=8765))
            return bytes(conn.out)
        self.assertIn(b"200 OK",request("GET / HTTP/1.1\r\nHost: localhost:8765\r\n\r\n"))
        self.assertIn(b"403 Forbidden",request("GET /api/state HTTP/1.1\r\nHost: example.com\r\n\r\n"))
        self.assertIn(b"403 Forbidden",request("POST /api/action HTTP/1.1\r\nHost: localhost:8765\r\nOrigin: https://example.com\r\n\r\n"))
        payload=json.dumps({"command":"comment","content":"hello"})
        result=request("POST /api/action HTTP/1.1\r\nHost: localhost:8765\r\nX-Operator-Request: 1\r\nContent-Length: "+str(len(payload))+"\r\n\r\n"+payload)
        self.assertIn(b"200 OK",result);self.assertEqual(len(state(home)["comments"]),1)
        self.assertNotIn("/*__STATE__*/",render(home,True))
    def test_source_text_is_escaped_in_report(self):
        self.put(summary="</script><img src=x onerror=alert(1)>")
        self.assertNotIn("</script><img",render(self.home,True))

