"use strict";
let S=JSON.parse(document.getElementById("state").textContent);
const $=id=>document.getElementById(id);
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const tabs=["今日工作","账号诊断","同行雷达","内容排期","评论互动","增长实验","运营手册","数据接入"];
let page=decodeURIComponent(location.hash.slice(1));if(!tabs.includes(page))page=tabs[0];
const tag=(x,c="")=>'<span class="tag '+c+'">'+esc(x)+'</span>';
const empty=t=>'<p class="empty">'+esc(t)+'</p>';
const card=(t,body)=>'<article class="card"><h3>'+esc(t)+'</h3>'+body+'</article>';
const box=(t,body)=>'<section class="box"><h2>'+esc(t)+'</h2>'+body+'</section>';
const stat=(n,t)=>'<div class="card stat"><small>'+esc(t)+'</small><strong>'+esc(n)+'</strong></div>';
const link=(url,title)=>'<a target="_blank" rel="noreferrer" href="'+esc(url)+'">'+esc(title)+'</a>';
const searchUrl=q=>"https://www.douyin.com/search/"+encodeURIComponent(q);
function input(n,t,v="",type="text",required=true){return '<label>'+esc(t)+'<input name="'+n+'" type="'+type+'" value="'+esc(v)+'" '+(required?"required":"")+'></label>'}
function area(n,t,v="",req=true){return '<label>'+esc(t)+'<textarea name="'+n+'" '+(req?"required":"")+'>'+esc(v)+'</textarea></label>'}
function options(n,t,values,sel=""){return '<label>'+esc(t)+'<select name="'+n+'">'+values.map(v=>'<option '+(v===sel?"selected":"")+'>'+esc(v)+'</option>').join("")+'</select></label>'}
const hid=(n,v)=>'<input type="hidden" name="'+n+'" value="'+esc(v)+'">';
function form(op,body,btn){return S.static?"":'<form data-op="'+op+'">'+body+'<button type="submit">'+esc(btn||"保存")+'</button></form>'}
function fold(t,body){return body?'<details><summary>'+esc(t)+'</summary>'+body+'</details>':""}
const tbl=(heads,data)=>'<div class="table"><table><thead><tr>'+heads.map(x=>'<th>'+esc(x)+'</th>').join("")+'</tr></thead><tbody>'+data.map(row=>'<tr>'+row.map(v=>'<td>'+esc(v)+'</td>').join("")+'</tr>').join("")+'</tbody></table></div>';
const studio="https://creator.douyin.com/creator-micro/home";
const day=()=>S.now.slice(0,10);
function planForm(extra="",value=""){return form("plan",extra+input("title","原创选题",value)+input("due","计划发布日",day(),"date")+area("brief","本期具体怎么拍，以及要观察哪个指标"),"加入排期")}
function today(){
 const blocks='<div class="stats">'+stat(S.count,"已记录作品")+stat(S.snapshot_count,"指标快照")+stat(S.forecast+"/"+S.profile.weekly_capacity,"未来七天排期")+'</div>';
 const jobs=S.today.map(j=>'<div class="item">'+tag(j.kind)+'<h3>'+esc(j.title)+'</h3><p>'+esc(j.detail)+'</p></div>').join("");
 return blocks+'<div class="grid">'+box("今日优先事项",jobs)+box("本轮运营",'<h3>'+esc(S.profile.name)+'</h3><p>'+esc(S.profile.promise)+'</p><p class="sub">'+esc(S.profile.audience)+'</p>'+S.profile.keywords.map(k=>tag(k)).join("")+'<div class="item"><h3>最近观察</h3>'+esc(S.last_observed||"尚未接入自己的作品")+'</div>'+[S.weekly,S.monthly].map(r=>'<div class="item"><b>近 '+r.days+' 天</b><p>'+r.works+' 条已记录作品 · '+r.plans+' 条排期</p><small>'+esc(Object.entries(r.series).map(([k,v])=>k+" "+v).join(" / ")||"尚无该周期作品")+r.signals.map(t=>"<p>"+esc(t)+"</p>").join("")+"<p>待补对照 "+r.insufficient+" 条作品</p>"+'</small></div>').join(""))+'</div>'+box("最近运行",S.events.slice(0,6).map(e=>'<div class="item"><small>'+esc(e.created.slice(5,16))+' · '+esc(e.kind)+'</small><div>'+esc(e.message)+'</div></div>').join("")||empty("首轮同步后显示运行记录。"));
}
function diagnostics(){
 return '<p class="sub">比较同系列、同流量类型、同观察窗口的历史中位数。窗口外和缺字段会单列，未知指标不计为零。</p>'+(!S.decisions.length?box("等待自己的作品",empty("在「数据接入」导入真实快照后，这里会列出每条作品的依据和下一步。")):S.decisions.map(d=>box(d.title,tag(d.series)+tag(d.traffic)+tag(d.window)+tag(d.label,"warn")+'<p>'+(d.trend?"同源相邻观察间增加 "+esc(d.trend.delta)+" 次播放，跨度 "+esc(d.trend.hours)+" 小时。 ":"")+esc(d.evidence)+'</p><b>'+esc(d.action)+'</b><p class="sub">采用快照 '+esc(d.observed.slice(0,16))+' · 最近采集 '+esc(d.latest_observed.slice(0,16))+' · '+esc(d.origin)+'</p>'+tbl(["指标","本篇","历史中位数","对照作品数"],d.signals.map(s=>[s.name,s.value,s.n>=3?s.base:"待积累",s.n]))+fold("最新原始指标",tbl(["指标","值"],Object.entries(d.latest).map(([k,v])=>[({"plays":"播放","likes":"赞","comments":"评论","shares":"分享","saves":"收藏","follows":"新增关注","completion":"完播率","retention5":"5秒留存率"})[k],v==null?"未提供":(["completion","retention5"].includes(k)?(100*v).toFixed(1)+"%":v)])) ))).join(""));
}
function radar(){
 const addPeer=form("peers",input("url","抖音作品或主页完整链接","","url")+input("author","作者（同名可用主页链接作标识）","", "text",false)+input("title","作品标题或主页名称")+input("keyword","匹配主题","", "text",false)+area("summary","观察摘要","",false),"存入雷达");
 const readText=i=>form("breakdown",hid("url",i.url)+area("transcript","粘贴可使用的字幕或逐段记录（支持 00:03 文本）")+'<label>拆解方式<select name="method"><option value="local">本地文字分析</option><option value="model">将该作品标题、输入文本发给 OpenAI 分析（需配置）</option></select></label>',"提取有出处的手法");
 const addNote=i=>form("note",hid("url",i.url)+options("aspect","拆解维度",["选题","标题","前三秒","结构","画面证据","节奏","互动","系列","转化"])+input("cue","时间点或出处，例如 00:12、作品标题、置顶评论")+area("evidence","看到或听到了什么")+options("pattern","可迁移手法",["提问","反差","先给结果","现场验证","对照实验","动作分解","故事回扣","评论答疑","系列追更","其他"]),"保存观察");
 return '<div class="controls">'+S.profile.keywords.map(k=>link(searchUrl(k),k+" ↗")).join(" · ")+'</div>'+fold("添加或校正同行线索",addPeer)+'<p class="sub">排名依据为主题匹配、作品数与证据覆盖。作者名称可能重复，可用同一主页链接重新归组。</p>'+
 S.peers.map(g=>box(g.author,tag(g.grade)+tag(g.works+" 条作品")+tag(g.reviewed+" 条有观察")+g.terms.map(k=>tag(k)).join("")+'<p class="sub">重复方法：'+esc(g.patterns.join("、")||"尚待跨作品验证")+'</p>'+g.items.map(i=>'<div class="item"><h3>'+link(i.url,i.title+" ↗")+'</h3><small>'+esc(i.source)+' · 入库 '+esc(i.first_seen.slice(0,10))+(i.likes==null?"":" · 公开点赞 "+esc(i.likes))+'</small><p>'+esc(i.summary)+'</p>'+i.notes.map(n=>'<p>'+tag(n.aspect)+' '+esc(n.cue)+' · '+esc(n.evidence)+' '+tag(n.pattern)+'</p>').join("")+(i.url.includes("/user/")?"":fold("按字幕自动拆解",readText(i))+fold("记录原作证据",addNote(i))+fold("借用手法，制作原创简报",planForm(hid("url",i.url))))+'</div>').join(""))).join("");
}
function calendar(){return fold("新增原创排期",planForm())+'<p>'+link(studio,"进入抖音创作者中心 ↗")+'</p>'+(S.plans.length?S.plans.map(p=>box(p.title,tag(p.stage)+tag(p.due)+'<p class="note">'+esc(p.brief)+'</p>'+fold("编辑标题、日期与简报",form("edit_plan",hid("id",p.id)+input("title","标题",p.title)+input("due","计划发布日",p.due,"date")+area("brief","简报",p.brief),"保存修改"))+fold("更新制作阶段",form("stage",hid("id",p.id)+options("stage","阶段",["选题","制作","待发布","已发布","已复盘"],p.stage)+input("work","发布后的实际作品 ID",p.work,"text",false),"更新阶段")))).join(""):empty("从同行的手法、评论问题或原创选题建立第一条排期。"))}
function comments(){return fold("登记一条观众反馈",form("comment",area("content","匿名评论原话")+input("work","来源作品 ID","","text",false)+options("kind","反馈类型",["","选题需求","事实纠错","商务咨询","一般反馈"]),"登记反馈"))+S.comments.map(c=>box(c.content,tag(c.kind)+tag(c.status)+'<small>'+esc(c.work)+'</small><p>'+esc(c.reply)+'</p>'+fold("记录回复或处理",form("reply",hid("id",c.id)+area("reply","回复草稿或已采取的动作",c.reply||({"选题需求":"你提到的这个场景很具体。你当时看到了什么现象？","事实纠错":"谢谢你指出这个细节。方便发一下对应的时间点或资料出处吗？","商务咨询":"可以具体说一下使用场景、交付物和期限吗？","一般反馈":""}[c.kind])),"保存处理记录"))+fold("转为原创选题",planForm(hid("feedback_id",c.id))))).join("")+(!S.comments.length?empty("记录真实观众的问题，系统优先提示事实质疑。"):"")}
function experiments(){return fold("登记单变量实验",form("experiment",area("hypothesis","预期哪种变化会改善哪项表现")+input("variable","只改变什么")+input("work","实验作品 ID（可预先约定，导入时须一致）")+input("series","历史对照系列")+options("traffic","流量类型",["自然","付费","混合"])+options("window","观察窗口",["2h","24h","72h","7d"],"24h")+'<label>主要指标<select name="metric"><option value="retention5">5秒留存率</option><option value="completion">完播率</option><option value="depth">每千播放收藏与分享</option><option value="conversion">每千播放新增关注</option><option value="plays">播放量</option></select></label>'+input("uplift","相对历史中位数提升（%）",10,"number"),"锁定对照与目标"))+(S.experiments.length?S.experiments.map(t=>box(t.hypothesis,tag(t.status)+tag(t.window)+'<p>'+esc(t.variable)+'</p>'+tbl(["历史基线","预设目标","已观察","对照数"],[[t.base_label,t.goal_label,t.result,t.controls_n]]))).join(""):empty("先积累三条可比作品，再锁定实验目标。"))}
function playbook(){return '<div class="cards">'+S.routines.map(r=>card(r[0],tag(r[1])+'<p>'+esc(r[2])+'</p><p><b>交付物</b>　'+esc(r[3])+'</p><small>'+esc(r[4])+'</small>')).join("")+'</div>'}
function settings(){
 const c=S.profile;
 const csvForm=form("metrics",'<label>读取本机 CSV<input id="csvfile" type="file" accept=".csv,text/csv"></label>'+area("csv","CSV 内容（UTF-8，可直接粘贴）")+input("observed","整表观察时间；文件已有该列可留空","","datetime-local",false),"校验并导入");
 return box("账号定位",S.static?esc(c.promise):form("profile",input("name","名称",c.name)+input("audience","目标受众",c.audience)+input("promise","栏目承诺",c.promise)+input("keywords","搜索词，以逗号分隔",c.keywords.join("，"))+input("weekly_capacity","每周产能",c.weekly_capacity,"number")+'<label><span><input style="width:auto" type="checkbox" name="auto_plan" '+(c.auto_plan?"checked":"")+'> 自动将真实观众需求和近期表现信号排入本周空档</span></label>',"保存定位"))+
 box("作品数据",'<p>导入同一作品不同时点的累计观察。文件目录模式会在工作台运行时每 30 秒检查一次。</p>'+fold("导入 CSV",csvForm)+'<small>必填作品ID、作品标题、发布时间、观察时间及至少一个指标。系列和流量类型决定能否比较。百分数填写 23% 或 0.23。</small>')+
 box("联网来源",Object.entries(S.sources).map(([k,v])=>'<div class="item">'+tag(v?"已配置":"未配置",v?"":"warn")+' '+esc(k)+'</div>').join("")+'<small>有资格的应用可接官方搜索和经营授权统计。公开网页索引有收录延迟。密钥只通过环境变量传入。接入步骤见 README。</small>')+box("连接记录",S.clocks.length?tbl(["来源","下次运行（北京时间）","连续异常"],S.clocks.map(x=>[x.name,x.next_time.slice(0,19),x.failures])):empty("尚未运行联网来源。"));
}
function draw(){
 $("mode").textContent=(S.demo?"演示 · ":"")+(S.static?"离线快照":"本地工作台");$("fresh").textContent=S.now.slice(0,16).replace("T"," ")+" 北京时间";
 $("date").textContent=S.profile.name+" / "+S.now.slice(0,10);$("account").innerHTML="<strong>"+esc(S.profile.name)+"</strong>"+esc(S.profile.audience);
 $("title").textContent=page;$("nav").innerHTML=tabs.map(t=>'<button data-tab="'+esc(t)+'" class="'+(page===t?"active":"")+'">'+esc(t)+'</button>').join("");
 $("view").innerHTML=[today,diagnostics,radar,calendar,comments,experiments,playbook,settings][tabs.indexOf(page)]();
 $("sync").hidden=S.static;
}
function notice(s){$("notice").hidden=false;$("notice").textContent=s}
async function reloadState(){let r=await fetch("/api/state",{cache:"no-store"});if(!r.ok)throw Error("读取失败");S=await r.json();draw()}
async function submit(b){let r=await fetch("/api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Operator-Request":"1"},body:JSON.stringify(b)});let result=await r.json();if(!r.ok)throw Error(result.error||"保存失败");await reloadState();notice(result.message)}
document.addEventListener("submit",async e=>{e.preventDefault();const f=e.target;const btn=f.querySelector("button");btn.disabled=true;try{await submit({...Object.fromEntries(new FormData(f)),command:f.dataset.op})}catch(x){notice(x.message)}finally{btn.disabled=false}});
$("nav").addEventListener("click",e=>{const b=e.target.closest("button");if(b){page=b.dataset.tab;history.replaceState(null,"","#"+encodeURIComponent(page));draw()}});
document.addEventListener("change",async e=>{if(e.target.id==="csvfile"&&e.target.files[0]){const f=e.target.files[0];if(f.size>3_800_000){notice("文件过大，请使用 inbox 文件夹。");return}e.target.closest("form").elements.csv.value=await f.text()}});
$("sync").onclick=async()=>{$("sync").disabled=true;try{await submit({command:"sync"})}catch(e){notice(e.message)}finally{$("sync").disabled=false}};
$("print").onclick=()=>window.print();
draw();if(!S.static)setInterval(()=>{if(!document.hidden&&!document.querySelector("details[open]")&&!["INPUT","TEXTAREA","SELECT"].includes(document.activeElement.tagName))reloadState().catch(()=>notice("工作台连接中断，已保留当前画面。"))},30000);

