"""Bounded executable studies; no local execution permitted by worker/runner."""
import ast,gc,json,hashlib
from pathlib import Path
from dataclasses import asdict,replace
from .requirements import save
from .checks import need,evaluate,close
from .scenarios import trials
HERE=Path(__file__).resolve().parent

def assertions(directory):
    for p in HERE.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    from .negative import run
    result=run();count=result['refusal_and_positive_witnesses']
    from .group_model.coordination import SourceObservation,ClosureObservation,ProjectProtection,SourcePLC,record,control_options
    o=SourceObservation(0,100000000,'sample',0.,0.,'A','W1',330/3600,0.,False,True,False,41.,(313.65,)*4,(313.65,)*4,330/3600,None,43.8,True,True)
    extra=dict(standby_near_c=40.5,standby_far_c=40.5,standby_flow_m3_s=90/3600,ready_sample_ns=0,claimed_ready=True,third_available=False,third_near_c=99.,third_far_c=99.,third_flow_m3_s=0.,source_enable_echo=False,load_selector='A',load_valve_feedback=1.,active_pumps=3,deadleg_verified=True,reserve_A_k=(313.65,)*17,reserve_B_k=(313.65,)*17,source_valve_target_echo=0.)
    q=ClosureObservation(**asdict(o),**extra);p=ProjectProtection({'extensions':True,'ready_flow_m3_h':90})
    p.evaluate(q,100000000);fresh=replace(q,sample_ns=1_000_000_000,release_ns=1_100_000_000,ready_sample_ns=1_000_000_000,record_id='fresh')
    need(p.evaluate(fresh,1_100_000_000)['data']['measured_cold_ready']['W2'],'POSITIVE_PAIRED_READY');count+=1
    for change in (dict(standby_far_c=48.29),dict(ready_sample_ns=-1_000_000_000),dict(standby_flow_m3_s=0),dict(deadleg_verified=False)):
        need(not p.evaluate(replace(fresh,**change),1_100_000_000)['data']['measured_cold_ready']['W2'],'FALSE_READY_WITNESS');count+=1
    opts=control_options(dict(extensions=True,fault_at_s=30,second_source_failure=True,hidden_true_state='forbidden',source_speed_margin=.03))
    need(set(opts)=={'extensions','source_speed_margin'},'CONTROLLER_SCENARIO_LEAK');count+=1
    s=record(dict(measurement_id=o.record_id));r=dict(permission=s['sha256'],observation_id=o.record_id,source_tank='A+B',source_path='W1',load_tank='A',recharge_enable=False)
    refused=False
    try:SourcePLC({'extensions':True}).issue(r,s,o,100000000)
    except ValueError:refused=True
    need(refused,'ILLEGAL_AB_REQUEST_ACCEPTED');count+=1
    refused=False
    try:close(330.,326.194)
    except ValueError:refused=True
    need(refused,'HYDRAULIC_CORRUPTION_NOT_REFUSED');count+=1
    reg=json.loads((HERE/'registration.json').read_bytes());expanded=[]
    for spec in reg['cases']:
        if spec['kind']=='bundle':expanded.extend(trials(spec['study']))
    need(len({c['id'] for c in expanded})==len(expanded),'DUPLICATE_INPUT_ID')
    save(directory/'expanded_registration.json',expanded)
    return dict(kind='assertions',status='MODEL_VALIDATED',refusal_and_positive_witnesses=count,expanded_trials=len(expanded))

def forward(c,directory,baseline=False):
    from .group_model.simulation import run
    need(c['dt_s'] in (.1,.05) and c['seconds']<=900,'FINITE_INPUT_BOUND')
    need(c.get('prelude_s',0)<=1200,'PRELUDE_BOUND')
    save(directory/'case_spec.json',c);run(c,directory/'case');result,points=evaluate(directory/'case',c)
    if baseline:need({k:v for k,v in result['raw_sha256'].items() if k in ('physics.json','series.json','phases.json','source_phases.json')}==json.loads((HERE/'baseline_hashes.json').read_bytes()),'EXACT_LEGACY_BASELINE_PHYSICAL_DRIFT')
    save(directory/'forward_result.json',result);save(directory/'plot_data.json',points);gc.collect();return result

def stage(spec,directory):
    kind=spec['kind']
    if kind=='negative':return assertions(directory)
    if kind=='prior':
        from .prior import run
        return run(directory)
    if kind=='analytic':
        from .requirements import analytic
        return dict(kind='analytic',results=analytic(directory))
    if kind=='legacy':
        c=dict(id=spec['id'],scope='GROUP18',ua_w_k=220000.,dt_s=.1,seconds=240.,source_variant='V9',tank_kind='STRATIFIED',fault='W1_LOSS',fault_at_s=30.,recharge_at_s=120.)
        return dict(kind='dynamic',cases=[forward(c,directory,True)])
    if kind=='bundle':
        results=[]
        for c in trials(spec['study']):
            d=directory/c['id'];d.mkdir();results.append(forward(c,d));print('CLOSURE_ACTUAL_CASE '+c['id']+' '+results[-1]['status'],flush=True)
        return dict(kind='dynamic',study=spec['study'],cases=results)
    if kind=='tank':
        from .storage import tank_study
        return tank_study(spec,directory)
    if kind=='standby':
        from .storage import standby
        return standby(spec,directory)
    if kind=='final':
        from .report import finalize
        return finalize(directory)
    raise ValueError('UNREGISTERED_STAGE')
