"""Preregistration and conservative R4.2 PI-boundary evidence checks."""

import json

import pytest
from v0_2.examples import phase5_r4_2_pi_boundary_search as search


@pytest.fixture(scope="module")
def registration():
    return json.loads(search.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(search.EVIDENCE.read_text(encoding="utf-8"))


def test_registration_was_frozen_before_execution(registration, evidence):
    source_registration = search.r41._load(search.r41.REGISTRATION)
    source_evidence = search.r41._load(search.r41.EVIDENCE)
    assert search.r41._sha(search.REGISTRATION) == search.EXPECTED_REGISTRATION_SHA256
    assert evidence["registration_sha256"] == search.EXPECTED_REGISTRATION_SHA256
    assert search._integrity(registration, source_registration, source_evidence)["status"] == "PASS"
    assert evidence["integrity"]["status"] == "PASS"
    assert all(evidence["integrity"]["checks"].values())
    assert evidence["source_r4_1_evidence_sha256"] == registration["source_r4_1_evidence_sha256"]


def test_fixed_domain_target_inner_and_historical_initial_states(registration, evidence):
    assert registration["kp_values"] == [2500, 3000, 3500, 4000, 4500, 5000]
    assert registration["ki_domain"] == [95.0, 125.0]
    assert registration["kd"] == 0
    assert registration["boundary_algorithm"]["bracket_tolerance_ki"] == 0.10
    assert registration["target_k"] == 313.71072595542387
    assert registration["inner"] == {"id": "inner_b", "kp": 1.5e-5, "ki": 4e-6, "kd": 0.0}
    source = search.r41._load(search.r41.EVIDENCE)
    for case in registration["training_cases"]:
        assert evidence["preparation"][case]["normalized_initial_state_sha256"] == source["preparation"][case]["normalized_initial_state_sha256"]
    assert registration["controller_structure_changes_authorized"] is False


def test_each_boundary_is_monotonic_and_conservative(evidence):
    canonical = evidence["canonical_boundaries"]
    assert [item["kp"] for item in canonical] == [2500, 3000, 3500, 4000, 4500, 5000]
    assert all(item["monotonicity_status"] == "PASS" for item in canonical)
    assert all(all(check["status"] == "PASS" for check in item["initial_monotonicity"].values()) for item in canonical)
    for item in canonical:
        for case, boundary_key in (("WARM_CAPTURE", "warm_boundary"), ("COLD_CAPTURE", "cold_boundary")):
            probes = {probe["ki"]: probe["pass"] for probe in item["probes"][case]}
            assert search._monotonicity(probes, case)["status"] == "PASS"
            boundary = item[boundary_key]
            if boundary["status"] == "BRACKETED":
                assert 0 < boundary["width_ki"] <= 0.10
                assert probes[boundary["pass_bound"]] is True
                assert probes[boundary["fail_bound"]] is False
                assert boundary["midpoint_estimate_ki"] == pytest.approx((boundary["pass_bound"] + boundary["fail_bound"]) / 2)
        if item["overlap"]["classification"] == "CONFIRMED_GAP":
            assert item["overlap"]["confirmed_gap_width_ki"] == pytest.approx(item["cold_boundary"]["fail_bound"] - item["warm_boundary"]["fail_bound"])
            assert item["overlap"]["confirmed_gap_width_ki"] > 0.10
    assert canonical[-1]["cold_boundary"]["status"] == "COLD_BOUNDARY_ABOVE_DOMAIN"
    assert canonical[-1]["overlap"]["classification"] == "DOMAIN_NO_OVERLAP"


def test_monotonicity_anomaly_and_ambiguous_boundary_rules():
    assert search._monotonicity({100.0: True, 105.0: False, 110.0: True}, "WARM_CAPTURE")["status"] == "FAIL"
    assert search._monotonicity({100.0: False, 105.0: True, 110.0: False}, "COLD_CAPTURE")["status"] == "FAIL"
    warm = {"status": "BRACKETED", "pass_bound": 110.0, "fail_bound": 110.078125}
    cold = {"status": "BRACKETED", "fail_bound": 110.0, "pass_bound": 110.078125}
    assert search._overlap(warm, cold, 0.10)["classification"] == "BOUNDARY_AMBIGUOUS_WITHIN_SEARCH_TOLERANCE"


def test_all_points_are_in_domain_valid_and_have_required_provenance(evidence):
    points = evidence["all_boundary_search_points"]
    assert evidence["historical_reused_run_count"] == 60
    assert evidence["new_executed_run_count"] == 194
    assert len(points) == 254
    assert len({(item["kp"], item["ki"], item["physics_dt_ns"], item["case"]) for item in points}) == len(points)
    assert all(item["kp"] in search.EXPECTED_KP and 95 <= item["ki"] <= 125 for item in points)
    assert all(item["status"] == "EXECUTED" and item["metrics"] is not None for item in points)
    assert all(item["metrics"]["ownership_lineage_pass"] and item["metrics"]["conservation_pass"] for item in points)
    assert all(item["attempt_count"] <= 2 for item in points)
    assert {item["provenance"] for item in points} == {"R4_1_FROZEN_EVIDENCE", "R4_2_NEW_EXECUTION"}


def test_two_smallest_gaps_stay_open_on_both_fine_meshes(evidence):
    canonical_gaps = sorted(
        (item for item in evidence["canonical_boundaries"] if item["overlap"]["classification"] == "CONFIRMED_GAP"),
        key=lambda item: (item["overlap"]["confirmed_gap_width_ki"], item["kp"]),
    )
    assert [item["kp"] for item in canonical_gaps[:2]] == [4500, 4000]
    fine = evidence["near_gap_fine_mesh"]
    assert {(item["kp"], item["physics_dt_ns"]) for item in fine} == {
        (4500, 100_000_000), (4500, 50_000_000),
        (4000, 100_000_000), (4000, 50_000_000),
    }
    assert all(item["monotonicity_status"] == "PASS" for item in fine)
    assert all(item["overlap"]["classification"] == "CONFIRMED_GAP" for item in fine)
    assert all(item["overlap"]["confirmed_gap_width_ki"] > 0.10 for item in fine)


def test_safety_ownership_conservation_and_stop(evidence):
    assert evidence["startup_safety"] == {
        "status": "STARTUP_SAFETY_BLOCKER_PENDING",
        "candidate_independent": True,
        "cold_degraded_duration_s": 0.4,
        "full_feedback_qualification_blocked": True,
    }
    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["conservation"]["status"] == "PASS"
    assert evidence["holdout_used_for_search"] is False
    assert evidence["independent_validation_claim_allowed"] is False
    assert evidence["phase6_authorized"] is False
    assert evidence["status"] == "NO_PI_OVERLAP_CONFIRMED_IN_R42_DOMAIN"
    assert evidence["selected_candidate"] is None
    assert evidence["repeatability"]["status"] == "NOT_EXECUTED"
    assert not search.CANDIDATE_BASELINE.exists()
    assert search.FIGURE.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
