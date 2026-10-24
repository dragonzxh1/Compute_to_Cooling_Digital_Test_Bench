import {escapeHTML as E,number as N,stateLabel,atTime,flowMark,advanceFlowOffset,flowGlyphs,temperatureColor,singleFrame,singleEvents,visibleEvents,matchingDynamic,singleScene,systemScene,sixScene,cduScene,tankScene,resultScene,sourceSwitchScene,cduSwitchScene,sceneSVG,referenceEnergy,curveSVG} from './visual-core.mjs';

export function visualReportHTML(options,session){
 const result=matchingDynamic(options.result,options.designHash);
 const payload={design:options.design,history:options.history,single:options.single,switching:options.switching,result,designHash:options.designHash,issues:options.issues||[],session:{...session,playing:false}};
 const script=options.coreSource.replaceAll('export ','')+'\nconst E=escapeHTML,N=number;\n'+options.uiSource.replace(/^import[^\n]+\n/,'').replaceAll('export ','')+'\nconst config=JSON.parse(document.getElementById("visual-data").textContent);mountVisual(document.getElementById("visual-root"),{...config,coreSource:null,uiSource:null});';
 return `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C2C 图形研究报告</title><style>${options.styles||''}</style><body><main class="offline-report"><h1>C2C 图形与回放报告</h1><p>离线只读 · MEMPHIS_ENGINEERING_NOT_APPROVED · 不发起远程任务或编辑原方案</p><div id="visual-root"></div></main><script id="visual-data" type="application/json">${JSON.stringify(payload).replaceAll('<','\\u003c')}</script><script type="module">${script.replaceAll('</script','<\\/script')}</script></body></html>`;
}

// One shared cursor drives the diagram, inspector, curves and event list.
// No interpolation of physical states; dots only express recorded flow direction.
export function mountVisual(host,options){
 const {design,history,switching,onCheck,onEdit,onTopology}=options;
 const verifiedResult=matchingDynamic(options.result,options.designHash);
 const s={dataset:'design',caseID:'SR_STUCK',cduCase:'T2_COLD_STANDBY',level:'system',unit:1,cdu:'A',selected:'tank-A',t:0,layer:'physical',future:false,display:'temperature',rate:1,playing:false,zoom:1,panX:0,panY:0,...options.session};
 let single=options.single.cases?.[s.caseID]||options.single;
 let sampleCache={};
 s.playing=false;
 let destroyed=false,raf=0,last=0,elapsed=0,panning=null,selectionLayer=null,renderScene=null;
 const flowOffsets=new Map();
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),q=sel=>host.querySelector(sel);
 const data=()=>s.dataset==='single'?single:s.dataset==='ab'?history:s.dataset==='source'?switching?.source:s.dataset==='cdu'?switching?.cdu_cases?.[s.cduCase]:s.dataset==='current'?verifiedResult:null;
 const duration=()=>s.dataset==='single'?single.series.at(-1).time_ns/1e9:data()?.frames?.at(-1)?.t_s||0;
 const stepSeconds=()=>['single','source','cdu'].includes(s.dataset)?.1:1;
 function frame(){return s.dataset==='single'?singleFrame(single,s.t,s.layer):atTime(data()?.frames||[],s.t);}
 function scene(){
  if(s.dataset==='single')return singleScene(single,s.t,s.layer);
  if(s.dataset==='current'&&verifiedResult)return resultScene(verifiedResult,s.t);
  if(s.dataset==='source'&&data())return s.level==='tanks'?tankScene(data(),frame()):sourceSwitchScene(data(),s.t);
  if(s.dataset==='cdu'&&data())return cduSwitchScene(data(),s.t,s.level==='six'?s.unit:null);
  const f=s.dataset==='ab'?frame():null;
  if(s.level==='tanks')return tankScene(data(),f);
  if(s.level==='cdu')return cduScene(design,`U${s.unit}-CDU-${s.cdu}`);
  if(s.level==='six')return sixScene(design,s.unit,f?{rack_inlet_c:f.rack_inlet_c?.slice((s.unit-1)*6,s.unit*6)}:null);
  return systemScene(design,f);
 }
 function stop(){s.playing=false;q('#v-play').textContent='播放';}
 function chooseDataset(value){stop();s.dataset=value;s.t=0;s.zoom=1;s.panX=s.panY=0;selectionLayer=null;flowOffsets.clear();
  s.level=value==='ab'?'tanks':'system';s.layer='physical';s.selected=value==='single'?'pump':value==='cdu'?'U1-CDU-A':'tank-A';shell();}
 function events(){
  if(s.dataset==='single')return visibleEvents(singleEvents(single),s.t,{future:s.future,layer:s.layer});
  return visibleEvents((data()?.events||[]).map(e=>({t_s:e.t_s,label:e.label||e.reason||e.event||`${e.from} → ${e.to}`,kind:'record'})),s.t,{future:s.future});
 }
 function identity(){
  if(s.dataset==='design')return '当前方案 · 静态功能图 · 无动态结果';
  if(s.dataset==='current')return verifiedResult?'当前输入身份匹配 · 远程研究结果':'当前版本无核验结果，未播放历史曲线';
  return `历史 ${data()?.run} / ${s.dataset==='single'?s.caseID:data()?.case} · 非当前方案${s.dataset==='cdu'?' · 仅U1动态；U2/U3无记录':''}`;
 }
 function shell(){
  host.innerHTML=`<section class="visual-workbench"><div class="visual-toolbar"><label>数据来源<select id="v-dataset"><option value="design">当前 00/01 研究方案 · 静态</option><option value="single">历史单柜 · 液体流动与卡泵</option><option value="ab">历史 A/B 罐 · 分层与冷库存</option><option value="current">当前版本 · 新动态结果</option></select></label><label>查看层级<select id="v-level" ${['single','current'].includes(s.dataset)?'disabled':''}><option value="system">系统总览</option><option value="six">六柜单元</option><option value="cdu">CDU 功能端口</option><option value="tanks">A/B 分层</option></select></label><label>单元<select id="v-unit" ${s.dataset!=='design'?'disabled':''}><option value="1">U1</option><option value="2">U2</option><option value="3">U3</option></select></label><label>显示<select id="v-display"><option value="temperature">节点温度</option><option value="flow">流量</option><option value="pressure">压差</option></select></label><button id="v-export">导出此图与回放</button></div>
   <div class="visual-origin" id="v-origin"></div><div id="v-presets" class="scenario-strip"></div><div class="visual-grid"><div class="visual-main"><div class="canvas-tools"><div><span id="v-breadcrumb"></span></div><div class="zoom-controls"><button id="v-up" aria-label="返回系统总览">上一级</button><button id="v-minus" aria-label="缩小">−</button><button id="v-fit">适合画布</button><button id="v-plus" aria-label="放大">＋</button></div></div><div id="v-stage" class="visual-stage" tabindex="0" aria-label="系统画布。方向键平移，Home复位，点击设备查看，双击下钻"><div id="v-scene"></div><canvas id="v-liquid" aria-hidden="true"></canvas></div><div class="canvas-legend"><span><i class="temp-key"></i>节点35–55°C</span><span>→ 已知流向</span><span>┄ 功能关联 / 未知流量</span><span>圆点速度仅表示相对流量，不是液团或输送时间</span></div><p id="v-scope" class="canvas-scope"></p></div><aside id="v-inspector" class="visual-inspector"></aside></div>
   <div class="replay-bar"><button id="v-play" class="primary">播放</button><button id="v-step" aria-label="前进一个保存帧">逐帧 ›</button><output id="v-clock">0.0 s</output><label class="time-control"><span class="sr-only">共同时间游标</span><input id="v-time" type="range" min="0" max="${duration()}" step="${s.dataset==='single'?'.1':'1'}" value="${s.t}"></label><label>速度<select id="v-rate"><option value="0.5">0.5×</option><option value="1">1×</option><option value="4">4×</option><option value="10">10×</option></select></label><label>记录<select id="v-layer" ${s.dataset!=='single'?'disabled':''}><option value="physical">模型真值</option><option value="arrived">已到达观测</option></select></label><label class="check-label"><input id="v-future" type="checkbox" ${s.future?'checked':''}>全时段事后分析</label></div>
   <div class="visual-lower"><section class="visual-curves"><div class="lower-heading"><h2>同步曲线</h2><span id="v-curve-mode"></span></div><div id="v-curves"></div></section><section class="visual-events"><h2>事件与原因</h2><div id="v-events"></div></section></div><p id="v-message" role="status" class="tagline"></p></section>`;
  if(switching)q('#v-dataset').insertAdjacentHTML('beforeend','<option value="source">历史冷源切换 · W1/W2与A/B罐</option><option value="cdu">6台CDU · 主备切换记录</option>');
  for(const [id,value]of Object.entries({'v-dataset':s.dataset,'v-level':s.level,'v-unit':String(s.unit),'v-display':s.display,'v-rate':String(s.rate),'v-layer':s.layer}))q('#'+id).value=value;
  q('#v-time').step=String(stepSeconds());q('#v-unit').disabled=!['design','cdu'].includes(s.dataset);
  if(['source','cdu'].includes(s.dataset))q('#v-level').querySelectorAll('option').forEach(o=>o.disabled=!(s.dataset==='source'?['system','tanks']:['system','six']).includes(o.value));
  q('.canvas-legend span:last-child').textContent='流带速度仅表达相对流量，不是液团或输送时间';
  if(s.dataset==='ab')q('#v-level').querySelectorAll('option').forEach(o=>o.disabled=['six','cdu'].includes(o.value));
  if(s.dataset==='single'){
   q('#v-presets').innerHTML='<span>已保存场景</span>'+Object.entries(options.single.cases||{}).map(([id,d])=>`<button data-case="${id}" aria-pressed="${id===s.caseID}">${E(d.label)}</button>`).join('')+'<small>保持同一游标，比较不同试验；不是即时故障注入。</small>';
   q('#v-presets').querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{stop();s.caseID=b.dataset.case;single=options.single.cases[s.caseID];sampleCache={};flowOffsets.clear();s.t=Math.min(s.t,duration());shell();});
  }else if(s.dataset==='cdu'){
   q('#v-presets').innerHTML='<span>历史R12 · U1试验</span>'+Object.entries(switching.cdu_cases).map(([id,d])=>`<button data-cdu-case="${id}" aria-pressed="${id===s.cduCase}">${E(d.label)}</button>`).join('');
   q('#v-presets').querySelectorAll('[data-cdu-case]').forEach(b=>b.onclick=()=>{stop();s.cduCase=b.dataset.cduCase;s.t=Math.min(s.t,duration());flowOffsets.clear();shell();});
  }else if(s.dataset==='source'){
   q('#v-presets').innerHTML='<span>实际切换关键点</span><button data-switch-time="0.1">切换前</button>'+data().events.filter(e=>e.kind==='physical').map(e=>`<button data-switch-time="${e.t_s}">${N(e.t_s)}s · ${E(e.label)}</button>`).join('');
   q('#v-presets').querySelectorAll('[data-switch-time]').forEach(b=>b.onclick=()=>{stop();s.t=Number(b.dataset.switchTime);update();});
  }else q('#v-presets').hidden=true;
  q('#v-dataset').onchange=e=>chooseDataset(e.target.value);
  q('#v-level').onchange=e=>{s.level=e.target.value;s.zoom=1;s.panX=s.panY=0;update();};
  q('#v-unit').onchange=e=>{s.unit=Number(e.target.value);if(s.dataset==='cdu'){s.level='six';s.selected=`U${s.unit}-CDU-A`;q('#v-level').value='six';}update();};
  q('#v-display').onchange=e=>{s.display=e.target.value;update();};
  q('#v-layer').onchange=e=>{s.layer=e.target.value;stop();update();};
  q('#v-rate').onchange=e=>s.rate=Number(e.target.value);
  q('#v-future').onchange=e=>{s.future=e.target.checked;update();};
  q('#v-time').oninput=e=>{stop();s.t=Number(e.target.value);update();};
  q('#v-step').onclick=()=>{stop();s.t=Math.min(duration(),Number((s.t+stepSeconds()).toFixed(1)));update();};
  q('#v-play').onclick=()=>{if(s.playing)stop();else if(duration()){if(s.t>=duration())s.t=0;s.playing=true;q('#v-play').textContent='暂停';last=0;update();}};
  q('#v-plus').onclick=()=>zoom(1.25);q('#v-minus').onclick=()=>zoom(.8);q('#v-fit').onclick=fit;
  q('#v-up').onclick=()=>{s.level=s.level==='cdu'?'six':'system';s.selected='';s.zoom=1;s.panX=s.panY=0;update();q('#v-level').value=s.level;};
  q('#v-export').onclick=exportReplay;
  const stage=q('#v-stage');
  stage.onkeydown=e=>{if(e.target!==stage)return;const delta={ArrowLeft:[-24,0],ArrowRight:[24,0],ArrowUp:[0,-24],ArrowDown:[0,24]}[e.key];if(delta){e.preventDefault();s.panX+=delta[0];s.panY+=delta[1];transform();}if(e.key==='Home'){e.preventDefault();fit();}};
  stage.onpointerdown=e=>{if(e.target.closest('[data-entity]'))return;panning={x:e.clientX,y:e.clientY,px:s.panX,py:s.panY};stage.setPointerCapture(e.pointerId);};
  stage.onpointermove=e=>{if(!panning)return;s.panX=panning.px+e.clientX-panning.x;s.panY=panning.py+e.clientY-panning.y;transform();};
  stage.onpointerup=()=>panning=null;stage.onpointercancel=()=>panning=null;
  stage.onwheel=e=>{if(!e.ctrlKey)return;e.preventDefault();zoom(e.deltaY>0?.9:1.1);};
  q('#v-play').disabled=q('#v-step').disabled=q('#v-time').disabled=!duration();
  update();
 }
 function fit(){s.zoom=1;s.panX=s.panY=0;transform();}
 function zoom(factor){s.zoom=Math.max(.65,Math.min(3,s.zoom*factor));transform();}
 function transform(){const target=q('#v-scene');if(target)target.style.transform=`translate(${s.panX}px, ${s.panY}px) scale(${s.zoom})`;}
 function pick(id,layer=null){
  s.selected=id;selectionLayer=layer;
  // Keep the hit target alive: replacing SVG here loses keyboard focus and
  // prevents the browser's second click from becoming a native double click.
  q('#v-scene').querySelectorAll('[data-entity]').forEach(el=>el.classList.toggle('picked',el.dataset.entity===id));
  q('#v-scene').querySelectorAll('[data-layer]').forEach(el=>el.classList.toggle('current-layer',el.closest('[data-entity]').dataset.entity===id&&Number(el.dataset.layer)===layer));
  q('#v-scene').querySelectorAll('[data-layer-index]').forEach(el=>el.classList.toggle('selected-temperature',el.closest('[data-entity]').dataset.entity===id&&Number(el.dataset.layerIndex)===layer));
  inspect(scene(),frame(),s.dataset==='design'?(options.issues||[]):[]);curves();
 }
 function drill(id){
  if(s.dataset==='cdu'){const m=id.match(/^U([123])/);if(m){s.unit=Number(m[1]);s.level='six';s.selected=id;s.zoom=1;s.panX=s.panY=0;q('#v-level').value='six';q('#v-unit').value=String(s.unit);update();}return;}
  if(s.dataset==='source'&&id.startsWith('tank-')){s.level='tanks';s.selected=id;q('#v-level').value='tanks';update();return;}
  if(s.dataset!=='design'&&s.dataset!=='ab')return;
  if(s.dataset==='ab'&&!id.startsWith('tank-'))return;
  if(id.startsWith('tank-'))s.level='tanks';
  else if(/^U[123]$/.test(id)){s.unit=Number(id.slice(1));s.level='six';}
  else if(/^U[123]-CDU-[AB]$/.test(id)){s.unit=Number(id[1]);s.cdu=id.at(-1);s.level='cdu';}
  else return;
  s.selected=id;s.zoom=1;s.panX=s.panY=0;q('#v-level').value=s.level;update();
 }
 function update(){
  const sc=scene(),f=frame(),issues=s.dataset==='design'?(options.issues||[]):[];
  renderScene=sc;
  if(!sc.nodes.some(n=>n.id===s.selected)&&!sc.edges.some(e=>e.id===s.selected))s.selected=sc.edges.find(e=>e.label==='pump')?.id||sc.nodes[0]?.id||'';
  q('#v-origin').textContent=identity();q('#v-origin').dataset.mode=s.dataset;
  q('#v-breadcrumb').textContent=sc.title;q('#v-scope').textContent=[sc.scope,...sc.notes].join(' ');
  q('#v-clock').textContent=N(s.t)+' s';q('#v-time').value=s.t;
  q('#v-scene').innerHTML=sceneSVG(sc,{selected:s.selected,selectedLayer:selectionLayer,issues,display:s.display});transform();
  q('#v-scene').querySelectorAll('[data-entity]').forEach(el=>{
   el.onclick=e=>{const l=e.target.closest('[data-layer],[data-layer-index]');pick(el.dataset.entity,l?Number(l.dataset.layer??l.dataset.layerIndex):null);};
   el.ondblclick=()=>drill(el.dataset.entity);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(el.dataset.entity);}if(e.key==='ArrowRight')drill(el.dataset.entity);};
  });
  inspect(sc,f,issues);curves();eventList();
  q('#v-curve-mode').textContent=s.future?'全时段事后分析':'未来隐藏 · 只显示游标前记录';
  if(s.dataset==='current'&&!verifiedResult)q('#v-scope').textContent='当前版本没有输入身份匹配的动态结果，图中无活动流路。修改参数只更新静态计算，不能缩放旧曲线。';
 }
 function inspect(sc,f,issues){
  const n=sc.nodes.find(n=>n.id===s.selected),edge=sc.edges.find(e=>e.id===s.selected),entity=n||edge;
  const rows=n?[...(n.metrics||[])]:edge?[metricRow('起点',edge.from),metricRow('终点',edge.to),metricRow('实际流量',edge.relation?null:edge.q,'m³/h'),metricRow('登记阀态',edge.active===undefined?'未记录':edge.active===null?'未知':edge.active?'开':'关')]:[];
  if(n?.layers){rows.push(metricRow('层数',n.layers.length),metricRow('参考显热',referenceEnergy(n.layers,data()),'MJ'));
   if(selectionLayer!==null)rows.push(metricRow(`底部第${selectionLayer+1}层`,n.layers[selectionLayer],'°C'));}
  const relevant=issues.filter(i=>i.edgeIds?.some(id=>id===s.selected||id.includes(s.selected))||i.id?.includes(s.selected));
  const params=s.dataset==='design'?(s.selected.startsWith('tank')?['tank_volume','cold_fraction','cold_c']:s.selected.includes('pump')?['pump_h0','pump_k','pump_speed']:s.selected.includes('CDU')?['ua','primary_c','secondary_target']:[]):[];
  const labels={tank_volume:'储罐容积',cold_fraction:'研究有效冷液比例',cold_c:'研究初始冷温',pump_h0:'泵关死压升',pump_k:'研究泵曲线K',pump_speed:'研究转速',ua:'CDU UA',primary_c:'一次边界温度',secondary_target:'二次目标温度'};
  q('#v-inspector').innerHTML=`<div class="overline">${s.dataset==='design'?'DESIGN CONTEXT':'RECORDED STATE'}</div><h2>${E(n?.label||edge?.label||edge?.id||'选择一个设备')}</h2><p class="tagline">${entity?'单击查看；双击设备下钻。':'从图中选择设备或管路，查看来源与缺失项。'}</p><dl>${rows.map(r=>`<div><dt>${E(r.label)}</dt><dd>${E(typeof r.value==='string'?r.value:N(r.value))} ${E(r.unit||'')}</dd></div>`).join('')}</dl>
   ${s.dataset==='single'?`<div class="control-chain"><h3>当前控制链</h3><p title="${E(f.pre)}">PRE：${E(stateLabel(f.pre))}</p><p title="${E(f.safety)}">Safety：${E(stateLabel(f.safety))}</p><p>POST锁存：${f.latched===null?'尚无事务':f.latched?'已锁存':'未锁存'}</p><p class="tagline">${E(f.quality)} · 记录 ${N(f.record_s)} s${s.layer==='arrived'?` · 到达 ${N(f.arrival_s)} s · 年龄 ${N(f.age_s)} s`:''}</p></div>`:''}
   ${s.dataset==='source'?`<div class="control-chain"><h3>命令与实际路径</h3><p>命令：${E(f?.command?.path)} / 源罐${E(f?.command?.source_tank)} / 负荷罐${E(f?.command?.load_tank)}</p><p>实际：${E(f?.source_path)} / 源罐${E(f?.source_tank)} / 负荷罐${E(f?.load_tank)}</p><p>命令时刻 ${N(f?.command?.issued_s)} s；物理记录 ${N(f?.t_s)} s</p><p class="tagline">源侧状态：${E(f?.source_state)}。RUN不代替实际冷水到达。</p></div>`:''}
   ${s.dataset==='cdu'?`<div class="control-chain"><h3>历史试验覆盖</h3><p>本时间轴只属于 U1：${E(f?.state||'尚无保存记录')}</p><p>U1实际压力主站：${E(f?.master||'未授予')}</p><p class="notice">U2/U3未动态验证。冷塔与A/B分层罐未纳入此R12试验，不与冷源回放拼接。</p>${s.future||s.t>=duration()?`<p>U1原结果：水力 ${E(data().summary.hydraulic_verdict)}；温度 ${E(data().summary.thermal_verdict)}；接管 ${E(data().summary.takeover_verdict)}；HX入口跨侧压力 ${E(data().summary.hx_pressure_verdict)}。不是整体工程通过。</p>`:''}</div>`:''}
   ${params.length?`<div class="visual-edit"><h3>修改研究方案</h3>${params.map(k=>`<label>${E(labels[k])} · ${E(design.parameters[k].unit)}<input type="number" step="any" data-visual-param="${k}" value="${design.parameters[k].value??''}" placeholder="未知，不补零" ${onEdit?'':'disabled'}></label>`).join('')}<p class="tagline">静态检查即时更新；动态结果需远程重算。</p></div>`:''}
   ${s.dataset==='design'?`<button id="v-check">查看相关工程检查</button>${s.level==='cdu'?'<button id="v-topology">编辑端口连接</button>':''}<h3 class="inspector-subhead">连接问题 ${issues.length}</h3>${(relevant.length?relevant:issues).map(i=>`<button class="visual-issue" data-visual-issue="${E(i.id)}">${E(i.title)}</button>`).join('')||'<p class="tagline">约简模板未检出冲突，不等于完整工程通过。</p>'}`:''}
   ${s.dataset==='ab'?`<p class="notice">${s.future||s.t>=duration()?`历史最高入口 ${N(history.summary.maximum_inlet_c)}°C。${E(history.summary.temperature_observation)} 保留，非当前设计结论。`:'完整场景结论保留在原报告。勾选事后分析可查看终局，不提前展示后续最高温度。'}</p>`:''}
   ${n?.layers?.length?`<div class="layer-values"><h3>逐层温度 · °C</h3><p class="tagline">顶部 → 底部；层号从底部起算。图上保留两位小数，不代表测量精度或已标定。</p>${selectionLayer!==null?`<p id="v-layer-raw" class="tagline">第 ${selectionLayer+1} 层原始记录：${E(n.layers[selectionLayer])} °C</p>`:''}<div class="layer-list">${n.layers.map((v,i)=>({v,i})).reverse().map(({v,i})=>`<button data-layer-pick="${i}" aria-pressed="${selectionLayer===i}"><span>第 ${i+1} 层</span><b>${Number.isFinite(v)?v.toFixed(3):'未知'} °C</b></button>`).join('')}</div></div>`:''}
   <details><summary>记录、来源与适用边界</summary><p>${E(sc.scope)}</p><p>缺少通道显示未知，不以命令或状态机 RUN 代替实际建流。节点温度不表示管内温度分布。</p><pre>${E(JSON.stringify({dataset:s.dataset,run:data()?.run,source:data()?.source||data()?.raw_sha256,bindings:data()?.bindings,record_s:f?.record_s??f?.t_s,model:data()?.model,design_sha256:data()?.design_sha256,entity:s.selected},null,2))}</pre></details>`;
  q('#v-inspector').querySelectorAll('[data-layer-pick]').forEach(b=>b.onclick=()=>pick(s.selected,Number(b.dataset.layerPick)));
  q('#v-inspector').querySelectorAll('[data-visual-param]').forEach(input=>input.onchange=()=>{stop();onEdit?.(input.dataset.visualParam,input.value===''?null:Number(input.value));});
  q('#v-check')?.addEventListener('click',()=>onCheck?.(s.selected.startsWith('tank')?'tank90':s.selected.includes('pump')?'pump_point':'ua'));
  q('#v-topology')?.addEventListener('click',()=>onTopology?.());
  q('#v-inspector').querySelectorAll('[data-visual-issue]').forEach(b=>b.onclick=()=>{const issue=issues.find(i=>i.id===b.dataset.visualIssue);s.selected=issue.edgeIds?.[0]||'';const edge=design.topology.edges.find(e=>e.id===s.selected);if(edge?.circuit){s.level='cdu';s.unit=Number(edge.circuit[1]);s.cdu=edge.circuit.at(-1);q('#v-level').value='cdu';}update();q('#v-message').textContent=issue.why;});
 }
 function metricRow(label,value,unit=''){return {label,value,unit};}
 function curves(){
  let samples,channels,threshold=null;
  const blue='oklch(.48 .10 220)',orange='oklch(.55 .12 55)',grey='oklch(.5 .02 245)',purple='oklch(.48 .12 310)';
  const c=(label,get,color)=>({label,get,color});
  if(s.dataset==='single'){
   const raw=s.layer==='physical'?single.series:single.measurements;
   samples=sampleCache[s.layer]||=raw.map(r=>{const t=(s.layer==='physical'?r.time_ns:r.available_ns)/1e9;return singleFrame(single,t,s.layer);});
   channels=s.selected==='pump'?[c('实际/观测转速 %',r=>r.actual_speed,blue),c('模拟PLC命令 %',r=>r.command,orange),c('控制请求 %',r=>r.request,purple)]:[c('入口 °C',r=>r.supply,blue),c('机柜出口 °C',r=>r.rack_return,orange),c('混合回液 °C',r=>r.mixed_return,grey)];
   threshold=s.selected==='pump'?null:45;
   q('#v-curves').innerHTML=curveSVG(samples,channels,s.t,{future:s.future,threshold})+curveSVG(samples,[c('回路实际流量 m³/h',r=>r.flow,blue),],s.t,{future:s.future});
  }else if(s.dataset==='source'){
   samples=data().frames;
   q('#v-curves').innerHTML=curveSVG(samples,[c('源侧实际流量 m³/h',r=>r.source_q,blue),c('负荷侧实际流量 m³/h',r=>r.load_q,orange)],s.t,{future:s.future})+curveSVG(samples,[c('一次入口 °C',r=>r.primary_c,blue),c('机柜最高入口 °C',r=>r.rack_max_c,orange)],s.t,{future:s.future,threshold:45});
  }else if(s.dataset==='cdu'){
   const selectedUnit=Number(s.selected.match(/^U([123])/)?.[1]||s.unit);
   if(selectedUnit!==1)q('#v-curves').innerHTML='<p class="empty-channel">该单元没有动态记录。未复制U1曲线，也未生成示例流动。</p>';
   else{samples=data().frames;q('#v-curves').innerHTML=curveSVG(samples,[c('U1 CDU A实际二次流量 m³/h',r=>r.cdus.A.secondary_flow_m3_h,blue),c('U1 CDU B实际二次流量 m³/h',r=>r.cdus.B.secondary_flow_m3_h,orange)],s.t,{future:s.future})+curveSVG(samples,[c('U1 CDU A出口 °C',r=>r.cdus.A.supply_C,blue),c('U1 CDU B出口 °C',r=>r.cdus.B.supply_C,orange)],s.t,{future:s.future});}
  }else if(data()?.frames){
   samples=data().frames;const f=samples[0];
   channels=Array.isArray(f.A)?[c('A罐阈值冷液体积 m³',r=>r.cold_A_m3,blue),c('B罐阈值冷液体积 m³',r=>r.cold_B_m3,orange)]:[c('机柜最高入口 °C',r=>r.rack_inlet_c?.length?Math.max(...r.rack_inlet_c):r.outlet_c,blue)];
   q('#v-curves').innerHTML=curveSVG(samples,channels,s.t,{future:s.future})+curveSVG(samples,[c(s.dataset==='ab'?'历史机柜最高入口 °C':'CDU实际换热 kW',r=>s.dataset==='ab'?Math.max(...r.rack_inlet_c):r.hx_kw,grey)],s.t,{future:s.future,threshold:s.dataset==='ab'?45:null});
  }else q('#v-curves').innerHTML='<div class="empty-channel">当前图是静态设计。<button id="v-try-single">查看历史单柜流动回放</button><p>修改参数会更新工程检查；没有当前动态证据时不生成曲线。</p></div>';
  q('#v-try-single')?.addEventListener('click',()=>chooseDataset('single'));
  q('#v-curves').querySelectorAll('.live-curve').forEach(el=>el.onclick=e=>{stop();const rect=el.getBoundingClientRect();const fraction=Math.max(0,Math.min(1,((e.clientX-rect.left)/rect.width*800-46)/710));s.t=Math.round(fraction*Number(el.dataset.maxTime)*10)/10;update();});
 }
 function eventList(){q('#v-events').innerHTML=events().map(e=>`<button data-v-event="${e.t_s}" class="event-item"><time>${N(e.t_s)} s</time><span>${E(e.label)}</span></button>`).join('')||'<p class="tagline">当前尚无可见事件。未来隐藏时，不提前展示后续故障确认。</p>';
  q('#v-events').querySelectorAll('[data-v-event]').forEach(b=>b.onclick=()=>{stop();s.t=Number(b.dataset.vEvent);update();});}
 function canvasDraw(dt){
  const canvas=q('#v-liquid'),svg=q('.system-svg'),stage=q('#v-stage');if(!canvas||!svg)return;
  const rect=stage.getBoundingClientRect(),ratio=Math.min(2,devicePixelRatio||1);if(canvas.width!==Math.round(rect.width*ratio)||canvas.height!==Math.round(rect.height*ratio)){canvas.width=Math.round(rect.width*ratio);canvas.height=Math.round(rect.height*ratio);}
  const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,rect.width,rect.height);
  const sc=renderScene;if(!sc)return;
  const box=svg.getBoundingClientRect(),scale=Math.min(box.width/sc.width,box.height/sc.height),ox=box.left-rect.left+(box.width-sc.width*scale)/2,oy=box.top-rect.top+(box.height-sc.height*scale)/2;
  for(const edge of sc.edges){const qValue=edge.relation?null:edge.q,options={playing:s.playing,reduced:reduced.matches},f=flowMark(qValue,options);
   const offset=advanceFlowOffset(flowOffsets.get(edge.id)||0,qValue,dt,options);flowOffsets.set(edge.id,offset);
   if(!f.direction)continue;
   for(const p of flowGlyphs(edge.points,offset)){
    ctx.save();ctx.translate(ox+p.x*scale,oy+p.y*scale);ctx.rotate(p.angle+(f.direction<0?Math.PI:0));ctx.scale(scale,scale);
    ctx.strokeStyle='oklch(.44 .10 220)';ctx.lineCap='round';ctx.lineJoin='round';
    ctx.globalAlpha=.18;ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(-15,0);ctx.lineTo(0,0);ctx.stroke();
    ctx.globalAlpha=.92;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-11,0);ctx.lineTo(-1,0);ctx.stroke();
    ctx.lineWidth=1.8;ctx.beginPath();ctx.moveTo(-3,-4);ctx.lineTo(2,0);ctx.lineTo(-3,4);ctx.stroke();ctx.restore();
   }
  }
 }
 function animate(now){if(destroyed)return;const dt=last?Math.min(.1,(now-last)/1000):0;last=now;
  if(s.playing){elapsed+=dt*s.rate;const step=stepSeconds();if(elapsed>=step){const jump=Math.floor(elapsed/step)*step;elapsed-=jump;s.t=Math.min(duration(),Number((s.t+jump).toFixed(1)));if(s.t>=duration())stop();update();}}
  canvasDraw(dt);raf=requestAnimationFrame(animate);
 }
 async function exportReplay(){
  if(!options.coreSource||!options.uiSource){q('#v-message').textContent='离线导出资料未完整加载，未生成不完整报告。';return;}
  const html=visualReportHTML(options,s);
  const a=document.createElement('a'),url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));a.href=url;a.download='c2c-visual-replay.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);q('#v-message').textContent='已导出当前视图、游标和嵌入式原始回放。离线报告不具备控制权限。';
 }
 shell();raf=requestAnimationFrame(animate);
 return {session:()=>({...s,playing:false}),destroy:()=>{destroyed=true;cancelAnimationFrame(raf);}};
}
