from copy import deepcopy

import pytest

from c2c.controls.supervisory import SupervisoryIntent
from c2c.controls.virtual_plc import VirtualPLC
from c2c.reports.metrics import benchmark_summary
from c2c.simulation.engine import run_benchmark
from c2c.simulation.scenario import load_scenario
from c2c.simulation.validation import ScenarioValidationError, validate_scenario


@pytest.mark.parametrize("dt", [1, 0.5, 0.25])
def test_slew_limits_target_and_fallback_in_physical_time(dt):
    _, cfg = load_scenario("configs/scenarios/workload_step.yaml")
    plc = VirtualPLC(cfg["controls"])
    intent = SupervisoryIntent(0, 100, 25, 0.01, 90, 100)
    output = plc.step(60, 30, 0, 0, intent, True)
    assert output.actual_temp_setpoint_c == 30
    for i in range(int(10 / dt)):
        output = plc.step(60, 30, dt, (i + 1) * dt, intent, True)
    assert output.accepted_temp_setpoint_c == 25
    assert output.actual_temp_setpoint_c == pytest.approx(29)
    held = plc.step(60, float("nan"), dt, 10 + dt, intent, True)
    assert held.actual_temp_setpoint_c == output.actual_temp_setpoint_c
    fallback = plc.step(60, 30, dt, 20, intent, True)
    assert fallback.intent_status == "LOCAL_FALLBACK"
    assert fallback.accepted_temp_setpoint_c == 30
    assert fallback.actual_temp_setpoint_c == pytest.approx(29 + 0.1 * dt)


@pytest.mark.parametrize("rate", [0, -1, float("nan"), float("inf")])
def test_invalid_ramp_is_rejected(rate):
    _, cfg = load_scenario("configs/scenarios/workload_step.yaml")
    cfg["controls"]["temp_setpoint_ramp_k_s"] = rate
    with pytest.raises(ScenarioValidationError, match="temp_setpoint_ramp"):
        validate_scenario(cfg)
    with pytest.raises(ValueError, match="temp_setpoint_ramp"):
        VirtualPLC(cfg["controls"])


def test_ramp_improves_tracking_without_hiding_final_target_error():
    _, cfg = load_scenario("configs/scenarios/workload_step.yaml")
    outputs = []
    for dt in [1, 0.5, 0.25, 0.125]:
        c = deepcopy(cfg)
        c["time"]["dt_s"] = dt
        result = benchmark_summary(run_benchmark(c), c)["cases"]["guarded_feedforward"]
        assert result["threshold_status"] == "PASS"
        assert result["post_step_supply_deviation_k"] < 2
        assert result["max_accepted_target_deviation_k"] > 3
        assert result["peak_gpu_temperature_c"] < 79
        outputs.append(result)
    assert (
        abs(
            outputs[-1]["post_step_supply_deviation_k"]
            - outputs[-2]["post_step_supply_deviation_k"]
        )
        < 0.01
    )
    assert abs(outputs[-1]["peak_gpu_temperature_c"] - outputs[-2]["peak_gpu_temperature_c"]) < 0.01
    immediate = deepcopy(cfg)
    immediate["controls"]["temp_setpoint_ramp_k_s"] = 100
    old = benchmark_summary(run_benchmark(immediate), immediate)["cases"]["guarded_feedforward"]
    assert old["threshold_status"] == "FAIL"
    assert outputs[0]["pump_energy_kwh"] == pytest.approx(old["pump_energy_kwh"])
    assert outputs[0]["facility_cooling_energy_kwh"] / old["facility_cooling_energy_kwh"] < 1.01
