"""R2R contract-only mapping and production representation audits."""

from v0_2.examples.phase5_r5_2_1r2r_mapping_validation import (
    CONTRACT,
    EVIDENCE,
    REG,
    ROOT,
    load,
    schema_audit,
    sha,
    validate,
)


def test_preregistration_and_frozen_sources():
    registration = load(REG)
    contract = load(CONTRACT)
    evidence = load(EVIDENCE)
    assert contract["registration_sha256"] == evidence["registration_sha256"] == sha(REG)
    assert REG.stat().st_mtime_ns <= EVIDENCE.stat().st_mtime_ns
    assert all(evidence["source_hash_checks"].values())
    assert registration["source_sha256"]["contracts/14_control_input_permission_contract.md"] == contract["contract14_sha256"]
    assert registration["source_sha256"]["contracts/15_safety_supervisor_contract.md"] == contract["contract15_sha256"]
    assert registration["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"] == contract["contract15a_sha256"]
    assert registration["source_sha256"]["phase5_r5_2_2_fixture_tracking_profile.json"] == sha(
        ROOT / "phase5_r5_2_2_fixture_tracking_profile.json")
    assert evidence["production_source_hashes_unchanged"]
    assert not registration["production_change_authorized"]


def test_six_state_mapping_and_reason_definitions():
    contract = load(CONTRACT)
    r3 = load(ROOT / "phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    assert contract["tracking_states"] == r3["tracking_states"]
    assert len(contract["tracking_states"]) == 6
    assert contract["tracking_states"]["HANDOFF_PENDING"]["severity"] == "NORMAL"
    assert contract["tracking_states"]["HANDOFF_PENDING"]["reason_codes"] == []
    assert contract["tracking_states"]["TRACKING_FAULT_SUSPECTED"]["reason_codes"] == ["ACTUATOR_TRACKING_SUSPECTED"]
    assert contract["tracking_states"]["TRACKING_FAULT_CONFIRMED"]["reason_codes"] == ["ACTUATOR_TRACKING_CONFIRMED"]
    assert contract["tracking_states"]["INSUFFICIENT_MEASUREMENT"]["reason_codes"] == []
    assert set(contract["reason_definitions"]) == {
        "ACTUATOR_TRACKING_PENDING", "ACTUATOR_TRACKING_SUSPECTED", "ACTUATOR_TRACKING_CONFIRMED"}
    assert not contract["reason_definitions"]["ACTUATOR_TRACKING_PENDING"]["new_mapping_use"]


def test_safety_types_can_represent_contract_without_primary_field():
    audit = schema_audit()
    assert audit["multiple_reasons_representable"]
    assert audit["severity_representable"]
    assert audit["envelope_representable"]
    assert audit["fault_reset_representable"]
    assert audit["tracking_provenance_link_possible"]
    assert audit["sensor_reason_coexistence_representable"]
    assert audit["current_single_branch_logic"]
    assert not audit["primary_reason_mandatory"]
    assert not audit["safety_decision_emits_command"]


def test_m1_to_m16_and_channel_interactions():
    evidence = validate()
    assert set(evidence["case_pass"]) == {f"M{i}" for i in range(1, 17)}
    assert all(evidence["case_pass"].values())
    out = evidence["case_outputs"]
    assert out["M2"]["final_safety"] == "NORMAL" and not out["M2"]["all_reasons"]
    assert out["M4"]["final_safety"] == "DEGRADED"
    assert out["M5"]["final_safety"] == "FAULT"
    assert out["M6"]["all_reasons"] == ["CRITICAL_LOCAL_SENSOR_INVALID"]
    assert out["M7"]["final_safety"] == "FAULT" and len(out["M7"]["all_reasons"]) == 2
    assert out["M9"]["final_safety"] == "PROTECTED"
    assert out["M10"]["final_safety"] == "FAULT"
    assert out["M13"]["prior_suspected_evidence_retained"]
    assert out["M14"]["latched_fault"] and len(out["M14"]["all_reasons"]) == 2
    assert out["M15"]["final_safety"] == "FF_DISABLED"
    assert out["M16"]["latched_fault"] and not out["M16"]["restored_motion_auto_clears_fault"]
    assert all(not value["tracking_specific_new_restriction"] for value in out.values())


def test_contract_audits_and_gate():
    evidence = validate()
    assert all(evidence["contract14_audit"].values())
    assert all(evidence["contract15_audit"].values())
    assert all(evidence["contract15a_audit"].values())
    assert evidence["reason_coexistence"]
    assert all(value for key, value in evidence["implementation_readiness"].items()
               if key != "schema_revision_required")
    assert not evidence["implementation_readiness"]["schema_revision_required"]
    assert evidence["status"] == "TRACKING_TO_SAFETY_MAPPING_CONTRACT_REVALIDATED"
