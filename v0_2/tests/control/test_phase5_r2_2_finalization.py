import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASELINE_SHA = "891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1"
EVIDENCE_SHA = "f33eb500ee224fbbd4a80b88affcaa77902ea08c33714c10ae4493c76d576208"
R1_SHA = "24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d"
CORE_SHA = "b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579"
TARGET = 313.71072595542387


def _load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def artifacts():
    return {
        "baseline": _load("phase5_r2_feedback_baseline.json"),
        "evidence": _load("phase5_r2_2_finalization_evidence.json"),
    }


def test_finalization_integrity_and_authorized_selection(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["integrity"]["status"] == "PASS"
    assert evidence["integrity"]["actual"] == evidence["integrity"]["expected"]
    assert evidence["user_authorized_selection"]["target_k"] == TARGET
    assert evidence["user_authorized_selection"]["inner"]["id"] == "inner_b"
    assert evidence["user_authorized_selection"]["outer"]["id"] == "outer_a"


def test_historical_stress_is_characterization_not_selection(artifacts):
    stress = artifacts["evidence"]["historical_stress"]
    assert stress["status"] == "PASS"
    assert stress["classification"] == "HISTORICAL STRESS CHARACTERIZATION"
    assert stress["selection_input"] is False
    assert stress["metrics"]["safety_fault_event_count"] == 0
    assert stress["metrics"]["saturation_duration_s"] == 0.0


def test_selected_baseline_three_mesh_convergence_passes(artifacts):
    convergence = artifacts["evidence"]["selected_baseline_convergence"]
    assert convergence["status"] == "PASS"
    for metric, difference in convergence["fine_pair_differences"].items():
        assert difference <= convergence["tolerances"][metric]
    assert convergence["coarse_metrics"]["temperature_iae_k_s"] == pytest.approx(11.853641284061212)
    assert convergence["fine_metrics"]["temperature_iae_k_s"] == pytest.approx(12.182465538164081)


def test_ownership_stability_and_closure_pass(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["ownership"]["validated_run_lineage_pass"] is True
    assert evidence["repeated_stability"]["status"] == "PASS"
    assert evidence["repeated_stability"]["runs"] == 10
    assert evidence["repeated_stability"]["identical_hashes"] is True
    assert evidence["repeated_stability"]["bounded_retained_memory"] is True
    assert evidence["mass_energy"]["status"] == "PASS"
    assert evidence["mass_energy"]["max_mass_residual_kg_s"] <= 1e-8
    assert evidence["mass_energy"]["max_energy_residual_j"] <= 0.001


def test_final_baseline_contains_frozen_r2_configuration_and_lineage(artifacts):
    baseline = artifacts["baseline"]
    assert baseline["schema"] == "phase5-r2-feedback-baseline-v1"
    assert baseline["revision"] == 2
    assert baseline["status"] == "FROZEN_GENERIC_TEST_BASELINE_REVISION_2_NOT_OEM"
    assert baseline["thermal_control_target_k"] == TARGET
    assert baseline["safety"]["control_target_k"] == TARGET
    assert baseline["inner_candidate_id"] == "inner_b"
    assert baseline["outer_candidate_id"] == "outer_a"
    assert baseline["inner_gains"] == {"kp": 1.5e-5, "ki": 4e-6, "kd": 0.0}
    assert baseline["outer_gains"] == {"kp": 1000.0, "ki": 20.0, "kd": 0.0}
    assert baseline["supersedes_r1_baseline_sha256"] == R1_SHA
    assert baseline["code_sha256"] == CORE_SHA
    assert baseline["historical_stress_id"] == "HOLDOUT-01-combined"


def test_baseline_payload_and_complete_file_hashes_are_valid(artifacts):
    baseline = artifacts["baseline"]
    payload = dict(baseline)
    expected_payload_sha = payload.pop("final_baseline_sha256")
    payload.pop("final_baseline_sha256_scope")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == expected_payload_sha
    assert _sha("phase5_r2_feedback_baseline.json") == BASELINE_SHA
    assert artifacts["evidence"]["final_baseline"]["file_sha256"] == BASELINE_SHA


def test_final_gate_evidence_is_frozen_and_phase_scope_stops(artifacts):
    evidence = artifacts["evidence"]
    assert evidence["status"] == "PASS_FINAL_R2_BASELINE_FROZEN_AWAITING_USER_REVIEW"
    assert _sha("phase5_r2_2_finalization_evidence.json") == EVIDENCE_SHA
