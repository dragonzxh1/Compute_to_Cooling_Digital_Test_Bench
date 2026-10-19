"""Independent persisted-evidence audit: deliberately imports NO plant/solver/M1."""
import json
from math import fsum,exp,sqrt
from hashlib import sha256
from .streaming import FileArray

CV=1009*4000
V=[.1,*([.025]*6),*([.15]*6),.15]
def read(p):return json.loads(p.read_bytes())
def require(ok,code):
    if not ok:raise ValueError(code)
def digest(d):return sha256(json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def close(a,b,ops=1024):
    g=ops*2**-53/(1-ops*2**-53)
    require(abs(a-b)<=g*max(1.,abs(a)+abs(b)),'INDEPENDENT_EQUATION_DIFFERENCE')

def close_rate(a,b,operand_scale):
    # Cancellation needs an absolute forward-error bound on the ORIGINAL
    # operands, not the almost-zero residual. 4096 roundoff operations,
    # independent of verdict/customer tolerances; a 1 W corruption still fails.
    g=4096*2**-53/(1-4096*2**-53)
    require(abs(a-b)<=g*max(1.,operand_scale,abs(a)+abs(b)),
            'INDEPENDENT_RATE_EQUATION_DIFFERENCE')

def verify_measurement(o,m,now):
    valid=o['quality']=='VALID' and now-o['sample_ns']<=1_000_000_000
    require(m['quality']==('VALID' if valid else 'MISSING'),'MEASUREMENT_QUALITY_MASK')
    if valid:close(o['pump_speed'],m['measured_speed'])
    else:require(m['measured_speed'] is None,'STALE_MEASUREMENT_NOT_MASKED')
def stored(s,header_volume=2.75,tank_volume=15.,wall_j_k=0.):
    total=fsum(CV*fsum(v*t for v,t in zip(V,[u['supply_header_k'],*u['inlet_k'],*u['rack_return_k'],u['return_k']])) for u in s['units'])
    if s['tank_A_k'] is not None:
        total+=fsum((CV*tank_volume+wall_j_k)/len(s[k])*fsum(s[k]) for k in ('tank_A_k','tank_B_k'))
        total+=fsum(CV*s.get('source_pipe_volumes_m3',{}).get(k,header_volume)/10*fsum(t) for k,t in s['source_pipe_k'].items())
    return total+CV*s.get("neutral_buffer_m3",0)*s.get("neutral_buffer_k",0)

def _unchanged_physics_audit(directory,spec):
    series=read(directory/'series.json');physics=FileArray(directory/'physics.json',round(spec['seconds']/spec['dt_s']))
    phases=read(directory/'phases.json');measurements=read(directory/'measurements.json')
    source=read(directory/'source_phases.json');result=read(directory/'result.json')
    factors=[.8,1,1.2,1.4,.9,1.1] if spec.get('unbalanced') else [1]*6
    qd=68.37/3600;bd=qd/6;bk=[171630*f/bd**2 for f in factors]
    equiv=1/fsum(1/sqrt(k) for k in bk)**2;common=(26600+123580+50000)/qd**2
    n=0;max_local=0.;liquid=pump=rejected=gained=0.
    for interval in physics:
        dt=(interval['end_ns']-interval['start_ns'])/1e9
        liquid+=883500*result['units']*dt
        pump+=dt*(interval.get('primary_pump_electrical_w',0.)+fsum(u['pump_electrical_w'] for u in interval['unit_records']))
        rejected+=dt*(interval['rejected_w'] if spec['scope']=='GROUP18' else interval['unit_records'][0]['hx_w'])
        gained+=dt*interval.get('ambient_gain_w',0.)
        for u in interval['unit_records']:
            q=u['flow_m3_s'];flows=u['branch_flow_m3_s'];old=u['old_k'];new=u['new_k'];d=u['edge_drops_pa']
            close(q,fsum(flows));close(u['dp_pa'],(common+equiv)*q*q)
            for i,f in enumerate(flows):
                close(f*f*bk[i],equiv*q*q)
                close(d['inlet'+str(i)],.1*bk[i]*f*f)
                close(d['rack'+str(i)],.9*bk[i]*f*f)
            close(u['pump_electrical_w'],u['dp_pa']*q/.65)
            close(u['pump_to_liquid_w'],u['pump_electrical_w'])
            cs=CV*q;cp=CV*u['primary_flow_m3_s'];cmin=min(cs,cp);cmax=max(cs,cp)
            if cmin==0:hx=0.
            else:
                cr=cmin/cmax;ntu=spec['ua_w_k']/cmin;e=exp(-ntu*(1-cr))
                epsilon=ntu/(1+ntu) if abs(1-cr)<1e-10 else (1-e)/(1-cr*e)
                hx=epsilon*cmin*(old[-1]-u['primary_inlet_k'])
            close(hx,u['hx_w'])
            supply_loss=q*(d['HX']+d['supply_pipe_filter'])
            rates=[CV*q*(old[-1]-old[0])-hx+supply_loss]
            rates += [CV*f*(old[0]-old[1+i])+f*d['inlet'+str(i)] for i,f in enumerate(flows)]
            rates += [CV*f*(old[1+i]-old[7+i])+147250+f*d['rack'+str(i)] for i,f in enumerate(flows)]
            rates += [fsum(CV*f*(old[7+i]-old[-1]) for i,f in enumerate(flows))+u['pump_electrical_w']-u['dp_pa']*q+q*(d['return_filter']+d['return_pipe'])]
            require(u['rack_it_w']==[155000]*6 and u['rack_liquid_w']==[147250]*6,'FULL_LOAD_IDENTITY')
            operand_scale=CV*q*2*max(map(abs,old))+abs(hx)+u['pump_electrical_w']+883500
            for a,b,v,r,recorded in zip(old,new,V,rates,u['local_rates_w']):
                close_rate(r,recorded,operand_scale);err=(b-a)*CV*v-dt*r
                close(b*CV*v,a*CV*v+dt*r);max_local=max(max_local,abs(err));n+=1
        for t in interval.get('tank_records',{}).values():
            old=t['old_k'];new=t['new_k'];fl=t['load_m3_s'];fs=t['source_m3_s']
            expected=dt*(CV*(fl*(t['return_k']-old[0])+fs*(t['source_in_k']-old[-1]))+t['pump_loss_w']+t.get('environment_heat_w',0.))
            cap=(CV*spec.get('tank_volume_m3',15.)+spec.get('wall_j_k',0.))/len(old)
            close(cap*fsum(new),cap*fsum(old)+expected,8192)
    initial,final=(stored(s,spec.get('header_volume_m3',2.75),spec.get('tank_volume_m3',15.),spec.get('wall_j_k',0.)) for s in (series[0],series[-1]));residual=final-initial-liquid-pump+rejected-gained
    ops=8192*(len(physics)+1);g=ops*2**-53/(1-ops*2**-53)
    bound=g*(abs(initial)+abs(final)+liquid+pump+rejected)
    require(abs(residual)<=bound,'INDEPENDENT_GLOBAL_ENERGY')
    byid={(m['unit'],m['measurement_record_id']):m for m in measurements};previous={};fault={};suspected={};confirmed={}
    for f in phases:
        i=f['unit'];pre,safety,plc,post=(f[k] for k in ('PRE','SAFETY','PLC','POST'))
        m=pre['measurement'];o=byid[i,m['measurement_record_id']]
        require(o['sample_ns']==m['sample_ns'] and o['available_ns']==m['release_ns']<=f['time_ns'],'CAUSAL_SAMPLE_RELEASE')
        verify_measurement(o,m,f['time_ns'])
        if i in previous:
            require(pre['old_command']['value']==previous[i]['command'] and pre['old_command']['issue_ns']==previous[i]['issue_ns'],'PRE_FUTURE_COMMAND')
        # Frozen Record uses canonical-json SHA; bindings are audited against
        # stored immutable digests, never recomputed by the candidate reducer.
        require(safety['pre_digest']==f['immutable_pre_digest'] and plc['safety_digest']==f['immutable_safety_digest'],'PHASE_BINDING')
        require(post['pre_id']==pre['record_id'] and post['plc_id']==plc['record_id'] and plc['safety_id']==safety['record_id'],'PLC_POST_BINDING')
        require(f['actuator_command']['producer_module']=='PLC' and f['envelope']['minimum_speed']<=plc['command']<=f['envelope']['maximum_speed'],'PLC_OWNERSHIP')
        if i in fault:require(safety['severity']=='FAULT','FAULT_AUTO_RESET')
        if safety['severity']=='FAULT':fault.setdefault(i,f['time_ns']/1e9)
        if pre['state']=='TRACKING_FAULT_SUSPECTED':suspected.setdefault(i,f['time_ns']/1e9)
        if pre['state']=='TRACKING_FAULT_CONFIRMED':confirmed.setdefault(i,f['time_ns']/1e9)
        previous[i]=plc
    prior=None
    for f in source:
        o=f['measurement'];r=f['request'];s=f['safety'];p=f['PLC']
        require(o['sample_ns']<=o['release_ns']<=f['time_ns'],'SOURCE_FUTURE_MEASUREMENT')
        require(digest(s['data'])==s['sha256'] and digest(p['data'])==p['sha256'],'SOURCE_EVIDENCE_HASH')
        require(p['data']['safety_sha256']==s['sha256']==r['permission'] and r['observation_id']==o['record_id'],'SOURCE_PLC_BINDING')
        if prior and (r['source_tank'],r['source_path'])!=(prior['source_tank'],prior['source_path']):
            require(o['source_speed']<=1e-9 and o['source_valve']<=1e-9,'SOURCE_BREAK_BEFORE_MAKE')
        require(not(r['recharge_enable'] and r['source_path']=='W2') or (spec.get('independent_recharge') and r.get('recharge_path')=='RC'),'SOURCE_ROLE_CONFLICT');prior=r
    maximum=max(max(u['inlet_k'])-273.15 for x in series for u in x['units'])
    minflow=min(min(u['branch_flows_m3_s'])*3600 for x in series for u in x['units'])
    fault_at=spec.get('fault_at_s');window=[x for x in series if fault_at is not None and fault_at<=x['time_ns']/1e9<=fault_at+90]
    winmax=max((max(u['inlet_k'])-273.15 for x in window for u in x['units']),default=None)
    returned=result['source_returned_at_ns'];ready_latency=None if returned is None or fault_at is None else returned/1e9-fault_at
    # State-machine readiness is NOT proof that cold water reached the tank.
    # Check every physical interval's actual available-source flow and return.
    recovery=next((r['end_ns']/1e9 for r in physics if fault_at is not None and returned is not None
        and r['start_ns']>=returned and r['source_available'][r['source_path']]
        and r['source_flow_m3_h']>=.8*330 and r['source_return_k']<=314.5948),None)
    latency=None if recovery is None or fault_at is None else recovery-fault_at
    # Measured90s window must cover all90s; no continuity credit for no fault.
    continuity='NOT_APPLICABLE_NO_CHANGEOVER'
    if window:
        continuity='CONDITIONAL_MET' if len(window)>=91 and winmax<=45 and latency is not None and latency<=90 else 'CONDITIONAL_NOT_MET'
    grades=dict(MODEL_NUMERICAL_VALIDITY='EQUATIONS_VERIFIED_FINITE_HORIZON',EQUIPMENT_SUITABILITY='NOT_VERIFIED',
        HYDRAULIC_ADEQUACY='CONDITIONAL_DESIGN_FLOW_MET' if minflow>=68.37/6*(1-1e-9) else 'CONDITIONAL_DESIGN_FLOW_SHORTFALL',
        THERMAL_ADEQUACY='CONDITIONAL_45C_MET' if maximum<=45 else 'CONDITIONAL_45C_EXCEEDED',
        CHANGEOVER_CONTINUITY=continuity,M1_CAUSAL_VALIDITY='PROJECT_OBSERVED_TRANSACTIONS_VERIFIED_NOT_INHERITED_C3C',
        OEM_CALIBRATION_STATUS='CALIBRATION_REQUIRED')
    return dict(grades=grades,no_aggregate_engineering_pass=True,control_volumes_checked=n,
        independent_energy=dict(initial_j=initial,final_j=final,liquid_j=liquid,pump_j=pump,export_j=rejected,environment_gain_j=gained,residual_j=residual,bound_j=bound,max_local_residual_j=max_local),
        maximum_inlet_c=maximum,secondary44C_target_met=maximum<=44.,maximum_return_c=result['maximum_rack_return_c'],minimum_branch_flow_m3_h=minflow,
        final_primary_inlet_c=series[-1]['primary_inlet_c'],primary_inlet_range_c=[min(s['primary_inlet_c'] for s in series),max(s['primary_inlet_c'] for s in series)],
        transactions=len(phases),source_transactions=len(source),first_fault_s=fault,first_tracking_suspected_s=suspected,first_tracking_confirmed_s=confirmed,
        changeover_window_maximum_inlet_c=winmax,takeover_latency_s=latency,coordinator_ready_latency_s=ready_latency,
        recovery_definition='FIRST_ACTUAL_AVAILABLE_SOURCE_FLOW_GE264M3H_AND_TANK_RETURN_LE41_4448C_AFTER_STARTUP_READY_NOT_CONTINUOUS_STABILITY_PROOF',
        maximum_recharge_flow_m3_h=max((r.get('recharge_flow_m3_h',0.) for r in physics),default=0.),
        maximum_recharge_requested_speed=max((r.get('recharge_requested_speed_unclipped',0.) for r in physics),default=0.),
        maximum_recharge_actual_speed=max((r.get('recharge_actual_speed',0.) for r in physics),default=0.),
        final_units=result['final_units'],final_inlet_c=max(max(u['inlet_k'])-273.15 for u in result['final_units']),
        final_return_c=max(max(u['rack_return_k'])-273.15 for u in result['final_units']),
        recharge_done=result['requested_recharge_done'],
        source_timeline=result['source_timeline'],final_cold_B_m3=series[-1]['cold_B_m3'],
        actual_equipment_ua=None,npshr=None,design_selections=None,air_heat_w=46500*result['units'],
        limitations=['No OEM calibration or pressure/MAWP/NPSHr guarantee','Finite horizon not steady-state proof','A_LEAK_SIGNAL tests measured isolation logic, not leak-rate or mass-loss physics','Zero-flow motor/deadhead losses not calibrated','Secondary45C is rack inlet, not return or GPU die','Shared source headers remain common cause','M1 period1s/5s is new project scheduling, not inherited formal detection guarantee'])

