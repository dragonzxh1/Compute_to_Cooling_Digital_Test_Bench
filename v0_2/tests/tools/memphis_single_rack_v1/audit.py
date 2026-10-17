"""Independent persisted equations and causal audit; no model/solver imports."""
import json
from math import sqrt,fsum,exp
from hashlib import sha256

def read(p):return json.loads(p.read_bytes())
def need(ok,why):
    if not ok:raise ValueError(why)
def tol(*terms,ops=4096):
    u=2**-53;return ops*u/(1-ops*u)*max(1.,fsum(abs(x) for x in terms))
def close(a,b,why):need(abs(a-b)<=tol(a,b),why)
def digest(d):return sha256(json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def audit(directory,spec):
    c=read(directory/'input.json');rows=read(directory/'series.json');steps=read(directory/'physics.json')
    phases=read(directory/'phases.json');observations=read(directory/'measurements.json');out=read(directory/'result.json')
    n=c['rack_count'];rho=c['density_kg_m3'];cv=rho*c['cp_j_kg_k'];vol=c['volumes_m3'];caps=[cv*v for v in vol]
    qd=c['design_flow_m3_s'];bd=qd/n;common=(c['design_dp_pa']-c['branch_dp_pa'])/qd**2
    bk=[c['branch_dp_pa']*f/bd**2 for f in c['branch_factors']];equiv=1/fsum(1/sqrt(k) for k in bk)**2
    curve=c['design_dp_pa']*(c['quadratic_shutoff_factor']-1)/qd**2
    h0=c['design_dp_pa']*c['quadratic_shutoff_factor']/c['design_speed']**2
    def hydraulic(speed):
        q=sqrt(h0*speed*speed/(common+equiv+curve));head=(common+equiv)*q*q
        return q,head,[sqrt(equiv*q*q/k) for k in bk]
    initial=fsum(t*cap for t,cap in zip([rows[0]['supply_k'],*rows[0]['rack_return_k'],rows[0]['return_k']],caps))
    ledger={k:0. for k in ('IT','liquid','pump','HX')};max_error=0.;previous=None;cursor=0
    bytime={r['time_ns']:r for r in rows};byid={r['measurement_record_id']:r for r in observations}
    need(len(steps)==c['duration_ns']//c['dt_ns'] and len(rows)==len(steps)+1,'FULL_PHYSICAL_COVERAGE')
    for s in steps:
        dt=(s['end_ns']-s['start_ns'])/1e9;a=bytime[s['start_ns']];b=bytime[s['end_ns']]
        old=[a['supply_k'],*a['rack_return_k'],a['return_k']];new=[b['supply_k'],*b['rack_return_k'],b['return_k']]
        need(s['old_k']==old and s['new_k']==new,'PHYSICAL_INTERVAL_BINDING')
        q,head,fl=hydraulic(b['actual_speed']);close(q,s['flow_m3_s'],'ACTUAL_SPEED_FLOW');close(head,s['dp_pa'],'ACTUAL_SPEED_HEAD')
        close(fsum(fl),q,'NODE_MASS')
        for x,y in zip(fl,s['branch_flows_m3_s']):close(x,y,'BRANCH_PRESSURE_BALANCE')
        primary=c['primary_inlet_k']+(4 if c['fault']=='PRIMARY_WARM' and s['start_ns']>=c['fault_at_ns'] else 0)
        need(primary==s['primary_k'],'SOURCE_BOUNDARY_TIME')
        cs=cv*q;cp=cv*c['primary_flow_m3_s'];small=min(cs,cp);large=max(cs,cp);cr=small/large;ntu=c['hx_ua_w_k']/small
        e=exp(-ntu*(1-cr));effect=ntu/(1+ntu) if abs(1-cr)<1e-10 else (1-e)/(1-cr*e)
        hx=effect*small*(old[-1]-primary);close(hx,s['hx_w'],'NTU_FORMULA')
        need(abs(cp*(s['primary_outlet_k']-primary)-hx)<=tol(cp*primary,cp*s['primary_outlet_k'],hx),'TWO_SIDED_HX_HEAT')
        electric=head*q/c['wire_efficiency'];close(electric,s['pump_electrical_w'],'WIRE_POWER')
        close(head*q,s['hydraulic_w'],'HYDRAULIC_WORK')
        close(electric,s['hydraulic_w']+s['pump_liquid_loss_w'],'PUMP_HEAT_NOT_DOUBLE_COUNTED')
        while cursor+1<len(c['load_profile']) and c['load_profile'][cursor+1]['time_ns']<=s['start_ns']:cursor+=1
        loads=c['load_profile'][cursor]['rack_it_w'];need(loads==s['rack_it_w'],'LOAD_FORCING_CAUSAL_OWNER')
        rates=[cv*q*(old[-1]-old[0])-hx+common/2*q**3]
        rates += [cv*f*(old[0]-t)+.95*w+k*f**3 for f,t,w,k in zip(fl,old[1:-1],loads,bk)]
        rates += [fsum(cv*f*(t-old[-1]) for f,t in zip(fl,old[1:-1]))+electric-head*q+common/2*q**3]
        for x,y,cap,r,recorded in zip(old,new,caps,rates,s['rates_w']):
            close(r,recorded,'RATE_RECONSTRUCTION');err=(y-x)*cap-dt*r
            need(abs(err)<=tol(x*cap,y*cap,dt*r),'LOCAL_CONTROL_VOLUME');max_error=max(max_error,abs(err))
        for k,w in dict(IT=fsum(loads),liquid=.95*fsum(loads),pump=electric,HX=hx).items():ledger[k]+=w*dt
        previous=s
    for r in rows:
        q,head,fl=hydraulic(r['actual_speed']);close(q,r['flow_m3_s'],'SNAPSHOT_FLOW');close(head,r['dp_pa'],'SNAPSHOT_HEAD')
        for f,g in zip(fl,r['branch_flows_m3_s']):close(f,g,'SNAPSHOT_BRANCH')
    final=fsum(t*cap for t,cap in zip([rows[-1]['supply_k'],*rows[-1]['rack_return_k'],rows[-1]['return_k']],caps))
    residual=final-initial-ledger['liquid']-ledger['pump']+ledger['HX']
    global_bound=tol(initial,final,*ledger.values(),ops=8192*(len(steps)+1))
    need(abs(residual)<=global_bound,'INDEPENDENT_GLOBAL_ENERGY')
    # Reconstruct the observation-only controller without using its code.
    integral=0.;prior_time=None;previous=None;first_fault=None;first_confirm=None;seen=set();duplicates=0
    for f in phases:
        pre,safety,plc,post=(f[x] for x in ('PRE','SAFETY','PLC','POST'));m=pre['measurement'];o=byid[m['measurement_record_id']]
        now=f['time_ns'];need(o['sample_ns']==m['sample_ns'] and o['available_ns']==m['release_ns']<=now,'CAUSAL_ARRIVAL')
        valid=o['quality']=='VALID' and now-o['sample_ns']<=c['sensor_max_age_ns']
        need((m['quality']=='VALID')==valid,'FRESHNESS_LABEL')
        if m['measurement_record_id'] in seen:duplicates+=1
        seen.add(m['measurement_record_id'])
        delta=0 if prior_time is None else (now-prior_time)/1e9;prior_time=now
        if valid:
            actual=bytime[o['sample_ns']];need(m['measured_speed']==o['pump_speed']==actual['actual_speed'],'ACTUAL_SENSOR_SPEED')
            need(o['supply_k']==actual['supply_k'] and o['rack_return_k']==actual['rack_return_k'],'ACTUAL_TEMPERATURE_MEASUREMENT')
            excess=max(0,max(o['rack_return_k'])-o['supply_k']-c['controller_deltaT_reference_K'])
            integral=min(.9-c['initial_speed'],max(0,integral+c['controller_ki_per_K_s']*excess*delta))
            request=min(.9,max(.3,c['initial_speed']+c['controller_kp_per_K']*excess+integral))
            close(request,f['controller_request'],'OBSERVATION_ONLY_FEEDBACK')
        else:need(f['controller_request'] is None and m['measured_speed'] is None,'NO_TRUTH_FALLBACK')
        if previous:need(pre['old_command']['value']==previous['command'] and pre['old_command']['issue_ns']==previous['issue_ns'],'PRE_NO_FUTURE_COMMAND')
        need(digest(pre)==f['immutable_pre_digest']==safety['pre_digest'],'PRE_DIGEST')
        need(digest(safety)==f['immutable_safety_digest']==plc['safety_digest'],'SAFETY_DIGEST')
        need(post['pre_id']==pre['record_id'] and post['plc_id']==plc['record_id'] and plc['safety_id']==safety['record_id'],'PLC_POST_BINDING')
        need(f['actuator_command']['producer_module']=='PLC' and f['envelope']['minimum_speed']<=plc['command']<=f['envelope']['maximum_speed'],'ISSUER_RESTRICTIONS')
        if first_fault is not None:need(safety['severity']=='FAULT','FAULT_LATCH_CLEARED')
        if safety['severity']=='FAULT' and first_fault is None:first_fault=now/1e9
        if pre['state']=='TRACKING_FAULT_CONFIRMED' and first_confirm is None:first_confirm=now/1e9
        previous=plc
    maximum=max(r['supply_k'] for r in rows)-273.15
    if spec['expect']=='NOMINAL':need(maximum<=45 and first_confirm is None and first_fault is None,'NOMINAL_THERMAL_OR_FALSE_FAULT')
    if spec['expect']=='RESPONSE':
        need(first_confirm is None and rows[-1]['flow_m3_s']>1.5*rows[0]['flow_m3_s'],'LOAD_STEP_FEEDBACK_OR_FALSE_TRACKING')
        need(maximum<=45,'LOAD_STEP_THERMAL_LIMIT')
    if spec['expect']=='TRACKING_FAULT':
        frozen=[r for r in rows if r['time_ns']>=c['fault_at_ns']]
        need(first_confirm is not None and first_fault is not None,'UNDETECTED_STUCK')
        need(len({r['actual_speed'] for r in frozen})==1 and max(r['commanded_speed'] for r in frozen)-frozen[0]['actual_speed']>=.15,'STUCK_DEMAND_AND_ACTUAL')
        need(all(not o['pump_fault'] and o['pump_ready'] for o in observations),'FABRICATED_EQUIPMENT_FAULT')
    if spec['expect']=='SENSOR_FAULT':need(first_fault is not None and first_confirm is None,'SENSOR_NOT_TRACKING_FAULT')
    if spec['expect']=='THERMAL_NEGATIVE':
        need(maximum>45 and any('LIQUID_SUPPLY_LIMIT_MEASURED' in f['SAFETY']['reason_codes'] for f in phases),'WARM_BOUNDARY_NOT_REPORTED')
    return dict(status='INDEPENDENT_EQUATIONS_AND_REGISTERED_BEHAVIOR_VERIFIED',rack_count=n,steps=len(steps),transactions=len(phases),
        unique_observations=len(seen),repeated_observations=duplicates,max_local_residual_j=max_error,
        global_energy_residual_j=residual,global_energy_bound_j=global_bound,independent_integrals=ledger,
        maximum_inlet_C=maximum,maximum_return_C=max(max(r['rack_return_k']) for r in rows)-273.15,
        final_inlet_C=rows[-1]['supply_k']-273.15,final_return_C=max(rows[-1]['rack_return_k'])-273.15,
        final_flow_m3_h=rows[-1]['flow_m3_s']*3600,minimum_branch_flow_m3_h=min(min(r['branch_flows_m3_s']) for r in rows)*3600,
        first_tracking_suspected_s=next((f['time_ns']/1e9 for f in phases if f['PRE']['state']=='TRACKING_FAULT_SUSPECTED'),None),
        first_tracking_confirmed_s=first_confirm,first_safety_fault_s=first_fault,
        supply45='CONDITIONAL_MET' if maximum<=45 else 'CONDITIONAL_EXCEEDED',supply44_target='CONDITIONAL_MET' if maximum<=44 else 'CONDITIONAL_EXCEEDED',
        OEM='CALIBRATION_REQUIRED',equipment='INCOMPLETE_VENDOR_MAPS_AND_GEOMETRY',no_aggregate_equipment_PASS=True,
        final_rack_inlet_C=[rows[-1]['supply_k']-273.15]*n,
        final_rack_return_C=[t-273.15 for t in rows[-1]['rack_return_k']],
        final_branch_flow_m3_h=[q*3600 for q in rows[-1]['branch_flows_m3_s']],
        finite_horizon_only=True,return45_limit='NOT_APPLICABLE',formal_C3C=False)
