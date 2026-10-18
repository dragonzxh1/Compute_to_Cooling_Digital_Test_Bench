"""Stage dispatch; imports only after the hosted Job identity handshake."""
import json,hashlib
from pathlib import Path
from .validation import validate
from .audit import need
from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import read,write

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def buffer(spec,directory):
    from .group_model.tank import Tank
    t=Tank(spec.get('layers',20),'MIXED' if spec.get('mixed') else 'STRATIFIED');initial=t.t[0]
    records=[];before=t.energy();q=330/3600;net=0.;dt=spec.get('dt',.1)
    for i in range(round(90/dt)):
        r=t.advance(dt,q,0.,321.44,314.0948);r['end_s']=(i+1)*dt;records.append(r)
        net+=dt*1009*4000*q*(321.44-r['old_k'][0])
    from .audit import bound
    residual=t.energy()-before-net;need(abs(residual)<=bound(before,t.energy(),net,ops=8192*(len(records)+1)),'BUFFER_INDEPENDENT_LEDGER')
    maxrise=max(r['new_k'][0]-initial for r in records)
    write(directory/'buffer_steps.json',records)
    return dict(case_id=spec['id'],kind='buffer',outlet_initial_c=initial-273.15,maximum_outlet_rise_K=maxrise,final_outlet_c=t.t[0]-273.15,
        cold_remaining_m3=t.cold_volume(),flow_m3_h=330,seconds=90,global_residual_j=residual,
        grades={'PHYSICAL_NUMERICAL_VALIDITY':'PASS','90_SECOND_BUFFER_COMPLIANCE':'PASS' if maxrise<=.5 else 'FAIL','OEM_CALIBRATION_STATUS':'NOT_VERIFIED'},
        condition='50/70% interface diffusion and missing real distributor calibration; nominal15m3 not sufficient proof')

def stage(spec,directory):
    validate(spec);kind=spec['kind']
    if kind=='negative':
        import pytest
        code=pytest.main(['-q','-p','no:cacheprovider',str(HERE/'test_validation.py')]);need(code==0,'NEW_REFUSAL_TEST_FAILURE')
        return dict(case_id=spec['id'],pytest_exitcode=int(code))
    if kind=='baseline':
        from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import run
        expected=read(HERE.parent/'gb300_m1_closed_loop_v2/v1_regression_hashes.json');out={}
        import pytest
        code=pytest.main(['-q','-p','no:cacheprovider',str(HERE.parent/'gb300_m1_closed_loop_v1/test_integration.py')]);need(code==0,'V1_BASELINE_TESTS')
        for name in ('LOAD_STEP','PUMP_STUCK'):
            payload=run(read(HERE.parent/'gb300_m1_closed_loop_v1/scenario.json'),name,directory/name)
            actual={k:hashlib.sha256((directory/name/k).read_bytes()).hexdigest() for k in expected[name]}
            need(actual==expected[name] and payload['status']=='PASS','V1_BASELINE_DRIFT');out[name]=actual
        return dict(case_id=spec['id'],fresh_regression=out)
    if kind=='single_history':
        from v0_2.tests.tools.memphis_single_rack_v1.cases import registration,config
        from v0_2.tests.tools.memphis_single_rack_v1.simulation import run
        from v0_2.tests.tools.memphis_single_rack_v1.audit import audit
        old=next(s for s in registration()['cases'] if s['id']=='SR_STUCK');run(config(old),directory/'case')
        result=audit(directory/'case',old)
        expected=read(HERE/'historical_hashes.json')['SR_STUCK'];actual={k:hashlib.sha256((directory/'case'/k).read_bytes()).hexdigest() for k in expected}
        need(actual==expected,'SINGLE_HISTORY_RAW_DRIFT')
        return dict(case_id=spec['id'],fresh_history=result,raw_hashes=actual)
    if kind=='group_history':
        from v0_2.tests.tools.memphis_project_v2.common import case_by_id
        from v0_2.tests.tools.memphis_project_v2.simulation import run
        from v0_2.tests.tools.memphis_project_v2.audit import audit
        old=case_by_id('WET_LOSS_STRATIFIED');run(old,directory/'case');result=audit(directory/'case',old)
        expected=read(HERE/'historical_hashes.json')['WET_LOSS_STRATIFIED'];actual={k:hashlib.sha256((directory/'case'/k).read_bytes()).hexdigest() for k in expected}
        need(actual==expected,'GROUP_HISTORY_RAW_DRIFT')
        return dict(case_id=spec['id'],fresh_history=result,raw_hashes=actual)
    if kind=='equipment':
        from .engineering import equipment
        return dict(case_id=spec['id'],engineering=equipment())
    if kind=='source_curves':
        from .engineering import curves
        return dict(case_id=spec['id'],engineering=curves())
    if kind=='buffer':return buffer(spec,directory)
    if kind=='unit':
        from .unit import run
        from .audit import unit
        run(spec,directory/'case');return unit(directory/'case')
    if kind=='group':
        from .group_model.simulation import run
        from .audit import group
        c=dict(spec,id=spec['id'],scope='GROUP18',ua_w_k=spec.get('ua',220000.),dt_s=spec.get('dt',.1),seconds=spec.get('seconds',240),
            tank_kind='STRATIFIED',fault_at_s=30.,recharge_at_s=120.,expect='ENGINEERING_RESULTS_NOT_ASSUMED')
        write(directory/'case_spec.json',c);run(c,directory/'case');return group(directory/'case',c)
    raise ValueError('UNREGISTERED_STAGE')
