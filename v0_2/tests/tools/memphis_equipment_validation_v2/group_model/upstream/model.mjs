import {candidateDefaults,assessCDU} from './cdu.mjs';
// New development control-volume model. No frozen solver or controller is modified.
// All liquid energy is accounted for; HX exchange cancels between its two sides.
export const bounded=(x,a,b)=>Math.max(a,Math.min(b,x));
export function projectDefaults(project,caseId='HOT') {
  const get=id=>{const p=project.parameters.find(p=>p.id===id);if(!p||p.value===null)throw Error('MISSING_PROJECT_INPUT:'+id);return p.value;};
  if(project.recharge.selected_variant!==null)throw Error('RECHARGE_SELECTION_CHANGED');
  const ref=project.reference_cases.find(c=>c.id===caseId);if(!ref)throw Error('UNKNOWN_CASE');
  return {schema:'US-PROJECT-DYNAMIC-v4',scope:'GROUP18_THREE_UNIT6',rack_count:18,gpu_per_rack:72,case_id:caseId,
    rack_it_w:Array(18).fill(get('rack_it_power')),liquid_fraction:get('liquid_capture_fraction'),
    fluid:{kind:'PG25_MASS_FRACTION',mass_fraction:get('fluid_pg_mass_fraction'),rho:get('fluid_density'),cp:get('fluid_specific_heat'),status:'DOCUMENT_ESTIMATE_CONSTANT_PROPERTIES'},
    primary_flow_m3_s:get('primary_group_flow'),primary_per_unit_m3_s:get('primary_flow_per_cdu'),
    secondary_flow_m3_s:Array(3).fill(ref.secondary_m3_h/3600),secondary_dp_pa:Array(3).fill(ref.loop_dp_kpa*1000),secondary_efficiency:get('secondary_efficiency_budget'),
    primary_pump_budget_w:get('primary_pump_heat_group'),load_pump_w:get('primary_group_flow')*get('load_loop_dp')/get('primary_efficiency_budget'),
    hx_ua_w_k:Array(3).fill(null),hx_nominal_w:get('cdu_initial_capacity'),hx_control:'FEEDBACK',
    outdoor_db_c:caseId==='NORMAL'?29:caseId==='MID'?35:46,outdoor_wb_c:caseId==='NORMAL'?29:30,
    primary_target_c:ref.primary_cdu_inlet_c,secondary_target_c:ref.rack_inlet_target_c,
    hard_limit_c:get('secondary_hard_limit'),force_takeover_c:get('secondary_force_takeover'),
    tank:{kind:'STRATIFIED_IDEAL',volume_m3:15,effective_fraction:.7,layers:80,mixing_m3_s:0},
    secondary_volume_each_m3:1.3,initial_secondary_return_c:ref.secondary_return_c-ref.loop_dp_kpa*1000/get('secondary_efficiency_budget')/(get('fluid_density')*get('fluid_specific_heat')),
    cdu_candidate:candidateDefaults(),cdu_requirements:{external_dp_kpa:Array(3).fill(caseId==='HOT'?295.21:caseId==='NORMAL'?152.81:null),primary_available_dp_kpa:null,pressure_envelope:{primary_max_g_kpa:null,secondary_max_g_kpa:null,secondary_min_g_kpa:null,includes_static_shutoff_transient:null,npsh_verified:null},external_dp_origin:'CUSTOMER03_PATH_BUDGET_NOT_MEASURED'},
    input_basis:{ua_origin:'UNSPECIFIED',supplier_reference:'',capacity_origin:'PROJECT_INITIAL_SIZING_SCENARIO_CAP_NOT_EQUIPMENT_GUARANTEE',initial_return_boundary:'BEFORE_SECONDARY_PUMP',controller_initialization:'MATCH_INITIAL_VALVE'},
    initial_cold_c:ref.primary_cdu_inlet_c-get('cold_header_correction'),initial_hot_c:ref.primary_source_hot_c,
    towers:{dry_nominal_w:get('dry_rated_capacity'),wet_nominal_w:get('wet_rated_capacity'),dry_derating:.9,wet_derating:1,wet_floor_c:get('wet_outlet_floor'),wet_min_flow_m3_s:get('wet_minimum_process_flow')},
    seconds:7200,dt_s:.5,output_every_s:10,steady_window_s:600,
    steady_power_fraction:.002,steady_drift_k_min:.01,
    outage:{enabled:false,at_s:3600,duration_s:90},
    assumptions:['Equipment UA is unspecified by default. Select an explicit theoretical/sensitivity scenario or enter supplier-declared data before simulation.',
      '18 prescribed rack powers; equal flow inside each six-rack unit, no per-rack hydraulic proof.',
      'Secondary1.3 m3/unit is an editable lumped storage assumption, not measured volume or cold-plate model.',
      'Source/load pump heat split of the document33.06 kW worst-case envelope; all enters liquid.',
      'Effective tower UA derived from document rating with capped capacity and assumed modulation; no manufacturer maps.',
      'MIXED is a counterexample tank; STRATIFIED_IDEAL is a finite-volume ideal bound with assumed effective volume/mixing.',
      'Feedback gains and actuator ramps are development assumptions, not PLC settings.',
      'Tower mode choice is instantaneous capacity screening, not120 s return/300 s dwell/30 s overlap control verification.',
      'An imposed90 s source interruption is not detection/valve/pump/emergency-power takeover verification.'],
    recharge_selection:'KEEP_BOTH_UNSELECTED',hardware:'CALIBRATION_REQUIRED',physical_validation:'INCOMPLETE'};
}
export function validateScenario(c){
  if(c.schema!=='US-PROJECT-DYNAMIC-v4'||c.scope!=='GROUP18_THREE_UNIT6'||c.rack_count!==18||c.gpu_per_rack!==72)throw Error('PROJECT_SCOPE_REQUIRED');
  if(!c.input_basis||!['UNSPECIFIED','DESIGN_REQUIREMENT','SENSITIVITY','SUPPLIER_DECLARED_UNVERIFIED'].includes(c.input_basis.ua_origin)||c.input_basis.initial_return_boundary!=='BEFORE_SECONDARY_PUMP'||c.input_basis.controller_initialization!=='MATCH_INITIAL_VALVE')throw Error('EXPLICIT_INPUT_BASIS_REQUIRED');
  if(c.input_basis.ua_origin==='UNSPECIFIED'||!Array.isArray(c.hx_ua_w_k)||c.hx_ua_w_k.some(x=>x===null))throw Error('INCOMPLETE_MISSING_EQUIPMENT_UA');
  if(c.input_basis.ua_origin==='SUPPLIER_DECLARED_UNVERIFIED'&&(typeof c.input_basis.supplier_reference!=='string'||!c.input_basis.supplier_reference.trim()))throw Error('SUPPLIER_REFERENCE_REQUIRED');
  const finite=(x,label)=>{if(typeof x!=='number'||!Number.isFinite(x))throw Error('NONFINITE:'+label);};
  const scan=(o,p='')=>{for(const [k,v]of Object.entries(o))if(v&&typeof v==='object')scan(v,p+k+'.');else if(typeof v==='number')finite(v,p+k);};scan(c);
  for(const key of ['secondary_flow_m3_s','secondary_dp_pa','hx_ua_w_k'])if(!Array.isArray(c[key])||c[key].length!==3||c[key].some(x=>typeof x!=='number'||!Number.isFinite(x)||x<=0))throw Error('THREE_POSITIVE_UNITS_REQUIRED:'+key);
  if(!Array.isArray(c.rack_it_w)||c.rack_it_w.length!==18||c.rack_it_w.some(x=>typeof x!=='number'||!Number.isFinite(x)||x<0||x>300000))throw Error('EXPLICIT_18_RACK_POWER_REQUIRED');
  if(c.liquid_fraction<0||c.liquid_fraction>1||c.secondary_efficiency<=0||c.secondary_efficiency>1)throw Error('INVALID_FRACTION');
  if(c.fluid.kind!=='PG25_MASS_FRACTION'||c.fluid.mass_fraction!==.25||c.fluid.rho<900||c.fluid.rho>1200||c.fluid.cp<2500||c.fluid.cp>4500)throw Error('PG25_PROPERTY_BOUNDARY_REQUIRED');
  if(Math.abs(c.primary_flow_m3_s-3*c.primary_per_unit_m3_s)>1e-10||c.primary_flow_m3_s<=0)throw Error('PRIMARY_FLOW_NOT_THREE_CDU_BRANCHES');
  if(c.seconds<600||c.seconds>14400||c.dt_s<.25||c.dt_s>2||c.seconds/c.dt_s>40000||Math.abs(c.seconds/c.dt_s-Math.round(c.seconds/c.dt_s))>1e-9)throw Error('BOUNDED_DURATION_DT_REQUIRED');
  if(c.output_every_s<c.dt_s||Math.abs(c.output_every_s/c.dt_s-Math.round(c.output_every_s/c.dt_s))>1e-9||c.steady_window_s<300||c.steady_window_s>c.seconds||c.steady_power_fraction<=0||c.steady_power_fraction>.05||c.steady_drift_k_min<=0||c.steady_drift_k_min>.1)throw Error('INVALID_OBSERVATION_WINDOW');
  if(c.secondary_volume_each_m3<=0||c.secondary_volume_each_m3>20||c.tank.volume_m3<=0||c.tank.volume_m3>100||c.tank.effective_fraction<=0||c.tank.effective_fraction>1||c.tank.mixing_m3_s<0||!['MIXED','STRATIFIED_IDEAL'].includes(c.tank.kind)||!Number.isInteger(c.tank.layers)||c.tank.layers<4||c.tank.layers>160)throw Error('INVALID_STORAGE');
  if(c.initial_cold_c<0||c.initial_cold_c>70||c.initial_hot_c<c.initial_cold_c||c.initial_hot_c>100||c.initial_secondary_return_c<0||c.initial_secondary_return_c>100)throw Error('INVALID_INITIAL_STATE');
  if(c.primary_pump_budget_w<c.load_pump_w||c.load_pump_w<0||c.hx_nominal_w<=0||!['FEEDBACK','FULL_OPEN'].includes(c.hx_control)||c.secondary_target_c<30||c.secondary_target_c>45||c.primary_target_c<30||c.primary_target_c>=c.secondary_target_c||c.hard_limit_c!==45||c.force_takeover_c!==44.5)throw Error('INVALID_CONTROL_OR_HEAT_BOUNDARY');
  if(c.outdoor_db_c<0||c.outdoor_db_c>50||c.outdoor_wb_c>c.outdoor_db_c||c.outdoor_wb_c<0||c.outdoor_wb_c>35)throw Error('INVALID_PAIRED_WEATHER');
  for(const x of [c.towers.dry_nominal_w,c.towers.wet_nominal_w])if(x<=0)throw Error('INVALID_TOWER_CAPACITY');
  for(const x of [c.towers.dry_derating,c.towers.wet_derating])if(x<0||x>1)throw Error('INVALID_TOWER_DERATING');
  if(c.towers.wet_floor_c<30||c.towers.wet_floor_c>40||c.towers.wet_min_flow_m3_s<=0||c.towers.wet_min_flow_m3_s>c.primary_flow_m3_s)throw Error('INVALID_WET_BOUND');
  if(c.recharge_selection!=='KEEP_BOTH_UNSELECTED')throw Error('RECHARGE_NOT_IMPLEMENTED_DO_NOT_SELECT');
  if(c.outage.enabled&&(c.outage.at_s<c.steady_window_s||c.outage.duration_s<=0||c.outage.duration_s>120||c.outage.at_s+c.outage.duration_s>c.seconds||Math.abs(c.outage.at_s/c.dt_s-Math.round(c.outage.at_s/c.dt_s))>1e-9||Math.abs(c.outage.duration_s/c.dt_s-Math.round(c.outage.duration_s/c.dt_s))>1e-9))throw Error('INVALID_OUTAGE_TIME');
  const vol=c.tank.kind==='MIXED'?c.tank.volume_m3:c.tank.volume_m3*c.tank.effective_fraction/c.tank.layers;
  if(c.dt_s*(c.primary_flow_m3_s+2*c.tank.mixing_m3_s)/vol>.5)throw Error('TANK_EXPLICIT_CFL_REDUCE_DT');
  for(const q of c.secondary_flow_m3_s)if(c.dt_s*q/c.secondary_volume_each_m3>.5)throw Error('SECONDARY_CFL_REDUCE_DT');
  if(c.input_basis.ua_origin==='DESIGN_REQUIREMENT'&&assessInputs(c).requirements.units.some(u=>u.target_ua.ua_w_k===null||Math.abs(u.entered_ua_w_k-u.target_ua.ua_w_k)>1e-5))throw Error('DESIGN_REQUIREMENT_UA_IDENTITY_MISMATCH');
  const equipment=assessInputs(c).cdu_suitability;
  if(equipment.status==='INVALID')throw Error('INVALID_CDU_CANDIDATE_INPUT');
  if(c.input_basis.derived_from_cdu_point){const ua=equipment.thermal_point.equivalent_ua_w_k,cap=equipment.thermal_point.effective_capacity_kw*1000;if(!ua||c.input_basis.ua_origin!=='SENSITIVITY'||c.input_basis.capacity_origin!=='DECLARED_POINT_NEGATIVE_TOLERANCE_APPLIED'||!c.cdu_candidate.source_reference?.trim()||!['SENSITIVITY','SUPPLIER_DECLARED'].includes(c.cdu_candidate.origin)||equipment.checks.some(x=>x.id.startsWith('THERMAL_POINT_')&&x.status!=='PASS_COMPATIBILITY')||c.hx_ua_w_k.some(v=>Math.abs(v-ua)>1e-6)||Math.abs(c.hx_nominal_w-cap)>1e-6)throw Error('INVALID_DERIVED_CDU_POINT_BINDING');}
  return c;
}
export function hxEffectiveness(ua,c1,c2){
  if(ua<=0||c1<=0||c2<=0)return 0;
  const min=Math.min(c1,c2),r=min/Math.max(c1,c2),n=ua/min;
  if(Math.abs(1-r)<1e-9)return n/(1+n);
  const e=Math.exp(-n*(1-r));return (1-e)/(1-r*e);
}
// Independent sizing calculation from required terminal temperatures, not an equipment curve.
export function requiredEffectiveUA(q,primaryIn,supply,c1,c2){
  if(![q,primaryIn,supply,c1,c2].every(Number.isFinite)||q<0||c1<=0||c2<=0)throw Error('INVALID_SIZING_INPUT');
  const a=supply+q/c2-primaryIn-q/c1,b=supply-primaryIn;
  if(a<=0||b<=0)return {status:'INFEASIBLE_ENDPOINTS',ua_w_k:null};
  const lmtd=Math.abs(a-b)<1e-9?b:(a-b)/Math.log(a/b);
  return {status:'THEORETICAL_REQUIREMENT_ONLY',ua_w_k:q/lmtd,lmtd_k:lmtd,primary_hot_c:primaryIn+q/c1,secondary_hx_hot_c:supply+q/c2};
}
export function assessInputs(c){
  const Cv=c.fluid.rho*c.fluid.cp;
  const units=Array.from({length:3},(_,i)=>{
    const liquid=c.rack_it_w.slice(i*6,i*6+6).reduce((a,b)=>a+b,0)*c.liquid_fraction,pump=c.secondary_flow_m3_s[i]*c.secondary_dp_pa[i]/c.secondary_efficiency,q=liquid+pump;
    const need=t=>requiredEffectiveUA(q,c.primary_target_c,t,Cv*c.primary_per_unit_m3_s,Cv*c.secondary_flow_m3_s[i]);
    const target=need(c.secondary_target_c),hard=need(c.hard_limit_c);
    return {unit:i+1,it_liquid_w:liquid,secondary_pump_w:pump,hx_demand_w:q,target_ua:target,hard_limit_ua:hard,
      nameplate_guarantee_ua:requiredEffectiveUA(c.hx_nominal_w,c.primary_target_c,c.secondary_target_c,Cv*c.primary_per_unit_m3_s,Cv*c.secondary_flow_m3_s[i]),
      entered_ua_w_k:c.hx_ua_w_k[i],target_ua_margin_fraction:Number.isFinite(c.hx_ua_w_k[i])&&target.ua_w_k>0?c.hx_ua_w_k[i]/target.ua_w_k-1:null,
      prescribed_flow_screen:!Number.isFinite(c.hx_ua_w_k[i])?'INCOMPLETE_MISSING_EQUIPMENT_UA':target.ua_w_k===null?'INFEASIBLE_ENDPOINTS':c.hx_ua_w_k[i]+1e-6>=target.ua_w_k?'MEETS_THEORETICAL_TARGET_UA_ONLY':'BELOW_THEORETICAL_TARGET_UA'};
  });
  return {cdu_suitability:assessCDU(c,c.cdu_candidate,units),customer:{rack_count:18,gpu_per_rack:72,rack_it_w:[...c.rack_it_w],liquid_fraction:c.liquid_fraction,liquid_fraction_status:'DESIGN_ASSUMPTION',primary_target_c:c.primary_target_c,secondary_target_c:c.secondary_target_c,hard_limit_c:c.hard_limit_c,outdoor_db_c:c.outdoor_db_c,outdoor_wb_c:c.outdoor_wb_c},
    equipment:{...c.input_basis,hx_ua_w_k:[...c.hx_ua_w_k],hx_nominal_w:c.hx_nominal_w,flow_status:'PRESCRIBED_NOT_HYDRAULICALLY_SOLVED',supplier_performance:'INCOMPLETE',tower_performance:'DOCUMENT_RATING_WITH_ASSUMED_MAP'},
    requirements:{units,group_total_liquid_heat_w:units.reduce((a,b)=>a+b.hx_demand_w,0)+c.primary_pump_budget_w,basis:'CONSTANT_PG25_IDEAL_COUNTERFLOW_AT_PRESCRIBED_PRIMARY_INLET_AND_FLOWS; NO_FOULING_OR_DESIGN_MARGIN'},
    conclusion_authority:'CONDITIONAL_MODEL_ONLY',physical_validation:'INCOMPLETE',qualification:'NOT_C3_QUALIFIED'};
}
export function heatExchange(hot,cold,ua,c1,c2,cap=Infinity){
  if(c1<=0||c2<=0)return {q:0,secondary_out:hot,primary_out:cold};
  const q=bounded(hxEffectiveness(ua,c1,c2)*Math.min(c1,c2)*(hot-cold),-cap,cap);
  return {q,secondary_out:hot-q/c2,primary_out:cold+q/c1};
}
export function towerRating(c){
  const C=c.fluid.rho*c.fluid.cp*c.primary_flow_m3_s;
  // Dry inlet is inferred by heat balance, not a recovered manufacturer spec.
  const dryInferred=37+c.towers.dry_nominal_w/C;
  return {dry_ua_w_k:C*Math.log((dryInferred-29)/(37-29))*c.towers.dry_derating,
    wet_ua_w_k:C*Math.log((43.92-30)/(35-30)),dry_inferred_inlet_c:dryInferred,
    basis:'ENGINEERING_RATING_REDUCTION_NOT_MEASURED_MAP'};
}
export function towerCapacity(c,hot,ratings,required){
  const Cv=c.fluid.rho*c.fluid.cp,flow=c.primary_flow_m3_s;
  const dry=f=>f<=0?0:Math.min(c.towers.dry_nominal_w, Cv*f*(1-Math.exp(-ratings.dry_ua_w_k/(Cv*f)))*Math.max(0,hot-c.outdoor_db_c));
  const wet=f=>f+1e-12<c.towers.wet_min_flow_m3_s?0:Math.min(c.towers.wet_nominal_w*c.towers.wet_derating,Cv*f*Math.max(0,hot-c.towers.wet_floor_c),Cv*f*(1-Math.exp(-ratings.wet_ua_w_k/(Cv*f)))*Math.max(0,hot-c.outdoor_wb_c));
  if(c.outdoor_db_c>c.primary_target_c-5)return {qmax:wet(flow),dry_fraction:0,wet_fraction:1,mode:'ONE_WET'};
  const qdry=dry(flow);if(qdry>=required)return {qmax:qdry,dry_fraction:1,wet_fraction:0,mode:'ONE_DRY'};
  let best={qmax:wet(flow),dry_fraction:0,wet_fraction:1,mode:'ONE_WET'};
  // Parallel branches share total flow; never add two330m3/h streams into660.
  const minFraction=c.towers.wet_min_flow_m3_s/flow;
  for(let i=0;i<=20;i++){const x=minFraction+(1-minFraction)*i/20,q=dry(flow*(1-x))+wet(flow*x);if(q>best.qmax)best={qmax:q,dry_fraction:1-x,wet_fraction:x,mode:x===1?'ONE_WET':'ONE_DRY_ONE_WET'};}
  return best;
}
export function primaryRates(c,temperatures,returnHot,sourceCold,sourceFlow){
  const Cv=c.fluid.rho*c.fluid.cp,F=c.primary_flow_m3_s,net=sourceFlow-F,N=temperatures.length,r=Array(N).fill(0);
  r[N-1]+=Cv*(F*returnHot-sourceFlow*temperatures[N-1]);
  r[0]+=Cv*(sourceFlow*sourceCold-F*temperatures[0]);
  for(let i=0;i<N-1;i++){
    const flux=Cv*net*(net>=0?temperatures[i]:temperatures[i+1]);r[i]-=flux;r[i+1]+=flux;
    const mixing=Cv*c.tank.mixing_m3_s*(temperatures[i+1]-temperatures[i]);r[i]+=mixing;r[i+1]-=mixing;
  }
  return r;
}
function evaluate(c,s,t,ratings,units,pumps){
  const Cv=c.fluid.rho*c.fluid.cp,F=c.primary_flow_m3_s,Cg=Cv*F,off=c.outage.enabled&&t>=c.outage.at_s-1e-9&&t<c.outage.at_s+c.outage.duration_s-1e-9;
  const sourceFlow=off?0:F,sourcePump=off?0:c.primary_pump_budget_w-c.load_pump_w;
  const primaryIn=s.tank[0]+c.load_pump_w/Cg;
  const exchanges=s.secondary.map((temp,i)=>heatExchange(temp+pumps[i]/(Cv*c.secondary_flow_m3_s[i]),primaryIn,c.hx_ua_w_k[i],Cv*c.primary_per_unit_m3_s*s.valves[i],Cv*c.secondary_flow_m3_s[i],c.hx_nominal_w));
  const qhx=exchanges.map(x=>x.q),returnHot=primaryIn+qhx.reduce((a,b)=>a+b,0)/Cg;
  const injected=units.reduce((a,b)=>a+b,0)+pumps.reduce((a,b)=>a+b,0)+c.load_pump_w+sourcePump;
  const sourceHot=s.tank.at(-1)+sourcePump/Cg;
  const availability=off?{qmax:0,mode:'IMPOSED_SOURCE_INTERRUPTION',dry_fraction:0,wet_fraction:0}:towerCapacity(c,sourceHot,ratings,injected);
  const rejected=off?0:s.tower*availability.qmax,sourceCold=sourceFlow>0?sourceHot-rejected/Cg:s.tank[0];
  const primary=primaryRates(c,s.tank,returnHot,sourceCold,sourceFlow);
  return {off,primary_in_c:primaryIn,secondary_supply_c:exchanges.map(x=>x.secondary_out),qhx,returnHot,sourceHot,sourceCold,availability,rejected,injected,sourceFlow,sourcePump,
    secondary_rates:units.map((q,i)=>q+pumps[i]-qhx[i]),primary_rates:primary};
}
export function* simulateProject(config){
  const c=structuredClone(config);validateScenario(c);
  const Cv=c.fluid.rho*c.fluid.cp,N=c.tank.kind==='MIXED'?1:c.tank.layers,V=c.tank.kind==='MIXED'?c.tank.volume_m3:c.tank.volume_m3*c.tank.effective_fraction,Vcell=V/N;
  const units=Array.from({length:3},(_,u)=>c.rack_it_w.slice(u*6,u*6+6).reduce((a,b)=>a+b,0)*c.liquid_fraction);
  const pumps=c.secondary_flow_m3_s.map((q,i)=>q*c.secondary_dp_pa[i]/c.secondary_efficiency);
  // Declared fully charged effective cold inventory, with one hot return cell.
  // No claimed measurement of the real tank thermocline or usable volume.
  const s={secondary:Array(3).fill(c.initial_secondary_return_c),tank:Array.from({length:N},(_,i)=>N>1&&i===N-1?c.initial_hot_c:c.initial_cold_c),valves:Array(3).fill(1),integral:Array(3).fill(0),tower:1};
  const energy=()=>Cv*(c.secondary_volume_each_m3*s.secondary.reduce((a,b)=>a+b,0)+Vcell*s.tank.reduce((a,b)=>a+b,0));
  const initE=energy(),ratings=towerRating(c),dt=c.dt_s,count=Math.round(c.seconds/dt),rows=[],history=[],profiles=[],events=[];
  let injectedJ=0,rejectedJ=0,maxStepResidual=0,end,preOutage=null;
  const makeRow=(t,e)=>({time_s:t,scope:'GROUP18',group_it_kw:c.rack_it_w.reduce((a,b)=>a+b,0)/1000,group_it_liquid_kw:units.reduce((a,b)=>a+b,0)/1000,
    pump_heat_kw:(pumps.reduce((a,b)=>a+b,0)+c.load_pump_w+e.sourcePump)/1000,total_input_kw:e.injected/1000,
    hx_kw:e.qhx.map(q=>q/1000),source_rejected_kw:e.rejected/1000,actual_primary_cdu_inlet_c:e.primary_in_c,
    primary_target_c:c.primary_target_c,actual_secondary_supply_c:e.secondary_supply_c,secondary_target_c:c.secondary_target_c,
    secondary_return_c:[...s.secondary],max_secondary_supply_c:Math.max(...e.secondary_supply_c),
    tank_bottom_c:s.tank[0],tank_top_c:s.tank.at(-1),tank_mean_c:s.tank.reduce((a,b)=>a+b,0)/N,
    source_flow_m3_h:e.sourceFlow*3600,load_flow_m3_h:c.primary_flow_m3_s*3600,secondary_flow_m3_h:c.secondary_flow_m3_s.map(q=>q*3600),
    tower_mode:e.availability.mode,tower_capacity_kw:e.availability.qmax/1000,tower_command:s.tower,hx_valves:[...s.valves],stored_change_mj:(energy()-initE)/1e6});
  const assessWindow=stop=>{
    const data=history.filter(r=>r.t>=stop-c.steady_window_s-1e-9&&r.t<=stop+1e-9),first=data[0],last=data.at(-1);
    if(data.length<2||last.t-first.t<c.steady_window_s-dt*1.1)return {status:'INCOMPLETE_WINDOW'};
    const avgIn=data.reduce((a,r)=>a+r.input,0)/data.length,avgOut=data.reduce((a,r)=>a+r.output,0)/data.length;
    const imbalance=Math.abs(avgIn-avgOut)/Math.max(avgIn,1),drift=Math.max(...last.temps.map((v,i)=>Math.abs(v-first.temps[i])))*60/(last.t-first.t);
    const storageRate=(last.E-first.E)/(last.t-first.t);
    return {status:imbalance<=c.steady_power_fraction&&drift<=c.steady_drift_k_min?'MODEL_STEADY_WINDOW':'INCOMPLETE_NOT_STEADY',window_s:last.t-first.t,input_mean_kw:avgIn/1000,rejected_mean_kw:avgOut/1000,imbalance_fraction:imbalance,max_temperature_drift_k_min:drift,storage_rate_kw:storageRate/1000,criteria_basis:'EXPLICIT_DEVELOPMENT_OBSERVATION_THRESHOLDS_NOT_CUSTOMER_TIMING_REQUIREMENTS'};
  };
  for(let i=0;i<=count;i++){
    const t=i*dt,e=evaluate(c,s,t,ratings,units,pumps);end=e;
    const row=makeRow(t,e);history.push({t,input:e.injected,output:e.rejected,E:energy(),bottom:s.tank[0],temps:[e.primary_in_c,...e.secondary_supply_c,s.tank[0],s.tank.at(-1)]});
    if(i%Math.round(c.output_every_s/dt)===0||i===count)rows.push(row);
    if(c.outage.enabled&&Math.abs(t-c.outage.at_s)<dt/2){preOutage={row,window:assessWindow(t-dt)};profiles.push({time_s:t,layer_c:[...s.tank]});}
    if(c.outage.enabled&&Math.abs(t-c.outage.at_s-c.outage.duration_s)<dt/2)profiles.push({time_s:t,layer_c:[...s.tank]});
    if(Math.max(...e.secondary_supply_c)>c.hard_limit_c&&(i===0||history.at(-2).temps.slice(1,4).every(x=>x<=c.hard_limit_c)))events.push({time_s:t,type:'MODEL_SUPPLY_LIMIT_EXCEEDED',meaning:'CONDITIONAL_MODEL_SCENARIO_NOT_REAL_PROTECTION_RECEIPT'});
    if(i===count)break;
    const before=energy();s.secondary=s.secondary.map((x,k)=>x+dt*e.secondary_rates[k]/(Cv*c.secondary_volume_each_m3));s.tank=s.tank.map((x,k)=>x+dt*e.primary_rates[k]/(Cv*Vcell));
    injectedJ+=e.injected*dt;rejectedJ+=e.rejected*dt;
    const residual=energy()-before-(e.injected-e.rejected)*dt;maxStepResidual=Math.max(maxStepResidual,Math.abs(residual));
    if([...s.secondary,...s.tank].some(x=>!Number.isFinite(x)||x<0||x>150)){
      const error=Error('INCOMPLETE_MODEL_TEMPERATURE_RANGE');error.details={time_s:t+dt,previous_valid_row:row,unvalidated_next_temperatures:[...s.secondary,...s.tank],reason:'Stop at model validity boundary; no clamping or fabricated steady result.'};throw error;
    }
    // Local feedback acts on computed temperatures. Targets never replace an output.
    for(let k=0;k<3;k++)if(c.hx_control==='FEEDBACK'){
      const error=e.secondary_supply_c[k]-c.secondary_target_c;
      if(i===0)s.integral[k]=s.valves[k]-.5-.05*error;
      const trial=s.integral[k]+.0005*error*dt,raw=.5+.05*error+trial;
      if(!((raw>1&&error>0)||(raw<.02&&error<0)))s.integral[k]=trial;
      const command=bounded(.5+.05*error+s.integral[k],.02,1);s.valves[k]+=bounded(command-s.valves[k],-.02*dt,.02*dt);
    }
    const command=bounded((e.injected+300000*(e.primary_in_c-c.primary_target_c))/Math.max(e.availability.qmax,1),0,1);
    // Source feedback already measures the CDU inlet including load-pump heat.
    s.tower+=bounded(command-s.tower,-.02*dt,.02*dt);
    if(i%400===0)yield {progress:i/count,time_s:t};
  }
  const steady=assessWindow(c.seconds),stored=energy()-initE,totalResidual=stored-injectedJ+rejectedJ;
  const maxSupply=Math.max(...history.map(r=>Math.max(...r.temps.slice(1,4)))),lastMax=Math.max(...end.secondary_supply_c);
  const steadyCapacity=steady.status==='MODEL_STEADY_WINDOW'?(lastMax<=c.hard_limit_c?'MODEL_CONDITIONAL_PASS':'MODEL_CONDITIONAL_FAIL'):'INCOMPLETE';
  const tracking=steady.status==='MODEL_STEADY_WINDOW'?(end.secondary_supply_c.every(x=>Math.abs(x-c.secondary_target_c)<=.1)?'MODEL_CONDITIONAL_PASS':'MODEL_CONDITIONAL_FAIL'):'INCOMPLETE';
  const wholeRun=maxSupply<=c.hard_limit_c?'MODEL_CONDITIONAL_PASS':'MODEL_CONDITIONAL_FAIL';
  const nominalStatus=steady.status!=='MODEL_STEADY_WINDOW'?'INCOMPLETE':steadyCapacity==='MODEL_CONDITIONAL_PASS'&&tracking==='MODEL_CONDITIONAL_PASS'&&wholeRun==='MODEL_CONDITIONAL_PASS'?'MODEL_CONDITIONAL_PASS':'MODEL_CONDITIONAL_FAIL';
  let interruption={status:'NOT_RUN',physical_status:'INCOMPLETE',reason:'No detection, valve, pump dynamics or emergency-power proof.'};
  if(preOutage){const during=history.filter(r=>r.t>=c.outage.at_s&&r.t<=c.outage.at_s+c.outage.duration_s),bottomRise=Math.max(...during.map(r=>r.bottom))-preOutage.row.tank_bottom_c;
    const max=Math.max(...during.map(r=>Math.max(...r.temps.slice(1,4))));
    const baseline=preOutage.window.status==='MODEL_STEADY_WINDOW'&&preOutage.row.max_secondary_supply_c<=45;
    const threshold=!baseline?'INVALID_BASELINE_NOT_STEADY_OR_ALREADY_OVER_LIMIT':bottomRise<=.5&&max<=45?'MODEL_CONDITIONAL_PASS':'MODEL_CONDITIONAL_FAIL';
    interruption={status:!baseline?threshold:c.tank.kind==='STRATIFIED_IDEAL'?'INCOMPLETE_IDEAL_TANK_NUMERICAL_AND_PHYSICAL_VALIDATION':threshold,threshold_status:threshold,numerical_mesh_qualification:'NOT_ESTABLISHED_IN_SINGLE_RUN',physical_status:'INCOMPLETE',pre_event:preOutage.window,baseline_supply_c:preOutage.row.max_secondary_supply_c,imposed_seconds:c.outage.duration_s,tank_outlet_rise_k:bottomRise,max_supply_c:max,tank_kind:c.tank.kind,meaning:'Imposed source interruption; ideal layers are numerically diffusive and layer-dependent; threshold result is descriptive only. Excludes fault recognition, build-cold and displacement implementation. No real stratified-tank approval.'};
  }
  const inputAssessment=assessInputs(c),cduStatus=inputAssessment.cdu_suitability.status;
  const systemStatus=cduStatus==='FAIL'||nominalStatus==='MODEL_CONDITIONAL_FAIL'||interruption.status==='MODEL_CONDITIONAL_FAIL'?'FAIL':cduStatus!=='PASS_COMPATIBILITY'||(c.outage.enabled&&interruption.status!=='MODEL_CONDITIONAL_PASS')?'INCOMPLETE':'PASS_COMPATIBILITY';
  return {version:'US-PROJECT-DYNAMIC-v4',status:'COMPLETED_BOUNDED_DEVELOPMENT_SIMULATION',config:c,scope:c.scope,rows,events,profiles,ratings,input_assessment:inputAssessment,
    system_assessment:{status:systemStatus,scope:'CDU_DECLARED_INPUT_COMPATIBILITY_AND_PRESCRIBED_FLOW_THERMAL_SCENARIO_ONLY',thermal:nominalStatus,cdu:cduStatus,interruption:interruption.status,physical_validation:'INCOMPLETE',qualification:'NOT_C3_QUALIFIED',meaning:'Known failures are not hidden by missing evidence or thermal-only PASS. No actual pump-network, tower or hardware qualification.'},
    summary:{max_supply_c:maxSupply,last_supply_c:end.secondary_supply_c,last_primary_inlet_c:end.primary_in_c,last_rejected_kw:end.rejected/1000,total_input_kw:end.injected/1000,nominal_model_status:nominalStatus,steady_supply_limit_status:steadyCapacity,steady_target_tracking_status:tracking,whole_run_supply_limit_status:wholeRun,steady,interruption,
      energy:{injected_j:injectedJ,rejected_j:rejectedJ,stored_change_j:stored,total_residual_j:totalResidual,max_step_residual_j:maxStepResidual,boundary:'THREE_SECONDARY_LIQUID_STORAGES_PLUS_ACTIVE_PRIMARY_TANK_PUMP_HEAT_INCLUDED_HX_INTERNAL_CANCELS'}},
    qualification:'NOT_C3_QUALIFIED',physical_validation:'INCOMPLETE',hardware:'CALIBRATION_REQUIRED',recharge:'KEEP_BOTH_UNSELECTED_NOT_SIMULATED',
    missing_evidence:['actual UA/fouling/capacity maps','tower maps and fan/flow response','pump/pipe curves and per-rack distribution','actual storage and stratification','sensor/valve/pump timing and emergency power','PG product temperature properties'],
    limits:c.assumptions};
}
export function runProject(c){const g=simulateProject(c);let n=g.next();while(!n.done)n=g.next();return n.value;}
