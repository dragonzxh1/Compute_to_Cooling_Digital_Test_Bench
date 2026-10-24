// File preparation only. No numerical solver is loaded or run locally.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const here=import.meta.dirname,repo=path.resolve(here,'../../../..');fs.mkdirSync(path.join(here,'data'),{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,'')),hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const basisPath=path.join(repo,'v0_2/tests/tools/memphis_00_01_hydraulic_v1/basis.json'),basis=read(basisPath);
const values={rack_kw:155,liquid_fraction:.95,rho:1009,cp:4000,primary_flow:330,secondary_flow:68.37,tank_volume:15,cold_fraction:.7,cold_c:40.9448,hot_c:48.29,mixing:0,primary_c:41,secondary_target:44,ua:220,pump_h0:null,pump_k:null,pump_speed:.9,source_reject:null,wet_bulb:30,dry_bulb:37,source_drop:96.52,load_drop:155.92,external_drop:123.58,rack_drop:171.63,hx_drop:26.6,internal_drop:50};
const {fields,SCHEMA,validate}=await import('./core.mjs');
fs.writeFileSync(path.join(here,'data/parameter_contract.json'),JSON.stringify(fields,null,2));
const study=new Set(['rho','cp','cold_fraction','cold_c','hot_c','mixing','ua','pump_speed','wet_bulb']);
const locators={rack_kw:'00 B020：单柜155kW设计功率',liquid_fraction:'00 B020：用户确认95%入液设计口径',primary_flow:'00 B020/B200：每18柜330m³/h设计流量，非实测',secondary_flow:'00 B163预算design_flow_m3_h：六柜68.37m³/h高温参考',tank_volume:'既有项目设计记录15m³；此依据摘录未含罐体条款，原件段落定位待补',primary_c:'01 B020：干球≥37°C，一次41°C边界',secondary_target:'01 B020：干球≥37°C，二次44°C目标，硬上限45°C',dry_bulb:'01 B020：选取37°C高温分界工况',source_drop:'00 B154/B200：源侧96.52kPa运行预算',load_drop:'00 B154/B200：负荷侧155.92kPa运行预算',external_drop:'00 B163：外部等效路径123.58kPa',rack_drop:'00 B163：单机柜并联支路171.63kPa，不乘六',hx_drop:'00 B163：板换二次26.60kPa预算',internal_drop:'00 B163：内部管阀过滤50kPa预算'};
const parameters=Object.fromEntries(Object.entries(values).map(([k,value])=>[k,{value,unit:fields[k][1],kind:value===null?'UNKNOWN':study.has(k)?'ENGINEERING_ASSUMPTION':'CUSTOMER_DESIGN',source:value===null?'尚无同工况厂家确认数据':study.has(k)?'明确研究初态/物性/边界；沿用既有研究口径，不是厂家保证':locators[k]}]));
const topology={authority:'CUSTOMER_FUNCTIONAL_REQUIREMENTS_NOT_AS_BUILT',description:'00/01功能要求模板。不是R12、施工图或已验证运行阀序；每CDU内部100%备用支路未展开。',ports:[],edges:[],circuits:[],primary_pairs:[],standby_pairs:[1,2,3].map(u=>({a:`U${u}-CDU-A`,b:`U${u}-CDU-B`})),inventory:{racks:18,cdus:6,secondary_pumps:12,rack_selectors:72}};
for(let u=1;u<=3;u++)for(const s of ['A','B']){const id=`U${u}-CDU-${s}`,domain=`SECONDARY-U${u}-${s}`;
 const nodes=['RETURN','PUMP_OUT','FILTER_OUT','SUPPLY'];nodes.forEach(n=>topology.ports.push({id:id+':'+n,domain,unit:u}));
 for(const [i,kind] of ['pump','filter','hx'].entries())topology.edges.push({id:id+'-'+kind,from:id+':'+nodes[i],to:id+':'+nodes[i+1],kind,circuit:id,active:null,provenance:'00/01功能序列约简，非逐段实物'});
 topology.circuits.push({id,from:id+':RETURN',to:id+':SUPPLY',unit:u,side:s});
}
const d={schema:SCHEMA,title:'孟菲斯 00/01 · 18柜设计基线',revision:'00-01 baseline',requirements:{rack_count:18,rack_inlet_max_c:45,primary_min_m3_h:330,reserve_s:90,tank_rise_max_k:.5},parameters,topology,patches:[],sources:{documents:basis.sources,basis_sha256:hash(basisPath),basis_locator:'word/document.xml顶层B编号，非印刷页码',extracts:basis.selected_source_blocks},engineering_status:'MEMPHIS_ENGINEERING_NOT_APPROVED'};validate(d);
fs.writeFileSync(path.join(here,'data/baseline.json'),JSON.stringify(d,null,2));
const root='D:/Github/c2c-evidence-review/memphis-equipment-v2/run39088951176/full/memphis-equipment-raw-group-a-39088951176/artifacts/m1-autonomous-development/memphis-equipment-v2-39088951176-1/group-a';
const source=path.join(root,'G_WET_LOSS/case/series.json'),indexPath=path.join(root,'artifact_hashes.json'),idx=read(indexPath);
const rows=idx.records||idx.files;const record=rows.find(r=>(r.path||r.relative_path||'').replaceAll('\\','/').endsWith('G_WET_LOSS/case/series.json'));
if(!record||(record.sha256||record.raw_sha256)!==hash(source))throw Error('HISTORICAL_INDEX_BINDING');
const resultPath=path.join(root,'G_WET_LOSS/case/result.json'),resultRecord=rows.find(r=>(r.path||r.relative_path||'').replaceAll('\\','/').endsWith('G_WET_LOSS/case/result.json'));
if(!resultRecord||(resultRecord.sha256||resultRecord.raw_sha256)!==hash(resultPath))throw Error('HISTORICAL_RESULT_INDEX_BINDING');
const result=read(resultPath),historicalVerdict={source_variant:result.source_variant,source_variant_approval:result.source_variant_approval,maximum_inlet_c:result.maximum_inlet_c,temperature_observation:result.maximum_inlet_c>45?'HISTORICAL_FAIL_45C':'HISTORICAL_RECORD_WITHIN_45C_NOT_APPROVAL',energy:result.energy};
const frames=read(source).map(r=>({t_s:r.time_ns/1e9,A:r.tank_A_k.map(k=>k-273.15),B:r.tank_B_k.map(k=>k-273.15),cold_A_m3:r.cold_A_m3,cold_B_m3:r.cold_B_m3,source_flow_m3_h:r.source_flow_m3_h,source_state:r.source_state,primary_c:r.primary_inlet_c,rack_inlet_c:r.units.flatMap(u=>u.inlet_k.map(k=>k-273.15)),unit_flow_m3_h:r.units.map(u=>u.flow_m3_s*3600),dp_kpa:r.units.map(u=>u.dp_pa/1000)}));
fs.writeFileSync(path.join(here,'data/historical.json'),JSON.stringify({schema:'C2C-HISTORICAL-REPLAY-1',mode:'HISTORICAL_NOT_CURRENT_DESIGN',run:'39088951176',case:'G_WET_LOSS',source_file:'G_WET_LOSS/case/series.json',raw_sha256:hash(source),result_sha256:hash(resultPath),index_sha256:hash(indexPath),scope:'旧V2 18柜W1失效、未选定条件性V9变体；不是当前00/01客户基线或新修改方案结果',summary:historicalVerdict,events:result.source_timeline.map(e=>({t_s:e.time_ns/1e9,from:e.from_state,to:e.to_state,reason:e.reason})),tank_volume_m3:15,reference_c:48.29,rho:1009,cp:4000,cold_threshold_c:41.4448,layer_order:'BOTTOM_TO_TOP',frames}));
console.log(JSON.stringify({baseline:true,historical_frames:frames.length,source_sha256:hash(source)}));
