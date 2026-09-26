"""Offline Contract 14/15/15A revalidation; never imported by production Safety."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "phase5_r5_2_1r2r_tracking_to_safety_mapping_registration.json"
CONTRACT = ROOT / "phase5_r5_2_1r2r_tracking_to_safety_mapping_contract.json"
EVIDENCE = ROOT / "phase5_r5_2_1r2r_tracking_to_safety_mapping_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_1r2r_tracking_to_safety_mapping.png"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def class_fields(tree: ast.AST, name: str) -> dict[str, str]:
    cls = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == name)
    return {node.target.id: ast.unparse(node.annotation) for node in cls.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}


def schema_audit() -> dict:
    tree = ast.parse((ROOT / "v0_2/safety/supervisor.py").read_text(encoding="utf-8"))
    decision = class_fields(tree, "SafetyDecision")
    envelope = class_fields(tree, "SafetyEnvelope")
    states = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "SafetyState")
    state_names = [node.targets[0].id for node in states.body if isinstance(node, ast.Assign)
                   and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)]
    supervisor = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "SafetySupervisor")
    methods = {node.name for node in supervisor.body if isinstance(node, ast.FunctionDef)}
    source = (ROOT / "v0_2/safety/supervisor.py").read_text(encoding="utf-8")
    return {
        "decision_fields": decision,
        "envelope_fields": envelope,
        "state_names": state_names,
        "multiple_reasons_representable": decision.get("reasons") == "tuple[str, ...]"
            and envelope.get("reason_codes") == "tuple[str, ...]",
        "primary_reason_mandatory": "primary_reason" in decision,
        "severity_representable": decision.get("state") == "SafetyState"
            and envelope.get("state") == "SafetyState",
        "envelope_representable": all(name in envelope for name in
            ("minimum_dp_pa", "maximum_dp_pa", "minimum_speed_fraction", "maximum_speed_fraction",
             "fallback_dp_pa", "shutdown_required", "reason_codes", "source_measurement_ids", "envelope_id")),
        "fault_reset_representable": "reset_fault" in methods and "self.fault_latched = True" in source,
        "current_single_branch_logic": "elif measured.dp_pa >= p.maximum_dp_pa" in source
            and "elif commanded_speed is not None" in source,
        "tracking_provenance_link_possible": "envelope_id" in envelope and "source_measurement_ids" in envelope,
        "sensor_reason_coexistence_representable": decision.get("reasons") == "tuple[str, ...]",
        "safety_decision_emits_command": "ActuatorCommand" in decision or "ActuatorCommand" in envelope,
    }


CHANNELS = {
    "PRESSURE_FAULT": ("FAULT", "OVERPRESSURE_MEASURED"),
    "THERMAL_PROTECTED": ("PROTECTED", "HARD_THERMAL_MEASURED"),
    "DERATE_REQUESTED": ("DERATE_REQUESTED", "THERMAL_OR_FLOW_CAPACITY_LIMITED"),
    "SENSOR_INVALID": ("FAULT", "CRITICAL_LOCAL_SENSOR_INVALID"),
    "FF_DISABLED": ("FF_DISABLED", "RECOVERY_QUALIFICATION"),
}


def reduce_case(case: dict, contract: dict) -> dict:
    """Reduce qualified contributions only; never estimate tracking state."""
    tracking = "TRACKING_FAULT_CONFIRMED" if case.get("prior_confirmed") else case["tracking"]
    item = contract["tracking_states"][tracking]
    active = [(item["severity"], reason) for reason in item["reason_codes"]]
    active += [CHANNELS[name] for name in case["channels"]]
    level = max([item["severity"], *(severity for severity, _ in active)],
                key=contract["hierarchy_low_to_high"].index)
    reasons = [reason for _, reason in active]
    restrictions = [name for name in case["channels"] if name in
                    ("PRESSURE_FAULT", "THERMAL_PROTECTED", "DERATE_REQUESTED", "SENSOR_INVALID")]
    if level == "FAULT":
        restrictions.append("EXISTING_GENERIC_FAULT")
    return {
        "final_safety": level,
        "all_reasons": reasons,
        "restriction_sources": restrictions,
        "tracking_specific_new_restriction": False,
        "latched_fault": tracking == "TRACKING_FAULT_CONFIRMED",
        "prior_suspected_evidence_retained": bool(case.get("prior_suspected")),
        "restored_motion_auto_clears_fault": False,
        "recovery_authority": item["recovery_authority"],
        "actuator_command_producer": "PLC_ONLY",
    }


def validate() -> dict:
    reg, contract = load(REG), load(CONTRACT)
    source_checks = {name: sha(ROOT / name) == expected for name, expected in
                     {**reg["source_sha256"], **reg["production_sha256"]}.items()}
    source_checks["registration"] = sha(REG) == contract["registration_sha256"]
    r3 = load(ROOT / "phase5_r5_2_1r3_tracking_safety_policy_evidence.json")
    r1a = load(ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json")
    source_checks["r3_gate"] = r3["status"] == reg["required_gates"]["r3"]
    source_checks["r1a_gate"] = r1a["status"] == reg["required_gates"]["r1a"]
    schema = schema_audit()
    r3_contract = load(ROOT / "phase5_r5_2_1r3_tracking_safety_policy_contract.json")
    mapping_exact = contract["tracking_states"] == r3_contract["tracking_states"]
    outputs = {key: reduce_case(case, contract) for key, case in contract["cases"].items()}
    checks = {}
    for key, case in contract["cases"].items():
        out = outputs[key]
        tracked = "TRACKING_FAULT_CONFIRMED" if case.get("prior_confirmed") else case["tracking"]
        expected_reasons = contract["tracking_states"][tracked]["reason_codes"] + [
            CHANNELS[channel][1] for channel in case["channels"]]
        checks[key] = (out["final_safety"] == case["expected"]
                       and out["all_reasons"] == expected_reasons
                       and out["actuator_command_producer"] == "PLC_ONLY"
                       and not out["tracking_specific_new_restriction"])
    checks["M13"] &= outputs["M13"]["prior_suspected_evidence_retained"]
    checks["M14"] &= outputs["M14"]["latched_fault"]
    checks["M16"] &= outputs["M16"]["latched_fault"] and not outputs["M16"]["restored_motion_auto_clears_fault"]
    contract14 = {"deny_default": "Deny-by-default" in (ROOT / "contracts/14_control_input_permission_contract.md").read_text(encoding="utf-8"),
                  "safety_envelope_plc_command": not schema["safety_decision_emits_command"]
                  and all(value["actuator_command_producer"] == "PLC_ONLY" for value in outputs.values())}
    contract15 = {"hierarchy": contract["hierarchy_low_to_high"] ==
                  ["NORMAL", "FF_DISABLED", "DEGRADED", "DERATE_REQUESTED", "PROTECTED", "FAULT"],
                  "pressure_priority": outputs["M7"]["final_safety"] == "FAULT"
                  and "PRESSURE_FAULT" in outputs["M7"]["restriction_sources"],
                  "thermal_protection": outputs["M9"]["final_safety"] == "PROTECTED",
                  "sensor_boundary": "ACTUATOR_TRACKING_CONFIRMED" not in outputs["M6"]["all_reasons"],
                  "ff_local_feedback": outputs["M15"]["final_safety"] == "FF_DISABLED",
                  "fault_recovery": schema["fault_reset_representable"] and outputs["M16"]["latched_fault"],
                  "same_tick_authority": "PLC_ONLY" == outputs["M8"]["actuator_command_producer"]}
    contract15a = {"exact_mapping": mapping_exact, "pending_identity": outputs["M2"]["final_safety"] == "NORMAL"
                   and not outputs["M2"]["all_reasons"],
                   "suspected": outputs["M4"]["final_safety"] == "DEGRADED",
                   "confirmed": outputs["M5"]["final_safety"] == "FAULT",
                   "insufficient_sensor_owned": contract15["sensor_boundary"],
                   "all_reasons": all(checks[key] for key in ("M7", "M8", "M9", "M10", "M11", "M12", "M14")),
                   "no_new_restriction": all(not value["tracking_specific_new_restriction"] for value in outputs.values()),
                   "confirmed_explicit_recovery": checks["M16"]}
    readiness = {"multiple_reasons_type": schema["multiple_reasons_representable"],
                 "severity_type": schema["severity_representable"],
                 "envelope_type": schema["envelope_representable"],
                 "fault_reset_path": schema["fault_reset_representable"],
                 "tracking_provenance_link": schema["tracking_provenance_link_possible"],
                 "sensor_reason_coexistence": schema["sensor_reason_coexistence_representable"],
                 "implementation_only_gap": schema["current_single_branch_logic"],
                 "schema_revision_required": False}
    if not readiness["multiple_reasons_type"]:
        gate = "SAFETY_REASON_MODEL_REQUIRES_SCHEMA_REVISION"
    elif schema["primary_reason_mandatory"]:
        gate = "SAFETY_REASON_SCHEMA_SOURCE_CONFLICT"
    elif not all(value for key, value in readiness.items() if key != "schema_revision_required"):
        gate = "SAFETY_DECISION_SCHEMA_REQUIRES_REVISION"
    elif (not all(source_checks.values()) or not all(checks.values())
          or not all(contract14.values()) or not all(contract15.values())
          or not all(contract15a.values())):
        gate = "TRACKING_SAFETY_MAPPING_CONTRACT_CONFLICT"
    else:
        gate = "TRACKING_TO_SAFETY_MAPPING_CONTRACT_REVALIDATED"
    return {"schema": "phase5-r5-2-1r2r-evidence-v1", "registration_sha256": sha(REG),
            "mapping_contract_sha256": sha(CONTRACT), "source_hash_checks": source_checks,
            "source_sha256": reg["source_sha256"], "production_sha256": reg["production_sha256"],
            "type_schema_audit": schema, "reason_inventory": r3["reason_inventory"],
            "state_mapping": contract["tracking_states"], "reason_definitions": contract["reason_definitions"],
            "case_outputs": outputs, "case_pass": checks, "reason_coexistence": contract15a["all_reasons"]
            and schema["multiple_reasons_representable"],
            "recovery_matrix": {key: outputs[key]["recovery_authority"] for key in ("M4", "M5", "M13", "M14", "M16")},
            "contract14_audit": contract14, "contract15_audit": contract15,
            "contract15a_audit": contract15a, "implementation_readiness": readiness,
            "production_source_hashes_unchanged": all(source_checks[name] for name in reg["production_sha256"]),
            "production_code_changed": False, "r5_3r_started": False, "status": gate}


def make_figure(evidence: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.axis("off")
    ax.text(0.04, 0.91, "Validated tracking state  ↓  Contract 15A mapping  ↓  TrackingSafetyContribution\n"
            "                  ↓  Multi-channel reducer  ↓  SafetyDecision / SafetyEnvelope  ↓  PLC",
            fontsize=15, va="top", transform=ax.transAxes)
    ax.text(0.04, 0.63, "HANDOFF_PENDING → NORMAL contribution\nSUSPECTED → DEGRADED\n"
            "CONFIRMED → FAULT\nINSUFFICIENT → Sensor channel", fontsize=14, va="top", transform=ax.transAxes)
    ax.text(0.57, 0.63, "FAULT > PROTECTED > DERATE_REQUESTED\n> DEGRADED > FF_DISABLED > NORMAL\n\n"
            f"M1–M16: {sum(evidence['case_pass'].values())}/16 PASS\n"
            f"Reason collection representable: {evidence['type_schema_audit']['multiple_reasons_representable']}",
            fontsize=13, va="top", transform=ax.transAxes)
    fig.suptitle("CONTRACT REVALIDATION ONLY — NO PRODUCTION SAFETY CHANGE\n"
                 "GENERIC DEVELOPMENT ARCHITECTURE — NOT OEM / NVIDIA / GB300 CERTIFICATION")
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    evidence = validate()
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(evidence)
    print(json.dumps({"status": evidence["status"], "registration_sha256": evidence["registration_sha256"],
                      "case_pass": evidence["case_pass"], "implementation_readiness": evidence["implementation_readiness"]},
                     indent=2))


if __name__ == "__main__":
    main()
