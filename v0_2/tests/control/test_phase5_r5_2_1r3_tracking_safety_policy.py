"""Scoped 15A tracking-to-Safety policy amendment; no production port."""

import json
from pathlib import Path

from v0_2.examples import phase5_r5_2_1r3_mapping_contract as mapping

ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_registration_predates_results_and_frozen_sources_unchanged():
    reg = read("phase5_r5_2_1r3_tracking_safety_policy_registration.json")
    contract = read("phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    evidence = read("phase5_r5_2_1r3_tracking_safety_policy_evidence.json")
    assert evidence["registration_sha256"] == mapping.sha(mapping.REGISTRATION)
    assert all(mapping.source_integrity(reg, contract).values())
    assert evidence["original_contract15_sha256"] == "1e93c50037e2b211494e98b30f951e638399e041d1c07b9c0daa2426fb00e073"
    assert contract["contract_14_sha256"] == "efd8d325753163b91170578ceeb3de02dafafbf8fb0a208a279c76c964d7b144"
    assert evidence["amendment_sha256"] == mapping.sha(mapping.AMENDMENT)
    assert evidence["machine_contract_sha256"] == mapping.sha(mapping.CONTRACT)
    assert evidence["production_source_hashes_unchanged"] is True


def test_exact_six_state_policy_and_new_reasons():
    contract = read("phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    states = contract["tracking_states"]
    assert len(states) == 6
    assert all(states[name]["severity"] == "NORMAL" and not states[name]["reason_codes"]
               for name in ("STEADY_TRACKING", "HANDOFF_PENDING", "TRACKING_PROGRESS",
                            "INSUFFICIENT_MEASUREMENT"))
    assert states["TRACKING_FAULT_SUSPECTED"]["severity"] == "DEGRADED"
    assert states["TRACKING_FAULT_SUSPECTED"]["reason_codes"] == ["ACTUATOR_TRACKING_SUSPECTED"]
    assert states["TRACKING_FAULT_SUSPECTED"]["restriction"] == "NONE"
    assert states["TRACKING_FAULT_CONFIRMED"]["severity"] == "FAULT"
    assert states["TRACKING_FAULT_CONFIRMED"]["reason_codes"] == ["ACTUATOR_TRACKING_CONFIRMED"]
    assert states["TRACKING_FAULT_CONFIRMED"]["restriction"] == "EXISTING_GENERIC_FAULT"
    assert "ACTUATOR_TRACKING_PENDING" not in {
        code for state in states.values() for code in state["reason_codes"]}
    assert set(contract["reason_codes"]) == {
        "ACTUATOR_TRACKING_SUSPECTED", "ACTUATOR_TRACKING_CONFIRMED", "ACTUATOR_TRACKING_PENDING"}


def test_a1_to_a16_reduction_reasons_and_recovery():
    evidence = read("phase5_r5_2_1r3_tracking_safety_policy_evidence.json")
    assert set(evidence["case_pass"]) == {f"A{i}" for i in range(1, 17)}
    assert all(evidence["case_pass"].values())
    output = evidence["case_outputs"]
    assert output["A2"]["final_safety"] == "NORMAL" and not output["A2"]["all_reasons"]
    assert output["A4"]["final_safety"] == "DEGRADED"
    assert output["A5"]["final_safety"] == "FAULT"
    assert output["A7"]["final_safety"] == "FAULT"
    assert output["A9"]["final_safety"] == "PROTECTED"
    assert output["A14"]["confirmed_latch_retained"] is True
    assert output["A16"]["restored_motion_clears_fault"] is False
    assert all(len(output[key]["all_reasons"]) == 2 for key in
               ("A7", "A8", "A9", "A10", "A11", "A12", "A14"))


def test_primary_reason_and_envelope_are_not_invented():
    contract = read("phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    evidence = read("phase5_r5_2_1r3_tracking_safety_policy_evidence.json")
    assert contract["primary_reason"]["current_api_has_primary_field"] is False
    assert all(out["primary_reason"] is None for out in evidence["case_outputs"].values())
    assert all(not out["tracking_specific_new_restriction"] for out in evidence["case_outputs"].values())
    assert "EXISTING_GENERIC_FAULT" in evidence["case_outputs"]["A5"]["restriction_sources"]
    assert "PRESSURE_FAULT" in evidence["case_outputs"]["A7"]["restriction_sources"]
    assert evidence["case_outputs"]["A6"]["all_reasons"] == ["CRITICAL_LOCAL_SENSOR_INVALID"]
    assert all(evidence["reason_checks"].values())


def test_contract14_15_ownership_scope_and_no_production_change():
    contract = read("phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    evidence = read("phase5_r5_2_1r3_tracking_safety_policy_evidence.json")
    assert contract["hierarchy_low_to_high"] == [
        "NORMAL", "FF_DISABLED", "DEGRADED", "DERATE_REQUESTED", "PROTECTED", "FAULT"]
    assert all(evidence["contract14_audit"].values())
    assert all(evidence["contract15_compatibility"].values())
    assert evidence["production_safety_changed"] is False
    assert evidence["r2r_started"] is False
    assert evidence["r5_3r_started"] is False
    assert evidence["phase6_started"] is False
    assert evidence["status"] == "TRACKING_SAFETY_POLICY_AMENDMENT_SPECIFIED_AND_VALIDATED"
    assert (ROOT / "docs/results/phase5_r5_2_1r3_tracking_safety_policy.png").is_file()
