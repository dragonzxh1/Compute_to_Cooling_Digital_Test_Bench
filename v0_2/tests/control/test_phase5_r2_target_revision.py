import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
R1_BASELINE_SHA = "24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d"
R1_CONTROL_CORE_SHA = "b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579"
R1_REGISTRATION_SHA = "9ef5cd97c2d4bf3f2540739a58d676bf2c64c4e6be0421fe8a21a4482cb36066"
R1_SELECTION_SHA = "fe9f5e78cbf27197ffbe61ea68f7b5ab76264ae6f864fa0494b6fdc6d5c1c6d5"
R2_REGISTRATION_SHA = "8b2bda84c6591e678d0fde972562e1f0dc7a10d0b22c82b76a10f34372c860a2"


def _json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def artifacts():
    return {
        "r1": _json("phase5_r1_feedback_baseline.json"),
        "tuning": _json("phase5_tuning_registration.json"),
        "registration": _json("phase5_r2_target_registration.json"),
        "evidence": _json("phase5_r2_selection_evidence.json"),
        "candidate": _json("phase5_r2_candidate_baseline.json"),
    }


def test_r1_integrity_and_endpoint_reproduction(artifacts):
    registration = artifacts["registration"]
    evidence = artifacts["evidence"]
    assert _sha("phase5_r1_feedback_baseline.json") == R1_BASELINE_SHA
    assert registration["source_r1_control_core_sha256"] == R1_CONTROL_CORE_SHA
    assert registration["source_r1_revision_registration_sha256"] == R1_REGISTRATION_SHA
    assert registration["source_r1_selection_evidence_sha256"] == R1_SELECTION_SHA
    assert evidence["endpoint_reproduction"]["status"] == "PASS"
    assert abs(evidence["endpoint_reproduction"]["low_difference_k"]) <= 0.01
    assert abs(evidence["endpoint_reproduction"]["high_difference_k"]) <= 0.01


def test_target_is_exact_registered_midpoint_with_two_sided_margin(artifacts):
    authority = artifacts["evidence"]["authority"]
    registration = artifacts["registration"]
    assert authority["target_k"] == (authority["t_low_k"] + authority["t_high_k"]) / 2
    assert authority["upper_margin_k"] == pytest.approx(
        authority["t_low_k"] - authority["target_k"], abs=1e-14
    )
    assert authority["lower_margin_k"] == pytest.approx(
        authority["target_k"] - authority["t_high_k"], abs=1e-14
    )
    minimum = registration["required_authority_margin_k_each_side"]
    assert authority["upper_margin_k"] >= minimum
    assert authority["lower_margin_k"] >= minimum


def test_only_target_dependent_baseline_fields_change_before_reselection(artifacts):
    r1 = artifacts["r1"]
    candidate = artifacts["candidate"]
    for field in (
        "sample_period_ns",
        "outer_period_ns",
        "plc_period_ns",
        "actuator_period_ns",
        "physics_period_ns",
        "safety_period_ns",
        "actuator",
        "sensor",
        "base_dp_pa",
    ):
        assert candidate[field] == r1[field]
    for key, value in r1["safety"].items():
        if key != "control_target_k":
            assert candidate["safety"][key] == value
    assert candidate["thermal_control_target_k"] == candidate["safety"]["control_target_k"]
    assert candidate["thermal_control_target_k"] < candidate["safety"]["derate_k"]
    assert candidate["safety"]["derate_k"] < candidate["safety"]["hard_k"]
    assert candidate["code_sha256"] == R1_CONTROL_CORE_SHA


def test_candidate_grids_priority_and_holdout_role_are_frozen(artifacts):
    registration = artifacts["registration"]
    tuning = artifacts["tuning"]
    evidence = artifacts["evidence"]
    policy = registration["controller_candidate_policy"]
    assert policy["inner_candidates"] == [item["id"] for item in tuning["inner_candidates"]]
    assert policy["outer_candidates"] == [item["id"] for item in tuning["outer_candidates"]]
    assert evidence["selection_priority"] == policy["selection_priority"]
    assert evidence["holdout_used_in_selection"] is False
    assert registration["historical_holdout_role"]["selection_input"] is False


def test_reselection_triggers_registered_stop_and_withholds_final_baseline(artifacts):
    evidence = artifacts["evidence"]
    candidate = artifacts["candidate"]
    assert evidence["selected"] == {"inner": "inner_b", "outer": "outer_b"}
    assert evidence["status"] == "OUTER_SELECTION_CHANGED_DUE_TO_TARGET_REVISION"
    assert candidate["status"] == evidence["status"]
    assert candidate["inner_candidate_id"] == "inner_b"
    assert candidate["outer_candidate_id"] == "outer_b"
    final_baseline = ROOT / "phase5_r2_feedback_baseline.json"
    if final_baseline.exists():
        frozen = _json("phase5_r2_feedback_baseline.json")
        finalization = _json("phase5_r2_2_finalization_evidence.json")
        assert frozen["user_authorized_final_selection"]["outer_candidate_id"] == "outer_a"
        assert finalization["status"] == "PASS_FINAL_R2_BASELINE_FROZEN_AWAITING_USER_REVIEW"
    assert evidence["downstream_stress_convergence_stability_executed"] is False


def test_ownership_and_training_conservation_remain_passing(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["ownership_audit_reference"]["status"] == "PASS"
    metrics = [
        row["metrics"]
        for stage in ("inner_training", "outer_training")
        for candidate in evidence[stage]
        for row in candidate["training"]
    ]
    assert max(item["max_mass_residual_kg_s"] for item in metrics) <= 1e-8
    assert max(item["max_energy_residual_j"] for item in metrics) <= 0.001


def test_artifact_linkage_and_authority_figure(artifacts):
    candidate = artifacts["candidate"]
    assert _sha("phase5_r2_target_registration.json") == R2_REGISTRATION_SHA
    assert candidate["r2_target_registration_sha256"] == R2_REGISTRATION_SHA
    assert candidate["selection_evidence_sha256"] == _sha("phase5_r2_selection_evidence.json")
    figure = ROOT / "docs/results/phase5_r2_target_authority.png"
    assert figure.is_file()
    assert figure.stat().st_size > 10_000
