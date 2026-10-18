"""Single registered comparison campaign; engineering FAIL does not fail software execution."""
import json,hashlib
from pathlib import Path
from .audit import group,need
HERE=Path(__file__).resolve().parent

def stage(spec,directory):
    if spec['kind']=='final':
        from .report import finalize
        return finalize(directory)
    if spec['kind']=='negative':
        from .negative import run
        return run()
    from .group_model.simulation import run
    from .analysis import diagnose
    c=dict(id=spec['id'],scope='GROUP18',ua_w_k=220000.,dt_s=.1,seconds=240.,
        source_variant='V9',tank_kind='STRATIFIED',fault='W1_LOSS',fault_at_s=30.,recharge_at_s=120.)
    c.update({k:v for k,v in spec.items() if k not in ('group','kind','expect')})
    if spec.get('recharge'):c.pop('fault');c.pop('fault_at_s')
    (directory/'case_spec.json').write_text(json.dumps(c,sort_keys=True),encoding='utf-8')
    run(c,directory/'case')
    result=group(directory/'case',c)
    result['diagnosis']=diagnose(directory/'case',c)
    if spec['id']=='G_WET_LOSS':
        expected=json.loads((HERE/'baseline_hashes.json').read_bytes())
        actual={k:hashlib.sha256((directory/'case'/k).read_bytes()).hexdigest() for k in expected}
        need(actual==expected,'V2_BASELINE_PHYSICS_OR_CAUSAL_RAW_DRIFT');result['baseline_raw_hashes']=actual
    if spec.get('expect')=='REFUSE_B':
        need(not result['actual_AB_switches'],'NEGATIVE_WARM_B_ACCEPTED')
    if spec.get('expect')=='FAIL':
        need(result['grades']['FULL_LOAD_CONTINUITY']=='FAIL','NEGATIVE_FALSE_CONTINUITY_PASS')
    return result
