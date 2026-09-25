"""AST and runtime ownership audit for the Phase 5 Revision 1 baseline."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from v0_2.control.inner_loop import LocalDPPLC
from v0_2.control.intent import IntentSupervisor
from v0_2.examples.phase5_validation import fixture_configs, run_scenario
from v0_2.measurement.local_sensor import MeasuredSnapshot
from v0_2.plant.controlled_loop import Disturbance, run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.safety.supervisor import SafetySupervisor

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/phase5_r1_ownership_audit.json"
PRODUCTION_FILES = (
    "v0_2/control/inner_loop.py",
    "v0_2/control/intent.py",
    "v0_2/control/outer_feedback.py",
    "v0_2/safety/supervisor.py",
    "v0_2/plant/controlled_loop.py",
    "v0_2/actuators/pump.py",
)


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def static_audit(root: Path = ROOT) -> dict[str, object]:
    command_constructors = []
    actuator_call_arguments = []
    forbidden_actuator_dependencies = []
    for relative in PRODUCTION_FILES:
        source = (root / relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) == "ActuatorCommand":
                command_constructors.append(relative)
            if (
                relative == "v0_2/plant/controlled_loop.py"
                and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "command"
            ):
                actuator_call_arguments.append(ast.unparse(node.args[0]))
        if relative == "v0_2/actuators/pump.py" and "SafetyDecision" in source:
            forbidden_actuator_dependencies.append("SafetyDecision")
    checks = {
        "plc_is_unique_actuator_command_constructor": command_constructors
        == ["v0_2/control/inner_loop.py"],
        "actuator_call_receives_plc_result_only": actuator_call_arguments
        == ["held_plc_result.actuator_command"],
        "actuator_has_no_safety_decision_dependency": not forbidden_actuator_dependencies,
        "safety_does_not_construct_actuator_command": "v0_2/safety/supervisor.py"
        not in command_constructors,
        "supervisor_does_not_construct_actuator_command": "v0_2/control/intent.py"
        not in command_constructors,
        "outer_feedback_does_not_construct_actuator_command": "v0_2/control/outer_feedback.py"
        not in command_constructors,
    }
    return {
        "checks": checks,
        "actuator_command_constructor_modules": command_constructors,
        "actuator_call_arguments": actuator_call_arguments,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def _runtime_summary(run) -> dict[str, object]:
    targets = {x.accepted_target_id: x for x in run.accepted_targets}
    envelopes = {x.envelope_id: x for x in run.safety_envelopes}
    cycles = {x.plc_cycle_id: x for x in run.plc_cycles}
    intents = {x.intent_id: x for x in run.fb_intents}
    lineage_ok = True
    for command in run.actuator_commands:
        cycle = cycles.get(command.plc_cycle_id)
        envelope = envelopes.get(command.safety_envelope_id)
        target = targets.get(command.accepted_target_id)
        if cycle is None or envelope is None or target is None:
            lineage_ok = False
            continue
        if target.fb_intent_id != "not_applicable" and target.fb_intent_id not in intents:
            lineage_ok = False
    producers = {x.producer_module for x in run.actuator_commands}
    return {
        "command_count": len(run.actuator_commands),
        "command_producers": sorted(producers),
        "all_commands_from_plc": producers == {"PLC"},
        "lineage_complete": lineage_ok,
        "safety_states": sorted({row.safety_state for row in run.rows}),
        "first_command": asdict(run.actuator_commands[0]),
        "last_command": asdict(run.actuator_commands[-1]),
    }


def _direct_safety_case(*, temperature=300.0, dp=20_000.0, speed=0.7, commanded=0.7):
    quality = tuple(
        (name, "VALID")
        for name in ("temperature", "dp", "flow", "pump_speed", "pump_status")
    )
    measured = MeasuredSnapshot(
        0,
        0,
        1,
        (("b0:die", temperature),),
        dp,
        0.1,
        speed,
        True,
        True,
        False,
        quality,
        measurement_record_id="measurement:direct-audit",
        actuator_state_id="actuator-state:direct-audit",
        hydraulic_solution_id="hydraulic-solution:direct-audit",
        source_ids=("actuator-state:direct-audit", "hydraulic-solution:direct-audit"),
    )
    *_, inner, policy = fixture_configs()
    target = IntentSupervisor(policy.fallback_dp_pa).accept_target(None, 0)
    decision = SafetySupervisor(policy).evaluate(
        0,
        measured,
        1_000_000_000,
        target.requested_dp_pa,
        commanded,
        accepted_target_id=target.accepted_target_id,
    )
    command = LocalDPPLC(inner).update(
        0, measured, target, decision.envelope, 1_000_000_000
    ).actuator_command
    return {
        "state": decision.state.value,
        "producer_module": command.producer_module,
        "speed": command.requested_speed,
        "mode": command.mode,
        "same_tick": command.created_ns == decision.envelope.created_ns,
    }


def runtime_audit() -> dict[str, object]:
    inner = {"kp": 0.000015, "ki": 0.000004, "kd": 0.0}
    outer = {"kp": 3000.0, "ki": 60.0, "kd": 0.0}
    normal = run_scenario("TUNE-01-load", inner=inner, outer=outer)
    plant, controls = physical_fixture(branch_count=2, power_each=120)
    fault = run_feedback(
        plant,
        controls,
        6_000_000_000,
        *fixture_configs(inner, outer),
        disturbances=(Disturbance(3_000_000_000, sensor_failures=("temperature",)),),
    )
    summaries = {"normal": _runtime_summary(normal), "fault": _runtime_summary(fault)}
    direct = {
        "degraded": _direct_safety_case(speed=0.2, commanded=0.9),
        "pressure_restriction": _direct_safety_case(dp=61_000),
        "protected": _direct_safety_case(temperature=345),
    }
    checks = {
        "normal_all_commands_from_plc": summaries["normal"]["all_commands_from_plc"],
        "fault_all_commands_from_plc": summaries["fault"]["all_commands_from_plc"],
        "normal_lineage_complete": summaries["normal"]["lineage_complete"],
        "fault_lineage_complete": summaries["fault"]["lineage_complete"],
        "fault_path_exercised": "FAULT" in summaries["fault"]["safety_states"],
        "degraded_path_through_plc": direct["degraded"]["state"] == "DEGRADED"
        and direct["degraded"]["producer_module"] == "PLC",
        "pressure_path_through_plc": direct["pressure_restriction"]["state"] == "FAULT"
        and direct["pressure_restriction"]["producer_module"] == "PLC",
        "protected_path_through_plc": direct["protected"]["state"] == "PROTECTED"
        and direct["protected"]["producer_module"] == "PLC",
        "emergency_paths_same_tick": direct["pressure_restriction"]["same_tick"]
        and direct["protected"]["same_tick"],
    }
    return {
        "checks": checks,
        "scenarios": summaries,
        "direct_safety_modes": direct,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def collect_audit() -> dict[str, object]:
    static = static_audit()
    runtime = runtime_audit()
    return {
        "schema": "phase5-r1-ownership-audit-v1",
        "static": static,
        "runtime": runtime,
        "status": "PASS" if static["status"] == runtime["status"] == "PASS" else "FAIL",
    }


def main() -> None:
    result = collect_audit()
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
