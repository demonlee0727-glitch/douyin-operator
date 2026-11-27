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
const paths = {
  home: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  pulse: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
  radar: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><path d="m12 12 7-7"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7.5 3v4m9-4v4M3 10h18m-14 4h3m4 0h3"/>',
  chat: '<path d="M20.5 14.5a3 3 0 0 1-3 3H10l-5 3v-3.2a3 3 0 0 1-2-2.8V7a3 3 0 0 1 3-3h11.5a3 3 0 0 1 3 3zM7 9h9m-9 4h6"/>',
  flask: '<path d="M9 3h6m-5 0v6l-5.7 9.2A2 2 0 0 0 6 21h12a2 2 0 0 0 1.7-2.8L14 9V3M8 15h8"/>',
  book: '<path d="M12 6c-3-2-6-2.5-9-1.5V19c3-1 6-1 9 1 3-2 6-2 9-1V4.5C18 3.5 15 4 12 6Zm0 0v14"/>',
  source: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  sync: '<path d="M3 10a9 9 0 0 1 15-5l2 2m0-4v4h-4M21 14a9 9 0 0 1-15 5l-2-2m0 4v-4h4"/>',
  print: '<path d="M7 8V3h10v5M7 17H4V9h16v8h-3"/><path d="M7 14h10v7H7zm9-3h1"/>',
  arrow: '<path d="m10 5 7 7-7 7"/>',
  import: '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  dial: '<path d="M4 17a9 9 0 1 1 16 0M12 12l4-5"/><circle cx="12" cy="12" r="1.7"/>'
};
const tabIcons = ['home','pulse','radar','calendar','chat','flask','book','source'];
const icon = (name,size=20) => '<svg class="icon" width="'+size+'" height="'+size+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+paths[name]+'</svg>';
const tabButton = (dest,body,cls='',name=dest) => '<button type="button" class="'+cls+'" data-tab="'+esc(dest)+'" title="'+esc(name)+'" aria-label="'+esc(name)+'">'+body+'</button>';
const cap = (label,glyph) => '<div class="panel-title">'+icon(glyph,16)+'<h2>'+esc(label)+'</h2></div>';
const readout = (label,value,unit='') => '<div class="readout"><span>'+esc(label)+'</span><strong>'+esc(value)+'<small>'+esc(unit)+'</small></strong></div>';
const viewChoice = {home:'schedule', diag:'retention5'};
const choices = {
  home: [['schedule','排期进度'],['feedback','反馈处理']],
  diag: [['retention5','5 秒留存'],['completion','完播率']]
};
function dialModel(kind){
  const key=viewChoice[kind];
  if(kind==='diag'){
    const work=S.decisions[0];
    const signal=work?.signals.find(s=>s.key===key);
    const value=signal && signal.value.endsWith('%') ? parseFloat(signal.value) : null;
    return {value,label:key==='retention5'?'5 秒留存率':'完播率',context:work?.title||'等待作品快照',left:[['历史中位数',signal && signal.n>=3 ? signal.base:'—'],['可比作品',signal?.n??0,'条']],
      entry:['数据接入','source'],secondary:['增长实验','flask']};
  }
  const feedback=key==='feedback';
  const total=feedback?S.comments.length:S.profile.weekly_capacity;
  const done=feedback?S.comments.filter(c=>c.status!=='待处理').length:S.forecast;
  return {value:total?100*done/total:null,label:feedback?'反馈处理率':'七天排期覆盖率',context:feedback?'已处理反馈 / 全部反馈':'未来七天 / 每周产能',
    left:feedback?[['已处理',done,'条'],['待处理',total-done,'条']]:[['已排期',done,'条'],['每周产能',total,'条']],
    entry:['内容排期','calendar'],secondary:['评论互动','chat']};
}
function meterPanel(kind){
  const m=dialModel(kind), value=m.value;
  const displayed=value===null?'—':String(Number(value.toFixed(kind==='diag'?1:0)));
  const arc=value===null?0:Math.max(0,Math.min(value,100))*2.7;
  const segment=choices[kind].map(([key,label])=>'<button type="button" data-dial="'+key+'" aria-pressed="'+(viewChoice[kind]===key)+'">'+label+'</button>').join('');
  return '<section class="instrument"><div class="instrument-head">'+cap(kind==='home'?'运营仪表盘':'作品表现仪表盘','dial')+
    '<span class="instrument-sub">'+(kind==='home'?'未来 7 天':'最近一篇')+'</span></div><div class="instrument-body"><div class="readouts">'+m.left.map(a=>readout(...a)).join('')+
    '</div><div class="meter-assembly"><div class="outer-orbit"></div><div class="meter '+(value===null?'no-value':'')+'" style="--sweep:'+arc+'deg">'+
    '<div class="dial-track"></div><div class="ticks"></div><div class="knob"><i class="indicator"></i><strong>'+esc(displayed)+(value===null?'':'<small>%</small>')+'</strong><span>'+esc(m.label)+'</span></div></div>'+
    tabButton(m.entry[0],icon(m.entry[1],16),'orb orb-a')+tabButton(m.secondary[0],icon(m.secondary[1],16),'orb orb-b')+
    '</div></div><div class="dial-caption">'+esc(m.context)+'</div><div class="segments" aria-label="仪表指标">'+segment+'</div></section>';
}
function weekSeries(){
  const start=Date.parse(S.now.slice(0,10)+'T00:00:00Z');
  return Array.from({length:7},(_,i)=>{
    const day=new Date(start+i*86400000).toISOString().slice(0,10);
    return {label:day.slice(5).replace('-','/'),value:S.plans.filter(p=>p.due===day).length};
  });
}
function linePlot(samples,unit){
  const w=316,h=94,x0=14,x1=302,y0=12,y1=72;
  const maximum=Math.max(1,...samples.map(a=>a.value));
  const point=(v,i)=>[samples.length===1?(x0+x1)/2:x0+(x1-x0)*i/Math.max(1,samples.length-1),y1-(y1-y0)*v/maximum];
  const points=samples.map((a,i)=>point(a.value,i));
  let grid='';
  for(const y of [y0,(y0+y1)/2,y1])grid+='<path class="gridline" d="M'+x0+' '+y+'H'+x1+'"/>';
  const line=points.map((p,i)=>(i?'L':'M')+p.map(a=>a.toFixed(2)).join(' ')).join(' ');
  const circles=points.map(([x,y],i)=>'<circle cx="'+x+'" cy="'+y+'" r="3"><title>'+esc(samples[i].label+' · '+samples[i].value+unit)+'</title></circle>').join('');
  const labels=samples.length?'<div class="axis"><span>'+esc(samples[0].label)+'</span><span>'+esc(samples[samples.length-1].label)+'</span></div>':'';
  return '<div class="chart"><svg preserveAspectRatio="none" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="'+esc(samples.map(v=>v.label+' '+v.value+unit).join('，')||'暂无可绘制数据')+'">'+grid+
    (points.length?'<path class="chart-fill" d="'+line+' L'+points[points.length-1][0]+' '+y1+' L'+points[0][0]+' '+y1+'Z"/><path class="chart-line" d="'+line+'"/>'+circles:'')+'</svg>'+
    (points.length?'':'<span class="chart-empty">等待作品快照</span>')+labels+'</div>';
}
function sidePanels(kind){
  const diag=kind==='diag', key=viewChoice.diag;
  const samples=diag?S.decisions.slice(0,7).reverse().flatMap(d=>{
    const s=d.signals.find(a=>a.key===key);
    return s?.value.endsWith('%')?[{label:d.published.slice(5,10).replace('-','/'),value:parseFloat(s.value)}]:[];
  }):weekSeries();
  const title=diag?(key==='retention5'?'近期作品留存':'近期作品完播'):'七天排期分布';
  const desc=diag?'各作品采用快照':'按计划发布日期';
  return '<div class="side-panels"><section class="surface trend-card">'+cap(title,'pulse')+'<div class="plot-info">'+esc(desc)+'<span><i></i>'+esc(diag?'比例':'条数')+'</span></div>'+linePlot(samples,diag?'%':' 条')+'</section>'+
    '<section class="surface data-card">'+cap('作品数据','source')+'<div class="data-numbers">'+readout('已记录作品',S.count,'条')+readout('指标快照',S.snapshot_count,'份')+'</div>'+
    tabButton('数据接入',icon('import',15)+'<span>'+(S.static?'查看数据接入':'导入作品快照')+'</span>'+icon('arrow',13),'data-link',S.static?'查看数据接入':'导入作品快照')+'</section></div>';
}
function dashboard(kind){return '<div class="dashboard">'+meterPanel(kind)+sidePanels(kind)+'</div>'}
const taskPage={'数据':'数据接入','排期':'内容排期','选题':'内容排期','诊断':'账号诊断','复盘':'账号诊断','互动':'评论互动','对标':'同行雷达','实验':'增长实验'};
function today(){
  const jobs=S.today.map(j=>'<div class="queue-row"><span class="queue-icon">'+icon(tabIcons[tabs.indexOf(taskPage[j.kind]||'今日工作')],17)+'</span><div><small>'+esc(j.kind)+'</small><h3>'+esc(j.title)+'</h3><p>'+esc(j.detail)+'</p></div>'+
      tabButton(taskPage[j.kind]||'今日工作',icon('arrow',14),'row-go','前往'+(taskPage[j.kind]||'今日工作'))+'</div>').join('');
  const periods=[S.weekly,S.monthly].map(r=>'<div class="item"><h3>近 '+r.days+' 天</h3><p>'+r.works+' 条已记录作品 · '+r.plans+' 条排期</p><small>'+
      esc(Object.entries(r.series).map(([k,v])=>k+' '+v).join(' / ')||'尚无该周期作品')+'</small>'+r.signals.map(t=>'<p>'+esc(t)+'</p>').join('')+'<p class="sub">待补对照 '+r.insufficient+' 条作品</p></div>').join('');
  const history=S.events.slice(0,6).map(e=>'<div class="item"><small>'+esc(e.created.slice(5,16))+' · '+esc(e.kind)+'</small><div>'+esc(e.message)+'</div></div>').join('');
  return dashboard('home')+'<div class="grid overview-grid">'+box('今日优先事项',jobs||empty('目前没有待处理事项。'))+
    box('本轮运营','<h3>'+esc(S.profile.name)+'</h3><p>'+esc(S.profile.promise)+'</p><p class="sub">'+esc(S.profile.audience)+'</p>'+S.profile.keywords.map(k=>tag(k)).join('')+
    '<div class="item"><small>最近观察</small><p>'+esc(S.last_observed||'尚未接入自己的作品')+'</p></div>'+fold('近 7 天与 30 天复盘',periods))+'</div>'+box('最近运行',history||empty('首轮同步后显示运行记录。'));
}
function diagnostics(){
 return dashboard('diag')+'<p class="sub diag-note">比较同系列、同流量类型、同观察窗口的历史中位数。窗口外和缺字段会单列，未知指标不计为零。</p>'+(!S.decisions.length?box("等待自己的作品",empty("在「数据接入」导入真实快照后，这里会列出每条作品的依据和下一步。")):S.decisions.map(d=>box(d.title,tag(d.series)+tag(d.traffic)+tag(d.window)+tag(d.label,"warn")+'<p>'+(d.trend?"同源相邻观察间增加 "+esc(d.trend.delta)+" 次播放，跨度 "+esc(d.trend.hours)+" 小时。 ":"")+esc(d.evidence)+'</p><b>'+esc(d.action)+'</b><p class="sub">采用快照 '+esc(d.observed.slice(0,16))+' · 最近采集 '+esc(d.latest_observed.slice(0,16))+' · '+esc(d.origin)+'</p>'+tbl(["指标","本篇","历史中位数","对照作品数"],d.signals.map(s=>[s.name,s.value,s.n>=3?s.base:"待积累",s.n]))+fold("最新原始指标",tbl(["指标","值"],Object.entries(d.latest).map(([k,v])=>[({"plays":"播放","likes":"赞","comments":"评论","shares":"分享","saves":"收藏","follows":"新增关注","completion":"完播率","retention5":"5秒留存率"})[k],v==null?"未提供":(["completion","retention5"].includes(k)?(100*v).toFixed(1)+"%":v)])) ))).join(""));
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
 $("mode").textContent=(S.demo?"演示 · ":"")+(S.static?"离线快照":"本地工作台");
 $("fresh").textContent="数据读取于 "+S.now.slice(0,16).replace("T"," ")+" 北京时间";
 $("date").textContent=S.now.slice(0,10).replaceAll("-"," / ");
 $("account").textContent=S.profile.name;
 $("title").textContent=page;
 $("nav").innerHTML=tabs.map((t,i)=>'<button type="button" data-tab="'+t+'" aria-label="'+t+'" title="'+t+'"'+(page===t?' aria-current="page"':'')+'>'+icon(tabIcons[i],20)+'<span>'+t+'</span></button>').join("");
 $("view").innerHTML=[today,diagnostics,radar,calendar,comments,experiments,playbook,settings][tabs.indexOf(page)]();
 $("sync").hidden=S.static;
}
function notice(s){$("notice").hidden=false;$("notice").textContent=s}
async function reloadState(){let r=await fetch("/api/state",{cache:"no-store"});if(!r.ok)throw Error("读取失败");S=await r.json();draw()}
async function submit(b){let r=await fetch("/api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Operator-Request":"1"},body:JSON.stringify(b)});let result=await r.json();if(!r.ok)throw Error(result.error||"保存失败");await reloadState();notice(result.message)}
document.addEventListener("submit",async e=>{e.preventDefault();const f=e.target;const btn=f.querySelector("button");btn.disabled=true;try{await submit({...Object.fromEntries(new FormData(f)),command:f.dataset.op})}catch(x){notice(x.message)}finally{btn.disabled=false}});
document.addEventListener("click",e=>{
 const dial=e.target.closest("button[data-dial]");
 if(dial){
   const kind=page==="今日工作"?"home":"diag";
   viewChoice[kind]=dial.dataset.dial;
   $("view").querySelector(".dashboard").outerHTML=dashboard(kind);
   $("view").querySelector('[data-dial="'+viewChoice[kind]+'"]').focus({preventScroll:true});
   return;
 }
 const button=e.target.closest("button[data-tab]");
 if(button && tabs.includes(button.dataset.tab) && page!==button.dataset.tab){
   page=button.dataset.tab;
   history.replaceState(null,"","#"+encodeURIComponent(page));
   draw();
   window.scrollTo(0,0);
   $("title").focus({preventScroll:true});
 }
});
document.addEventListener("change",async e=>{if(e.target.id==="csvfile"&&e.target.files[0]){const f=e.target.files[0];if(f.size>3_800_000){notice("文件过大，请使用 inbox 文件夹。");return}e.target.closest("form").elements.csv.value=await f.text()}});
$("sync").onclick=async()=>{$("sync").disabled=true;try{await submit({command:"sync"})}catch(e){notice(e.message)}finally{$("sync").disabled=false}};
$("print").onclick=()=>window.print();
$("sync").innerHTML=icon("sync",16)+"<span>立即检查</span>";
$("print").innerHTML=icon("print",17);
$("title").setAttribute("tabindex","-1");
draw();if(!S.static)setInterval(()=>{if(!document.hidden&&!document.querySelector("details[open]")&&!["INPUT","TEXTAREA","SELECT"].includes(document.activeElement.tagName))reloadState().catch(()=>notice("工作台连接中断，已保留当前画面。"))},30000);

