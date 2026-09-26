"""Pre-registered R41-1..R41-8 mini-suite; offline semantics only."""

import json
from dataclasses import replace
from pathlib import Path

from v0_2.examples.phase5_r5_2_1r1_validation import cases as historical_c_cases
from v0_2.examples.phase5_r5_2_1r_validation import from_calibration, synthetic
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_r5_2_1r4_1_deferred_engine import DeferredDemandTrackingQualifier
from v0_2.examples.phase5_r5_2_2_tracking_calibration import run_open_loop

ROOT = Path(__file__).resolve().parents[3]
PROFILE = json.loads((ROOT / "phase5_r5_2_2_fixture_tracking_profile.json").read_text())
CLASSIFIER = json.loads((ROOT / "phase5_r5_2_silent_tracking_fault_registration.json").read_text())["classifier"]


def _normal(commands, duration_ns):
    return from_calibration(run_open_loop(0.5, tuple(commands.items()), 200_000_000, duration_ns)["rows"])


def _blackout(source, start_ns, end_ns):
    return [replace(item, measured_speed=None, quality="MISSING")
            if start_ns <= item.time_ns < end_ns else item for item in source]


def _cases():
    c11 = historical_c_cases(PROFILE)["C11"]
    tune = json.loads((ROOT / "phase5_r5_3r_a_tune01_released_input_trace.json").read_text())["rows"]
    tune = [ReleasedObservation(**{field: row[field] for field in ReleasedObservation.__dataclass_fields__})
            for row in tune]
    return {
        "R41-1": c11,
        "R41-2": _blackout(_normal({0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7}, 3_000_000_000),
                           400_000_000, 1_200_000_000),
        "R41-3": synthetic(PROFILE, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                      600_000_000: 0.8}, duration_ns=3_000_000_000,
                           initial_speed=0.5, invalid=(400_000_000, 1_200_000_000)),
        "R41-4": synthetic(PROFILE, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                      600_000_000: 0.5}, duration_ns=3_000_000_000,
                           initial_speed=0.5, invalid=(400_000_000, 1_200_000_000)),
        "R41-5": synthetic(PROFILE, {0: 0.5, 200_000_000: 0.7}, duration_ns=3_000_000_000,
                           initial_speed=0.5, invalid=(1_000_000_000, 1_800_000_000)),
        "R41-6": _blackout(_normal({0: 0.5, 200_000_000: 0.7, 800_000_000: 0.85},
                                       4_000_000_000), 1_200_000_000, 2_000_000_000),
        "R41-7": synthetic(PROFILE, {0: 0.5, 200_000_000: 0.7, 600_000_000: 0.3},
                           duration_ns=3_000_000_000, initial_speed=0.5,
                           invalid=(400_000_000, 1_200_000_000)),
        "R41-8": tune,
    }


def _run(source):
    qualifier = DeferredDemandTrackingQualifier(PROFILE, CLASSIFIER)
    for item in source:
        qualifier.update(item)
    return qualifier.snapshot()


def _states(result):
    return [row["state"] for row in result["records"]]


def test_r41_1_c11_stuck_recovery_without_command_event():
    result = _run(_cases()["R41-1"])
    rows = result["records"]
    assert rows[2]["deferred_demand_active"]
    assert rows[2]["first_observable_demand_ns"] == 400_000_000
    recovery = next(row for row in rows if row["time_ns"] == 1_200_000_000)
    assert recovery["recovery_reevaluated"]
    assert recovery["oldest_unresolved_demand_ns"] == 400_000_000
    assert "TRACKING_FAULT_SUSPECTED" in _states(result)
    assert "TRACKING_FAULT_CONFIRMED" in _states(result)


def test_r41_2_normal_movement_credited_at_recovery():
    result = _run(_cases()["R41-2"])
    recovery = next(row for row in result["records"] if row["time_ns"] == 1_200_000_000)
    assert recovery["recovery_reevaluated"]
    assert recovery["qualified_progress"]
    assert recovery["progress_pair_id_before_evaluation"] is not None
    assert "TRACKING_FAULT_CONFIRMED" not in _states(result)


def test_r41_3_growing_demand_keeps_first_time_and_detects_stuck():
    result = _run(_cases()["R41-3"])
    rows = result["records"]
    assert all(row["first_observable_demand_ns"] == 400_000_000
               for row in rows if row["time_ns"] in (400_000_000, 600_000_000, 800_000_000))
    recovery = next(row for row in rows if row["time_ns"] == 1_200_000_000)
    assert recovery["recovery_reevaluated"]
    assert "TRACKING_FAULT_CONFIRMED" in _states(result)


def test_r41_4_canceled_unobserved_demand_does_not_fault():
    result = _run(_cases()["R41-4"])
    assert any(event["event"] == "CANCEL" for event in result["deferred_events"])
    assert "TRACKING_FAULT_CONFIRMED" not in _states(result)


def test_r41_5_prior_valid_suspicion_survives_invalid_interval():
    result = _run(_cases()["R41-5"])
    before = [row for row in result["records"] if row["time_ns"] < 1_000_000_000]
    invalid = [row for row in result["records"] if 1_000_000_000 <= row["time_ns"] < 1_800_000_000]
    assert any(row["state"] == "TRACKING_FAULT_SUSPECTED" for row in before)
    assert all(row["fault_evidence_before_evaluation"] == row["carried_suspicion_evidence"]
               for row in invalid)
    assert any(row["time_ns"] >= 1_800_000_000 and row["state"] == "TRACKING_FAULT_CONFIRMED"
               for row in result["records"])


def test_r41_6_qualified_progress_before_outage_retained():
    result = _run(_cases()["R41-6"])
    before = [row for row in result["records"] if row["time_ns"] < 1_200_000_000]
    assert any(row["qualified_progress"] for row in before)
    credit = max(row["credited_motion"] for row in before)
    assert all(row["credited_motion"] >= credit for row in result["records"]
               if row["time_ns"] >= 1_200_000_000)
    assert "TRACKING_FAULT_CONFIRMED" not in _states(result)


def test_r41_7_reversal_during_outage_is_causal():
    result = _run(_cases()["R41-7"])
    assert any(event["event"] == "REVERSAL" for event in result["deferred_events"])
    assert not any(row["qualified_progress"] for row in result["records"] if not row["valid"])
    recovery = next(row for row in result["records"] if row["time_ns"] == 1_200_000_000)
    assert recovery["recovery_reevaluated"]
    assert recovery["oldest_unresolved_demand_ns"] == 200_000_000
    assert any(event["event"] == "START" and event["expected_direction"] == -1
               for event in result["epoch_events"] if event["time_ns"] >= 1_200_000_000)
    assert "TRACKING_FAULT_SUSPECTED" in _states(result)
    assert "TRACKING_FAULT_CONFIRMED" in _states(result)


def test_r41_8_tune01_paired_reference_fix_remains():
    result = _run(_cases()["R41-8"])
    assert "TRACKING_FAULT_CONFIRMED" not in _states(result)
