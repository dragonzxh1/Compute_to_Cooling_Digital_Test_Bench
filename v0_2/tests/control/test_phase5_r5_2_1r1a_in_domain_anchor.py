"""In-domain two-stage fixture validation without R1 semantic changes."""

import json
from pathlib import Path

from v0_2.examples import phase5_r5_2_1r1a_validation as validation
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_preregistration_profile_source_and_historical_c9_immutable():
    reg = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json")
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
    assert evidence["registration_sha256"] == sha(validation.REGISTRATION)
    assert all(validation.integrity(reg, profile).values())
    assert reg["r1_registration_sha256"] == "349faabfeda2661c472044bf572e6073d49c76d9f4042bc1158d37ff13a8ead1"
    assert evidence["profile_sha256"] == "9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8"
    assert evidence["historical_original_c9"]["source_evidence_sha256"] == "889c78af7c8f3e39300c607c820de8db6752951f835cf12e7aec447459221620"
    assert evidence["historical_original_c9"]["status"] == "INVALID_VALIDATION_FIXTURE: COMMAND_OUTSIDE_FROZEN_PROFILE_DOMAIN"
    assert read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")["c_pass"]["C9"] is False


def test_exact_registered_sequence_and_domain_are_checked_before_run():
    reg = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json")
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
    commands = reg["replacement_case"]["commands"]
    assert [(x["time_ns"], x["command"]) for x in commands] == [
        (0, 0.35), (200_000_000, 0.40), (400_000_000, 0.45),
        (600_000_000, 0.51), (3_000_000_000, 0.56),
        (3_200_000_000, 0.61), (3_400_000_000, 0.67),
    ]
    assert all(validation.preregistered_sequence_validity(reg, profile).values())
    assert all(evidence["pre_execution_sequence_validity"].values())
    assert evidence["profile_bounds"] == {"speed_min": 0.3, "speed_max": 0.9}
    assert all(evidence["domain_checks"].values())
    assert all(0.3 < item["command"] < 0.9 for item in commands)


def test_two_anchor_advances_follow_resolved_epochs_only():
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    anchors = evidence["c9r_anchor_table"]
    assert [(item["anchor"], item["value"], item["established_at_ns"])
            for item in anchors] == [("A", 0.35, 0), ("B", 0.51, 1_200_000_000),
                                    ("C", 0.67, 4_000_000_000)]
    assert anchors[0]["source_obligation"] is None
    assert anchors[1]["source_obligation"] == "tracking-epoch:1"
    assert anchors[2]["source_obligation"] == "tracking-epoch:2"
    assert all(evidence["c9r_pass_criteria"].values())


def test_stage_two_uses_B_not_A_and_audit_is_complete():
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    rows = evidence["c9r_audit_table"]
    at_first = next(row for row in rows if row["time_ns"] == 600_000_000)
    at_second = next(row for row in rows if row["time_ns"] == 3_400_000_000)
    assert at_first["qualified_anchor"] == 0.35
    assert abs(at_first["net_demand"] - 0.16) < 1e-9
    assert at_second["qualified_anchor"] == 0.51
    assert abs(at_second["net_demand"] - 0.16) < 1e-9
    assert abs(at_second["net_demand"] - (0.67 - 0.35)) > 1e-9
    assert len(rows) == len(evidence["c9r_case"]["records"])
    assert all({"time_ns", "plc_command", "qualified_anchor", "net_demand", "demand_class",
                "epoch_id", "watch_id", "measured_speed", "tracking_state", "anchor_update"} <= set(row)
               for row in rows)


def test_valid_cases_historical_sequences_and_invariants():
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    assert set(evidence["c_regression"]) == {f"C{i}" for i in range(1, 13) if i != 9} | {
        "C9R_IN_DOMAIN_ANCHOR_ADVANCEMENT"}
    assert all(evidence["c_regression"].values())
    assert set(evidence["s_regression"]) == {f"S{i}" for i in range(1, 17)} | {"S16_variant"}
    assert all(evidence["s_regression"].values())
    assert len(evidence["invariants_1_to_14"]) == 14
    assert all(evidence["invariants_1_to_14"].values())
    assert all(evidence["prefix_causality"].values())
    assert evidence["status"] == "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN"


def test_semantic_profile_and_production_freeze():
    evidence = read("phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    assert evidence["semantic_engine_sha256"] == "e9bb0de5c15c10a9ccbdbe899c3fd1cb1f5e05145af79c2e142b9990cd7020ef"
    assert evidence["semantic_rules_changed"] is False
    assert evidence["recalibration_performed"] is False
    assert evidence["new_numeric_tracking_parameters"] is False
    assert evidence["production_hashes_unchanged"] is True
    assert evidence["production_safety_changed"] is False
    assert evidence["phase5_r5_3r_started"] is False
    assert evidence["final_feedback_baseline_frozen"] is False
    assert evidence["phase6_started"] is False
    assert (ROOT / "docs/results/phase5_r5_2_1r1a_in_domain_anchor_revalidation.png").is_file()
