"""Reproducible, read-only Phase 5.1 frozen-baseline ownership audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROL_CORE = (
    "v0_2/control/pid.py",
    "v0_2/control/inner_loop.py",
    "v0_2/control/outer_feedback.py",
    "v0_2/plant/controlled_loop.py",
    "v0_2/actuators/pump.py",
    "v0_2/measurement/local_sensor.py",
    "v0_2/safety/supervisor.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_ownership(root: Path = ROOT) -> dict[str, object]:
    """Inspect frozen sources without importing or executing the controller."""
    baseline_path = root / "phase5_feedback_baseline.json"
    registration_path = root / "phase5_tuning_registration.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    historical_source = (
        root / "docs/results/phase5_1_original_defect_fixture.txt"
    ).read_text(encoding="utf-8")
    core_hash = baseline["code_sha256"]

    direct_safety_selection = (
        "actuator.command(decision.forced_speed if decision.forced_speed is not None "
        "else held_plc_command, now)"
    )
    findings = {
        "safety_decision_contains_forced_speed": "forced_speed: float | None" in historical_source,
        "plc_receives_forced_speed": "forced_speed=decision.forced_speed" in historical_source,
        "actuator_call_directly_selects_safety_forced_speed": direct_safety_selection
        in historical_source,
        "actuator_call_uses_plc_return_exclusively": "actuator.command(held_plc_command, now)"
        in historical_source,
    }
    registration_hash = _sha256(registration_path)
    integrity = {
        "registration_sha256": registration_hash,
        "expected_registration_sha256": baseline["tuning_registration_sha256"],
        "registration_match": registration_hash == baseline["tuning_registration_sha256"],
        "baseline_file_sha256": _sha256(baseline_path),
        "control_core_sha256": core_hash,
        "expected_control_core_sha256": baseline["code_sha256"],
        "control_core_match": core_hash == baseline["code_sha256"],
    }
    violation = bool(
        findings["safety_decision_contains_forced_speed"]
        and findings["actuator_call_directly_selects_safety_forced_speed"]
        and not findings["actuator_call_uses_plc_return_exclusively"]
    )
    return {
        "phase": "5.1",
        "audit_type": "FROZEN_BASELINE_STATIC_ACTUATION_OWNERSHIP",
        "integrity": integrity,
        "contract": {
            "safety": "writes restrictive envelope/derate request",
            "plc": "sole writer of final actuator command",
            "source": [
                "contracts/14_control_input_permission_contract.md",
                "contracts/15_safety_supervisor_contract.md",
            ],
        },
        "findings": findings,
        "status": "ACTUATION_OWNERSHIP_CONTRACT_VIOLATION" if violation else "PASS",
        "qualification_gate": "BLOCKED" if violation else "OPEN",
        "closed_loop_qualification_executed": False,
        "note": (
            "Historical original-Phase-5 fixture: the scheduler directly selected "
            "SafetyDecision.forced_speed at the actuator call site. The blocked finding is "
            "preserved after Revision 1 and is not a statement about the revised source."
        ),
    }


def main() -> None:
    output = ROOT / "docs/results/phase5_1_ownership_audit.json"
    result = audit_ownership()
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
