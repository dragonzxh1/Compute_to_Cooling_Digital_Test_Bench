"""R5 directional-law, architecture, and frozen-grid evidence checks."""

import inspect
import json
from dataclasses import replace

import pytest
from v0_2.control.directional_outer import DirectionalOuterFeedback
from v0_2.control.outer_feedback import OuterFeedback
from v0_2.examples import phase5_r5_directional_pi as tuning


class GuardedMeasurement:
    def __init__(self, temperature_k):
        self.device_temperatures_k = (("device", temperature_k),)

    def qualified(self, name, now_ns, max_age_ns):
        return name == "temperature"

    def __getattr__(self, name):
        raise AssertionError(f"Controller attempted forbidden measurement field: {name}")


@pytest.fixture(scope="module")
def registration():
    return json.loads(tuning.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(tuning.EVIDENCE.read_text(encoding="utf-8"))


def test_exact_directional_blend_law_and_measured_only_input():
    config = replace(tuning.qualification.fixture_configs()[3], target_k=313.71072595542387)
    controller = DirectionalOuterFeedback(config, 110.0, 130.0)
    assert controller.effective_ki(-0.2) == (130.0, "COLD")
    assert controller.effective_ki(-0.1) == (130.0, "COLD")
    assert controller.effective_ki(0.0) == (120.0, "BLEND")
    assert controller.effective_ki(0.05)[0] == pytest.approx(115.0)
    assert controller.effective_ki(0.05)[1] == "BLEND"
    assert controller.effective_ki(0.1) == (110.0, "HOT")
    assert controller.effective_ki(0.2) == (110.0, "HOT")
    for name in ("scenario", "case", "true_temperature", "raw_actual"):
        assert name not in inspect.signature(DirectionalOuterFeedback.update).parameters
    for i, error in enumerate((0.2, 0.05, 0.0, -0.05, -0.2, 0.2)):
        controller.update(i * 1_000_000_000, GuardedMeasurement(config.target_k + error), config.base_dp_pa, 1_000_000_000)
    assert len(controller.ticks) == 6
    assert all(tick["integral_continuity_pass"] for tick in controller.ticks)
    assert all(tick["instantaneous_gain_jump_pa"] == 0 for tick in controller.ticks)
    assert isinstance(controller.pid.integral, float)
    assert "hot_integral" not in vars(controller) and "cold_integral" not in vars(controller)


def test_constant_directional_gain_matches_unchanged_pid_anti_windup():
    config = replace(tuning.qualification.fixture_configs()[3], target_k=313.71072595542387)
    config = replace(config, pid=replace(config.pid, ki=120.0))
    ordinary = OuterFeedback(config)
    directional = DirectionalOuterFeedback(config, 120.0, 120.0)
    for i, error in enumerate((0.3, 0.15, 0.05, -0.03, -0.2, 0.1)):
        measured = GuardedMeasurement(config.target_k + error)
        applied = config.base_dp_pa + 100.0 * i
        a = ordinary.update(i * 1_000_000_000, measured, applied, 1_000_000_000)
        b = directional.update(i * 1_000_000_000, measured, applied, 1_000_000_000)
        assert a.requested_dp_pa == b.requested_dp_pa
        assert ordinary.pid.integral == directional.pid.integral
    assert len(directional.ticks) == 6


def test_preregistration_and_historical_integrity(registration, evidence):
    historical = tuning.r41._load(tuning.r41.REGISTRATION)
    assert tuning.r41._sha(tuning.REGISTRATION) == tuning.EXPECTED_REGISTRATION_SHA256
    assert evidence["registration_sha256"] == tuning.EXPECTED_REGISTRATION_SHA256
    assert tuning._integrity(registration, historical)["status"] == "PASS"
    assert evidence["integrity"]["status"] == "PASS"
    assert all(evidence["integrity"]["checks"].values())
    assert evidence["source_r4_2_evidence_sha256"] == registration["source_r4_2_evidence_sha256"]
    assert registration["outer_kp"] == 4500 and registration["outer_kd"] == 0
    assert registration["directional_law"]["single_integral_state"] is True


def test_exact_32_run_grid_and_historical_preparation(registration, evidence):
    candidates = tuning._candidates(registration)
    assert len(candidates) == 16
    assert evidence["candidates"] == candidates
    assert {(item["ki_hot"], item["ki_cold"]) for item in candidates} == {
        (hot, cold) for hot in (110, 112, 114, 116) for cold in (124, 126, 128, 130)
    }
    assert evidence["stage_a"]["expected_runs"] == evidence["stage_a"]["completed_runs"] == 32
    assert evidence["stage_a"]["invalid_runs"] == evidence["invalid_run_count"] == 0
    assert {(item["candidate_id"], item["case"], item["physics_dt_ns"]) for item in evidence["stage_a"]["run_matrix"]} == {
        (candidate["id"], case, 200_000_000) for candidate in candidates for case in registration["training_cases"]
    }
    previous = tuning.r41._load(tuning.r41.EVIDENCE)
    for case in registration["training_cases"]:
        assert evidence["preparation"][case]["normalized_initial_state_sha256"] == previous["preparation"][case]["normalized_initial_state_sha256"]


def test_feasibility_map_and_per_tick_blend_audit(evidence):
    assert evidence["stage_a"]["thermally_feasible_count"] == 12
    decisions = evidence["stage_a"]["candidate_decisions"]
    assert sum(item["map_status"] == "BOTH_PASS" for item in decisions) == 12
    assert sum(item["map_status"] == "WARM_ONLY" for item in decisions) == 4
    assert all(item["map_status"] == evidence["feasibility_map"][str(int(item["ki_hot"]))][str(int(item["ki_cold"]))] for item in decisions)
    for record in evidence["stage_a"]["run_matrix"]:
        audit = record["blend_audit"]
        assert audit["status"] == "PASS"
        assert audit["integral_continuity_all_ticks_pass"] is True
        assert len(audit["outer_ticks"]) == 181
        assert audit["complete_directional_traversals_final_60s"] <= 6
        assert sum(audit["region_duration_s"].values()) == pytest.approx(180.0)
        assert all(tick["integral_continuity_pass"] and tick["instantaneous_gain_jump_pa"] == 0 for tick in audit["outer_ticks"])
        assert all(110 <= tick["ki_eff"] <= 130 for tick in audit["outer_ticks"])
        assert record["metrics"]["ownership_lineage_pass"] and record["metrics"]["conservation_pass"]


def test_five_finalists_pass_all_meshes_and_selected_score(evidence):
    expected = [
        "R5-KP4500-H110-C130", "R5-KP4500-H112-C130", "R5-KP4500-H114-C130",
        "R5-KP4500-H116-C130", "R5-KP4500-H110-C128",
    ]
    assert evidence["stage_b"]["finalist_ids"] == expected
    assert evidence["stage_b"]["expected_runs"] == evidence["stage_b"]["completed_runs"] == 20
    assert all(item["status"] == "PASS" and item["directional_all_meshes_pass"] for item in evidence["stage_b"]["convergence"])
    assert evidence["selection"]["candidate_id"] == expected[0]
    selected = next(item for item in evidence["stage_a"]["candidate_decisions"] if item["id"] == expected[0])
    assert selected["score"]["warm_settling_time_s"] == 109.0
    assert selected["score"]["cold_settling_time_s"] == 127.2
    assert selected["score"]["worst_side_settling_time_s"] == 127.2
    assert selected["score"]["total_directional_traversals"] == 1


def test_safety_ownership_conservation_repeatability_and_candidate_baseline(evidence):
    assert evidence["startup_safety"]["status"] == "STARTUP_SAFETY_BLOCKER_PENDING"
    assert evidence["startup_safety"]["candidate_independent"] is True
    assert evidence["startup_safety"]["full_feedback_qualification_blocked"] is True
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["conservation"]["status"] == "PASS"
    assert evidence["repeatability"]["status"] == "PASS"
    assert [item["completed_runs"] for item in evidence["repeatability"]["cases"]] == [10, 10]
    assert all(item["identical_hashes"] for item in evidence["repeatability"]["cases"])
    assert evidence["holdout_used_for_tuning"] is False
    assert evidence["training_cases_not_independent_validation"] is True
    assert evidence["phase6_authorized"] is False
    assert evidence["status"] == "DIRECTIONAL_PI_CANDIDATE_FOUND_WITH_STARTUP_SAFETY_BLOCKER"
    baseline = json.loads(tuning.CANDIDATE_BASELINE.read_text(encoding="utf-8"))
    assert baseline["outer_kp"] == 4500
    assert baseline["ki_hot"] == 110 and baseline["ki_cold"] == 130
    assert baseline["single_integral_state"] is True
    assert baseline["evidence_sha256"] == tuning.r41._sha(tuning.EVIDENCE)
    assert tuning.FIGURE.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert not (tuning.ROOT / "phase5_r5_directional_pi_feedback_baseline.json").exists()
    assert not (tuning.ROOT / "phase5_r5_feedback_baseline.json").exists()
