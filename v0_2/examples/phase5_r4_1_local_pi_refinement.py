"""Execute the pre-registered Phase 5R4.1 local outer-PI search."""

from __future__ import annotations

import hashlib
import json
from functools import cmp_to_key
from itertools import pairwise
from pathlib import Path

from v0_2.examples import phase5_1r2_qualification as qualification
from v0_2.examples import phase5_r4_outer_tuning as r4
from v0_2.examples.phase5_r1_ownership_audit import collect_audit

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r4_1_local_pi_refinement_registration.json"
EVIDENCE = ROOT / "phase5_r4_1_local_pi_refinement_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r4_1_candidate_baseline.json"
FIGURE = ROOT / "docs/results/phase5_r4_1_local_pi_refinement.png"
SOURCE_R4_REGISTRATION = r4.REGISTRATION
SOURCE_R4_EVIDENCE = r4.EVIDENCE
EXPECTED_REGISTRATION_SHA256 = "87ee1de2312de45fe598712f951c3e08621a06f68dbf5f64bceb98c46cdf8925"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_grid() -> list[dict]:
    return [
        {"id": f"R41-KP{kp}-KI{ki}", "kp": float(kp), "ki": float(ki), "kd": 0.0}
        for kp in (2500, 3000, 3500, 4000, 4500, 5000)
        for ki in (100, 105, 110, 115, 120)
    ]


def _integrity(registration: dict) -> dict:
    old = _load(SOURCE_R4_REGISTRATION)
    frozen = (
        "target_k", "inner", "training_cases", "workload_w_per_device", "preparation",
        "qualification_duration_ns", "final_window_start_ns", "final_window_end_ns",
        "settling", "saturation", "control_direction", "nonphysics_clocks_ns",
        "conservation_limits", "selected_candidate_repeatability",
    )
    checks = {
        "registration_preregistered_sha": _sha(REGISTRATION) == EXPECTED_REGISTRATION_SHA256,
        "r2_sha": _sha(r4.SOURCE_R2) == registration["source_r2_baseline_sha256"],
        "r4_registration_sha": _sha(SOURCE_R4_REGISTRATION) == registration["source_r4_registration_sha256"],
        "r4_evidence_sha": _sha(SOURCE_R4_EVIDENCE) == registration["source_r4_evidence_sha256"],
        "historical_registration_sha": _sha(r4.SOURCE_5_1R2_REGISTRATION) == registration["source_phase5_1r2_registration_sha256"],
        "historical_result_sha": _sha(r4.SOURCE_5_1R2_RESULT) == registration["source_phase5_1r2_result_sha256"],
        "r4_integrity": r4._integrity(old)["status"] == "PASS",
        "frozen_exam": all(registration[key] == old[key] for key in frozen),
        "exact_grid": registration["outer_candidates"] == _expected_grid(),
        "stage_a": registration["stage_a"]["expected_runs"] == 60
        and registration["stage_a"]["physics_dt_ns"] == 200_000_000,
        "stage_b_numeric_rules": all(
            registration["stage_b"][key] == old["stage_b"][key]
            for key in ("maximum_finalists", "physics_dt_ns", "requires_both_cases_pass_all_three_meshes", "adjacent_settling_time_tolerance_s", "fine_pair_continuous_metric_tolerances")
        ),
        "numerical_rule": all(
            registration["numerical_uncertainty_rule"][key] == old["numerical_uncertainty_rule"][key]
            for key in ("comparison_mesh_ns", "sensitivity_pair_ns", "metrics_in_priority_order")
        ),
        "safety_rule": all(
            registration["safety_startup_handling"][key] == old["safety_startup_handling"][key]
            for key in ("policy_unchanged", "startup_ff_disabled_allowed", "common_degraded_reason", "common_degraded_must_be_candidate_independent", "forbidden_states", "noncommon_degraded_is_hard_failure")
        ),
        "no_holdout_or_phase6": registration["holdout_used_for_tuning"] is False
        and registration["phase6_authorized"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_R4_1_INTEGRITY_FAILURE: {checks!r}")
    return {"status": "PASS", "checks": checks}


def _oscillation(trace: list[dict], target: float, band: float, minimum: float, maximum: float, tolerance: float) -> dict:
    lower, upper = target - band, target + band
    inside = [lower <= row["measured_device_k"] <= upper for row in trace]
    first_dwell_end = next(
        (i for i in range(len(trace)) if inside[i] and trace[i]["time_s"] - trace[next((j for j in range(i, -1, -1) if not inside[j]), -1) + 1]["time_s"] >= 15.0),
        None,
    )
    settle_then_exit = first_dwell_end is not None and any(not value for value in inside[first_dwell_end + 1 :])
    one_second = [row for row in trace if row["time_s"] >= 20 and abs(row["time_s"] - round(row["time_s"])) < 1e-8]
    values = [row["measured_device_k"] for row in one_second]
    extrema = [values[i] for i in range(1, len(values) - 1) if (values[i] - values[i - 1]) * (values[i + 1] - values[i]) < 0]
    amplitudes = [abs(b - a) for a, b in pairwise(extrema)]
    growing = len(extrema) >= 4 and amplitudes[-1] > 1.2 * amplitudes[0] and amplitudes[-1] > amplitudes[0] + 0.05
    final = [row for row in trace if row["time_s"] > 150]
    high_entries = sum(row["measured_device_k"] > upper and (i == 0 or final[i - 1]["measured_device_k"] <= upper) for i, row in enumerate(final))
    low_entries = sum(row["measured_device_k"] < lower and (i == 0 or final[i - 1]["measured_device_k"] >= lower) for i, row in enumerate(final))
    both_boundaries = high_entries >= 2 and low_entries >= 2
    limit_states = ["MIN" if row["pump_actual"] <= minimum + tolerance else "MAX" if row["pump_actual"] >= maximum - tolerance else "INTERIOR" for row in final]
    limit_transitions = [state for i, state in enumerate(limit_states) if state != "INTERIOR" and (i == 0 or state != limit_states[i - 1])]
    limit_cycling = len(limit_transitions) >= 4 and len(set(limit_transitions)) == 2 and all(a != b for a, b in pairwise(limit_transitions))
    reasons = [name for name, bad in (
        ("SETTLE_THEN_EXIT", settle_then_exit),
        ("GROWING_OSCILLATION", growing),
        ("FINAL_WINDOW_BOTH_BOUNDARIES", both_boundaries),
        ("PUMP_LIMIT_CYCLING", limit_cycling),
    ) if bad]
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons, "first_dwell_end_s": trace[first_dwell_end]["time_s"] if first_dwell_end is not None else None, "extrema_count": len(extrema), "final_window_high_entries": high_entries, "final_window_low_entries": low_entries, "final_window_limit_transitions": limit_transitions}


def _run(candidate: dict, case: str, dt_ns: int, state, speed: float, registration: dict):
    record, controlled = r4._run(candidate, case, dt_ns, state, speed, registration)
    trace = qualification._trace(controlled) if controlled is not None else []
    record["oscillation"] = _oscillation(trace, registration["target_k"], registration["settling"]["band_k"], registration["saturation"]["minimum_speed_fraction"], registration["saturation"]["maximum_speed_fraction"], registration["saturation"]["bound_tolerance_fraction"]) if trace else {"status": "INVALID", "reasons": ["NO_TRACE"]}
    return record, trace


def _reasons(record: dict, common_startup: bool) -> list[str]:
    return r4._hard_run_reasons(record, common_startup) + record["oscillation"]["reasons"]


def _common_startup(records: list[dict]) -> dict:
    cold = [item for item in records if item["case"] == "COLD_CAPTURE" and item["status"] == "EXECUTED"]
    warm = [item for item in records if item["case"] == "WARM_CAPTURE" and item["status"] == "EXECUTED"]
    expected = (
        (200_000_000, "DEGRADED", ("ACTUATOR_TRACKING_PENDING",)),
        (600_000_000, "FF_DISABLED", ("RECOVERY_QUALIFICATION",)),
        (2_600_000_000, "NORMAL", ()),
    )
    same = len(cold) == 30 and len(warm) == 30 and all(r4._safety_signature(item["metrics"]) == expected for item in cold)
    warm_normal = all(set(item["metrics"]["safety_states"]) <= {"FF_DISABLED", "NORMAL"} for item in warm)
    return {"status": "COMMON_STARTUP_SAFETY_BLOCKER" if same and warm_normal else "NO_COMMON_STARTUP_SIGNATURE", "candidate_independent": same and warm_normal, "cold_degraded_duration_s": 0.4 if same else None, "full_feedback_qualification_pending": same and warm_normal}


def _decisions(registration: dict, records: list[dict], common: bool) -> list[dict]:
    output = []
    for candidate in registration["outer_candidates"]:
        selected = [record for record in records if record["candidate_id"] == candidate["id"]]
        reasons = {record["case"]: _reasons(record, common) for record in selected}
        by_case = {record["case"]: record["metrics"] for record in selected if record["metrics"] is not None}
        score = r4._score(by_case) if len(by_case) == 2 else None
        feasible = len(selected) == 2 and all(not failures for failures in reasons.values())
        warm = not reasons.get("WARM_CAPTURE", ["MISSING"])
        cold = not reasons.get("COLD_CAPTURE", ["MISSING"])
        map_status = "BOTH_PASS" if feasible else "WARM_ONLY" if warm else "COLD_ONLY" if cold else "NEITHER"
        output.append({"candidate_id": candidate["id"], "kp": candidate["kp"], "ki": candidate["ki"], "kd": candidate["kd"], "map_status": map_status, "status": "BIDIRECTIONAL_THERMAL_FEASIBLE" if feasible else "BIDIRECTIONAL_THERMAL_FAIL", "failure_reasons_by_case": reasons, "score": score})
    return output


def _figure(evidence: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    decisions = evidence["stage_a"]["candidate_decisions"]
    statuses = ["NEITHER", "WARM_ONLY", "COLD_ONLY", "BOTH_PASS"]
    kps = [2500, 3000, 3500, 4000, 4500, 5000]
    kis = [100, 105, 110, 115, 120]
    by_gain = {(int(item["kp"]), int(item["ki"])): item["map_status"] for item in decisions}
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    ax = axes[0, 0]
    ax.imshow([[statuses.index(by_gain[(kp, ki)]) for ki in kis] for kp in kps], cmap=ListedColormap(["#dddddd", "#f4a261", "#76b7e5", "#59a66b"]), vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(5), kis)
    ax.set_yticks(range(6), kps)
    ax.set_xlabel("Outer Ki")
    ax.set_ylabel("Outer Kp")
    ax.set_title("Stage A feasibility (grey neither, orange warm, blue cold, green both)")
    for i, kp in enumerate(kps):
        for j, ki in enumerate(kis):
            ax.text(j, i, by_gain[(kp, ki)].replace("_", "\n"), ha="center", va="center", fontsize=7)
    target = evidence["target_k"]
    for case, ax in zip(("WARM_CAPTURE", "COLD_CAPTURE"), (axes[0, 1], axes[1, 0])):
        for candidate_id in evidence["stage_b"]["finalist_ids"]:
            trace = evidence["figure_traces"][candidate_id][case]
            ax.plot([row["time_s"] for row in trace], [row["measured_device_k"] for row in trace], label=candidate_id)
        ax.axhspan(target - 0.5, target + 0.5, alpha=0.15, color="green")
        ax.axhline(target, color="black", linestyle="--", linewidth=1)
        ax.set_title(f"{case} measured temperature")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("K")
        ax.legend(fontsize=7)
    ax = axes[1, 1]
    selected = evidence["selection"]["candidate_id"]
    if selected:
        for case in ("WARM_CAPTURE", "COLD_CAPTURE"):
            trace = evidence["figure_traces"][selected][case]
            ax.plot([row["time_s"] for row in trace], [row["pump_actual"] for row in trace], label=f"{case} pump")
    for item in evidence["stage_a"]["candidate_decisions"]:
        if item["candidate_id"] in evidence["stage_b"]["finalist_ids"]:
            ax.scatter(item["score"]["warm_settling_time_s"], item["score"]["cold_settling_time_s"], label=f"{item['candidate_id']} settling")
    ax.set_xlabel("Time (s) / warm settling (s)")
    ax.set_ylabel("Pump fraction / cold settling (s)")
    ax.set_title("Selected pump speed and finalist settling pairs")
    ax.legend(fontsize=7)
    fig.suptitle("PHASE 5R4.1 — TUNING EVIDENCE, NOT INDEPENDENT VALIDATION")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)


def main() -> None:
    registration = _load(REGISTRATION)
    integrity = _integrity(registration)
    preparations, states = r4._prepare(registration)
    records, traces = [], {}
    for candidate in registration["outer_candidates"]:
        for case in registration["training_cases"]:
            record, trace = _run(candidate, case, 200_000_000, states[case], preparations[case]["speed_fraction"], registration)
            records.append(record)
            traces[(candidate["id"], case)] = trace
        print(f"Stage A {candidate['id']} completed", flush=True)
    common = _common_startup(records)
    decisions = _decisions(registration, records, common["candidate_independent"])
    feasible = sorted((item for item in decisions if item["map_status"] == "BOTH_PASS"), key=r4._score_key)
    finalists = feasible[: registration["stage_b"]["maximum_finalists"]]
    finalist_ids = [item["candidate_id"] for item in finalists]
    fine_records, convergence, comparisons = [], [], []
    selected_id, selection_reason = None, None
    if finalists:
        for item in finalists:
            candidate = next(candidate for candidate in registration["outer_candidates"] if candidate["id"] == item["candidate_id"])
            for dt_ns in registration["stage_b"]["physics_dt_ns"]:
                for case in registration["training_cases"]:
                    record, _ = _run(candidate, case, dt_ns, states[case], preparations[case]["speed_fraction"], registration)
                    fine_records.append(record)
            print(f"Stage B {candidate['id']} completed", flush=True)
        all_records = records + fine_records
        for candidate_id in finalist_ids:
            result = r4._fine_convergence(all_records, registration, candidate_id, common["candidate_independent"])
            selected_records = [record for record in all_records if record["candidate_id"] == candidate_id]
            result["oscillation_all_meshes_pass"] = all(record["oscillation"]["status"] == "PASS" for record in selected_records)
            if not result["oscillation_all_meshes_pass"]:
                result["status"] = "FAIL"
            convergence.append(result)
        robust_ids = [item["candidate_id"] for item in convergence if item["status"] == "PASS"]
        for i, left in enumerate(robust_ids):
            for right in robust_ids[i + 1 :]:
                comparisons.append(r4._uncertainty_comparison(all_records, left, right))
        if robust_ids:
            by_pair = {frozenset(item["pair"]): item for item in comparisons}

            def compare(left: str, right: str) -> int:
                if left == right:
                    return 0
                return -1 if by_pair[frozenset((left, right))]["preferred_candidate"] == left else 1

            ordered = sorted(robust_ids, key=cmp_to_key(compare))
            selected_id = ordered[0]
            selection_reason = "SOLE_ROBUST_BIDIRECTIONAL_CANDIDATE" if len(ordered) == 1 else by_pair[frozenset((ordered[0], ordered[1]))]["selection_reason"]
    all_records = records + fine_records
    invalid = [record for record in all_records if record["status"] == "INVALID" or record["metrics"] is None]
    ownership_audit = collect_audit()
    ownership_pass = ownership_audit["status"] == "PASS" and all(record["metrics"]["ownership_lineage_pass"] for record in all_records if record["metrics"] is not None)
    conservation_pass = all(record["metrics"]["conservation_pass"] for record in all_records if record["metrics"] is not None)
    repeatability = {"status": "NOT_EXECUTED", "reason": "no robust selected candidate"}
    if selected_id:
        selected = next(candidate for candidate in registration["outer_candidates"] if candidate["id"] == selected_id)
        repeated = [r4._repeat_case(selected, case, registration, states[case], preparations[case]["speed_fraction"]) for case in registration["training_cases"]]
        repeatability = {"status": "PASS" if all(item["status"] == "PASS" for item in repeated) else "FAIL", "cases": repeated}
    if not feasible:
        gate = "NO_LOCAL_PI_OVERLAP_REGION_FOUND"
    elif not selected_id or repeatability["status"] != "PASS" or not ownership_pass or not conservation_pass:
        gate = "LOCAL_PI_FINE_MESH_OR_INTEGRITY_FAILURE"
    elif common["candidate_independent"]:
        gate = "LOCAL_PI_CANDIDATE_FOUND_WITH_STARTUP_SAFETY_BLOCKER"
    else:
        gate = "LOCAL_PI_CANDIDATE_FOUND"
    feasibility_map = {str(kp): {str(ki): next(item["map_status"] for item in decisions if item["kp"] == kp and item["ki"] == ki) for ki in (100, 105, 110, 115, 120)} for kp in (2500, 3000, 3500, 4000, 4500, 5000)}
    evidence = {
        "schema": "phase5-r4-1-local-pi-evidence-v1", "status": gate,
        "registration_sha256": _sha(REGISTRATION), "source_r2_baseline_sha256": _sha(r4.SOURCE_R2), "source_r4_evidence_sha256": _sha(SOURCE_R4_EVIDENCE),
        "integrity": integrity, "target_k": registration["target_k"], "inner": registration["inner"], "outer_candidates": registration["outer_candidates"],
        "preparation": preparations, "training_cases_not_independent_validation": True,
        "stage_a": {"expected_runs": 60, "completed_runs": len(records), "invalid_runs": sum(record["status"] == "INVALID" for record in records), "run_matrix": records, "candidate_decisions": decisions, "thermally_feasible_count": len(feasible), "feasible_ranking": [item["candidate_id"] for item in feasible]},
        "feasibility_map": feasibility_map,
        "stage_b": {"status": "EXECUTED" if finalists else "NOT_EXECUTED_NO_STAGE_A_FEASIBLE_CANDIDATE", "finalist_ids": finalist_ids, "expected_runs": 4 * len(finalists), "completed_runs": len(fine_records), "run_matrix": fine_records, "convergence": convergence, "robust_candidate_ids": [item["candidate_id"] for item in convergence if item["status"] == "PASS"]},
        "numerical_uncertainty": {"status": "EXECUTED" if comparisons else "NOT_APPLICABLE_NO_ROBUST_PAIR", "pairwise_comparisons": comparisons},
        "selection_hierarchy": registration["stage_a"]["ranking_hierarchy"], "selection": {"candidate_id": selected_id, "reason": selection_reason, "frozen_final_baseline": False},
        "startup_safety": common, "ownership": {"status": "PASS" if ownership_pass else "FAIL", "audit": ownership_audit},
        "conservation": {"status": "PASS" if conservation_pass else "FAIL", "max_mass_residual_kg_s": max(record["metrics"]["max_mass_residual_kg_s"] for record in all_records if record["metrics"] is not None), "max_energy_residual_j": max(record["metrics"]["max_energy_residual_j"] for record in all_records if record["metrics"] is not None)},
        "invalid_run_count": len(invalid), "repeatability": repeatability, "holdout_used_for_tuning": False, "phase6_authorized": False,
        "figure_traces": {candidate_id: {case: traces[(candidate_id, case)] for case in registration["training_cases"]} for candidate_id in finalist_ids},
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False, default=lambda item: item.item()) + "\n", encoding="utf-8")
    if finalists:
        _figure(evidence)
    if selected_id and repeatability["status"] == "PASS" and ownership_pass and conservation_pass:
        selected = next(candidate for candidate in registration["outer_candidates"] if candidate["id"] == selected_id)
        score = r4._aggregate_by_dt(all_records, selected_id, 200_000_000)
        selected_runs = {record["case"]: record["metrics"] for record in records if record["candidate_id"] == selected_id}
        baseline = {"schema": "phase5-r4-1-candidate-baseline-v1", "status": "CANDIDATE_AWAITING_USER_REVIEW_NOT_FROZEN", "target_k": registration["target_k"], "inner_candidate_id": registration["inner"]["id"], "inner_gains": r4._gains(registration["inner"]), "outer_candidate_id": selected_id, "outer_gains": r4._gains(selected), "selection_reason": selection_reason, **score, "warm_final_window_mean_k": selected_runs["WARM_CAPTURE"]["final_window_mean_measured_k"], "cold_final_window_mean_k": selected_runs["COLD_CAPTURE"]["final_window_mean_measured_k"], "registration_sha256": _sha(REGISTRATION), "evidence_sha256": _sha(EVIDENCE), "source_r2_baseline_sha256": _sha(r4.SOURCE_R2), "source_r4_evidence_sha256": _sha(SOURCE_R4_EVIDENCE), "startup_safety_blocker_status": common["status"], "ownership_status": "PASS", "convergence_status": "PASS", "repeatability_status": repeatability["status"], "training_cases_not_independent_validation": True, "phase6_authorized": False}
        CANDIDATE_BASELINE.write_text(json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    elif CANDIDATE_BASELINE.exists():
        raise RuntimeError("Stale R4.1 candidate baseline exists after no-selection result")
    print(json.dumps({"status": gate, "registration_sha256": _sha(REGISTRATION), "evidence_sha256": _sha(EVIDENCE), "stage_a_runs": len(records), "stage_a_feasible": len(feasible), "finalists": finalist_ids, "stage_b_runs": len(fine_records), "selected_candidate": selected_id, "invalid_runs": len(invalid)}, indent=2))


if __name__ == "__main__":
    main()
