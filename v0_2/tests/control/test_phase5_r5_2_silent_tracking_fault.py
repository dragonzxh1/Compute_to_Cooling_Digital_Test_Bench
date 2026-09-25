"""R5.2 test-only silent fault, causal classifier and frozen-source guards."""

import inspect
import json
from dataclasses import asdict, fields

import pytest
from v0_2.examples import phase5_r5_2_silent_tracking_fault as audit
from v0_2.plant import controlled_loop
from v0_2.safety.supervisor import SafetySupervisor


@pytest.fixture(scope="module")
def registration():
    return json.loads(audit.REGISTRATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    return json.loads(audit.EVIDENCE.read_text(encoding="utf-8"))


def test_frozen_r5_and_historical_hashes(registration, evidence):
    assert all(audit.integrity(registration).values())
    assert evidence["registration_sha256"] == audit.sha(audit.REGISTRATION)
    assert evidence["source_r5_1_registration_sha256"] == registration["source_r5_1_registration_sha256"]
    assert evidence["source_r5_1_evidence_sha256"] == registration["source_r5_1_evidence_sha256"]
    assert evidence["frozen_controller"] == {"kp": 4500.0, "ki_hot": 110.0, "ki_cold": 130.0, "kd": 0.0, "blend_halfwidth_k": 0.1, "single_integral_state": True}
    assert registration["nominal_actuator_contract"] == {"minimum": 0.3, "maximum": 0.9, "command_delay_ns": 200_000_000, "tau_s": 1.0, "ramp_per_s": 0.2}
    assert evidence["production_safety_changed"] is False
    assert evidence["final_feedback_baseline_frozen"] is False


def test_exact_cold_preparation_and_nominal_reproduction(registration, evidence):
    prep = evidence["preparation"]
    prior = json.loads(audit.r51.EVIDENCE.read_text(encoding="utf-8"))["preparation"]["COLD_CAPTURE"]
    assert prep["normalized_initial_state_sha256"] == prior["normalized_initial_state_sha256"]
    assert prep["speed_fraction"] == 0.9
    assert prep["duration_s"] == 180
    assert prep["controller_prehistory"] == "none"
    assert prep["integrator_warm_start"] is False
    assert registration["preparation"]["power_w_per_device"] == 120
    assert evidence["nominal_reproduced"]
    nominal = evidence["cases"]["NOMINAL_COLD"]
    assert nominal["speed_only_diagnostic"]["records"][0]["observation"]["previous_plc_command"] is None
    assert nominal["speed_only_diagnostic"]["records"][0]["features"]["command_step_magnitude"] == pytest.approx(0.252)
    assert nominal["first_command_delta"] == pytest.approx(-0.252)
    assert nominal["first_measured_response_ns"] == 400_000_000
    assert nominal["speed_only_diagnostic"]["first_state_times_ns"]["TRACKING_PROGRESS"] == 400_000_000
    assert nominal["speed_only_diagnostic"]["fault_confirmation_ns"] is None


def test_silent_stuck_uses_healthy_fault_bits_and_confirms_from_measurements(registration, evidence):
    silent = evidence["cases"]["SILENT_STUCK"]
    assert silent["measured_fault_bit_all_false"]
    assert silent["first_measured_response_ns"] is None
    assert silent["speed_only_diagnostic"]["fault_confirmation_ns"] == 1_200_000_000
    assert silent["speed_only_diagnostic"]["first_state_times_ns"]["TRACKING_FAULT_SUSPECTED"] == 400_000_000
    assert silent["current_safety_final_state"] == "FAULT"
    assert registration["test_only_fault_fixtures"]["tags"] == ["NUMERICAL_TEST_FIXTURE", "FAULT_INJECTION", "NOT_OEM"]


def test_delay_and_sluggish_boundary(evidence):
    cases = evidence["cases"]
    assert cases["DELAY_0_6"]["first_measured_response_ns"] == 800_000_000
    assert cases["DELAY_0_6"]["speed_only_diagnostic"]["fault_confirmation_ns"] is None
    assert cases["DELAY_1_0"]["first_measured_response_ns"] == 1_200_000_000
    assert cases["DELAY_1_0"]["speed_only_diagnostic"]["fault_confirmation_ns"] == 1_200_000_000
    assert cases["DELAY_2_0"]["first_measured_response_ns"] == 2_200_000_000
    assert cases["DELAY_2_0"]["speed_only_diagnostic"]["fault_confirmation_ns"] == 1_200_000_000
    assert cases["SLOW_RAMP_0_1"]["speed_only_diagnostic"]["fault_confirmation_ns"] is None
    assert cases["SLOW_RAMP_0_05"]["speed_only_diagnostic"]["fault_confirmation_ns"] == 1_200_000_000


def test_quality_and_latency_do_not_become_false_faults(evidence):
    assert evidence["sensor_quality_insufficient"]
    assert evidence["cases"]["SENSOR_QUALITY_INVALID"]["speed_only_diagnostic"]["fault_confirmation_ns"] is None
    assert evidence["cases"]["SENSOR_QUALITY_INVALID"]["speed_only_diagnostic"]["final_state"] == "INSUFFICIENT_MEASUREMENT"
    delayed = evidence["cases"]["AUDITOR_TELEMETRY_DELAY_0_4"]["speed_only_diagnostic"]
    assert delayed["fault_confirmation_ns"] is None
    assert delayed["final_state"] == "TRACKING_PROGRESS"


def test_classifier_input_contract_excludes_truth_and_identity(registration, evidence):
    names = {field.name for field in fields(audit.PermittedObservation)}
    assert names == set(registration["permitted_online_fields"])
    assert not names.intersection(registration["forbidden_online_fields"])
    update_source = inspect.getsource(audit.MeasuredOnlyClassifier.update)
    for forbidden in ("actual_pump_speed", "fault_active", "fault_id", "scenario_identity", "pump_fault_bit"):
        assert forbidden not in update_source
    assert "scenario" not in inspect.signature(audit.MeasuredOnlyClassifier.update).parameters
    assert "actual" not in inspect.signature(audit.MeasuredOnlyClassifier.update).parameters
    assert "phase5_r5_2_silent_tracking_fault" not in inspect.getsource(SafetySupervisor.evaluate)
    assert "phase5_r5_2_silent_tracking_fault" not in inspect.getsource(controlled_loop.run_feedback)
    assert evidence["silent_stuck_no_measured_fault_bit"]


def test_online_prefix_causality_and_no_retroactive_labels(registration, evidence):
    for case in ("NOMINAL_COLD", "SILENT_STUCK", "DELAY_1_0"):
        full = evidence["cases"][case]["speed_only_diagnostic"]["records"]
        source = [audit.PermittedObservation(**record["observation"]) for record in full]
        for count in range(1, len(source) + 1):
            prefix = audit.audit_observations(source[:count], registration, with_hydraulics=False)
            assert prefix["records"][-1]["features"] == full[count - 1]["features"]
            assert prefix["transitions"] == [t for t in evidence["cases"][case]["speed_only_diagnostic"]["transitions"] if t["timestamp_ns"] <= source[count - 1].timestamp_ns]


def test_auditor_read_only_and_ownership(registration, evidence):
    historical = json.loads(audit.r4.REGISTRATION.read_text(encoding="utf-8"))
    preparations, states = audit.r4._prepare(historical)
    run, _ = audit.run_case("NOMINAL_COLD", states["COLD_CAPTURE"], preparations["COLD_CAPTURE"]["speed_fraction"], historical, registration, duration_ns=10_000_000_000)
    before = audit.canonical({"rows": [asdict(x) for x in run.rows], "commands": [asdict(x) for x in run.actuator_commands], "safety": run.events})
    source = audit.observations(run, 0.9, 10_000_000_000)
    audit.audit_observations(source, registration, with_hydraulics=False)
    audit.audit_observations(source, registration, with_hydraulics=True)
    after = audit.canonical({"rows": [asdict(x) for x in run.rows], "commands": [asdict(x) for x in run.actuator_commands], "safety": run.events})
    assert before == after
    assert all(command.producer_module == "PLC" for command in run.actuator_commands)
    assert "ActuatorCommand(" not in inspect.getsource(SafetySupervisor.evaluate)
    assert evidence["ownership_status"] == "PASS"
    assert evidence["causality_status"] == "PASS"
    assert evidence["conservation_status"] == "PASS"


def test_repeatability_and_gate(evidence):
    for case in ("NOMINAL_COLD", "SILENT_STUCK", "DELAY_1_0"):
        repeated = evidence["repeatability"][case]
        assert repeated["runs"] == 10
        assert repeated["all_identical"]
        assert len(set(repeated["all_hashes"])) == 1
    assert evidence["status"] == "MEASURED_ONLY_SILENT_TRACKING_FAULT_SEPARATION_PASS"
