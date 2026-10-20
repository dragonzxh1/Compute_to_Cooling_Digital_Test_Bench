"""Fresh bounded proposals, no local entry or inherited engineering PASS."""
import ast,json,os,gc
from pathlib import Path
from math import isclose
from .checks import save,require,evaluate
HERE=Path(__file__).resolve().parent

def assertions(directory):
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    from .coordination import control_options,Controller,PLC,record
    from types import SimpleNamespace
    require(control_options(dict(extensions=True,architecture='ORIGINAL_SHARED',fault_at_s=30,repair_W1_at_s=900,second_fault_at_s=1800,hidden_state=True))==dict(extensions=True,architecture='ORIGINAL_SHARED'),'FUTURE_SCHEDULE_WHITELIST')
    from v0_2.tests.tools.memphis_topology_audit_v1.verify import assertions as fv
    negatives=fv();refused=[]
    s=record(dict(measurement_id='synthetic-refusal-fixture'))
    o=SimpleNamespace(record_id='synthetic-refusal-fixture',source_speed=.5,source_valve=1.,recharge_speed=.5,rc_valve_feedback=1.)
    base=dict(source_tank='A',source_path='W1',load_tank='A',rc_tank='B',recharge_enable=False,recharge_path='RC',permission=s['sha256'],observation_id=o.record_id)
    for name,change in [('CROSS_RC',{'rc_tank':'X'}),('ENABLE_CLOSED_RC',{'recharge_enable':True}),('WRONG_AUTHORITY',{'permission':'BAD'}),('CHANGE_SOURCE_RUNNING',{'source_tank':'B'}),('CHANGE_RC_RUNNING',{'rc_tank':'A'})]:
        plc=PLC();plc.prior=dict(base);obs=o
        if name=='ENABLE_CLOSED_RC':obs=SimpleNamespace(**dict(vars(o),rc_valve_feedback=0.))
        try:plc.issue(dict(base,**change),s,obs,0)
        except (ValueError,RuntimeError,AssertionError):refused.append(name)
        else:raise ValueError('NEGATIVE_NOT_REFUSED:'+name)
    require(len(refused)==5,'ALL_REFUSALS_REQUIRED')
    reg=json.loads((HERE/'registration.json').read_bytes())
    ids=[x['id'] for x in reg['cases']];require(len(set(ids))==len(ids),'UNIQUE_STAGE_IDS')
    expanded=[]
    for entry in reg['cases']:
        if entry['kind']=='forward':
            c=dict(reg['common_input'],**entry['change'],id=entry['id'])
            c['shared_recharge']=c['architecture']=='ORIGINAL_SHARED'
            require(c['seconds']<=1890 and c['dt_s'] in (.1,.05),'BOUNDED_INPUT')
            expanded.append(c)
    save(directory/'expanded_inputs.json',expanded)
    return dict(independent_fv=negatives,synthetic_refusal_tests_only_not_PLC_issue_evidence=refused,forward_cases=len(expanded))

def source_checks(directory,c):
    from v0_2.tests.tools.memphis_hydraulic_continuity_v1.streaming import FileArray
    from v0_2.tests.tools.memphis_hydraulic_continuity_v1.independent import close
    rows=FileArray(directory/'case/physics.json',round(c['seconds']/c['dt_s']))
    source_warmup=False;rc_a=False;rc_b=False;sink_witness=False;pump_witness=False;sample_binding={}
    for r in rows:
        require(r.get('neutral') is None and r['load_tank']=='A','NO_THIRD_LOOP_OR_HIDDEN_LOAD_TRANSFER')
        require(r['aux_rejected_w']==0 and r['aux_pump_w']==0,'NO_EXTRA_PRECONDITIONING_COLD_SERVICE')
        require(r['source_available']['W1']==(r['start_ns']/1e9<c['fault_at_s'] or r['start_ns']/1e9>=c.get('repair_W1_at_s',float('inf'))),'EXACT_PHYSICAL_FAULT_REPAIR_SCHEDULE')
        if r['source_startup_elapsed_s']<c['physical_startup_s']:
            require(r['main_rejected_w']==0,'PREMATURE_SOURCE_COOLING');source_warmup=True
        if r['recharge_flow_m3_h']>1e-8:
            require(r['rc_valve']>=1-1e-9,'RC_VALVE_LEGAL_ACTUAL_PAIR')
            rc_a |= r['rc_tank']=='A';rc_b |= r['rc_tank']=='B'
            sink=0 if r['start_ns']/1e9>=c.get('rc_sink_loss_at_s',float('inf')) else c['rc_capacity_kW']*1000
            require(0<=r['rc_rejected_w']<=sink+1e-8,'RC_SINK_PHYSICAL_BOUND')
            if sink==0:sink_witness=True
        if c.get('pump_loss_at_s') is not None and r['start_ns']/1e9>=c['pump_loss_at_s']:
            require(r['actual_source_pumps']<=3,'SOURCE_PUMP_FAILURE_NOT_ACTUAL');pump_witness=True
        if r['end_ns']%200000000==0:
            sample_binding[r['end_ns']]=dict(source_flow_m3_s=r['source_flow_m3_h']/3600,
                recharge_speed=r['recharge_actual_speed'],rc_valve_feedback=r['rc_valve'],actual_rc_tank=r['rc_tank'],
                current_source_near_c=r['source_pipe_after_k'][0]-273.15,current_source_far_c=r['source_pipe_after_k'][-1]-273.15,
                reserve_A_k=[r['tank_records']['A']['new_k'][round(i*(c['layers']-1)/16)] for i in range(17)],
                reserve_B_k=[r['tank_records']['B']['new_k'][round(i*(c['layers']-1)/16)] for i in range(17)])
    require(source_warmup,'PHYSICAL_COLD_START_NOT_EXCITED')
    if c['id']=='RC_A_SERVICE':require(rc_a,'RC_A_CONNECTION_NOT_EXERCISED')
    if c.get('rc_sink_loss_at_s') is not None:require(sink_witness,'RC_SINK_FAILURE_NOT_EXERCISED')
    if c.get('pump_loss_at_s') is not None:require(pump_witness,'PUMP_FAILURE_NOT_EXERCISED')
    frames=json.loads((directory/'case/source_phases.json').read_bytes());prior=None;current_since=None
    for f in frames:
        o=f['measurement'];r=f['request'];now=f['time_ns']
        if o['sample_ns']:
            physical=sample_binding[o['sample_ns']]
            for key,value in physical.items():
                if isinstance(value,list):require(o[key]==value,'ACTUAL_RELEASED_TANK_TT_BINDING')
                elif isinstance(value,str):require(o[key]==value,'ACTUAL_RC_SELECTOR_FEEDBACK_BINDING')
                else:close(o[key],value)
        if prior and r['rc_tank']!=prior['rc_tank']:
            require(o['recharge_speed']<=1e-9 and o['rc_valve_feedback']<=1e-9,'INDEPENDENT_RC_BREAK_BEFORE_MAKE')
        fresh=0<=now-o['sample_ns']<=600000000
        cold=fresh and max(o['current_source_near_c'],o['current_source_far_c'])+.2<=41.4448 and o['source_flow_m3_s']>=330/3600-1e-12
        if cold:
            if current_since is None:current_since=now
        else:current_since=None
        expected=bool(cold and now-current_since>=round(c['ready_hold_s']*1e9))
        require(f['safety']['data']['current_cold_return_confirmed']==expected,'INDEPENDENT_CURRENT_COLD_READY')
        require(o['wet_inlet_gauge_pa'] is None,'NO_FABRICATED_ABSOLUTE_PRESSURE')
        prior=r
    return dict(actual_RC_served_A=rc_a,actual_RC_served_B=rc_b,source_cold_start_exercised=source_warmup,RC_sink_loss_exercised=sink_witness,pump_loss_exercised=pump_witness)

def stage(entry,directory):
    if entry['kind']=='assertions':return assertions(directory)
    if entry['kind']=='old':
        from v0_2.tests.tools.memphis_topology_audit_v1.stages import stage as old
        return old(dict(kind='forward',id='BASELINE_EXACT',change={}),directory)
    if entry['kind']=='smoke':
        from .simulation import run
        from v0_2.tests.tools.memphis_hydraulic_continuity_v1.independent import _unchanged_physics_audit
        reg=json.loads((HERE/'registration.json').read_bytes());receipts=[]
        for arch in ('ORIGINAL_SHARED','SELECTABLE_RC'):
            c=dict(reg['common_input'],id='SMOKE_'+arch,architecture=arch,seconds=12.,
                shared_at_s=.2,physical_startup_s=1.,fault_at_s=2.,independent_recharge=arch=='SELECTABLE_RC',
                backup_initial='COLD',cold_fraction_A=.7,cold_fraction_B=.95,shared_recharge=arch=='ORIGINAL_SHARED')
            path=directory/arch;run(c,path);proof=_unchanged_physics_audit(path,c)
            receipts.append(dict(architecture=arch,transactions=proof['transactions'],energy=proof['independent_energy'],
                scope='SHORT_SYNTHETIC_PATH_SMOKE_NOT_CUSTOMER_90S_QUALIFICATION'))
        return dict(smoke=receipts)
    if entry['kind']=='final':
        from .report import finalize
        return finalize(directory)
    if entry['kind']=='conditional':
        analysis=HERE.parents[3]/'artifacts/memphis-loop-validation-v1-analysis'
        bound={}
        for p in analysis.rglob('loop_summary.json'):
            a=json.loads(p.read_bytes());bound[a['id']]=a
        a,b=(bound[n] for n in ('SHARED_SECOND_REPAIRED','RC_SECOND_REPAIRED'))
        require(a['source_commit']==b['source_commit']==os.environ['GITHUB_SHA'],'C_REQUIRES_SAME_EXECUTION_PRIOR_EVIDENCE')
        unqualified=all(not x['second_fault']['pre_event_component_qualified'] or x['grades']['SECOND_FAULT_90S']!='PASS' for x in (a,b))
        hydraulic=any(x['minimum_load_m3_h']<330-1e-8 for x in (a,b)) or a['source_final_m3_h']<=330+1e-8
        decision=dict(id=entry['id'],A_B_both_unqualified=unqualified,observed_hydraulic_deficit=hydraulic,
            source_commit=os.environ['GITHUB_SHA'],status='RUN_DECLARED_SOURCE_VFD_MARGIN' if unqualified and hydraulic else 'NOT_RUN_NO_JUSTIFIED_HYDRAULIC_DEFICIT',
            scope='Gated diagnostic, not an approved pump/valve redesign',registered_change=entry['change'])
        save(directory/'C_DECISION.json',decision)
        if not (unqualified and hydraulic):return decision
    reg=json.loads((HERE/'registration.json').read_bytes());c=dict(reg['common_input'],**entry['change'],id=entry['id'])
    c['shared_recharge']=c['architecture']=='ORIGINAL_SHARED'
    save(directory/'case_spec.json',c)
    from . import simulation
    from .observer import ObservedPlant
    plant=[]
    def factory(s):p=ObservedPlant(s,directory);plant.append(p);return p
    simulation.SourcePlant=factory
    try:simulation.run(c,directory/'case')
    finally:observed=plant[0].finish() if plant else None
    result=evaluate(directory/'case',c)
    from v0_2.tests.tools.memphis_topology_audit_v1.discharge import full_discharge
    result['final_full_discharge']=full_discharge(result['final_tanks_k'],c,observed['return_boundary_C'],directory/'FINAL_DISCHARGE.csv')
    result['observed']=observed;result['proposal_checks']=source_checks(directory,c)
    result['source_commit']=os.environ['GITHUB_SHA']
    if result['second_fault']:
        qualifies=all(x['status']=='PASS' for x in observed['pre_second_challenge'])
        result['second_fault']['pre_event_component_qualified']=qualifies
        result['second_fault']['qualification']='CONDITIONAL_QUALIFIED_EVENT' if qualifies and result['grades']['SECOND_FAULT_90S']=='PASS' else 'UNQUALIFIED_DIAGNOSTIC'
    save(directory/'loop_summary.json',result);gc.collect()
    return dict(id=c['id'],source_commit=result['source_commit'],grades=result['grades'],checks=result['proposal_checks'],scope='SOFTWARE_VALIDATION_NOT_CUSTOMER_ENGINEERING_APPROVAL')
