"""R5.1 diagnostic guards: evidence cannot alter the frozen production loop."""

import inspect
import json
from dataclasses import asdict

import pytest
from v0_2.examples import phase5_r5_1_safety_handoff_audit as audit
from v0_2.safety.supervisor import SafetySupervisor


@pytest.fixture(scope="module")
def evidence():
    return json.loads(audit.EVIDENCE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registration():
    return json.loads(audit.REGISTRATION.read_text(encoding="utf-8"))


def test_preregistration_and_frozen_sources(registration, evidence):
    assert evidence["registration_sha256"] == audit.sha(audit.REGISTRATION)
    assert all(audit.integrity(registration).values())
    assert evidence["candidate"] == registration["frozen_controller"]
    assert evidence["candidate"]["kp"] == 4500
    assert evidence["candidate"]["ki_hot"] == 110
    assert evidence["candidate"]["ki_cold"] == 130
    assert registration["nominal_actuator_contract"] == {"minimum": 0.3, "maximum": 0.9, "tau_s": 1.0, "ramp_per_s": 0.2, "command_delay_ns": 200_000_000}
    assert evidence["production_behavior_changed"] is False


def test_exact_preparation_and_no_warm_start(registration, evidence):
    for case, speed in (("WARM_CAPTURE", 0.3), ("COLD_CAPTURE", 0.9)):
        prepared = evidence["preparation"][case]
        assert prepared["speed_fraction"] == speed
        assert prepared["duration_s"] == 180
        assert prepared["controller_prehistory"] == "none"
        assert prepared["integrator_warm_start"] is False
        assert prepared["reproduction_status"] == "PASS"
    assert registration["preparation"]["power_w_per_device"] == 120


def test_nominal_event_reproduced_and_actuator_follows_frozen_response(evidence):
    cold = evidence["cases"]["cold"]
    assert [200_000_000, "DEGRADED", ["ACTUATOR_TRACKING_PENDING"]] in cold["safety_events"]
    assert cold["first_plc_command"] == pytest.approx(0.648)
    assert cold["first_possible_response_ns"] == 200_000_000
    assert cold["first_actual_response_ns"] == 400_000_000
    assert cold["first_measured_response_ns"] == 400_000_000
    assert cold["first_expected_response_violation_ns"] is None
    assert cold["expected_response_max_difference"] <= 1e-9


def test_stuck_remains_restrictive_and_measured_only_separates(evidence):
    assert evidence["cases"]["stuck"]["safety_final_state"] == "FAULT"
    assert evidence["cases"]["stuck"]["first_measured_response_ns"] is None
    assert evidence["measured_only_separation"]["status"] == "MEASURED_ONLY_SEPARATION_PASS"
    assert evidence["measured_only_separation"]["nominal_measured_speed_drop"] > 0.001
    assert evidence["measured_only_separation"]["stuck_measured_speed_drop"] == 0
    assert evidence["status"] == "NORMAL_HANDOFF_MISCLASSIFIED_AS_DEGRADED"
    assert len(evidence["false_positive_checks"]) == 9
    assert all(evidence["false_positive_checks"].values())


def test_ownership_causality_and_accounting(evidence):
    assert evidence["ownership_causality_status"] == "PASS"
    assert evidence["conservation_status"] == "PASS"
    for case in evidence["cases"].values():
        assert case["provenance_links_pass"]
        assert all(event["plc_actuator_command"]["producer_module"] == "PLC" for event in case["events"])
        assert all(event["measurement_age_ns"] == 0 for event in case["events"])


def test_diagnostic_read_only_and_no_truth_leakage(registration, evidence):
    source = inspect.getsource(audit)
    assert "patch.object(controlled_loop, \"OuterFeedback\", factory)" in source
    assert "controlled_loop.run_feedback(" in source
    assert "safety.evaluate(" not in source
    assert "actuator.command(" not in source
    assert "actual_pump_speed" not in inspect.getsource(audit.classify)
    assert "expected_pump_speed" not in inspect.getsource(audit.classify)
    assert evidence["production_behavior_changed"] is False
    assert registration["safety_change_authorized"] is False
    safety_source = inspect.getsource(SafetySupervisor.evaluate)
    assert "actuator.actual" not in safety_source
    assert "ActuatorCommand(" not in safety_source
    assert "actual" not in inspect.signature(SafetySupervisor.evaluate).parameters


def test_audit_sink_cannot_change_completed_control_output():
    historical = json.loads(audit.r4.REGISTRATION.read_text(encoding="utf-8"))
    preparations, states = audit.r4._prepare(historical)
    speed = preparations["COLD_CAPTURE"]["speed_fraction"]
    run, ticks = audit.run_case("COLD_CAPTURE", states["COLD_CAPTURE"], speed, historical)
    before = audit.canonical({"rows": [asdict(row) for row in run.rows], "commands": [asdict(command) for command in run.actuator_commands], "safety": run.events})
    audit.trace(run, ticks, speed, False)
    audit.expected_trajectory(run, speed)
    after = audit.canonical({"rows": [asdict(row) for row in run.rows], "commands": [asdict(command) for command in run.actuator_commands], "safety": run.events})
    assert before == after


def test_repeatability(evidence):
    for case in ("cold", "stuck"):
        result = evidence["repeatability"][case]
        assert result["runs"] == 10
        assert result["all_identical"]
        assert len(set(result["all_hashes"])) == 1
