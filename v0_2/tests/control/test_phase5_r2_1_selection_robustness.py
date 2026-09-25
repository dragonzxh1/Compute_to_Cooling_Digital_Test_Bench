import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REGISTRATION_SHA = "4942860bf06d991942b4ae5fbe1d8bfd9a28ded3263e77c716bfabaa5481f735"
EVIDENCE_SHA = "dafa0034206912172901de8655c147886cfb7296a3c24601dcc64e3696fa2052"
TARGET = 313.71072595542387


def _load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def artifacts():
    return {
        "registration": _load("phase5_r2_1_selection_robustness_registration.json"),
        "evidence": _load("phase5_r2_1_selection_robustness_evidence.json"),
    }


def test_registration_frozen_inputs_and_integrity(artifacts):
    registration = artifacts["registration"]
    evidence = artifacts["evidence"]
    assert _sha("phase5_r2_1_selection_robustness_registration.json") == REGISTRATION_SHA
    assert evidence["registration_sha256"] == REGISTRATION_SHA
    assert evidence["integrity"]["status"] == "PASS"
    assert evidence["integrity"]["actual"] == evidence["integrity"]["expected"]
    assert registration["target_k"] == TARGET
    assert registration["inner_candidate"]["id"] == "inner_b"
    assert [item["id"] for item in registration["outer_candidates"]] == [
        "outer_a",
        "outer_b",
        "outer_c",
    ]
    assert registration["physics_dt_ns"] == [200_000_000, 100_000_000, 50_000_000]


def test_complete_36_run_matrix_has_no_invalid_cell(artifacts):
    evidence = artifacts["evidence"]
    summary = evidence["run_matrix_summary"]
    assert summary == {
        "expected_runs": 36,
        "completed_runs": 36,
        "passing_runs": 36,
        "invalid_runs": 0,
    }
    keys = {
        (item["candidate_id"], item["physics_dt_ns"], item["scenario_id"])
        for item in evidence["run_matrix"]
    }
    assert len(keys) == 36


def test_aggregation_and_raw_winners_are_stable_across_meshes(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["raw_winners_by_dt_ns"] == {
        "200000000": "outer_b",
        "100000000": "outer_b",
        "50000000": "outer_b",
    }
    for aggregate in evidence["aggregates"]:
        assert aggregate["feasibility_failed"] is False
    assert evidence["candidate_convergence_pass"] is True
    assert all(item["acceptable"] for item in evidence["candidate_sensitivity"])


def test_registered_uncertainty_veto_makes_candidates_indistinguishable(artifacts):
    evidence = artifacts["evidence"]
    comparisons = {item["pair"]: item for item in evidence["pairwise"]}
    ab = comparisons["outer_a_minus_outer_b"]
    assert ab["fine_mesh_absolute_difference"] == pytest.approx(0.01153351974586414)
    assert ab["numerical_uncertainty_bound"] == pytest.approx(0.22036788364440518)
    assert ab["distinguishable"] is False
    assert all(item["distinguishable"] is False for item in comparisons.values())


def test_registered_tie_break_changes_final_selection_and_forces_stop(artifacts):
    evidence = artifacts["evidence"]
    fine = {
        item["candidate_id"]: item
        for item in evidence["aggregates"]
        if item["physics_dt_ns"] == 50_000_000
    }
    assert fine["outer_a"]["control_total_variation"] < fine["outer_b"]["control_total_variation"]
    assert fine["outer_a"]["control_total_variation"] < fine["outer_c"]["control_total_variation"]
    assert evidence["selection"]["candidate_id"] == "outer_a"
    assert evidence["selection"]["reason"] == "NUMERICALLY_INDISTINGUISHABLE_TIE_BREAK"
    assert evidence["status"] == "FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS"
    final_baseline = ROOT / "phase5_r2_feedback_baseline.json"
    if final_baseline.exists():
        frozen = _load("phase5_r2_feedback_baseline.json")
        finalization = _load("phase5_r2_2_finalization_evidence.json")
        assert frozen["user_authorized_final_selection"]["outer_candidate_id"] == "outer_a"
        assert finalization["status"] == "PASS_FINAL_R2_BASELINE_FROZEN_AWAITING_USER_REVIEW"


def test_ownership_mass_energy_and_no_holdout_selection(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["ownership"]["static"]["status"] == "PASS"
    assert evidence["ownership"]["runtime"]["status"] == "PASS"
    assert evidence["ownership"]["matrix_lineage_pass"] is True
    metrics = [item["metrics"] for item in evidence["run_matrix"]]
    assert max(item["max_mass_residual_kg_s"] for item in metrics) <= 1e-8
    assert max(item["max_energy_residual_j"] for item in metrics) <= 0.001
    assert evidence["holdout_used_in_selection"] is False


def test_downstream_work_is_withheld_after_changed_selection(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["historical_stress"]["status"] == "NOT_EXECUTED"
    assert evidence["selected_baseline_convergence"]["status"] == "NOT_EXECUTED"
    assert evidence["repeated_stability"]["status"] == "NOT_EXECUTED"
    assert _sha("phase5_r2_1_selection_robustness_evidence.json") == EVIDENCE_SHA
