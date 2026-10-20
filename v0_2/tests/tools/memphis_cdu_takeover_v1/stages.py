"""Numerical integrity guards fatal; engineering FAIL/UNEXERCISED are persisted.

This distinction prevents one unmet design gate from suppressing independent
negative cases or pretending that an unexcited branch was tested.
"""
import ast,json,os,csv,gc,hashlib
from pathlib import Path
from math import fsum,isclose
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,separators=(',',':'))
def require(ok,code):
    if not ok:raise ValueError(code)

def assertions(d):
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    from . import simulation,plant,unit,control,report
    require(control.control_options(dict(extensions=True,architecture='ORIGINAL_SHARED',fault_at_s=30,second_fault_at_s=1500,hidden_profile=[1]))==dict(extensions=True,architecture='ORIGINAL_SHARED'),'NO_FUTURE_OPTIONS')
    q,dp,head,ks=unit.coupled_secondary([.9,0.],[1.,0.])
    require(isclose(q[0],68.37/3600,rel_tol=1e-12) and q[1]==0.,'PRIOR_SINGLE_RUNNING_SECONDARY_POINT')
    q2,*_=unit.coupled_secondary([.9,.9],[1.,1.]);require(fsum(q2)>fsum(q) and all(x>0 for x in q2),'COUPLED_PARALLEL_NOT_IMPOSED_FLOW')
    q,_,_=plant.primary_network([1.,1.,1.],[False]*3,.9);require(isclose(fsum(q)*3600,330,rel_tol=1e-12),'PRIOR_PRIMARY_POINT')
    q,_,_=plant.primary_network([1.,1.,1.],[True,False,False],.9);require(q[0]==0 and q[1]>0,'LOCAL_LOSS_NOT_HEADER_EQUIVALENCE')
    reg=json.loads((HERE/'registration.json').read_bytes());u=unit.DualUnit(reg['common_input'],0)
    r=u.advance(0,100000000,[313.65,313.65],[110/3600,0],[155920,0]);require(abs(r['energy_residual_J'])<.001,'NEW_DUAL_UNIT_ENERGY_SMOKE')
    # Test the measurement boundary, not fabricated PLC issue evidence.
    ctl=control.CDUController();bad=dict(id='synthetic',sample_ns=2,release_ns=1,units=[])
    try:ctl.request(bad,3)
    except AssertionError:pass
    else:raise ValueError('FUTURE_SOURCE_REFUSAL')
    # Pure control regression: a released failed-primary observation must not
    # leave an uncooled old secondary branch blocking the spare design flow.
    pair=[dict(ready=True,primary_m3_h=0.,secondary_m3_h=68.37,primary_valve=1.),dict(ready=True,primary_m3_h=0.,secondary_m3_h=0.,primary_valve=0.)]
    controller=control.CDUController()
    for now in (0,1000000000,1200000000):
        observation=dict(id='regression:'+str(now),sample_ns=now,release_ns=now,units=[dict(cdu=pair) for _ in range(3)])
        issued=controller.request(observation,now)
    require(issued['primary'][0][0]==0 and issued['secondary'][0][0]==0 and issued['pumps'][0][0]==0,'FAILED_PRIMARY_OLD_BRANCH_ISOLATION')
    require(issued['primary'][1][0]==1 and issued['secondary'][1][0]==1,'ONLY_LOCAL_SELECTED_PAIR_CHANGED')
    ids=[s['id'] for s in reg['cases']];require(len(set(ids))==len(ids),'UNIQUE_REGISTERED_CASES')
    expanded=[dict(reg['common_input'],**s.get('change',{}),id=s['id']) for s in reg['cases'] if s['kind']=='forward']
    require(all(c['seconds']<=1800 and c['dt_s'] in (.1,.05) and not c['independent_recharge'] for c in expanded),'BOUNDED_NO_RC')
    save(d/'expanded_inputs.json',expanded)
    return dict(registered_forward_cases=len(expanded),source='NEW_DUAL_CDU_DISCRETE_EQUATIONS_NOT_OEM',synthetic_refusal_scope='NOT_PLC_ISSUE_EVIDENCE')

def analyze(c,d,r):
    from v0_2.tests.tools.memphis_hydraulic_continuity_v1.streaming import FileArray
    hot=56.56138914432239;max_global=0.;hx_cancellation=0.;source_B_frames=0;maximum_unit_CV_residual=0.
    tank_mass=0.;complete_secondary_steps=0;local_deficit_without_header_deficit=0
    for row in FileArray(d/'case/physics.json',round(c['seconds']/c['dt_s'])):
        require(row['source_tank'] in ('A','B'),'ILLEGAL_SOURCE_SELECTION')
        require(row['source_supply_valve']==row['source_return_valve'],'SOURCE_PAIR_SPLIT')
        require(row['source_startup_elapsed_s']>=c['physical_startup_s'] or row['source_W']==0,'SOURCE_STARTUP_BOUNDARY')
        primary=[fsum(u['cdu'][j]['primary_m3_h'] for u in row['unit_records']) for j in range(2)]
        require(isclose(primary[0],row['primary_A_m3_h'],abs_tol=1e-7) and isclose(primary[1],row['primary_B_m3_h'],abs_tol=1e-7),'PRIMARY_LOCAL_FLOW_SUM')
        for u in row['unit_records']:
            require(isclose(fsum(u['secondary_branch_m3_h']),u['secondary_total_m3_h'],abs_tol=1e-7),'SECONDARY_RACK_MASS')
            require(isclose(fsum(x['secondary_m3_h'] for x in u['cdu']),u['secondary_total_m3_h'],abs_tol=1e-7),'CDU_PARALLEL_MASS')
            for x in u['cdu']:
                require(x['tank'] in ('A','B'),'NO_PRIMARY_CROSS_MIX')
                expected=4036000*x['primary_m3_h']/3600*(x['primary_outlet_C']-x['primary_inlet_C'])
                hx_cancellation=max(hx_cancellation,abs(expected-x['hx_W']))
                require(abs(expected-x['hx_W'])<1e-5,'HX_PRIMARY_SECONDARY_RECEIPT')
                hot=max(hot,x['primary_outlet_C'])
            a=u['control_volume_audit'];old=a['old_k'];new=a['new_k'];caps=a['capacities_J_K'];ks=a['branch_resistance'];dt=(row['end_ns']-row['start_ns'])/1e9
            qs=[x['secondary_m3_h']/3600 for x in u['cdu']];q=fsum(qs);rackq=q/6;common=u['secondary_common_dp_pa']*q
            p=[x['pump_electrical_W'] for x in u['cdu']];heads=[x['secondary_head_pa'] for x in u['cdu']]
            motor_and_branch=[k*f**3+e-h*f for k,f,e,h in zip(ks,qs,p,heads)]
            rates=[fsum(4036000*f*(t-old[0]) for f,t in zip(qs,old[16:18]))]
            rates += [4036000*rackq*(old[0]-t)+common*.1/6 for t in old[1:7]]
            rates += [4036000*rackq*(a-b)+147250+common*.9/6 for a,b in zip(old[1:7],old[7:13])]
            rates += [fsum(4036000*rackq*(t-old[13]) for t in old[7:13])]
            rates += [4036000*f*(old[13]-t)+e for f,t,e in zip(qs,old[14:16],motor_and_branch)]
            rates += [4036000*f*(a-b)-x['hx_W'] for f,a,b,x in zip(qs,old[14:16],old[16:18],u['cdu'])]
            for a,b,cap,rate in zip(old,new,caps,rates):
                res=(b-a)*cap-dt*rate;maximum_unit_CV_residual=max(maximum_unit_CV_residual,abs(res))
                require(abs(res)<1e-5,'INDEPENDENT_ALL18_CV_UNIT_ENERGY')
        total_ok=row['primary_total_m3_h']>=330-1e-7
        local_bad=any(fsum(x['primary_m3_h'] for x in u['cdu'])<110-1e-7 or u['secondary_total_m3_h']<68.37-1e-7 for u in row['unit_records'])
        if total_ok and local_bad:local_deficit_without_header_deficit+=1
        if not local_bad:complete_secondary_steps+=1
        max_global=max(max_global,abs(row['energy_residual_J']))
    # Independently bind issued source/CDU observations to timestamp causality.
    requests=0;observed_spare_flow=0
    for f in FileArray(d/'case/cdu_frames.json',None):
        o=f['observation'];cmd=f['command'];require(o['sample_ns']<=o['release_ns']<=cmd['time_ns'],'CDU_FUTURE_SAMPLE')
        require(cmd['measurement_id']==o['id'],'CDU_COMMAND_OBSERVATION_BINDING')
        requests+=sum(x[1]>.5 for x in cmd['primary']);observed_spare_flow+=sum(u['cdu'][1]['secondary_m3_h']>0 for u in o['units'])
    for f in FileArray(d/'case/source_frames.json',None):
        o=f['measurement'];require(o['sample_ns']<=o['release_ns']<=f['time_ns'],'SOURCE_FUTURE_SAMPLE')
        require(f['PLC']['data']['request']==f['request'],'ACTUAL_SOURCE_PLC_BINDING')
        source_B_frames+=int(f['request']['source_tank']=='B')
    # Exact saved profiles are challenged OFFLINE, never returned to a controller.
    from v0_2.tests.tools.memphis_topology_audit_v1.discharge import full_discharge
    qualification=[]
    for sample in r['qualification_samples']:
        trials=full_discharge(sample['profiles'],c,hot,d/('PROFILE_'+str(round(sample['time_s'])).zfill(5)+'_90S.csv'))
        qualification.append(dict(time_s=sample['time_s'],trials=trials))
    pre=None
    if r['pre_second']:pre=full_discharge(r['pre_second']['profiles'],c,hot,d/'PRE_SECOND_90S.csv')
    final=full_discharge(r['final_profiles'],c,hot,d/'FINAL_90S.csv')
    qualified=bool(pre and all(t['status']=='PASS' for t in pre));w=r['B_path']
    physical_B=w['B_command_s'] is not None and w['B_flow_s'] is not None and w['B_net_source_J']<0 and w['B_inventory_increase_s'] is not None
    takeover=any(e['to_state']=='CDU_TAKEOVER_COMPLETED' for e in r['CDU_events'])
    first_thermal=all(x['first90_max_C']<=45 for x in r['units'])
    first_flow=all(x['first90_min_primary']>=110-1e-7 and x['first90_min_secondary']>=68.37-1e-7 for x in r['units'])
    second_ok=qualified and all(x['second90_max_C'] is not None and x['second90_max_C']<=45 and x['second90_min_primary']>=110-1e-7 and x['second90_min_secondary']>=68.37-1e-7 for x in r['units'])
    statuses=dict(CONTROL_PATH_STATUS='CANDIDATE_EXECUTABLE_CUSTOMER_PID_MATRIX_MISSING',CDU_TAKEOVER_STATUS='PHYSICAL_COMPLETED_CONTINUITY_SEPARATE' if takeover else 'NOT_REQUIRED_SOURCE_ONLY' if c['fault'] in ('NONE','W1_LOSS') else 'INCOMPLETE_OR_FAILED',
        PHYSICAL_RESERVE_STATUS='ACTUAL_B_CDU_HEAT_FLOW_AND_LAYER_DEPLETION' if w['B_load_volume_m3']>0 and w['B_CDU_heat_J']>0 and w['B_min_cold_m3']<w['B_initial_cold_m3'] else 'ACTUAL_A_LOAD_ONLY' if c['fault'] in ('NONE','W1_LOSS') else 'B_IT_HEAT_DEPLETION_NOT_PROVEN',
        RECHARGE_RECOVERY_STATUS='PHYSICAL_B_RECHARGE; FULL_RESERVE_SEPARATE' if physical_B else 'UNREACHABLE_OR_NOT_REQUIRED_IN_THIS_CASE',SECOND_FAULT_STATUS='PASS_CONDITIONAL_MODEL' if second_ok else 'UNQUALIFIED_DIAGNOSTIC' if pre else 'NOT_SCHEDULED',MODEL_VALIDITY_STATUS='DISCRETE_ENERGY_AND_CAUSALITY_VERIFIED_NOT_PHYSICAL_CALIBRATION',OEM_VERIFICATION_STATUS='NOT_VERIFIED')
    negative='NOT_APPLICABLE'
    if c.get('standby_valve_stuck') or c.get('standby_start_failed'):negative='EXERCISED_NO_FALSE_COMPLETION' if requests and not takeover else 'INCOMPLETE_NOT_EXCITED_OR_UNEXPECTED_COMPLETION'
    if c.get('B_source_valve_stuck') or c.get('B_source_pump_no_flow'):negative='EXERCISED_NO_FALSE_RECHARGE_SUCCESS' if source_B_frames and not physical_B else 'INCOMPLETE_NOT_EXCITED_OR_UNEXPECTED_SUCCESS'
    if c['fault']=='W1_LOSS':require(requests==0,'SOURCE_FAILURE_MUST_NOT_INVENT_CDU_TRANSFER')
    gates=dict(GATE1='INCOMPLETE_CUSTOMER_FINAL_PID_AND_FAULT_MATRIX_MISSING',GATE2=statuses['CDU_TAKEOVER_STATUS'],GATE3='DISCRETE_MASS_ENERGY_VERIFIED',GATE4='ACTUAL_B_PATH' if physical_B else 'INCOMPLETE_OR_NOT_REQUIRED',GATE5='INCOMPLETE' if not physical_B else 'SEE_ACTUAL_RETURN_EVENTS',GATE6='PASS_COMPONENT_ONLY' if all(t['status']=='PASS' for t in final) else 'FAIL_COMPONENT',GATE7=statuses['SECOND_FAULT_STATUS'],GATE8='PASS_FINITE_FIRST90_ONLY' if first_flow and first_thermal else 'FAIL_FIRST90_THERMAL_OR_LOCAL_FLOW')
    r.update(statuses=statuses,gates=gates,negative_control=negative,first90=dict(thermal='PASS' if first_thermal else 'FAIL',local_primary_and_secondary_flow='PASS' if first_flow else 'FAIL'),qualification=qualification,final_discharge=final,pre_second_discharge=pre,
        independent=dict(max_whole_step_residual_J=max_global,max_HX_receipt_difference_W=hx_cancellation,max_unit_CV_residual_J=maximum_unit_CV_residual,header_OK_but_local_flow_bad_steps=local_deficit_without_header_deficit,actual_spare_primary_request_frames=requests,actual_spare_flow_observation_frames=observed_spare_flow,source_B_command_frames=source_B_frames),engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',scope='All later gates diagnostic if earlier gate fails; no full engineering approval')
    save(d/'summary.json',r)
    # Small analysis data is independent of the full raw archive, not a substitute.
    return dict(id=c['id'],statuses=statuses,gates=gates,negative_control=negative,first90=r['first90'],scope='DEVELOPMENT_EXECUTION_NOT_AGGREGATE_ENGINEERING_PASS')

def stage(entry,d):
    if entry['kind']=='assertions':return assertions(d)
    if entry['kind']=='old':
        from v0_2.tests.tools.memphis_topology_audit_v1.stages import stage as old
        return old(dict(kind='forward',id='BASELINE_EXACT',change={}),d)
    if entry['kind']=='final':
        from .report import finalize
        return finalize(d)
    reg=json.loads((HERE/'registration.json').read_bytes());c=dict(reg['common_input'],**entry.get('change',{}),id=entry['id'])
    if entry['kind']=='smoke':c.update(seconds=45,fault='CDU_FAILURE',fault_at_s=2)
    from .simulation import run
    save(d/'case_spec.json',c);result=run(c,d/'case')
    if entry['kind']=='smoke':
        require(result['B_path']['B_load_volume_m3']>0,'PHYSICAL_STANDBY_SMOKE_NOT_EXERCISED')
        return dict(scope='45S_DEVELOPMENT_INTERFACE_ONLY_NOT_CUSTOMER_QUALIFICATION',events=result['CDU_events'],B_load_volume_m3=result['B_path']['B_load_volume_m3'],energy=result['energy'])
    result=analyze(c,d,result);gc.collect();return result
