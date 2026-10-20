// Document compiler and SVG renderer only. No physical solver, controller or M1 import.
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {dirname, resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root = dirname(fileURLToPath(import.meta.url));
const sha = data => createHash('sha256').update(data).digest('hex');
const load = name => JSON.parse(readFileSync(join(root, name), 'utf8'));
const save = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2)+'\n', 'utf8');
const spec = load('pid_spec.json');
const baselineBytes = readFileSync(join(root, spec.baseline.file));
if (sha(baselineBytes) !== spec.baseline.sha256) throw Error('BASELINE_HASH_MISMATCH');
const base = JSON.parse(baselineBytes);
const graph = {
  schema:'C2C-PID-EXPANDED-1', revision:spec.revision, status:spec.status,
  engineering_status:spec.engineering_status, authority:spec.authority,
  input_sha256:sha(readFileSync(join(root,'pid_spec.json'))), baseline:spec.baseline,
  sources:spec.sources, inventory:spec.inventory, rules:spec.rules,
  changes:spec.changes, unresolved:spec.unresolved, drawing:spec.drawing,
  components:[], ports:[], edges:[], sensors:[], heat_couplings:[], assemblies:[],
  inherited_context_scope:'Original source/tank functional graph retained unchanged, not detailed or dynamically verified by this revision.'
};
const affected = id => /^G01-C0[123][AB](?:$|[:\/-])/.test(id) || /^G01-U[123]-R0[1-6](?:$|[:\/-])/.test(id);
graph.components = structuredClone(base.components.filter(x => !affected(x.tag)));
graph.edges = structuredClone(base.edges.filter(x => !affected(x.id)));
graph.sensors = structuredClone(base.sensors.filter(x => !affected(x.id)));
const ports = new Map(base.ports.filter(x=>!affected(x.id)).map(x=>[x.id,structuredClone(x)]));
function port(id, domain, extra={}) {
  if (ports.has(id) && ports.get(id).fluid_domain !== domain) throw Error('DOMAIN_CONFLICT '+id);
  if (!ports.has(id)) ports.set(id,{id, fluid_domain:domain, ...extra});
  return id;
}
const substitute = (s,u,side) => s.replaceAll('{unit}',String(u)).replaceAll('{side}',side||'');

function expand(templateName, tag, unit, side=null) {
  const t=spec.templates[templateName], map=new Map();
  const domain = d=>substitute(d,unit,side);
  const asm={tag, template:templateName, unit, secondary_network:side,
    CDU_IDENTITY:templateName==='CDU'?tag.replace('G01-',''):null,
    selectable_primary_networks:templateName==='CDU'?['A','B']:null,
    devices:[],junctions:[],boundaries:[],pipes:[],instruments:[]};
  graph.components.push({tag,kind:templateName==='CDU'?'CDU':'RACK_LOAD',unit,
    CDU_IDENTITY:asm.CDU_IDENTITY,secondary_network:side,
    primary_selection_independent:templateName==='CDU',source_refs:t.source_refs});
  for(const b of t.boundaries) {
    const id=substitute(t.boundary_bindings[b.id],unit,side);
    port(id,domain(b.domain)); map.set(b.id,{in:id,out:id,xy:b.xy});
    asm.boundaries.push({...b,fluid_domain:domain(b.domain),port_id:id});
  }
  for(const j of t.junctions) {
    const id=port(tag+':'+j.id,domain(j.domain),{equipment_tag:tag,kind:'JUNCTION'});
    map.set(j.id,{in:id,out:id,xy:j.xy});
    asm.junctions.push({...j,port_id:id});
  }
  for(const d of t.devices) {
    const id=tag+'-'+d.id;
    const status=d.proposal?'PROPOSED_DESIGN_REVISION':'DRAWING_TEMPLATE_EXPANSION';
    const device={...d,tag:id,parent:tag,unit,confirmation:status,fluid_domain:d.domain?domain(d.domain):null,
      normal_position:null,fail_position:null,actual_feedback:null,source_refs:t.source_refs};
    delete device.domain;
    if(d.kind==='heat_exchanger') {
      device.ports={};
      for(const [suffix,xy] of Object.entries(d.ports)) {
        const p=port(id+':'+suffix,domain(d.domains[suffix]),{equipment_tag:id});
        device.ports[suffix]=p; map.set(d.id+':'+suffix,{in:p,out:p,xy});
      }
      for(const n of ['P1','P2']) graph.edges.push({id:id+'/'+n,upstream:device.ports[n+'-IN'],
        downstream:device.ports[n+'-OUT'],fluid_domain:domain(d.domains[n+'-IN']),
        kind:'HX_PASS',equipment_tag:id,confirmation:status,source_refs:t.source_refs});
      graph.heat_couplings.push({id:id+'/HEAT',primary_edge:id+'/P1',secondary_edge:id+'/P2',
        fluid_mixing:false,UA_actual:null,pressure_drop_actual:null,energy_coupling_only:true});
    } else {
      const half=d.kind==='rack'?90:d.kind==='pump'?32:22;
      const pin=port(id+':IN',domain(d.domain),{equipment_tag:id});
      const pout=port(id+':OUT',domain(d.domain),{equipment_tag:id});
      device.ports={IN:pin,OUT:pout};
      map.set(d.id,{in:pin,out:pout,inXY:[d.xy[0]-half,d.xy[1]],outXY:[d.xy[0]+half,d.xy[1]],xy:d.xy});
      graph.edges.push({id:id+'/through',upstream:pin,downstream:pout,
        fluid_domain:domain(d.domain),kind:'DEVICE_PASS',equipment_tag:id,
        device_kind:d.kind,direction:d.kind==='check_valve'?'FORWARD_ONLY':'DESIGN_REFERENCE_FLOW_NOT_REVERSAL_PROOF',
        actual_feedback_required:['motor_valve','isolation_valve','pump'].includes(d.kind),
        confirmation:status,source_refs:t.source_refs});
    }
    graph.components.push(device); asm.devices.push(device);
  }
  let index=0;
  for(const chain of t.chains) {
    for(let i=0;i<chain.length-1;i++) {
      const a=map.get(chain[i]),b=map.get(chain[i+1]);
      if(!a||!b) throw Error('UNRESOLVED_CHAIN '+tag+JSON.stringify(chain));
      if(ports.get(a.out).fluid_domain!==ports.get(b.in).fluid_domain) throw Error('CROSS_FLUID_PIPE');
      const xy1=a.outXY||a.xy,xy2=b.inXY||b.xy;
      // Routing is drawing-only. It never creates a node at an incidental crossing.
      const targetIsJunction=t.junctions.some(j=>j.id===chain[i+1]);
      const route=xy1[1]===xy2[1]?[xy1,xy2]:targetIsJunction?[xy1,[xy2[0],xy1[1]],xy2]:[xy1,[xy1[0],xy2[1]],xy2];
      const e={id:tag+'/PIPE-'+String(++index).padStart(2,'0'),upstream:a.out,downstream:b.in,
        fluid_domain:ports.get(a.out).fluid_domain,kind:'PIPE',drawing_points:route,
        confirmation:'REVISED_EXPLICIT_CONNECTIVITY',source_refs:t.source_refs};
      graph.edges.push(e); asm.pipes.push(e);
    }
  }
  for(const s of t.instruments) {
    const endpoint=token=>{
      if(map.has(token)) {const r=map.get(token);return {port:r.out,xy:r.outXY||r.xy};}
      const at=token.lastIndexOf(':'), key=token.slice(0,at), suffix=token.slice(at+1);
      const r=map.get(key); if(!r||!['IN','OUT'].includes(suffix)) throw Error('UNKNOWN_TAP '+token);
      return {port:suffix==='IN'?r.in:r.out,xy:suffix==='IN'?(r.inXY||r.xy):(r.outXY||r.xy)};
    };
    const tap=endpoint(s.tap),low=s.low_tap?endpoint(s.low_tap):null;
    const instrument={...s,tag:tag+'-'+s.id,parent:tag,tap_port:tap.port,tap_xy:tap.xy,
      low_tap_port:low?.port||null,low_tap_xy:low?.xy||null,
      measured_value:null,timestamp:null,hardware_independence:'NOT_HARDWARE_VERIFIED'};
    asm.instruments.push(instrument);
    for(const ch of s.channels||['SINGLE']) graph.sensors.push({...instrument,id:instrument.tag+'-'+ch,
      port:tap.port,channel:ch,confirmation:s.status,source_refs:t.source_refs});
  }
  graph.assemblies.push(asm);
}
for(const u of spec.inventory.units) {
  for(const s of spec.inventory.cdu_sides) expand('CDU',`G01-C${String(u).padStart(2,'0')}${s}`,u,s);
  for(let r=1;r<=spec.inventory.racks_per_unit;r++) expand('RACK',`G01-U${u}-R${String(r).padStart(2,'0')}`,u);
}
const usedPorts=new Set(graph.edges.flatMap(e=>[e.upstream,e.downstream]));
graph.ports=[...ports.values()].filter(p=>usedPorts.has(p.id));

const checks=[];
function check(id, result, detail) {checks.push({id,status:result?'PASS':'FAIL',detail});if(!result) throw Error(id+' '+detail);}
function unique(xs,key){return new Set(xs.map(x=>x[key])).size===xs.length;}
check('UNIQUE_COMPONENT_IDS',unique(graph.components,'tag'),'No duplicate equipment tags');
check('UNIQUE_EDGE_IDS',unique(graph.edges,'id'),'No duplicate pipe/pass tags');
check('UNIQUE_PORT_IDS',unique(graph.ports,'id'),'No duplicate graph nodes');
const pmap=new Map(graph.ports.map(p=>[p.id,p]));
check('ALL_ENDPOINTS_RESOLVED',graph.edges.every(e=>pmap.has(e.upstream)&&pmap.has(e.downstream)),'Explicit port references only');
check('NO_CROSS_FLUID_PIPE',graph.edges.every(e=>pmap.get(e.upstream).fluid_domain===pmap.get(e.downstream).fluid_domain),'HX heat couplings are not fluid edges');
check('ALL_SENSOR_TAPS_RESOLVED',graph.sensors.every(s=>pmap.has(s.port)&&(!s.low_tap_port||pmap.has(s.low_tap_port))),'No dangling proposed or inherited tap');
const counts={cdus:graph.assemblies.filter(a=>a.template==='CDU').length,
  secondary_pumps:graph.components.filter(c=>c.kind==='pump').length,
  racks:graph.assemblies.filter(a=>a.template==='RACK').length,
  rack_selector_valves:graph.components.filter(c=>c.kind==='motor_valve'&&/^G01-U\d-R\d+-CV-/.test(c.tag)).length};
for(const [key,value] of Object.entries(spec.inventory.required_counts)) check('COUNT_'+key.toUpperCase(),counts[key]===value,`${counts[key]} / ${value}`);
check('INHERITED_CONTEXT_UNCHANGED',base.edges.filter(e=>!affected(e.id)).every(e=>JSON.stringify(e)===JSON.stringify(graph.edges.find(n=>n.id===e.id))), 'Exact original source/tank edges retained');
check('NO_SERVICE_PSEUDOVALVES',graph.components.every(c=>!c.tag.includes('-SERVICE')),'Logical FILTER-SERVICE replaced by explicit equipment');
check('UNKNOWN_VALVE_STATES_NOT_INVENTED',graph.assemblies.every(a=>a.devices.every(d=>d.actual_feedback===null&&d.fail_position===null&&d.normal_position===null)),'No simulation or PLC feedback generated');
// Exhaustive small document-graph path checks, not a hydraulic or Boolean stress test.
function hasPath(start,end,blocked) {
  const queue=[start],seen=new Set(queue);
  for(let i=0;i<queue.length;i++)for(const e of graph.edges)if(e.upstream===queue[i]&&!blocked(e)&&!seen.has(e.downstream)){
    if(e.downstream===end)return true;seen.add(e.downstream);queue.push(e.downstream);
  }
  return false;
}
for(const a of graph.assemblies.filter(a=>a.template==='CDU')) {
  const ret=a.boundaries.find(b=>b.id==='SEC_RET').port_id,sup=a.boundaries.find(b=>b.id==='SEC_SUP').port_id;
  const onlyThis=e=>!e.id.startsWith(a.tag+'/')&&!e.id.startsWith(a.tag+'-');
  check(a.tag+'_HAS_DESIGN_PATH',hasPath(ret,sup,onlyThis),'A pump + a filter + HX on an explicit route');
  check(a.tag+'_NO_PUMP_BYPASS',!hasPath(ret,sup,e=>onlyThis(e)||e.device_kind==='pump'),'Removing both pump passes removes all supply paths');
  check(a.tag+'_NO_FILTER_BYPASS',!hasPath(ret,sup,e=>onlyThis(e)||e.device_kind==='filter'),'Removing both secondary filter passes removes all supply paths');
  check(a.tag+'_NO_HX_BYPASS',!hasPath(ret,sup,e=>onlyThis(e)||e.kind==='HX_PASS'),'Removing secondary HX pass removes supply path');
  for(const f of a.devices.filter(d=>d.kind==='filter'))check(f.tag+'_TWO_ISOLATIONS',
    a.devices.some(d=>d.id===f.id+'-I')&&a.devices.some(d=>d.id===f.id+'-O'),'Each filter explicitly has I and O');
}
check('HX_FLUID_SEPARATION',graph.heat_couplings.length===6&&graph.heat_couplings.every(h=>h.fluid_mixing===false),'6 heat-only interfaces');
graph.validation_summary={scope:'DOCUMENT_STRUCTURE_AND_CONNECTIVITY_ONLY',counts,checks:checks.length,
  dynamic_result:'NOT_DYNAMICALLY_VERIFIED',engineering_result:spec.engineering_status};

// Pure presentation function: consumes expanded JSON. No hidden connectivity or live simulation.
export function render(g,cduTag,rackTag) {
  const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  const c=g.assemblies.find(a=>a.tag===cduTag&&a.template==='CDU');
  const r=g.assemblies.find(a=>a.tag===rackTag&&a.template==='RACK');
  if(!c||!r||c.unit!==r.unit)throw Error('CDU_RACK_UNIT_MISMATCH');
  const primary='#22d3ee',secondary='#34d399',proposal='#fb923c',text='#e2e8f0',muted='#94a3b8';
  const line=(points,color,width=2,dashed=false,attr='')=>`<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="${width}" ${dashed?'stroke-dasharray="6 5"':''} ${attr}/>`;
  const label=(x,y,s,size=16,color=text,anchor='middle',extra='')=>`<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${color}" ${extra}>${esc(s)}</text>`;
  const box=(x,y,w,h,stroke,fill='#0f172a')=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="${fill}" stroke="${stroke}"/>`;
  let s=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="${g.drawing.viewBox.join(' ')}" role="img" aria-labelledby="title desc"><title id="title">${esc(g.revision)} ${esc(cduTag)} ${esc(rackTag)}</title><desc id="desc">JSON-driven process P&amp;ID. Not a construction drawing, operating state or dynamic result.</desc><defs><style>text{font-family:'Cascadia Code','Microsoft YaHei','Noto Sans SC',sans-serif} text{font-weight:400}</style><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#1e293b" stroke-width=".5"/></pattern><marker id="flow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0 0L8 3L0 6" fill="none" stroke="#94a3b8"/></marker></defs><rect width="2200" height="1980" fill="#0f172a"/><rect width="2200" height="1980" fill="url(#grid)"/>`;
  s+=label(45,44,'MEMPHIS / R12 · JSON 驱动的过程 P&ID',29,text,'start');
  s+=label(45,78,`${g.revision} · 非施工批准 / 非运行画面 / 非热水力 PASS`,18,proposal,'start');
  s+=label(45,112,`01  CDU详图：${cduTag}    身份=${c.CDU_IDENTITY}    二次网=${c.secondary_network}    一次网=A 或 B（独立选择）`,19,text,'start');
  s+=box(42,137,2110,370,primary,'rgba(8,51,68,.16)');
  s+=box(42,545,2110,560,secondary,'rgba(6,78,59,.12)');
  s+=label(65,492,'一次 PG25 · 内部 DN150 为图纸要求；新增两路过滤，不设无过滤旁通',16,primary,'start');
  s+=label(65,576,'二次 PG25 · 各泵独立 VFD；两泵 1用1备；泵 → 过滤器 → HX → 供液',18,secondary,'start');
  s+=label(45,1190,`02  机柜接口：${rackTag}    本模板展开到本组全部18柜；每柜4个选择阀`,21,text,'start');
  s+=box(42,1220,2110,500,secondary,'rgba(6,78,59,.08)');
  const pipes=[],instruments=[],bodies=[],labels=[];
  for(const a of [c,r]) {
    for(const p of a.pipes){
      const color=p.fluid_domain==='PG25_PRIMARY'?primary:secondary;
      pipes.push(`<g data-edge="${esc(p.id)}"><title>${esc(p.id+' | '+p.upstream+' → '+p.downstream)}</title>${line(p.drawing_points,color,2.4,false,'marker-end="url(#flow)"')}</g>`);
    }
    for(const j of a.junctions){bodies.push(`<circle cx="${j.xy[0]}" cy="${j.xy[1]}" r="5" fill="${a.template==='RACK'?secondary:j.domain==='PG25_PRIMARY'?primary:secondary}" data-port="${esc(j.port_id)}"><title>${esc(j.port_id)}</title></circle>`);}
    for(const b of a.boundaries){labels.push(label(b.xy[0],b.xy[1]-40,b.label,16,b.fluid_domain==='PG25_PRIMARY'?primary:secondary));labels.push(label(b.xy[0],b.xy[1]+35,b.port_id.replace('G01-',''),12,muted));bodies.push(`<circle cx="${b.xy[0]}" cy="${b.xy[1]}" r="6" stroke="#94a3b8" fill="#0f172a"/>`);}
    for(const d of a.devices) {
      const [x,y]=d.xy,col=d.proposal?proposal:d.kind==='heat_exchanger'?'#a78bfa':(d.fluid_domain||'').includes('PRIMARY')?primary:secondary;
      let b='';
      if(d.kind==='heat_exchanger'){
        const endpoints={};for(const p of a.pipes)for(const [id,pt] of [[p.upstream,p.drawing_points[0]],[p.downstream,p.drawing_points.at(-1)]])if(Object.values(d.ports).includes(id))endpoints[id]=pt;
        const p1i=endpoints[d.ports['P1-IN']],p1o=endpoints[d.ports['P1-OUT']],p2i=endpoints[d.ports['P2-IN']],p2o=endpoints[d.ports['P2-OUT']];
        const cx=(p1i[0]+p1o[0])/2,cy=(p1i[1]+p2i[1])/2;
        b=box(p1i[0],p1i[1]-50,p1o[0]-p1i[0],p2i[1]-p1i[1]+100,col);
        b+=line([p1i,p1o],primary,3)+line([p2i,p2o],secondary,3);
        b+=line([[cx,p1i[1]+50],[cx,p2i[1]-50]],'#a78bfa',2,true);
        b+=label(cx,cy-45,'HX',27,'#a78bfa')+label(cx,cy-10,'仅传热',17)+label(cx,cy+20,'不混液',17)+label(cx,cy+55,'UA 待厂家',13,muted);
      } else if(d.kind==='rack') {
        b=box(x-90,y-65,180,130,col)+label(x,y-14,'GB300',21)+label(x,y+20,'147.25 kW 入液',15)+label(x,y+48,'设计负荷',13,muted);
      } else if(d.kind==='pump') {
        b=`<circle cx="${x}" cy="${y}" r="32" fill="#0f172a" stroke="${col}" stroke-width="2"/><path d="M${x-16} ${y-20}L${x+23} ${y}L${x-16} ${y+20}Z" fill="none" stroke="${col}"/>`;
      } else if(d.kind==='filter') {
        b=`<rect x="${x-22}" y="${y-25}" width="44" height="50" fill="#0f172a" stroke="${col}"/><path d="M${x-18} ${y+20}L${x+18} ${y-20}M${x-15} ${y-20}L${x+15} ${y+20}" stroke="${col}" fill="none"/>`;
      } else if(d.kind==='check_valve') {
        b=`<rect x="${x-23}" y="${y-20}" width="46" height="40" fill="#0f172a"/><path d="M${x-18} ${y-17}L${x+12} ${y}L${x-18} ${y+17}ZM${x+18} ${y-19}V${y+19}" stroke="${col}" fill="none" stroke-width="2"/>`;
      } else {
        b=`<rect x="${x-23}" y="${y-21}" width="46" height="42" fill="#0f172a"/><path d="M${x-22} ${y-17}L${x+22} ${y+17}V${y-17}L${x-22} ${y+17}Z" fill="none" stroke="${col}" stroke-width="2"/>`;
        if(d.kind==='motor_valve')b+=line([[x,y-19],[x,y-40]],col)+box(x-13,y-65,26,25,col)+label(x,y-47,'M',16,col);
      }
      bodies.push(`<g data-equipment="${esc(d.tag)}"><title>${esc(d.tag+' | '+d.confirmation+' | actual_feedback=null')}</title>${b}</g>`);
      if(d.kind!=='heat_exchanger'){
        labels.push(label(x,y+(d.kind==='rack'?96:56),d.id,14,col));
        if(d.kind==='filter')labels.push(label(x,y+78,`≤${d.micron_requirement} μm${d.proposal?' · 拟定':''}`,12,muted));
        if(d.kind==='pump')labels.push(label(x,y+80,'VFD · 100%要求',12,muted));
      }
    }
    for(const i of a.instruments){
      const [x,y]=i.xy,col=i.status.startsWith('PROPOSED')?proposal:muted;
      // Instrument lines are dashed and do not add fluid edges. Separate routes avoid central hardware.
      const tapLine=(xy,n)=>{
        const above=y<xy[1],lane=above?y+56:y-56;
        if(i.id==='P2-SYS-PDT')return line([[x+(n?8:-8),y-24],[x+(n?8:-8),1072+n*14],[xy[0]+(n?-18:18),1072+n*14],[xy[0]+(n?-18:18),xy[1]],[xy[0],xy[1]]],col,1,true);
        return line([[x+(n?7:0),y+(above?24:-24)],[x+(n?7:0),lane],[xy[0],lane],xy],col,1,true);
      };
      instruments.push(`<g data-instrument="${esc(i.tag)}"><title>${esc(i.tag+' | tap '+i.tap_port+(i.low_tap_port?' / L '+i.low_tap_port:'')+' | '+i.status)}</title>${tapLine(i.tap_xy,0)}${i.low_tap_xy?tapLine(i.low_tap_xy,1):''}<circle cx="${x}" cy="${y}" r="24" fill="#0f172a" stroke="${col}"/>${label(x,y+6,i.symbol,15,col)}</g>`);
      labels.push(label(x,y-39,i.id,13,col));
      if(i.channels)labels.push(label(x,y+41,i.channels.join('/'),11,col));
    }
  }
  s+=pipes.join('')+instruments.join('')+bodies.join('')+labels.join('');
  s+=label(100,1140,`全位号前缀：${cduTag}-；下方机柜前缀：${rackTag}-。橙色设备为修订提案，不代表已采购或厂家已提供。`,16,muted,'start');
  s+=label(1050,1685,'机柜选择阀必须供回成对；受控短时重叠另受 ΔT≤2K、Δp≤5kPa、稳定5s、重叠≤30s 约束。',16,muted);
  s+=box(42,1760,2110,175,'#475569');
  for(let i=0;i<g.drawing.notes.length;i++)s+=label(65,1792+i*29,g.drawing.notes[i],15,i===1?proposal:muted,'start');
  s+=label(45,1968,`图纸身份 ${g.input_sha256.slice(0,20)}… / JSON登记6 CDU · 12二次泵 · 18柜 · 72选择阀 / 未运行仿真`,14,muted,'start');
  return s+'</svg>';
}

const out=resolve(process.argv[2]||join(root,'diagram'));
mkdirSync(out,{recursive:true});
const expandedPath=join(out,'memphis_r12_pid.expanded.json');
save(expandedPath,graph);
// Strict two-stage order: persist expanded JSON, then load it back as the sole renderer input.
const drawingInput=JSON.parse(readFileSync(expandedPath,'utf8'));
const svg=render(drawingInput,spec.drawing.default_cdu,spec.drawing.default_rack);
writeFileSync(join(out,'memphis_r12_pid.svg'),svg,'utf8');
save(join(out,'document_validation.json'),{status:'PASS',scope:'DOCUMENT_FILE_VALIDATION_ONLY_NOT_MODEL_TEST',checks,
  counts,original_baseline_sha256:spec.baseline.sha256,input_sha256:graph.input_sha256,
  expanded_raw_sha256:sha(readFileSync(expandedPath)),dynamic_result:'NOT_DYNAMICALLY_VERIFIED',engineering_status:spec.engineering_status});
const data=JSON.stringify(drawingInput).replaceAll('<','\\u003c');
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Memphis R12 · JSON P&ID</title><style>body{margin:0;background:#0b1221;color:#e2e8f0;font:16px 'Microsoft YaHei',sans-serif}header{padding:20px 28px;background:#152039;position:sticky;top:0;z-index:2;box-shadow:0 3px 14px #0008}h1{font-size:22px;margin:0 0 10px}p{margin:6px 0;color:#a9b8d2}select,button,a{background:#1e3150;color:#fff;border:1px solid #496383;border-radius:6px;padding:8px;margin:4px;text-decoration:none}main{overflow:auto;padding:10px}#drawing{width:2200px;transform-origin:top left}svg{display:block;width:100%;height:auto}details{margin:20px 30px;padding:12px;border:1px solid #475569}pre{white-space:pre-wrap;font-size:13px}label{white-space:nowrap}</style><header><h1>孟菲斯 R12 · 可追溯 P&ID 过程验证修订版</h1><p>先 JSON → 显式端口/管路展开 → 同源绘图。不是实时故障画面，也不是仿真结果。</p><label>CDU <select id="cdu"></select></label><label>机柜 <select id="rack"></select></label><label>缩放 <select id="zoom"><option value="0.55">55%</option><option value="0.75">75%</option><option value="1">100%</option><option value="1.25">125%</option></select></label><button id="download">下载当前 SVG</button><a href="memphis_r12_pid.expanded.json">完整展开 JSON</a><a href="pid_spec.json">编制 JSON</a><a href="README_ZH.md">修订说明</a><p id="identity"></p></header><main id="canvas"><div id="drawing"></div></main><details><summary>本轮修订与仍未解决的工程事项</summary><pre id="notes"></pre></details><script>const graph=${data};const render=${render.toString()};const cdu=document.getElementById('cdu'),rack=document.getElementById('rack'),drawing=document.getElementById('drawing'),zoom=document.getElementById('zoom');for(const a of graph.assemblies.filter(a=>a.template==='CDU'))cdu.add(new Option(a.tag,a.tag));cdu.value=graph.drawing.default_cdu;function racks(){const u=graph.assemblies.find(a=>a.tag===cdu.value).unit;const old=rack.value;rack.replaceChildren();for(const a of graph.assemblies.filter(a=>a.template==='RACK'&&a.unit===u))rack.add(new Option(a.tag,a.tag));if([...rack.options].some(o=>o.value===old))rack.value=old;}function redraw(){drawing.innerHTML=render(graph,cdu.value,rack.value);drawing.style.width=(2200*Number(zoom.value))+'px';document.getElementById('identity').textContent=graph.revision+' | JSON SHA256 '+graph.input_sha256;}cdu.onchange=()=>{racks();redraw()};rack.onchange=redraw;zoom.onchange=redraw;document.getElementById('download').onclick=()=>{const url=URL.createObjectURL(new Blob([render(graph,cdu.value,rack.value)],{type:'image/svg+xml'}));const a=document.createElement('a');a.href=url;a.download=cdu.value+'-'+rack.value+'-PID.svg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};document.getElementById('notes').textContent=JSON.stringify({changes:graph.changes,unresolved:graph.unresolved},null,2);racks();redraw();</script></html>`;
writeFileSync(join(out,'pid_viewer.html'),html,'utf8');
for(const file of ['pid_spec.json','README_ZH.md','build.mjs'])writeFileSync(join(out,file),readFileSync(join(root,file)));
mkdirSync(join(out,'inputs'),{recursive:true});
writeFileSync(join(out,spec.baseline.file),baselineBytes);
const names=['pid_spec.json','build.mjs','README_ZH.md',spec.baseline.file,'memphis_r12_pid.expanded.json','document_validation.json','memphis_r12_pid.svg','pid_viewer.html'];
save(join(out,'package_manifest.json'),{schema:'C2C-PID-PACKAGE-HASHES-1',revision:spec.revision,
  scope:'DOCUMENT_ONLY_NOT_DYNAMIC_PASS',baseline:spec.baseline,
  files:names.map(file=>({file,sha256:sha(readFileSync(join(out,file))),bytes:readFileSync(join(out,file)).length})),
  manifest_self_hash:'Not embedded; compute SHA256 of this file externally.'});
console.log(JSON.stringify({output:out,document_checks:checks.length,counts,graph_edges:graph.edges.length,
  manifest_sha256:sha(readFileSync(join(out,'package_manifest.json'))),engineering_status:spec.engineering_status},null,2));
