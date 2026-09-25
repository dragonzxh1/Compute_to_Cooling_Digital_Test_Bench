import hashlib
import json
from pathlib import Path

import pytest
from v0_2.actuators.pump import PumpActuator
from v0_2.control.inner_loop import ActuatorCommand, LocalDPPLC
from v0_2.control.intent import IntentSupervisor
from v0_2.examples.phase5_r1_ownership_audit import collect_audit, static_audit
from v0_2.examples.phase5_validation import fixture_configs, run_scenario
from v0_2.measurement.local_sensor import MeasuredSnapshot
from v0_2.plant.controlled_loop import Disturbance, run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.safety.supervisor import SafetyState, SafetySupervisor
from v0_2.thermal.validity import ThermalError

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL_REGISTRATION_SHA = "9a937de41a8466f4a6f33a06de899929576a3653217901084a2fb7675f0fe00f"
ORIGINAL_BASELINE_SHA = "b14281edc630b49de1ddcfbff1894cfe129f75e1c6b891786dbeae02de73b033"
ORIGINAL_CORE_SHA = "092b3ff035da69a95294543cdf716e4a025f506ab213543d1a640ed1d10db6d8"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _measured(*, temperature=300.0, dp=20_000.0, valid=True):
    quality = tuple(
        (name, "VALID" if valid else "MISSING")
        for name in ("temperature", "dp", "flow", "pump_speed", "pump_status")
    )
    return MeasuredSnapshot(
        0,
        0,
        1,
        (("b0:die", temperature),) if valid else (),
        dp if valid else None,
        0.1 if valid else None,
        0.7 if valid else None,
        True if valid else None,
        True if valid else None,
        False if valid else None,
        quality,
        measurement_record_id="measurement:test",
        actuator_state_id="actuator-state:test",
        hydraulic_solution_id="hydraulic-solution:test",
        source_ids=("actuator-state:test", "hydraulic-solution:test"),
    )


def _restricted_cycle(measured):
    *_, inner, policy = fixture_configs()
    target = IntentSupervisor(policy.fallback_dp_pa).accept_target(None, 0)
    decision = SafetySupervisor(policy).evaluate(
        0,
        measured,
        1_000_000_000,
        target.requested_dp_pa,
        0.7,
        accepted_target_id=target.accepted_target_id,
    )
    result = LocalDPPLC(inner).update(0, measured, target, decision.envelope, 1_000_000_000)
    return policy, decision, result


def test_original_baseline_artifacts_remain_byte_identical():
    assert _sha(ROOT / "phase5_tuning_registration.json") == ORIGINAL_REGISTRATION_SHA
    assert _sha(ROOT / "phase5_feedback_baseline.json") == ORIGINAL_BASELINE_SHA
    baseline = json.loads((ROOT / "phase5_feedback_baseline.json").read_text(encoding="utf-8"))
    assert baseline["code_sha256"] == ORIGINAL_CORE_SHA


def test_historical_blocked_audit_still_reproduces_original_defect():
    result = json.loads(
        (ROOT / "docs/results/phase5_1_ownership_audit.json").read_text(encoding="utf-8")
    )
    fixture = (ROOT / "docs/results/phase5_1_original_defect_fixture.txt").read_text(
        encoding="utf-8"
    )
    assert result["status"] == "ACTUATION_OWNERSHIP_CONTRACT_VIOLATION"
    assert "decision.forced_speed if decision.forced_speed is not None" in fixture


def test_static_unique_writer_ast_gate():
    result = static_audit()
    assert result["status"] == "PASS"
    assert result["actuator_command_constructor_modules"] == ["v0_2/control/inner_loop.py"]
    assert result["actuator_call_arguments"] == ["held_plc_result.actuator_command"]


def test_runtime_unique_writer_normal_and_fault_modes():
    result = collect_audit()["runtime"]
    assert result["status"] == "PASS"
    assert result["scenarios"]["normal"]["command_producers"] == ["PLC"]
    assert result["scenarios"]["fault"]["command_producers"] == ["PLC"]


def test_normal_mode_lineage_is_complete():
    run = run_scenario(
        "TUNE-01-load",
        inner={"kp": 0.000015, "ki": 0.000004, "kd": 0.0},
        outer={"kp": 3000.0, "ki": 60.0, "kd": 0.0},
    )
    cycles = {x.plc_cycle_id for x in run.plc_cycles}
    envelopes = {x.envelope_id for x in run.safety_envelopes}
    targets = {x.accepted_target_id for x in run.accepted_targets}
    assert all(command.producer_module == "PLC" for command in run.actuator_commands)
    assert all(command.plc_cycle_id in cycles for command in run.actuator_commands)
    assert all(command.safety_envelope_id in envelopes for command in run.actuator_commands)
    assert all(command.accepted_target_id in targets for command in run.actuator_commands)


def test_pressure_restriction_is_materialized_by_plc():
    policy, decision, result = _restricted_cycle(_measured(dp=61_000))
    assert decision.state == SafetyState.FAULT
    assert decision.envelope.minimum_speed_fraction == policy.fault_speed
    assert decision.envelope.maximum_speed_fraction == policy.fault_speed
    assert result.actuator_command.requested_speed == policy.fault_speed
    assert result.actuator_command.producer_module == "PLC"


def test_exact_safe_speed_and_protected_path_use_plc_command():
    policy, decision, result = _restricted_cycle(_measured(temperature=345))
    assert decision.state == SafetyState.PROTECTED
    assert result.actuator_command.requested_speed == policy.fault_speed
    assert result.actuator_command.mode == "EMERGENCY"
    assert result.actuator_command.safety_envelope_id == decision.envelope.envelope_id


def test_fault_safe_action_and_same_tick_emergency_cycle():
    plant, controls = physical_fixture(branch_count=2, power_each=120)
    run = run_feedback(
        plant,
        controls,
        4_000_000_000,
        *fixture_configs(),
        disturbances=(Disturbance(3_000_000_000, sensor_failures=("temperature",)),),
    )
    command = next(x for x in run.actuator_commands if x.created_ns == 3_000_000_000)
    envelope = next(x for x in run.safety_envelopes if x.envelope_id == command.safety_envelope_id)
    cycle = next(x for x in run.plc_cycles if x.plc_cycle_id == command.plc_cycle_id)
    assert envelope.state == SafetyState.FAULT
    assert envelope.created_ns == cycle.created_ns == command.created_ns
    assert command.producer_module == "PLC"


def test_missing_or_wrong_command_provenance_is_rejected():
    fields = {
        "command_id": "bad",
        "created_ns": 0,
        "producer_module": "SAFETY",
        "plc_cycle_id": "plc-cycle:test",
        "accepted_target_id": "accepted-target:test",
        "safety_envelope_id": "safety-envelope:test",
        "requested_speed": 0.5,
        "applied_command_before_actuator_dynamics": 0.5,
        "reason": "test",
        "mode": "test",
        "source_ids": (),
    }
    with pytest.raises(ThermalError, match="ACTUATION_OWNERSHIP_VIOLATION"):
        ActuatorCommand(**fields)
    fields["producer_module"] = "PLC"
    fields["plc_cycle_id"] = ""
    with pytest.raises(ThermalError, match="CONFIG_INVALID"):
        ActuatorCommand(**fields)
    with pytest.raises(ThermalError, match="ACTUATION_OWNERSHIP_VIOLATION"):
        PumpActuator(fixture_configs()[2], 0.7).command(0.5, 0)


def test_no_true_raw_actual_or_future_reference_added_to_safety_or_plc():
    for relative in ("v0_2/safety/supervisor.py", "v0_2/control/inner_loop.py"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert ".actual" not in source
        assert "future" not in source.lower()
        assert "physical_fixture" not in source


def test_r1_evidence_preserves_selection_behavior_and_numerics():
    evidence = json.loads(
        (ROOT / "phase5_r1_selection_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["selected"] == {"inner": "inner_b", "outer": "outer_c"}
    assert evidence["historical_holdout"]["trace_comparison"]["status"] == "PASS"
    assert all(
        item["difference"] == 0 and item["producer_module"] == "PLC"
        for item in evidence["safety_active_equivalence"]
    )
    assert evidence["convergence"]["status"] == "PASS"
    assert evidence["stability"]["runs"] == 10
    assert evidence["stability"]["identical_hashes"] is True
    assert evidence["stability"]["bounded_memory"] is True


def test_r1_baseline_supersession_chain_and_frozen_parameters():
    old = json.loads((ROOT / "phase5_feedback_baseline.json").read_text(encoding="utf-8"))
    new = json.loads((ROOT / "phase5_r1_feedback_baseline.json").read_text(encoding="utf-8"))
    assert new["supersedes_original_baseline_sha256"] == ORIGINAL_BASELINE_SHA
    assert new["original_control_core_sha256"] == old["code_sha256"]
    assert new["inner_gains"] == old["inner_gains"]
    assert new["outer_gains"] == old["outer_gains"]
    assert new["actuator"] == old["actuator"]
    assert new["sensor"] == old["sensor"]
    assert new["safety"] == old["safety"]
