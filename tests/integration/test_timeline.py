import json

import numpy as np
import pytest

from c2c.reports.metrics import benchmark_summary
from c2c.reports.timeline import response_events
from c2c.simulation.engine import run_benchmark
from c2c.simulation.scenario import load_scenario


@pytest.fixture(scope="module")
def benchmark():
    _, config = load_scenario("configs/scenarios/workload_step.yaml")
    return config, run_benchmark(config)


def test_timeline_uses_actual_pre_command_inputs(benchmark):
    config, frame = benchmark
    for _, case in frame.groupby("case"):
        np.testing.assert_allclose(
            case.plc_measured_supply_temp_c.iloc[1:],
            case.secondary_supply_temp_c.iloc[:-1],
        )
        np.testing.assert_allclose(
            case.plc_measured_dp_kpa.iloc[1:], case.secondary_dp_kpa.iloc[:-1]
        )
    events = response_events(frame, config)
    summary = benchmark_summary(frame, config)
    for name, case_events in events["cases"].items():
        assert case_events["valve"] == summary["cases"][name]["controller_response_delay_s"]
    assert events["cases"]["guarded_feedforward"]["pump"] == 0
    assert events["cases"]["guarded_feedforward"]["pressure"] == 1
    assert events["cases"]["feedback_only"]["pressure"] is None
    json.dumps(events, allow_nan=False)


def test_no_crossing_is_not_reported_as_zero_or_recovery_event(benchmark):
    config, frame = benchmark
    changed = frame.copy()
    changed["valve_position_pct"] = 40.0
    changed.loc[changed.timestamp_s >= 750, "valve_position_pct"] = 80.0
    events = response_events(changed, config)
    assert all(case["valve"] is None for case in events["cases"].values())


def test_timeline_does_not_invent_intent_update_at_non_aligned_step():
    _, config = load_scenario("configs/scenarios/workload_step.yaml")
    config["workload"]["phases"][1]["start_s"] = 302
    events = response_events(run_benchmark(config), config)
    assert events["step_s"] == 302
    assert events["cases"]["guarded_feedforward"]["intent"] == 3
