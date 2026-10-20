// Read-only evidence arithmetic and report packaging. Never imports a model.
import {readFileSync,writeFileSync,mkdirSync,readdirSync,cpSync,existsSync} from 'node:fs';
import {join,resolve,relative} from 'node:path';
import {createHash} from 'node:crypto';
const repo=resolve(process.argv[2]),base=resolve(process.argv[3]),out=resolve(process.argv[4]);
const ns='memphis_r12_solver_pressure_safety_v1',art='memphis-r12-solver-pressure-safety-v1';
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const write=(name,value)=>writeFileSync(join(out,name),typeof value==='string'?value:JSON.stringify(value,null,2)+'\n');
const cell=x=>'"'+String(x??'').replaceAll('"','""')+'"';
const csv=(name,rows)=>{const keys=[...new Set(rows.flatMap(Object.keys))];write(name,'\uFEFF'+keys.map(cell).join(',')+'\n'+rows.map(r=>keys.map(k=>cell(typeof r[k]==='object'?JSON.stringify(r[k]):r[k]??'')).join(',')).join('\n')+'\n');};
const check=(yes,why)=>{if(!yes)throw Error(why);};
mkdirSync(out,{recursive:true});
const byte=read(join(base,'independent_byte_review.json')),tr=read(join(base,'independent_trace_review.json'));
check(tr.status==='EVIDENCE_CONSISTENT_NOT_ENGINEERING_APPROVED','TRACE_REVIEW_NOT_COMPLETE');
const runtime=join(byte.official_root,'artifacts',art,byte.run+'-1');
const src=join(repo,'v0_2/tests/tools',ns);
const reg=read(join(repo,'v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1/registration.json'));
const basis=read(join(src,'basis_reconciliation.json')),authority=read(join(src,'design_basis.json'));
const manifest=read(join(src,'source_manifest.json'));
check(hash(join(src,'source_manifest.json'))===byte.source_manifest_sha256,'LOCAL_SOURCE_IDENTITY');
const math=read(join(runtime,'suite/delivery/math/tests.json'));
check(math.length===28&&math.every(r=>r.test_pass),'MATHEMATICAL_COVERAGE');
const mathReview=[];
for(const r of math){
 if(!r.flows_m3_s)continue;
 const [p1,c1,p2,c2,q]=r.flows_m3_s;
 const kcl=Math.max(Math.abs(p1-c1),Math.abs(p2-c2),Math.abs(c1+c2-q))/.02;
 const s=r.load_K*q*q,loadHead=q*Math.sqrt(r.load_K*(s+Math.sqrt(s*s+.04))/2);
 const errors=[];
 if(p1>1e-8)errors.push(Math.abs(r.heads_Pa[0]-1e8*p1*p1-1e6*c1*c1-loadHead));
 if(p2>1e-8)errors.push(Math.abs(r.heads_Pa[1]-1e8*p2*p2-1e6*c2*c2-loadHead));
 const maxHead=Math.max(0,...errors);
 check(kcl<1e-6&&maxHead<.001&&Math.min(p1,c1,p2,c2)>-1e-12,'INDEPENDENT_MATH '+r.test);
 mathReview.push({test:r.test,KCL_relative:kcl,open_loop_head_residual_Pa:maxHead});
}
write('07_COMPLEMENTARITY_SOLVER_TESTS.json',{scope:'A_L_PLUS_FROZEN_REJECTED_TRIAL',cases:math,independent_flow_and_head_checks:mathReview,
 infeasible_case_meaning:'Expected refusal is a passing negative test, NOT a hydraulic feasibility PASS.',
 timing_note:'Windows monotonic clock resolution can report 0 for sub-tick solves; not zero computational cost.'});
const cases=[];
for(const stage of ['baseline','suite']){
 const d=join(runtime,stage,'delivery');
 for(const item of readdirSync(d,{withFileTypes:true}).filter(e=>e.isDirectory()&&e.name!=='math')){
  const dir=join(d,item.name);if(!existsSync(join(dir,'trace.ndjson')))continue;
  const rows=readFileSync(join(dir,'trace.ndjson'),'utf8').trim().split('\n').map(JSON.parse);
  const result=existsSync(join(dir,'case_result.json'))?read(join(dir,'case_result.json')):null;
  const samples=rows.map(r=>({t:r.post.t,state:r.state,flow:Math.min(...Object.values(r.post.racks).map(x=>x.flow_m3_h)),
    inlet:Math.max(...Object.values(r.post.racks).map(x=>x.supply_C)),outlet:Math.max(...Object.values(r.post.racks).map(x=>x.return_C)),
    dp:Math.max(...Object.values(r.post.cdus).map(x=>x.hx_inlet_gauge_difference_kPa)),
    speed:r.post.speeds['G01-C01A-P2-PM1']}));
  cases.push({stage,id:item.name,dir,rows,result,samples});
 }
}
const get=(id,stage='suite')=>cases.find(c=>c.id===id&&c.stage===stage);
const cold=get('T2_COLD_STANDBY'),lost=get('NEG_DUTY_PUMP_LOSS'),early=get('NEG_EARLY_DUTY_EXIT'),protect=get('PRESSURE_PROTECTED_COLD');
const pressureRows=[],earlyRows=[],lostRows=[],protectionRows=[],independent=[];
let maxDP=null,maxDynamicKCL=0,maxEqPressure=0,maxComp=0,minForward=0,nonuniqueSteps=0;
for(const c of cases.filter(c=>c.stage==='suite')){
 let qHeadError=0,pressureMappingError=0;
 for(const r of c.rows){
  for(const [side,p] of Object.entries(r.post.cdus)){
   const delta=p.P1_IN_kPa_g-p.P2_IN_kPa_g;
   pressureMappingError=Math.max(pressureMappingError,Math.abs(Math.abs(delta)-p.hx_inlet_gauge_difference_kPa));
   const entry={case:c.id,t:r.post.t,state:r.state,cdu:side,
    P1_IN_kPa_g:p.P1_IN_kPa_g,P1_OUT_kPa_g:p.P1_OUT_kPa_g,P2_IN_kPa_g:p.P2_IN_kPa_g,P2_OUT_kPa_g:p.P2_OUT_kPa_g,
    signed_cross_kPa:delta,abs_cross_kPa:Math.abs(delta),limit_kPa:10,reference_difference_kPa:65,
    primary_relative_to_reference_kPa:p.P1_IN_kPa_g-165,secondary_relative_to_reference_kPa:p.P2_IN_kPa_g-100,
    pump_in_kPa_g:p.pump_in_kPa_g,pump_out_kPa_g:p.pump_out_kPa_g,filter_in_kPa_g:p.filter_in_kPa_g,filter_out_kPa_g:p.filter_out_kPa_g,
    primary_flow_m3_h:p.primary_flow_m3_h,secondary_flow_m3_h:p.secondary_flow_m3_h,
    pressure_interpretation:'RESEARCH_COMMON_DATUM_NO_TRAPPED_PRESSURE_COMPLIANCE_OR_ELEVATION_PROOF'};
   pressureRows.push(entry);
   if(c===cold&&p.primary_flow_m3_h>1&&p.secondary_flow_m3_h>1&&(!maxDP||entry.abs_cross_kPa>maxDP.abs_cross_kPa))maxDP=entry;
   if(p.primary_flow_m3_h>1)qHeadError=Math.max(qHeadError,Math.abs((p.P1_IN_kPa_g-p.P1_OUT_kPa_g)*1000-130000*(p.primary_flow_m3_h/110)**2));
   if(p.secondary_flow_m3_h>1)qHeadError=Math.max(qHeadError,Math.abs((p.P2_IN_kPa_g-p.P2_OUT_kPa_g)*1000-172180*(p.secondary_flow_m3_h/68.37)**2));
  }
  for(const st of Object.values(r.post.solver)){
   maxDynamicKCL=Math.max(maxDynamicKCL,st.kcl_max);maxEqPressure=Math.max(maxEqPressure,st.pressure_residual_Pa);
   maxComp=Math.max(maxComp,st.complementarity_residual);minForward=Math.min(minForward,st.min_forward_scaled_flow);
   if(st.pressure_nonunique)nonuniqueSteps++;
   check(st.status==='CONVERGED'&&st.kcl_max<1e-6&&!st.physical_violation,'DYNAMIC_SOLVER');
  }
  const m=r.released_measurements;
  const detail={t:r.post.t,state:r.state,master:r.post.master,pumpA:r.post.speeds['G01-C01A-P2-PM1'],pumpB:r.post.speeds['G01-C01B-P2-PM1'],
   min_rack_flow_m3_h:Math.min(...Object.values(r.post.racks).map(x=>x.flow_m3_h)),unit_m3_h:r.post.unit_flow_m3_h,
   inlet_C:Math.max(...Object.values(r.post.racks).map(x=>x.supply_C)),outlet_C:Math.max(...Object.values(r.post.racks).map(x=>x.return_C)),
   mass_residual:r.post.secondary_mass_residual,primary_A_valve:r.post.valves['G01-C01A-P1-CV-AS'],
   measured_at:m?.sampled_at??null,released_at:m?.release_at??null,
   measured_cross_A_kPa:m?Math.abs(m.cdus.A.P1_IN_kPa_g-m.cdus.A.P2_IN_kPa_g):null,
   actual_cross_A_kPa:r.post.cdus.A.hx_inlet_gauge_difference_kPa,command:r.command};
  if(c===early)earlyRows.push(detail);
  if(c===lost)lostRows.push(detail);
  if(c===protect){
   if(r.state==='PRESSURE_FAIL_STOP'){
    check(m&&m.sampled_at<=m.release_at&&m.release_at<=r.t+1e-8,'PROTECTION_FUTURE_FRAME');
    check(r.command.master===null&&Object.values(r.command.speeds).every(x=>x===0),'PROTECTION_STOP_COMMAND');
   }
   protectionRows.push(detail);
  }
 }
 check(pressureMappingError<1e-8&&qHeadError<.001,'PRESSURE_MAPPING_OR_LOSS_LAW');
 independent.push({case:c.id,pressure_tap_mapping_error_kPa:pressureMappingError,HX_loss_law_error_Pa:qHeadError});
}
csv('04_HX_DIFFERENTIAL_PRESSURE_RESULTS.csv',pressureRows);csv('09_NEG_EARLY_EXIT_REPLAY.csv',earlyRows);
csv('11_SUDDEN_PUMP_LOSS_RETEST.csv',lostRows);csv('12_PROTECTION_RESPONSE_TIMELINE.csv',protectionRows);
csv('10_T2_BASELINE_BEFORE_AFTER.csv',cases.map(c=>({case:c.id,stage:c.stage,steps:c.rows.length,
 execution:c.result?'COMPLETE_60S':'INVALID_AT_13_5S',takeover_at:c.result?.complete_at,
 min_rack_flow_m3_h:c.result?.min_rack_flow_m3_h,inlet_C:c.result?.max_rack_inlet_C,
 maximum_outlet_C:Math.max(...c.samples.map(x=>x.outlet)),flow_deficit_m3:c.result?.flow_deficit_volume_m3,
 zero_duration_registered_window_s:c.result?.near_zero_flow_duration_s,pressure_verdict:c.result?.hx_pressure_verdict})));
csv('03_STATIC_PRESSURE_MODEL_AUDIT.csv',basis.rows);
const graph=read(join(repo,'v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1/inputs/pid.expanded.json'));
write('02_PRESSURE_PORT_MAPPING.json',{definition_source:'00 B146/B168',absolute_pressure_Pa:null,atmospheric_pressure_Pa:null,
 elevations_m:null,hydrostatic_correction:'NOT_REGISTERED_SAME_DATUM_RESEARCH_ASSUMPTION',dynamic_velocity_pressure:'NOT_MODELED_NO_REGISTERED_PIPE_GEOMETRY',
 primary_reference_kPa_g:165,secondary_reference_kPa_g:100,
 sensors:graph.sensors.filter(s=>['G01-C01A','G01-C01B'].includes(s.parent)&&['PT','PDT'].includes(s.symbol)).map(s=>({
  id:s.id,tap:s.tap_port,low_tap:s.low_tap_port,source:s.source_refs,hardware_status:s.hardware_independence})),
 virtual_diagnostic_taps:['HX:P1-IN','HX:P1-OUT','HX:P2-IN','HX:P2-OUT','P2-PM1:IN','P2-PM1:OUT','P2-F01:IN','P2-F01:OUT'],
 diagnostic_warning:'Pump flange and filter body virtual taps are NOT identical to common PT-SUC/PT-DIS/filter-PDT taps across isolation/check valves.',
 overlap_permission:'HX secondary outlet A versus B, not cross-media 10 kPa',pressure_measurement_error_budget:null});
const trip=protect.rows.find(r=>r.state==='PRESSURE_FAIL_STOP'),stopped=protect.rows.find(r=>Object.values(r.post.speeds).every(n=>Math.abs(n)<.001));
const isolated=protect.rows.find(r=>r.post.valves['G01-C01A-P1-CV-AS']<.001),terminal=protect.rows.at(-1);
const statuses={
 NUMERICAL_SOLVER_STATUS:'BOUNDED_MATHEMATICAL_AND_FOUR_CASE_REGRESSION_VALIDATED',
 PRESSURE_REQUIREMENT_STATUS:'10_KPA_CONFIRMED_00_01_IMPLEMENTATION_CLARIFICATION_REQUIRED',
 PRESSURE_PROTECTION_STATUS:'MEASURED_TRIP_AND_ACTUATION_VERIFIED_SAFE_PRESSURE_STATE_NOT_PROVEN',
 CONTROLLED_TAKEOVER_STATUS:'RESEARCH_ORIGINAL_CONTROL_THERMAL_FLOW_PASS_HX_PRESSURE_FAIL',
 SUDDEN_FAILURE_CONTINUITY_STATUS:'PHYSICAL_CONTINUITY_FAILURE_IN_RESEARCH_MODEL',
 MODEL_VALIDITY_STATUS:'CONDITIONAL_RESEARCH_NOT_FINAL_00_01_DESIGN_VALIDATION',
 OEM_CALIBRATION_STATUS:'CALIBRATION_REQUIRED',ENGINEERING_APPROVAL_STATUS:'MEMPHIS_ENGINEERING_NOT_APPROVED'};
const stats={...statuses,scope_decision:basis.scope_decision,source_commit:byte.source_commit,run:byte.run,
 math_subcases:math.length,mathematical_feasible_converged:math.filter(r=>r.metrics.status==='CONVERGED').length,
 expected_infeasible:math.filter(r=>r.metrics.status==='PHYSICAL_INFEASIBLE').length,
 independent_math_checks:mathReview,independent_pressure_checks:independent,max_dynamic_KCL:maxDynamicKCL,
 max_dynamic_equation_residual_Pa:maxEqPressure,max_dynamic_complementarity:maxComp,
 minimum_forward_scaled_flow_raw:minForward,numerical_roundoff_note:'Tiny signed roundoff retained without clipping; not a physical reverse-flow interpretation.',
 nonunique_pressure_solve_records:nonuniqueSteps,rank_null_interpretation:'NOT_ASSESSED_THIS_STEP_NOT_PROOF_OF_UNIQUENESS',
 pressure_peak_breakdown:maxDP,protection:{trip_decision_s:trip.t,source_sample_s:trip.released_measurements.sampled_at,
 release_s:trip.released_measurements.release_at,actual_pumps_stopped_post_s:stopped.post.t,actual_primary_isolated_post_s:isolated.post.t,
 terminal_model_cross_dp_kPa:terminal.post.cdus.A.hx_inlet_gauge_difference_kPa,
 terminal_pressure_meaning:'65 kPa reference arithmetic in isolated zones, NOT a physical trapped-pressure prediction',
 full_window_near_zero_sampled_duration_s:protect.samples.filter(x=>x.flow<.001).length*.1},
 original_reproduction_first_run:'39495584820 expected failure did not recur; assertion FAIL preserved',
 original_reproduction_current_run:'39497147240 cold pressure reproduced and early-exit failure recurred at13.5s',
 extension_18_racks_or_1800_s:false};
write('13_NUMERICAL_AND_PHYSICAL_STATUS.json',stats);
write('independent_hydraulic_review.json',{scope:'SAVED_EVIDENCE_ARITHMETIC_ONLY',...stats});
write('08_HYDRAULIC_SOLVER_PATCH_REPORT.md',`# 求解器修改与实际差异

执行源码 ${byte.source_commit}，run${byte.run}。仅新研究命名空间；旧模型、冻结M1及00/01原件不变。
先原样执行旧算法。本轮13.5s失败复现，并保存最后有效步、被拒试算、Jacobian、节点/分支、阀泵状态与残差。
此前复现run39495584820同源码旧算法曾完成早退案例，说明该失败对数值路径敏感；失败断言及原证据保留，不伪造每次必现。

旧算法逐边截断前向流量，零流量处导数为零，Newton局部方程失去可用方向；泵零流量和串联止回正流量不满足KCL。
新算法联合求解压力、分支流量与互补条件，精确保留原被动损失律及其0.1Pa平滑，见05方程说明。
28项子案例中27项收敛、1项预期物理无解被拒；该拒绝不是可行工况PASS。
历史拒绝状态重新求解KCL为${math.at(-1).metrics.kcl_max}，原为0.033574007。
新算法五个60s案例全部完成；冷态接管35.2→35.3s，匹配许可17.8→17.9s，仍是原0.1s物理步长。
更严格残差改变了临界测量落在哪一采样步；未强制锁旧事件时间，温度及流量差异全部保留。

原研究参数与00/01差异见03及basis_reconciliation.json。不得将172.18改26.60或调静压直接取PASS。
隔离压力非唯一、无压力容性和泄压物理设备，故保护动作正确不等于恢复安全压差。
`);
const baselineCopy=['01_PRESSURE_REQUIREMENT_PROVENANCE.md','05_PUMP_CHECK_VALVE_EQUATIONS.md','basis_reconciliation.json','design_basis.json'];
for(const n of baselineCopy)cpSync(join(src,n),join(out,n));
write('06_SOLVER_FAILURE_REPRODUCER.py',`"""Remote controlled entry only. Actual reproduction implementation is in source/.
Run through source/v0_2/tests/tools/${ns}/run_remote.ps1 -Stage baseline.
The imported worker refuses local/non-Job execution before importing NumPy.
"""
from v0_2.tests.tools.${ns}.worker import main
if __name__ == "__main__":
    raise SystemExit(main())
`);
const report=`# 孟菲斯最终设计依据核对与求解器修复结果

日期：2026年10月21日，新加坡。工程总状态：**MEMPHIS_ENGINEERING_NOT_APPROVED**。
最终设计依据仍为00/01，R12只作过程参考。本轮完成20项映射及原研究模型的数值对照，没有把它重标为00/01完整动态验收。
执行：[run${byte.run}](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/${byte.run})；源码：${byte.source_commit}。

## 最重要的四个结果

| 项目 | 原算法 | 新算法 | 工程解释 |
|---|---:|---:|---|
| 冷态接管完成 | 35.2s | ${cold.result.complete_at}s | 原控制研究工况，非最终设计全域 |
| 最低单柜流量 | 11.622904 | ${cold.result.min_rack_flow_m3_h.toFixed(6)}m³/h | 温度/流量门槛仍满足 |
| 最高机柜入口 | 39.611420 | ${cold.result.max_rack_inlet_C.toFixed(6)}°C | 固定37°C一次边界，不是41°C热端验证 |
| 早退案例 | 13.5s数值INVALID | 完整60s，${early.result.near_zero_flow_duration_s.toFixed(1)}s近零流量 | 数值问题修复后暴露物理连续供冷失败 |

突然失泵仍有50.0s近零流量、0.949583m³亏缺，最高机柜出口${Math.max(...lost.samples.map(x=>x.outlet)).toFixed(3)}°C。入口未超45°C不意味着停流机柜仍安全，GPU die未建模。

## 00/01与当前模型对照

| 核查项目 | 00/01最终依据 | 当前研究模型 | 处理 |
|---|---|---|---|
${basis.rows.map(r=>'|'+[r.item,r.final_00_01,r.current_model,r.required_action].map(x=>x.replaceAll('|','/')).join('|')+'|').join('\n')}

## 十四项答复

1. **10kPa测点**：00 B146/B168，板换一次入口对二次入口的表压差绝对值；不是单侧压损或板片各位置差压。5kPa是另一个R12研究并流许可。
2. **192.412kPa来源**：本轮B侧30.5s一次入口${maxDP.P1_IN_kPa_g.toFixed(6)}、二次入口${maxDP.P2_IN_kPa_g.toFixed(6)}kPa(g)。有符号差=65+${maxDP.primary_relative_to_reference_kPa.toFixed(6)}−${maxDP.secondary_relative_to_reference_kPa.toFixed(6)}=−${maxDP.abs_cross_kPa.toFixed(6)}kPa。65为参考差，其余来自研究泵压和阻力分配。不是只由静压偏置造成。
3. **问题归属**：研究边界及分段阻力不对应最终设计；原控制也没有跨侧压差保护。00/01实际定压措施仍需深化，不能据该模型直接认定真实设计相同FAIL。
4. **13.5s为何失败**：逐边截断和零导数导致局部Newton停滞；泵与止回未能同时满足节点守恒。本轮原算法复现原残差0.033574。
5. **新约束收敛**：A–L及历史拒绝状态共28项检查，27项可行收敛、1项无源净需求物理无解按预期拒绝；数学KCL最大4.62e−13，未放宽原1e−6。动态KCL最大${maxDynamicKCL.toExponential(3)}。微小负舍入数原样保留，不人为截断成零。
6. **旧泵早退可否算完**：能完成60s，但近零流量${early.result.near_zero_flow_duration_s.toFixed(1)}s、亏缺${early.result.flow_deficit_volume_m3.toFixed(6)}m³；接管仍未完成。
7. **受控接管**：原研究控制的冷态温度/流量仍PASS，17s重叠，接管35.3s，比原延后一个0.1s采样步；压差仍FAIL，不可总体PASS。
8. **保护实际响应**：独立研究停泵策略只读已释放压力，0.1s用0.0s采样/0.1s释放触发；3.8s实际泵停、5.9s一次阀隔离。最终参考差65kPa并未达到10kPa，且隔离压力无容性模型。只能确认命令及动作链，不能宣称安全状态已恢复；流量连续性FAIL。
9. **突然失泵**：反例原样保留，50s失流，不通过延迟故障、启动虚拟设备或删热量来修饰。
10. **数值错误**：原低速/止回切换的局部解法失效；不能把数值INVALID冒充真实水力FAIL。
11. **物理风险**：失泵失流、跨侧压差实现、单侧失压、隔离液体受压、共同接口和源侧储冷均未闭环。准稳态不证明无水锤。
12. **客户/OEM需确认**：逐件Kv/压损与标高、PG25全曲线/效率/NPSH、定压膨胀、HX最大允许差压及单侧失压、仪表误差/响应、失电阀位、独立保护。00的60/335.89kPa为初设示例，不是施工整定。
13. **下一轮单六柜**：可继续受控数值研究；要评价00/01设计，先在JSON中独立分配外管123.58、二次HX26.60、内部50及一次HX85.92kPa，并绑定真实压力接口。不得只替换常数取PASS。
14. **18柜/1800s**：本轮不进入。最终设计动态绑定、跨侧压差保护、突然失泵连续性、源/罐动态与长程预算仍阻塞；本轮没有新增授权。

## 独立复核与证据

官方ZIP逐字节SHA256与GitHub digest一致；raw索引、来源清单、实际Python Job及退出cleanup已回读。PID分别为${byte.stages.map(s=>s.actual_python_pid).join('/')}，CPU25%、256/512MiB、480s；两阶段模型耗时${byte.stages.map(s=>s.result.elapsed_s.toFixed(3)).join('/')}s，cleanup=true/active0。
8个完整60s记录共4800帧，另保留原13.5s无效前缀。已独立复算质量、HX两侧热、储能和总流量；数学流量和开启回路压差另行复算。没有借旧PASS。
原复现run39495584820未再次失败的事实及失败断言保留，本轮相同旧算法再次复现，说明旧低速解法对数值路径敏感，不能删掉其中一份。
保护报告的全窗近零流量为${stats.protection.full_window_near_zero_sampled_duration_s.toFixed(1)}s，旧通用摘要仅按10s故障窗统计，不把该摘要当保护触发后的全窗指标。

官方ZIP SHA256：${byte.official_zip_sha256}。
执行源码清单 SHA256：${byte.source_manifest_sha256}。
完整源/输入/原始证据和16号清单在本机交付包；Git专用分支保存报告、表格和清单，不自动合并、不发版、不正式C3-C、不运行硬件或Phase6。
`;
write('14_ENGINEERING_REPORT_ZH.md',report);
// Keep all exact runtime evidence and the complete source closure locally.
cpSync(runtime,join(out,'raw'),{recursive:true});
for(const r of manifest.source_files){
 let from=join(repo,r.path);
 if(r.path==='.github/workflows/ci.yml')from=join(src,'infra/ci-branch-only.yml');
 check(hash(from)===r.sha256,'SOURCE_CLOSURE '+r.path);
 const dest=join(out,'source',r.path);mkdirSync(resolve(dest,'..'),{recursive:true});cpSync(from,dest);
}
cpSync(join(src,'source_manifest.json'),join(out,'source_manifest.json'));
for(const name of ['independent_byte_review.json','independent_trace_review.json','github_artifacts.json','github_run.json'])cpSync(join(base,name),join(out,name));
const data={cases:cases.map(({stage,id,result,samples})=>({stage,id,result,samples})),basis:basis.rows,statuses,stats};
write('report_data.json',data);
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>孟菲斯 00/01依据与数值修复对照</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f7;color:#182e40;font:15px/1.65 "Microsoft YaHei",sans-serif}
main{max-width:1280px;margin:auto;padding:32px}h1{font-size:30px;margin:5px 0 12px}h2{font-size:22px}h3{font-size:17px}
.eyebrow{color:#526d7f;font-size:13px;letter-spacing:1px}.notice{padding:18px 22px;border-left:4px solid #b66327;background:#fff5e9}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}.card,section{background:white;border:1px solid #dce4ea;border-radius:12px;padding:22px;margin-bottom:22px}
.card{margin:0}.big{font-size:32px;font-weight:700;color:#126e76}.danger{color:#a3402b}
select,input,button{font:inherit;padding:9px 12px;border:1px solid #a7b9c7;border-radius:6px;background:white;color:inherit}
label{display:inline-block;margin:0 12px 12px 0}select{max-width:100%}input[type=range]{width:100%;padding:0}svg{width:100%;height:auto}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #dee6ec;padding:13px;text-align:left;vertical-align:top}th{background:#eef3f6;white-space:nowrap}
.muted{color:#587081}.legend{display:flex;gap:20px;flex-wrap:wrap}a{color:#086b83}.mono{font-family:Consolas,monospace;overflow-wrap:anywhere}
@media(max-width:760px){main{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:24px}.card,section{padding:16px}}
</style><main><div class="eyebrow">MEMPHIS · 00/01 FINAL DESIGN BASIS · OFFLINE RESEARCH</div>
<h1>设计依据已对齐，工程问题仍需闭环</h1>
<p class="notice">本页是原研究模型的算法前后对照，<strong>不是00/01完整动态验收</strong>。数值收敛不等于压力合格或连续供冷合格。MEMPHIS_ENGINEERING_NOT_APPROVED。</p>
<div class="grid"><div class="card"><div class="muted">A–L与历史拒绝状态</div><div class="big">28 / 28</div><div>27可行收敛＋1预期无解拒绝</div></div>
<div class="card"><div class="muted">研究模型跨侧入口压差</div><div class="big danger">192.412 kPa</div><div>00要求≤10kPa，仍FAIL</div></div>
<div class="card"><div class="muted">突然失泵近零流量</div><div class="big danger">50.0 s</div><div>0.949583m³亏缺，连续供冷FAIL</div></div></div>
<section><h2>从实际记录看变化</h2><label>场景 <select id="case"></select></label><label>曲线 <select id="metric"><option value="flow">最低单柜流量 m³/h</option><option value="temp">机柜入口与出口 °C</option><option value="dp">跨侧入口压差 kPa</option></select></label>
<svg id="chart" viewBox="0 0 1080 310" role="img" aria-label="原始动态记录同步曲线"></svg><div id="legend" class="legend"></div>
<label style="display:block">回放时间 <span id="at"></span><input id="time" type="range" min="0" max="599" value="299" aria-label="记录时间"></label>
<div id="reading"></div><details><summary>控制事件时间轴</summary><div id="events"></div></details>
<p class="muted">全部曲线来自官方trace逐帧记录。红虚线为登记门槛。失流时入口可能仍冷，必须同时看机柜出口和流量；没有GPU die安全结论。</p></section>
<section><h2>00/01、R12与当前模型的20项对照</h2><p>最终源文件哈希已重新核对。R12是过程参考；标识为研究假设或缺失的项目，不能自动成为客户设计。</p>
<label>查找 <input id="filter" placeholder="例如 板换、回充、静压"></label><button id="differences">仅看差异或未覆盖</button>
<div class="scroll"><table><thead><tr><th>项目</th><th>00/01最终依据</th><th>当前模型</th><th>依据定位与下一步</th></tr></thead><tbody id="matrix"></tbody></table></div></section>
<section><h2>保护链已动作，但未证明安全压差恢复</h2><p>0.1s从已释放压力触发停泵；3.8s实际泵停；5.9s一次阀隔离。最后模型参考差仍65kPa，不是物理被困压力预测。停泵会失去供冷，不能把保护动作与连续供冷合并为PASS。</p>
<p>源泵/罐体定压、真实膨胀容积、泄压与单侧失压能力未建模。不得仅调165/100kPa参考来得到10kPa以内。</p></section>
<section><h2>复核状态与原始文件</h2><div class="scroll"><table><tbody>${Object.entries(statuses).map(([k,v])=>'<tr><th>'+esc(k)+'</th><td>'+esc(v)+'</td></tr>').join('')}</tbody></table></div>
<p><a href="14_ENGINEERING_REPORT_ZH.md">中文综合报告与十四项答复</a> · <a href="03_STATIC_PRESSURE_MODEL_AUDIT.csv">20项对照CSV</a> · <a href="07_COMPLEMENTARITY_SOLVER_TESTS.json">数学原始结果</a> · <a href="16_SOURCE_AND_EVIDENCE_MANIFEST.json">源码证据哈希</a></p>
<p><a href="https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/${byte.run}">GitHub run${byte.run}</a></p>
<p class="mono">执行源码 ${byte.source_commit}<br>source manifest ${byte.source_manifest_sha256}</p>
<p class="muted">未改冻结M1、00/01原件或旧结果；未运行18柜/1800s、正式C3-C、现场硬件、生产或Phase6。</p></section>
<script type="application/json" id="data">${JSON.stringify(data).replaceAll('<','\\u003c')}</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent),E=id=>document.getElementById(id),esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;');
for(let i=0;i<D.cases.length;i++){const c=D.cases[i];E('case').add(new Option((c.stage==='suite'?'新算法':'原算法')+' · '+c.id,i));}
E('case').value=D.cases.findIndex(c=>c.stage==='suite'&&c.id==='T2_COLD_STANDBY');
function draw(){
const c=D.cases[+E('case').value],m=E('metric').value,keys=m==='temp'?['inlet','outlet']:[m==='dp'?'dp':'flow'],limit=m==='temp'?45:m==='dp'?10:11.395;
const cols=['#087b86','#b56327'],v=c.samples.flatMap(r=>keys.map(k=>r[k])).concat(limit),lo=Math.min(...v),hi=Math.max(...v),pad=Math.max(1,(hi-lo)*.1),a=lo-pad,b=hi+pad;
E('time').max=c.samples.length-1;const ix=Math.min(+E('time').value,c.samples.length-1),r=c.samples[ix],X=t=>75+t/60*965,Y=x=>260-(x-a)/(b-a)*220;
let svg='';for(let j=0;j<5;j++){let val=a+(b-a)*j/4,y=Y(val);svg+='<path d="M75 '+y+'H1040" stroke="#dce5eb"/><text x="5" y="'+(y+5)+'" font-size="13" fill="#526a79">'+val.toFixed(2)+'</text>';}
svg+='<path d="M75 '+Y(limit)+'H1040" stroke="#b23d35" stroke-dasharray="6 5"/><text x="80" y="'+(Y(limit)-6)+'" fill="#a3402b" font-size="13">'+(m==='temp'?'仅机柜入口上限45°C':m==='dp'?'跨侧入口压差上限10kPa':'流量下限11.395m³/h')+'</text>';
keys.forEach((k,j)=>svg+='<polyline fill="none" stroke="'+cols[j]+'" stroke-width="2.5" points="'+c.samples.map(p=>X(p.t).toFixed(2)+','+Y(p[k]).toFixed(2)).join(' ')+'"/>');
svg+='<path d="M'+X(r.t)+' 30V270" stroke="#758b98" stroke-dasharray="3 4"/><text x="75" y="295">0s</text><text x="1000" y="295">60s</text>';
E('chart').innerHTML=svg;E('at').textContent=r.t.toFixed(1)+'s';E('legend').innerHTML=keys.map((k,j)=>'<span style="color:'+cols[j]+'">'+({inlet:'机柜入口',outlet:'机柜出口',flow:'最低单柜流量',dp:'最大跨侧入口压差'})[k]+'</span>').join('');
E('reading').textContent='状态 '+r.state+'；流量 '+(Math.abs(r.flow)<1e-9?'≈0（原值'+r.flow.toExponential(2)+'）':r.flow.toFixed(3))+'m³/h；入口 '+r.inlet.toFixed(3)+'°C；出口 '+r.outlet.toFixed(3)+'°C；压差 '+r.dp.toFixed(3)+'kPa';
E('events').innerHTML=c.result?'<ol>'+c.result.events.map(x=>'<li>'+x.t.toFixed(1)+'s '+esc(x.new)+' · '+esc(x.reason)+'</li>').join('')+'</ol>':'原算法13.5s数值失败，后续没有有效记录。';
}
let dif=false;function matrix(){let term=E('filter').value.trim();E('matrix').innerHTML=D.basis.filter(r=>(!dif||!r.classification.startsWith('CONSISTENT'))&&JSON.stringify(r).includes(term)).map(r=>'<tr><td>'+esc(r.item)+'</td><td>'+esc(r.final_00_01)+'</td><td>'+esc(r.current_model)+'</td><td>'+esc(r.source_locator)+'<br>'+esc(r.required_action)+'</td></tr>').join('');}
for(const k of ['case','metric','time'])E(k).addEventListener('input',draw);E('filter').addEventListener('input',matrix);E('differences').onclick=()=>{dif=!dif;E('differences').textContent=dif?'显示全部20项':'仅看差异或未覆盖';matrix();};draw();matrix();
</script></main></html>`;
write('15_INTERACTIVE_ENGINEERING_REPORT.html',html);
const records=[];
function walk(folder){for(const d of readdirSync(folder,{withFileTypes:true})){const p=join(folder,d.name);if(d.isDirectory())walk(p);else if(d.name!=='16_SOURCE_AND_EVIDENCE_MANIFEST.json')records.push({path:relative(out,p).replaceAll('\\','/'),bytes:readFileSync(p).length,sha256:hash(p)});}}
walk(out);
write('16_SOURCE_AND_EVIDENCE_MANIFEST.json',{schema:'MEMPHIS-SOLVER-PRESSURE-REVIEWED-PACKAGE-v1',source_commit:byte.source_commit,run:byte.run,
 final_design_source_hashes:authority.final_design_sources,source_manifest_sha256:byte.source_manifest_sha256,
 official_zip_sha256:byte.official_zip_sha256,raw_logs_sha256:byte.raw_logs_sha256,source_zip_sha256:byte.source_zip_sha256,
 hash_rule:'SHA256 of file raw bytes; this manifest excluded to avoid circular hashing',records,statuses,native_jobs:byte.stages.map(s=>({
 stage:s.stage,pid:s.actual_python_pid,environment:s.environment,job:s.job}))});
console.log(JSON.stringify({files:records.length,manifest_sha256:hash(join(out,'16_SOURCE_AND_EVIDENCE_MANIFEST.json')),out,statuses},null,2));
