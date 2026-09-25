"""Pre-registered two-stage outer PI tuning on the frozen generic plant."""

from __future__ import annotations

import gc
import hashlib
import json
import sys
from dataclasses import asdict
from functools import cmp_to_key
from math import fsum
from pathlib import Path

from v0_2.examples import phase5_1r2_qualification as qualification
from v0_2.examples.phase5_r1_ownership_audit import collect_audit
from v0_2.examples.phase5_r2_1_robustness import _control_core_sha, _plant_sha

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r4_outer_tuning_registration.json"
EVIDENCE = ROOT / "phase5_r4_outer_tuning_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r4_candidate_baseline.json"
SOURCE_R2 = ROOT / "phase5_r2_feedback_baseline.json"
SOURCE_R3_REGISTRATION = ROOT / "phase5_r3_bidirectional_selection_registration.json"
SOURCE_R3_EVIDENCE = ROOT / "phase5_r3_bidirectional_selection_evidence.json"
SOURCE_5_1R2_REGISTRATION = ROOT / "phase5_1r2_qualification_registration.json"
SOURCE_5_1R2_RESULT = ROOT / "phase5_1r2_nominal_result.json"
EXPECTED_REGISTRATION_SHA256 = "b75eb532e825eea4960956c0812e19eb70ca3055c22a483b5b435f665a1e93b8"
EXPECTED_PLANT_SHA256 = "d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value) -> bytes:
    return qualification._canonical(value)


def _gains(candidate: dict) -> dict:
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def _expected_grid() -> list[dict]:
    return [
        {"id": f"R4-KP{kp}-KI{ki}", "kp": float(kp), "ki": float(ki), "kd": 0.0}
        for kp in (3000, 4000, 5000, 6000)
        for ki in (60, 80, 100, 120)
    ]


def _integrity(registration: dict) -> dict:
    baseline = _load(SOURCE_R2)
    old_registration = _load(SOURCE_5_1R2_REGISTRATION)
    exam_keys = (
        "workload_w_per_device",
        "qualification_duration_ns",
        "final_window_start_ns",
        "final_window_end_ns",
        "settling",
        "saturation",
        "conservation_limits",
    )
    preparation_keys = (
        "duration_ns",
        "physics_dt_ns",
        "warm_speed_fraction",
        "cold_speed_fraction",
        "endpoint_window_start_ns",
        "endpoint_window_end_ns",
        "historical_warm_endpoint_k",
        "historical_cold_endpoint_k",
        "endpoint_reproduction_tolerance_k",
        "controller_prehistory",
        "integrator_warm_start",
    )
    direction_keys = (
        "evaluation_window_ns",
        "minimum_dp_change_pa",
        "minimum_actual_speed_change_fraction",
    )
    checks = {
        "registration_sha256": _sha(REGISTRATION) == EXPECTED_REGISTRATION_SHA256,
        "r2_baseline_sha256": _sha(SOURCE_R2) == registration["source_r2_baseline_sha256"],
        "r3_registration_sha256": _sha(SOURCE_R3_REGISTRATION)
        == registration["source_r3_registration_sha256"],
        "r3_evidence_sha256": _sha(SOURCE_R3_EVIDENCE)
        == registration["source_r3_evidence_sha256"],
        "phase5_1r2_registration_sha256": _sha(SOURCE_5_1R2_REGISTRATION)
        == registration["source_phase5_1r2_registration_sha256"],
        "phase5_1r2_result_sha256": _sha(SOURCE_5_1R2_RESULT)
        == registration["source_phase5_1r2_result_sha256"],
        "r2_lineage": qualification._integrity(old_registration, baseline)["status"] == "PASS",
        "target": registration["target_k"] == baseline["target_k"],
        "inner": registration["inner"]["id"] == baseline["inner_candidate_id"]
        and _gains(registration["inner"]) == baseline["inner_gains"],
        "grid_exact": registration["outer_candidates"] == _expected_grid(),
        "exam_unchanged": all(registration[key] == old_registration[key] for key in exam_keys)
        and all(registration["preparation"][key] == old_registration["preparation"][key] for key in preparation_keys)
        and all(registration["control_direction"][key] == old_registration["control_direction"][key] for key in direction_keys),
        "nonphysics_clocks": registration["nonphysics_clocks_ns"]
        == {key.removesuffix("_ns"): value for key, value in old_registration["nonphysics_clocks"].items()},
        "control_core": _control_core_sha() == baseline["code_sha256"],
        "plant_core": _plant_sha() == EXPECTED_PLANT_SHA256,
        "r3_gate": _load(SOURCE_R3_EVIDENCE)["status"]
        == "NO_EXISTING_OUTER_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION",
        "no_holdout": registration["holdout_used_for_tuning"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_R4_BASELINE_INTEGRITY_FAILURE: {checks!r}")
    return {"status": "PASS", "checks": checks, "registration_sha256": _sha(REGISTRATION), "source_r2_baseline_sha256": _sha(SOURCE_R2), "source_r3_evidence_sha256": _sha(SOURCE_R3_EVIDENCE), "control_core_sha256": _control_core_sha(), "plant_sha256": _plant_sha()}


def _prepare(registration: dict) -> tuple[dict, dict]:
    old = _load(SOURCE_5_1R2_RESULT)["preparation"]
    records, states = {}, {}
    for label, speed in (
        ("WARM_CAPTURE", registration["preparation"]["warm_speed_fraction"]),
        ("COLD_CAPTURE", registration["preparation"]["cold_speed_fraction"]),
    ):
        records[label], states[label] = qualification._prepare(label, speed, registration)
        if records[label]["normalized_initial_state_sha256"] != old[label]["normalized_initial_state_sha256"]:
            raise RuntimeError(f"PHASE5_R4_INITIAL_STATE_MISMATCH: {label}")
    return records, states


def _run(candidate: dict, label: str, dt_ns: int, state, speed: float, registration: dict) -> tuple[dict, object | None]:
    try:
        controlled, metrics = qualification._run_case(
            label,
            dt_ns,
            state,
            speed,
            registration,
            {"inner_gains": _gains(registration["inner"]), "outer_gains": _gains(candidate)},
        )
        return {"candidate_id": candidate["id"], "case": label, "physics_dt_ns": dt_ns, "status": "EXECUTED", "metrics": metrics}, controlled
    except Exception as error:  # noqa: BLE001 - preserve a failed grid cell as evidence
        return {"candidate_id": candidate["id"], "case": label, "physics_dt_ns": dt_ns, "status": "INVALID", "error": f"{type(error).__name__}: {error}", "metrics": None}, None


def _safety_signature(metrics: dict) -> tuple:
    return tuple((event[0], event[1], tuple(event[2])) for event in metrics["safety_events"])


def _common_startup(records: list[dict]) -> dict:
    cold = [item for item in records if item["case"] == "COLD_CAPTURE" and item["status"] == "EXECUTED"]
    warm = [item for item in records if item["case"] == "WARM_CAPTURE" and item["status"] == "EXECUTED"]
    signatures = [_safety_signature(item["metrics"]) for item in cold]
    expected = (
        (200_000_000, "DEGRADED", ("ACTUATOR_TRACKING_PENDING",)),
        (600_000_000, "FF_DISABLED", ("RECOVERY_QUALIFICATION",)),
        (2_600_000_000, "NORMAL", ()),
    )
    same = len(cold) == 16 and len(warm) == 16 and all(signature == expected for signature in signatures)
    warm_normal = all(
        set(item["metrics"]["safety_states"]) <= {"FF_DISABLED", "NORMAL"}
        for item in warm
    )
    return {
        "status": "COMMON_STARTUP_SAFETY_BLOCKER" if same and warm_normal else "NO_COMMON_STARTUP_SIGNATURE",
        "candidate_independent": same and warm_normal,
        "expected_cold_startup_events": [[time, state, list(reasons)] for time, state, reasons in expected],
        "cold_degraded_duration_s": 0.4 if same else None,
        "full_feedback_qualification_pending": same and warm_normal,
    }


def _hard_run_reasons(record: dict, common_startup: bool) -> list[str]:
    if record["status"] != "EXECUTED" or record["metrics"] is None:
        return ["SOLVER_OR_RUN_INVALID"]
    m = record["metrics"]
    checks = {
        "NONFINITE": qualification._finite(m),
        "NO_SETTLING": m["settling_pass"],
        "FINAL_WINDOW_TEMPERATURE": m["final_window_pass"],
        "FINAL_SATURATION": m["final_saturation_pass"],
        "CONTROL_SIGN": m["control_direction_pass"],
        "CONSERVATION": m["conservation_pass"],
        "OWNERSHIP": m["ownership_lineage_pass"],
        "FORBIDDEN_SAFETY_STATE": not any(
            state in m["safety_states"] for state in ("DERATE_REQUESTED", "PROTECTED", "FAULT")
        ),
        "NONCOMMON_DEGRADED": "DEGRADED" not in m["safety_states"] or common_startup,
    }
    return [name for name, passed in checks.items() if not passed]


def _score(metrics_by_case: dict[str, dict]) -> dict:
    warm = metrics_by_case["WARM_CAPTURE"]
    cold = metrics_by_case["COLD_CAPTURE"]
    return {
        "warm_settling_time_s": warm["settling_time_s"],
        "cold_settling_time_s": cold["settling_time_s"],
        "worst_side_settling_time_s": max(warm["settling_time_s"], cold["settling_time_s"]) if warm["settling_time_s"] is not None and cold["settling_time_s"] is not None else None,
        "warm_temperature_iae_k_s": warm["temperature_iae_k_s"],
        "cold_temperature_iae_k_s": cold["temperature_iae_k_s"],
        "total_temperature_iae_k_s": fsum((warm["temperature_iae_k_s"], cold["temperature_iae_k_s"])),
        "total_control_total_variation": fsum((warm["control_total_variation"], cold["control_total_variation"])),
        "total_pump_electrical_j": fsum((warm["pump_electrical_j"], cold["pump_electrical_j"])),
    }


def _stage_a_decisions(registration: dict, records: list[dict], common_startup: bool) -> list[dict]:
    decisions = []
    for candidate in registration["outer_candidates"]:
        selected = [item for item in records if item["candidate_id"] == candidate["id"]]
        reasons = {item["case"]: _hard_run_reasons(item, common_startup) for item in selected}
        by_case = {item["case"]: item["metrics"] for item in selected if item["metrics"] is not None}
        score = _score(by_case) if len(by_case) == 2 else None
        feasible = len(selected) == 2 and all(not items for items in reasons.values())
        decisions.append({"candidate_id": candidate["id"], "kp": candidate["kp"], "ki": candidate["ki"], "kd": candidate["kd"], "status": "BIDIRECTIONAL_THERMAL_FEASIBLE" if feasible else "BIDIRECTIONAL_THERMAL_FAIL", "failure_reasons_by_case": reasons, "score": score})
    return decisions


def _score_key(decision: dict) -> tuple:
    score = decision["score"]
    return (score["worst_side_settling_time_s"], score["total_temperature_iae_k_s"], score["total_control_total_variation"], score["total_pump_electrical_j"], decision["candidate_id"])


def _fine_convergence(records: list[dict], registration: dict, candidate_id: str, common_startup: bool) -> dict:
    selected = [item for item in records if item["candidate_id"] == candidate_id]
    by_key = {(item["case"], item["physics_dt_ns"]): item for item in selected}
    tolerances = registration["stage_b"]["fine_pair_continuous_metric_tolerances"]
    dts = (200_000_000, 100_000_000, 50_000_000)
    cases = {}
    for label in registration["training_cases"]:
        entries = [by_key.get((label, dt)) for dt in dts]
        if any(item is None or item["metrics"] is None for item in entries):
            cases[label] = {"status": "FAIL", "reason": "MISSING_OR_INVALID_MESH"}
            continue
        metrics = [item["metrics"] for item in entries]
        settling_differences = [
            abs(a["settling_time_s"] - b["settling_time_s"])
            if a["settling_time_s"] is not None and b["settling_time_s"] is not None
            else None
            for a, b in ((metrics[0], metrics[1]), (metrics[1], metrics[2]))
        ]
        medium, fine = metrics[1], metrics[2]
        differences = {
            "peak_device_k": abs(medium["peak_device_k"] - fine["peak_device_k"]),
            "minimum_device_k": abs(medium["minimum_device_k"] - fine["minimum_device_k"]),
            "final_window_mean_measured_k": abs(medium["final_window_mean_measured_k"] - fine["final_window_mean_measured_k"]),
            "temperature_iae_k_s": abs(medium["temperature_iae_k_s"] - fine["temperature_iae_k_s"]),
            "dp_tracking_iae_pa_s": abs(medium["dp_tracking_iae_pa_s"] - fine["dp_tracking_iae_pa_s"]),
            "pump_electrical_relative": abs(medium["pump_electrical_j"] - fine["pump_electrical_j"]) / max(abs(fine["pump_electrical_j"]), 1e-12),
            "control_total_variation": abs(medium["control_total_variation"] - fine["control_total_variation"]),
            "actuator_tracking_iae_fraction_s": abs(medium["actuator_tracking_iae_fraction_s"] - fine["actuator_tracking_iae_fraction_s"]),
            "saturation_duration_s": abs(medium["command_saturation_duration_s"] - fine["command_saturation_duration_s"]),
        }
        run_checks = all(not _hard_run_reasons(item, common_startup) for item in entries)
        time_checks = all(value is not None and value <= registration["stage_b"]["adjacent_settling_time_tolerance_s"] for value in settling_differences)
        continuous_checks = all(differences[key] <= tolerances[key] for key in differences)
        cases[label] = {"status": "PASS" if run_checks and time_checks and continuous_checks else "FAIL", "all_mesh_runs_pass": run_checks, "adjacent_settling_time_differences_s": settling_differences, "fine_pair_differences": differences, "tolerances": tolerances}
    return {"candidate_id": candidate_id, "status": "PASS" if all(item["status"] == "PASS" for item in cases.values()) else "FAIL", "cases": cases}


SCORE_METRICS = (
    "worst_side_settling_time_s",
    "total_temperature_iae_k_s",
    "total_control_total_variation",
    "total_pump_electrical_j",
)


def _aggregate_by_dt(records: list[dict], candidate_id: str, dt_ns: int) -> dict:
    by_case = {item["case"]: item["metrics"] for item in records if item["candidate_id"] == candidate_id and item["physics_dt_ns"] == dt_ns}
    return _score(by_case)


def _uncertainty_comparison(records: list[dict], left: str, right: str) -> dict:
    by_candidate = {
        candidate: {dt: _aggregate_by_dt(records, candidate, dt) for dt in (200_000_000, 100_000_000, 50_000_000)}
        for candidate in (left, right)
    }
    criteria = []
    for metric in SCORE_METRICS:
        a, b = by_candidate[left], by_candidate[right]
        difference = abs(a[200_000_000][metric] - b[200_000_000][metric])
        bound = abs(a[100_000_000][metric] - a[50_000_000][metric]) + abs(b[100_000_000][metric] - b[50_000_000][metric])
        criteria.append({"metric": metric, "canonical_difference": difference, "combined_numerical_uncertainty": bound, "distinguishable": difference > bound})
    decisive = next((item for item in criteria if item["distinguishable"]), None)
    if decisive is None:
        preferred = min(left, right)
        reason = "CANDIDATE_ID_AFTER_UNCERTAINTY_VETO"
    else:
        metric = decisive["metric"]
        preferred = min((left, right), key=lambda candidate: by_candidate[candidate][200_000_000][metric])
        reason = metric
    return {"pair": [left, right], "criteria": criteria, "preferred_candidate": preferred, "selection_reason": reason}


def _repeat_case(candidate: dict, label: str, registration: dict, state, speed: float) -> dict:
    hashes, live_bytes = [], []
    runs = registration["selected_candidate_repeatability"]["warm_runs" if label == "WARM_CAPTURE" else "cold_runs"]
    for _ in range(runs):
        record, controlled = _run(candidate, label, 200_000_000, state, speed, registration)
        if controlled is None or record["status"] != "EXECUTED":
            return {"case": label, "status": "FAIL", "completed_runs": len(hashes), "error": record.get("error")}
        hashes.append(hashlib.sha256(_canonical({"rows": [asdict(row) for row in controlled.rows], "metrics": record["metrics"]})).hexdigest())
        del controlled
        gc.collect()
        live_bytes.append(sum(sys.getsizeof(item) for item in gc.get_objects()))
    memory_span = max(live_bytes) - min(live_bytes)
    passed = len(set(hashes)) == 1 and memory_span < registration["selected_candidate_repeatability"]["retained_memory_span_limit_bytes"]
    return {"case": label, "status": "PASS" if passed else "FAIL", "completed_runs": len(hashes), "identical_hashes": len(set(hashes)) == 1, "result_hash_sha256": hashes[0], "retained_memory_span_bytes": memory_span, "measurement": "post-GC shallow size of GC-tracked live objects"}


def main() -> None:
    registration = _load(REGISTRATION)
    integrity = _integrity(registration)
    preparations, states = _prepare(registration)
    stage_a_records, stage_a_traces = [], {}
    for candidate in registration["outer_candidates"]:
        for label in registration["training_cases"]:
            record, controlled = _run(candidate, label, registration["stage_a"]["physics_dt_ns"], states[label], preparations[label]["speed_fraction"], registration)
            stage_a_records.append(record)
            if controlled is not None:
                stage_a_traces[(candidate["id"], label)] = qualification._trace(controlled)
            del controlled
        print(f"Stage A {candidate['id']} completed", flush=True)
    common = _common_startup(stage_a_records)
    decisions = _stage_a_decisions(registration, stage_a_records, common["candidate_independent"])
    feasible = sorted((item for item in decisions if item["status"] == "BIDIRECTIONAL_THERMAL_FEASIBLE"), key=_score_key)
    finalists = feasible[: registration["stage_b"]["maximum_finalists"]]
    finalist_ids = [item["candidate_id"] for item in finalists]

    stage_b_records, convergence, comparisons = [], [], []
    selected_id, selection_reason = None, None
    if finalists:
        for candidate_id in finalist_ids:
            candidate = next(item for item in registration["outer_candidates"] if item["id"] == candidate_id)
            for dt_ns in registration["stage_b"]["physics_dt_ns"]:
                for label in registration["training_cases"]:
                    record, controlled = _run(candidate, label, dt_ns, states[label], preparations[label]["speed_fraction"], registration)
                    stage_b_records.append(record)
                    del controlled
            print(f"Stage B {candidate_id} completed", flush=True)
        all_records = stage_a_records + stage_b_records
        convergence = [_fine_convergence(all_records, registration, candidate_id, common["candidate_independent"]) for candidate_id in finalist_ids]
        robust_ids = [item["candidate_id"] for item in convergence if item["status"] == "PASS"]
        for i, left in enumerate(robust_ids):
            for right in robust_ids[i + 1 :]:
                comparisons.append(_uncertainty_comparison(all_records, left, right))
        if robust_ids:
            by_pair = {frozenset(item["pair"]): item for item in comparisons}

            def compare(left: str, right: str) -> int:
                if left == right:
                    return 0
                preferred = by_pair[frozenset((left, right))]["preferred_candidate"]
                return -1 if preferred == left else 1

            ordered_ids = sorted(robust_ids, key=cmp_to_key(compare))
            selected_id = ordered_ids[0]
            if len(robust_ids) == 1:
                selection_reason = "SOLE_ROBUST_BIDIRECTIONAL_CANDIDATE"
            else:
                runner_up = ordered_ids[1]
                selection_reason = by_pair[frozenset((selected_id, runner_up))]["selection_reason"]
    all_records = stage_a_records + stage_b_records
    ownership = collect_audit()
    ownership_pass = ownership["status"] == "PASS" and all(item["metrics"]["ownership_lineage_pass"] for item in all_records if item["metrics"] is not None)
    conservation_pass = all(item["metrics"]["conservation_pass"] for item in all_records if item["metrics"] is not None)
    invalid = [item for item in all_records if item["status"] == "INVALID" or item["metrics"] is None]
    repeatability = {"status": "NOT_EXECUTED", "reason": "no selected robust candidate"}
    if selected_id is not None:
        selected_candidate = next(item for item in registration["outer_candidates"] if item["id"] == selected_id)
        repeated = [_repeat_case(selected_candidate, label, registration, states[label], preparations[label]["speed_fraction"]) for label in registration["training_cases"]]
        repeatability = {"status": "PASS" if all(item["status"] == "PASS" for item in repeated) else "FAIL", "cases": repeated}
    if selected_id is None:
        gate = "NO_R4_GRID_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION"
    elif repeatability["status"] != "PASS" or not ownership_pass or not conservation_pass:
        gate = "R4_NUMERICAL_OR_OWNERSHIP_FAILURE"
    elif common["candidate_independent"]:
        gate = "R4_THERMAL_CONTROLLER_FOUND_WITH_STARTUP_SAFETY_BLOCKER"
    else:
        gate = "R4_CONTROLLER_CANDIDATE_FOUND"
    evidence = {
        "schema": "phase5-r4-outer-pi-tuning-evidence-v1",
        "status": gate,
        "registration_sha256": _sha(REGISTRATION),
        "source_r2_baseline_sha256": _sha(SOURCE_R2),
        "source_r3_evidence_sha256": _sha(SOURCE_R3_EVIDENCE),
        "integrity": integrity,
        "target_k": registration["target_k"],
        "inner": registration["inner"],
        "outer_candidates": registration["outer_candidates"],
        "preparation": preparations,
        "training_cases_not_independent_validation": True,
        "stage_a": {"expected_runs": 32, "completed_runs": len(stage_a_records), "invalid_runs": sum(item["status"] == "INVALID" for item in stage_a_records), "run_matrix": stage_a_records, "candidate_decisions": decisions, "thermally_feasible_count": len(feasible), "feasible_ranking": [item["candidate_id"] for item in feasible]},
        "stage_b": {"status": "EXECUTED" if finalists else "NOT_EXECUTED_NO_STAGE_A_FEASIBLE_CANDIDATE", "finalist_ids": finalist_ids, "expected_runs": 4 * len(finalists), "completed_runs": len(stage_b_records), "run_matrix": stage_b_records, "convergence": convergence, "robust_candidate_ids": [item["candidate_id"] for item in convergence if item["status"] == "PASS"]},
        "numerical_uncertainty": {"status": "EXECUTED" if comparisons else "NOT_APPLICABLE_NO_ROBUST_FINALIST", "pairwise_comparisons": comparisons},
        "selection_hierarchy": registration["stage_a"]["ranking_hierarchy"],
        "selection": {"candidate_id": selected_id, "reason": selection_reason, "frozen_final_baseline": False},
        "startup_safety": common,
        "ownership": {"status": "PASS" if ownership_pass else "FAIL", "audit": ownership},
        "conservation": {"status": "PASS" if conservation_pass else "FAIL", "max_mass_residual_kg_s": max(item["metrics"]["max_mass_residual_kg_s"] for item in all_records if item["metrics"] is not None), "max_energy_residual_j": max(item["metrics"]["max_energy_residual_j"] for item in all_records if item["metrics"] is not None)},
        "invalid_run_count": len(invalid),
        "repeatability": repeatability,
        "holdout_used_for_tuning": False,
        "phase6_authorized": False,
        "figure_traces": {candidate_id: {label: stage_a_traces[(candidate_id, label)] for label in registration["training_cases"]} for candidate_id in finalist_ids},
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False, default=lambda item: item.item()) + "\n", encoding="utf-8")
    if selected_id is not None and repeatability["status"] == "PASS" and ownership_pass and conservation_pass:
        score = _aggregate_by_dt(all_records, selected_id, 200_000_000)
        selected = next(item for item in registration["outer_candidates"] if item["id"] == selected_id)
        baseline = {"schema": "phase5-r4-candidate-baseline-v1", "status": "CANDIDATE_AWAITING_USER_REVIEW_NOT_FROZEN", "target_k": registration["target_k"], "inner_candidate_id": registration["inner"]["id"], "inner_gains": _gains(registration["inner"]), "outer_candidate_id": selected_id, "outer_gains": _gains(selected), "selection_reason": selection_reason, **score, "registration_sha256": _sha(REGISTRATION), "evidence_sha256": _sha(EVIDENCE), "source_r2_baseline_sha256": _sha(SOURCE_R2), "startup_safety_blocker_status": common["status"], "ownership_status": "PASS", "numerical_robustness_status": "PASS", "training_cases_not_independent_validation": True, "phase6_authorized": False}
        CANDIDATE_BASELINE.write_text(json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    elif CANDIDATE_BASELINE.exists():
        raise RuntimeError("Stale R4 candidate baseline exists after a no-selection result")
    print(json.dumps({"status": gate, "registration_sha256": _sha(REGISTRATION), "evidence_sha256": _sha(EVIDENCE), "stage_a_runs": len(stage_a_records), "stage_a_feasible": len(feasible), "finalists": finalist_ids, "stage_b_runs": len(stage_b_records), "selected_candidate": selected_id, "startup_safety_blocker": common["candidate_independent"], "invalid_runs": len(invalid)}, indent=2))


if __name__ == "__main__":
    main()
