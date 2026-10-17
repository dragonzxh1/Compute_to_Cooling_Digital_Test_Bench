import os
if os.environ.get('MEMPHIS_VERIFIED_PID')!=str(os.getpid()):raise RuntimeError('VERIFIED_REMOTE_TEST_ONLY')
from dataclasses import replace
import pytest
from .cases import registration,config,validate
from .plant import RackLoop
from .simulation import Feedback
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import Sensor,measurement_view,IndependentSafety

def c():return config(next(s for s in registration()['cases'] if s['id']=='SR_HOT'))
def observation():
    x=c();return Sensor(x['sensor_delay_ns']).sample(RackLoop(x).snapshot(0,.9,'test'))

@pytest.mark.parametrize('racks',[1,6])
def test_design_point_and_no_six_head_on_single(racks):
    x=c() if racks==1 else config(next(s for s in registration()['cases'] if s['id']=='SIX_HOT'))
    s=RackLoop(x).snapshot(0,.9,'test')
    assert len(s.branch_flows_m3_s)==racks
    assert s.flow_m3_s==pytest.approx(x['design_flow_m3_s'],rel=1e-12)
    assert s.dp_pa==pytest.approx(x['design_dp_pa'],rel=1e-12)
    if racks==1:assert s.dp_pa!=pytest.approx(371810)

def test_45_is_inlet_not_return():
    x=c();o=observation();assert o.rack_return_k[0]>318.15 and o.supply_k<318.15
    channels=IndependentSafety(x).channels(o,o.available_ns,10**9)
    assert 'LIQUID_SUPPLY_LIMIT_MEASURED' not in {r['code'] for r in channels}

@pytest.mark.parametrize('bad',['future','missing','stale'])
def test_future_or_invalid_no_truth_fallback(bad):
    x=c();o=observation();f=Feedback(x)
    if bad=='future':
        with pytest.raises(ValueError,match='FUTURE'):f.request(o,o.available_ns-1,10**9)
    else:
        if bad=='missing':o=replace(o,quality='MISSING',pump_speed=None)
        now=o.available_ns+(2*10**9 if bad=='stale' else 0)
        assert f.request(o,now,10**9) is None
        assert measurement_view(o,now,10**9).measured_speed is None

def test_no_future_forcing_in_feedback():
    x=c();o=observation();a=Feedback(x).request(o,o.available_ns,10**9)
    x['fault']='STUCK';x['load_profile'][0]['rack_it_w']=[0]
    assert Feedback(x).request(o,o.available_ns,10**9)==a

@pytest.mark.parametrize('field,value',[('hx_ua_w_k',None),('hx_ua_w_k',float('nan')),('rack_count',18),('supply_hard_k',320.)])
def test_refusals(field,value):
    x=c();x[field]=value
    with pytest.raises((ValueError,TypeError)):validate(x)

def test_actual_speed_drives_flow():
    p=RackLoop(c());assert p.snapshot(0,.35,'a').flow_m3_s<p.snapshot(0,.9,'b').flow_m3_s

def test_pump_and_IT_heat_ownership():
    x=c();p=RackLoop(x);p.advance(0,100000000,.9,[155000],314.15);l=p.ledger()
    assert l['it_j']==15500 and l['liquid_j']==14725 and l['air_j']==775
    assert abs(l['residual_j'])<=l['bound_j']

def test_cancellation_bound_is_operand_scaled_and_rejects_real_error():
    from .audit import tol
    # Persisted Build2 near-cancellation witness, not a fitted multiplier.
    reconstructed=15.128076691681912;recorded=15.128076691710902
    operands=147437.19189669657+147250.+202.3199733882569
    assert abs(reconstructed-recorded)>tol(reconstructed,recorded)
    assert abs(reconstructed-recorded)<=tol(operands)
    assert .001>tol(operands)  # a genuine1mW accounting error still fails
