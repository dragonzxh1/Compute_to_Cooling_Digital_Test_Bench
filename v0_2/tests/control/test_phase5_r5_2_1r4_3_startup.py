"""Startup acceptance uses frozen historical sources and thresholds."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import build_cases, synthetic
from v0_2.tests.control import test_phase5_r5_2_1r4_1_deferred_demand as r41
from v0_2.tests.control import test_phase5_r5_2_1r4_2_directional_obligation as r42

ROOT = Path(__file__).resolve().parents[3]


def sources():
    def load(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    return build_cases(r41.PROFILE, load("phase5_r5_2_silent_tracking_fault_evidence.json"),
                       load("phase5_r5_2_2_tracking_calibration_evidence.json"))


def run(source):
    q = StartupTrackingQualifier(r41.PROFILE, r41.CLASSIFIER)
    for item in source:
        q.update(item)
    return q.snapshot()


@pytest.mark.parametrize("name", ["S2", "S4", "S6", "S8_stuck", "S12", "S15", "S16", "S16_variant"])
def test_previously_missed_startup_faults(name):
    result = run(sources()[name])
    assert result["confirmed_latched"]


@pytest.mark.parametrize("name", ["S1", "S3", "S8_normal", "S9_up_down", "S9_down_up", "S10", "S14"])
def test_healthy_and_tolerated_startup_cases(name):
    assert not run(sources()[name])["confirmed_latched"]


def test_stuck_startup_never_fabricates_resolved_pair():
    result = run(sources()["S6"])
    assert result["resolved_pair"] is None
    assert not result["resolved_pair_events"]
    assert result["records"][0]["startup_observation"]["command"] == 0.7
    assert result["records"][0]["startup_observation"]["measured_speed"] == 0.5
    assert all(not row["baseline_resolved"] for row in result["records"])


@pytest.mark.parametrize("name", ["S5", "S13"])
def test_progress_does_not_immunize_later_stall(name):
    result = run(sources()[name])
    assert any(row["qualified_progress"] for row in result["records"])
    assert result["confirmed_latched"]


def test_startup_and_checkpoint_prefix_causality():
    source = sources()["S8_normal"]
    result = run(source)
    for stop in range(1, len(source) + 1):
        assert run(source[:stop])["records"] == result["records"][:stop]
    assert run(source) == result


@pytest.mark.parametrize("name", sorted(name for name in vars(r41) if name.startswith("test_r41_")))
def test_recovery_regression(name, monkeypatch):
    monkeypatch.setattr(r41, "DeferredDemandTrackingQualifier", StartupTrackingQualifier)
    getattr(r41, name)()


@pytest.mark.parametrize("name", [
    "test_watch_and_pair_survive_direction_change",
    "test_negative_derivative_without_net_reversal_keeps_direction",
    "test_multiple_reversals_preserve_watch",
    "test_deferred_only_demand_reverses_before_any_epoch",
    "test_prior_suspicion_survives_reversal",
    "test_nonzero_suspicion_count_survives_reversal",
    "test_repeatability_and_prefix_causality",
])
def test_directional_candidate_controls(name, monkeypatch):
    monkeypatch.setattr(r42, "DirectionalObligationTrackingQualifier", StartupTrackingQualifier)
    getattr(r42, name)()


@pytest.mark.parametrize("reversal_ns", [600_000_000, 1_000_000_000])
def test_directional_healthy_controls(reversal_ns, monkeypatch):
    monkeypatch.setattr(r42, "DirectionalObligationTrackingQualifier", StartupTrackingQualifier)
    r42.test_healthy_outage_reversal_not_confirmed(reversal_ns)


def test_initial_sensor_loss_does_not_infer_unseen_motion():
    source = synthetic(r41.PROFILE, {0: 0.7}, duration_ns=4_000_000_000,
                       initial_speed=0.5, invalid=(0, 1_200_000_000))
    result = run(source)
    assert all(row["state"] == "INSUFFICIENT_MEASUREMENT" for row in result["records"][:6])
    first = result["records"][6]
    assert first["expected_motion"] == 0
    assert first["carried_suspicion_evidence"] == 0
    assert result["confirmed_latched"]


def test_startup_outage_reversal_preserves_observation_pair():
    source = synthetic(r41.PROFILE, {0: 0.7, 600_000_000: 0.3},
                       duration_ns=3_000_000_000, initial_speed=0.5,
                       invalid=(200_000_000, 1_200_000_000))
    result = run(source)
    before = result["records"][0]
    recovery = result["records"][6]
    assert recovery["progress_pair_id_before_evaluation"] == before["progress_pair_id"]
    assert recovery["oldest_unresolved_demand_ns"] == 0
    assert result["confirmed_latched"]


def test_unproven_startup_demand_cancellation_and_reintroduction():
    source = synthetic(r41.PROFILE, {0: 0.7, 200_000_000: 0.5, 1_400_000_000: 0.7},
                       duration_ns=3_000_000_000, initial_speed=0.5)
    result = run(source)
    at = {row["time_ns"]: row for row in result["records"]}
    assert at[200_000_000]["state"] == "STEADY_TRACKING"
    assert not any(row["state"] == "TRACKING_FAULT_CONFIRMED"
                   for row in result["records"] if row["time_ns"] < 1_400_000_000)
    starts = [event for event in result["watch_events"] if event["event"] == "START"]
    assert [event["watch_start_ns"] for event in starts] == [0, 1_400_000_000]
    assert any(event["event"] == "CANCEL" for event in result["watch_events"])
    assert at[1_400_000_000]["carried_suspicion_evidence"] == 0
    assert result["confirmed_latched"]


@pytest.mark.parametrize("name", ["S3", "S14"])
def test_startup_cancellation_does_not_erase_real_measured_progress(name):
    result = run(sources()[name])
    assert any(row["qualified_progress"] for row in result["records"])
    assert not any(event["event"] == "CANCEL" for event in result["watch_events"])
    assert not result["confirmed_latched"]


def test_startup_demand_with_suspicion_suspends_then_reintroduces():
    source = synthetic(r41.PROFILE, {0: 0.7, 1_400_000_000: 0.5,
                                    2_600_000_000: 0.7},
                       duration_ns=4_000_000_000, initial_speed=0.5)
    result = run(source)
    at = {row["time_ns"]: row for row in result["records"]}
    assert at[1_200_000_000]["carried_suspicion_evidence"] == 1
    assert at[1_400_000_000]["startup_demand_suspended"]
    assert all(not row["confirmed_latched"] for row in result["records"]
               if 1_400_000_000 <= row["time_ns"] <= 2_600_000_000)
    assert at[2_600_000_000]["carried_suspicion_evidence"] == 1
    assert at[2_600_000_000]["oldest_unresolved_demand_ns"] == 0
    assert at[2_600_000_000]["expected_motion"] == 0
    assert len([event for event in result["watch_events"] if event["event"] == "START"]) == 1
    assert result["confirmed_latched"]


@pytest.mark.parametrize("name", ["S3", "S14"])
def test_same_sample_resolution_publishes_real_progress_first(name):
    result = run(sources()[name])
    at = {row["time_ns"]: row for row in result["records"]}
    progress = at[1_000_000_000]
    assert progress["qualified_progress"]
    assert progress["state"] == "TRACKING_PROGRESS"
    assert progress["resolved_anchor_pair_id"] is not None
    assert progress["watch_id"] is None
    assert any(event["time_ns"] == 1_000_000_000 and event["event"] == "RESOLVE"
               for event in result["watch_events"])
    assert at[1_200_000_000]["state"] == "STEADY_TRACKING"


def test_same_sample_resolution_followed_by_command_withdrawal_is_reevaluated():
    source = sources()["S3"][:7]
    source[-1] = replace(source[-1], plc_command=0.5, command_timestamp_ns=1_200_000_000)
    result = run(source)
    assert result["records"][-2]["state"] == "TRACKING_PROGRESS"
    assert result["records"][-1]["state"] != "STEADY_TRACKING"
    assert not result["confirmed_latched"]
    assert result["resolved_pair_events"][-1]["time_ns"] == 1_000_000_000


def test_same_sample_resolution_followed_by_invalid_measurement_is_reevaluated():
    source = sources()["S3"][:7]
    source[-1] = replace(source[-1], measured_speed=None, quality="MISSING")
    result = run(source)
    assert result["records"][-2]["state"] == "TRACKING_PROGRESS"
    assert result["records"][-1]["state"] == "INSUFFICIENT_MEASUREMENT"
    assert result["resolved_pair_events"][-1]["time_ns"] == 1_000_000_000


@pytest.mark.parametrize("changes", [
    {"sample_ns": 200_000_000, "release_ns": 0},
    {"sample_ns": 0, "release_ns": -1},
    {"measured_speed": float("nan")},
    {"measured_speed": float("inf")},
])
def test_invalid_observations_cannot_establish_startup_baseline(changes):
    first = synthetic(r41.PROFILE, {0: 0.7}, duration_ns=0, initial_speed=0.5)[0]
    result = run([replace(first, **changes)])
    assert result["state"] == "INSUFFICIENT_MEASUREMENT"
    assert not result["records"][0]["startup_observation"]
    assert not result["resolved_pair"]
