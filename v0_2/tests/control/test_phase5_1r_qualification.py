import hashlib
import json
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R1_BASELINE_SHA = "24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d"
R1_CODE_SHA = "b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579"
R1_REGISTRATION_SHA = "9ef5cd97c2d4bf3f2540739a58d676bf2c64c4e6be0421fe8a21a4482cb36066"
R1_SELECTION_SHA = "fe9f5e78cbf27197ffbe61ea68f7b5ab76264ae6f864fa0494b6fdc6d5c1c6d5"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_01_r1_baseline_integrity_and_immutability():
    baseline = _json(ROOT / "phase5_r1_feedback_baseline.json")
    assert _sha(ROOT / "phase5_r1_feedback_baseline.json") == R1_BASELINE_SHA
    assert baseline["code_sha256"] == R1_CODE_SHA
    assert _sha(ROOT / "phase5_r1_revision_registration.json") == R1_REGISTRATION_SHA
    assert _sha(ROOT / "phase5_r1_selection_evidence.json") == R1_SELECTION_SHA


def test_02_qualification_registration_preserves_frozen_parameters():
    baseline = _json(ROOT / "phase5_r1_feedback_baseline.json")
    registration = _json(ROOT / "phase5_1r_qualification_registration.json")
    assert registration["thermal_target_k"] == baseline["thermal_control_target_k"] == 305
    assert registration["saturation_limits"]["bounds_fraction"] == [
        baseline["actuator"]["minimum"],
        baseline["actuator"]["maximum"],
    ]
    assert registration["dt_meshes_ns"][0] == baseline["physics_period_ns"]
    assert registration["retuning_allowed"] is False


def test_03_candidate_grid_is_deterministic_and_covers_registered_endpoints():
    registration = _json(ROOT / "phase5_1r_qualification_registration.json")
    grid = registration["candidate_grid_w_per_device"]
    assert grid == [120.0, 140.0, 160.0, 180.0, 200.0, 220.0, 240.0]
    assert len({b - a for a, b in pairwise(grid)}) == 1


def test_04_scan_is_plant_only_and_uses_every_candidate_once():
    registration = _json(ROOT / "phase5_1r_qualification_registration.json")
    scan = _json(ROOT / "docs/results/phase5_1r_feasibility_scan.json")
    assert scan["controller_executed"] is False
    assert scan["selection_uses_closed_loop_metrics"] is False
    assert [x["power_w_per_device"] for x in scan["candidates"]] == registration[
        "candidate_grid_w_per_device"
    ]


def test_05_no_candidate_brackets_frozen_305_k_target():
    scan = _json(ROOT / "docs/results/phase5_1r_feasibility_scan.json")
    assert all(
        item["low_cooling"]["qualified_window_mean_max_device_k"] > 305.5
        for item in scan["candidates"]
    )
    assert all(
        item["maximum_cooling"]["qualified_window_mean_max_device_k"] >= 304.5
        for item in scan["candidates"]
    )
    assert not any(item["target_bracketed_by_plant"] for item in scan["candidates"])


def test_06_selection_is_deterministically_blocked_before_closed_loop():
    scan = _json(ROOT / "docs/results/phase5_1r_feasibility_scan.json")
    result = _json(ROOT / "phase5_1r_nominal_result.json")
    assert scan["selected"] is None
    assert scan["status"] == "NO_FEASIBLE_REGULATION_REGION"
    assert result["nominal_fixture_sha256"] is None
    assert result["closed_loop_executed"] is False
    assert result["blocking_classification"] == "A_NO_FEASIBLE_REGULATION_REGION"


def test_07_open_loop_scan_preserves_mass_and_energy_gates():
    scan = _json(ROOT / "docs/results/phase5_1r_feasibility_scan.json")
    endpoints = [
        item[label]
        for item in scan["candidates"]
        for label in ("low_cooling", "maximum_cooling")
    ]
    assert max(x["max_mass_residual_kg_s"] for x in endpoints) < 1e-8
    assert max(x["max_energy_residual_j"] for x in endpoints) < 0.001


def test_08_no_nominal_figure_is_claimed_after_feasibility_block():
    assert not (ROOT / "docs/results/phase5_nominal_regulation_r1.png").exists()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "NO_FEASIBLE_REGULATION_REGION" in readme
    assert "phase5_nominal_regulation_r1.png" not in readme
