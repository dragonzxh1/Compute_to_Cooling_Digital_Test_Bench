from copy import deepcopy
from pathlib import Path

import pytest

from c2c.core.time import SimulationClock
from c2c.simulation.scenario import load_scenario
from c2c.simulation.validation import ScenarioValidationError, validate_scenario
from c2c.thermal.transport import TransportDelay

CONFIG = Path("configs/scenarios/workload_step.yaml")


def test_clock_never_steps_past_duration():
    timestamps = [timestamp for _, timestamp in SimulationClock(0.6, 1.0).steps()]
    assert timestamps == [0.0, 0.6]


def test_clock_rejects_non_positive_timestep():
    with pytest.raises(ValueError, match="greater than zero"):
        list(SimulationClock(0, 10).steps())


def test_zero_transport_delay_returns_current_value():
    delay = TransportDelay(0, 1, 30)
    assert delay.step(42) == 42


def test_scenario_rejects_utilization_above_100_percent():
    _, config = load_scenario(CONFIG)
    invalid = deepcopy(config)
    invalid["workload"]["phases"][1]["utilization_pct"] = 101
    with pytest.raises(ScenarioValidationError, match="between 0 and 100"):
        validate_scenario(invalid)


def test_scenario_rejects_local_setpoint_outside_plc_guardrail():
    _, config = load_scenario(CONFIG)
    invalid = deepcopy(config)
    invalid["controls"]["supply_temp_setpoint_c"] = 40
    with pytest.raises(ScenarioValidationError, match="must be between"):
        validate_scenario(invalid)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("time", "duration_s"), 0, "greater than zero"),
        (("compute", "gpu_count"), 0.5, "must be an integer"),
        (("compute", "gpu_power_limit_w"), 100, "must be between"),
        (("lci", "target_delta_t_k"), 0, "greater than zero"),
        (("lci", "update_interval_s"), -1, "greater than zero"),
        (("controls", "temp_pid", "kp"), -1, "non-negative"),
    ],
)
def test_scenario_rejects_invalid_physical_parameters(path, value, message):
    _, config = load_scenario(CONFIG)
    invalid = deepcopy(config)
    target = invalid
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ScenarioValidationError, match=message):
        validate_scenario(invalid)


def test_scenario_rejects_non_numeric_phase_values_consistently():
    _, config = load_scenario(CONFIG)
    invalid = deepcopy(config)
    invalid["workload"]["phases"][1]["start_s"] = None
    with pytest.raises(ScenarioValidationError, match="finite numbers"):
        validate_scenario(invalid)


def test_scenario_rejects_too_few_benchmark_phases():
    _, config = load_scenario(CONFIG)
    invalid = deepcopy(config)
    invalid["workload"]["phases"] = invalid["workload"]["phases"][:1]
    with pytest.raises(ScenarioValidationError, match="at least two"):
        validate_scenario(invalid)
