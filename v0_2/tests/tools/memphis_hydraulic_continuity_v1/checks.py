"""Independent saved-evidence checks. No plant/solver imports in audit path."""
import json,hashlib
from math import fsum,sqrt,exp
from .streaming import FileArray
from .independent import _unchanged_physics_audit,close,close_rate,require,CV

def read(p):return json.loads(p.read_bytes())
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()

def save(p,obj):
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,sort_keys=True,allow_nan=False);f.write('\n')

def verify_primary(r,c):
    nominal=330/3600;eta=c.get('primary_efficiency',.7)
    valve=r['load_valve'];factor=r['load_resistance_factor']
    kt=(135920+20000/max(valve,.001)**2)/nominal**2*factor
    kp_load=155920/nominal**2*.25;h0_load=155920*1.25/.9**2
    qt=sqrt(h0_load*.9**2/(kt+kp_load)) if valve>1e-9 else 0.
    neutral=r.get('neutral')
    expected_main_on=r['start_ns']/1e9<c.get('common_load_loss_at_s',float('inf'))
    main=(nominal if expected_main_on else 0.) if neutral else qt
    if neutral:
        require(r['load_flow_m3_h'] in (0.,330.) or abs(r['load_flow_m3_h']-330)<1e-8,'NEUTRAL_MAIN_QH')
        close(r['transfer_flow_m3_h'],qt*3600)
        cm=CV*main;ct=CV*qt
        if min(cm,ct)==0:heat=0.
        else:
            cmin=min(cm,ct);cr=cmin/max(cm,ct);ntu=c['neutral_hx_ua_w_k']/cmin
            e=exp(-ntu*(1-cr));effect=ntu/(1+ntu) if abs(1-cr)<1e-10 else (1-e)/(1-cr*e)
            heat=effect*cmin*(r['actual_primary_return_c']+273.15-neutral['transfer_in_k'])
        close(heat,neutral['transfer_heat_w'])
        close(neutral['main_pump_w'],main*155920/eta if main else 0.)
        close(neutral['transfer_pump_w'],qt**3*kt/eta)
        close(neutral['transfer_return_k'],neutral['transfer_in_k']+heat/(CV*qt) if qt else neutral['transfer_in_k'])
        dt=(r['end_ns']-r['start_ns'])/1e9
        rate=r['unit_hx_w']+neutral['main_pump_w']-heat+neutral['environment_w']
        close(neutral['new_k']*neutral['capacity_j_k'],neutral['old_k']*neutral['capacity_j_k']+rate*dt,8192)
        require(neutral['AB_direct_mass_connection'] is False,'ILLEGAL_AB_NEUTRAL_CONNECTION')
    close(r['load_flow_m3_h'],main*3600)
    wet=r['source_path'].startswith('W');dp=96520 if wet else 63210;modules=r['active_module_count']
    ks=dp*(.2/max(r['source_valve'],.001)**2+.8*((5/modules)**2 if wet else 1))/nominal**2
    rho=1009.;g=9.80665
    h0=rho*g*(34*1.2 if c['source_variant']=='V9' else 18)
    pid_k=(rho*g*18-115820)/(110/3600)**2
    kp=(rho*g*34*.2/(115/3600)**2 if c['source_variant']=='V9' else pid_k)/r['actual_source_pumps']**2
    qs=sqrt(h0*c.get('source_head_factor',1)*r['source_speed']**2/(ks+kp)) if r['source_valve']>1e-9 and r['source_speed']>1e-9 and (r['source_header_available'] or r['source_path']=='W3') else 0.
    kr=c.get('recharge_dp_kpa',115.82)*1000/nominal**2
    qr=sqrt(rho*g*18*c.get('recharge_head_factor',1)*r['recharge_actual_speed']**2/(kr+pid_k/9)) if r['recharge_actual_speed']>1e-9 else 0.
    close(r['source_flow_m3_h'],qs*3600);close(r['recharge_flow_m3_h'],qr*3600)
    aux=fsum(q/3600*20000/.65 for q in r['aux_actual_flows_m3_h'].values())
    electric=(qt**3*kt+qs**3*ks+qr**3*kr)/eta+aux
    if neutral:electric+=main*155920/eta
    close(r['primary_pump_electrical_w'],electric)
    for name,t in r['tank_records'].items():
        close(t['load_m3_s'],qt if name==r['load_tank'] else 0.)
        close(t['source_m3_s'],(qs if name==r['source_tank'] else 0.)+(qr if name=='B' else 0.))
    close(fsum(u['primary_flow_m3_s'] for u in r['unit_records']),main)

def reserve_challenge(final,c):
    # Exact final state, no ideal profile reset. Uniform finite-volume refinement
    # splits each final cell into equal cells, conserving the exact stored heat.
    # Tank math reuse is allowed here after independent forward audit completed.
    from v0_2.tests.tools.memphis_failure_closure_v1.group_model.tank import Tank
    results=[];dt=.05;load=330/3600
    for name in ('A','B'):
        actual=final['tank_'+name+'_k']
        for mult in (1,2):
            n=len(actual)*mult;t=Tank(n,volume=c.get('tank_volume_m3',15.))
            t.t=[x for x in actual for _ in range(mult)]
            before=t.energy();initial=t.t[0];hot=48.29+273.15;worst=initial
            for _ in range(round(90/dt)):
                t.advance(dt,load,0.,hot,t.t[0],0.,c.get('short_circuit',0.))
                worst=max(worst,t.t[0])
            rise=worst-initial
            cold=sum(x<=314.5948 for x in actual)*c.get('tank_volume_m3',15.)/len(actual)
            met=initial<=314.5948 and cold>=.85*c.get('tank_volume_m3',15.) and rise<=.5
            results.append(dict(tank=name,layers=n,dt_s=dt,initial_outlet_C=initial-273.15,initial_cold_m3=cold,
                rise_K=rise,initial_energy_J=before,final_energy_J=t.energy(),status='PASS' if met else 'FAIL',
                method='EXACT_FINAL_PROFILE_CONSERVATIVE_REFINEMENT_NO_NONZERO_DIFFUSION_CLAIM',return_boundary_C=48.29))
    return results

def evaluate(d,c):
    independent=_unchanged_physics_audit(d,c)
    from v0_2.tests.tools.memphis_failure_closure_v1.audit import causal
    frames=read(d/'phases.json');measurements=read(d/'measurements.json')
    for unit in range(3):causal([f for f in frames if f['unit']==unit],[m for m in measurements if m['unit']==unit])
    rows=FileArray(d/'physics.json',round(c['seconds']/c['dt_s']))
    initial=read(d/'series.json')[0];final=read(d/'series.json')[-1]
    peak=max(max(u['inlet_k'])-273.15 for u in initial['units']);peak90=-1e9
    minload=1e9;min90=1e9;deficit=deficit90=zero=short=0.;first_short=last_short=None
    first_cold=first_B_cold=None;source_tail=[];points=[];last=None;count=0
    fault=c.get('fault_at_s',30.);window_n=0;qd=330.;minimum_at=None
    for r in rows:
        verify_primary(r,c);count+=1;last=r
        t=r['end_ns']/1e9;start=r['start_ns']/1e9;dt=t-start
        maximum=max(max(u['new_k'][1:7])-273.15 for u in r['unit_records'])
        peak=max(peak,maximum);q=r['load_flow_m3_h']
        if q<minload:minload=q;minimum_at=t
        if q<qd-1e-8:
            short+=dt;deficit+=(qd-q)*dt/3600
            if first_short is None:first_short=start
            last_short=t
        if q<=1e-8:zero+=dt
        if start>=fault-1e-9 and t<=fault+90+1e-9:
            window_n+=1;peak90=max(peak90,maximum);min90=min(min90,q)
            deficit90+=max(0.,qd-q)*dt/3600
        good=r['source_available'].get(r['source_path'],False) and r['source_flow_m3_h']>=330-1e-8 and r['source_return_k']<=314.5948
        if start>=fault and first_cold is None and good:first_cold=t
        if start>=fault and first_B_cold is None and good and r['source_tank']=='B':first_B_cold=t
        if t>c['seconds']-5:source_tail.append(good)
        if r['end_ns']%1_000_000_000==0 or q<330-1e-8:
            points.append(dict(time_s=t,rack_C=maximum,load_m3_h=q,source_m3_h=r['source_flow_m3_h'],
                transfer_m3_h=r.get('transfer_flow_m3_h'),primary_C=r['primary_inlet_c'],cold_A_m3=r['tank_A_cold_m3'],cold_B_m3=r['tank_B_cold_m3'],
                source_tank=r['source_tank'],load_tank=r['load_tank'],source_path=r['source_path'],
                source_return_C=r['source_return_k']-273.15,primary_pump_kW=r['primary_pump_electrical_w']/1000,
                load_dp_quasi_pa=r.get('neutral',{}).get('main_dp_pa'),transfer_dp_quasi_pa=r.get('neutral',{}).get('transfer_dp_pa')))
    require(count==round(c['seconds']/c['dt_s']) and window_n==round(90/c['dt_s']),'EXACT_TIME_AND90_WINDOW')
    source_frames=read(d/'source_phases.json')
    codes=sorted({x for f in source_frames for x in f['safety']['data']['codes']})
    actual_B=any(f['request']['load_tank']=='B' for f in source_frames)
    if c.get('load_valve_stuck'):require(actual_B,'STUCK_NEGATIVE_MUST_BE_ACTUALLY_EXCITED')
    since={};false_claim_witness=False
    for f in source_frames:
        o=f['measurement'];now=f['time_ns'];expected={}
        for path,a,b,q,av in [('W2',o['standby_near_c'],o['standby_far_c'],o['standby_flow_m3_s'],o['w2_available']),('W3',o['third_near_c'],o['third_far_c'],o['third_flow_m3_s'],o['third_available'])]:
            valid=0<=now-o['ready_sample_ns']<=round(c.get('source_ready_ttl_s',.6)*1e9) and max(a,b)+.2<=41.4448 and abs(a-b)<=.3 and q>=c.get('ready_flow_m3_h',60)/3600 and av and o['deadleg_verified']
            if valid:since.setdefault(path,now)
            else:since.pop(path,None)
            expected[path]=bool(valid and now-since.get(path,now)>=round(c.get('ready_hold_s',1)*1e9))
        require(expected==f['safety']['data']['measured_cold_ready'],'INDEPENDENT_READY_CAUSAL_RECONSTRUCTION')
        if c.get('false_ready_claim') and fault<=now/1e9<=fault+90 and not expected['W2']:false_claim_witness=True
    if c.get('false_ready_claim'):require(false_claim_witness,'FALSE_READY_NEGATIVE_NOT_EXCITED')
    if c.get('common_load_loss_at_s') is not None:require(minload<=1e-8,'COMMON_LOAD_NEGATIVE_NOT_EXCITED')
    required_cold=first_B_cold if c.get('fault')=='A_LOAD_RESTRICTION' else first_cold
    grades={'THERMAL_COMPLIANCE':'PASS' if peak<=45 else 'FAIL','LOAD_FLOW_COMPLIANCE':'PASS' if minload>=330-1e-8 else 'FAIL',
        '90S_CONTINUITY':'PASS' if peak90<=45 and min90>=330-1e-8 else 'FAIL',
        'SOURCE_RECOVERY':'PASS' if required_cold is not None and required_cold-fault<=90 and all(source_tail) else 'FAIL',
        'RESERVE_RECOVERY':'NOT_RUN','PRESSURE_TRANSIENT':'NOT_VERIFIED','ABSOLUTE_PRESSURE_NPSH':'NOT_VERIFIED',
        'M1_CAUSALITY':'VERIFIED_NEW_INTEGRATION_NOT_INHERITED_C3C','OEM_EVIDENCE':'NOT_VERIFIED'}
    challenge=[]
    if c.get('shared_recharge') or c.get('independent_recharge'):
        challenge=reserve_challenge(final,c)
        grades['RESERVE_RECOVERY']='PASS' if all(x['status']=='PASS' for x in challenge) else 'FAIL'
    output=read(d/'result.json')
    result=dict(id=c['id'],parameters=c,grades=grades,maximum_inlet_C=peak,maximum90_inlet_C=peak90,minimum_load_m3_h=minload,
        minimum_time_s=minimum_at,shortfall_duration_s=short,zero_flow_duration_s=zero,deficit_m3=deficit,deficit90_m3=deficit90,first_short_s=first_short,last_short_s=last_short,
        source_cold_delay_s=None if required_cold is None else required_cold-fault,any_source_first_cold_s=first_cold,
        first_actual_B_cold_s=first_B_cold,source_final_m3_h=last['source_flow_m3_h'],
        final_pumps=last['actual_source_pumps'],final_tanks_k={n:final['tank_'+n+'_k'] for n in ('A','B')},
        cold_A_final_m3=final['cold_A_m3'],cold_B_final_m3=final['cold_B_m3'],reserve_challenge=challenge,
        codes=codes,events=output['source_timeline'],independent=independent,
        raw_sha256={n:digest(d/n) for n in ('physics.json','series.json','phases.json','source_phases.json','measurements.json','source_observations.json')},
        engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',hardware=False,source_first_good_is_not_B_path_transfer_proof=True)
    save(d.parent/'forward_result.json',result);save(d.parent/'plot_data.json',points)
    return result
