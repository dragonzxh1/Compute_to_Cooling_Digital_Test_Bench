"""Finite staged development, after actual remote Job verification only."""
import ast,json,gc
from pathlib import Path
from .checks import save,evaluate,require,digest
from .scenarios import cases
HERE=Path(__file__).resolve().parent

def stage(spec,directory):
    if spec['kind']=='assertions':
        for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
        expanded=cases();reg=json.loads((HERE/'registration.json').read_bytes())
        require({x['id'] for x in expanded}=={x['id'] for x in reg['cases'] if x['kind']=='forward'},'REGISTRY_EXPANSION_MISMATCH')
        require(len({x['id'] for x in expanded})==len(expanded),'DUPLICATE_REGISTRY_ID')
        require(all(c['parameters']['dt_s'] in (.1,.05) and c['parameters']['seconds']<=1800 for c in expanded),'FINITE_CAMPAIGN_BOUND')
        from .coordination import control_options
        require(control_options({'extensions':True,'fault_at_s':30,'hidden_state':'NO','architecture':'NEUTRAL_BUFFER'})=={'extensions':True,'architecture':'NEUTRAL_BUFFER'},'CONTROLLER_FUTURE_SCHEDULE_ACCESS')
        from v0_2.tests.tools.memphis_failure_closure_v1.negative import run
        witnesses=run()
        save(directory/'expanded_inputs.json',expanded)
        return dict(kind='registry_and_refusal_checks',dynamic_cases=len(expanded),old_refusal_witnesses=witnesses)
    if spec['kind']=='old':
        from v0_2.tests.tools.memphis_failure_closure_v1.group_model.simulation import run
        from v0_2.tests.tools.memphis_failure_closure_v1.checks import evaluate as old_evaluate
        bound=next(x for x in json.loads((HERE/'prior_baseline.json').read_bytes()) if x['id']==spec['prior_id'])
        p=directory/'case';run(bound['parameters'],p)
        result,points=old_evaluate(p,bound['parameters'])
        require(result['raw_sha256']==bound['raw_sha256'],'EXACT_BASELINE_RAW_EVIDENCE_DRIFT')
        save(directory/'forward_result.json',result);save(directory/'plot_data.json',points)
        return dict(kind='fresh_exact_old_case_baseline',cases=[result])
    if spec['kind']=='forward':
        from .simulation import run
        c=next(x['parameters'] for x in cases() if x['id']==spec['id'])
        save(directory/'case_spec.json',c);run(c,directory/'case');result=evaluate(directory/'case',c);gc.collect()
        print('HYDRAULIC_ACTUAL_CASE '+c['id']+' '+str(result['grades']),flush=True)
        return dict(kind='fresh_coupled_engineering_case',cases=[result])
    if spec['kind']=='final':
        from .report import finalize
        return finalize(directory)
    raise ValueError('UNREGISTERED_STAGE')
