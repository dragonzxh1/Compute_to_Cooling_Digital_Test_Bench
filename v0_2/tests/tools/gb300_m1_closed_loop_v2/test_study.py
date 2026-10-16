"""V2-only tests. Run in the controlled remote worker, never local model probes."""
import os
import pytest
if os.environ.get('SIX_RACK_V2_VERIFIED_PID')!=str(os.getpid()):
    pytest.skip('Requires externally verified remote Job',allow_module_level=True)
from dataclasses import replace
from math import sqrt
from .cases import config,matrix
from .extensions import StudyPlant,FaultActuator,FaultSensor,apply_fault
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import actuator_config,measurement_view
from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import read,ROOT


def test_exact_matrix_and_one_factor_at_a_time():
    cases=matrix()
    assert len(cases)==21
    assert {s['group'] for s in cases.values()}=={'baseline','sensitivity-a','sensitivity-b','fault'}
    for s in cases.values():
        changed=sum(s['setting'][k]!=1 for k in ('ua_scale','pump_head_scale','inventory_scale'))
        assert changed<=1


def test_pump_uncertainty_is_not_a_refitted_noop():
    specs=matrix();base=specs['BASE__LOAD_STEP']; high=specs['PUMP_HIGH__LOAD_STEP']
    p=StudyPlant(config(base),base['setting']); h=StudyPlant(config(high),high['setting'])
    assert p.graph==h.graph
    a=p.snapshot(0,.6,'test');b=h.snapshot(0,.6,'test')
    assert b.flow_m3_s/a.flow_m3_s==pytest.approx(sqrt(1.2),rel=32*2**-52)
    # Refitting the same quadratic design point cancels the shape factor.
    c=config(base);c['quadratic_shutoff_factor']=1.5
    same=StudyPlant(c,base['setting']).snapshot(0,.6,'test')
    assert same.flow_m3_s==pytest.approx(a.flow_m3_s,rel=32*2**-52)


def test_inventory_scaling_changes_storage_not_sources():
    specs=matrix();s=specs['INVENTORY_LOW__LOAD_STEP'];b=specs['BASE__LOAD_STEP']
    p=StudyPlant(config(s),s['setting']);q=StudyPlant(config(b),b['setting'])
    assert p.capacities==[x*.5 for x in q.capacities]
    assert p.c['load_profile']==q.c['load_profile'] and p.curve==q.curve


def test_held_packets_do_not_get_fresh_timestamps():
    spec=matrix()['BASE__LOAD_STEP'];p=StudyPlant(config(spec),spec['setting'])
    sensor=FaultSensor(100_000_000)
    sensor.sample(p.snapshot(0,.35,'s0'));old=sensor.release(100_000_000)
    sensor.withheld=True
    assert sensor.sample(p.snapshot(2_000_000_000,.35,'new')) is None
    assert sensor.release(2_100_000_000) is old
    assert measurement_view(old,2_100_000_000,10**9).quality=='MISSING'


def test_physical_faults_are_silent_and_recover_without_reset_authority():
    spec=matrix()['ACTUATOR_RECOVERY'];c=config(spec);p=StudyPlant(c,spec['setting'])
    profile=read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json')
    a=FaultActuator(actuator_config(profile),.35);sensor=FaultSensor(c['sensor_delay_ns'])
    apply_fault(spec['fault'],10_000_000_000,a,sensor,p)
    assert a.silent_hold and not a.fault_stuck
    apply_fault(spec['fault'],45_000_000_000,a,sensor,p)
    assert not a.silent_hold and not a.fault_stuck


def test_missing_sensor_does_not_fallback_to_truth():
    spec=matrix()['BASE__LOAD_STEP'];p=StudyPlant(config(spec),spec['setting'])
    sensor=FaultSensor(100_000_000);sensor.missing=True
    o=sensor.sample(p.snapshot(0,.35,'a'))
    assert o.quality=='MISSING' and o.pump_speed is None and o.flow_m3_s is None
