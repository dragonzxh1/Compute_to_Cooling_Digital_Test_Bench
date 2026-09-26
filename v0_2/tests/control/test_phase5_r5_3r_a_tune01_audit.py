"""Forensic checks for the frozen TUNE-01 false-positive root-cause audit."""

from v0_2.examples.phase5_r5_3r_a_tune01_audit import (
    CLASSIFIER,
    EVIDENCE,
    PROFILE,
    REG,
    TRACE,
    domain,
    extract,
    integrity,
    load,
    replay,
    replay_port,
    sha,
)


def test_preregistration_source_and_revert_integrity():
    reg = load(REG)
    evidence = load(EVIDENCE)
    assert evidence["registration_sha256"] == sha(REG)
    assert REG.stat().st_mtime_ns <= TRACE.stat().st_mtime_ns
    assert all(integrity(reg).values())
    assert evidence["root_cause_class"] == "FROZEN_SEMANTICS_FALSE_POSITIVE_ON_VALID_IN_DOMAIN_TRACE"


def test_trace_is_reconstructed_causal_prefix_not_raw_truth():
    trace = load(TRACE)
    regenerated, run = extract()
    assert regenerated == trace
    assert trace["provenance"] == "UNCHANGED_BASELINE_RECONSTRUCTION_NOT_ORIGINAL_FAILED_TRIAL_CAPTURE"
    assert trace["no_raw_actual_or_true_plant_fields"]
    assert all("actual" not in row and "fault_id" not in row for row in trace["rows"])
    assert all(row["release_ns"] is None or row["release_ns"] <= row["time_ns"] for row in trace["rows"])
    assert domain(trace, run, load(PROFILE))["required_explicit_bounds_pass"]
    assert sha(TRACE) == load(EVIDENCE)["trace_sha256"]


def test_offline_and_functional_port_reconstruction_same_prefix():
    trace = load(TRACE)
    profile = load(PROFILE)
    classifier = load(CLASSIFIER)["classifier"]
    offline, _ = replay(trace["rows"], profile, classifier)
    production, _ = replay_port(trace["rows"], profile, classifier)
    assert offline == production
    assert next(row["time_ns"] for row in offline if row["state"] == "TRACKING_FAULT_SUSPECTED") == 29_600_000_000
    assert next(row["time_ns"] for row in offline if row["state"] == "TRACKING_FAULT_CONFIRMED") == 31_000_000_000
    assert load(EVIDENCE)["first_divergence"] is None


def test_stale_command_anchor_versus_current_measurement_anchor():
    points = load(EVIDENCE)["critical_progress"]
    suspected = points["29600000000"]
    confirmed = points["31000000000"]
    assert suspected["qualified_command_anchor"] == 0.7
    assert suspected["epoch_anchor_measured_speed"] > 0.84
    assert suspected["epoch_expected_displacement"] > suspected["epoch_measured_directed_progress"]
    assert suspected["command_measured_gap"] < 0.01
    assert confirmed["epoch_measured_directed_progress"] > 0.01
    assert confirmed["epoch_progress_ratio"] < 0.35
    assert confirmed["state"] == "TRACKING_FAULT_CONFIRMED"


def test_repeatability_causality_and_no_production_fix():
    evidence = load(EVIDENCE)
    assert evidence["repeatability"]["replays"] >= 10
    assert evidence["repeatability"]["identical"]
    assert evidence["prefix_causality"]["all_equal"]
    assert evidence["tick_mismatch_count"] == 0
    assert evidence["status"] == "TUNE01_FALSE_POSITIVE_ROOT_CAUSE_IDENTIFIED"
    assert not evidence["trace_full_failed_run_capture"]
