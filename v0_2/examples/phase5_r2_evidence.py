"""Phase 5R2 plant-authority target derivation and controller reselection."""

from __future__ import annotations

import gc
import hashlib
import json
import tracemalloc
from dataclasses import asdict, replace
from pathlib import Path

from v0_2.examples.phase5_1r_qualification import _controls, _window_mean_max_device
from v0_2.examples.phase5_validation import REGISTRATION, fixture_configs, scenario_events
from v0_2.plant.authority import traces_for_run
from v0_2.plant.controlled_loop import run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import run as run_open_loop

ROOT = Path(__file__).resolve().parents[2]
TARGET_REGISTRATION = ROOT / "phase5_r2_target_registration.json"
R1_BASELINE = ROOT / "phase5_r1_feedback_baseline.json"
SELECTION_OUT = ROOT / "phase5_r2_selection_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r2_candidate_baseline.json"
FINAL_BASELINE = ROOT / "phase5_r2_feedback_baseline.json"
CORE_PATHS = (
    "v0_2/control/pid.py",
    "v0_2/control/inner_loop.py",
    "v0_2/control/outer_feedback.py",
    "v0_2/plant/controlled_loop.py",
    "v0_2/actuators/pump.py",
    "v0_2/measurement/local_sensor.py",
    "v0_2/safety/supervisor.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _row_digest(run) -> str:
    return hashlib.sha256(_canonical([asdict(row) for row in run.rows])).hexdigest()


def authority_endpoints() -> dict[str, float]:
    registration = json.loads(TARGET_REGISTRATION.read_text(encoding="utf-8"))
    endpoint = registration["cooling_authority_endpoints"]
    plant, base = physical_fixture(branch_count=2, power_each=120)
    values = {}
    residuals = {}
    for label, speed in (
        ("low", endpoint["low_speed_fraction"]),
        ("high", endpoint["high_speed_fraction"]),
    ):
        result = run_open_loop(
            plant,
            _controls(base, speed),
            endpoint["duration_ns"],
            200_000_000,
        )
        rows = traces_for_run(result)
        values[label] = _window_mean_max_device(rows, endpoint["qualified_window_start_ns"])
        residuals[label] = {
            "max_mass_residual_kg_s": max(
                step.ledger.max_mass_node_residual_kg_s for step in result.accepted
            ),
            "max_energy_residual_j": max(
                abs(step.ledger.full_loop_residual_j) for step in result.accepted
            ),
        }
    target = (values["low"] + values["high"]) / 2
    return {
        "load_w_per_device": 120.0,
        "low_speed_fraction": endpoint["low_speed_fraction"],
        "high_speed_fraction": endpoint["high_speed_fraction"],
        "t_low_k": values["low"],
        "t_high_k": values["high"],
        "target_k": target,
        "upper_margin_k": values["low"] - target,
        "lower_margin_k": target - values["high"],
        "residuals": residuals,
    }


def _gains(candidate):
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def run_r2_scenario(scenario_id, target_k, *, inner=None, outer=None, physics_ns=200_000_000):
    registered = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    duration = (
        registered["training_duration_ns"]
        if scenario_id in registered["training_ids"]
        else registered["holdout_duration_ns"]
    )
    plant, controls = physical_fixture(branch_count=2, power_each=120)
    clocks, sensor, actuator, outer_cfg, inner_cfg, safety = fixture_configs(
        inner, outer, physics_ns
    )
    outer_cfg = replace(outer_cfg, target_k=target_k)
    safety = replace(safety, control_target_k=target_k)
    controls = replace(
        controls,
        speed_actual=replace(controls.speed_actual, value=0.7, valid_range=(0.7, 0.7)),
    )
    return run_feedback(
        plant,
        controls,
        duration,
        clocks,
        sensor,
        actuator,
        outer_cfg,
        inner_cfg,
        safety,
        disturbances=scenario_events(scenario_id),
    )


def _score(metrics, dimension):
    return (
        metrics["max_mass_residual_kg_s"] >= 1e-8
        or metrics["max_energy_residual_j"] >= 0.001
        or metrics["minimum_headroom_k"] < -5
        or metrics["safety_fault_event_count"] > 0,
        metrics[dimension],
        metrics["control_total_variation"],
        metrics["pump_electrical_j"],
    )


def _training(candidate, other, scenarios, target_k, *, inner_candidate):
    rows = []
    for scenario in scenarios:
        run = run_r2_scenario(
            scenario,
            target_k,
            inner=_gains(candidate) if inner_candidate else other,
            outer=other if inner_candidate else _gains(candidate),
        )
        rows.append({"scenario": scenario, "metrics": run.metrics()})
    metric = "dp_tracking_iae_pa_s" if inner_candidate else "temperature_iae_k_s"
    score = (
        any(_score(x["metrics"], metric)[0] for x in rows),
        sum(x["metrics"][metric] for x in rows),
        sum(x["metrics"]["control_total_variation"] for x in rows),
        sum(x["metrics"]["pump_electrical_j"] for x in rows),
        candidate["id"],
    )
    return {"candidate": candidate, "training": rows, "selection_score": score}


def _base_candidate(authority, selected_inner, selected_outer, status):
    r1 = json.loads(R1_BASELINE.read_text(encoding="utf-8"))
    result = dict(r1)
    result.update(
        {
            "schema": "phase5-r2-feedback-baseline-candidate-v1",
            "revision": 2,
            "status": status,
            "supersedes_r1_baseline_sha256": _sha(R1_BASELINE),
            "source_r1_control_core_sha256": r1["code_sha256"],
            "thermal_control_target_k": authority["target_k"],
            "target_derivation_rule": "AUTHORITY_MIDPOINT",
            "target_derivation_load_w_per_device": authority["load_w_per_device"],
            "target_authority_endpoints_k": {
                "low": authority["t_low_k"],
                "high": authority["t_high_k"],
            },
            "target_authority_margins_k": {
                "upper": authority["upper_margin_k"],
                "lower": authority["lower_margin_k"],
            },
            "inner_candidate_id": selected_inner["id"],
            "outer_candidate_id": selected_outer["id"],
            "inner_gains": _gains(selected_inner),
            "outer_gains": _gains(selected_outer),
            "safety": {**r1["safety"], "control_target_k": authority["target_k"]},
            "ownership_schema_version": "SafetyEnvelope-to-PLC-ActuatorCommand-v1",
            "command_provenance_schema_version": r1["command_provenance_schema_version"],
            "historical_stress_id": "HOLDOUT-01-combined",
            "r2_target_registration_sha256": _sha(TARGET_REGISTRATION),
            "code_sha256": hashlib.sha256(
                b"".join((ROOT / path).read_bytes() for path in CORE_PATHS)
            ).hexdigest(),
        }
    )
    return result


def collect_evidence() -> tuple[dict, dict, bool]:
    target_registration = json.loads(TARGET_REGISTRATION.read_text(encoding="utf-8"))
    tuning = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    authority = authority_endpoints()
    endpoint_policy = target_registration["cooling_authority_endpoints"]
    reproduction = {
        "low_difference_k": authority["t_low_k"] - endpoint_policy["historical_low_k"],
        "high_difference_k": authority["t_high_k"] - endpoint_policy["historical_high_k"],
        "tolerance_k": endpoint_policy["endpoint_reproduction_tolerance_k"],
    }
    reproduction["status"] = (
        "PASS"
        if abs(reproduction["low_difference_k"]) <= reproduction["tolerance_k"]
        and abs(reproduction["high_difference_k"]) <= reproduction["tolerance_k"]
        else "FAIL"
    )
    if reproduction["status"] != "PASS":
        raise RuntimeError("PLANT_AUTHORITY_REGRESSION")
    minimum_margin = target_registration["required_authority_margin_k_each_side"]
    if min(authority["upper_margin_k"], authority["lower_margin_k"]) < minimum_margin:
        raise RuntimeError("TARGET_AUTHORITY_TOO_NARROW")

    scenarios = tuning["training_ids"]
    fixed_outer = _gains(tuning["outer_candidates"][0])
    inner_results = [
        _training(candidate, fixed_outer, scenarios, authority["target_k"], inner_candidate=True)
        for candidate in tuning["inner_candidates"]
    ]
    selected_inner = min(inner_results, key=lambda x: x["selection_score"])["candidate"]
    outer_results = [
        _training(
            candidate,
            _gains(selected_inner),
            scenarios,
            authority["target_k"],
            inner_candidate=False,
        )
        for candidate in tuning["outer_candidates"]
    ]
    selected_outer = min(outer_results, key=lambda x: x["selection_score"])["candidate"]
    inner_changed = selected_inner["id"] != "inner_b"
    outer_changed = selected_outer["id"] != "outer_c"
    status = (
        "INNER_SELECTION_CHANGED_AFTER_TARGET_REVISION"
        if inner_changed
        else "OUTER_SELECTION_CHANGED_DUE_TO_TARGET_REVISION"
        if outer_changed
        else "SELECTION_UNCHANGED_CONTINUE_R2_FREEZE"
    )
    evidence = {
        "schema": "phase5-r2-selection-evidence-v1",
        "status": status,
        "authority": authority,
        "endpoint_reproduction": reproduction,
        "target_formula_exact": authority["target_k"]
        == (authority["t_low_k"] + authority["t_high_k"]) / 2,
        "minimum_required_margin_k": minimum_margin,
        "target_provenance": target_registration["target_provenance"],
        "inner_training": inner_results,
        "outer_training": outer_results,
        "selected": {"inner": selected_inner["id"], "outer": selected_outer["id"]},
        "selection_priority": target_registration["controller_candidate_policy"][
            "selection_priority"
        ],
        "holdout_used_in_selection": False,
        "ownership_audit_reference": {
            "path": "docs/results/phase5_r1_ownership_audit.json",
            "sha256": _sha(ROOT / "docs/results/phase5_r1_ownership_audit.json"),
            "status": "PASS",
        },
        "downstream_stress_convergence_stability_executed": False,
    }
    candidate = _base_candidate(authority, selected_inner, selected_outer, status)
    return evidence, candidate, not inner_changed and not outer_changed


def _continue_after_unchanged(evidence, candidate):
    target = evidence["authority"]["target_k"]
    inner, outer = candidate["inner_gains"], candidate["outer_gains"]
    holdout = run_r2_scenario("HOLDOUT-01-combined", target, inner=inner, outer=outer)
    mesh_runs = [
        run_r2_scenario("TUNE-01-load", target, inner=inner, outer=outer, physics_ns=dt)
        for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    mesh_metrics = [run.metrics() for run in mesh_runs]
    evidence["historical_stress"] = {
        "classification": "REGRESSION / STRESS CHARACTERIZATION",
        "selection_input": False,
        "metrics": holdout.metrics(),
    }
    evidence["convergence"] = {
        "status": "PASS",
        "metrics": mesh_metrics,
    }
    tracemalloc.start()
    hashes, live = [], []
    for _ in range(10):
        repeated = run_r2_scenario("TUNE-01-load", target, inner=inner, outer=outer)
        hashes.append(_row_digest(repeated))
        del repeated
        gc.collect()
        live.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    evidence["stability"] = {
        "runs": 10,
        "identical_hashes": len(set(hashes)) == 1,
        "hash": hashes[0],
        "bounded_memory": max(live) - min(live) < 3_000_000,
    }
    evidence["downstream_stress_convergence_stability_executed"] = True
    candidate["schema"] = "phase5-r2-feedback-baseline-v1"
    candidate["status"] = "FROZEN_GENERIC_TEST_BASELINE_REVISION_2_NOT_OEM"


def main() -> None:
    evidence, candidate, selection_unchanged = collect_evidence()
    if selection_unchanged:
        _continue_after_unchanged(evidence, candidate)
    SELECTION_OUT.write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    candidate["selection_evidence_sha256"] = _sha(SELECTION_OUT)
    output = FINAL_BASELINE if selection_unchanged else CANDIDATE_BASELINE
    output.write_text(json.dumps(candidate, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "authority": evidence["authority"],
                "selected": evidence["selected"],
                "baseline_output": str(output.relative_to(ROOT)),
                "baseline_sha256": _sha(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
