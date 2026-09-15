from c2c.controls.pid import PID
from c2c.controls.supervisory import SupervisoryIntent
from c2c.controls.virtual_plc import VirtualPLC


def test_pid_saturates_without_integral_runaway():
    pid = PID(10, 5, 0, 0, 100)
    for _ in range(100):
        assert pid.step(100, 1) == 100
    assert pid.integral == 0


def test_plc_uses_local_fallback_when_intent_times_out():
    cfg = {
        "dp_target_kpa": 60,
        "supply_temp_setpoint_c": 30,
        "pump_speed_min_pct": 25,
        "pump_speed_max_pct": 100,
        "valve_min_pct": 5,
        "valve_max_pct": 100,
        "pump_ramp_pct_s": 2,
        "valve_ramp_pct_s": 2,
        "intent_timeout_s": 10,
        "dp_deadband_kpa": 0,
        "temp_deadband_k": 0,
        "dp_pid": {"kp": 1, "ki": 0, "kd": 0},
        "temp_pid": {"kp": 1, "ki": 0, "kd": 0},
    }
    intent = SupervisoryIntent(0, 100, 25, 0.01, 90, 100)
    output = VirtualPLC(cfg).step(60, 30, 1, 20, intent, True)
    assert output.intent_status == "LOCAL_FALLBACK"
    assert output.accepted_temp_setpoint_c == 30
    assert output.accepted_dp_kpa == 60


def test_plc_clamps_intent_to_configured_safety_bounds():
    cfg = {
        "dp_target_kpa": 60,
        "supply_temp_setpoint_c": 30,
        "supply_temp_min_c": 26,
        "supply_temp_max_c": 31,
        "dp_min_kpa": 40,
        "dp_max_kpa": 80,
        "pump_speed_min_pct": 25,
        "pump_speed_max_pct": 100,
        "valve_min_pct": 5,
        "valve_max_pct": 100,
        "pump_ramp_pct_s": 2,
        "valve_ramp_pct_s": 2,
        "intent_timeout_s": 10,
        "dp_deadband_kpa": 0,
        "temp_deadband_k": 0,
        "dp_pid": {"kp": 1, "ki": 0, "kd": 0},
        "temp_pid": {"kp": 1, "ki": 0, "kd": 0},
    }
    intent = SupervisoryIntent(0, 100, 10, 0.01, 200, 100)
    output = VirtualPLC(cfg).step(60, 30, 1, 0, intent, True)
    assert output.requested_temp_setpoint_c == 10
    assert output.accepted_temp_setpoint_c == 26
    assert output.requested_dp_kpa == 200
    assert output.accepted_dp_kpa == 80


def test_plc_deadband_suppresses_small_measurement_errors():
    cfg = {
        "dp_target_kpa": 60,
        "supply_temp_setpoint_c": 30,
        "pump_speed_min_pct": 25,
        "pump_speed_max_pct": 100,
        "valve_min_pct": 5,
        "valve_max_pct": 100,
        "pump_ramp_pct_s": 2,
        "valve_ramp_pct_s": 2,
        "intent_timeout_s": 10,
        "dp_deadband_kpa": 0.2,
        "temp_deadband_k": 0.15,
        "dp_pid": {"kp": 1, "ki": 0, "kd": 0},
        "temp_pid": {"kp": 10, "ki": 0, "kd": 0},
    }
    output = VirtualPLC(cfg).step(60.1, 30.1, 1, 0, None, False)
    assert output.pump_speed_pct == 60
    assert output.valve_position_pct == 40


def test_plc_initial_actuators_respect_configured_bounds():
    cfg = {
        "dp_target_kpa": 75,
        "supply_temp_setpoint_c": 30,
        "pump_speed_min_pct": 70,
        "pump_speed_max_pct": 80,
        "valve_min_pct": 50,
        "valve_max_pct": 55,
        "pump_ramp_pct_s": 0,
        "valve_ramp_pct_s": 0,
        "intent_timeout_s": 10,
        "dp_deadband_kpa": 0,
        "temp_deadband_k": 0,
        "dp_pid": {"kp": 1, "ki": 0, "kd": 0},
        "temp_pid": {"kp": 1, "ki": 0, "kd": 0},
    }
    output = VirtualPLC(cfg).step(75, 30, 1, 0, None, False)
    assert output.pump_speed_pct == 70
    assert output.valve_position_pct == 50
