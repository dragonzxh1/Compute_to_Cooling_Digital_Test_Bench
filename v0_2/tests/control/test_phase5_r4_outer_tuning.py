"""Frozen-grid and stop-condition regression checks for Phase 5R4."""

import json

import pytest
from v0_2.examples import phase5_r4_outer_tuning as tuning


@pytest.fixture(scope="module")
def registration():
    return json.loads(tuning.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(tuning.EVIDENCE.read_text(encoding="utf-8"))


def test_preregistration_and_frozen_source_integrity(registration, evidence):
    assert tuning._sha(tuning.REGISTRATION) == tuning.EXPECTED_REGISTRATION_SHA256
    assert evidence["registration_sha256"] == tuning.EXPECTED_REGISTRATION_SHA256
    assert tuning._integrity(registration)["status"] == "PASS"
    assert evidence["integrity"]["status"] == "PASS"
    assert all(evidence["integrity"]["checks"].values())
    assert registration["outer_candidates"] == tuning._expected_grid()
    assert len(registration["outer_candidates"]) == 16
    assert registration["inner"]["id"] == "inner_b"


def test_exact_stage_a_matrix_and_historical_initial_states(registration, evidence):
    stage = evidence["stage_a"]
    assert stage["expected_runs"] == stage["completed_runs"] == 32
    assert stage["invalid_runs"] == evidence["invalid_run_count"] == 0
    assert {
        (run["candidate_id"], run["case"], run["physics_dt_ns"])
        for run in stage["run_matrix"]
    } == {
        (candidate["id"], case, 200_000_000)
        for candidate in registration["outer_candidates"]
        for case in ("WARM_CAPTURE", "COLD_CAPTURE")
    }
    historical = json.loads(tuning.SOURCE_5_1R2_RESULT.read_text(encoding="utf-8"))
    for case in ("WARM_CAPTURE", "COLD_CAPTURE"):
        assert evidence["preparation"][case]["reproduction_status"] == "PASS"
        assert evidence["preparation"][case]["normalized_initial_state_sha256"] == (
            historical["preparation"][case]["normalized_initial_state_sha256"]
        )


def test_no_candidate_satisfies_both_directions(evidence):
    decisions = evidence["stage_a"]["candidate_decisions"]
    assert len(decisions) == 16
    assert evidence["stage_a"]["thermally_feasible_count"] == 0
    assert evidence["stage_a"]["feasible_ranking"] == []
    assert all(item["status"] == "BIDIRECTIONAL_THERMAL_FAIL" for item in decisions)
    assert all(any(item["failure_reasons_by_case"].values()) for item in decisions)
    cold_success = [
        item for item in decisions
        if not item["failure_reasons_by_case"]["COLD_CAPTURE"]
    ]
    assert [item["candidate_id"] for item in cold_success] == ["R4-KP3000-KI120"]
    assert cold_success[0]["failure_reasons_by_case"]["WARM_CAPTURE"] == [
        "NO_SETTLING", "FINAL_WINDOW_TEMPERATURE"
    ]


def test_common_startup_is_separate_from_thermal_failure(evidence):
    assert evidence["startup_safety"]["candidate_independent"] is True
    assert evidence["startup_safety"]["cold_degraded_duration_s"] == 0.4
    assert evidence["startup_safety"]["full_feedback_qualification_pending"] is True
    cold = [
        run for run in evidence["stage_a"]["run_matrix"]
        if run["case"] == "COLD_CAPTURE"
    ]
    assert len(cold) == 16
    assert all("DEGRADED" in run["metrics"]["safety_states"] for run in cold)
    assert all("NONCOMMON_DEGRADED" not in tuning._hard_run_reasons(run, True) for run in cold)
    assert all("NONCOMMON_DEGRADED" in tuning._hard_run_reasons(run, False) for run in cold)


def test_ownership_conservation_and_information_boundary(evidence):
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["conservation"]["status"] == "PASS"
    assert all(
        run["metrics"]["ownership_lineage_pass"]
        and run["metrics"]["conservation_pass"]
        for run in evidence["stage_a"]["run_matrix"]
    )
    assert evidence["holdout_used_for_tuning"] is False
    assert evidence["training_cases_not_independent_validation"] is True
    assert evidence["phase6_authorized"] is False


def test_zero_feasible_stop_prevents_later_stages(evidence):
    assert evidence["status"] == "NO_R4_GRID_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION"
    assert evidence["stage_b"]["status"] == "NOT_EXECUTED_NO_STAGE_A_FEASIBLE_CANDIDATE"
    assert evidence["stage_b"]["completed_runs"] == 0
    assert evidence["stage_b"]["finalist_ids"] == []
    assert evidence["numerical_uncertainty"]["pairwise_comparisons"] == []
    assert evidence["selection"]["candidate_id"] is None
    assert evidence["repeatability"]["status"] == "NOT_EXECUTED"
    assert evidence["figure_traces"] == {}
    assert not tuning.CANDIDATE_BASELINE.exists()
