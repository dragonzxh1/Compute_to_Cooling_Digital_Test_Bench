// Display-only projection of saved keyframes. Never runs physical equations.
// Source execution HTML is retained unchanged in the official raw artifact.
const originalShow = show;
let manualFrame = null;
const diagramView=document.createElement('select');diagramView.id='diagram-view';diagramView.setAttribute('aria-label','图纸范围');
for(const [value,label] of [['A','A罐回路'],['B','B罐与RC'],['neutral','缓冲主环'],['secondary','CDU与二次侧'],['private','备用管私有预冷'],['all','完整功能图']])diagramView.add(new Option(label,value));
document.querySelector('section .controls').append(diagramView);
function activeCase(){return D[$('case').value];}
function pastFrame(){
  if(manualFrame!==null)return activeCase().keyframes[manualFrame];
  const a=activeCase(),r=a.curves[Math.min(+$('time').value,a.curves.length-1)];
  return a.keyframes.filter(f=>f.time_s<=r.time_s+1e-8).at(-1)||null;
}
function resetFrames(){
  $('frame').replaceChildren();activeCase().keyframes.forEach((f,i)=>$('frame').add(new Option(f.time_s+' s',i)));
}
pid=function(){
  const f=pastFrame();
  if(kind==='customer'){
    $('pid').innerHTML=CUSTOMER;
    $('pidnote').textContent='00/01文字功能重建；不含新增第三介质环或独立RC。不是正式施工图，也不代表所选研究案例按客户原拓扑运行。';return;
  }
  if(!f){$('pid').textContent='当前时间以前尚无详细P&ID快照；不以未来快照补齐。';$('pidnote').textContent='完整逐步轨迹保存在官方raw文件中。';return;}
  $('pid').innerHTML=DIAGS.at(-1); // identical structural netlist, values rebound below
  const edges=MODEL_NETLIST.edges;
  const extra=edges.filter(e=>e.path.startsWith('PRELOOP_'));
  if(extra.length){
    const root=$('pid').querySelector('svg'),ns='http://www.w3.org/2000/svg',height=root.viewBox.baseVal.height;
    root.viewBox.baseVal.height=height+240;
    for(let i=0;i<extra.length;i++){
      const e=extra[i],x=24+(i%3)*450,y=height+40+Math.floor(i/3)*110;
      const g=document.createElementNS(ns,'g');g.dataset.edgeId=e.id;
      const label=document.createElementNS(ns,'text');label.setAttribute('x',x);label.setAttribute('y',y);label.setAttribute('font-size','13');label.textContent=e.source_component+' → '+e.destination_component;g.append(label);
      const value=document.createElementNS(ns,'text');value.setAttribute('x',x);value.setAttribute('y',y+25);value.setAttribute('font-size','13');g.append(value);root.append(g);
    }
  }
  for(const e of edges){
    const g=$('pid').querySelector('[data-edge-id="'+e.id+'"]');if(!g)throw Error('MISSING_DRAWN_EDGE '+e.id);
    let q=null,temp=null;const p=e.path,n=p.endsWith('_A')?'A':'B';
    if(p.startsWith('TRANSFER_')){
      q=n===f.load_tank?f.transfer_m3_h:0;
      if(q>0)temp=e.source_component==='TANK_'+n?f.tanks[n].old_k[0]-273.15:e.destination_component==='TANK_'+n?f.tanks[n].return_k-273.15:null;
    }else if(p.startsWith('SOURCE_')){
      q=n===f.source_tank?f.source_m3_h:0;
      if(q>0)temp=e.source_component==='TANK_'+n?f.tanks[n].old_k.at(-1)-273.15:e.destination_component==='TANK_'+n?f.tanks[n].source_in_k-273.15:null;
    }else if(p==='RC_B'){q=f.recharge_m3_h;if(q>0&&e.source_component==='TANK_B')temp=f.tanks.B.old_k.at(-1)-273.15;}
    else if(p.startsWith('PRELOOP_')){
      const path=p.slice(8),online=path==='W2'?(f.source_path==='W2'&&f.source_m3_h>0):f.recharge_m3_h>0;
      q=online?0:MODEL_NETLIST.precool_flow_m3_h; // registered QH point; baseline CV witness in netlist, no guessed measurement
    }
    else if(p==='NEUTRAL')q=f.main_m3_h;
    else if(p.startsWith('CDU_PRIMARY_'))q=f.main_m3_h/3;
    const text=p.startsWith('PRELOOP_')?g.querySelectorAll('text')[1]:g.querySelector('text');text.textContent=q===null?'Q见原始单元轨迹':q.toFixed(3)+' m³/h'+(temp===null?'':' / '+temp.toFixed(3)+'°C');
    g.dataset.actualFlow=q===null?'unbound':String(q);g.dataset.caseId=$('case').value;g.dataset.snapshotTime=String(f.time_s);
  }
  $('pid').querySelector('svg title').textContent=$('case').value+' actual keyframe '+f.time_s+'s';
  const first=$('pid').querySelector('svg > text');if(first)first.textContent='当前源码功能级 P&ID · '+$('case').value+' · '+f.time_s+'s';
  $('pidnote').textContent='实际快照 '+f.time_s+'s；源路径 '+f.source_path+' / 源罐 '+f.source_tank+' / 负载转移罐 '+f.load_tank+'；源阀开度 '+f.valves.source+'，转移阀开度 '+f.valves.transfer+'。登记一次设计点330m³/h，每CDU110；实际Q见箭头。零流量用Q=0标识。重复节点为同一组件不同回路展开，非额外设备。';
  const root=$('pid').querySelector('svg'),paths=[...new Set(edges.filter(e=>!e.path.startsWith('PRELOOP_')).map(e=>e.path))];
  let chosen=[];const mode=diagramView.value;
  if(mode==='A')chosen=['TRANSFER_A','SOURCE_A'];
  else if(mode==='B')chosen=['TRANSFER_B','SOURCE_B','RC_B'];
  else if(mode==='neutral')chosen=['NEUTRAL'];
  else if(mode==='secondary')chosen=paths.filter(p=>p.startsWith('CDU_PRIMARY_')||p.startsWith('SECONDARY_'));
  if(chosen.length){const ii=chosen.map(p=>paths.indexOf(p));root.setAttribute('viewBox','0 '+(92+128*Math.min(...ii))+' 1460 '+(128*(Math.max(...ii)-Math.min(...ii)+1)));}
  else if(mode==='private')root.setAttribute('viewBox','0 '+(root.viewBox.baseVal.height-230)+' 1460 220');
};
show=function(){
  originalShow();const f=pastFrame();pid();
  if(!f){$('ports').textContent='当前时刻以前尚无详细接口快照；不使用未来数据。';return;}
  $('frame').value=String(activeCase().keyframes.indexOf(f));
  const rr=[];for(const n of ['A','B']){
    const t=f.tanks[n];rr.push({罐:n,实际快照_s:f.time_s,顶部热入_m3h:t.load_m3_s*3600,顶部热入_C:t.return_k-273.15,
      底部冷出_m3h:t.load_m3_s*3600,底部冷出_C:t.old_k[0]-273.15,顶部热出_m3h:t.source_m3_s*3600,
      顶部热出_C:t.old_k.at(-1)-273.15,底部冷入_m3h:t.source_m3_s*3600,底部冷入_C:t.source_in_k-273.15,
      来源:'物理真值；无流接口温度不代表真实流动',绝对压力:'NOT_VERIFIED'});
  }$('ports').innerHTML=table(rr);
};
$('case').onchange=()=>{manualFrame=null;resetFrames();$('time').max=activeCase().curves.length-1;$('time').value=$('time').max;show();};
$('time').oninput=()=>{manualFrame=null;show();};
$('frame').onchange=()=>{manualFrame=+$('frame').value;show();};
diagramView.onchange=pid;
$('case').value='BASELINE_EXACT';resetFrames();$('time').max=activeCase().curves.length-1;$('time').value=$('time').max;show();
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(show,100);});
