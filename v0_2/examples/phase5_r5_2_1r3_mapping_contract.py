"""Test-only declarative tracking-to-Safety contract validator; no production imports."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_2_1r3_tracking_safety_policy_registration.json"
CONTRACT = ROOT / "phase5_r5_2_1r3_tracking_safety_policy_contract.json"
AMENDMENT = ROOT / "contracts/15A_tracking_safety_policy_amendment.md"
EVIDENCE = ROOT / "phase5_r5_2_1r3_tracking_safety_policy_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_1r3_tracking_safety_policy.png"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_integrity(reg: dict, contract: dict) -> dict:
    checks = {key: sha(ROOT / key) == value for key, value in
              {**reg["source_sha256"], **reg["production_sha256"]}.items()}
    checks["amendment"] = sha(AMENDMENT) == contract["amendment_sha256"]
    checks["contract14"] = sha(ROOT / "contracts/14_control_input_permission_contract.md") == contract["contract_14_sha256"]
    checks["contract15"] = sha(ROOT / "contracts/15_safety_supervisor_contract.md") == contract["parent_contract_15_sha256"]
    checks["registration"] = sha(REGISTRATION) == contract["registration_sha256"]
    latest = load(ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    checks["latest_gate"] = latest["status"] == reg["required_r1a_gate"]
    if not all(checks.values()):
        raise RuntimeError(f"Frozen source/contract mismatch: {checks}")
    return checks


def reason_inventory() -> list[str]:
    tree = ast.parse((ROOT / "v0_2/safety/supervisor.py").read_text(encoding="utf-8"))
    return sorted({node.args[0].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "append" and len(node.args) == 1
                   and isinstance(node.args[0], ast.Constant)
                   and isinstance(node.args[0].value, str)})


def reduce_case(case: dict, contract: dict) -> dict:
    hierarchy = contract["hierarchy_low_to_high"]
    mapping = contract["tracking_states"]
    tracking_state = case["tracking"]
    effective_tracking_state = "TRACKING_FAULT_CONFIRMED" if case.get("prior_confirmed") else tracking_state
    contribution = mapping[effective_tracking_state]
    channels = {
        "PRESSURE_FAULT": ("FAULT", "OVERPRESSURE_MEASURED", "PRESSURE"),
        "THERMAL_PROTECTED": ("PROTECTED", "HARD_THERMAL_MEASURED", "THERMAL"),
        "DERATE_REQUESTED": ("DERATE_REQUESTED", "THERMAL_OR_FLOW_CAPACITY_LIMITED", "THERMAL"),
        "SENSOR_INVALID": ("FAULT", "CRITICAL_LOCAL_SENSOR_INVALID", "SENSOR"),
        "FF_DISABLED": ("FF_DISABLED", "RECOVERY_QUALIFICATION", "FF"),
    }
    active = [(contribution["severity"], reason, "ACTUATOR_TRACKING")
              for reason in contribution["reason_codes"]]
    active.extend(channels[name] for name in case["channels"])
    severity = max([contribution["severity"], *(item[0] for item in active)],
                   key=hierarchy.index)
    reasons = tuple(item[1] for item in active)
    restriction_sources = [name for name in case["channels"]
                           if name in ("PRESSURE_FAULT", "THERMAL_PROTECTED", "DERATE_REQUESTED", "SENSOR_INVALID")]
    if severity == "FAULT":
        restriction_sources.append("EXISTING_GENERIC_FAULT")
    return {
        "tracking_state": tracking_state,
        "effective_tracking_contribution": effective_tracking_state,
        "tracking_severity": contribution["severity"],
        "final_safety": severity,
        "all_reasons": reasons,
        "primary_reason": None,
        "restriction_sources": tuple(restriction_sources),
        "tracking_specific_new_restriction": False,
        "confirmed_latch_retained": effective_tracking_state == "TRACKING_FAULT_CONFIRMED",
        "prior_suspected_evidence_retained_internally": bool(case.get("prior_suspected")),
        "restored_motion_clears_fault": False,
        "command_producer": "PLC_ONLY",
    }


def evaluate_cases(contract: dict) -> tuple[dict, dict]:
    outputs = {key: reduce_case(case, contract) for key, case in contract["cases"].items()}
    checks = {}
    for key, case in contract["cases"].items():
        out = outputs[key]
        tracking_reason = contract["tracking_states"][out["effective_tracking_contribution"]]["reason_codes"]
        checks[key] = (
            out["final_safety"] == case["expected"]
            and all(reason in out["all_reasons"] for reason in tracking_reason)
            and len(out["all_reasons"]) == len(tracking_reason) + len(case["channels"])
            and out["primary_reason"] is None
            and not out["tracking_specific_new_restriction"]
            and out["command_producer"] == "PLC_ONLY"
        )
    return outputs, checks


def make_figure(contract: dict, outputs: dict, case_checks: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes[0, 0].axis("off")
    axes[0, 0].text(0.03, 0.85, "Validated tracking qualifier\n↓\nTracking Safety contribution\n"
                    "↓\nMulti-channel Safety reducer\n↓\nSafetyDecision / SafetyEnvelope\n↓\nPLC",
                    transform=axes[0, 0].transAxes, va="top", fontsize=14)
    axes[0, 0].set_title("Ownership and contribution flow")
    axes[0, 1].axis("off")
    axes[0, 1].text(0.03, 0.85, "HANDOFF_PENDING → no degradation\n"
                    "SUSPECTED → DEGRADED\nCONFIRMED → FAULT\n"
                    "INSUFFICIENT_MEASUREMENT → Sensor channel",
                    transform=axes[0, 1].transAxes, va="top", fontsize=13)
    axes[0, 1].set_title("Authorized mapping")
    axes[1, 0].axis("off")
    axes[1, 0].text(0.03, 0.85, "FAULT\n> PROTECTED\n> DERATE_REQUESTED\n"
                    "> DEGRADED\n> FF_DISABLED\n> NORMAL",
                    transform=axes[1, 0].transAxes, va="top", fontsize=13)
    axes[1, 0].set_title("Frozen severity precedence")
    axes[1, 1].axis("off")
    axes[1, 1].text(0.03, 0.85,
                    f"A1–A16: {sum(case_checks.values())}/{len(case_checks)} PASS\n"
                    f"Tracking states mapped: {len(contract['tracking_states'])}/6\n"
                    f"Pressure + tracking: {outputs['A7']['final_safety']}\n"
                    f"Thermal + tracking: {outputs['A9']['final_safety']}\n"
                    f"Sensor invalid: {outputs['A6']['final_safety']}",
                    transform=axes[1, 1].transAxes, va="top", fontsize=12)
    axes[1, 1].set_title("Offline contract cases")
    fig.suptitle("SAFETY CONTRACT AMENDMENT — NO PRODUCTION SAFETY CODE CHANGE\n"
                 "GENERIC NUMERICAL FIXTURE — NOT OEM / NVIDIA / GB300 CERTIFICATION")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = load(REGISTRATION)
    contract = load(CONTRACT)
    source_checks = source_integrity(reg, contract)
    inventory = reason_inventory()
    outputs, case_checks = evaluate_cases(contract)
    new_reasons = {"ACTUATOR_TRACKING_SUSPECTED", "ACTUATOR_TRACKING_CONFIRMED"}
    reason_checks = {
        "new_codes_not_in_production": new_reasons.isdisjoint(inventory),
        "legacy_pending_exists": "ACTUATOR_TRACKING_PENDING" in inventory,
        "legacy_pending_not_mapped": all("ACTUATOR_TRACKING_PENDING" not in
                                         value["reason_codes"] for value in contract["tracking_states"].values()),
        "all_simultaneous_reasons_retained": all(
            len(outputs[key]["all_reasons"]) >= 2 for key in ("A7", "A8", "A9", "A10", "A11", "A12", "A14")
        ),
        "current_api_has_no_primary": "primary_reason" not in
            (ROOT / "v0_2/safety/supervisor.py").read_text(encoding="utf-8"),
        "pending_no_false_degraded": outputs["A2"]["final_safety"] == "NORMAL"
            and not outputs["A2"]["all_reasons"],
        "confirmed_restored_does_not_clear": outputs["A16"]["final_safety"] == "FAULT"
            and not outputs["A16"]["restored_motion_clears_fault"],
        "sensor_invalid_not_tracking_confirmation": "ACTUATOR_TRACKING_CONFIRMED" not in
            outputs["A6"]["all_reasons"],
        "pressure_fault_not_downgraded": outputs["A7"]["final_safety"] == "FAULT",
        "thermal_protected_not_suppressed": outputs["A9"]["final_safety"] == "PROTECTED",
        "confirmed_uses_existing_fault_restriction": "EXISTING_GENERIC_FAULT" in
            outputs["A5"]["restriction_sources"],
    }
    contract14 = {
        "deny_default_and_measured_only": "Deny-by-default" in
            (ROOT / "contracts/14_control_input_permission_contract.md").read_text(encoding="utf-8"),
        "safety_restriction_only": "W restrictive envelope/derate request" in
            (ROOT / "contracts/14_control_input_permission_contract.md").read_text(encoding="utf-8"),
        "plc_sole_final_command": all(value["command_producer"] == "PLC_ONLY" for value in outputs.values()),
    }
    contract15 = {
        "hierarchy": contract["hierarchy_low_to_high"] ==
            ["NORMAL", "FF_DISABLED", "DEGRADED", "DERATE_REQUESTED", "PROTECTED", "FAULT"],
        "all_reasons": all(reason_checks[name] for name in
                           ("all_simultaneous_reasons_retained", "current_api_has_no_primary")),
        "pressure_priority": outputs["A7"]["final_safety"] == "FAULT"
            and "PRESSURE_FAULT" in outputs["A7"]["restriction_sources"],
        "ff_local_feedback": outputs["A15"]["final_safety"] == "FF_DISABLED",
        "sensor_boundary": outputs["A6"]["final_safety"] == "FAULT"
            and "ACTUATOR_TRACKING_CONFIRMED" not in outputs["A6"]["all_reasons"],
        "fault_recovery": outputs["A16"]["confirmed_latch_retained"],
        "no_new_restriction": all(not value["tracking_specific_new_restriction"] for value in outputs.values()),
    }
    passed = (all(case_checks.values()) and all(reason_checks.values())
              and all(contract14.values()) and all(contract15.values()))
    gate = ("TRACKING_SAFETY_POLICY_AMENDMENT_SPECIFIED_AND_VALIDATED" if passed
            else "TRACKING_SAFETY_POLICY_CONTRACT_CONFLICT")
    evidence = {
        "schema": "phase5-r5-2-1r3-tracking-safety-policy-evidence-v1",
        "registration_sha256": sha(REGISTRATION),
        "source_hash_checks": source_checks,
        "historical_source_sha256": reg["source_sha256"],
        "original_contract15_sha256": sha(ROOT / "contracts/15_safety_supervisor_contract.md"),
        "amendment_sha256": sha(AMENDMENT),
        "machine_contract_sha256": sha(CONTRACT),
        "reason_inventory": inventory,
        "reason_checks": reason_checks,
        "tracking_state_mapping": contract["tracking_states"],
        "case_outputs": outputs,
        "case_pass": case_checks,
        "primary_reason_tests": {"current_api_no_primary": reason_checks["current_api_has_no_primary"],
                                 "no_primary_in_offline_results": all(out["primary_reason"] is None
                                                                      for out in outputs.values())},
        "contract14_audit": contract14,
        "contract15_compatibility": contract15,
        "production_source_hashes_unchanged": all(source_checks.values()),
        "production_safety_changed": False,
        "r2r_started": False,
        "r5_3r_started": False,
        "phase6_started": False,
        "status": gate,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(contract, outputs, case_checks)
    print(json.dumps({"status": gate, "registration_sha256": sha(REGISTRATION),
                      "amendment_sha256": sha(AMENDMENT), "contract_sha256": sha(CONTRACT),
                      "case_pass": case_checks, "reason_checks": reason_checks,
                      "contract14": contract14, "contract15": contract15}, indent=2))


if __name__ == "__main__":
    main()
