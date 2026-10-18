"""Persisted equations/causality and disaggregated engineering verdicts; no plant import."""
import json,hashlib,gc
from math import fsum,sqrt
from pathlib import Path
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def close(a,b):need(abs(a-b)<=4096*2**-53/(1-4096*2**-53)*max(1,abs(a)+abs(b)),'PRIMARY_QH_MASS_PUMP_HEAT')
def primary(rows,c):
    if not c.get('extensions'):return dict(status='LEGACY_SECONDARY_HX_ENERGY_CAUSAL_AUDIT_RETAINED',steps=0)
    Q=330/3600;rho=1009.;G=9.80665;eta=c.get('primary_efficiency',.7);pidK=(rho*G*18-115820)/(110/3600)**2;n=0
    for r in rows:
        v=r['load_valve'];kl=(135920+20000/max(v,.001)**2)/Q**2*r['load_resistance_factor']
        ql=sqrt((155920*1.25/.9**2)*.9**2/(kl+155920/Q**2*.25)) if v>1e-9 else 0.
        wet=r['source_path'].startswith('W');dp=96520 if wet else 63210;m=r['active_module_count']
        ks=dp*(.2/max(r['source_valve'],.001)**2+.8*((5/m)**2 if wet else 1))/Q**2
        h0=rho*G*(34*1.2 if c['source_variant']=='V9' else 18)
        kp=(rho*G*34*.2/(115/3600)**2 if c['source_variant']=='V9' else pidK)/r['actual_source_pumps']**2
        qs=sqrt(h0*c.get('source_head_factor',1)*r['source_speed']**2/(ks+kp)) if r['source_valve']>1e-9 and r['source_speed']>1e-9 and (r['source_header_available'] or r['source_path']=='W3') else 0.
        kr=c.get('recharge_dp_kpa',115.82)*1000/Q**2
        qr=sqrt(rho*G*18*c.get('recharge_head_factor',1)*r['recharge_actual_speed']**2/(kr+pidK/9)) if r['recharge_actual_speed']>1e-9 else 0.
        aux=fsum(q/3600*20000/.65 for q in r['aux_actual_flows_m3_h'].values());close(aux,r['aux_pump_w'])
        for actual,expected in ((r['load_flow_m3_h'],ql*3600),(r['source_flow_m3_h'],qs*3600),(r['recharge_flow_m3_h'],qr*3600)):close(actual,expected)
        close(r['primary_pump_electrical_w'],(ql**3*kl+qs**3*ks+qr**3*kr)/eta+aux)
        for name,t in r['tank_records'].items():
            close(t['load_m3_s'],ql if name==r['load_tank'] else 0.)
            close(t['source_m3_s'],(qs if name==r['source_tank'] else 0.)+(qr if name=='B' else 0.))
        close(fsum(u['primary_flow_m3_s'] for u in r['unit_records']),ql);n+=1
    return dict(status='INDEPENDENT_PRIMARY_QH_MASS_PUMP_HEAT_VERIFIED',steps=n)
def evaluate(d,c):
    from .group_model.legacy_audit import _unchanged_physics_audit
    independent=_unchanged_physics_audit(d,c);gc.collect()
    rows=read(d/'physics.json');series=read(d/'series.json');frames=read(d/'source_phases.json');out=read(d/'result.json');hyd=primary(rows,c)
    from .audit import causal
    phases=read(d/'phases.json');observations=read(d/'measurements.json')
    for unit in range(3):causal([f for f in phases if f['unit']==unit],[m for m in observations if m['unit']==unit])
    del phases,observations;gc.collect()
    if c.get('extensions'):
        since={}
        for f in frames:
            o=f['measurement'];now=f['time_ns'];expected={}
            for path,a,b,q,av in [('W2',o['standby_near_c'],o['standby_far_c'],o['standby_flow_m3_s'],o['w2_available']),('W3',o['third_near_c'],o['third_far_c'],o['third_flow_m3_s'],o['third_available'])]:
                acceptable=0<=now-o['ready_sample_ns']<=round(c.get('source_ready_ttl_s',.6)*1e9) and max(a,b)+.2<=41.4448 and abs(a-b)<=.3 and q>=c.get('ready_flow_m3_h',60)/3600 and av and o['deadleg_verified']
                if acceptable:since.setdefault(path,now)
                else:since.pop(path,None)
                expected[path]=bool(acceptable and now-since.get(path,now)>=round(c.get('ready_hold_s',1)*1e9))
            need(expected==f['safety']['data']['measured_cold_ready'],'INDEPENDENT_READY_RECONSTRUCTION')
            if f['request']['recharge_enable']:need(c.get('independent_recharge') and f['request']['recharge_path']=='RC','DOUBLE_USE_ONLINE_SOURCE')
    fault=c.get('fault_at_s',30.);dt=c['dt_s'];end=c['seconds']
    fault_required=bool(c.get('fault') or c.get('module_loss') or c.get('common_load_loss_at_s') or c.get('common_source_loss_at_s'))
    temp=lambda r:max(max(u['new_k'][1:7])-273.15 for u in r['unit_records'])
    good=lambda r:r['source_available'].get(r['source_path'],False) and r['source_flow_m3_h']>=330-1e-8 and r['source_return_k']<=314.5948
    post=[r for r in rows if r['start_ns']>=round(fault*1e9)];window=[r for r in post if r['end_ns']<=round((fault+90)*1e9)]
    need(len(window)==round(90/dt),'EXACT90_WINDOW');need(len(rows)==round(end/dt),'TIME_COVERAGE')
    peak=max([temp(r) for r in rows]+[max(max(u['inlet_k'])-273.15 for u in series[0]['units'])])
    peak90=max(map(temp,window));minload=min(r['load_flow_m3_h'] for r in post)
    first=lambda rr,test:next((r['end_ns']/1e9 for r in rr if test(r)),None)
    cold=first(post,good);tail=[r for r in rows if r['end_ns']>round((end-5)*1e9)];restored=cold is not None and cold-fault<=90 and all(map(good,tail))
    codes=sorted({code for f in frames for code in f['safety']['data']['codes']})
    blocked={'SOURCE_SENSOR_STALE','SOURCE_COMMAND_WITHOUT_MEASURED_FLOW','VALVE_NOT_AT_REQUESTED_TARGET','WET_COIL_PRESSURE_RANGE_MEASURED'}&set(codes)
    thermal='PASS' if peak<=45 else 'FAIL';hydraulic='PASS' if minload>=330-1e-8 else 'FAIL'
    continuity='PASS' if peak90<=45 and min(r['load_flow_m3_h'] for r in window)>=330-1e-8 else 'FAIL'
    recovery=('PASS' if restored else 'FAIL') if fault_required else 'NOT_APPLICABLE_NO_FAULT'
    reserve='NOT_RUN' if not c.get('recharge') else 'PASS' if out['requested_recharge_done'] and all(series[-1]['cold_'+k+'_m3']>=.85*c.get('tank_volume_m3',15) for k in ('A','B')) else 'FAIL'
    required_reserve=bool(c.get('recharge'))
    expected_excitation={};events=out['source_timeline']
    if c.get('load_valve_stuck'):
        expected_excitation=dict(demand_issued=any(f['request']['load_tank']=='B' for f in frames),actual_selector_changed=any(r['load_tank']=='B' for r in rows),
            nonresponse=any(f['request']['load_tank']=='B' and f['measurement'].get('load_selector','A')=='A' for f in frames))
        need(expected_excitation['demand_issued'] and expected_excitation['nonresponse'],'STUCK_VALVE_NOT_EXCITED')
    if c.get('source_valve_stuck'):need('VALVE_NOT_AT_REQUESTED_TARGET' in codes,'SOURCE_VALVE_FAILURE_NOT_PROTECTED')
    if c.get('valve_feedback_lie'):need('SOURCE_COMMAND_WITHOUT_MEASURED_FLOW' in codes,'FALSE_OPEN_NOT_CHECKED_AGAINST_FLOW')
    if c.get('false_ready_claim') or c.get('precool_sensor_stuck_low') or c.get('ready_extra_age_s'):
        need(all(not f['safety']['data'].get('measured_cold_ready',{}).get('W2',False) for f in frames if fault<=f['time_ns']/1e9<=fault+90),'FALSE_READY_NOT_REJECTED')
    # The safety test may correctly FAIL cooling. Do not relabel that as a
    # thermal/hydraulic PASS. Causal/latched decisions are checked above.
    safety='MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED';qualified=thermal==hydraulic==continuity=='PASS' and (recovery=='PASS' or not fault_required) and not blocked and (not required_reserve or reserve=='PASS')
    if not fault_required:continuity='NOT_APPLICABLE_NO_FAULT'
    firsts=dict(thermal=first(post,lambda r:temp(r)>45),load_flow=first(post,lambda r:r['load_flow_m3_h']<330-1e-8),
        recovery_deadline=None if cold is not None and cold-fault<=90 else fault+90,
        protected=next((f['time_ns']/1e9 for f in frames if set(f['safety']['data']['codes'])&blocked),None))
    result=dict(id=c['id'],parameters=c,status='CONDITIONALLY_FEASIBLE' if qualified else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',
        grades=dict(THERMAL_COMPLIANCE=thermal,HYDRAULIC_COMPLIANCE=hydraulic,**{'90S_CONTINUITY':continuity},SOURCE_RECOVERY=recovery,RESERVE_RECOVERY=reserve,SAFETY_CORRECTNESS=safety,OEM_EVIDENCE='OEM_NOT_VERIFIED'),
        maximum_inlet_C=peak,maximum90_inlet_C=peak90,minimum_load_m3_h=minload,cold_return_delay_s=None if cold is None else cold-fault,
        normal_or_hot_operating_target_C=40 if c.get('primary_target_c')==37 else 44,operating_target_met=peak<=(40 if c.get('primary_target_c')==37 else 44),
        source_final_m3_h=rows[-1]['source_flow_m3_h'],source_final_reject_kW=rows[-1].get('main_rejected_w',rows[-1]['rejected_w'])/1000,maximum_primary_return_C=max(r['actual_primary_return_c'] for r in rows),
        max_recharge_m3_h=max(r['recharge_flow_m3_h'] for r in rows),first_violations_s=firsts,codes=codes,excitation=expected_excitation,
        first_reserve_actual_s=next((r['time_ns']/1e9 for r in series if r['time_ns']>=round(fault*1e9) and all(r['cold_'+k+'_m3']>=.85*c.get('tank_volume_m3',15) for k in ('A','B'))),None),
        final_tanks_k={k:series[-1]['tank_'+k+'_k'] for k in ('A','B')},independent_energy=independent['independent_energy'],independent_primary=hyd,
        transactions=independent['transactions'],events=events,prelude=read(d/'component_prelude.json')['ledger'] if c.get('extensions') else None,
        raw_sha256={name:sha(d/name) for name in ('physics.json','series.json','phases.json','source_phases.json','measurements.json','source_observations.json')},
        OEM_GUARANTEED_VALUE=None,engineering='MEMPHIS_ENGINEERING_NOT_APPROVED')
    points=[dict(time_s=r['end_ns']/1e9,rack_C=temp(r),primary_C=r['primary_inlet_c'],load_m3_h=r['load_flow_m3_h'],source_m3_h=r['source_flow_m3_h'],recharge_m3_h=r['recharge_flow_m3_h'],cold_A_m3=r['tank_A_cold_m3'],cold_B_m3=r['tank_B_cold_m3'],source_path=r['source_path'],source_valve=r['source_valve'],load_valve=r['load_valve'],source_speed=r['source_speed'],rejected_kW=r['rejected_w']/1000,aux_pump_kW=r.get('aux_pump_w',0)/1000) for r in rows if r['end_ns']%1_000_000_000==0]
    return result,points
