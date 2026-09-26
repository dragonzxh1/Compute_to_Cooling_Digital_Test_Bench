"""R5.2.2 fixture-only calibration, information boundary and source freeze."""

import hashlib
import json
from pathlib import Path

from v0_2.examples import phase5_r5_2_2_tracking_calibration as c

ROOT = Path(__file__).resolve().parents[3]


def _read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def test_registration_precedes_results_and_sources_stay_frozen():
    reg = _read("phase5_r5_2_2_tracking_calibration_registration.json")
    evidence = _read("phase5_r5_2_2_tracking_calibration_evidence.json")
    assert evidence["registration_sha256"] == _sha("phase5_r5_2_2_tracking_calibration_registration.json")
    assert all(c.source_integrity(reg).values())
    assert all(evidence["source_hash_checks"].values())
    assert evidence["production_changed"] is False
    assert evidence["r5_2_1_restarted"] is False
    assert evidence["r5_3_restarted"] is False


def test_profile_separates_fixture_from_hardware_and_model_absences():
    schema = _read("phase5_tracking_profile_schema.json")
    profile = _read("phase5_r5_2_2_fixture_tracking_profile.json")
    evidence = _read("phase5_r5_2_2_tracking_calibration_evidence.json")
    assert evidence["profile_sha256"] == _sha("phase5_r5_2_2_fixture_tracking_profile.json")
    assert set(schema["required"][1:]) <= set(profile)
    for group in schema["required"][1:]:
        assert set(schema["properties"][group]["required"]) <= set(profile[group])
        for item in profile[group].values():
            assert set(schema["$defs"]["parameter"]["required"]) <= set(item)
            assert "NUMERICAL_TEST_FIXTURE" in item["calibration_status"]
    sensor = profile["SensorObservationProfile"]
    assert sensor["speed_measurement_noise_bound"]["value"] == 0.0
    assert sensor["speed_measurement_resolution"]["value"] is None
    assert sensor["speed_measurement_resolution"]["source_type"] == "NOT_MODELED"
    assert "REQUIRES RECALIBRATION FOR REAL EQUIPMENT" in profile["classification"]
    assert evidence["model_audit"]["speed_measurement_quantization"] == "SPEED_MEASUREMENT_QUANTIZATION_NOT_MODELED"


def test_observation_floor_and_parameter_derived_opening():
    reg = _read("phase5_r5_2_2_tracking_calibration_registration.json")
    evidence = _read("phase5_r5_2_2_tracking_calibration_evidence.json")
    expected = max(0.01, 2 * max(evidence["stationary_floor"], evidence["mesh_floor"]))
    assert evidence["minimum_observable_speed_change"] == expected
    assert all(item["summary"]["peak_to_peak"] == 0 for item in evidence["static"].values())
    for case in evidence["step_cases"].values():
        assert case["response_open_ns"] == c.response_open_ns(0, case["magnitude"], expected, reg)
        assert case["observable"]
    assert evidence["checks"]["mesh_floor_bounded"]


def test_measured_only_whitelist_and_prefix_causality():
    evidence = _read("phase5_r5_2_2_tracking_calibration_evidence.json")
    reg = _read("phase5_r5_2_2_tracking_calibration_registration.json")
    case = evidence["moving_command"]["NORMAL"]
    source = c.observations({"rows": case["released_trace"]})
    assert set(source[0]) == {"time_ns", "command", "command_timestamp_ns", "measured_speed", "sample_ns", "release_ns", "quality", "measurement_record_id"}
    assert set(source[0]).isdisjoint({"actual_speed", "fault_identity", "scenario_label", "plant_truth"})
    for index in range(1, len(source) + 1):
        assert c.qualified_progress(source[:index], 0, 0.5, 1, evidence["minimum_observable_speed_change"], reg["fixture_sensor"]["max_age_ns"]) == case["decisions"][:index]
    assert all(not item["qualified"] for item in evidence["sensor_loss_recovery"]["decisions"] if not item["valid"])


def test_observability_conservation_and_repeatability_gates():
    evidence = _read("phase5_r5_2_2_tracking_calibration_evidence.json")
    assert evidence["status"] == "FIXTURE_TRACKING_CALIBRATION_AND_OBSERVABILITY_CLOSED"
    assert all(evidence["checks"].values())
    assert evidence["moving_command"]["NORMAL"]["first_qualified_ns"] is not None
    assert evidence["moving_command"]["SILENT_STUCK"]["first_qualified_ns"] is None
    assert evidence["post_startup_stuck"]["first_qualified_ns"] is None
    assert all(item["first_qualified_ns"] is not None for item in evidence["reversals"].values())
    assert all(item["all_identical"] and item["runs"] == 10 for item in evidence["static"].values())
    assert all(item["all_identical"] and item["runs"] == 10 for item in evidence["repeat_steps"].values())
    assert (ROOT / "docs/results/phase5_r5_2_2_tracking_observability.png").is_file()
