"""Persisted independent equations and event gates. Does not import the plant."""
import json
from math import fsum,sqrt,exp,isfinite
from hashlib import sha256

def read(p):return json.loads(p.read_bytes())
def need(ok,why):
    if not ok:raise ValueError(why)
def bound(*v,ops=4096):
    g=ops*2**-53/(1-ops*2**-53);return g*max(1.,fsum(abs(x) for x in v))
def close(a,b,why,scale=None):need(abs(a-b)<=bound(a,b) if scale is None else abs(a-b)<=bound(*scale),why)
def digest(v):return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def causal(phases,observations):
    byid={o['measurement_record_id']:o for o in observations};prior=None;latch=False;confirmed=None
    for f in phases:
        pre,safe,plc,post=(f[k] for k in ('PRE','SAFETY','PLC','POST'));m=pre['measurement'];o=byid[m['measurement_record_id']]
        need(o['sample_ns']==m['sample_ns'] and o['available_ns']==m['release_ns']<=f['time_ns'],'FUTURE_OR_UNRELEASED_SAMPLE')
        need(digest(pre)==f['immutable_pre_digest']==safe['pre_digest'],'PRE_IMMUTABILITY')
        need(digest(safe)==f['immutable_safety_digest']==plc['safety_digest'],'SAFETY_IMMUTABILITY')
        need(post['plc_id']==plc['record_id'] and post['pre_id']==pre['record_id'] and plc['safety_id']==safe['record_id'],'WRONG_PLC_RECEIPT')
        if prior:need(pre['old_command']['value']==prior['command'] and pre['old_command']['issue_ns']==prior['issue_ns'],'PRE_FUTURE_COMMAND')
        if latch:need(safe['severity']=='FAULT','FAULT_LATCH_CLEARED')
        latch=latch or safe['severity']=='FAULT'
        if pre['state']=='TRACKING_FAULT_CONFIRMED' and confirmed is None:confirmed=f['time_ns']/1e9
        need(f['actuator_command']['producer_module']=='PLC','WRONG_COMMAND_ISSUER')
        if f.get('fast_permission'):
            p=f['fast_permission'];need(digest(p['data'])==p['sha256'],'FAST_PERMISSION_HASH')
            b=f.get('backup_PLC')
            if b:
                need(digest(b['data'])==b['sha256'] and b['data']['producer']=='MEMPHIS_SIMULATED_BACKUP_PLC','BACKUP_RECEIPT')
                # Receipt is persistent and bound to its original permission,
                # not falsely rebound to a newer sensor frame.
                need(b['data']['time_ns']<=f['time_ns'],'FUTURE_BACKUP_ISSUE')
            bo=f.get('backup_measurement')
            if bo:need(bo['sample_ns']<=bo['release_ns']<=f['time_ns'],'FUTURE_BACKUP_SENSOR')
        prior=plc
    return dict(transactions=len(phases),tracking_confirmed_s=confirmed,fault_latched=latch)

def first_held(rows,predicate,start_ns=10_000_000_000,hold_ns=5_000_000_000):
    first=None
    for r in rows:
        if r['time_ns']<start_ns:continue
        if predicate(r):
            if first is None:first=r['time_ns']
            if r['time_ns']-first>=hold_ns:return first/1e9
        else:first=None
    return None

def terminal_held(rows,predicate,hold_ns=5_000_000_000):
    last=rows[-1]['time_ns'];tail=[r for r in rows if r['time_ns']>=last-hold_ns]
    return bool(tail) and tail[0]['time_ns']<=last-hold_ns and all(predicate(r) for r in tail)

def source_change_cut(before,after):
    # Selection happens before the new valve's first opening movement.
    # Never use a later closed state to excuse an unsafe earlier selection.
    need(max(before['source_supply_valve'],before['source_return_valve'])<=1e-9 and before['source_speed']<=1e-9 and after['source_speed']<=1e-9,'SOURCE_AB_NOT_ISOLATED')

def unit(directory):
    inp=read(directory/'input.json');c=inp['config'];spec=inp['spec'];rows=read(directory/'series.json');steps=read(directory/'physics.json')
    phases=read(directory/'phases.json');causality=causal(phases,read(directory/'measurements.json'))
    bytime={r['time_ns']:r for r in rows}
    for o in read(directory/'measurements.json'):
        if o['quality']!='VALID':continue
        r=bytime[o['sample_ns']]
        need(o['pump_speed']==r['main_speed'] and o['supply_k']==r['supply_k'] and o['rack_return_k']==r['rack_return_k'],'PHYSICAL_MEASUREMENT_BINDING')
        need(o['source_ids']==[r['main_actuator_state_id'],r['hydraulic_solution_id']],'MEASUREMENT_SOURCE_BINDING')
    cv=c['density_kg_m3']*c['cp_j_kg_k'];caps=[cv*v for v in c['volumes_m3']]
    qd=c['design_flow_m3_s'];n=c['rack_count'];kc=(c['design_dp_pa']-c['branch_dp_pa'])/qd**2
    kb=[c['branch_dp_pa']*f/(qd/n)**2 for f in c['branch_factors']];ke=1/fsum(1/sqrt(k) for k in kb)**2
    kp=c['design_dp_pa']*(c['quadratic_shutoff_factor']-1)/qd**2
    h0=c['design_dp_pa']*c['quadratic_shutoff_factor']/c['design_speed']**2*spec.get('pump_factor',1)
    need(len(steps)==c['duration_ns']//c['dt_ns'] and len(rows)==len(steps)+1,'MISSING_PHYSICAL_INTERVAL')
    heat=pump=hxsum=0.;maxerr=0.
    for i,s in enumerate(steps):
        old=s['old_k'];new=s['new_k'];dt=(s['end_ns']-s['start_ns'])/1e9
        a,b=rows[i:i+2]
        need(s['start_ns']==a['time_ns'] and s['end_ns']==b['time_ns'],'TIME_GAP')
        need(old==[a['supply_k'],*a['rack_return_k'],a['return_k']] and new==[b['supply_k'],*b['rack_return_k'],b['return_k']],'SERIES_PHYSICS_BINDING')
        q=sqrt(h0*s['effective_speed']**2/(kc*s['common_factor']+ke+kp));dp=(kc*s['common_factor']+ke)*q*q
        close(q,s['flow_m3_s'],'Q_H_INTERSECTION');close(dp,s['dp_pa'],'NETWORK_PRESSURE')
        fs=[sqrt(ke*q*q/k) for k in kb];close(fsum(fs),q,'MASS_CONSERVATION')
        for x,y in zip(fs,s['branch_flows_m3_s']):close(x,y,'BRANCH_FLOW')
        electric=q*dp/c['wire_efficiency'];close(electric,s['pump_electrical_w'],'PUMP_ELECTRICAL')
        close(electric,s['hydraulic_w']+s['pump_liquid_loss_w'],'PUMP_HEAT_TWICE')
        small,large=sorted((cv*q,cv*c['primary_flow_m3_s']))
        if small==0:hx=0.
        else:
            cr=small/large;ntu=c['hx_ua_w_k']/small;e=exp(-ntu*(1-cr));eps=ntu/(1+ntu) if abs(1-cr)<1e-10 else (1-e)/(1-cr*e)
            hx=small*eps*(old[-1]-c['primary_inlet_k'])
        close(hx,s['hx_w'],'INDEPENDENT_HX')
        loads=s['rack_it_w'];rates=[cv*q*(old[-1]-old[0])-hx+kc*s['common_factor']/2*q**3]
        rates += [cv*f*(old[0]-t)+.95*w+k*f**3 for f,t,w,k in zip(fs,old[1:-1],loads,kb)]
        rates += [fsum(cv*f*(t-old[-1]) for f,t in zip(fs,old[1:-1]))+electric-dp*q+kc*s['common_factor']/2*q**3]
        scale=fsum(abs(cv*f*t) for f,t in zip([q,*fs,q],old))+fsum(loads)+abs(hx)+electric
        for x,y,cap,rate,reported in zip(old,new,caps,rates,s['rates_w']):
            close(rate,reported,'RATE_RECONSTRUCTION',[scale]);err=(y-x)*cap-dt*rate
            need(abs(err)<=bound(x*cap,y*cap,dt*rate),'LOCAL_ENERGY');maxerr=max(maxerr,abs(err))
        heat+=.95*fsum(loads)*dt;pump+=electric*dt;hxsum+=hx*dt
        need(all(isfinite(v) for v in old+new),'NONFINITE_EVIDENCE')
    initial=fsum(x*cap for x,cap in zip(steps[0]['old_k'],caps));final=fsum(x*cap for x,cap in zip(steps[-1]['new_k'],caps))
    residual=final-initial-heat-pump+hxsum;limit=bound(initial,final,heat,pump,hxsum,ops=8192*(len(steps)+1))
    need(abs(residual)<=limit,'GLOBAL_ENERGY')
    for a,b in zip(rows,rows[1:]):
        if (a['active_cdu'],a['active_pump'])!=(b['active_cdu'],b['active_pump']):need(b['valve_opening']==0,'ILLEGAL_AB_OR_PUMP_PARALLEL')
    mx=max(r['supply_k']-273.15 for r in rows);events=read(directory/'events.json')
    flow=first_held(rows,lambda r:r['flow_m3_s']>=.99*qd and (r['active_cdu'],r['active_pump'])!=(0,0))
    pressure=first_held(rows,lambda r:r['dp_pa']>=.99*c['design_dp_pa'] and (r['active_cdu'],r['active_pump'])!=(0,0))
    temp=first_held(rows,lambda r:r['supply_k']<=318.15 and (r['active_cdu'],r['active_pump'])!=(0,0))
    thermal='PASS' if mx<=45 else 'FAIL'
    transfer_required=spec.get('fault') in ('STUCK','CDU_LOSS','RESTRICTION') or bool(events)
    terminal=terminal_held(rows,lambda r:r['flow_m3_s']>=.99*qd and r['dp_pa']>=.99*c['design_dp_pa'] and r['supply_k']<=318.15)
    recover=flow is not None and pressure is not None and temp is not None and terminal
    if spec.get('fault')=='STUCK':
        frozen=[r for r in rows if r['time_ns']>=10_000_000_000]
        need(len({r['main_speed'] for r in frozen})==1 and max(r['main_command'] for r in frozen)-frozen[0]['main_speed']>=.15,'INVALID_STUCK_EXCITATION')
        need(causality['tracking_confirmed_s'] is not None,'STUCK_TRACKING_CONFIRMATION_MISSING')
    full=all(all(w==155000 for w in r['rack_it_w']) for r in rows if r['time_ns']>=10_000_000_000)
    grade=dict(SOFTWARE_EXECUTION_VALIDITY='PASS',PHYSICAL_NUMERICAL_VALIDITY='PASS',CDU_EQUIPMENT_SUITABILITY='NOT_VERIFIED',PUMP_EQUIPMENT_SUITABILITY='NOT_VERIFIED',RACK_THERMAL_COMPLIANCE=thermal,RACK_HYDRAULIC_COMPLIANCE='NOT_VERIFIED',FAILOVER_RECOVERY=('PASS' if recover else 'FAIL') if transfer_required else 'INCOMPLETE',FULL_LOAD_CONTINUITY='PASS' if full and thermal=='PASS' and terminal and (recover or not transfer_required) else 'FAIL',SOURCE_COOLING_ADEQUACY='NOT_VERIFIED',OEM_CALIBRATION_STATUS='NOT_VERIFIED',CUSTOMER_DESIGN_APPROVAL_STATUS='INCOMPLETE',**{'90_SECOND_BUFFER_COMPLIANCE':'INCOMPLETE'})
    if spec.get('loads'):grade['FULL_LOAD_CONTINUITY']='INCOMPLETE'
    return dict(case_id=spec['id'],kind='unit',grades=grade,maximum_inlet_c=mx,final_inlet_c=rows[-1]['supply_k']-273.15,
        final_return_c=max(rows[-1]['rack_return_k'])-273.15,final_mixed_return_c=rows[-1]['return_k']-273.15,
        final_flow_m3_h=rows[-1]['flow_m3_s']*3600,final_branches_m3_h=[f*3600 for f in rows[-1]['branch_flows_m3_s']],
        maximum_it_w=max(fsum(r['rack_it_w']) for r in rows),minimum_branch_m3_h=min(min(r['branch_flows_m3_s']) for r in rows)*3600,
        events=events,flow_recovered_s=flow,pressure_recovered_s=pressure,temperature_recovered_s=temp,terminal_recovery_maintained=terminal,
        thermal_exceedance_K_s=fsum(max(0,r['supply_k']-318.15)*c['dt_ns']/1e9 for r in rows[:-1]),
        liquid_j=heat,pump_j=pump,hx_j=hxsum,global_residual_j=residual,global_bound_j=limit,max_local_residual_j=maxerr,
        causal=causality,steps=len(steps),condition='MODEL_ASSUMPTIONS_ONLY; shared rack inventory; inactive CDU internal inventory unknown',procurement='NOT_RELEASED')

def source_ready(s,threshold):
    return (s['source_available'][s['source_path']] and
        s['source_flow_m3_h']>=threshold-1e-8 and s['source_return_k']<=314.5948)

def first_post_fault_cold(steps,fault,threshold):
    # The interval ending exactly at fault is still pre-fault physics.
    # Availability alone is not a recovery receipt: require a post-fault
    # interval, an available selected source, real design flow and cold return.
    return next((s['end_ns']/1e9-fault for s in steps
        if s['start_ns']>=round(fault*1e9) and source_ready(s,threshold)),None)

def terminal_source_ready(steps,threshold,hold_s=5.):
    end=steps[-1]['end_ns'];begin=end-round(hold_s*1e9)
    window=[s for s in steps if s['end_ns']>begin]
    return bool(window and window[0]['start_ns']<=begin and
        all(source_ready(s,threshold) for s in window))

def group(directory,spec):
    # Dedicated group equation audit retained independently of the copied plant.
    from .group_model.legacy_audit import _unchanged_physics_audit as audit
    analysis=audit(directory,spec)
    rows=read(directory/'series.json');steps=read(directory/'physics.json');fault=spec.get('fault_at_s',30.)
    window=[s for s in steps if fault< s['end_ns']/1e9<=fault+90]
    maximum=max(max(max(u['new_k'][1:7])-273.15 for u in s['unit_records']) for s in window)
    transfer_required=bool(spec.get('fault'))
    strict=first_post_fault_cold(steps,fault,330) if transfer_required else None
    old=first_post_fault_cold(steps,fault,264) if transfer_required else None
    terminal=terminal_source_ready(steps,330)
    for s in steps:need(s['recharge_flow_m3_h']==0 or spec.get('recharge')=='INDEPENDENT','UNREGISTERED_RECHARGE_PUMP')
    switches=[]
    for a,b in zip(steps,steps[1:]):
        if a['load_tank']!=b['load_tank']:
            need(max(b['load_supply_valve'],b['load_return_valve'])<=1e-9,'LOAD_AB_NOT_ISOLATED')
            switches.append(dict(time_s=b['end_ns']/1e9,from_tank=a['load_tank'],to_tank=b['load_tank']))
        if (a['source_tank'],a['source_path'])!=(b['source_tank'],b['source_path']):
            source_change_cut(a,b)
    allmax=max(max(max(u['new_k'][1:7])-273.15 for u in s['unit_records']) for s in steps)
    recovery=next((r['time_ns']/1e9 for r in rows if r['cold_A_m3']>=10 and r['cold_B_m3']>=8.25 and r['time_ns']/1e9>=120),None)
    recharge=spec.get('recharge')
    recharge_peak=max((s['recharge_flow_m3_h'] if recharge=='INDEPENDENT' else s['source_flow_m3_h'] if s['source_tank']=='B' and s['load_tank']=='A' else 0 for s in steps if s['end_ns']/1e9>=120),default=0.)
    recovered=strict is not None and strict<=90 and terminal
    grades=dict(SOFTWARE_EXECUTION_VALIDITY='PASS',PHYSICAL_NUMERICAL_VALIDITY='PASS',CDU_EQUIPMENT_SUITABILITY='NOT_VERIFIED',PUMP_EQUIPMENT_SUITABILITY='NOT_VERIFIED',RACK_THERMAL_COMPLIANCE='PASS' if allmax<=45 else 'FAIL',RACK_HYDRAULIC_COMPLIANCE='NOT_VERIFIED',FAILOVER_RECOVERY=('PASS' if recovered else 'FAIL') if transfer_required else 'INCOMPLETE',FULL_LOAD_CONTINUITY='PASS' if allmax<=45 and terminal and (recovered or not transfer_required) else 'FAIL',SOURCE_COOLING_ADEQUACY='NOT_VERIFIED',OEM_CALIBRATION_STATUS='NOT_VERIFIED',CUSTOMER_DESIGN_APPROVAL_STATUS='INCOMPLETE',**{'90_SECOND_BUFFER_COMPLIANCE':'INCOMPLETE'})
    dt=spec['dt_s'];exceed=fsum(max(0,max(max(u['new_k'][1:7])-273.15 for u in s['unit_records'])-45)*dt for s in steps)
    persecond=[dict(time_s=s['end_ns']/1e9,stored_j=s['stored_j'],rejected_w=s['rejected_w'],pump_w=s['primary_pump_electrical_w']+s['secondary_pump_electrical_w'],tank_A_cold_m3=s['tank_A_cold_m3'],tank_B_cold_m3=s['tank_B_cold_m3'],primary_c=s['primary_inlet_c'],source_m3_h=s['source_flow_m3_h'],load_m3_h=s['load_flow_m3_h']) for s in window if s['end_ns']%1_000_000_000==0]
    return dict(case_id=spec['id'],kind='group',grades=grades,maximum_inlet_c=allmax,first90_maximum_inlet_c=maximum,
        first_cold_return_330_delay_s=strict,historical_264_threshold_delay_s=old,actual_AB_switches=switches,
        terminal_source_recovery_maintained=terminal,recovery_definition='POST_FAULT_INTERVAL_AVAILABLE_SOURCE_DESIGN_FLOW_COLD_RETURN; FIRST_RETURN_NOT_CONTINUITY; FINAL5S_REQUIRED',
        thermal_exceedance_K_s=exceed,thermal_exceedance_duration_s=sum(max(max(u['new_k'][1:7])-273.15 for u in s['unit_records'])>45 for s in steps)*dt,
        reserve_ready_absolute_s=recovery,minimum_cold_A_m3=min(s['tank_A_cold_m3'] for s in steps),final_cold_A_m3=rows[-1]['cold_A_m3'],final_cold_B_m3=rows[-1]['cold_B_m3'],
        recharge_flow_comparison=dict(required_m3_h=330,maximum_actual_m3_h=recharge_peak,status=('PASS' if recharge_peak>=330-1e-8 else 'FAIL') if recharge else 'INCOMPLETE'),
        first90_energy_rows=persecond,independent=analysis,steps=len(steps),condition='CONDITIONAL_UNCALIBRATED_TOWER_CURVES; paired valves synchronized assumption; no pressure transient model')
