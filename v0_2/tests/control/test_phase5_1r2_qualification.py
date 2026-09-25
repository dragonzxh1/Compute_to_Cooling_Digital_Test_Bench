import json

from v0_2.examples import phase5_1r2_qualification as qualification


def result():
    return json.loads(qualification.RESULT.read_text(encoding="utf-8"))


def test_frozen_baseline_and_all_referenced_hashes_are_intact():
    registration = qualification._load(qualification.REGISTRATION)
    baseline = qualification._load(qualification.BASELINE)

    integrity = qualification._integrity(registration, baseline)

    assert integrity["status"] == "PASS"
    assert all(integrity["checks"].values())


def test_result_uses_frozen_bidirectional_six_run_matrix():
    evidence = result()

    assert evidence["integrity"]["status"] == "PASS"
    assert len(evidence["run_matrix"]) == 6
    assert {
        (record["case"], record["physics_dt_ns"])
        for record in evidence["run_matrix"]
    } == {
        (case, dt)
        for case in ("WARM_CAPTURE", "COLD_CAPTURE")
        for dt in (200_000_000, 100_000_000, 50_000_000)
    }
    assert evidence["retuning_performed"] is False
    assert evidence["phase6_authorized"] is False


def test_blocked_gate_is_supported_by_metrics_not_capacity_saturation():
    evidence = result()
    warm = [item for item in evidence["run_matrix"] if item["case"] == "WARM_CAPTURE"]
    cold = [item for item in evidence["run_matrix"] if item["case"] == "COLD_CAPTURE"]

    assert all(item["metrics"]["status"] == "PASS" for item in warm)
    assert all(item["metrics"]["settling_time_s"] is None for item in cold)
    assert all(item["metrics"]["control_direction_pass"] for item in cold)
    assert all(item["metrics"]["final_saturation_pass"] for item in cold)
    assert evidence["failure_classifications"] == [
        "B_COLD_SIDE_CANNOT_SETTLE",
        "E_SAFETY_RESTRICTION_REQUIRED",
        "F_NUMERICAL_CONVERGENCE_FAILURE",
    ]


def test_ownership_conservation_repeatability_and_figure_evidence_pass():
    evidence = result()

    assert evidence["ownership"]["status"] == "PASS"
    assert evidence["conservation"]["status"] == "PASS"
    assert evidence["stability"]["status"] == "PASS"
    assert evidence["stability"]["runs"] == 10
    assert qualification.ROOT.joinpath(
        "docs/results/phase5_1r2_nominal_regulation.png"
    ).is_file()
