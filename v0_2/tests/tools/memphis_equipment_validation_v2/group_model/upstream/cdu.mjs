// Development compatibility screening. No manufacturer curve, receipt or physical qualification is fabricated.
export function candidateDefaults(){
 return {schema:'CDU-CANDIDATE-v1',model:'待选定',origin:'UNSPECIFIED',source_reference:'',
  thermal:{capacity_kw:null,primary_inlet_c:null,secondary_supply_c:null,primary_flow_m3_h:null,secondary_flow_m3_h:null,fluid:'UNSPECIFIED',tolerance_fraction:null,service_condition:'UNSPECIFIED'},
  hydraulic:{fluid:'UNSPECIFIED',min_fluid_c:null,max_fluid_c:null,boundary:'UNSPECIFIED',filter_condition:'UNSPECIFIED',primary_curve:[],installed_pumps:null,normal:{running_pumps:null,curve:[]},one_pump_out:{running_pumps:null,curve:[]}},
  pressure:{primary_mawp_g_kpa:null,secondary_mawp_g_kpa:null,minimum_return_g_kpa:null},
  control:{measurement_error_k:null,distribution_rise_k:null,normal_overshoot_k:null,takeover_rise_k:null},
  interfaces:{pg_materials:null,filter_service:null,expansion_relief:null,leak_isolation:null,local_protection:null,independent_sensors:null,dewpoint_control:null,dual_power_full_load:null,modbus_points:null},
  electrical:{voltage_v:null,voltage_tolerance_fraction:null,frequency_hz:null,frequency_tolerance_hz:null,phase_count:null,max_input_kw:null}};
}

export function assessCDU(config,candidate,units){
 const c=config,e=candidate??{},checks=[],req=config.cdu_requirements??{},invalid=[];
 const finite=x=>typeof x==='number'&&Number.isFinite(x),positive=x=>finite(x)&&x>0,nonneg=x=>finite(x)&&x>=0;
 const add=(id,category,status,reason,details={})=>checks.push({id,category,status,reason,...details});
 const valid=(x,label,test=nonneg)=>{if(x===null||x===undefined)return false;if(!test(x)){invalid.push(label);return false;}return true;};
 const same=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=1e-6*Math.max(1,Math.abs(b));
 const compare=(id,category,available,required,reason)=>{
  if(!valid(required,id+'.required')||!valid(available,id+'.available'))return add(id,category,'INCOMPLETE','缺少有效的需求或设备数据',{available:available??null,required:required??null});
  add(id,category,available+1e-8>=required?'PASS_COMPATIBILITY':'FAIL',reason,{available,required,margin:available-required});
 };
 const truth=(id,category,value,description)=>{
  if(value===null||value===undefined)add(id,category,'INCOMPLETE','待补：'+description);
  else if(typeof value!=='boolean'){invalid.push(id);add(id,category,'INVALID','必须明确填写支持、不支持或待补');}
  else add(id,category,value?'PASS_COMPATIBILITY':'FAIL',description);
 };
 if(!Array.isArray(units)||units.length!==3||!Array.isArray(c.secondary_flow_m3_s)||c.secondary_flow_m3_s.length!==3)return {schema:'CDU-SUITABILITY-v1',status:'INVALID',checks:[{id:'SCOPE',category:'输入',status:'INVALID',reason:'需要三个六柜单元的有效需求'}],physical_validation:'INCOMPLETE'};
 if(!['UNSPECIFIED','SENSITIVITY','SUPPLIER_DECLARED'].includes(e.origin)){invalid.push('origin');}
 if(e.schema!==undefined&&e.schema!=='CDU-CANDIDATE-v1')invalid.push('candidate.schema');
 add('PROVENANCE','来源',e.origin==='UNSPECIFIED'||!e.source_reference?.trim()?'INCOMPLETE':'PASS_COMPATIBILITY',e.origin==='SENSITIVITY'?'合成/敏感性输入，仅作条件比较':'厂家录入也不自动取得实物资格',{origin:e.origin??'UNSPECIFIED',model:e.model??'待选定',source_reference:e.source_reference??''});
 const t=e.thermal??{},h=e.hydraulic??{},p=e.pressure??{},ctl=e.control??{},electrical=e.electrical??{};
 for(const key of ['capacity_kw','primary_flow_m3_h','secondary_flow_m3_h'])valid(t[key],'thermal.'+key,positive);
 for(const key of ['primary_inlet_c','secondary_supply_c'])valid(t[key],'thermal.'+key,x=>finite(x)&&x>=0&&x<=150);
 valid(t.tolerance_fraction,'thermal.tolerance_fraction',x=>finite(x)&&x>=0&&x<1);
 if(!['UNSPECIFIED','CLEAN_ONLY','GUARANTEED_SERVICE'].includes(t.service_condition??'UNSPECIFIED'))invalid.push('thermal.service_condition');
 const requirements=units.map((u,i)=>({unit:i+1,runtime_heat_kw:u.hx_demand_w/1000,design_capacity_kw:Math.ceil((u.hx_demand_w*1.2-1e-6)/100000)*100,
  primary_inlet_c:c.primary_target_c,secondary_supply_c:c.secondary_target_c,primary_flow_m3_h:c.primary_per_unit_m3_s*3600,secondary_flow_m3_h:c.secondary_flow_m3_s[i]*3600,
  external_dp_kpa:Array.isArray(req.external_dp_kpa)?req.external_dp_kpa[i]??null:null,required_ua_w_k:u.target_ua.ua_w_k}));
 const service=t.service_condition==='GUARANTEED_SERVICE';
 add('THERMAL_SERVICE','换热',service?'PASS_COMPATIBILITY':'INCOMPLETE','须明确服务状态下的污垢、公差和保证边界；清洁点不能自动变成长期保证');
 const thermalPoint={...t,effective_capacity_kw:positive(t.capacity_kw)&&valid(t.tolerance_fraction,'thermal.tolerance_fraction',x=>finite(x)&&x>=0&&x<1)?t.capacity_kw*(1-t.tolerance_fraction):null};
 for(const r of requirements){
  const matches=t.fluid===c.fluid.kind&&same(t.primary_inlet_c,r.primary_inlet_c)&&same(t.secondary_supply_c,r.secondary_supply_c)&&same(t.primary_flow_m3_h,r.primary_flow_m3_h)&&same(t.secondary_flow_m3_h,r.secondary_flow_m3_h);
  const missing=['primary_inlet_c','secondary_supply_c','primary_flow_m3_h','secondary_flow_m3_h'].some(k=>!finite(t[k]))||!t.fluid||t.fluid==='UNSPECIFIED';
  add('THERMAL_POINT_U'+r.unit,'换热',matches?'PASS_COMPATIBILITY':'INCOMPLETE',matches?'声明点温度、流量、两侧介质与当前工况一致；非曲线外推':missing?'温度、流量或两侧介质资料不足':'资料点与当前工况不同，禁止线性降额或直接套用',{unit:r.unit,required:r});
  if(matches){
   compare('THERMAL_RUNTIME_U'+r.unit,'换热',thermalPoint.effective_capacity_kw,r.runtime_heat_kw,'扣除声明负公差后覆盖实际运行热量');
   compare('THERMAL_DESIGN_U'+r.unit,'换热',thermalPoint.effective_capacity_kw,r.design_capacity_kw,'按客户计算规则：运行需求×1.20，按100kW向上取整；单独于运行需求');
  }else for(const kind of ['RUNTIME','DESIGN'])add('THERMAL_'+kind+'_U'+r.unit,'换热','INCOMPLETE','缺少同工况设备能力，额定kW不能直接比较',{unit:r.unit});
 }
 // This is an explicitly derived, constant-property equivalent, never manufacturer-measured UA.
 thermalPoint.equivalent_ua_w_k=null;
 if(positive(thermalPoint.effective_capacity_kw)&&positive(t.primary_flow_m3_h)&&positive(t.secondary_flow_m3_h)&&finite(t.primary_inlet_c)&&finite(t.secondary_supply_c)&&t.secondary_supply_c>t.primary_inlet_c&&t.fluid===c.fluid.kind){
  const q=thermalPoint.effective_capacity_kw*1000,C1=c.fluid.rho*c.fluid.cp*t.primary_flow_m3_h/3600,C2=c.fluid.rho*c.fluid.cp*t.secondary_flow_m3_h/3600,cm=Math.min(C1,C2),ratio=cm/Math.max(C1,C2),eps=q/(cm*(t.secondary_supply_c+q/C2-t.primary_inlet_c));
  if(eps>0&&eps<1)thermalPoint.equivalent_ua_w_k=cm*(Math.abs(1-ratio)<1e-9?eps/(1-eps):Math.log((1-eps*ratio)/(1-eps))/(1-ratio));
 }
 thermalPoint.equivalent_ua_basis='DECLARED_POINT_NEGATIVE_TOLERANCE_APPLIED_CONSTANT_DOCUMENT_PG_PROPERTIES_IDEAL_COUNTERFLOW_NOT_MEASURED_UA';
 if(positive(thermalPoint.effective_capacity_kw)&&finite(t.primary_inlet_c)&&finite(t.secondary_supply_c)&&positive(t.primary_flow_m3_h)&&positive(t.secondary_flow_m3_h)&&t.fluid===c.fluid.kind)add('THERMAL_ENDPOINTS','换热',thermalPoint.equivalent_ua_w_k?'PASS_COMPATIBILITY':'FAIL','声明点需满足理想逆流能量与端温的必要条件');
 const hydraulicContext=h.fluid===c.fluid.kind&&h.boundary==='COMPLETE_CDU_EXTERNAL_PORTS'&&h.filter_condition==='DIRTY_TERMINAL';
 add('HYDRAULIC_CONTEXT','流量压差',hydraulicContext?'PASS_COMPATIBILITY':'INCOMPLETE','要求项目介质、整机供回接口可用差压及污堵终态；不能填泵总扬程或重复扣内部损失');
 valid(h.min_fluid_c,'hydraulic.min_fluid_c',x=>finite(x)&&x>=0&&x<=150);valid(h.max_fluid_c,'hydraulic.max_fluid_c',x=>finite(x)&&x>=0&&x<=150);
 if(finite(h.min_fluid_c)&&finite(h.max_fluid_c)&&h.min_fluid_c>h.max_fluid_c)invalid.push('hydraulic.temperature_range');
 const primaryCurve=h.primary_curve??[];
 let primaryCurveOK=Array.isArray(primaryCurve)&&primaryCurve.length>=2;
 if(!Array.isArray(primaryCurve))invalid.push('primary_curve');
 if(Array.isArray(primaryCurve)&&primaryCurve.length){for(let i=0;i<primaryCurve.length;i++){const v=primaryCurve[i];if(!v||!nonneg(v.flow_m3_h)||!nonneg(v.dp_kpa)||(i>0&&(v.flow_m3_h<=primaryCurve[i-1]?.flow_m3_h||v.dp_kpa<primaryCurve[i-1]?.dp_kpa)))primaryCurveOK=false;}if(!primaryCurveOK)invalid.push('primary_curve_requires_ascending_flow_nondecreasing_dp_at_least_two_points');}
 const primaryEstimates=[];
 for(const r of requirements){
  const q=r.primary_flow_m3_h,returnC=r.primary_inlet_c+r.runtime_heat_kw*1000/(c.fluid.rho*c.fluid.cp*c.primary_per_unit_m3_s);
  let loss=null;if(primaryCurveOK&&q>=primaryCurve[0].flow_m3_h&&q<=primaryCurve.at(-1).flow_m3_h){for(let i=1;i<primaryCurve.length;i++)if(q<=primaryCurve[i].flow_m3_h){const a=primaryCurve[i-1],b=primaryCurve[i];loss=a.dp_kpa+(b.dp_kpa-a.dp_kpa)*(q-a.flow_m3_h)/(b.flow_m3_h-a.flow_m3_h);break;}}
  primaryEstimates.push({unit:r.unit,required_flow_m3_h:q,cdu_pressure_loss_kpa:loss,facility_available_dp_kpa:req.primary_available_dp_kpa??null});
  if(!hydraulicContext||!finite(h.min_fluid_c)||!finite(h.max_fluid_c)||h.min_fluid_c>r.primary_inlet_c||h.max_fluid_c<returnC||loss===null)add('PRIMARY_FLOW_U'+r.unit,'流量压差','INCOMPLETE','一次侧整机压降曲线或工况不足；不得用额定流量、板换单点或源泵扬程代替',primaryEstimates.at(-1));
  else compare('PRIMARY_FLOW_U'+r.unit,'流量压差',req.primary_available_dp_kpa,loss,'一次110m³/h时，现场接口可用压差须覆盖整机一次侧压降');
 }
 const installedOK=valid(h.installed_pumps,'installed_pumps',x=>Number.isInteger(x)&&x>=1&&x<=20);
 const curves={primary:{curve:primaryCurve,estimates:primaryEstimates}};
 for(const mode of ['normal','one_pump_out']){
  const m=h[mode]??{},curve=m.curve??[],lost=mode==='one_pump_out'?1:0;
  const countOK=valid(m.running_pumps,mode+'.running_pumps',x=>Number.isInteger(x)&&x>=0&&x<=20);
  if(installedOK&&countOK)add('PUMP_COUNT_'+mode,'流量压差',m.running_pumps>0&&m.running_pumps<=h.installed_pumps-lost?'PASS_COMPATIBILITY':'FAIL','故障后不得使用已失效泵或额外备用信用',{installed:h.installed_pumps,running:m.running_pumps,lost});
  else add('PUMP_COUNT_'+mode,'流量压差','INCOMPLETE','待补安装和实际运行泵数');
  let curveOK=Array.isArray(curve)&&curve.length>=2;
  if(!Array.isArray(curve))invalid.push(mode+'.curve');
  if(Array.isArray(curve)&&curve.length){
   for(let i=0;i<curve.length;i++){const v=curve[i];if(!v||!nonneg(v.flow_m3_h)||!nonneg(v.dp_kpa)||(i>0&&(v.flow_m3_h<=curve[i-1]?.flow_m3_h||v.dp_kpa>curve[i-1]?.dp_kpa)))curveOK=false;}
   if(!curveOK)invalid.push(mode+'.curve_requires_ascending_flow_nonincreasing_dp_at_least_two_points');
  }
  const interpolate=q=>{if(!curveOK||q<curve[0].flow_m3_h||q>curve.at(-1).flow_m3_h)return null;for(let i=1;i<curve.length;i++)if(q<=curve[i].flow_m3_h){const a=curve[i-1],b=curve[i];return a.dp_kpa+(b.dp_kpa-a.dp_kpa)*(q-a.flow_m3_h)/(b.flow_m3_h-a.flow_m3_h);}return null;};
  const estimates=[];
  for(const r of requirements){
   const returnTemp=r.secondary_supply_c+r.runtime_heat_kw*1000/(c.fluid.rho*c.fluid.cp*c.secondary_flow_m3_s[r.unit-1]);
   const tempOK=finite(h.min_fluid_c)&&finite(h.max_fluid_c)&&h.min_fluid_c<=r.secondary_supply_c&&h.max_fluid_c>=returnTemp;
   const available=interpolate(r.secondary_flow_m3_h);
   let operatingFlow=null;
   if(curveOK&&positive(r.external_dp_kpa)){
    let lo=curve[0].flow_m3_h,hi=curve.at(-1).flow_m3_h;const delta=q=>interpolate(q)-r.external_dp_kpa*(q/r.secondary_flow_m3_h)**2;
    if(delta(lo)>=0&&delta(hi)<=0){for(let k=0;k<60;k++){const mid=(lo+hi)/2;if(delta(mid)>=0)lo=mid;else hi=mid;}operatingFlow=(lo+hi)/2;}
   }
   estimates.push({unit:r.unit,available_dp_kpa:available,required_external_dp_kpa:r.external_dp_kpa,conditional_operating_flow_m3_h:operatingFlow,network_model:'DOCUMENT_PATH_KQ2_BUDGET_NOT_PER_RACK_NETWORK',temperature_covered:tempOK});
   if(!hydraulicContext||!tempOK||!curveOK||available===null)add('HYDRAULIC_'+mode+'_U'+r.unit,'流量压差','INCOMPLETE','介质/温度/过滤状态/接口边界缺失，或需求流量超曲线范围；禁止外推',{unit:r.unit,...estimates.at(-1)});
   else compare('HYDRAULIC_'+mode+'_U'+r.unit,'流量压差',available,r.external_dp_kpa,'在规定流量下比较整机可用差压；交点仅为平方阻力预算的条件工作点');
  }
  curves[mode]={curve,estimates};
 }
 const envelope=req.pressure_envelope??{};
 for(const [id,available,required]of [['PRIMARY_MAWP',p.primary_mawp_g_kpa,envelope.primary_max_g_kpa],['SECONDARY_MAWP',p.secondary_mawp_g_kpa,envelope.secondary_max_g_kpa],['MIN_RETURN',envelope.secondary_min_g_kpa,p.minimum_return_g_kpa]])compare(id,'承压',available,required,'表压边界；系统包络必须包含定压、关死和瞬态，不能将压差当表压');
 truth('PRESSURE_ENVELOPE_SCOPE','承压',envelope.includes_static_shutoff_transient,'系统压力包络已覆盖静压、关死与瞬态；待输入实际计算结果');
 truth('NPSH','承压',envelope.npsh_verified,'吸入条件及NPSH余量已独立核对');
 for(const k of ['measurement_error_k','distribution_rise_k','normal_overshoot_k','takeover_rise_k'])valid(ctl[k],'control.'+k);
 const temperatureBudgets={};
 for(const [id,rise,room]of [['NORMAL_TEMPERATURE','normal_overshoot_k',c.hard_limit_c-c.secondary_target_c],['TAKEOVER_TEMPERATURE','takeover_rise_k',c.hard_limit_c-c.force_takeover_c]]){
  const values=[ctl.measurement_error_k,ctl.distribution_rise_k,ctl[rise]],knownLowerBound=values.filter(nonneg).reduce((a,b)=>a+b,0),complete=values.every(nonneg);
  const status=knownLowerBound>room+1e-10?'FAIL':complete?'PASS_COMPATIBILITY':'INCOMPLETE';
  temperatureBudgets[id]={available_margin_k:room,known_consumed_k:knownLowerBound,remaining_margin_k:complete?room-knownLowerBound:null};
  add(id,'温控',status,'测量误差＋分配温升＋该阶段动态升温不得超过温度余量；缺值不视为零',temperatureBudgets[id]);
 }
 const descriptions={pg_materials:'两侧PG25与接液材料/密封兼容',filter_service:'过滤精度、污堵差压及维护隔离满足项目要求',expansion_relief:'独立补液、膨胀接受量及泄压路径已核对',leak_isolation:'漏液检测、隔离与补液限制满足项目要求',local_protection:'本地保护独立于BMS及网络',independent_sensors:'关键测量链独立并有故障处置',dewpoint_control:'露点控制与供液上限同时满足',dual_power_full_load:'任一路承担全批准负荷且转供动态满足',modbus_points:'Modbus点表、单位比例、权限和故障质量已核对'};
 for(const [id,description]of Object.entries(descriptions))truth(id,['independent_sensors','dewpoint_control'].includes(id)?'温控':'接口配套',e.interfaces?.[id],description);
 for(const k of ['voltage_v','frequency_hz','max_input_kw'])valid(electrical[k],'electrical.'+k,positive);
 const vt=valid(electrical.voltage_tolerance_fraction,'electrical.voltage_tolerance_fraction',x=>nonneg(x)&&x<1),ft=valid(electrical.frequency_tolerance_hz,'electrical.frequency_tolerance_hz');
 const phase=valid(electrical.phase_count,'electrical.phase_count',x=>Number.isInteger(x)&&x>=1&&x<=3);
 const electricComplete=positive(electrical.voltage_v)&&positive(electrical.frequency_hz)&&vt&&ft&&phase;
 const powerMatch=electricComplete&&electrical.phase_count===3&&480>=electrical.voltage_v*(1-electrical.voltage_tolerance_fraction)&&480<=electrical.voltage_v*(1+electrical.voltage_tolerance_fraction)&&Math.abs(electrical.frequency_hz-60)<=electrical.frequency_tolerance_hz;
 add('ELECTRICAL_SUPPLY','接口配套',electricComplete?powerMatch?'PASS_COMPATIBILITY':'FAIL':'INCOMPLETE','按厂家声明允差核480V三相、60Hz标称供电点；277V为相电压，未覆盖未知电网波动包络');
 compare('ELECTRICAL_BUDGET','接口配套',63,electrical.max_input_kw,'每CDU 63kW是现有UPS负荷预算，不是实际耗电或泵入液热');
 if(invalid.length)add('INVALID_VALUES','输入','INVALID','非法数值/曲线/枚举：'+[...new Set(invalid)].join(', '));
 const overall=items=>items.some(x=>x.status==='INVALID')?'INVALID':items.some(x=>x.status==='FAIL')?'FAIL':items.some(x=>x.status==='INCOMPLETE')?'INCOMPLETE':'PASS_COMPATIBILITY';
 const categories=Object.fromEntries([...new Set(checks.map(x=>x.category))].map(k=>[k,overall(checks.filter(x=>x.category===k))]));
 return {schema:'CDU-SUITABILITY-v1',status:overall(checks),model:e.model??'待选定',origin:e.origin??'UNSPECIFIED',checks,categories,requirements,thermal_point:thermalPoint,hydraulic:curves,temperature_budgets:temperatureBudgets,
  missing:checks.filter(x=>x.status==='INCOMPLETE').map(x=>x.id),failures:checks.filter(x=>x.status==='FAIL').map(x=>x.id),invalid:[...new Set(invalid)],
  meaning:'声明输入与工程预算的条件适配筛查；PASS_COMPATIBILITY不等于设备性能、客户验收或因果PASS。已知FAIL不被其他缺项掩盖。',
  physical_validation:'INCOMPLETE',hardware:'CALIBRATION_REQUIRED',qualification:'NOT_C3_QUALIFIED',dynamic_flow_coupling:'NOT_IMPLEMENTED_PRESCRIBED_FLOWS_UNCHANGED',
  reference:'Vertiv SL-70618_REVB_07-22用于选型方法和资料完整度参照，未填入任何Vertiv厂家性能值；需求取客户02/03/04/08。'};
}
