"""R5.2.1 pre-validation stop and frozen-source audit; no production port."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRATION = ROOT / "phase5_r5_2_1_continuous_tracking_semantics_registration.json"
SPEC = ROOT / "phase5_r5_2_1_continuous_tracking_semantics_spec.json"
EVIDENCE = ROOT / "phase5_r5_2_1_continuous_tracking_semantics_evidence.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_registration_precedes_specification_and_evidence():
    registration = _read(REGISTRATION)
    spec = _read(SPEC)
    evidence = _read(EVIDENCE)
    assert spec["registration_sha256"] == _sha(REGISTRATION)
    assert evidence["registration_sha256"] == _sha(REGISTRATION)
    assert evidence["machine_spec_sha256"] == _sha(SPEC)
    assert registration["production_change_authorized"] is False


def test_historical_sources_and_production_files_unchanged():
    registration = _read(REGISTRATION)
    sources = {
        "r5_registration": "phase5_r5_directional_pi_registration.json",
        "r5_evidence": "phase5_r5_directional_pi_evidence.json",
        "r5_candidate": "phase5_r5_directional_pi_candidate_baseline.json",
        "r5_1_registration": "phase5_r5_1_safety_handoff_audit_registration.json",
        "r5_1_evidence": "phase5_r5_1_safety_handoff_audit_evidence.json",
        "r5_2_registration": "phase5_r5_2_silent_tracking_fault_registration.json",
        "r5_2_evidence": "phase5_r5_2_silent_tracking_fault_evidence.json",
    }
    for key, name in sources.items():
        assert _sha(ROOT / name) == registration["source_sha256"][key]
    production = {
        "safety": "v0_2/safety/supervisor.py",
        "directional_outer": "v0_2/control/directional_outer.py",
        "outer_feedback": "v0_2/control/outer_feedback.py",
        "inner_loop": "v0_2/control/inner_loop.py",
        "pid": "v0_2/control/pid.py",
        "actuator": "v0_2/actuators/pump.py",
        "plant": "v0_2/plant/controlled_loop.py",
        "sensor": "v0_2/measurement/local_sensor.py",
    }
    for key, name in production.items():
        assert _sha(ROOT / name) == registration["frozen_production_sha256"][key]


def test_specification_does_not_claim_unsupported_validation():
    registration = _read(REGISTRATION)
    spec = _read(SPEC)
    evidence = _read(EVIDENCE)
    assert len(registration["synthetic_sequences"]) == 16
    assert set(evidence["synthetic_sequence_results"]) == {f"S{i}" for i in range(1, 17)}
    assert set(evidence["synthetic_sequence_results"].values()) == {"NOT_RUN_PRE_VALIDATION_STOP"}
    assert len(spec["states"]) == 6
    assert len(spec["invariants"]) == 8
    assert any(guard.startswith("UNRESOLVED") for guard in spec["guards"].values())
    assert evidence["status"] == "TRACKING_SEMANTICS_REQUIRE_CALIBRATION_PARAMETERS"
    assert spec["production_port_allowed"] is False


def test_information_and_ownership_boundary():
    registration = _read(REGISTRATION)
    spec = _read(SPEC)
    allowed = " ".join(registration["allowed_information"]).lower()
    for forbidden in ("actual", "fault identity", "scenario identity", "future data", "plant truth"):
        assert forbidden not in allowed
    assert all("ActuatorCommand" not in state for state in spec["states"])
    assert spec["recovery_constraints"].startswith("No qualifier output clears top-level FAULT")
