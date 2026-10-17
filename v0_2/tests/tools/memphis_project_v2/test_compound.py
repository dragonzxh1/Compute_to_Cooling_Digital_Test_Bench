"""New bounded DEVELOPMENT regressions; only executed in verified hosted Job."""
import os
if os.environ.get('MEMPHIS_VERIFIED_PID')!=str(os.getpid()):raise RuntimeError('VERIFIED_REMOTE_TEST_ONLY')
from dataclasses import replace
import pytest
from .coordination import Coordinator,ProjectProtection,SourcePLC
from .test_project import observation

def call(c,t,**kw):
    ns=round(t*1e9)
    o=observation(sample_ns=ns-100000000,release_ns=ns,record_id='m:'+str(ns),**kw)
    s=ProjectProtection().evaluate(o,ns)
    return c.request(o,s,ns),o,s

def source_first():
    c=Coordinator()
    call(c,.1,w1_available=False)
    call(c,1.1,w1_available=False)
    assert c.state=='STOP_SOURCE' and c.source_fault_handled
    call(c,1.3,w1_available=False,source_speed=0.)
    call(c,1.5,w1_available=False,source_speed=0.,source_valve=0.)
    assert c.path=='W2' and c.state=='OPEN'
    call(c,1.7,w1_available=False,source_speed=0.,source_path='W2')
    assert c.state=='BUILD_COLD'
    call(c,55.7,w1_available=False,source_path='W2')
    assert c.state=='RUN' and c.failure_seen and not c.startup_required
    return c

def test_source_then_thermal_not_blocked_by_historical_latch():
    c=source_first()
    r,_,_=call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    assert c.thermal_takeover_used and r['load_tank']=='B' and c.state=='STOP_SOURCE'
    assert r['source_path']=='W2' and c.needed_tank=='B'

def test_no_duplicate_thermal_action():
    c=source_first()
    for t in (56.,56.2,56.4):call(c,t,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    assert sum(e['reason']=='SECONDARY_INLET44_5_AND_MEASURED_B_RESERVE' for e in c.events)==1

def test_same_source_tank_transfer_does_not_restart_standby_54s():
    c=source_first();ready=c.returned_at
    call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    call(c,56.2,w1_available=False,source_path='W2',source_speed=0.,maximum_secondary_inlet_c=44.6)
    call(c,56.4,w1_available=False,source_path='W2',source_speed=0.,source_valve=0.,maximum_secondary_inlet_c=44.6)
    assert c.tank=='B' and c.path=='W2' and c.state=='OPEN'
    call(c,56.6,w1_available=False,source_path='W2',source_tank='B',source_speed=0.,maximum_secondary_inlet_c=44.6)
    assert c.state=='RUN' and c.returned_at==ready

def test_warm_backup_refused_without_consuming_takeover():
    c=source_first()
    r,_,_=call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6,tank_B_tt_k=(321.,)*4)
    assert not c.thermal_takeover_used and r['load_tank']=='A'
    assert r['thermal_blocked_reason']=='B_COLD_RESERVE_NOT_PROVEN'

def test_later_proven_cold_backup_can_be_used():
    c=source_first()
    call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6,tank_B_tt_k=(321.,)*4)
    r,_,_=call(c,56.2,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    assert r['load_tank']=='B' and c.thermal_takeover_used

def test_unacknowledged_source_path_cannot_trigger_reserve_transfer():
    c=source_first()
    r,_,_=call(c,56.,w1_available=False,source_path='W1',maximum_secondary_inlet_c=44.6)
    assert not c.thermal_takeover_used and r['thermal_blocked_reason']=='ACTIVE_SOURCE_NOT_PROVEN'

def test_stale_observation_refuses_thermal_takeover():
    c=source_first();now=56_000_000_000
    o=observation(sample_ns=now-2_000_000_000,release_ns=now,record_id='stale',source_path='W2',w1_available=False,maximum_secondary_inlet_c=44.6)
    s=ProjectProtection().evaluate(o,now);r=c.request(o,s,now)
    assert not c.thermal_takeover_used and r['load_tank']=='A' and r['thermal_blocked_reason']=='PROTECTION_BLOCK'

def test_pressure_fault_not_overridden_by_thermal_takeover():
    c=source_first()
    r,_,_=call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6,wet_inlet_gauge_pa=700000.)
    assert c.state=='PRESSURE_STOP' and not r['source_enable'] and not c.thermal_takeover_used

def test_no_source_fault_not_restarted_by_thermal_takeover():
    c=source_first()
    call(c,56.,w1_available=False,w2_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    r,_,_=call(c,57.,w1_available=False,w2_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    assert c.state=='NO_SOURCE' and not r['source_enable'] and not c.thermal_takeover_used

def test_thermal_only_also_works_once():
    c=Coordinator()
    r,_,_=call(c,.1,maximum_secondary_inlet_c=44.6)
    assert r['load_tank']=='B' and c.thermal_takeover_used and not c.source_fault_handled

def test_source_plc_still_rejects_open_moving_change():
    p=SourcePLC();c=source_first()
    r,o,s=call(c,56.,w1_available=False,source_path='W2',maximum_secondary_inlet_c=44.6)
    p.issue(r,s,o,56_000_000_000)
    with pytest.raises(ValueError,match='FORBIDDEN_OPEN_OR_MOVING_PATH_CHANGE'):
        p.issue(dict(r,source_tank='B'),s,o,56_000_000_000)

def test_future_observation_still_rejected():
    with pytest.raises(ValueError,match='FUTURE'):
        ProjectProtection().evaluate(observation(sample_ns=2,release_ns=3),1)
