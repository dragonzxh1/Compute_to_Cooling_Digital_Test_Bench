"""New integration negatives; no frozen fixture/test expectation is edited."""
import copy
from dataclasses import replace
import pytest

from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.scheduler import MeasurementView, PriorCommand, SimulatedPLC, CapabilityError
from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from .simulation import ROOT, HERE, read, validate_config
from .interfaces import Sensor, Feedback, IndependentSafety, IntegrationPLC, measurement_view
from .plant import SixRackPlant, audit_hydraulics


def config():
    return read(HERE/'scenario.json')


def engine():
    return SplitEngine(read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json'),
        read(ROOT/'phase5_r5_2_silent_tracking_fault_registration.json')['classifier'])


def observation():
    c = config()
    return Sensor(c['sensor_delay_ns']).sample(SixRackPlant(c).snapshot(0, .35, 'initial'))


def test_reused_hydraulic_solver_at_registered_design_point():
    c = config(); plant = SixRackPlant(c)
    s = plant.snapshot(0, c['design_speed'], 'test')
    assert s.flow_m3_s == pytest.approx(c['design_secondary_flow_m3_s'], rel=1e-12)
    assert s.dp_pa == pytest.approx(c['design_secondary_dp_pa'], rel=1e-12)
    assert len(s.branch_flows_m3_s) == 6


def test_future_sensor_cannot_be_released_or_consumed():
    o = observation()
    with pytest.raises(ValueError, match='FUTURE'):
        measurement_view(o, o.available_ns-1, 10**9)
    with pytest.raises(CapabilityError, match='UNRELEASED'):
        MeasurementView(0, .35, 0, 1, 'VALID', 'future')
    sensor = Sensor(100)
    sensor.sample(SixRackPlant(config()).snapshot(0, .35, 'test'))
    assert sensor.release(99) is None
    assert sensor.release(100).measurement_record_id == 'measurement:0'


@pytest.mark.parametrize('kind', ['stale', 'quality'])
def test_unobservable_evidence_is_not_tracking_confirmation(kind):
    c = config(); o = observation(); now = o.available_ns
    if kind == 'stale': now += c['sensor_max_age_ns']+1
    else: o = replace(o, quality='MISSING', pump_speed=None)
    m = measurement_view(o, now, c['sensor_max_age_ns'])
    e = engine(); pre = e.pre(m, PriorCommand(.9, 0, 'initial'), 'invalid')
    assert pre.data()['state'] == 'INSUFFICIENT_MEASUREMENT'
    s = e.safety(pre, IndependentSafety(c).channels(o, now, c['sensor_max_age_ns']))
    assert s.data()['severity'] == 'FAULT'
    assert 'ACTUATOR_TRACKING_CONFIRMED' not in s.data()['reason_codes']


def test_duplicate_measurement_id_never_earns_second_credit():
    e = engine(); prior = PriorCommand(.35, 0, 'initial')
    for i, command in enumerate((.35, .8, .8, .8)):
        now = (i+1)*200_000_000
        # Last packet reuses exact earlier source identity and sample timestamp.
        sample = now if i < 3 else 600_000_000
        m = MeasurementView(now, .35, sample, sample, 'VALID', 'sample:'+str(sample))
        pre = e.pre(m, prior, 'duplicate:'+str(i)); safety = e.safety(pre)
        plc = SimulatedPLC([dict(time_ns=now, plc_command=command,
            command_timestamp_ns=now if command != prior.value else prior.issue_ns)])
        plc.prior = prior
        e.accept_plc(plc.issue(safety, m)); e.post(); prior = plc.prior
        if i == 2:
            before = (e.q.carried_suspicion_evidence, len(e.q.response_history), set(e.q.consumed_samples))
    assert (e.q.carried_suspicion_evidence, len(e.q.response_history), set(e.q.consumed_samples)) == before


def test_wrong_receipt_is_refused_without_fabricated_producer():
    e = engine(); o = observation(); m = measurement_view(o, o.available_ns, 10**9)
    pre = e.pre(m, PriorCommand(.35, 0, 'initial'), 'correct')
    e.safety(pre)
    other = engine(); p = other.pre(m, PriorCommand(.35, 0, 'initial'), 'wrong')
    s = other.safety(p)
    plc = SimulatedPLC([dict(time_ns=m.time_ns, plc_command=.35, command_timestamp_ns=0)])
    with pytest.raises(CapabilityError, match='AUTHORITY'):
        e.accept_plc(plc.issue(s, m))


def test_nonfinite_inputs_and_inconsistent_hydraulics_refused():
    c = config(); c['hx_ua_w_k'] = float('nan')
    with pytest.raises(ValueError, match='NONFINITE'): validate_config(c)
    with pytest.raises(ValueError, match='NONFINITE'):
        measurement_view(replace(observation(), pump_speed=float('inf')), 100_000_000, 10**9)
    from v0_2.hydraulics.solver import solve
    p = SixRackPlant(config()); h = solve(p.graph, p.curve, .35, 1009)
    with pytest.raises(ValueError, match='INCONSISTENT'):
        audit_hydraulics(replace(h, total_flow_m3_s=h.total_flow_m3_s*2), 1009)


def test_controller_has_no_future_load_or_truth_inputs():
    c = config(); o = observation()
    a = Feedback(c).request(o, o.available_ns, 10**9)
    c['load_profile'][1]['rack_it_w'] = [0]*6
    c['silent_stuck_at_ns'] = 0
    b = Feedback(c).request(o, o.available_ns, 10**9)
    assert a == b
    assert not hasattr(o, 'actual_speed') and not hasattr(o, 'future_load')


def test_safety_pressure_priority_and_no_second_tracking_timer():
    c = config(); o = replace(observation(), dp_pa=700000., supply_k=320.)
    policy = IndependentSafety(c)
    channels = policy.channels(o, o.available_ns, 10**9)
    assert {x['code'] for x in channels} >= {'OVERPRESSURE_MEASURED','LIQUID_SUPPLY_LIMIT_MEASURED'}
    assert not any('TRACKING' in x['code'] for x in channels)
    s = Record.make(dict(record_id='s', time_ns=o.available_ns, severity='FAULT',
        reason_codes=[x['code'] for x in channels]))
    env = policy.envelope(s).data()
    assert env['minimum_speed'] == env['maximum_speed'] == .3
    env['safety_digest'] = 'bad'
    with pytest.raises(ValueError, match='WRONG_SAFETY'):
        IntegrationPLC(.35).issue(.9, Record.make(env), s,
            measurement_view(o, o.available_ns, 10**9))


def test_missing_safety_configuration_stops_before_simulation():
    c = config(); c['safety_recovery_samples'] = 1
    with pytest.raises(ValueError, match='MANDATORY_SAFETY'): validate_config(c)


def test_physical_flow_is_driven_by_actual_not_commanded_speed():
    p = SixRackPlant(config())
    stuck = p.snapshot(0, .35, 'stuck'); healthy = p.snapshot(0, .9, 'healthy')
    assert stuck.flow_m3_s < healthy.flow_m3_s
    assert stuck.dp_pa < healthy.dp_pa
    assert stuck.flow_m3_s/healthy.flow_m3_s == pytest.approx(.35/.9)


def test_conservative_heat_step_and_no_double_pump_heat():
    c = config(); p = SixRackPlant(c)
    p.advance(0, c['physics_dt_ns'], .35, c['load_profile'][0]['rack_it_w'])
    ledger = p.ledger()
    assert ledger['energy_closed'] and ledger['heat_source_closed'] and ledger['pump_energy_closed']
