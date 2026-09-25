"""Phase 5R4.1 preregistration, evidence, and stop-condition checks."""

import json

import pytest
from v0_2.examples import phase5_r4_1_local_pi_refinement as refinement


@pytest.fixture(scope="module")
def registration():
    return json.loads(refinement.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(refinement.EVIDENCE.read_text(encoding="utf-8"))


def test_preregistration_and_frozen_source_hashes(registration, evidence):
    assert refinement._sha(refinement.REGISTRATION) == refinement.EXPECTED_REGISTRATION_SHA256
    assert evidence["registration_sha256"] == refinement.EXPECTED_REGISTRATION_SHA256
    assert refinement._integrity(registration)["status"] == "PASS"
    assert evidence["integrity"]["status"] == "PASS"
    assert all(evidence["integrity"]["checks"].values())


def test_exact_local_grid_and_frozen_exam(registration):
    assert registration["target_k"] == 313.71072595542387
    assert registration["inner"] == {"id": "inner_b", "kp": 1.5e-5, "ki": 4e-6, "kd": 0.0}
    assert registration["outer_candidates"] == refinement._expected_grid()
    assert len(registration["outer_candidates"]) == 30
    assert {item["kp"] for item in registration["outer_candidates"]} == {2500, 3000, 3500, 4000, 4500, 5000}
    assert {item["ki"] for item in registration["outer_candidates"]} == {100, 105, 110, 115, 120}
    assert all(item["kd"] == 0 for item in registration["outer_candidates"])
    assert registration["qualification_duration_ns"] == 180_000_000_000
    assert registration["settling"]["band_k"] == 0.5
    assert registration["settling"]["continuous_dwell_ns"] == 15_000_000_000


def test_sixty_valid_registered_stage_a_runs_and_historical_preparation(registration, evidence):
    stage = evidence["stage_a"]
    assert stage["expected_runs"] == stage["completed_runs"] == 60
    assert stage["invalid_runs"] == evidence["invalid_run_count"] == 0
    assert {
        (record["candidate_id"], record["case"], record["physics_dt_ns"])
        for record in stage["run_matrix"]
    } == {
        (candidate["id"], case, 200_000_000)
        for candidate in registration["outer_candidates"]
        for case in ("WARM_CAPTURE", "COLD_CAPTURE")
    }
    historical = json.loads(refinement.r4.SOURCE_5_1R2_RESULT.read_text(encoding="utf-8"))
    for case in registration["training_cases"]:
        assert evidence["preparation"][case]["reproduction_status"] == "PASS"
        assert evidence["preparation"][case]["normalized_initial_state_sha256"] == historical["preparation"][case]["normalized_initial_state_sha256"]


def test_oscillation_rejection_is_explicit_and_monotonic_is_not_mislabeled():
    monotonic = [
        {"time_s": float(i), "measured_device_k": 315.0 - 1.0 * i / 180, "pump_actual": 0.6}
        for i in range(181)
    ]
    assert refinement._oscillation(monotonic, 313.71072595542387, 0.5, 0.3, 0.9, 1e-6)["status"] == "PASS"
    settles_then_exits = [
        {"time_s": float(i), "measured_device_k": 313.7 if 30 <= i < 100 else 314.5, "pump_actual": 0.6}
        for i in range(181)
    ]
    assert "SETTLE_THEN_EXIT" in refinement._oscillation(settles_then_exits, 313.71072595542387, 0.5, 0.3, 0.9, 1e-6)["reasons"]


def test_feasibility_map_is_complete_and_shows_no_overlap(evidence):
    decisions = evidence["stage_a"]["candidate_decisions"]
    assert len(decisions) == 30
    assert evidence["stage_a"]["thermally_feasible_count"] == 0
    assert evidence["stage_a"]["feasible_ranking"] == []
    assert {status: sum(item["map_status"] == status for item in decisions) for status in ("BOTH_PASS", "WARM_ONLY", "COLD_ONLY", "NEITHER")} == {
        "BOTH_PASS": 0, "WARM_ONLY": 18, "COLD_ONLY": 4, "NEITHER": 8
    }
    for item in decisions:
        assert evidence["feasibility_map"][str(int(item["kp"]))][str(int(item["ki"]))] == item["map_status"]
        assert item["status"] == "BIDIRECTIONAL_THERMAL_FAIL"


def test_common_startup_is_separate_and_safety_unchanged(registration, evidence):
    assert registration["safety_startup_handling"]["policy_unchanged"] is True
    assert evidence["startup_safety"]["candidate_independent"] is True
    assert evidence["startup_safety"]["cold_degraded_duration_s"] == 0.4
    assert evidence["startup_safety"]["full_feedback_qualification_pending"] is True
    assert all(
        "DEGRADED" in record["metrics"]["safety_states"]
        for record in evidence["stage_a"]["run_matrix"]
        if record["case"] == "COLD_CAPTURE"
    )


def test_ownership_conservation_information_boundary_and_stop(evidence):
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["conservation"]["status"] == "PASS"
    assert all(
        record["metrics"]["ownership_lineage_pass"] and record["metrics"]["conservation_pass"]
        for record in evidence["stage_a"]["run_matrix"]
    )
    assert evidence["holdout_used_for_tuning"] is False
    assert evidence["training_cases_not_independent_validation"] is True
    assert evidence["phase6_authorized"] is False
    assert evidence["status"] == "NO_LOCAL_PI_OVERLAP_REGION_FOUND"
    assert evidence["stage_b"]["status"] == "NOT_EXECUTED_NO_STAGE_A_FEASIBLE_CANDIDATE"
    assert evidence["stage_b"]["completed_runs"] == 0
    assert evidence["stage_b"]["finalist_ids"] == []
    assert evidence["selection"]["candidate_id"] is None
    assert evidence["repeatability"]["status"] == "NOT_EXECUTED"
    assert not refinement.CANDIDATE_BASELINE.exists()
    assert not refinement.FIGURE.exists()
