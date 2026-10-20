// Presentation/packaging of already-saved official evidence. No model execution.
import {readFileSync,writeFileSync,mkdirSync,existsSync,cpSync,readdirSync} from 'node:fs';
import {resolve,join,basename} from 'node:path';
import {createInterface} from 'node:readline';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
const base=resolve(process.argv[2]),out=resolve(process.argv[3]);mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const save=(name,value)=>writeFileSync(join(out,name),JSON.stringify(value,null,2)+'\n');
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const byte=read(join(base,'independent_byte_review.json')),review=read(join(base,'independent_trace_review.json'));
const official=join(base,'official'),root=join(official,'artifacts','memphis-r12-dynamic-hydraulic-v1',byte.run+'-1');
const regPath=join(official,'v0_2','tests','tools','memphis_r12_dynamic_hydraulic_v1','registration.json');
const reg=read(regPath),caseData=[];
for(const stage of ['baseline','suite']){
  const d=join(root,stage,'delivery');if(!existsSync(d))continue;
  for(const sub of readdirSync(d,{withFileTypes:true}).filter(x=>x.isDirectory())){
    const dir=join(d,sub.name);cpSync(dir,join(out,sub.name),{recursive:true,errorOnExist:true,force:false});
    const full=existsSync(join(dir,'case_result.json'));const result=full?read(join(dir,'case_result.json')):null;
    const samples=[];let maxActiveGauge=0,maxActiveGaugeTime=null,maxReturn=0;
    for await(const line of createInterface({input:createReadStream(join(dir,'trace.ndjson')),crlfDelay:Infinity})){
      const row=JSON.parse(line),p=row.post,rs=Object.values(p.racks);
      for(const c of Object.values(p.cdus))if(c.primary_flow_m3_h>1&&c.secondary_flow_m3_h>1&&c.hx_inlet_gauge_difference_kPa>maxActiveGauge){maxActiveGauge=c.hx_inlet_gauge_difference_kPa;maxActiveGaugeTime=p.t;}
      maxReturn=Math.max(maxReturn,...rs.map(r=>r.return_C));
      samples.push({t:p.t,state:row.state,flow:Math.min(...rs.map(r=>r.flow_m3_h)),temp:Math.max(...rs.map(r=>r.supply_C)),
        return:Math.max(...rs.map(r=>r.return_C)),A:p.cdus.A.secondary_flow_m3_h,B:p.cdus.B.secondary_flow_m3_h});
    }
    caseData.push({id:sub.name,stage,complete:full,result,samples,maxActiveGauge,maxActiveGaugeTime,maxReturn});
  }
}
for(const name of ['independent_byte_review.json','independent_trace_review.json','github_run.json','github_artifacts.json'])cpSync(join(base,name),join(out,name));
cpSync(regPath,join(out,'registration.json'));
const normal=caseData.find(c=>c.id==='T2_COLD_STANDBY'),warm=caseData.find(c=>c.id==='T2_WARM_STANDBY'),lost=caseData.find(c=>c.id==='NEG_DUTY_PUMP_LOSS');
const coverage=reg.cases.map(c=>{
  const data=caseData.find(d=>d.id===c.id),r=data?.result;
  return {id:c.id,registration:c,status:!data?'NOT_EXECUTED':!r?'INVALID_NUMERICAL_MODEL_PREFIX_ONLY':'COMPLETE_60S_RESEARCH_MODEL_CASE',
    engineering_takeover:r?.takeover_verdict||null,
    negative_behavior:!r?'NOT_PROVEN':c.kind==='WARM_STANDBY'?(r.complete_at===null&&r.max_actual_overlap_s===0?'TEMPERATURE_PERMISSION_NOT_FORCED':'FAIL'):
      c.kind==='DUTY_PUMP_LOSS'?(r.min_rack_flow_m3_h===0?'FLOW_FAILURE_EXPOSED_NOT_A_CONTINUITY_PASS':'FAIL'):null};
});
const pressure={requirement_kPa:10,normal_max_all_states_kPa:normal.result.max_hx_inlet_gauge_difference_kPa,
  normal_max_when_both_sides_flow_kPa:normal.maxActiveGauge,at_s:normal.maxActiveGaugeTime,
  status:'FAIL_UNDER_REGISTERED_PRESSURE_REFERENCES_NOT_OEM_PERFORMANCE_PROOF',
  interpretation:'Primary and secondary static pressure/equalization policy is unclosed; do not tune offsets just to obtain PASS. Isolated trapped pressure is not modeled.'};
save('R12_T2_PHYSICAL_TAKEOVER_TESTS.json',{scope:reg.scope,engineering_status:reg.engineering_status,
  complete_cases:caseData.filter(c=>c.complete).map(c=>c.result),partial:review.invalid_partial_cases,not_executed:review.not_executed});
save('R12_DYNAMIC_NEGATIVE_TESTS.json',{status:'INCOMPLETE',coverage});
save('R12_PRESSURE_MASTER_TRANSFER.json',{scope:'ONE_UNIT_RESEARCH_CONTROLLER_NOT_FROZEN_M1',events:normal.result.events,
  five_second_stability:review.cases.find(c=>c.case==='T2_COLD_STANDBY').five_second_stability,
  max_actual_overlap_s:normal.result.max_actual_overlap_s,actual_master_count_max:1,actual_primary_B_valve_max:0});
save('R12_PID005_CONNECTIVITY_DECISION.json',{revision:'R12-PID005-006-VALIDATION-REV01',
  authoring_sha256:reg.topology_authoring_sha256,expanded_sha256:reg.topology_sha256,
  structural_decision:'EXPLICIT_PUMP_FILTER_HX_PATH_NO_UNFILTERED_OR_UNPUMPED_BYPASS',
  oem_or_construction_approved:false,dynamic_scope:'ONE_SIX_RACK_UNIT_ONLY'});
save('R12_DYNAMIC_MODEL_ADAPTER.json',{source_commit:byte.source_commit,scope:reg.scope,assumptions:reg.assumptions,
  capability_missing:reg.capability_missing,frozen_m1_modified:false,
  result:'PARTIAL_DYNAMIC_ADAPTER_EVIDENCE_NOT_FULL_VALIDATION',automatic_retries_stopped:true});
save('R12_MEASUREMENT_INTERFACE_MATRIX.json',{source:'RELEASED_MODELED_SENSOR_FRAMES_SAVED_IN_TRACE_NOT_FIELD_IO',
  sample_s:.1,release_delay_s:.1,lag_s:.2,max_age_s:.5,
  cdu_fields:['primary_flow_m3_h','primary_inlet_C','primary_outlet_C','primary_dp_kPa','secondary_flow_m3_h','secondary_hx_inlet_C','supply_C','secondary_dp_kPa','heat_W','speed','outlet_kPa_g','suction_kPa_g'],
  rack_fields:['flow_m3_h','supply_C','return_C','dp_kPa','A_supply_m3_h','B_supply_m3_h','A_return_m3_h','B_return_m3_h'],
  individual_valve_and_pump_feedback:'Saved each integration step',hardware_independence:'NOT_VERIFIED',
  P1_FT:'PROPOSED_REQUIRED_INTERFACE_NOT_ORIGINAL_INSTALLED_SENSOR',units_2_3:'NOT_DYNAMICALLY_VERIFIED'});
save('R12_OPEN_DESIGN_BLOCKERS.json',{engineering_status:reg.engineering_status,
  pressure,solver:{status:'BLOCKED_THREE_CANDIDATES_STOPPED',case:'NEG_EARLY_DUTY_EXIT',t_s:13.5,
    evidence:'Pump predicted zero flow while following check valve predicted0.000637626m3/s; KCL residual0.033574 at PM1 outlet, so trial step was rejected.',
    questionable_assumption:'Clipped one-way pump/check algebraic flow laws handled by plain nodal Newton across zero-speed/complementarity transitions. Needs solver-method review, not a larger budget or relaxed conservation.'},
  warm_standby:'46C spare cannot obtain <=2K match; no secondary-flow standby cooling path validated.',
  hard_pump_loss:'Diagnostic controlled handover does not cover sudden loss of duty pumping;50s modeled zero-flow in60s case.',
  vendor_data:['Q-H/efficiency/NPSHr and response','filter clean/blocked dp','valve Kv/Cv and travel','fouled HX UA/dp','sensor accuracy and actual IO chains'],
  long_run:'NOT_ADMITTED_OR_REQUESTED; first close solver, absolute pressure and failure-coverage issues'});
const observed=[];
for(const stage of ['baseline','suite']){
  const d=join(root,stage);if(!existsSync(d))continue;
  const heartbeats=readdirSync(d).filter(n=>n.startsWith('job_start.json.heartbeat-')).map(n=>read(join(d,n)));
  observed.push({stage,pid:byte.stages.find(s=>s.stage===stage).actual_python_pid,
    peak_job_bytes_observed_in_heartbeats:Math.max(...heartbeats.map(h=>h.peak_job_memory_bytes)),
    last_heartbeat:heartbeats.at(-1),note:'Heartbeat observation, not a claim to have captured final lifetime peak. Limits and cleanup independently verified.'});
}
save('R12_SOURCE_INPUT_ENVIRONMENT_HASH_MANIFEST.json',{source_commit:byte.source_commit,registration_raw_sha256:hash(regPath),
  topology_raw_sha256:reg.topology_sha256,authoring_sha256:reg.topology_authoring_sha256,
  source_manifest_sha256:byte.source_manifest_sha256,source_zip_sha256:byte.source_zip_sha256,
  official_zip_sha256:byte.official_zip_sha256,raw_logs_sha256:byte.raw_logs_sha256,
  native_jobs:byte.stages.map(s=>({stage:s.stage,pid:s.actual_python_pid,environment:s.environment,job:s.job})),observed,
  no_local_model_execution:true,formal_c3c:false,hardware:false,phase6:false});
const md=`# R12 单六柜短程动态接管 V1 · 部分完成，工程不批准

日期：2026-10-21（新加坡）。源码：\`${byte.source_commit}\`。运行：[${byte.run}](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/${byte.run})。GitHub整轮FAIL；不能用基线执行PASS覆盖整轮失败。

## 已完成与未完成

- 13个登记案例：3个完整60s案例、1个13.5s数值失效前缀、9个未执行。0.1s时间步，每个完整案例600步；失败后未继续补跑或增加预算。
- 冷态备用/诊断告警后受控接管：10s告警注入，10.2s进入准备；12.8–17.8s匹配稳定5s；17.8s开始重叠；29.7s备用实际建流后撤销旧主站；32.9s获旧泵零速证明；35.0s旧路隔离后授予新主站；35.2s接管完成。实际阀位重叠17.0s。
- 故障后最小单柜流量 **${normal.result.min_rack_flow_m3_h.toFixed(6)}m³/h**（门槛11.395），单元最小 **${normal.result.min_unit_flow_m3_h.toFixed(6)}m³/h**（门槛68.37）；最高机柜入口 **${normal.result.max_rack_inlet_C.toFixed(6)}°C**。0.1s采样的近零流量累计0s、流量亏缺0m³；不等于证明亚时间步无断流或无水锤。
- **该基线仍不是工程PASS**：板换一次/二次入口表压差最大 **${pressure.normal_max_all_states_kPa.toFixed(6)}kPa**，两侧均有流时最大 **${pressure.normal_max_when_both_sides_flow_kPa.toFixed(6)}kPa**（${pressure.at_s}s），超过10kPa要求。数值依赖本轮未标定静压基准，不是对真实设备的测量；不得只调静压偏置取PASS。两侧定压/均压及10kPa保护尚未闭环。

## 两个完整反例

46°C暖备用保持PREPARE_B，没有强行放行温差许可；运行A维持最小单柜${warm.result.min_rack_flow_m3_h.toFixed(6)}m³/h，最高入口${warm.result.max_rack_inlet_C.toFixed(6)}°C，但备用没有接管。不能将“备用泵转起来”当成“已预冷可接管”。

运行泵突然失效：模型出现 **50s零流量**，流量亏缺 **${lost.result.flow_deficit_volume_m3.toFixed(6)}m³**，接管INCOMPLETE。停滞入口液体未超过45°C并不证明冷却正常；热仍积累在回液/机柜控制体，最高机柜出口${lost.maxReturn.toFixed(3)}°C，且没有GPU die模型。受控诊断交接不能推广成突然失泵连续供冷PASS。

## 数值阻塞与停止

旧泵过早退出案例在13.5s、PREPARE_B阶段失效。试算泵流量截断为0，止回阀仍算出0.000637626m³/s，导致PM1出口KCL相对残差0.033574，超过原1e-6容差，试算步被拒绝。它是求解器在低速/止回互补条件切换处的失效，不是现场流量结论。未放宽容差、未加旁通、未删负荷。三个候选后已停止自动修复，未启动第四轮。

## 九项答复

1. PID-005原贯通线歧义在本次过程验证修订JSON中已消除；原R12不改，不等于厂家内部结构或施工审批。
2. 压力主站交接接口在冷态诊断告警案例可执行；单主站、旧泵零速/旧路隔离后授予B有保存证据，异常域覆盖未完成。
3. CDU B在一次A不变的边界下完成动态建流；一次B阀实际开度始终0。源泵/冷塔/储罐没有动态验证，不能由此宣称B罐真实放冷或冷源能力合格。
4. 本单元6柜各有独立求解流量、温度和压差记录；未用总量除6。其余12柜只登记结构，NOT_DYNAMICALLY_VERIFIED。
5. 冷态基线未见0.1s采样断流；突然失泵反例有50s零流量；低速退出案例数值INVALID，不能外推。
6. 泵曲线/效率、UA、阻力/Kv、液体库存、初态备用40°C、一次37°C边界、静压基准、泵阀/仪表动态均为研究假设。不是41°C一次热端或完整气象包络验证。
7. 厂家泵、过滤器、阀门、HX、测量链、静压/均压设计及瞬态/水锤/空化资料仍阻塞工程认可；源侧、罐与M1集成也未完成。
8. 已完成首轮独立短程研究验证，但**不能批准该适配器覆盖全异常域**；先审查互补求解与静压/10kPa保护，再进入新的短程候选。
9. **不进入、不申请1800s长程预算**。当前阻塞不是480s耗尽；增预算不能修复求解和安全约束。

## 独立核验与身份

官方ZIP、raw日志、source snapshot及manifest已核验；3个完整案例共1800步独立复算质量、换热和能量；3个完整案例账本一致不等于工程要求通过。冷态基线最大单步能量误差0.000728716J，累计误差0.0523103J；HX两侧热量最大差5.82e-10W；单柜节点最大质量差6.23e-6m³/h。实际Python PID7312/5208，CPU25%、256/512MiB、480s，cleanup=true、active0；非正式M1环境。

源码manifest：\`${byte.source_manifest_sha256}\`

官方ZIP：\`${byte.official_zip_sha256}\`

raw日志：\`${byte.raw_logs_sha256}\`

展开JSON：\`${reg.topology_sha256}\`

Build001 run39491851591、Build002 run39492422095的失败源码、ZIP及日志保留，不借旧PASS；Build003也保持原结果不修改。

**MEMPHIS_ENGINEERING_NOT_APPROVED**。未改冻结M1，未正式C3-C、未合并/发版、未真实硬件、未生产、未Phase6。下一步是求解方法/静压保护审查，不是扩大柜数或重新调容量。
`;
writeFileSync(join(out,'R12_DYNAMIC_ADMISSION_REPORT_ZH.md'),md);
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function plot(rows,keys,limit,title){
  const cols=['#087f8c','#ea6b27','#5570b0'],width=1000,left=70,right=965,top=40,bottom=240;
  let values=rows.flatMap(r=>keys.map(k=>r[k]));if(limit!==null)values.push(limit);
  let lo=Math.min(...values),hi=Math.max(...values),pad=Math.max(1,(hi-lo)*.12);lo-=pad;hi+=pad;
  const xy=(t,v)=>[left+(right-left)*t/60,bottom-(bottom-top)*(v-lo)/(hi-lo)];
  let s=`<svg viewBox="0 0 ${width} 280" role="img"><text x="20" y="24">${esc(title)}</text>`;
  for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4,y=xy(0,v)[1];s+=`<path d="M${left} ${y}H${right}" stroke="#dde5ee"/><text x="5" y="${y+5}" font-size="13">${v.toFixed(2)}</text>`;}
  if(limit!==null){const y=xy(0,limit)[1];s+=`<path d="M${left} ${y}H${right}" stroke="#b42330" stroke-dasharray="7 4"/>`;}
  keys.forEach((k,i)=>s+=`<polyline points="${rows.map(r=>xy(r.t,r[k]).map(v=>v.toFixed(2)).join(',')).join(' ')}" fill="none" stroke="${cols[i]}" stroke-width="2.4"/>`);
  s+=`<text x="${left}" y="270">0s</text><text x="${right-30}" y="270">60s</text></svg>`;
  return s+'<p>'+keys.map((k,i)=>`<span style="color:${cols[i]}">${esc(k)}</span>`).join(' / ')+'</p>';
}
let h=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R12 短程动态接管 · 部分结果与阻塞</title><style>body{margin:0;background:#eff4f9;color:#17324f;font:16px/1.7 'Microsoft YaHei',sans-serif}main{max-width:1120px;margin:auto;padding:28px}section{background:white;border:1px solid #dbe5ef;border-radius:14px;margin:20px 0;padding:24px}h1{font-size:28px}h2{font-size:22px}.warn{background:#fff1dc;border-left:5px solid #df8722;padding:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{padding:18px;border:1px solid #dbe5ef;border-radius:10px;background:white}.num{font-size:27px;font-weight:700}svg{width:100%;font:15px sans-serif;fill:#3c5670}table{width:100%;border-collapse:collapse;font-size:14px}td,th{border:1px solid #dbe5ef;padding:10px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.8 'Microsoft YaHei',sans-serif}a{color:#006e94}@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:14px}}</style><main><h1>R12 单六柜 · 动态接管部分验证与失败边界</h1><p>输入JSON → 实际泵阀反馈 → 逐机柜水力/热量 → 已保存的PRE/POST证据；不是实时设备画面。</p><p class="warn"><b>整轮FAIL / MEMPHIS_ENGINEERING_NOT_APPROVED</b><br>3个完整案例、1个数值INVALID前缀、9个未执行。禁止把冷态基线的温度/流量PASS写成工程PASS。</p><div class="grid"><div class="card">冷态基线接管完成<div class="num">35.2 s</div>一次A不变；受控诊断告警</div><div class="card">冷态基线最小单柜流量<div class="num">11.623 m³/h</div>门槛11.395；单元69.737</div><div class="card">冷态基线最高入口<div class="num">39.611 °C</div>37°C一次边界、40°C初态备用</div></div><section><h2>不能批准的两个P0</h2><p><b>静压/保护未闭环：</b>板换入口表压差最大${pressure.normal_max_all_states_kPa.toFixed(3)}kPa，超过10kPa；两侧均有流时仍达到${pressure.normal_max_when_both_sides_flow_kPa.toFixed(3)}kPa。数值依赖研究参考压，不是现场测量；不能靠调整偏置取PASS。</p><p><b>低速/止回互补求解未通过：</b>旧泵过早退出案例13.5s失效，KCL相对残差0.033574（容差1e-6），试算步已拒绝。第三候选后停止自动修复；这不是证明现场会按该失效值运行。</p></section><section><h2>场景覆盖</h2><table><tr><th>登记案例</th><th>执行状态</th><th>接管</th></tr>`;
for(const c of coverage)h+=`<tr><td>${esc(c.id)}</td><td>${esc(c.status)}</td><td>${esc(c.engineering_takeover||'NOT_PROVEN')}</td></tr>`;
h+='</table></section>';
for(const c of caseData){
 h+=`<section><h2>${esc(c.id)}</h2><p>${c.complete?'完整60s模型记录':'仅13.5s失效前缀，不能形成完整场景结论'}；${c.result?'接管 '+c.result.takeover_verdict:''}</p>`;
 if(c.id==='NEG_DUTY_PUMP_LOSS')h+='<p class="warn">50秒零流量。停滞入口液体仍低于45°C，不代表有连续冷却；应结合流量、回液储热与负载判断。</p>';
 h+=plot(c.samples,['flow'],11.395,'六柜中最小单柜流量 · m³/h');
 h+=plot(c.samples,['temp','return'],45,'最高机柜入口 / 出口温度 · °C');
 h+=plot(c.samples,['A','B'],null,'CDU A / B实际二次流量 · m³/h');
 if(c.result)h+='<h3>事件时间轴</h3><pre>'+esc(JSON.stringify(c.result.events,null,2))+'</pre>';
 h+=`<p><a href="${c.id}/trace.ndjson">原始PRE/命令/POST</a>`+(c.result?` · <a href="${c.id}/racks.csv">每柜CSV</a> · <a href="${c.id}/energy.csv">能量账本</a> · <a href="${c.id}/case_result.json">原始判定</a>`:` · <a href="${c.id}/numerical_failure.json">数值失败诊断</a>`)+`</p></section>`;
}
h+='<section><h2>完整中文准入报告与九项答复</h2><pre>'+esc(md)+'</pre></section><p><a href="independent_trace_review.json">独立逐步复算</a> · <a href="R12_SOURCE_INPUT_ENVIRONMENT_HASH_MANIFEST.json">源码/输入/环境身份</a> · <a href="registration.json">全部研究假设</a></p></main></html>';
writeFileSync(join(out,'engineering_report.html'),h);
save('delivery_hashes.json',{scope:'POST_REVIEW_DELIVERY_NOT_MODEL_REEXECUTION',run:byte.run,source_commit:byte.source_commit,
  files:readdirSync(out).filter(n=>!['delivery_hashes.json'].includes(n)&&!readdirSync(out,{withFileTypes:true}).find(d=>d.name===n).isDirectory()).map(file=>({file,sha256:hash(join(out,file))}))});
console.log(JSON.stringify({delivery:out,complete:caseData.filter(c=>c.complete).length,partial:caseData.filter(c=>!c.complete).length,
  not_executed:review.not_executed.length,pressure,manifest_sha256:hash(join(out,'delivery_hashes.json')),engineering_status:reg.engineering_status},null,2));
