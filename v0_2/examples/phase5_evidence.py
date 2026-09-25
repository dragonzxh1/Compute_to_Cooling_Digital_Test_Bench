"""Reproducible Phase 5 tuning and qualification, all generic numerical fixtures."""

import gc
import hashlib
import json
import tracemalloc
from dataclasses import asdict
from itertools import pairwise

from v0_2.examples.phase5_validation import REGISTRATION, ROOT, run_scenario

OUT = ROOT / "docs" / "results"
BASELINE = ROOT / "phase5_feedback_baseline.json"


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


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


def _training(candidate, other, scenarios, *, inner_candidate):
    rows = []
    for scenario in scenarios:
        run = run_scenario(
            scenario,
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


def _gains(candidate):
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def _row_digest(run):
    return digest([asdict(row) for row in run.rows])


def _convergence(inner, outer):
    runs = [run_scenario("TUNE-01-load", inner=inner, outer=outer, physics_ns=dt) for dt in (200_000_000, 100_000_000, 50_000_000)]
    metrics = [r.metrics() for r in runs]
    if len({tuple(s.next_state.time_ns for s in r.steps) for r in runs}) != 3:
        return {"status": "NOT_EVALUABLE", "reason": "identical effective meshes"}
    fields = {
        "peak_device_k": 0.1,
        "minimum_headroom_k": 0.1,
        "temperature_iae_k_s": 5.0,
        "dp_tracking_iae_pa_s": 10000.0,
        "pump_electrical_j": max(1.0, 0.01 * metrics[-1]["pump_electrical_j"]),
        "saturation_duration_s": 0.2,
        "control_total_variation": 0.01,
    }
    adjacent = [
        {key: abs(a[key] - b[key]) for key in fields}
        for a, b in pairwise(metrics)
    ]
    passed = all(
        adjacent[0][key] <= tolerance and adjacent[1][key] <= tolerance
        and (adjacent[1][key] <= adjacent[0][key] or max(adjacent[0][key], adjacent[1][key]) <= 0.1 * tolerance)
        for key, tolerance in fields.items()
    )
    return {"status": "PASS" if passed else "FAIL", "metrics": metrics, "adjacent": adjacent, "tolerances": fields, "effective_steps": [len(r.steps) for r in runs]}


def collect_evidence():
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    scenarios = registration["training_ids"]
    fixed_outer = _gains(registration["outer_candidates"][0])
    inner_results = [
        _training(candidate, fixed_outer, scenarios, inner_candidate=True)
        for candidate in registration["inner_candidates"]
    ]
    selected_inner = min(inner_results, key=lambda x: x["selection_score"])["candidate"]
    outer_results = [
        _training(candidate, _gains(selected_inner), scenarios, inner_candidate=False)
        for candidate in registration["outer_candidates"]
    ]
    selected_outer = min(outer_results, key=lambda x: x["selection_score"])["candidate"]
    inner, outer = _gains(selected_inner), _gains(selected_outer)
    # Holdout is run only after both gain selections and is never fed into either score.
    holdout = run_scenario(registration["holdout_ids"][0], inner=inner, outer=outer)
    convergence = _convergence(inner, outer)
    tracemalloc.start()
    repeats, live_bytes = [], []
    for _ in range(10):
        run = run_scenario("TUNE-01-load", inner=inner, outer=outer)
        repeats.append(_row_digest(run))
        del run
        gc.collect()
        live_bytes.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    stability = {
        "runs": len(repeats),
        "identical_hashes": len(set(repeats)) == 1,
        "hash": repeats[0],
        "live_bytes": live_bytes,
        "bounded_memory": max(live_bytes) - min(live_bytes) < 3_000_000,
    }
    paths = [
        ROOT / "v0_2" / "control" / "pid.py",
        ROOT / "v0_2" / "control" / "inner_loop.py",
        ROOT / "v0_2" / "control" / "outer_feedback.py",
        ROOT / "v0_2" / "plant" / "controlled_loop.py",
        ROOT / "v0_2" / "actuators" / "pump.py",
        ROOT / "v0_2" / "measurement" / "local_sensor.py",
        ROOT / "v0_2" / "safety" / "supervisor.py",
    ]
    code_hash = hashlib.sha256(b"".join(x.read_bytes() for x in paths)).hexdigest()
    baseline = {
        "schema": "phase5-feedback-baseline-v1",
        "status": "FROZEN_GENERIC_TEST_BASELINE_NOT_OEM",
        "inner_gains": inner,
        "outer_gains": outer,
        "inner_candidate_id": selected_inner["id"],
        "outer_candidate_id": selected_outer["id"],
        "sample_period_ns": 200_000_000,
        "outer_period_ns": 1_000_000_000,
        "plc_period_ns": 200_000_000,
        "actuator_period_ns": 200_000_000,
        "actuator": asdict(holdout.actuator_config),
        "sensor": asdict(holdout.sensor_config),
        "safety": asdict(holdout.safety_policy),
        "thermal_control_target_k": holdout.outer_config.target_k,
        "base_dp_pa": holdout.outer_config.base_dp_pa,
        "tuning_registration_sha256": hashlib.sha256(REGISTRATION.read_bytes()).hexdigest(),
        "training_ids": scenarios,
        "holdout_ids": registration["holdout_ids"],
        "code_sha256": code_hash,
    }
    evidence = {
        "provenance": "GENERIC NUMERICAL FIXTURE; NOT GB300/OEM/Safety validated",
        "registration_sha256": baseline["tuning_registration_sha256"],
        "inner_training": inner_results,
        "outer_training": outer_results,
        "selected": {"inner": selected_inner["id"], "outer": selected_outer["id"]},
        "holdout": {"metrics": holdout.metrics(), "events": holdout.events, "rows": [asdict(row) for row in holdout.rows]},
        "convergence": convergence,
        "stability": stability,
        "baseline": baseline,
    }
    return evidence


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = collect_evidence()
    (OUT / "phase5_evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    BASELINE.write_text(json.dumps(evidence["baseline"], indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"selected": evidence["selected"], "holdout": evidence["holdout"]["metrics"], "convergence": evidence["convergence"]["status"], "stability": evidence["stability"]}, indent=2))


if __name__ == "__main__":
    main()
