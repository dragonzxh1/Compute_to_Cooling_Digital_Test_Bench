"""R1 cumulative-net-demand offline evidence and immutable-source checks."""

import json
from pathlib import Path

from v0_2.examples import phase5_r5_2_1r1_validation as validation
from v0_2.examples.phase5_r5_2_1r1_cumulative_engine import CumulativeTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_registration_source_and_profile_freeze():
    registration = read("phase5_r5_2_1r1_cumulative_command_demand_registration.json")
    evidence = read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")
    assert evidence["registration_sha256"] == sha(validation.REGISTRATION)
    assert registration["prior_gate"] == "TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT"
    assert all(validation.verify_sources(registration).values())
    assert evidence["profile_sha256"] == "9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8"
    assert evidence["profile_recalibrated"] is False
    assert evidence["new_numeric_tracking_parameters"] is False


def test_anchor_is_resolved_command_not_previous_step_or_prep_history():
    evidence = read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")
    c1 = evidence["c_cases"]["C1"]
    assert c1["anchor_events"][0]["anchor_update_reason"] == "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE"
    assert c1["records"][2]["plc_command"] == 0.7
    assert c1["records"][2]["qualified_command_anchor"] == 0.5
    assert c1["records"][2]["net_command_demand"] > 0.15
    assert c1["records"][2]["epoch_start_ns"] == 400_000_000
    c10 = evidence["c_cases"]["C10"]
    assert c10["qualified_command_anchor"] == 0.5
    c2 = evidence["c_cases"]["C2"]
    assert c2["anchor_events"][-1]["anchor_update_reason"] == "QUALIFIED_EPOCH_RESOLVED_TO_STEADY"
    assert c2["qualified_command_anchor"] == 0.8
    # A first PLC command outside frozen steady tolerance keeps startup anchor absent.
    profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
    classifier = read("phase5_r5_2_silent_tracking_fault_registration.json")["classifier"]
    qualifier = CumulativeTrackingQualifier(profile, classifier)
    qualifier.update(ReleasedObservation(0, 0.7, 0, 0.5, 0, 0, "VALID", "first"))
    assert qualifier.qualified_command_anchor is None


def test_net_not_absolute_path_and_fault_evidence_retained():
    evidence = read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")
    c4 = evidence["c_cases"]["C4"]
    assert not [event for event in c4["epoch_events"] if event["event"] == "START"]
    assert max(abs(row["net_command_demand"]) for row in c4["records"]) < 0.15
    assert evidence["c_cases"]["C7"]["confirmed_latched"]
    assert evidence["c_cases"]["C8_stuck"]["confirmed_latched"]
    assert evidence["c_cases"]["C11"]["confirmed_latched"]
    assert evidence["c_cases"]["C12"]["confirmed_latched"]


def test_registered_sequences_and_invariants_with_domain_block():
    evidence = read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")
    assert set(evidence["c_pass"]) == {f"C{i}" for i in range(1, 13)}
    assert all(ok for key, ok in evidence["c_pass"].items() if key != "C9")
    assert evidence["c_pass"]["C9"] is False
    assert evidence["semantic_c_pass_before_domain_audit"]["C9"] is True
    assert evidence["post_validation_domain_audit"]["C9"]
    assert evidence["profile_command_domain"]["max"] == 0.9
    assert evidence["status"] == "CUMULATIVE_COMMAND_DEMAND_VALIDATION_FIXTURE_OUT_OF_PROFILE_DOMAIN"
    assert set(evidence["historical_pass"]) == {f"S{i}" for i in range(1, 17)} | {"S16_variant"}
    assert all(evidence["historical_pass"].values())
    assert len(evidence["original_invariants"]) == 8
    assert len(evidence["added_invariants"]) == 4
    assert all(evidence["original_invariants"].values())
    assert all(evidence["added_invariants"].values())
    assert all(evidence["prefix_causality"].values())


def test_audit_tables_boundary_and_no_production_change():
    evidence = read("phase5_r5_2_1r1_cumulative_command_demand_evidence.json")
    assert set(evidence["audit_tables"]) == {"C1", "C2", "C4", "C7", "C9", "C12"}
    assert all(evidence["audit_tables"].values())
    assert evidence["production_hashes_unchanged"] is True
    assert evidence["production_safety_changed"] is False
    assert evidence["phase5_r5_3r_started"] is False
    assert evidence["phase6_started"] is False
    assert set(ReleasedObservation.__dataclass_fields__).isdisjoint(
        {"actual_speed", "fault_identity", "scenario_label", "future_measurement"}
    )
    assert "ActuatorCommand" not in CumulativeTrackingQualifier.__dict__
    assert (ROOT / "docs/results/phase5_r5_2_1r1_cumulative_command_demand.png").is_file()
