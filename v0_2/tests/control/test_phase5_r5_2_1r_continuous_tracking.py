"""Frozen, offline continuous-tracking qualification boundary."""

import json
from pathlib import Path

from v0_2.examples import phase5_r5_2_1r_validation as validation
from v0_2.examples.phase5_r5_2_1r_semantic_engine import (
    STATES,
    OfflineTrackingQualifier,
    ReleasedObservation,
)

ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_preregistration_sources_and_production_hashes_frozen():
    reg = read("phase5_r5_2_1r_continuous_tracking_semantics_registration.json")
    evidence = read("phase5_r5_2_1r_continuous_tracking_semantics_evidence.json")
    assert evidence["registration_sha256"] == validation.sha(validation.REGISTRATION)
    assert all(validation.integrity(reg).values())
    assert evidence["profile_sha256"] == "9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8"
    assert evidence["production_safety_changed"] is False
    assert reg["historical_blocked_r5_3"] == "R5_2_TRACKING_RULE_INSUFFICIENTLY_SPECIFIED_FOR_PRODUCTION_PORT"


def test_six_states_complete_transition_and_lifecycle_contract():
    spec = read("phase5_r5_2_1r_continuous_tracking_semantics_spec.json")
    reg = read("phase5_r5_2_1r_continuous_tracking_semantics_registration.json")
    assert set(STATES) == set(spec["states"]) == set(reg["states"])
    assert set(reg["epoch_fields"]) == set(spec["epoch_fields"])
    assert set(reg["watch_fields"]) == set(spec["unresolved_watch_fields"])
    assert len(spec["transitions"]) >= 10
    assert len(spec["epoch_lifecycle"]) == 4
    assert len(spec["watch_lifecycle"]) == 4
    assert len(spec["invariants"]) == 8
    assert spec["production_safety_change"] is False


def test_all_registered_sequences_invariants_and_causality():
    evidence = read("phase5_r5_2_1r_continuous_tracking_semantics_evidence.json")
    assert evidence["status"] == "TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT"
    assert set(evidence["sequence_pass"]) == {f"S{i}" for i in range(1, 17)} | {"S16_variant"}
    assert all(evidence["sequence_pass"].values())
    assert len(evidence["invariants"]) == 8 and all(evidence["invariants"].values())
    assert all(evidence["prefix_causality"].values())
    assert evidence["cases"]["S6"]["confirmed_latched"]
    assert evidence["cases"]["S16"]["confirmed_latched"]
    assert evidence["cases"]["S13"]["confirmed_latched"]
    assert evidence["cases"]["S15"]["restored_motion_after_confirmation"]


def test_cumulative_subthreshold_command_is_recorded_as_blocker():
    evidence = read("phase5_r5_2_1r_continuous_tracking_semantics_evidence.json")
    audit = evidence["post_validation_audit"]
    assert audit["observed_terminal_state"] == "STEADY_TRACKING"
    assert audit["observed_epoch_count"] == 0
    assert audit["registered_rules_modified_after_outcomes"] is False


def test_no_forbidden_information_or_auto_actuation():
    assert set(ReleasedObservation.__dataclass_fields__).isdisjoint(
        {"actual_speed", "fault_identity", "scenario_label", "plant_truth", "future_measurement"}
    )
    spec = read("phase5_r5_2_1r_continuous_tracking_semantics_spec.json")
    assert "ActuatorCommand" not in OfflineTrackingQualifier.__dict__
    assert "existing top-level Safety reset authority" in spec["confirmed_recovery_authority"]
    assert "first valid released measurement" in spec["sensor_recovery_rule"]


def test_fixture_numeric_parameters_and_r52_rules_reused():
    evidence = read("phase5_r5_2_1r_continuous_tracking_semantics_evidence.json")
    profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
    classifier = read("phase5_r5_2_silent_tracking_fault_registration.json")["classifier"]
    assert evidence["frozen_r5_2_classifier"] == classifier
    qualifier = validation.OfflineTrackingQualifier(profile, classifier)
    assert qualifier.confirm_samples == classifier["confirm_consecutive_qualified_samples"]
    assert qualifier.minimum_motion == profile["TrackingQualificationProfile"]["minimum_observable_speed_change"]["value"]
    assert qualifier._response_open(0, 0.02) > qualifier._response_open(0, 0.2)
    assert (ROOT / "docs/results/phase5_r5_2_1r_continuous_tracking_semantics.png").is_file()
