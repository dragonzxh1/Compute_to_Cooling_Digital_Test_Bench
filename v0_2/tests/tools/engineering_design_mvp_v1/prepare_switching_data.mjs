// Project already saved evidence; does not import or advance a physical model.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const here=import.meta.dirname,read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,'')),hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sourceRoot='D:/Github/c2c-evidence-review/memphis-equipment-v2/run39088951176/full/memphis-equipment-raw-group-a-39088951176/artifacts/m1-autonomous-development/memphis-equipment-v2-39088951176-1/group-a';
const index=read(path.join(sourceRoot,'artifact_hashes.json')),rawBindings={};
function sourceFile(name){const p=path.join(sourceRoot,'G_WET_LOSS/case',name),rec=(index.records||index.files).find(r=>(r.path||r.relative_path).replaceAll('\\','/').endsWith('G_WET_LOSS/case/'+name));if(!rec||(rec.sha256||rec.raw_sha256)!==hash(p))throw Error('SOURCE_RAW_HASH '+name);rawBindings[name]=hash(p);return read(p);}
const physics=sourceFile('physics.json'),phases=sourceFile('source_phases.json'),result=sourceFile('result.json');let phaseIndex=-1;
const sourceFrames=physics.map(p=>{while(phaseIndex+1<phases.length&&phases[phaseIndex+1].time_ns<=p.end_ns)phaseIndex++;
 const phase=phases[phaseIndex];
 return {t_s:p.end_ns/1e9,source_path:p.source_path,source_tank:p.source_tank,load_tank:p.load_tank,source_q:p.source_flow_m3_h,load_q:p.load_flow_m3_h,
  source_speed:p.source_speed,source_supply_valve:p.source_supply_valve,source_return_valve:p.source_return_valve,load_supply_valve:p.load_supply_valve,load_return_valve:p.load_return_valve,
  available:p.source_available,source_outlet_c:p.source_cold_k-273.15,source_return_c:p.source_return_k-273.15,primary_c:p.primary_inlet_c,
  source_state:phase?.request.coordinator_state??null,command:phase?{issued_s:phase.time_ns/1e9,path:phase.request.source_path,source_tank:phase.request.source_tank,load_tank:phase.request.load_tank,enable:phase.request.source_enable,valve:phase.request.source_valve}:null,
  A:p.tank_records.A.new_k.map(k=>k-273.15),B:p.tank_records.B.new_k.map(k=>k-273.15),cold_A_m3:p.tank_A_cold_m3,cold_B_m3:p.tank_B_cold_m3,
  rack_max_c:Math.max(...p.unit_records.flatMap(u=>u.new_k.slice(1,7).map(k=>k-273.15)))};
});
const sourceEvents=result.source_timeline.map(e=>({t_s:e.time_ns/1e9,label:`源侧状态 ${e.from_state} → ${e.to_state}`,reason:e.reason,kind:'controller'}));let prior=null;
for(const f of sourceFrames){if(prior){for(const [key,label]of [['source_path','冷源实际路径'],['source_tank','源侧选罐'],['load_tank','负荷侧选罐']])if(f[key]!==prior[key])sourceEvents.push({t_s:f.t_s,label:`${label} ${prior[key]} → ${f[key]}`,kind:'physical',reason:'原始0.1秒POST记录，不是命令即生效'});}prior=f;}
sourceEvents.sort((a,b)=>a.t_s-b.t_s);
const source={run:'39088951176',case:'G_WET_LOSS',scope:'旧V2条件性V9替代方案的W1失效与W2接管，非当前00/01。W1/W2是旧研究冷源ID，A/B罐另行表示。',
 bindings:rawBindings,index_sha256:hash(path.join(sourceRoot,'artifact_hashes.json')),frames:sourceFrames,events:sourceEvents,summary:{peak_rack_inlet_c:result.maximum_inlet_c,temperature_verdict:'HISTORICAL_FAIL_45C'}};
const tankMetadata=read(path.join(here,'data/historical.json'));
if(tankMetadata.result_sha256!==rawBindings['result.json'])throw Error('TANK_METADATA_CASE_IDENTITY');
for(const k of ['tank_volume_m3','reference_c','rho','cp','cold_threshold_c'])source[k]=tankMetadata[k];
const cduRoot='D:/Github/Compute_to_Cooling_Digital_Test_Bench/artifacts/memphis-r12-dynamic-hydraulic-v1/reviewed-delivery',binding=read(path.join(here,'data/cdu_zip_bindings.json')),cases={};
for(const [id,label]of [['T2_COLD_STANDBY','冷态备用：受控 A→B 接管'],['T2_WARM_STANDBY','暖态备用：接管许可不成立'],['NEG_DUTY_PUMP_LOSS','运行泵失效：流量中断反例']]){
 const get=name=>{const p=path.join(cduRoot,id,name);if(hash(p)!==binding.files[id+'/'+name].sha256)throw Error('CDU_RAW_CHANGED '+id+'/'+name);return p;};
 const rows=fs.readFileSync(get('trace.ndjson'),'utf8').trim().split(/\r?\n/).map(JSON.parse),r=read(get('case_result.json'));
 cases[id]={run:binding.run,source:binding.source_commit,case:id,label,scope:'历史R12单六柜U1、CDU A→B、一次网A保持不变。U2/U3未计算；旧静压基准存在压力FAIL，非当前00/01结果。',
  bindings:{trace:binding.files[id+'/trace.ndjson'],result:binding.files[id+'/case_result.json'],zip_sha256:binding.official_zip_sha256},
  coverage:{unit:1,cdus:['G01-C01A','G01-C01B'],unmodeled:['G01-C02A','G01-C02B','G01-C03A','G01-C03B']},
  summary:r,events:r.events.map(e=>({t_s:e.t,label:`${e.old} → ${e.new}`,reason:e.reason})),
  frames:rows.map(row=>({t_s:row.post.t,state:row.state,master:row.post.master,cdus:row.post.cdus,racks:row.post.racks,valves:row.post.valves,speeds:row.post.speeds,command:{issued_s:row.t,...row.command},unit_flow_m3_h:row.post.unit_flow_m3_h}))};
}
const out={schema:'C2C-SWITCHING-REPLAY-1',scope:'READ_ONLY_HISTORICAL_SOURCE_AND_CDU_REPLAY_NOT_CURRENT_DESIGN',source,cdu_cases:cases,engineering_status:'MEMPHIS_ENGINEERING_NOT_APPROVED'};
fs.writeFileSync(path.join(here,'data/switching.json'),JSON.stringify(out));
console.log(JSON.stringify({source_frames:sourceFrames.length,cdu_cases:Object.keys(cases),cdu_frames:Object.fromEntries(Object.entries(cases).map(([id,d])=>[id,d.frames.length])),new_model_run:false}));
