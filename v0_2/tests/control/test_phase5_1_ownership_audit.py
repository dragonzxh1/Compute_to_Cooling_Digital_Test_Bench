from v0_2.examples.phase5_1_ownership_audit import audit_ownership


def test_frozen_phase5_baseline_records_actuation_ownership_blocker():
    result = audit_ownership()

    assert result["integrity"]["registration_match"] is True
    assert result["integrity"]["control_core_match"] is True
    assert result["findings"]["plc_receives_forced_speed"] is True
    assert result["findings"]["actuator_call_directly_selects_safety_forced_speed"] is True
    assert result["findings"]["actuator_call_uses_plc_return_exclusively"] is False
    assert result["status"] == "ACTUATION_OWNERSHIP_CONTRACT_VIOLATION"
    assert result["qualification_gate"] == "BLOCKED"
