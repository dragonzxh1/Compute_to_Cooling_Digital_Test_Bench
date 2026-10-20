// Read-only evidence arithmetic. Does not import or execute the physical model.
import {readFileSync,writeFileSync,existsSync,createReadStream,readdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createInterface} from 'node:readline';
const base=resolve(process.argv[2]);
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const bytes=read(join(base,'independent_byte_review.json'));
const evidence=join(base,'official','artifacts','memphis-r12-dynamic-hydraulic-v1',bytes.run+'-1');
const reg=read(join(base,'official','v0_2','tests','tools','memphis_r12_dynamic_hydraulic_v1','registration.json'));
const all=[],partial=[],seen=new Set();
for(const stage of ['baseline','suite']){
  const delivery=join(evidence,stage,'delivery');if(!existsSync(delivery))continue;
  for(const d of readdirSync(delivery,{withFileTypes:true}).filter(d=>d.isDirectory())){
    const folder=join(delivery,d.name),path=join(folder,'case_result.json');
    if(existsSync(path)&&!seen.has(d.name)){seen.add(d.name);all.push({result:read(path),folder,stage});}
    else if(!existsSync(path)&&existsSync(join(folder,'trace.ndjson')))partial.push({case:d.name,stage,
      status:'NUMERICALLY_INVALID_PREFIX_NOT_COMPLETE_CASE',failure:existsSync(join(folder,'numerical_failure.json'))?read(join(folder,'numerical_failure.json')):null});
  }
}
const reviews=[];
for(const entry of all){
  const result=entry.result,id=result.case.id,path=join(entry.folder,'trace.ndjson');let count=0,last=null;
  let minimum=Infinity,maximum=-Infinity,zero=0,deficit=0,maxLocalMass=0,maxHXError=0,maxStepEnergy=0,net=0,initialEnergy=null,finalEnergy=null;
  let primaryB=0,maxOverlap=0,overlapStart=null,stableSince=null,stableEvidence=null,singleMaster=true,latched=false;
  const issues=[],limitViolations=new Set();
  const check=(ok,why)=>{if(!ok&&!issues.includes(why))issues.push(why);};
  const stream=createInterface({input:createReadStream(path),crlfDelay:Infinity});
  for await(const line of stream){
    const row=JSON.parse(line),p=row.post,m=row.released_measurements;count++;
    check(Math.abs(p.t-row.t-reg.resources.dt_s)<1e-7,'STEP_TIME');
    check(last===null||Math.abs(row.t-last.post.t)<1e-7,'TRACE_GAP');
    if(m){
      check(m.sampled_at<=m.release_at&&m.release_at<=row.t+1e-8,'FUTURE_MEASUREMENT');
      check(m.evidence_type==='RELEASED_MODELED_SENSOR_FRAME_NOT_FIELD_MEASUREMENT','MEASUREMENT_AUTHORITY');
      const match=Math.abs(m.cdus.A.supply_C-m.cdus.B.supply_C)<=reg.requirements.match_delta_T_K
        &&Math.abs(m.cdus.A.outlet_kPa_g-m.cdus.B.outlet_kPa_g)<=reg.requirements.match_delta_p_kPa
        &&m.cdus.B.primary_flow_m3_h>0&&m.cdus.B.speed>.01&&row.t-m.sampled_at<=reg.assumptions.measurement_max_age_s;
      if(match){if(stableSince===null)stableSince=row.t;}else stableSince=null;
      if(row.state==='OVERLAP'&&last?.state!=='OVERLAP'){
        stableEvidence={at:row.t,observed_stable_since:stableSince,elapsed:stableSince===null?null:row.t-stableSince};
        check(stableSince!==null&&row.t-stableSince>=5-1e-7,'FIVE_SECOND_MATCH_NOT_PROVEN');
      }
    }else check(row.pre_sampled_at===null&&row.pre_release_at===null,'MISSING_RELEASED_FRAME');
    check(Object.keys(p.racks).length===6&&Object.keys(p.cdus).length===2,'LOCAL_COVERAGE');
    const local=Object.values(p.racks), min=Math.min(...local.map(r=>r.flow_m3_h)),max=Math.max(...local.map(r=>r.supply_C));
    for(const r of local){
      maxLocalMass=Math.max(maxLocalMass,Math.abs(r.A_supply_m3_h+r.B_supply_m3_h-r.flow_m3_h),Math.abs(r.A_return_m3_h+r.B_return_m3_h-r.flow_m3_h));
    }
    check(p.secondary_mass_residual<=reg.assumptions.mass_relative_tolerance&&p.primary_mass_residual<=reg.assumptions.mass_relative_tolerance,'SOLVER_MASS_RESIDUAL');
    check(Math.abs(local.reduce((a,r)=>a+r.flow_m3_h,0)-p.unit_flow_m3_h)<1e-7,'UNIT_FLOW_SUM');
    for(const [tag,v] of Object.entries(p.valves))if(tag.includes('-P1-CV-B'))primaryB=Math.max(primaryB,v);
    singleMaster&&=['A','B',null].includes(p.master);
    if(p.master==='B'&&last?.post.master!=='B'){
      check(last?.post.master!== 'A','MASTER_DIRECT_A_TO_B');
      check(p.speeds['G01-C01A-P2-PM1']<.001,'NEW_MASTER_BEFORE_ZERO_SPEED');
      check(Object.entries(p.valves).filter(([tag])=>tag.startsWith('G01-C01A-')||(tag.includes('-R0')&&(/CV-A[SR]$/.test(tag)))).every(([,v])=>v<.001),'NEW_MASTER_BEFORE_ISOLATION');
    }
    const overlap=Array.from({length:6},(_,i)=>`G01-U1-R0${i+1}`).some(tag=>p.valves[tag+'-CV-AS']>.001&&p.valves[tag+'-CV-BS']>.001);
    if(overlap&&overlapStart===null)overlapStart=p.t;
    if(overlap)maxOverlap=Math.max(maxOverlap,p.t-overlapStart+reg.resources.dt_s);else overlapStart=null;
    let hx=0;
    for(const c of Object.values(p.cdus)){
      const cv=reg.assumptions.rho_kg_m3*reg.assumptions.cp_J_kgK;
      const qp=cv*c.primary_flow_m3_h/3600*(c.primary_outlet_C-c.primary_inlet_C);
      const qs=cv*c.secondary_flow_m3_h/3600*(c.secondary_hx_inlet_C-c.secondary_hx_equilibrium_outlet_C);
      maxHXError=Math.max(maxHXError,Math.abs(qp-c.heat_W),Math.abs(qs-c.heat_W));hx+=c.heat_W;
    }
    const e=p.energy,step=(e.load_W+e.secondary_pump_electric_W-hx)*reg.resources.dt_s;
    if(initialEnergy===null)initialEnergy=e.stored_before_J;
    if(finalEnergy!==null)check(Math.abs(finalEnergy-e.stored_before_J)<1e-6,'STORED_ENERGY_GAP');
    finalEnergy=e.stored_after_J;net+=step;
    maxStepEnergy=Math.max(maxStepEnergy,Math.abs(e.stored_after_J-e.stored_before_J-step));
    check(Math.abs(e.load_W-6*147250)<1e-8,'MISSING_RACK_LOAD');
    check(Math.abs(e.primary_boundary_rejection_W-hx-e.primary_pump_electric_W)<1e-6,'PRIMARY_HEAT_NOT_REJECTED');
    if(row.t>=result.case.fault_s-reg.resources.dt_s){
      if(p.t>=result.case.fault_s){minimum=Math.min(minimum,min);maximum=Math.max(maximum,max);if(min<.001)zero+=reg.resources.dt_s;deficit+=local.reduce((a,r)=>a+Math.max(0,reg.requirements.each_rack_flow_hot_m3_h-r.flow_m3_h),0)*reg.resources.dt_s/3600;}
    }
    if(max>45)limitViolations.add('RACK_INLET_OVER_45C');
    if(min+1e-7<reg.requirements.each_rack_flow_hot_m3_h)limitViolations.add('LOCAL_FLOW_BELOW_11.395M3H');
    if(Object.values(p.cdus).some(c=>c.hx_inlet_gauge_difference_kPa>10))limitViolations.add('HX_INLET_GAUGE_DIFFERENCE_OVER_10KPA');
    if(Object.values(p.cdus).some(c=>c.suction_kPa_g<50))limitViolations.add('PUMP_SUCTION_BELOW_50KPA_G');
    last=row;
  }
  check(count===Math.round(reg.resources.physical_seconds_per_case/reg.resources.dt_s),'INCOMPLETE_60S_TRACE');
  check(maxStepEnergy<=reg.assumptions.energy_step_tolerance_J,'SECONDARY_ENERGY_IMBALANCE');
  check(maxHXError<.001,'HX_PRIMARY_SECONDARY_HEAT_DISAGREEMENT');
  check(maxLocalMass<.001,'RACK_BRANCH_MASS_IMBALANCE');
  check(primaryB===0,'PRIMARY_B_ACTUALLY_OPEN');check(singleMaster,'MULTIPLE_ACTUAL_MASTERS');
  check(Math.abs(minimum-result.min_rack_flow_m3_h)<1e-6,'REPORTED_MINIMUM_DIFFERS');
  check(Math.abs(maximum-result.max_rack_inlet_C)<1e-6,'REPORTED_TEMPERATURE_DIFFERS');
  check(Math.abs(deficit-result.flow_deficit_volume_m3)<1e-6,'REPORTED_DEFICIT_DIFFERS');
  check(Math.abs(zero-result.near_zero_flow_duration_s)<1e-6,'REPORTED_ZERO_DURATION_DIFFERS');
  if(maxOverlap>30+1e-7)limitViolations.add('ACTUAL_OVERLAP_OVER_30S');
  reviews.push({case:id,scope:'INDEPENDENT_SAVED_EVIDENCE_ARITHMETIC_NOT_MODEL_REEXECUTION',
    evidence_consistency:issues.length?'FAIL':'PASS',issues,hard_requirement_violations:[...limitViolations],
    rows:count,min_rack_flow_m3_h:minimum,max_rack_inlet_C:maximum,near_zero_flow_duration_s:zero,
    flow_deficit_volume_m3:deficit,max_rack_node_mass_error_m3_h:maxLocalMass,max_HX_heat_balance_error_W:maxHXError,
    max_energy_step_error_J:maxStepEnergy,cumulative_energy_error_J:finalEnergy-initialEnergy-net,
    primary_B_max_valve_position:primaryB,max_actual_overlap_s:maxOverlap,five_second_stability:stableEvidence,
    controller_terminal:result.controller_terminal,takeover_verdict:result.takeover_verdict,
    thermal_verdict:result.thermal_verdict,hydraulic_verdict:result.hydraulic_verdict,hx_pressure_verdict:result.hx_pressure_verdict});
}
const report={schema:'R12-INDEPENDENT-TRACE-REVIEW-1',run:bytes.run,source_commit:bytes.source_commit,stage:'BASELINE_AND_COMPLETED_SUITE_CASES',
  status:reviews.every(r=>r.evidence_consistency==='PASS')?'EVIDENCE_CONSISTENT_NOT_ENGINEERING_APPROVED':'EVIDENCE_CONSISTENCY_FAIL',
  engineering_status:'MEMPHIS_ENGINEERING_NOT_APPROVED',case_count:reviews.length,cases:reviews,
  invalid_partial_cases:partial.map(p=>({case:p.case,stage:p.stage,status:p.status,t:p.failure?.t,state:p.failure?.state,
    worst_node:p.failure?.secondary?.worst_node||p.failure?.primary?.worst_node,
    mass_relative_residual:p.failure?.secondary?.residual||p.failure?.primary?.residual})),
  not_executed:reg.cases.filter(c=>!seen.has(c.id)&&!partial.some(p=>p.case===c.id)).map(c=>c.id)};
writeFileSync(join(base,'independent_trace_review.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
