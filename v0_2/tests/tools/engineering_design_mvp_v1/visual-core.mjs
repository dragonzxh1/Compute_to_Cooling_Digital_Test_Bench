// Display adapters only. This module never advances a physical model.
export const escapeHTML=x=>String(x??'未知').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export const number=x=>Number.isFinite(x)?Number(x.toFixed(3)).toLocaleString('zh-CN'):'未知';
const known=x=>Number.isFinite(x),celsius=x=>known(x)?x-273.15:null;
export function stateLabel(code){return ({STEADY_TRACKING:'正常跟踪',TRACKING_PROGRESS:'响应跟踪中',HANDOFF_PENDING:'交接确认中',TRACKING_FAULT_SUSPECTED:'疑似跟踪故障',TRACKING_FAULT_CONFIRMED:'跟踪故障已确认',INSUFFICIENT_MEASUREMENT:'测量不足',NORMAL:'正常',FAULT:'故障保持',DEGRADED:'降级',PROTECTED:'保护',DERATE_REQUESTED:'请求降额',STUCK:'静默卡泵',MISSING:'测量丢失',PRIMARY_WARM:'一次边界升温'})[code]||code;}
export function atTime(rows,t,key='t_s'){
 let lo=0,hi=rows.length-1,found=-1;
 while(lo<=hi){const i=(lo+hi)>>1;if(rows[i][key]<=t+1e-9){found=i;lo=i+1;}else hi=i-1;}
 return found<0?null:rows[found];
}
export function flowMark(q,{playing=false,reduced=false,valid=true}={}){
 // Exact zero: the adapter has not registered a nonzero flow tolerance.
 if(!valid||!known(q))return {state:'unknown',direction:0,speed:0,label:'流量未知'};
 if(q===0)return {state:'zero',direction:0,speed:0,label:'零流量'};
 return {state:'known',direction:Math.sign(q),speed:playing&&!reduced?12+48*Math.abs(q)/(Math.abs(q)+20):0,label:`${number(q)} m³/h`};
}
export function advanceFlowOffset(offset,q,dt,options={}){
 const f=flowMark(q,options);
 if(!f.speed||!known(dt)||dt<=0)return offset;
 return ((offset+f.direction*f.speed*dt)%56+56)%56;
}
export function flowGlyphs(points,offset){
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
 const total=lengths.reduce((a,b)=>a+b,0),out=[];
 for(let pos=((offset%56)+56)%56;pos<total;pos+=56){let d=pos,i=0;while(i<lengths.length-1&&d>=lengths[i]){d-=lengths[i];i++;}
  if(!lengths[i])continue;const a=points[i],b=points[i+1],u=d/lengths[i];
  out.push({x:a[0]+(b[0]-a[0])*u,y:a[1]+(b[1]-a[1])*u,angle:Math.atan2(b[1]-a[1],b[0]-a[0])});
 }
 return out;
}
export function labelledLayers(temps){
 // Label every layer for the normal 20-layer replay. Dense 80/160 meshes
 // retain all bands and use sampled labels plus a complete inspector table.
 const step=Math.max(1,Math.ceil(temps.length/20));
 return temps.map((value,index)=>({value,index})).filter(r=>r.index%step===0||r.index===temps.length-1);
}
export function temperatureColor(t){
 if(!known(t))return 'oklch(.79 .009 80)';
 const f=Math.max(0,Math.min(1,(t-35)/20));
 return `oklch(${.74-f*.04} .11 ${230-f*185})`;
}
export function singleFrame(data,t,layer='physical'){
 const physical=atTime(data.series,t*1e9,'time_ns'),measurement=atTime(data.measurements,t*1e9,'available_ns'),phase=atTime(data.phases,t*1e9,'time_ns');
 const age=measurement?t-measurement.sample_ns/1e9:null;
 const valid=layer==='physical'?!!physical:!!measurement&&measurement.quality==='VALID'&&age<=data.input.sensor_max_age_ns/1e9;
 const r=valid?(layer==='physical'?physical:measurement):null;
 return {t_s:t,record_s:r?(layer==='physical'?r.time_ns:r.sample_ns)/1e9:null,arrival_s:measurement?.available_ns/1e9,
  quality:layer==='physical'?'MODEL_TRUTH':!measurement?'NOT_ARRIVED':!valid?'INVALID_OR_STALE':measurement.quality,
  age_s:age,flow:r? r.flow_m3_s*3600:null,dp:r?r.dp_pa/1000:null,supply:celsius(r?.supply_k),
  rack_return:celsius(r?.rack_return_k?.[0]),mixed_return:celsius(r?.return_k),
  actual_speed:r?(layer==='physical'?r.actual_speed:r.pump_speed)*100:null,command:phase?phase.PLC.command*100:null,
  request:phase?phase.controller_request*100:null,it_kw:layer==='physical'&&physical?physical.rack_it_w[0]/1000:null,
  pre:phase?.PRE.state??'尚无事务',safety:phase?.SAFETY.severity??'尚无事务',latched:phase?.POST.confirmed_latched??null,
  raw:r,phase,measurement,physical};
}
export function singleEvents(data){
 const events=[];let last='';
 for(const p of data.input.load_profile.slice(1))events.push({t_s:p.time_ns/1e9,label:'物理配置：负载阶跃',kind:'physical'});
 if(data.input.fault&&data.input.fault!=='NONE')events.push({t_s:data.input.fault_at_ns/1e9,label:'物理配置：'+stateLabel(data.input.fault),kind:'physical'});
 for(const p of data.phases){const key=`${p.PRE.state} / ${p.SAFETY.severity} / 锁存 ${p.POST.confirmed_latched}`;
  if(key!==last){events.push({t_s:p.time_ns/1e9,label:`${stateLabel(p.PRE.state)} / ${stateLabel(p.SAFETY.severity)} / ${p.POST.confirmed_latched?'已锁存':'未锁存'}`,raw:key,kind:'observed'});last=key;}}
 return events.sort((a,b)=>a.t_s-b.t_s);
}
export function visibleEvents(events,t,{future=false,layer='physical'}={}){
 return events.filter(e=>(future||e.t_s<=t+1e-9)&&(layer==='physical'||e.kind!=='physical'));
}
export function matchingDynamic(result,designHash){
 return result?.design_sha256===designHash&&/^[a-f0-9]{64}$/.test(designHash||'')?result:null;
}
const metric=(label,value,unit='')=>({label,value,unit});
const node=(id,label,type,x,y,extra={})=>({id,label,type,x,y,...extra});
const pipe=(id,from,to,points,q=null,extra={})=>({id,from,to,points,q,...extra});
export function singleScene(data,t,layer='physical'){
 const f=singleFrame(data,t,layer);
 return {id:'single',title:'单柜约简回路',scope:data.scope,width:1120,height:480,frame:f,
  notes:['按原 RackLoop 三个集中热容绘制，不代表设备实物顺序或施工布管。泵向串联回路施压，板换仅热耦合。','管路使用同一串联回路实际求解流量；节点着温度色，不虚构管内空间温度或输送延迟。'],
  nodes:[
   node('primary','一次侧登记初始边界','source',120,100,{temperature:celsius(data.input.primary_inlet_k),metrics:[metric('登记初始温度，非实时反馈',celsius(data.input.primary_inlet_k),'°C'),metric('给定流量',data.input.primary_flow_m3_s*3600,'m³/h')],boundary:true}),
   node('hx','换热器 / 供液容积','hx',300,240,{temperature:f.supply,valueLabel:'供液',metrics:[metric('供液温度',f.supply,'°C'),metric('UA 研究假设',data.input.hx_ua_w_k/1000,'kW/K')]}),
   node('pump','二次泵','pump',550,240,{speed:f.actual_speed,metrics:[metric('实际/观测转速',f.actual_speed,'%'),metric('模拟 PLC 命令',f.command,'%'),metric('控制请求',f.request,'%'),metric('回路流量',f.flow,'m³/h'),metric('泵压升',f.dp,'kPa')],fault:f.pre==='TRACKING_FAULT_CONFIRMED'}),
   node('rack','GB300 单柜','rack',850,240,{temperature:f.rack_return,valueLabel:'出口',metrics:[metric('入口',f.supply,'°C'),metric('机柜出口',f.rack_return,'°C'),metric('IT负载，仅物理记录',f.it_kw,'kW')],fault:known(f.supply)&&f.supply>45}),
   node('return','回液混合容积','junction',550,390,{temperature:f.mixed_return,metrics:[metric('混合温度',f.mixed_return,'°C')]})],
  edges:[pipe('supply','hx','pump',[[325,240],[526,240]],f.flow),pipe('rack-feed','pump','rack',[[574,240],[826,240]],f.flow),
   pipe('rack-return','rack','return',[[874,240],[1010,240],[1010,390],[569,390]],f.flow),
   pipe('return-hx','return','hx',[[531,390],[180,390],[180,240],[275,240]],f.flow),
   pipe('thermal','primary','hx',[[160,100],[300,100],[300,200]],null,{relation:true,label:'仅热耦合，无介质连接'})]};
}
export function systemScene(design,historyFrame=null){
 const historical=!!historyFrame,top=design.topology;
 const nodes=[node('dry','干冷源','source',110,110),node('wet','湿冷源','source',110,330),
  node('source-pumps','源侧泵组','pump',330,110,{metrics:historical?[metric('源侧总流量',historyFrame.source_flow_m3_h,'m³/h')]:[]}),
  node('tank-A','A 储罐','tank',530,110,{temperature:historyFrame?.A?.[0],annotation:historical?null:`设计 ${number(design.parameters.tank_volume.value)} m³`,metrics:historical?[metric('阈值冷液体积',historyFrame.cold_A_m3,'m³')]:[metric('设计容积',design.parameters.tank_volume.value,'m³')]}),
  node('tank-B','B 储罐','tank',530,330,{temperature:historyFrame?.B?.[0],annotation:historical?null:`设计 ${number(design.parameters.tank_volume.value)} m³`,metrics:historical?[metric('阈值冷液体积',historyFrame.cold_B_m3,'m³')]:[metric('设计容积',design.parameters.tank_volume.value,'m³')]}),
  node('load-pumps','负荷侧泵组','pump',750,110),
  ...[0,1,2].map(i=>node(`U${i+1}`,`单元 ${i+1} · 六柜`,'unit',970,100+i*150,{metrics:historical?[metric('该单元总流量',historyFrame.unit_flow_m3_h?.[i],'m³/h')]:[],unit:i+1}))];
 // These are functional associations, not asserted physical hydraulic edges.
 const edges=[pipe('dry-source','dry','source-pumps',[[150,110],[290,110]],null,{relation:true}),
  pipe('wet-source','wet','source-pumps',[[150,330],[230,330],[230,150],[330,150]],null,{relation:true}),
  pipe('source-A','source-pumps','tank-A',[[370,110],[490,110]],null,{relation:true}),
  pipe('source-B','source-pumps','tank-B',[[330,150],[330,330],[490,330]],null,{relation:true}),
  pipe('A-load','tank-A','load-pumps',[[570,110],[710,110]],null,{relation:true}),
  pipe('B-load','tank-B','load-pumps',[[570,330],[660,330],[660,150],[750,150]],null,{relation:true}),
  ...[0,1,2].map(i=>pipe(`load-U${i+1}`,'load-pumps',`U${i+1}`,[[790,110],[840,110],[840,100+i*150],[930,100+i*150]],null,{relation:true}))];
 return {id:historical?'historical-system':'system',title:historical?'旧 V2 设备分组与记录':'00/01 设备功能总览',width:1120,height:500,nodes,edges,
  scope:historical?'历史 V9 条件性替代研究，非当前00/01。分组图不复原未知的原始阀序。':top.description,
  notes:['虚线表示设备功能关联，不是已确认的供回液管路；缺少逐段连接与实际阀态时，不画活动流路。','一次A/B、CDU身份与二次环保持独立。可下钻六柜及CDU功能端口；完整72阀未展开。']};
}
export function sixScene(design,u=1,frame=null){
 const nodes=[node('primary-A','一次网 A','source',100,100),node('primary-B','一次网 B','source',100,330),
  node(`U${u}-CDU-A`,'CDU A','hx',380,100,{unit:u}),node(`U${u}-CDU-B`,'CDU B','hx',380,330,{unit:u}),
  ...Array.from({length:6},(_,i)=>node(`rack-${i+1}`,`机柜 ${i+1}`,'rack',670+(i%3)*170,120+Math.floor(i/3)*220,{
   temperature:frame?.rack_inlet_c?.[i],metrics:[metric('入口',frame?.rack_inlet_c?.[i],'°C'),metric('本柜实际流量',frame?.rack_flow_m3_h?.[i],'m³/h')]}))];
 const edges=[]; // Do not visually bind CDU B to primary B, even as a guessed route.
 // Do not invent which CDU secondary loop has been selected at each rack.
 return {id:'six',title:`单元 ${u} · 六柜与备用 CDU`,width:1120,height:490,nodes,edges,
  scope:'设备分组。CDU身份与一次A/B选网不绑定；未确认的选网及机柜四阀不补连线，有总流量不等于每柜已有流量证据。',
  notes:['点击 CDU 查看当前方案的实际功能端口连接。A/B供回选择阀未展开，不默认接通。','各柜未知流量独立标记。给定边界的短程研究不等于完整冷源或接管验证。']};
}
export function cduScene(design,id){
 const t=design.topology,c=t.circuits.find(c=>c.id===id)||t.circuits[0];
 if(!c)return {id:'cdu',title:'无登记 CDU 路径',scope:'导入方案未登记 circuits',width:1120,height:480,nodes:[],edges:[],notes:[]};
 const relevant=t.edges.filter(e=>e.circuit===c.id||[c.from,c.to].includes(e.from)||[c.from,c.to].includes(e.to));
 const ids=[...new Set([c.from,...relevant.flatMap(e=>[e.from,e.to]),c.to])];
 const positions=new Map(ids.map((id,i)=>[id,[90+i%4*310,160+Math.floor(i/4)*180]]));
 const nodes=ids.map(id=>{const [x,y]=positions.get(id);return node(id,id.split(':').at(-1),'port',x,y,{metrics:[metric('端口ID',id),metric('介质域',t.ports.find(p=>p.id===id)?.domain)]});});
 const edges=relevant.map(e=>{const a=positions.get(e.from),b=positions.get(e.to);return pipe(e.id,e.from,e.to,[a,[(a[0]+b[0])/2,Math.min(a[1],b[1])-45],b],null,{label:e.kind,active:e.active});});
 return {id:'cdu',title:`${c.id} · 功能端口`,width:1120,height:Math.max(420,220+Math.ceil(ids.length/4)*180),nodes,edges,
  scope:t.description,notes:['连线直接来自当前 JSON 端口与边。泵、过滤器、板换是边上的功能元件，阀态与实际流量分别处理。','此约简模板未展开二次泵100%备用、过滤器双支路和全部仪表。不能作为施工图。']};
}
export function tankScene(data,frame){
 const nodes=['A','B'].map((s,i)=>node(`tank-${s}`,`${s} 储罐`,'layers',290+i*490,300,{layers:frame?.[s],temperature:frame?.[s]?.[0],
  metrics:[metric('顶部',frame?.[s]?.at(-1),'°C'),metric('底部',frame?.[s]?.[0],'°C'),metric('阈值冷液体积',frame?.[`cold_${s}_m3`],'m³'),metric('温度阈值',data?.cold_threshold_c,'°C')]}));
 return {id:'tanks',title:'A/B 分层记录',scope:data?.scope||'当前版本没有逐层温度结果',width:1120,height:600,nodes,edges:[],
  notes:['固定35–55°C色标；底部第1层向上排列。颜色不是故障判定。','低于阈值的体积、参考显热和90秒出口表现分别评价；独立罐试验不是A/B系统切换。']};
}
export function resultScene(result,t){
 const f=atTime(result.frames,t);
 if(result.model==='tank90')return tankScene(result,f);
 // Accepted short-run RackLoop: one serial total and six explicitly solved branches.
 const scene={id:'short-six',title:'单六柜约简热水力回路',scope:result.scope,width:1120,height:500,notes:result.assumptions||[],
  nodes:[node('hx','换热器 / 供液容积','hx',170,220,{temperature:f?.rack_inlet_c?.[0],metrics:[metric('实际换热',f?.hx_kw,'kW')]}),
   node('pump','给定转速泵','pump',400,220,{metrics:[metric('总流量',f?.unit_flow_m3_h?.[0],'m³/h'),metric('压升',f?.dp_kpa?.[0],'kPa')]}),
   ...Array.from({length:6},(_,i)=>node(`rack-${i+1}`,`机柜 ${i+1}`,'rack',620+(i%3)*170,130+Math.floor(i/3)*220,{temperature:f?.rack_inlet_c?.[i],metrics:[metric('入口',f?.rack_inlet_c?.[i],'°C'),metric('流量',f?.rack_flow_m3_h?.[i],'m³/h')]}))],
  edges:[pipe('loop-total','hx','pump',[[210,220],[360,220]],f?.unit_flow_m3_h?.[0])],frame:f};
 for(let i=0;i<6;i++){const x=620+i%3*170,y=130+Math.floor(i/3)*220,q=f?.rack_flow_m3_h?.[i];scene.edges.push(pipe(`feed-${i}`,'pump',`rack-${i+1}`,[[440,220],[500,220],[500,y],[x-40,y]],q));}
 scene.notes=[...scene.notes,'支路供流来自逐柜求解值；回流集管在本约简画面折叠，不代表开放回路。一次冷源为边界，不画为完整设备动态。'];
 return scene;
}
export function sourceSwitchScene(data,t){
 const f=atTime(data.frames,t),paths=['W1','W2','D1','D2'];
 const nodes=paths.map((id,i)=>node(id,`${id.startsWith('W')?'湿冷源':'干冷源'} ${id}`,'source',100,80+i*130,{
  temperature:f?.source_path===id?f.source_outlet_c:null,statusLabel:!f?'未到达记录':f.available?.[id]===false?'不可用反馈':f.source_path===id?'实际选中':'未选中',
  operating:f?.source_path===id&&f.source_q>0,statusPosition:'side',compactLabel:true,fault:f?.available?.[id]===false,
  metrics:[metric('设备可用反馈',f?.available?.[id]===undefined?'未知':f.available[id]?'可用':'不可用'),metric('实际流量',f?(f.source_path===id?f.source_q:0):null,'m³/h'),metric('设备出口冷液',f?.source_path===id?f.source_outlet_c:null,'°C'),metric('输送回罐温度',f?.source_path===id?f.source_return_c:null,'°C')]}));
 nodes.push(node('source-pumps','源侧泵 / 供回阀组','pump',340,220,{speed:f?f.source_speed*100:null,operating:f?.source_q>0,
  metrics:[metric('实际流量',f?.source_q,'m³/h'),metric('实际供阀',f?.source_supply_valve),metric('实际回阀',f?.source_return_valve),metric('控制状态',f?.source_state||'尚无记录')]}));
 for(const [i,s]of ['A','B'].entries())nodes.push(node(`tank-${s}`,`${s} 储罐`,'tank',610,140+i*280,{temperature:f?.[s]?.[0],
  statusLabel:f?.source_tank===s&&f?.load_tank===s?'源侧 + 负荷侧选中':f?.source_tank===s?'源侧选中':f?.load_tank===s?'负荷侧选中':f?'非当前选罐':'无记录',
  metrics:[metric('底部温度',f?.[s]?.[0],'°C'),metric('顶部温度',f?.[s]?.at(-1),'°C'),metric('阈值冷库存',f?.[`cold_${s}_m3`],'m³')]}));
 nodes.push(node('load-pumps','负荷供回阀组','valve',840,280,{temperature:f?.primary_c,operating:f?.load_q>0,
  metrics:[metric('实际供流',f?.load_q,'m³/h'),metric('供阀实际开度',f?.load_supply_valve),metric('回阀实际开度',f?.load_return_valve),metric('实际选罐',f?.load_tank)]}),
  node('load','18柜负载侧','unit',1040,280,{temperature:f?.rack_max_c,valueLabel:'最高入口',metrics:[metric('最高机柜入口',f?.rack_max_c,'°C')],fault:Number.isFinite(f?.rack_max_c)&&f.rack_max_c>45}));
 const edges=paths.map((id,i)=>pipe(`source-${id}`,id,'source-pumps',[[140,80+i*130],[230,80+i*130],[230,220],[316,220]],f?(f.source_path===id?f.source_q:0):null));
 for(const [i,s]of ['A','B'].entries()){
  edges.push(pipe(`source-tank-${s}`,'source-pumps',`tank-${s}`,[[364,220],[460,220],[460,140+i*280],[583,140+i*280]],f?(f.source_tank===s?f.source_q:0):null));
  edges.push(pipe(`load-tank-${s}`,`tank-${s}`,'load-pumps',[[637,140+i*280],[730,140+i*280],[730,280],[815,280]],f?(f.load_tank===s?f.load_q:0):null));
 }
 edges.push(pipe('load-feed','load-pumps','load',[[865,280],[1006,280]],f?.load_q));
 return {id:'source-switch',title:'冷源切换与A/B储罐路径',width:1140,height:570,frame:f,nodes,edges,scope:data.scope,
  notes:['图中供回管成对折叠，箭头按原始实际流量显示；选中路径不等于已有流量。源侧选罐与负荷侧选罐独立。','W1/W2是历史模型的两台湿冷源，不把它们的名称当作客户00/01设备编号。回充支路未在此图展开。']};
}
export function cduPrimaryFlow(frame,side,network){
 const d=frame?.cdus?.[side];if(!d)return null;
 const prefix=`G01-C01${side}-P1-CV-`,v=frame.valves||{},s=v[prefix+network+'S'],r=v[prefix+network+'R'];
 if(s===0||r===0)return 0;
 const other=network==='A'?'B':'A';
 if(s>0&&r>0&&v[prefix+other+'S']===0&&v[prefix+other+'R']===0)return d.primary_flow_m3_h;
 return null; // Aggregate CDU flow cannot resolve simultaneously connected primary networks.
}
export function cduSwitchScene(data,t,unit=null){
 const f=atTime(data.frames,t),nodes=[node('primary-A','一次网 A（边界）','source',90,110),node('primary-B',unit&&unit!==1||!f?'一次网 B（阀态未知）':'一次网 B（U1隔离）','source',90,470)],edges=[];
 const units=unit?[unit]:[1,2,3];
 for(const u of units){
  const y=unit?250:100+(u-1)*190;
  for(const [i,side]of ['A','B'].entries()){
   const d=u===1?f?.cdus?.[side]:null,id=`U${u}-CDU-${side}`,x=unit?350:390+i*340,cy=unit?140+i*280:y;
   nodes.push(node(id,`U${u} · CDU ${side}`,'hx',x,cy,{temperature:d?.supply_C,
    statusLabel:!d?'未动态验证':f.master===side?(d.secondary_flow_m3_h>0?'当前压力主站':'主站仍登记 / 已失流'):d.secondary_flow_m3_h>0?'实际供流中':'当前未供流',
    operating:d?.secondary_flow_m3_h>0,
    metrics:[metric('设备ID',`G01-C0${u}${side}`),metric('一次流量',d?.primary_flow_m3_h,'m³/h'),metric('二次流量',d?.secondary_flow_m3_h,'m³/h'),metric('二次出口',d?.supply_C,'°C'),metric('实际换热',d?.heat_W===undefined?null:d.heat_W/1000,'kW'),metric('实际转速',d?.speed===undefined?null:d.speed*100,'%'),metric('二次压差',d?.secondary_dp_kPa,'kPa'),metric('HX入口跨侧表压差',d?.hx_inlet_gauge_difference_kPa,'kPa'),metric('实际供阀',u===1?f?.valves?.[`G01-C01${side}-P2-XV-SUP`]:null),metric('实际回阀',u===1?f?.valves?.[`G01-C01${side}-P2-XV-RET`]:null)]}));
   if(u===1)for(const [j,net]of ['A','B'].entries())edges.push(pipe(`P1-${side}-${net}`,`primary-${net}`,id,[[130,110+j*360],[200+j*25,110+j*360],[200+j*25,40+j*530],[x-60,40+j*530],[x-60,cy],[x-25,cy]],cduPrimaryFlow(f,side,net)));
   if(!unit)edges.push(pipe(`P2-U${u}-${side}`,id,`U${u}`,[[x+25,cy],[x+80,cy],[x+80,cy+(i?70:-70)],[990,cy+(i?70:-70)],[990,cy],[1026,cy]],d?.secondary_flow_m3_h,{relation:u!==1}));
  }
  if(!unit)nodes.push(node(`U${u}`,`U${u} · 六柜`,'unit',1060,y,{statusLabel:u===1?(f?f.state:'未到达记录'):'该单元无动态记录',metrics:[metric('单元实际流量',u===1?f?.unit_flow_m3_h:null,'m³/h')]}));
 }
 if(unit)for(let i=0;i<6;i++){
  const r=unit===1?f?.racks?.[String(i+1)]:null,x=620+(i%3)*190,y=130+Math.floor(i/3)*270,id=`rack-${i+1}`;
  nodes.push(node(id,`U${unit} · 机柜${i+1}`,'rack',x,y,{temperature:r?.supply_C,metrics:[metric('实际流量',r?.flow_m3_h,'m³/h'),metric('入口',r?.supply_C,'°C'),metric('回液',r?.return_C,'°C')]}));
  for(const [j,side]of ['A','B'].entries())edges.push(pipe(`rack-${side}-${i+1}`,`U${unit}-CDU-${side}`,id,[[375,140+j*280],[450+j*45,140+j*280],[450+j*45,y+(j?45:-45)],[x,y+(j?45:-45)],[x,y+(j?33:-33)]],r?.[side+'_supply_m3_h']));
 }
 return {id:'cdu-switch',title:unit?`U${unit} 六柜主备接管`:'6台CDU · 三个六柜单元',width:1140,height:610,nodes,edges,frame:unit&&unit!==1?null:f,scope:data.scope,
  notes:['仅U1有历史动态记录。U2/U3及其4台CDU不借用U1数据，未知状态不着运行色、不生成流动。','一次网、CDU身份和二次环独立；图上供回管与选择阀成对折叠。CDU B接管并不意味着一次B投入或B罐放冷。']};
}
function symbol(type){
 const forms={pump:'<circle r="24"/><path d="M-9-15 16 0-9 15Z M-32 0h8 M24 0h8 M-19 30h38"/>',hx:'<rect x="-25" y="-30" width="50" height="60" rx="5"/><path d="M-14-22v44 M0-22v44 M14-22v44"/>',
  rack:'<rect x="-24" y="-33" width="48" height="66" rx="4"/><path d="M-24-12h48 M-24 9h48 M-16-23h6 M-16-2h6 M-16 20h6"/>',
  filter:'<rect x="-24" y="-24" width="48" height="48" rx="3"/><path d="M-16 17 16-17 M-16 5 4-17 M-4 17 16-5"/>',
  valve:'<path d="M-25-18 25 18V-18L-25 18Z M0-18v-18 M-12-36h24"/>',
  source:'<path d="M-26 22-19-22h38l7 44Z M-16-12h32 M-20 12h40 M0-22v44"/>',tank:'<rect x="-27" y="-34" width="54" height="68" rx="16"/><path d="M-27-13h54 M-27 10h54"/>',
  unit:'<rect x="-34" y="-29" width="68" height="58" rx="5"/><path d="M-20-18v36 M0-18v36 M20-18v36"/>',junction:'<circle r="19"/><path d="M-12 0h24 M0-12v24"/>',port:'<circle r="7"/>'};
 return forms[type]||forms.junction;
}
export function sceneSVG(scene,{selected='',selectedLayer=null,issues=[],display='temperature'}={}){
 const E=escapeHTML,bad=new Set(issues.flatMap(i=>i.edgeIds||[]));
 let out=`<svg class="system-svg" viewBox="0 0 ${scene.width} ${scene.height}" aria-label="${E(scene.title)}"><title>${E(scene.title)}</title><g class="scene-content">`;
 for(const edge of scene.edges){const q=flowMark(edge.relation?null:edge.q),points=edge.points.map(p=>p.join(',')).join(' '),isBad=bad.has(edge.id);
  out+=`<g data-entity="${E(edge.id)}" tabindex="0" role="button" aria-label="${E(edge.label||edge.id)}：${E(edge.relation?'功能关联，非水力连接':q.label)}" class="pipe-entity ${selected===edge.id?'picked':''} ${isBad?'issue-edge':''}"><polyline class="pipe-hit" points="${points}"/><polyline class="pipe ${edge.relation?'association':''} ${q.state}" points="${points}"/><title>${E(edge.id)} · ${E(edge.relation?'功能关联，不表示已接通':q.label)} · ${E(edge.active===undefined?'':edge.active===null?'阀态未知':edge.active?'登记开':'登记关')}</title>`;
  if(edge.label){const p=edge.points[Math.floor(edge.points.length/2)],hasSymbol=['pump','filter','hx','valve'].includes(edge.label);out+=`<text class="edge-label" x="${p[0]}" y="${p[1]-(hasSymbol?30:12)}">${E(edge.label)}</text>`;if(hasSymbol)out+=`<g class="device-symbol" fill="oklch(.96 .01 80)" transform="translate(${p[0]} ${p[1]}) scale(.65)">${symbol(edge.label)}</g>`;}
  if(q.direction){const a=edge.points[0],b=edge.points[1],angle=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI+(q.direction<0?180:0);out+=`<path class="flow-direction" d="M-5-4 2 0-5 4" transform="translate(${(a[0]+b[0])/2} ${(a[1]+b[1])/2}) rotate(${angle})"/>`;}
  out+='</g>';
 }
 for(const n of scene.nodes){const fill=display==='temperature'?temperatureColor(n.temperature):'oklch(.95 .01 80)';
  out+=`<g data-entity="${E(n.id)}" tabindex="0" role="button" aria-label="${E(n.label)}" class="equipment ${selected===n.id?'picked':''} ${n.fault?'fault':''} ${n.operating?'operating':''}" transform="translate(${n.x} ${n.y})"><title>${E(n.label)}</title>`;
  if(n.type==='layers'){
   out+='<rect class="tank-outline" x="-80" y="-200" width="160" height="400" rx="18"/>';
   if(n.layers?.length){const h=380/n.layers.length;n.layers.forEach((v,i)=>{out+=`<rect data-layer="${i}" class="${selected===n.id&&selectedLayer===i?'current-layer':''}" x="-70" y="${190-(i+1)*h}" width="140" height="${h+.05}" fill="${temperatureColor(v)}"><title>底部第${i+1}层 · ${number(v)}°C</title></rect>`;});
    for(const {value,index}of labelledLayers(n.layers)){const y=190-(index+.5)*h;
     out+=`<path class="layer-tick" d="M80 ${y}h12"/><text data-layer-index="${index}" class="layer-temperature ${selected===n.id&&selectedLayer===index?'selected-temperature':''}" x="99" y="${y+4}">${String(index+1).padStart(2,'0')} · ${known(value)?value.toFixed(2):'未知'} °C<title>底部第${index+1}层：${number(value)} °C</title></text>`;
    }
   }
   else out+='<text x="0" y="-10" text-anchor="middle">逐层数据未知</text>';
   out+='<text class="node-hint" x="0" y="-215" text-anchor="middle">顶部</text><text class="node-hint" x="0" y="225" text-anchor="middle">底部 · 第1层</text>';
  }else out+=`<rect class="selection-box" x="-49" y="-49" width="98" height="98" rx="12"/><g class="device-symbol" fill="${fill}">${symbol(n.type)}</g>`;
  const y=n.type==='layers'?255:n.compactLabel?51:66;
  out+=`<text class="node-title" x="0" y="${y}" text-anchor="middle">${E(n.label)}</text>`;
  const read=display==='pressure'?n.metrics?.find(m=>m.unit==='kPa'):display==='flow'?n.metrics?.find(m=>m.unit==='m³/h'):metric('温度',n.temperature,'°C');
  const text=display==='temperature'&&known(n.speed)?`反馈 ${number(n.speed)}%`:known(read?.value)?`${n.valueLabel||''} ${number(read.value)} ${read.unit}`:display==='temperature'?'温度未知':display==='flow'?'流量未知':'压力未知';
  out+=`<text class="node-value" x="0" y="${y+23}" text-anchor="middle">${E(text)}</text>`;
  if(n.annotation)out+=`<text class="node-hint" x="0" y="${y+43}" text-anchor="middle">${E(n.annotation)}</text>`;
  if(n.statusLabel)out+=`<text class="equipment-state" x="${n.statusPosition==='side'?44:0}" y="${n.statusPosition==='side'?-14:-57}" text-anchor="${n.statusPosition==='side'?'start':'middle'}">${E(n.statusLabel)}</text>`;
  if(n.fault)out+=`<text class="fault-text" x="44" y="-32">!</text>`;
  out+='</g>';
 }
 return out+'</g></svg>';
}
export function referenceEnergy(temps,data){
 if(!temps?.length||![data?.reference_c,data?.rho,data?.cp,data?.tank_volume_m3].every(known))return null;
 return temps.reduce((s,t)=>s+Math.max(0,data.reference_c-t)*data.rho*data.cp*data.tank_volume_m3/temps.length/1e6,0);
}
export function curveSVG(samples,channels,t,{future=true,threshold=null}={}){
 const rows=future?samples:samples.filter(f=>f.t_s<=t+1e-9),vals=rows.flatMap(r=>channels.map(c=>c.get(r))).filter(known);
 if(!vals.length)return '<p class="empty-channel">本通道没有已到达、有效的计算记录。</p>';
 let lo=Math.min(...vals,...(known(threshold)?[threshold]:[])),hi=Math.max(...vals,...(known(threshold)?[threshold]:[]));
 if(hi-lo<.1){lo-=.1;hi+=.1;}const maxT=Math.max(.1,samples.at(-1)?.t_s||0),x=s=>46+s/maxT*710,y=v=>155-(v-lo)/(hi-lo)*125;
 let s=`<svg class="live-curve" viewBox="0 0 800 195" role="img" aria-label="${escapeHTML(channels.map(c=>c.label).join(' / '))}" data-max-time="${maxT}"><path d="M46 20V155H756" fill="none" stroke="oklch(.83 .01 80)"/><text x="3" y="30">${number(hi)}</text><text x="3" y="156">${number(lo)}</text>`;
 if(known(threshold))s+=`<path d="M46 ${y(threshold)}H756" stroke="oklch(.55 .17 25)" stroke-dasharray="5 5"/><text x="650" y="${y(threshold)-5}">入口上限 ${threshold}°C</text>`;
 for(const c of channels){let pen=false;const points=rows.map(r=>{const v=c.get(r);if(!known(v)){pen=false;return '';}const cmd=pen?'L':'M';pen=true;return `${cmd}${x(r.t_s)},${y(v)}`;}).join(' ');s+=`<path d="${points}" fill="none" stroke="${c.color}" stroke-width="2"/>`;}
 s+=`<path d="M${x(t)} 20V155" stroke="oklch(.4 .01 80)" stroke-dasharray="3 4"/><text x="46" y="180">0 s</text><text x="710" y="180">${number(maxT)} s</text></svg>`;
 return s+`<div class="curve-key">${channels.map(c=>`<span style="color:${c.color}">${escapeHTML(c.label)}</span>`).join('')}</div>`;
}
