"""Run the pre-registered Phase 5R2.1 outer-selection robustness matrix."""

from __future__ import annotations

import gc
import hashlib
import json
import math
import tracemalloc
from dataclasses import asdict
from pathlib import Path

from v0_2.examples.phase5_r1_ownership_audit import collect_audit, static_audit
from v0_2.examples.phase5_r2_evidence import run_r2_scenario

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r2_1_selection_robustness_registration.json"
EVIDENCE = ROOT / "phase5_r2_1_selection_robustness_evidence.json"
FINAL_BASELINE = ROOT / "phase5_r2_feedback_baseline.json"
R1_BASELINE = ROOT / "phase5_r1_feedback_baseline.json"
R2_TARGET_REGISTRATION = ROOT / "phase5_r2_target_registration.json"
R2_SELECTION = ROOT / "phase5_r2_selection_evidence.json"
R2_CANDIDATE = ROOT / "phase5_r2_candidate_baseline.json"
OWNERSHIP_AUDIT = ROOT / "docs/results/phase5_r1_ownership_audit.json"
PLANT_DIRECTORIES = ("thermal", "fluids", "hydraulics", "coolant", "cdu", "plant")
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


def _control_core_sha() -> str:
    return hashlib.sha256(b"".join((ROOT / path).read_bytes() for path in CORE_PATHS)).hexdigest()


def _plant_sha() -> str:
    paths = sorted(
        (
            path
            for directory in PLANT_DIRECTORIES
            for path in (ROOT / "v0_2" / directory).glob("*.py")
            if path.name != "controlled_loop.py"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _row_digest(run) -> str:
    return hashlib.sha256(_canonical([asdict(row) for row in run.rows])).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gains(candidate: dict) -> dict:
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def _integrity(registration: dict) -> dict:
    expected = registration["source_integrity"]
    actual = {
        "phase5_r1_baseline_sha256": _sha(R1_BASELINE),
        "phase5_r2_target_registration_sha256": _sha(R2_TARGET_REGISTRATION),
        "phase5_r2_initial_selection_evidence_sha256": _sha(R2_SELECTION),
        "phase5_r2_candidate_baseline_sha256": _sha(R2_CANDIDATE),
        "r1_control_core_sha256": _control_core_sha(),
        "frozen_plant_sha256": _plant_sha(),
    }
    if actual != expected:
        raise RuntimeError(f"PHASE5_R2_1_BASELINE_INTEGRITY_FAILURE: {actual!r}")
    selection = _load(R2_SELECTION)
    candidate = _load(R2_CANDIDATE)
    if selection["authority"]["target_k"] != registration["target_k"]:
        raise RuntimeError("PHASE5_R2_1_BASELINE_INTEGRITY_FAILURE: target changed")
    if candidate["inner_candidate_id"] != registration["inner_candidate"]["id"]:
        raise RuntimeError("PHASE5_R2_1_BASELINE_INTEGRITY_FAILURE: inner changed")
    if candidate["outer_candidate_id"] != "outer_b":
        raise RuntimeError("PHASE5_R2_1_BASELINE_INTEGRITY_FAILURE: coarse selection changed")
    return {"status": "PASS", "expected": expected, "actual": actual}


def _finite(value) -> bool:
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def _run_record(candidate: dict, dt_ns: int, scenario: str, target: float, inner: dict):
    try:
        run = run_r2_scenario(
            scenario,
            target,
            inner=_gains(inner),
            outer=_gains(candidate),
            physics_ns=dt_ns,
        )
        metrics = run.metrics()
        lineage_pass = all(
            command.producer_module == "PLC" and command.plc_cycle_id
            for command in run.actuator_commands
        )
        failed_reasons = []
        if not _finite(metrics):
            failed_reasons.append("NONFINITE")
        if metrics["max_mass_residual_kg_s"] >= 1e-8:
            failed_reasons.append("MASS")
        if metrics["max_energy_residual_j"] >= 0.001:
            failed_reasons.append("ENERGY")
        if metrics["minimum_headroom_k"] < -5.0:
            failed_reasons.append("HEADROOM")
        if metrics["safety_fault_event_count"] > 0:
            failed_reasons.append("SAFETY_FAULT")
        if not lineage_pass:
            failed_reasons.append("OWNERSHIP")
        return {
            "candidate_id": candidate["id"],
            "physics_dt_ns": dt_ns,
            "scenario_id": scenario,
            "status": "PASS" if not failed_reasons else "FEASIBILITY_FAIL",
            "failed_reasons": failed_reasons,
            "ownership_lineage_pass": lineage_pass,
            "metrics": metrics,
        }, run
    except Exception as exc:  # noqa: BLE001 - retain an invalid matrix cell as evidence
        return {
            "candidate_id": candidate["id"],
            "physics_dt_ns": dt_ns,
            "scenario_id": scenario,
            "status": "FEASIBILITY_FAIL",
            "failed_reasons": ["EXCEPTION"],
            "error": f"{type(exc).__name__}: {exc}",
            "ownership_lineage_pass": False,
            "metrics": None,
        }, None


def _aggregate(records: list[dict], candidate_id: str, dt_ns: int) -> dict:
    selected = [
        record
        for record in records
        if record["candidate_id"] == candidate_id and record["physics_dt_ns"] == dt_ns
    ]
    feasible = len(selected) == 4 and all(record["status"] == "PASS" for record in selected)
    if not feasible:
        return {
            "candidate_id": candidate_id,
            "physics_dt_ns": dt_ns,
            "feasibility_failed": True,
            "thermal_iae": None,
            "control_total_variation": None,
            "pump_electrical_j": None,
        }
    return {
        "candidate_id": candidate_id,
        "physics_dt_ns": dt_ns,
        "feasibility_failed": False,
        "thermal_iae": sum(record["metrics"]["temperature_iae_k_s"] for record in selected),
        "control_total_variation": sum(
            record["metrics"]["control_total_variation"] for record in selected
        ),
        "pump_electrical_j": sum(record["metrics"]["pump_electrical_j"] for record in selected),
    }


def _score(aggregate: dict) -> tuple:
    return (
        aggregate["feasibility_failed"],
        aggregate["thermal_iae"] if aggregate["thermal_iae"] is not None else math.inf,
        (
            aggregate["control_total_variation"]
            if aggregate["control_total_variation"] is not None
            else math.inf
        ),
        (
            aggregate["pump_electrical_j"]
            if aggregate["pump_electrical_j"] is not None
            else math.inf
        ),
        aggregate["candidate_id"],
    )


def _candidate_sensitivity(by_key: dict, candidate_id: str) -> dict:
    iae = {dt: by_key[(candidate_id, dt)]["thermal_iae"] for dt in by_key_dt()}
    coarse = abs(iae[200_000_000] - iae[100_000_000])
    fine = abs(iae[100_000_000] - iae[50_000_000])
    return {
        "candidate_id": candidate_id,
        "iae_by_dt_ns": {str(key): value for key, value in iae.items()},
        "coarse_pair_difference": coarse,
        "fine_pair_difference": fine,
        "acceptable": fine <= coarse,
    }


def by_key_dt() -> tuple[int, int, int]:
    return (200_000_000, 100_000_000, 50_000_000)


def _pairwise(by_key: dict, sensitivities: dict, left: str, right: str) -> dict:
    deltas = {
        dt: by_key[(left, dt)]["thermal_iae"] - by_key[(right, dt)]["thermal_iae"]
        for dt in by_key_dt()
    }
    bound = (
        sensitivities[left]["fine_pair_difference"] + sensitivities[right]["fine_pair_difference"]
    )
    fine_difference = abs(deltas[50_000_000])
    return {
        "pair": f"{left}_minus_{right}",
        "delta_by_dt_ns": {str(key): value for key, value in deltas.items()},
        "numerical_uncertainty_bound": bound,
        "fine_mesh_absolute_difference": fine_difference,
        "distinguishable": fine_difference > bound,
    }


def _select_final(by_key: dict, pairwise: list[dict]) -> tuple[str, str, list[str]]:
    fine = [by_key[(candidate, 50_000_000)] for candidate in ("outer_a", "outer_b", "outer_c")]
    feasible = [item for item in fine if not item["feasibility_failed"]]
    if not feasible:
        return "", "NO_FEASIBLE_CANDIDATE", []
    raw_best = min(feasible, key=_score)
    pair_map = {item["pair"]: item for item in pairwise}
    thermal_equivalent = [raw_best["candidate_id"]]
    for item in feasible:
        candidate = item["candidate_id"]
        if candidate == raw_best["candidate_id"]:
            continue
        direct = f"{candidate}_minus_{raw_best['candidate_id']}"
        reverse = f"{raw_best['candidate_id']}_minus_{candidate}"
        comparison = pair_map.get(direct) or pair_map.get(reverse)
        if comparison is not None and not comparison["distinguishable"]:
            thermal_equivalent.append(candidate)
    if len(thermal_equivalent) == 1:
        return raw_best["candidate_id"], "THERMAL_IAE_DISTINGUISHABLE", thermal_equivalent
    finalists = [item for item in feasible if item["candidate_id"] in thermal_equivalent]
    selected = min(
        finalists,
        key=lambda item: (
            item["control_total_variation"],
            item["pump_electrical_j"],
            item["candidate_id"],
        ),
    )
    return selected["candidate_id"], "NUMERICALLY_INDISTINGUISHABLE_TIE_BREAK", thermal_equivalent


def _convergence(metrics: list[dict], tolerances: dict) -> dict:
    coarse, medium, fine = metrics
    differences = {
        "peak_device_k": abs(medium["peak_device_k"] - fine["peak_device_k"]),
        "temperature_iae_k_s": abs(medium["temperature_iae_k_s"] - fine["temperature_iae_k_s"]),
        "dp_tracking_iae_pa_s": abs(medium["dp_tracking_iae_pa_s"] - fine["dp_tracking_iae_pa_s"]),
        "pump_electrical_relative": abs(medium["pump_electrical_j"] - fine["pump_electrical_j"])
        / max(abs(fine["pump_electrical_j"]), 1e-12),
        "saturation_duration_s": abs(
            medium["saturation_duration_s"] - fine["saturation_duration_s"]
        ),
        "control_total_variation": abs(
            medium["control_total_variation"] - fine["control_total_variation"]
        ),
        "actuator_tracking_iae_fraction_s": abs(
            medium["actuator_tracking_iae_fraction_s"] - fine["actuator_tracking_iae_fraction_s"]
        ),
    }
    return {
        "status": (
            "PASS" if all(differences[key] <= tolerances[key] for key in differences) else "FAIL"
        ),
        "coarse_metrics": coarse,
        "medium_metrics": medium,
        "fine_metrics": fine,
        "fine_pair_differences": differences,
        "tolerances": tolerances,
    }


def main() -> None:
    registration = _load(REGISTRATION)
    integrity = _integrity(registration)
    target = registration["target_k"]
    inner = registration["inner_candidate"]
    candidates = registration["outer_candidates"]
    records = []
    for candidate in candidates:
        for dt_ns in registration["physics_dt_ns"]:
            for scenario in registration["training_ids"]:
                record, _ = _run_record(candidate, dt_ns, scenario, target, inner)
                records.append(record)

    aggregates = [
        _aggregate(records, candidate["id"], dt_ns)
        for candidate in candidates
        for dt_ns in registration["physics_dt_ns"]
    ]
    by_key = {(item["candidate_id"], item["physics_dt_ns"]): item for item in aggregates}
    raw_winners = {
        str(dt_ns): min((by_key[(candidate["id"], dt_ns)] for candidate in candidates), key=_score)[
            "candidate_id"
        ]
        for dt_ns in registration["physics_dt_ns"]
    }
    sensitivities = {
        candidate["id"]: _candidate_sensitivity(by_key, candidate["id"]) for candidate in candidates
    }
    pairwise = [
        _pairwise(by_key, sensitivities, "outer_a", "outer_b"),
        _pairwise(by_key, sensitivities, "outer_a", "outer_c"),
        _pairwise(by_key, sensitivities, "outer_b", "outer_c"),
    ]
    final_candidate, selection_reason, thermal_equivalent = _select_final(by_key, pairwise)
    all_runs_pass = len(records) == 36 and all(record["status"] == "PASS" for record in records)
    candidate_convergence_pass = all(item["acceptable"] for item in sensitivities.values())
    audit = collect_audit()
    ownership = {
        "static": static_audit(),
        "runtime": audit["runtime"],
        "frozen_audit_sha256": _sha(OWNERSHIP_AUDIT),
        "matrix_lineage_pass": all(record["ownership_lineage_pass"] for record in records),
    }
    ownership_pass = (
        ownership["static"]["status"] == "PASS"
        and ownership["runtime"]["status"] == "PASS"
        and ownership["matrix_lineage_pass"]
    )

    evidence = {
        "schema": "phase5-r2-1-selection-robustness-evidence-v1",
        "registration_sha256": _sha(REGISTRATION),
        "integrity": integrity,
        "target_k": target,
        "run_matrix": records,
        "run_matrix_summary": {
            "expected_runs": 36,
            "completed_runs": len(records),
            "passing_runs": sum(record["status"] == "PASS" for record in records),
            "invalid_runs": sum(record["status"] != "PASS" for record in records),
        },
        "aggregates": aggregates,
        "raw_winners_by_dt_ns": raw_winners,
        "candidate_sensitivity": list(sensitivities.values()),
        "pairwise": pairwise,
        "selection": {
            "candidate_id": final_candidate,
            "reason": selection_reason,
            "thermal_equivalent_set": thermal_equivalent,
            "same_as_coarse_r2": final_candidate == "outer_b",
        },
        "ownership": ownership,
        "candidate_convergence_pass": candidate_convergence_pass,
        "holdout_used_in_selection": False,
        "historical_stress": {"status": "NOT_EXECUTED"},
        "selected_baseline_convergence": {"status": "NOT_EXECUTED"},
        "repeated_stability": {"status": "NOT_EXECUTED"},
    }

    freeze_allowed = (
        all_runs_pass
        and candidate_convergence_pass
        and ownership_pass
        and final_candidate == "outer_b"
    )
    if freeze_allowed:
        selected = next(candidate for candidate in candidates if candidate["id"] == final_candidate)
        stress = run_r2_scenario(
            registration["holdout_policy"]["scenario_id"],
            target,
            inner=_gains(inner),
            outer=_gains(selected),
        )
        evidence["historical_stress"] = {
            "status": "PASS",
            "classification": "HISTORICAL STRESS CHARACTERIZATION",
            "selection_input": False,
            "metrics": stress.metrics(),
        }
        convergence_runs = [
            run_r2_scenario(
                "TUNE-01-load",
                target,
                inner=_gains(inner),
                outer=_gains(selected),
                physics_ns=dt_ns,
            )
            for dt_ns in registration["physics_dt_ns"]
        ]
        evidence["selected_baseline_convergence"] = _convergence(
            [run.metrics() for run in convergence_runs],
            registration["selected_baseline_convergence_policy"]["fine_pair_tolerances"],
        )
        tracemalloc.start()
        hashes = []
        live_memory = []
        for _ in range(registration["repeated_stability_runs"]):
            repeated = run_r2_scenario(
                "TUNE-01-load", target, inner=_gains(inner), outer=_gains(selected)
            )
            hashes.append(_row_digest(repeated))
            del repeated
            gc.collect()
            live_memory.append(tracemalloc.get_traced_memory()[0])
        tracemalloc.stop()
        evidence["repeated_stability"] = {
            "status": (
                "PASS"
                if len(set(hashes)) == 1 and max(live_memory) - min(live_memory) < 3_000_000
                else "FAIL"
            ),
            "runs": len(hashes),
            "identical_hashes": len(set(hashes)) == 1,
            "hash": hashes[0],
            "bounded_memory": max(live_memory) - min(live_memory) < 3_000_000,
            "live_memory_span_bytes": max(live_memory) - min(live_memory),
        }
        freeze_allowed = (
            evidence["historical_stress"]["status"] == "PASS"
            and evidence["selected_baseline_convergence"]["status"] == "PASS"
            and evidence["repeated_stability"]["status"] == "PASS"
        )

    evidence["status"] = (
        "PASS_FINAL_R2_BASELINE_FREEZE"
        if freeze_allowed
        else "FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS"
        if final_candidate != "outer_b"
        else "PHASE5_R2_1_VALIDATION_FAILURE"
    )
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    if freeze_allowed:
        baseline = _load(R2_CANDIDATE)
        baseline.update(
            {
                "schema": "phase5-r2-feedback-baseline-v1",
                "status": "FROZEN_GENERIC_TEST_BASELINE_REVISION_2_NOT_OEM",
                "revision": 2,
                "thermal_control_target_k": target,
                "inner_candidate_id": "inner_b",
                "outer_candidate_id": "outer_b",
                "inner_gains": _gains(inner),
                "outer_gains": _gains(
                    next(candidate for candidate in candidates if candidate["id"] == "outer_b")
                ),
                "target_derivation_evidence_sha256": _sha(R2_SELECTION),
                "r2_initial_selection_evidence_sha256": _sha(R2_SELECTION),
                "r2_1_robustness_registration_sha256": _sha(REGISTRATION),
                "r2_1_robustness_evidence_sha256": _sha(EVIDENCE),
                "code_sha256": _control_core_sha(),
            }
        )
        FINAL_BASELINE.write_text(
            json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    elif FINAL_BASELINE.exists():
        raise RuntimeError("Refusing to leave an unauthorized final R2 baseline")

    print(
        json.dumps(
            {
                "status": evidence["status"],
                "registration_sha256": _sha(REGISTRATION),
                "evidence_sha256": _sha(EVIDENCE),
                "raw_winners_by_dt_ns": raw_winners,
                "selection": evidence["selection"],
                "baseline_created": FINAL_BASELINE.exists(),
                "baseline_sha256": _sha(FINAL_BASELINE) if FINAL_BASELINE.exists() else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
