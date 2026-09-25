import json

import pytest
from v0_2.examples import phase5_r3_bidirectional_selection as selection


@pytest.fixture(scope="module")
def registration():
    return json.loads(selection.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(selection.EVIDENCE.read_text(encoding="utf-8"))


def test_registration_was_frozen_before_execution(registration, evidence):
    assert selection._sha(selection.REGISTRATION) == selection.EXPECTED_REGISTRATION_SHA
    assert evidence["registration_sha256"] == selection.EXPECTED_REGISTRATION_SHA
    assert evidence["integrity"]["status"] == "PASS"
    assert all(evidence["integrity"]["checks"].values())


def test_target_inner_and_candidate_grid_are_frozen(registration):
    assert registration["target_k"] == 313.71072595542387
    assert registration["inner"] == {
        "id": "inner_b",
        "kp": 1.5e-5,
        "ki": 4e-6,
        "kd": 0.0,
    }
    assert registration["outer_candidates"] == [
        {"id": "outer_a", "kp": 1000.0, "ki": 20.0, "kd": 0.0},
        {"id": "outer_b", "kp": 2000.0, "ki": 40.0, "kd": 0.0},
        {"id": "outer_c", "kp": 3000.0, "ki": 60.0, "kd": 0.0},
    ]
    assert registration["new_gains_allowed"] is False


def test_exactly_eighteen_registered_runs_used_unchanged_exam(registration, evidence):
    assert registration["preparation"]["duration_ns"] == 180_000_000_000
    assert registration["qualification_duration_ns"] == 180_000_000_000
    assert registration["preparation"]["warm_speed_fraction"] == 0.3
    assert registration["preparation"]["cold_speed_fraction"] == 0.9
    assert evidence["run_matrix_summary"] == {
        "expected_runs": 18,
        "completed_runs": 18,
        "invalid_runs": 0,
    }
    assert len(evidence["run_matrix"]) == 18
    assert evidence["preparation_state_hashes_match_phase5_1r2"] is True
    assert {
        (item["candidate_id"], item["case"], item["physics_dt_ns"])
        for item in evidence["run_matrix"]
    } == {
        (candidate, case, dt)
        for candidate in ("outer_a", "outer_b", "outer_c")
        for case in ("WARM_CAPTURE", "COLD_CAPTURE")
        for dt in (200_000_000, 100_000_000, 50_000_000)
    }


def test_bidirectional_feasibility_is_first_and_holdout_is_excluded(
    registration, evidence
):
    assert registration["selection_hierarchy"][0] == "bidirectional_feasibility"
    assert registration["holdout_selection_allowed"] is False
    assert evidence["holdout_used_in_selection"] is False
    assert evidence["historical_holdout_executed"] is False
    assert all(
        item["status"] == "BIDIRECTIONAL_FEASIBILITY_FAIL"
        for item in evidence["candidate_decisions"]
    )
    assert evidence["selection"]["candidate_id"] is None


def test_numerical_uncertainty_veto_calculations_are_exact(evidence):
    by_id = {
        item["candidate_id"]: item["aggregates_by_dt_ns"]
        for item in evidence["candidate_decisions"]
    }
    for comparison in evidence["numerical_uncertainty"]:
        left, right = comparison["pair"].split("_vs_")
        a, b = by_id[left], by_id[right]
        expected_difference = abs(
            a["200000000"]["temperature_iae_k_s"]
            - b["200000000"]["temperature_iae_k_s"]
        )
        expected_bound = abs(
            a["100000000"]["temperature_iae_k_s"]
            - a["50000000"]["temperature_iae_k_s"]
        ) + abs(
            b["100000000"]["temperature_iae_k_s"]
            - b["50000000"]["temperature_iae_k_s"]
        )
        assert comparison["canonical_iae_difference_k_s"] == pytest.approx(
            expected_difference
        )
        assert comparison["numerical_uncertainty_bound_k_s"] == pytest.approx(
            expected_bound
        )
        assert comparison["thermal_iae_result"] == (
            "NUMERICALLY_INDISTINGUISHABLE"
            if expected_difference <= expected_bound
            else "NUMERICALLY_DISTINGUISHABLE"
        )


def test_safety_acceptance_is_not_relaxed(registration, evidence):
    policy = registration["safety_acceptance"]
    assert policy["startup_state_allowed"] == "FF_DISABLED"
    assert policy["qualified_states"] == ["NORMAL"]
    assert policy["restrictive_degraded_allowed"] is False
    assert "ACTUATOR_TRACKING_PENDING" in policy["forbidden_reasons"]
    assert evidence["safety"]["rule_unchanged_from_phase5_1r2"] is True
    assert evidence["safety"]["common_startup_safety_acceptance_blocker"] is False


def test_common_startup_blocker_requires_thermal_pass_only():
    candidate = {"id": "outer_a"}
    metric = {
        "settling_pass": True,
        "final_window_pass": True,
        "final_saturation_pass": True,
        "conservation_pass": True,
        "control_direction_pass": True,
        "ownership_lineage_pass": True,
        "safety_pass": True,
        "temperature_iae_k_s": 1.0,
        "control_total_variation": 0.1,
        "pump_electrical_j": 2.0,
    }
    records = [
        {
            "candidate_id": "outer_a",
            "case": case,
            "physics_dt_ns": dt,
            "metrics": {**metric, "safety_pass": case == "WARM_CAPTURE"},
        }
        for dt in (200_000_000, 100_000_000, 50_000_000)
        for case in ("WARM_CAPTURE", "COLD_CAPTURE")
    ]

    decision = selection._candidate_decision(candidate, records)

    assert decision["failure_reasons"] == ["SAFETY"]
    assert decision["safety_only_failure"] is True


def test_ownership_conservation_and_information_boundaries_pass(evidence):
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["ownership_all_runs_pass"] is True
    assert evidence["conservation"]["status"] == "PASS"
    assert evidence["no_truth_or_future_access"] is True
    assert evidence["new_gains_created"] is False
    assert evidence["r2_baseline_overwritten"] is False
    assert evidence["phase6_authorized"] is False


def test_no_candidate_baseline_is_created_when_no_candidate_is_feasible(evidence):
    assert evidence["status"] == (
        "NO_EXISTING_OUTER_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION"
    )
    assert evidence["blocking_classification"] == evidence["status"]
    assert not selection.CANDIDATE_BASELINE.exists()
