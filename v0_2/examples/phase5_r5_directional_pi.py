"""Pre-registered R5 directional outer PI tuning on the frozen fixture."""

from __future__ import annotations

import gc
import hashlib
import json
import sys
from dataclasses import asdict, replace
from functools import cmp_to_key
from itertools import pairwise
from math import fsum
from pathlib import Path
from unittest.mock import patch

from v0_2.control.directional_outer import DirectionalOuterFeedback
from v0_2.examples import phase5_1r2_qualification as qualification
from v0_2.examples import phase5_r4_1_local_pi_refinement as r41
from v0_2.examples import phase5_r4_2_pi_boundary_search as r42
from v0_2.examples import phase5_r4_outer_tuning as r4
from v0_2.examples.phase5_r1_ownership_audit import collect_audit
from v0_2.plant import controlled_loop

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_directional_pi_registration.json"
EVIDENCE = ROOT / "phase5_r5_directional_pi_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r5_directional_pi_candidate_baseline.json"
FIGURE = ROOT / "docs/results/phase5_r5_directional_pi_tuning.png"
EXPECTED_REGISTRATION_SHA256 = "61f48d159f208ce4ba8a7e5e958ccad31b659e24bfee69f199133fdf2cf52791"


def _candidates(registration: dict) -> list[dict]:
    return [
        {"id": f"R5-KP4500-H{int(hot)}-C{int(cold)}", "kp": 4500.0, "ki_hot": hot, "ki_cold": cold, "kd": 0.0}
        for hot in (110.0, 112.0, 114.0, 116.0)
        for cold in (124.0, 126.0, 128.0, 130.0)
    ]


def _integrity(registration: dict, historical: dict) -> dict:
    r42_registration = r41._load(r42.REGISTRATION)
    r42_evidence = r41._load(r42.EVIDENCE)
    checks = {
        "registration_sha": r41._sha(REGISTRATION) == EXPECTED_REGISTRATION_SHA256,
        "r4_2_registration_sha": r41._sha(r42.REGISTRATION) == registration["source_r4_2_registration_sha256"],
        "r4_2_evidence_sha": r41._sha(r42.EVIDENCE) == registration["source_r4_2_evidence_sha256"],
        "r4_1_registration_sha": r41._sha(r41.REGISTRATION) == registration["source_r4_1_registration_sha256"],
        "r2_baseline_sha": r41._sha(r4.SOURCE_R2) == registration["source_r2_baseline_sha256"],
        "r4_2_integrity": r42._integrity(r42_registration, historical, r41._load(r41.EVIDENCE))["status"] == "PASS",
        "r4_2_gate": r42_evidence["status"] == "NO_PI_OVERLAP_CONFIRMED_IN_R42_DOMAIN",
        "target_inner": registration["target_k"] == historical["target_k"] and registration["inner"] == historical["inner"],
        "fixed_kp_kd": registration["outer_kp"] == 4500.0 and registration["outer_kd"] == 0.0,
        "exact_grid": registration["ki_hot_values"] == [110.0, 112.0, 114.0, 116.0]
        and registration["ki_cold_values"] == [124.0, 126.0, 128.0, 130.0]
        and registration["candidate_count"] == 16,
        "blend_law": registration["directional_law"]["blend_halfwidth_k"] == 0.1
        and registration["directional_law"]["single_integral_state"] is True,
        "frozen_exam": historical["qualification_duration_ns"] == 180_000_000_000
        and historical["settling"]["band_k"] == 0.5
        and historical["settling"]["continuous_dwell_ns"] == 15_000_000_000,
        "stage_a": registration["stage_a"]["expected_runs"] == 32
        and registration["stage_a"]["physics_dt_ns"] == 200_000_000,
        "chatter": registration["blend_audit"]["maximum_complete_traversals"] == 6
        and registration["blend_audit"]["chatter_window_start_ns"] == 120_000_000_000,
        "stage_b": registration["stage_b"]["maximum_finalists"] == 5
        and registration["stage_b"]["physics_dt_ns"] == [100_000_000, 50_000_000],
        "no_holdout_or_phase6": registration["holdout_used_for_tuning"] is False
        and registration["phase6_authorized"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_R5_INTEGRITY_FAILURE: {checks!r}")
    return {"status": "PASS", "checks": checks}


def _run_controlled(candidate: dict, case: str, dt_ns: int, state, speed: float, historical: dict):
    plant, controls = qualification.physical_fixture(branch_count=2, power_each=historical["workload_w_per_device"])
    plant = replace(plant, initial_state=state)
    controls = qualification._controls(controls, speed)
    configs = list(qualification.fixture_configs(r4._gains(historical["inner"]), {"kp": candidate["kp"], "ki": candidate["ki_hot"], "kd": 0.0}, dt_ns))
    configs[3] = replace(configs[3], target_k=historical["target_k"])
    configs[5] = replace(configs[5], control_target_k=historical["target_k"])
    holder = {}

    def directional_factory(config):
        controller = DirectionalOuterFeedback(config, candidate["ki_hot"], candidate["ki_cold"])
        holder["controller"] = controller
        return controller

    with patch.object(controlled_loop, "OuterFeedback", directional_factory):
        controlled = controlled_loop.run_feedback(plant, controls, historical["qualification_duration_ns"], *configs)
    return controlled, qualification._metrics(controlled, historical, case, speed), holder["controller"].ticks


def _blend_audit(ticks: list[dict], rows: tuple, registration: dict) -> dict:
    by_time = {row.time_ns: row for row in rows}
    transitions = []
    for previous, current in pairwise(ticks):
        if previous["region"] != current["region"]:
            before_row = next(row for row in reversed(rows) if row.time_ns < current["time_ns"])
            after_row = by_time[current["time_ns"]]
            transitions.append({
                "time_ns": current["time_ns"], "from": previous["region"], "to": current["region"],
                "ki_eff_before": previous["ki_eff"], "ki_eff_after": current["ki_eff"],
                "integral_before": current["integral_before"], "integral_after": current["integral_after"],
                "accepted_dp_before_pa": before_row.accepted_dp_pa, "accepted_dp_after_pa": after_row.accepted_dp_pa,
                "requested_dp_before_pa": current["requested_dp_before_pa"], "requested_dp_after_pa": current["requested_dp_after_pa"],
                "integral_continuity_pass": current["integral_continuity_pass"],
                "instantaneous_gain_jump_pa": current["instantaneous_gain_jump_pa"],
            })
    final_ticks = [tick for tick in ticks if tick["time_ns"] >= registration["blend_audit"]["chatter_window_start_ns"]]
    last_full, traversals = None, 0
    for tick in final_ticks:
        if tick["region"] in ("HOT", "COLD"):
            if last_full is not None and tick["region"] != last_full:
                traversals += 1
            last_full = tick["region"]
    prior_rows = [row for row in rows if 60_000_000_000 <= row.time_ns <= 120_000_000_000]
    final_rows = [row for row in rows if 120_000_000_000 <= row.time_ns <= 180_000_000_000]
    previous_tv = fsum(abs(a.pump_command - b.pump_command) for a, b in pairwise(prior_rows))
    final_tv = fsum(abs(a.pump_command - b.pump_command) for a, b in pairwise(final_rows))
    growing_tv = traversals >= 4 and final_tv > 1.5 * previous_tv + 0.05
    chatter = traversals > registration["blend_audit"]["maximum_complete_traversals"]
    continuity = all(tick["integral_continuity_pass"] and abs(tick["instantaneous_gain_jump_pa"]) <= 1e-8 for tick in ticks)
    durations = {region: fsum((later["time_ns"] - tick["time_ns"]) / 1e9 for tick, later in pairwise(ticks) if tick["region"] == region) for region in ("HOT", "COLD", "BLEND")}
    reasons = [name for name, bad in (("DIRECTIONAL_GAIN_CHATTER", chatter), ("GROWING_CONTROL_TV", growing_tv), ("INTEGRAL_CONTINUITY_OR_OUTPUT_JUMP", not continuity)) if bad]
    return {
        "status": "PASS" if not reasons else "FAIL", "reasons": reasons,
        "outer_ticks": ticks, "region_transitions": transitions,
        "ki_eff_min": min(tick["ki_eff"] for tick in ticks), "ki_eff_max": max(tick["ki_eff"] for tick in ticks),
        "ki_eff_mean": fsum(tick["ki_eff"] for tick in ticks) / len(ticks),
        "region_duration_s": durations, "complete_directional_traversals_final_60s": traversals,
        "previous_60s_pump_command_tv": previous_tv, "final_60s_pump_command_tv": final_tv,
        "integral_continuity_all_ticks_pass": continuity,
    }


def _run(candidate: dict, case: str, dt_ns: int, state, speed: float, registration: dict, historical: dict):
    try:
        controlled, metrics, ticks = _run_controlled(candidate, case, dt_ns, state, speed, historical)
        trace = qualification._trace(controlled)
        oscillation = r41._oscillation(trace, historical["target_k"], historical["settling"]["band_k"], historical["saturation"]["minimum_speed_fraction"], historical["saturation"]["maximum_speed_fraction"], historical["saturation"]["bound_tolerance_fraction"])
        blend = _blend_audit(ticks, controlled.rows, registration)
        record = {"candidate_id": candidate["id"], "case": case, "physics_dt_ns": dt_ns, "status": "EXECUTED", "metrics": metrics, "oscillation": oscillation, "blend_audit": blend}
        return record, controlled, trace
    except Exception as error:  # noqa: BLE001 - preserve an invalid cell as explicit evidence
        return {"candidate_id": candidate["id"], "case": case, "physics_dt_ns": dt_ns, "status": "INVALID", "error": f"{type(error).__name__}: {error}", "metrics": None, "oscillation": None, "blend_audit": None}, None, []


def _common_startup(records: list[dict]) -> dict:
    cold = [item for item in records if item["case"] == "COLD_CAPTURE" and item["status"] == "EXECUTED"]
    warm = [item for item in records if item["case"] == "WARM_CAPTURE" and item["status"] == "EXECUTED"]
    same = len(cold) == 16 and len(warm) == 16 and all(r4._safety_signature(item["metrics"]) == r42.EXPECTED_COLD_SIGNATURE for item in cold)
    warm_normal = all(set(item["metrics"]["safety_states"]) <= {"FF_DISABLED", "NORMAL"} for item in warm)
    return {"status": "STARTUP_SAFETY_BLOCKER_PENDING" if same and warm_normal else "NO_COMMON_STARTUP_SIGNATURE", "candidate_independent": same and warm_normal, "cold_degraded_duration_s": 0.4 if same else None, "full_feedback_qualification_blocked": same and warm_normal}


def _reasons(record: dict, common_startup: bool) -> list[str]:
    if record["status"] != "EXECUTED":
        return ["SOLVER_OR_RUN_INVALID"]
    return r4._hard_run_reasons(record, common_startup) + record["oscillation"]["reasons"] + record["blend_audit"]["reasons"]


def _score(by_case: dict[str, dict], blend_by_case: dict[str, dict]) -> dict:
    score = r4._score(by_case)
    score["settling_imbalance_s"] = abs(score["warm_settling_time_s"] - score["cold_settling_time_s"]) if score["worst_side_settling_time_s"] is not None else None
    score["total_directional_traversals"] = sum(item["complete_directional_traversals_final_60s"] for item in blend_by_case.values())
    return score


SCORE_FIELDS = ("worst_side_settling_time_s", "settling_imbalance_s", "total_temperature_iae_k_s", "total_control_total_variation", "total_pump_electrical_j", "total_directional_traversals")


def _score_key(decision: dict) -> tuple:
    return tuple(decision["score"][name] for name in SCORE_FIELDS) + (decision["id"],)


def _decisions(registration: dict, candidates: list[dict], records: list[dict], common: bool) -> list[dict]:
    decisions = []
    for candidate in candidates:
        selected = [item for item in records if item["candidate_id"] == candidate["id"]]
        reasons = {item["case"]: _reasons(item, common) for item in selected}
        metrics = {item["case"]: item["metrics"] for item in selected if item["metrics"] is not None}
        blends = {item["case"]: item["blend_audit"] for item in selected if item["blend_audit"] is not None}
        score = _score(metrics, blends) if len(metrics) == 2 else None
        warm = not reasons.get("WARM_CAPTURE", ["MISSING"])
        cold = not reasons.get("COLD_CAPTURE", ["MISSING"])
        chatter = any("DIRECTIONAL_GAIN_CHATTER" in failures for failures in reasons.values())
        map_status = "CHATTER_FAIL" if chatter else "BOTH_PASS" if warm and cold else "WARM_ONLY" if warm else "COLD_ONLY" if cold else "NEITHER"
        decisions.append({**candidate, "status": "BIDIRECTIONAL_THERMAL_FEASIBLE" if warm and cold else "BIDIRECTIONAL_THERMAL_FAIL", "map_status": map_status, "failure_reasons_by_case": reasons, "score": score})
    return decisions


def _convergence(records: list[dict], registration: dict, historical: dict, candidate_id: str, common: bool) -> dict:
    result = r4._fine_convergence(records, historical, candidate_id, common)
    selected = [item for item in records if item["candidate_id"] == candidate_id]
    directional = len(selected) == 6 and all(not _reasons(item, common) for item in selected)
    result["directional_all_meshes_pass"] = directional
    if not directional:
        result["status"] = "FAIL"
    return result


def _uncertainty(records: list[dict], left: str, right: str) -> dict:
    scores = {}
    for candidate_id in (left, right):
        scores[candidate_id] = {}
        for dt_ns in (200_000_000, 100_000_000, 50_000_000):
            selected = [item for item in records if item["candidate_id"] == candidate_id and item["physics_dt_ns"] == dt_ns]
            scores[candidate_id][dt_ns] = _score({item["case"]: item["metrics"] for item in selected}, {item["case"]: item["blend_audit"] for item in selected})
    criteria = []
    for metric in SCORE_FIELDS:
        difference = abs(scores[left][200_000_000][metric] - scores[right][200_000_000][metric])
        uncertainty = sum(abs(scores[candidate][100_000_000][metric] - scores[candidate][50_000_000][metric]) for candidate in (left, right))
        criteria.append({"metric": metric, "canonical_difference": difference, "combined_numerical_uncertainty": uncertainty, "distinguishable": difference > uncertainty})
    decisive = next((item for item in criteria if item["distinguishable"]), None)
    preferred = min((left, right), key=lambda candidate: scores[candidate][200_000_000][decisive["metric"]]) if decisive else min(left, right)
    return {"pair": [left, right], "criteria": criteria, "preferred_candidate": preferred, "selection_reason": decisive["metric"] if decisive else "CANDIDATE_ID_AFTER_UNCERTAINTY_VETO"}


def _repeat(candidate: dict, case: str, registration: dict, historical: dict, state, speed: float) -> dict:
    hashes, retained = [], []
    count = registration["selected_candidate_repeatability"]["warm_runs" if case == "WARM_CAPTURE" else "cold_runs"]
    for _ in range(count):
        record, controlled, _ = _run(candidate, case, 200_000_000, state, speed, registration, historical)
        if controlled is None or record["status"] != "EXECUTED":
            return {"case": case, "status": "FAIL", "completed_runs": len(hashes), "error": record.get("error")}
        hashes.append(hashlib.sha256(qualification._canonical({"rows": [asdict(row) for row in controlled.rows], "metrics": record["metrics"], "blend": record["blend_audit"]})).hexdigest())
        del controlled, record
        gc.collect()
        retained.append(sum(sys.getsizeof(item) for item in gc.get_objects()))
    span = max(retained) - min(retained)
    passed = len(set(hashes)) == 1 and span < registration["selected_candidate_repeatability"]["retained_memory_span_limit_bytes"]
    return {"case": case, "status": "PASS" if passed else "FAIL", "completed_runs": len(hashes), "identical_hashes": len(set(hashes)) == 1, "result_hash_sha256": hashes[0], "retained_memory_span_bytes": span}


def _figure(evidence: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    hot_values = [110, 112, 114, 116]
    cold_values = [124, 126, 128, 130]
    statuses = ["NEITHER", "WARM_ONLY", "COLD_ONLY", "BOTH_PASS", "CHATTER_FAIL"]
    colors = ListedColormap(["#dddddd", "#f4a261", "#76b7e5", "#59a66b", "#b34a4a"])
    fig, axes = plt.subplots(4, 2, figsize=(16, 19))
    ax = axes[0, 0]
    ax.imshow([[statuses.index(evidence["feasibility_map"][str(hot)][str(cold)]) for cold in cold_values] for hot in hot_values], cmap=colors, vmin=0, vmax=4, aspect="auto")
    ax.set_xticks(range(4), cold_values)
    ax.set_yticks(range(4), hot_values)
    ax.set_xlabel("Ki_cold")
    ax.set_ylabel("Ki_hot")
    ax.set_title("Directional PI feasibility map")
    for i, hot in enumerate(hot_values):
        for j, cold in enumerate(cold_values):
            ax.text(j, i, evidence["feasibility_map"][str(hot)][str(cold)].replace("_", "\n"), ha="center", va="center", fontsize=8)
    target = evidence["target_k"]
    for case, ax in zip(("WARM_CAPTURE", "COLD_CAPTURE"), (axes[0, 1], axes[1, 0])):
        for candidate_id in evidence["stage_b"]["finalist_ids"]:
            trace = evidence["figure_traces"][candidate_id][case]
            ax.plot([row["time_s"] for row in trace], [row["measured_device_k"] for row in trace], label=candidate_id)
        ax.axhspan(target - 0.5, target + 0.5, color="green", alpha=0.12, label="±0.5 K")
        ax.axhspan(target - 0.1, target + 0.1, color="blue", alpha=0.12, label="±0.1 K blend")
        ax.axhline(target, color="black", linestyle="--")
        ax.set_title(f"{case}: released measured temperature")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("K")
        ax.legend(fontsize=7)
    selected = evidence["selection"]["candidate_id"] or evidence["stage_b"]["finalist_ids"][0]
    for case, row_index in (("WARM_CAPTURE", 2), ("COLD_CAPTURE", 3)):
        trace = evidence["figure_traces"][selected][case]
        ticks = evidence["selected_or_first_finalist_ticks"][case]
        ax = axes[row_index, 0]
        ax.plot([tick["time_ns"] / 1e9 for tick in ticks], [tick["ki_eff"] for tick in ticks], label="Ki_eff")
        ax2 = ax.twinx()
        ax2.plot([tick["time_ns"] / 1e9 for tick in ticks], [tick["integral_after"] for tick in ticks], color="purple", alpha=0.65, label="Integral state")
        ax.set_title(f"{case}: effective Ki and one integral state")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Ki_eff")
        ax2.set_ylabel("Integral state (Pa)")
        ax = axes[row_index, 1]
        for field in ("pump_command", "pump_actual", "pump_measured"):
            ax.plot([row["time_s"] for row in trace], [row[field] for row in trace], label=field)
        ax.set_title(f"{case}: pump command, actual, measured")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Speed fraction")
        ax.legend(fontsize=7)
    ax = axes[1, 1]
    safety_trace = evidence["figure_traces"][selected]["COLD_CAPTURE"]
    states = {"NORMAL": 0, "FF_DISABLED": 1, "DEGRADED": 2, "DERATE_REQUESTED": 3, "PROTECTED": 4, "FAULT": 5}
    ax.step([row["time_s"] for row in safety_trace], [states[row["safety_state"]] for row in safety_trace], where="post")
    ax.set_yticks(list(states.values()), list(states))
    ax.set_title("Cold-start Safety timeline")
    ax.set_xlabel("Time (s)")
    fig.suptitle("DIRECTIONAL PI TUNING EVIDENCE — NOT INDEPENDENT VALIDATION — NOT OEM / NVIDIA / GB300 VALIDATION", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)


def main() -> None:
    registration = r41._load(REGISTRATION)
    historical = r41._load(r41.REGISTRATION)
    integrity = _integrity(registration, historical)
    preparations, states = r4._prepare(historical)
    candidates = _candidates(registration)
    stage_a, traces = [], {}
    for candidate in candidates:
        for case in registration["training_cases"]:
            record, controlled, trace = _run(candidate, case, 200_000_000, states[case], preparations[case]["speed_fraction"], registration, historical)
            stage_a.append(record)
            traces[(candidate["id"], case)] = trace
            del controlled
        print(f"Stage A {candidate['id']} completed", flush=True)
    common = _common_startup(stage_a)
    decisions = _decisions(registration, candidates, stage_a, common["candidate_independent"])
    feasible = sorted((item for item in decisions if item["status"] == "BIDIRECTIONAL_THERMAL_FEASIBLE"), key=_score_key)
    finalists = feasible[: registration["stage_b"]["maximum_finalists"]]
    finalist_ids = [item["id"] for item in finalists]
    stage_b, convergence, comparisons = [], [], []
    selected_id, selection_reason = None, None
    if finalists:
        for item in finalists:
            candidate = next(value for value in candidates if value["id"] == item["id"])
            for dt_ns in registration["stage_b"]["physics_dt_ns"]:
                for case in registration["training_cases"]:
                    record, controlled, _ = _run(candidate, case, dt_ns, states[case], preparations[case]["speed_fraction"], registration, historical)
                    stage_b.append(record)
                    del controlled
            print(f"Stage B {candidate['id']} completed", flush=True)
        all_records = stage_a + stage_b
        convergence = [_convergence(all_records, registration, historical, candidate_id, common["candidate_independent"]) for candidate_id in finalist_ids]
        robust = [item["candidate_id"] for item in convergence if item["status"] == "PASS"]
        for i, left in enumerate(robust):
            for right in robust[i + 1 :]:
                comparisons.append(_uncertainty(all_records, left, right))
        if robust:
            by_pair = {frozenset(item["pair"]): item for item in comparisons}

            def compare(left: str, right: str) -> int:
                if left == right:
                    return 0
                return -1 if by_pair[frozenset((left, right))]["preferred_candidate"] == left else 1

            ordered = sorted(robust, key=cmp_to_key(compare))
            selected_id = ordered[0]
            selection_reason = "SOLE_ROBUST_DIRECTIONAL_CANDIDATE" if len(ordered) == 1 else by_pair[frozenset((ordered[0], ordered[1]))]["selection_reason"]
    all_records = stage_a + stage_b
    invalid = [item for item in all_records if item["status"] == "INVALID" or item["metrics"] is None]
    ownership_audit = collect_audit()
    ownership_pass = ownership_audit["status"] == "PASS" and all(item["metrics"]["ownership_lineage_pass"] for item in all_records if item["metrics"] is not None)
    conservation_pass = all(item["metrics"]["conservation_pass"] for item in all_records if item["metrics"] is not None)
    repeatability = {"status": "NOT_EXECUTED", "reason": "no robust selected candidate"}
    if selected_id:
        selected = next(item for item in candidates if item["id"] == selected_id)
        repeated = [_repeat(selected, case, registration, historical, states[case], preparations[case]["speed_fraction"]) for case in registration["training_cases"]]
        repeatability = {"status": "PASS" if all(item["status"] == "PASS" for item in repeated) else "FAIL", "cases": repeated}
    if not feasible:
        gate = "NO_R5_DIRECTIONAL_PI_CANDIDATE_FOUND"
    elif not selected_id or repeatability["status"] != "PASS" or not ownership_pass or not conservation_pass:
        gate = "R5_FINE_MESH_OR_INTEGRITY_FAILURE"
    elif common["candidate_independent"]:
        gate = "DIRECTIONAL_PI_CANDIDATE_FOUND_WITH_STARTUP_SAFETY_BLOCKER"
    else:
        gate = "DIRECTIONAL_PI_CANDIDATE_FOUND"
    feasibility_map = {str(int(hot)): {str(int(cold)): next(item["map_status"] for item in decisions if item["ki_hot"] == hot and item["ki_cold"] == cold) for cold in registration["ki_cold_values"]} for hot in registration["ki_hot_values"]}
    evidence = {
        "schema": "phase5-r5-directional-pi-evidence-v1", "status": gate,
        "registration_sha256": r41._sha(REGISTRATION), "source_r4_2_registration_sha256": r41._sha(r42.REGISTRATION), "source_r4_2_evidence_sha256": r41._sha(r42.EVIDENCE), "source_r2_baseline_sha256": r41._sha(r4.SOURCE_R2),
        "integrity": integrity, "controller_law": registration["directional_law"], "target_k": registration["target_k"], "inner": registration["inner"], "candidates": candidates, "preparation": preparations,
        "stage_a": {"expected_runs": 32, "completed_runs": len(stage_a), "invalid_runs": sum(item["status"] == "INVALID" for item in stage_a), "run_matrix": stage_a, "candidate_decisions": decisions, "thermally_feasible_count": len(feasible), "feasible_ranking": [item["id"] for item in feasible]},
        "feasibility_map": feasibility_map,
        "stage_b": {"status": "EXECUTED" if finalists else "NOT_EXECUTED_NO_STAGE_A_FEASIBLE_CANDIDATE", "finalist_ids": finalist_ids, "expected_runs": 4 * len(finalists), "completed_runs": len(stage_b), "run_matrix": stage_b, "convergence": convergence, "robust_candidate_ids": [item["candidate_id"] for item in convergence if item["status"] == "PASS"]},
        "numerical_uncertainty": {"status": "EXECUTED" if comparisons else "NOT_APPLICABLE_NO_ROBUST_PAIR", "pairwise_comparisons": comparisons},
        "selection_hierarchy": registration["stage_a"]["ranking_hierarchy"], "selection": {"candidate_id": selected_id, "reason": selection_reason, "frozen_final_baseline": False},
        "startup_safety": common, "ownership": {"status": "PASS" if ownership_pass else "FAIL", "audit": ownership_audit},
        "conservation": {"status": "PASS" if conservation_pass else "FAIL", "max_mass_residual_kg_s": max(item["metrics"]["max_mass_residual_kg_s"] for item in all_records if item["metrics"] is not None), "max_energy_residual_j": max(item["metrics"]["max_energy_residual_j"] for item in all_records if item["metrics"] is not None)},
        "invalid_run_count": len(invalid), "repeatability": repeatability, "holdout_used_for_tuning": False, "training_cases_not_independent_validation": True, "phase6_authorized": False,
        "figure_traces": {candidate_id: {case: traces[(candidate_id, case)] for case in registration["training_cases"]} for candidate_id in finalist_ids},
        "selected_or_first_finalist_ticks": {case: next(item["blend_audit"]["outer_ticks"] for item in stage_a if item["candidate_id"] == (selected_id or finalist_ids[0]) and item["case"] == case) for case in registration["training_cases"]} if finalists else {},
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False, default=lambda item: item.item()) + "\n", encoding="utf-8")
    if finalists:
        _figure(evidence)
    if selected_id and repeatability["status"] == "PASS" and ownership_pass and conservation_pass:
        selected = next(item for item in decisions if item["id"] == selected_id)
        baseline = {"schema": "phase5-r5-directional-pi-candidate-baseline-v1", "status": "CANDIDATE_AWAITING_USER_REVIEW_NOT_FROZEN", "target_k": registration["target_k"], "inner": registration["inner"], "outer_kp": 4500.0, "ki_hot": selected["ki_hot"], "ki_cold": selected["ki_cold"], "kd": 0.0, "blend_halfwidth_k": 0.1, "blending_law": registration["directional_law"]["blend_region"], "single_integral_state": True, **selected["score"], "all_mesh_robustness": next(item for item in convergence if item["candidate_id"] == selected_id), "startup_safety_blocker_status": common["status"], "ownership_status": "PASS", "conservation_status": "PASS", "repeatability_status": repeatability["status"], "registration_sha256": r41._sha(REGISTRATION), "evidence_sha256": r41._sha(EVIDENCE), "source_r4_2_evidence_sha256": r41._sha(r42.EVIDENCE), "phase6_authorized": False}
        CANDIDATE_BASELINE.write_text(json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    elif CANDIDATE_BASELINE.exists():
        raise RuntimeError("Stale R5 candidate baseline exists after no-selection result")
    print(json.dumps({"status": gate, "registration_sha256": r41._sha(REGISTRATION), "evidence_sha256": r41._sha(EVIDENCE), "stage_a_runs": len(stage_a), "stage_a_feasible": len(feasible), "finalists": finalist_ids, "stage_b_runs": len(stage_b), "selected_candidate": selected_id, "invalid_runs": len(invalid)}, indent=2))


if __name__ == "__main__":
    main()
