// Project design arithmetic. This module does not simulate hardware or dispatch control.
export function get(project,id){
  const found=project.parameters.find(p=>p.id===id);
  if(!found||found.value===null)throw Error('INCOMPLETE_PARAMETER: '+id);
  return found.value;
}
export function validatePackage(project){
  const ids=new Set();
  const sources=new Set(project.sources.map(s=>s.id));
  for(const p of project.parameters){
    if(ids.has(p.id))throw Error('DUPLICATE_PARAMETER: '+p.id);ids.add(p.id);
    if(!p.unit||!p.scope||!p.location||!sources.has(p.source?.document)||!p.source?.locator)throw Error('MISSING_SEMANTICS_OR_PROVENANCE: '+p.id);
    if(p.value!==null&&(!Number.isFinite(p.value)||p.value<0))throw Error('INVALID_VALUE: '+p.id);
    if(p.basis==='MISSING'&&(p.value!==null||p.evidence_status!=='INCOMPLETE'))throw Error('MISSING_VALUE_MUST_STAY_NULL: '+p.id);
    if(p.evidence_status==='CALIBRATED'||p.evidence_status==='MEASURED')throw Error('UNSUPPORTED_PHYSICAL_CLAIM: '+p.id);
  }
  for(const [id,unit]of Object.entries({rack_it_power:'W',liquid_capture_fraction:'1',fluid_density:'kg/m3',fluid_specific_heat:'J/(kg K)',primary_group_flow:'m3/s',primary_flow_per_cdu:'m3/s',secondary_hot_loop_dp:'Pa',hx_inlet_difference_limit:'Pa',pump_suction_min_gauge:'Pa(g)'})){
    if(project.parameters.find(p=>p.id===id)?.unit!==unit)throw Error('UNIT_MISMATCH: '+id);
  }
  const fraction=get(project,'liquid_capture_fraction');
  if(fraction>1)throw Error('FRACTION_OUT_OF_RANGE');
  for(const id of ['fluid_density','fluid_specific_heat','primary_group_flow','primary_flow_per_cdu','secondary_normal_flow','secondary_hot_flow','buffer_volume_each','secondary_main_inner_diameter'])if(get(project,id)<=0)throw Error('POSITIVE_PHYSICAL_VALUE_REQUIRED: '+id);
  for(const id of ['primary_efficiency_budget','secondary_efficiency_budget','buffer_effective_fraction','water_effective_fraction'])if(get(project,id)<=0||get(project,id)>1)throw Error('FRACTION_OUT_OF_RANGE: '+id);
  if(Math.abs(get(project,'primary_group_flow')-3*get(project,'primary_flow_per_cdu'))>1e-12)throw Error('PRIMARY_GROUP_FLOW_MISMATCH');
  if(get(project,'racks_per_unit')!==6||get(project,'units_per_group')!==3||get(project,'groups_per_site')!==5)throw Error('PROJECT_TOPOLOGY_MISMATCH');
  if(get(project,'active_cdus_per_unit')!==1||get(project,'cdus_per_unit')!==2||project.topology.parent_group18.primary_A_B_interconnection_allowed!==false)throw Error('REDUNDANCY_OR_ISOLATION_MISMATCH');
  if(project.recharge.selected_variant!==null&&!project.recharge.variants.some(v=>v.id===project.recharge.selected_variant))throw Error('UNKNOWN_VARIANT');
  return {status:'PASS',scope:'PARAMETER_STRUCTURE_AND_INPUT_SEMANTICS',physical_status:'INCOMPLETE'};
}
export function canonicalPower(project,input){
  if(input.quantity!=='IT_ELECTRICAL_POWER'||input.unit!=='W')throw Error('INVALID_POWER_QUANTITY_OR_UNIT');
  const count={RACK:1,UNIT6:6,GROUP18:18,SITE90:90}[input.scope];
  if(!count||input.rack_count!==count)throw Error('POWER_SCOPE_MISMATCH');
  if(input.basis!=='CUSTOMER_DESIGN')throw Error('UNSUPPORTED_POWER_BASIS');
  if(!Number.isFinite(input.value)||input.value<0)throw Error('INVALID_POWER');
  // Members permit aggregation only when each unique physical rack is explicitly present.
  if(input.members){
    if(input.members.length!==count||new Set(input.members.map(m=>m.rack_id)).size!==count)throw Error('DUPLICATE_OR_MISSING_RACK');
    const sum=input.members.reduce((s,m)=>{
      if(m.quantity!=='IT_ELECTRICAL_POWER'||m.unit!=='W'||m.scope!=='RACK'||!Number.isFinite(m.value)||m.value<0)throw Error('INVALID_MEMBER');
      return s+m.value;
    },0);
    if(Math.abs(sum-input.value)>1e-6)throw Error('AGGREGATION_MISMATCH');
  }
  return {quantity:'IT_ELECTRICAL_POWER',unit:'W',scope:input.scope,rack_count:count,value:input.value,liquid_heat_w:input.value*get(project,'liquid_capture_fraction'),air_heat_w:input.value*(1-get(project,'liquid_capture_fraction')),status:'DESIGN_LOAD_ONLY'};
}
export function temperatureTargets(project,db){
  if(!Number.isFinite(db))throw Error('INVALID_DRY_BULB');
  const secondary=db<=29?get(project,'secondary_normal_supply'):db>=37?get(project,'secondary_hot_supply'):40+.5*(db-29);
  const primary=secondary-3;
  return {primary_cdu_front_target_c:primary,secondary_rack_target_c:secondary,source_cold_header_target_c:primary-get(project,'cold_header_correction'),dry_exit:db>primary-get(project,'dry_exit_approach'),status:'DOCUMENT_TARGET_NOT_ACTUAL_TEMPERATURE'};
}
export function requireDynamicInputs(project){
  if(project.recharge.selected_variant===null)throw Error('INCOMPLETE_UNSELECTED_RECHARGE_VARIANT');
  const missing=project.parameters.filter(p=>p.value===null).map(p=>p.id);
  if(missing.length)throw Error('INCOMPLETE_DYNAMIC_INPUTS: '+missing.join(','));
  throw Error('INCOMPLETE_PROJECT_DYNAMIC_SOLVER_NOT_IMPLEMENTED');
}
export function recompute(project){
  validatePackage(project);
  const rho=get(project,'fluid_density'),cp=get(project,'fluid_specific_heat'),q1=get(project,'primary_flow_per_cdu'),qg=get(project,'primary_group_flow');
  const rack=get(project,'rack_it_power'),frac=get(project,'liquid_capture_fraction'),unit=rack*6*frac;
  const rows=project.reference_cases.map(c=>{
    const q2=c.secondary_m3_h/3600;
    const pump=q2*c.loop_dp_kpa*1000/get(project,'secondary_efficiency_budget');
    const hx=unit+pump;
    const group=3*hx+get(project,'primary_pump_heat_group');
    const primaryHX=c.primary_cdu_inlet_c+hx/(rho*cp*q1);
    const cold=c.primary_cdu_inlet_c-get(project,'cold_header_correction');
    return {id:c.id,secondary_pump_heat_w:pump,hx_heat_w:hx,group_reject_w:group,
      primary_hx_outlet_c:primaryHX,primary_source_hot_c:cold+group/(rho*cp*qg),secondary_return_c:c.rack_inlet_target_c+hx/(rho*cp*q2),
      table_hx_residual_w:c.hx_w===null?null:hx-c.hx_w,table_group_residual_w:group-c.group_reject_w,
      source_hot_residual_k:cold+group/(rho*cp*qg)-c.primary_source_hot_c,
      secondary_return_residual_k:c.rack_inlet_target_c+hx/(rho*cp*q2)-c.secondary_return_c,
      basis:'SAME_DESIGN_EQUATIONS_COMPATIBILITY_ONLY_NOT_INDEPENDENT_VALIDATION'};
  });
  return {scope:'DESIGN_ARITHMETIC_NOT_TRANSIENT_SIMULATION',loads:{rack_it_w:rack,unit6_it_w:rack*6,unit6_it_liquid_w:unit,group18_it_liquid_w:unit*3,site90_it_liquid_w:unit*15},cases:rows,
    buffer:{required_cold_m3:qg*get(project,'source_takeover_budget'),budget_cold_m3:get(project,'buffer_volume_each')*get(project,'buffer_effective_fraction'),ideal_displacement_s:get(project,'buffer_volume_each')*get(project,'buffer_effective_fraction')/qg,actual_outlet_rise_k:null,actual_performance:'INCOMPLETE'},
    water:{required_m3:get(project,'makeup_max_flow')*get(project,'water_outage_duration')*(1+get(project,'water_reserve_margin')),budget_m3:get(project,'water_tank_each')*get(project,'water_effective_fraction'),actual_supply_performance:'INCOMPLETE'},
    ups:{continuous_margin_w:get(project,'ups_capacity_each')-get(project,'ups_continuous_load'),overlap_margin_w:get(project,'ups_capacity_each')-get(project,'ups_overlap_load'),actual_power_continuity:'INCOMPLETE'},
    document_failures:[{id:'C03',source:'03.docx B028',stated_normal_w:4920,recomputed_normal_w:rows[0].secondary_pump_heat_w,residual_w:rows[0].secondary_pump_heat_w-4920,status:'FAIL',scope:'DOCUMENT_ARITHMETIC'}],
    dynamic_status:'INCOMPLETE',hardware_status:'CALIBRATION_REQUIRED',c3_status:'NOT_RUN'};
}
