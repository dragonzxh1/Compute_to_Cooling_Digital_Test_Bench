from math import exp

import pytest
from v0_2.actuators.pump import PumpActuator, PumpActuatorConfig
from v0_2.control.inner_loop import ActuatorCommand
from v0_2.control.outer_feedback import OuterConfig, OuterFeedback
from v0_2.control.pid import PIDConfig, TrackingPID
from v0_2.examples.phase5_validation import fixture_configs, run_scenario
from v0_2.measurement.local_sensor import LocalMeasurement, MeasuredSnapshot, SensorConfig
from v0_2.plant.controlled_loop import Disturbance, run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.safety.supervisor import SafetyState, SafetySupervisor
from v0_2.thermal.validity import ThermalError


def actuator_config(*, delay=0, ramp=10.0):
    return PumpActuatorConfig(0.1, 0.9, 1.0, ramp, delay)


def plc_command(value, now=0, sequence=1):
    return ActuatorCommand(
        f"actuator-command:{now}:{sequence}",
        now,
        "PLC",
        f"plc-cycle:{now}:{sequence}",
        "accepted-target:test",
        "safety-envelope:test",
        value,
        value,
        "TEST_FIXTURE",
        "NORMAL",
        (f"plc-cycle:{now}:{sequence}",),
    )


def test_actuator_analytic_lag_without_ramp():
    actuator = PumpActuator(actuator_config(), 0.2)
    actuator.command(plc_command(0.8), 0)
    actuator.advance(0, 1_000_000_000)
    assert actuator.actual == pytest.approx(0.8 + (0.2 - 0.8) * exp(-1))


def test_actuator_saturation_ramp_delay_and_stuck():
    actuator = PumpActuator(actuator_config(delay=1_000_000_000, ramp=0.1), 0.2)
    actuator.command(plc_command(1.2), 0)
    actuator.advance(0, 500_000_000)
    assert actuator.actual == 0.2
    actuator.advance(500_000_000, 1_500_000_000)
    assert actuator.actual <= 0.25 + 1e-12
    assert actuator.commanded == 0.9
    assert len(actuator.saturation_events) == 1
    actuator.fault_stuck = True
    old = actuator.actual
    actuator.advance(1_500_000_000, 3_000_000_000)
    assert actuator.actual == old


def measured(sequence=1, *, temperature=310, dp=20000, speed=0.6, flow=0.1, available=0, quality=None):
    return MeasuredSnapshot(
        0, available, sequence, (("b0:die", temperature),), dp, flow, speed,
        True, True, False,
        tuple((x, "VALID") for x in ("temperature", "dp", "flow", "pump_speed", "pump_status"))
        if quality is None else quality,
    )


def test_measurement_release_and_controller_no_truth_reference():
    plant, controls = physical_fixture()
    actuator = PumpActuator(actuator_config(), 0.6)
    sensor = LocalMeasurement(SensorConfig(200_000_000, 300_000_000))
    sensor.sample(0, plant, plant.initial_state, controls, actuator)
    assert sensor.release(299_999_999) is None
    record = sensor.release(300_000_000)
    assert record.layer == "MEASURED" and record.available_ns == 300_000_000
    assert not hasattr(record, "plant") and not hasattr(record, "actual")
    assert record.pump_speed == actuator.actual
    outer_cfg = OuterConfig(PIDConfig(1000, 0, 0, 1_000_000_000, -10000, 20000, 20000), 20000, 305)
    controller = OuterFeedback(outer_cfg)
    a = controller.update(300_000_000, record, 20000, 1_000_000_000)
    # Different hidden truth cannot change a current action while the released record is fixed.
    b = OuterFeedback(outer_cfg).update(300_000_000, record, 20000, 1_000_000_000)
    assert a == b and a.ff_component_pa == 0
    with pytest.raises(ThermalError):
        controller.update(299_999_999, record, 20000, 1_000_000_000)


def test_tracking_anti_windup_and_bumpless_manual_transfer():
    config = PIDConfig(0.00002, 0.00001, 0, 200_000_000, 0.2, 0.9, 0.9, tracking_gain=5)
    pid = TrackingPID(config)
    for _ in range(100):
        pid.update(100000, 0.9)
    assert abs(pid.integral) <= 0.9
    pid.update(0, 0.5, automatic=False)
    assert pid.update(0, 0.5) == pytest.approx(0.5)


def test_safety_pressure_priority_hard_threshold_and_fault_latch():
    policy = fixture_configs()[-1]
    hard = SafetySupervisor(policy).evaluate(
        0, measured(temperature=policy.hard_k, dp=20000), 1_000_000_000, 50000
    )
    assert hard.state == SafetyState.PROTECTED
    assert "HARD_THERMAL_MEASURED" in hard.reasons
    safety = SafetySupervisor(policy)
    d = safety.evaluate(0, measured(temperature=350, dp=61000), 1_000_000_000, 50000)
    assert d.state == SafetyState.FAULT
    assert d.envelope.minimum_speed_fraction == policy.fault_speed
    assert d.envelope.maximum_speed_fraction == policy.fault_speed
    assert "OVERPRESSURE_MEASURED" in d.reasons
    d = safety.evaluate(3_000_000_000, measured(2, temperature=300), 4_000_000_000, 30000)
    assert d.state == SafetyState.FAULT
    safety.reset_fault(3_000_000_000)
    d = safety.evaluate(3_000_000_000, measured(3, temperature=300), 4_000_000_000, 30000)
    assert d.state == SafetyState.FF_DISABLED


def test_sensor_failure_and_measured_stall_detection():
    policy = fixture_configs()[-1]
    for failed_channel in ("temperature", "dp", "flow", "pump_speed", "pump_status"):
        safety = SafetySupervisor(policy)
        broken = measured(
            quality=tuple(
                (x, "MISSING" if x == failed_channel else "VALID")
                for x in ("temperature", "dp", "flow", "pump_speed", "pump_status")
            )
        )
        assert safety.evaluate(0, broken, 1_000_000_000, 25000).state == SafetyState.FAULT
    safety = SafetySupervisor(policy)
    for t in (0, 1_000_000_000, 2_100_000_000):
        result = safety.evaluate(t, measured(t + 1), 4_000_000_000, 25000, commanded_speed=0.9)
    assert result.state == SafetyState.FAULT
    assert "ACTUATOR_TRACKING_FAILURE_MEASURED" in result.reasons


def test_closed_loop_load_and_conservation():
    run = run_scenario("TUNE-01-load")
    metrics = run.metrics()
    assert metrics["max_mass_residual_kg_s"] < 1e-8
    assert metrics["max_energy_residual_j"] < 1e-3
    assert metrics["temperature_iae_k_s"] > 0
    assert max(r.pump_actual for r in run.rows) <= run.actuator_config.maximum
    assert all(r.safety_state != "FAULT" for r in run.rows)


def test_unreleased_future_disturbance_cannot_change_current_command():
    plant, controls = physical_fixture()
    configs = fixture_configs()
    a = run_feedback(plant, controls, 5_000_000_000, *configs)
    b = run_feedback(plant, controls, 5_000_000_000, *configs, disturbances=(Disturbance(4_000_000_000, power_each_w=240),))
    assert [r.pump_command for r in a.rows if r.time_ns < 4_000_000_000] == [r.pump_command for r in b.rows if r.time_ns < 4_000_000_000]


def test_outer_load_response_is_measured_and_increases_cooling_effort():
    run = run_scenario("TUNE-01-load")
    before = [r for r in run.rows if 8_000_000_000 <= r.time_ns < 10_000_000_000]
    after = [r for r in run.rows if r.time_ns >= 30_000_000_000]
    assert max(r.measured_device_k for r in after) > max(r.measured_device_k for r in before)
    assert max(r.requested_dp_pa for r in after) > max(r.requested_dp_pa for r in before)
    assert max(r.pump_actual for r in after) > max(r.pump_actual for r in before)
    assert max(r.total_flow_kg_s for r in after) > max(r.total_flow_kg_s for r in before)


@pytest.mark.parametrize("scenario", ["TUNE-02-fws-temperature", "TUNE-03-fws-flow", "TUNE-04-branch-restriction"])
def test_registered_disturbances_remain_causal_and_conservative(scenario):
    run = run_scenario(scenario)
    metrics = run.metrics()
    assert metrics["max_mass_residual_kg_s"] < 1e-8
    assert metrics["max_energy_residual_j"] < 1e-3
    baseline = next(r for r in run.rows if r.time_ns == 10_000_000_000)
    assert all(r.pump_command == baseline.pump_command for r in run.rows if r.time_ns == 10_000_000_000)


def test_thermal_state_continuity_at_control_event():
    run = run_scenario("TUNE-01-load")
    at_event = next(r for r in run.rows if r.time_ns == 10_000_000_000)
    previous = max((r for r in run.rows if r.time_ns < at_event.time_ns), key=lambda x: x.time_ns)
    assert abs(at_event.device_k - previous.device_k) < 0.2


def test_runtime_sensor_failure_and_actuator_failure_do_not_read_truth():
    plant, controls = physical_fixture()
    configs = fixture_configs()
    sensor_fault = run_feedback(
        plant, controls, 6_000_000_000, *configs,
        disturbances=(Disturbance(3_000_000_000, sensor_failures=("temperature",)),),
    )
    assert any(r.safety_state == "FAULT" for r in sensor_fault.rows if r.time_ns >= 3_000_000_000)
    pump_fault = run_feedback(
        plant, controls, 8_000_000_000, *configs,
        disturbances=(Disturbance(3_000_000_000, pump_stuck=True),),
    )
    assert any(r.safety_state == "FAULT" for r in pump_fault.rows)


def test_safety_hysteresis_does_not_chatter():
    policy = fixture_configs()[-1]
    safety = SafetySupervisor(policy)
    states = []
    for index, temperature in enumerate((336, 334, 335.5, 334.5, 332.5, 332.0, 332.0, 332.0, 332.0, 332.0)):
        now = index * 500_000_000
        states.append(safety.evaluate(now, measured(index + 1, temperature=temperature), 5_000_000_000, 30000).state)
    assert states[0] == SafetyState.DERATE_REQUESTED
    assert SafetyState.NORMAL not in states[:5]


def test_independent_clocks_and_three_physics_meshes():
    results = [run_scenario("TUNE-01-load", physics_ns=dt) for dt in (200_000_000, 100_000_000, 50_000_000)]
    assert [len(x.steps) for x in results] == [200, 400, 800]
    assert all(x.clocks.outer_ns == 1_000_000_000 for x in results)
    peaks = [x.metrics()["peak_device_k"] for x in results]
    assert abs(peaks[1] - peaks[2]) < abs(peaks[0] - peaks[1]) < 0.1
