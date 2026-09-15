import json
from copy import deepcopy
from dataclasses import replace
from math import isfinite

import pandas as pd
import pytest

from c2c.controls.supervisory import SupervisoryIntent
from c2c.controls.virtual_plc import VirtualPLC
from c2c.reports.metrics import _first_response_delay, _integrate_kwh, benchmark_summary
from c2c.simulation.engine import run_benchmark
from c2c.simulation.scenario import load_scenario
from c2c.simulation.validation import ScenarioValidationError, validate_scenario
from c2c.thermal.rc_network import RCThermalModel, ThermalState
from c2c.thermal.transport import TransportDelay


@pytest.fixture(scope="module")
def config():
    return load_scenario("configs/scenarios/workload_step.yaml")[1]


@pytest.fixture(scope="module")
def frame(config):
    return run_benchmark(config)


def test_unstable_two_sided_conduction_is_rejected():
    cfg = {
        "c_die_j_k": 1000,
        "c_package_j_k": 1,
        "c_cold_plate_j_k": 1000,
        "c_coolant_j_k": 1000,
        "r_die_package_k_w": 0.01,
        "r_package_plate_k_w": 10,
        "r_plate_coolant_k_w": 0.01,
    }
    model = RCThermalModel(cfg, ThermalState(1, 0, 0, 0))
    with pytest.raises(ValueError, match="too large"):
        model.step(0, 0, 0, 4180, 1)
    assert model.state.package_temp_c == 0


def test_coolant_advection_limits_timestep(config):
    model = RCThermalModel(config["thermal"], ThermalState(60, 50, 40, 32))
    with pytest.raises(ValueError, match="too large"):
        model.step(0, 30, 10000, 4180, 1)


def test_rc_step_closes_stored_energy_balance(config):
    cfg = config["thermal"]
    initial = ThermalState(60, 50, 40, 32)
    heat, flow, cp, supply, dt = 40000, 5, 4180, 30, 0.25
    model = RCThermalModel(cfg, initial)
    after = model.step(heat, supply, flow, cp, dt)
    capacities = [
        cfg[key] for key in ("c_die_j_k", "c_package_j_k", "c_cold_plate_j_k", "c_coolant_j_k")
    ]
    stored = sum(
        c * (new - old)
        for c, old, new in zip(
            capacities, vars(initial).values(), vars(after).values(), strict=True
        )
    )
    assert stored == pytest.approx(dt * (heat - flow * cp * (32 - supply)))


@pytest.mark.parametrize("delay,expected", [(0, 100), (0.25, 75), (0.5, 50), (1, 0), (1.5, 0)])
def test_fractional_transport_keeps_positive_delay(delay, expected):
    line = TransportDelay(delay, 1, 0)
    assert line.step(100) == pytest.approx(expected)


def test_integer_transport_delivers_after_exact_number_of_steps():
    line = TransportDelay(2, 1, 0)
    assert [line.step(v) for v in (10, 20, 30, 40)] == [0, 0, 10, 20]


@pytest.mark.parametrize(
    "change",
    [
        {"timestamp_s": 1000},
        {"recommended_dp_kpa": float("nan")},
        {"recommended_supply_temp_setpoint_c": float("inf")},
    ],
)
def test_invalid_intents_fall_back(config, change):
    plc = VirtualPLC(config["controls"])
    intent = replace(SupervisoryIntent(0, 100, 25, 0.01, 90, 100), **change)
    output = plc.step(60, 30, 1, 0, intent, True)
    assert output.intent_status == "LOCAL_FALLBACK"
    assert output.accepted_temp_setpoint_c == config["controls"]["supply_temp_setpoint_c"]
    assert output.accepted_dp_kpa == config["controls"]["dp_target_kpa"]


@pytest.mark.parametrize("measurement", [(float("nan"), 30), (60, float("inf"))])
def test_bad_sensor_holds_actuator_and_recovers(config, measurement):
    plc = VirtualPLC(config["controls"])
    output = plc.step(*measurement, 1, 0, None, False)
    assert output.intent_status == "INVALID_MEASUREMENT_HOLD"
    assert output.pump_speed_pct == 60
    assert output.valve_position_pct == 40
    for t in range(1, 20):
        output = plc.step(50, 31, 1, t, None, False)
    assert isfinite(plc.dp_pid.integral) and isfinite(plc.temp_pid.integral)
    assert output.intent_status == "SHADOW"
    assert output.pump_speed_pct != 60
    assert output.valve_position_pct != 40


def test_setpoint_change_does_not_count_as_valve_response():
    case = pd.DataFrame(
        {
            "timestamp_s": [0.0, 1.0, 2.0, 3.0],
            "valve_position_pct": [40.0, 40.0, 40.0, 40.0],
            "temperature_setpoint_c": [30.0, 30.0, 25.0, 25.0],
        }
    )
    assert _first_response_delay(case, 2) is None
    assert _first_response_delay(case, 2, column="temperature_setpoint_c", threshold=0.25) == 0


def test_controlled_comparison_has_identical_pre_step_trajectory(frame):
    pre = frame[frame.timestamp_s < 300].drop(columns=["case"])
    baseline, feedforward = (
        pre.iloc[:300].reset_index(drop=True),
        pre.iloc[300:].reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(baseline, feedforward)


@pytest.mark.parametrize(
    "mutation", ["nan", "infinity", "missing_row", "duplicate_time", "missing_column", "text"]
)
def test_invalid_data_never_passes_threshold_checks(config, frame, mutation):
    broken = frame.copy()
    if mutation in {"nan", "infinity"}:
        broken.loc[400, "gpu_temperature_c"] = float("nan" if mutation == "nan" else "inf")
    elif mutation == "missing_row":
        broken = broken.drop(index=400)
    elif mutation == "duplicate_time":
        broken.loc[400, "timestamp_s"] = 399
    elif mutation == "missing_column":
        broken = broken.drop(columns="gpu_temperature_c")
    else:
        broken["gpu_temperature_c"] = "bad reading"
    summary = benchmark_summary(broken, config)
    assert summary["cases"]["feedback_only"]["threshold_status"] == "INVALID"
    assert summary["comparison"] is None
    json.dumps(summary, allow_nan=False)


def test_one_sample_high_window_is_rejected_before_simulation(config):
    short = deepcopy(config)
    short["workload"]["phases"][2]["start_s"] = 301
    with pytest.raises(ScenarioValidationError, match="sampled points"):
        validate_scenario(short)


def test_zero_pump_energy_has_no_percentage_denominator(config):
    zero = deepcopy(config)
    zero["hydraulics"]["system_k_pa_s2_m6"] = 0
    validate_scenario(zero)
    summary = benchmark_summary(run_benchmark(zero), zero)
    assert summary["comparison"]["pump_energy_change_pct"] is None
    json.dumps(summary, allow_nan=False)


def test_energy_integral_follows_held_engine_commands():
    assert _integrate_kwh(
        pd.Series([1.0, 3.0, 100.0]), pd.Series([0.0, 1.0, 2.0])
    ) == pytest.approx(4 / 3600)
