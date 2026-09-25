"""Execute the pre-registered Phase 5R3 bidirectional outer-controller selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from v0_2.examples import phase5_1r2_qualification as qualification
from v0_2.examples.phase5_r1_ownership_audit import collect_audit

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r3_bidirectional_selection_registration.json"
EVIDENCE = ROOT / "phase5_r3_bidirectional_selection_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r3_candidate_baseline.json"
R2_BASELINE = ROOT / "phase5_r2_feedback_baseline.json"
PHASE5_1R2_REGISTRATION = ROOT / "phase5_1r2_qualification_registration.json"
PHASE5_1R2_RESULT = ROOT / "phase5_1r2_nominal_result.json"
EXPECTED_REGISTRATION_SHA = "7636af8958f6c87a2516ba1cc90ac357fd7f1812a4234ed97749a434c5a2bbf6"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gains(candidate: dict) -> dict:
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def _integrity(registration: dict, baseline: dict) -> dict:
    checks = {
        "registration_frozen_before_execution": _sha(REGISTRATION)
        == EXPECTED_REGISTRATION_SHA,
        "source_r2_baseline": _sha(R2_BASELINE)
        == registration["source_r2_baseline_sha256"],
        "source_phase5_1r2_registration": _sha(PHASE5_1R2_REGISTRATION)
        == registration["source_phase5_1r2_registration_sha256"],
        "source_phase5_1r2_result": _sha(PHASE5_1R2_RESULT)
        == registration["source_phase5_1r2_result_sha256"],
        "r2_referenced_hashes": qualification._integrity(
            qualification._load(qualification.REGISTRATION), baseline
        )["status"]
        == "PASS",
        "target_unchanged": registration["target_k"] == baseline["target_k"],
        "inner_unchanged": registration["inner"]["id"] == baseline["inner_candidate_id"]
        and _gains(registration["inner"]) == baseline["inner_gains"],
        "candidate_grid_exact": [item["id"] for item in registration["outer_candidates"]]
        == ["outer_a", "outer_b", "outer_c"],
        "phase5_1r2_exam_reused": registration["qualification_duration_ns"]
        == 180_000_000_000
        and registration["preparation"]["duration_ns"] == 180_000_000_000
        and registration["physics_dt_ns"] == [200_000_000, 100_000_000, 50_000_000],
        "no_holdout_selection": registration["holdout_selection_allowed"] is False,
        "no_new_gains": registration["new_gains_allowed"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_R3_BASELINE_INTEGRITY_FAILURE: {checks!r}")
    return {
        "status": "PASS",
        "checks": checks,
        "registration_sha256": _sha(REGISTRATION),
        "source_r2_baseline_sha256": _sha(R2_BASELINE),
        "source_phase5_1r2_registration_sha256": _sha(PHASE5_1R2_REGISTRATION),
        "source_phase5_1r2_result_sha256": _sha(PHASE5_1R2_RESULT),
    }


def _run_pass_without_safety(metrics: dict) -> bool:
    return all(
        metrics[key]
        for key in (
            "settling_pass",
            "final_window_pass",
            "final_saturation_pass",
            "conservation_pass",
            "control_direction_pass",
            "ownership_lineage_pass",
        )
    )


def _candidate_decision(candidate: dict, records: list[dict]) -> dict:
    selected = [record for record in records if record["candidate_id"] == candidate["id"]]
    reasons = []
    if len(selected) != 6:
        reasons.append("INCOMPLETE_RUN_MATRIX")
    if any(not item["metrics"]["settling_pass"] for item in selected):
        reasons.append("SETTLING")
    if any(not item["metrics"]["final_window_pass"] for item in selected):
        reasons.append("FINAL_WINDOW_TEMPERATURE")
    if any(not item["metrics"]["final_saturation_pass"] for item in selected):
        reasons.append("FINAL_SATURATION")
    if any(not item["metrics"]["control_direction_pass"] for item in selected):
        reasons.append("CONTROL_SIGN")
    if any(not item["metrics"]["safety_pass"] for item in selected):
        reasons.append("SAFETY")
    if any(not item["metrics"]["ownership_lineage_pass"] for item in selected):
        reasons.append("OWNERSHIP")
    if any(not item["metrics"]["conservation_pass"] for item in selected):
        reasons.append("CONSERVATION")
    by_dt = {
        dt: {
            case: next(
                item["metrics"]
                for item in selected
                if item["physics_dt_ns"] == dt and item["case"] == case
            )
            for case in ("WARM_CAPTURE", "COLD_CAPTURE")
        }
        for dt in (200_000_000, 100_000_000, 50_000_000)
    }
    aggregates = {
        str(dt): {
            "temperature_iae_k_s": sum(
                by_dt[dt][case]["temperature_iae_k_s"]
                for case in ("WARM_CAPTURE", "COLD_CAPTURE")
            ),
            "control_total_variation": sum(
                by_dt[dt][case]["control_total_variation"]
                for case in ("WARM_CAPTURE", "COLD_CAPTURE")
            ),
            "pump_electrical_j": sum(
                by_dt[dt][case]["pump_electrical_j"]
                for case in ("WARM_CAPTURE", "COLD_CAPTURE")
            ),
            "warm_temperature_iae_k_s": by_dt[dt]["WARM_CAPTURE"][
                "temperature_iae_k_s"
            ],
            "cold_temperature_iae_k_s": by_dt[dt]["COLD_CAPTURE"][
                "temperature_iae_k_s"
            ],
        }
        for dt in by_dt
    }
    thermal_without_safety = all(
        _run_pass_without_safety(item["metrics"]) for item in selected
    )
    safety_only_failure = thermal_without_safety and reasons == ["SAFETY"]
    return {
        "candidate_id": candidate["id"],
        "status": "BIDIRECTIONAL_FEASIBLE" if not reasons else "BIDIRECTIONAL_FEASIBILITY_FAIL",
        "failure_reasons": reasons,
        "thermal_control_pass_without_safety": thermal_without_safety,
        "safety_only_failure": safety_only_failure,
        "aggregates_by_dt_ns": aggregates,
    }


def _pairwise_uncertainty(decisions: list[dict]) -> list[dict]:
    by_id = {item["candidate_id"]: item for item in decisions}
    output = []
    for left, right in (("outer_a", "outer_b"), ("outer_a", "outer_c"), ("outer_b", "outer_c")):
        a = by_id[left]["aggregates_by_dt_ns"]
        b = by_id[right]["aggregates_by_dt_ns"]
        difference = abs(
            a["200000000"]["temperature_iae_k_s"]
            - b["200000000"]["temperature_iae_k_s"]
        )
        bound = abs(
            a["100000000"]["temperature_iae_k_s"]
            - a["50000000"]["temperature_iae_k_s"]
        ) + abs(
            b["100000000"]["temperature_iae_k_s"]
            - b["50000000"]["temperature_iae_k_s"]
        )
        output.append(
            {
                "pair": f"{left}_vs_{right}",
                "canonical_iae_difference_k_s": difference,
                "numerical_uncertainty_bound_k_s": bound,
                "thermal_iae_result": (
                    "NUMERICALLY_INDISTINGUISHABLE"
                    if difference <= bound
                    else "NUMERICALLY_DISTINGUISHABLE"
                ),
            }
        )
    return output


def _select(decisions: list[dict], pairwise: list[dict]) -> tuple[str | None, str]:
    feasible = [item for item in decisions if item["status"] == "BIDIRECTIONAL_FEASIBLE"]
    if not feasible:
        return None, "NO_EXISTING_OUTER_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION"
    if len(feasible) == 1:
        return feasible[0]["candidate_id"], "SOLE_BIDIRECTIONALLY_FEASIBLE_CANDIDATE"
    best = min(
        feasible,
        key=lambda item: item["aggregates_by_dt_ns"]["200000000"][
            "temperature_iae_k_s"
        ],
    )
    comparisons = {item["pair"]: item for item in pairwise}
    equivalent = [best]
    for item in feasible:
        if item is best:
            continue
        pair = comparisons.get(f"{best['candidate_id']}_vs_{item['candidate_id']}")
        if pair is None:
            pair = comparisons[f"{item['candidate_id']}_vs_{best['candidate_id']}"]
        if pair["thermal_iae_result"] == "NUMERICALLY_INDISTINGUISHABLE":
            equivalent.append(item)
    if len(equivalent) == 1:
        return best["candidate_id"], "DISTINGUISHABLE_CANONICAL_THERMAL_IAE"
    selected = min(
        equivalent,
        key=lambda item: (
            item["aggregates_by_dt_ns"]["200000000"]["control_total_variation"],
            item["aggregates_by_dt_ns"]["200000000"]["pump_electrical_j"],
            item["candidate_id"],
        ),
    )
    return selected["candidate_id"], "NUMERICAL_UNCERTAINTY_VETO_THEN_TV_ENERGY_ID"


def main() -> None:
    registration = _load(REGISTRATION)
    baseline = _load(R2_BASELINE)
    integrity = _integrity(registration, baseline)
    preparations = {}
    states = {}
    for label, speed in (
        ("WARM_CAPTURE", registration["preparation"]["warm_speed_fraction"]),
        ("COLD_CAPTURE", registration["preparation"]["cold_speed_fraction"]),
    ):
        preparations[label], states[label] = qualification._prepare(
            label, speed, registration
        )
    source_preparations = _load(PHASE5_1R2_RESULT)["preparation"]
    for label in registration["qualification_cases"]:
        if (
            preparations[label]["normalized_initial_state_sha256"]
            != source_preparations[label]["normalized_initial_state_sha256"]
        ):
            raise RuntimeError(f"PHASE5_R3_INITIAL_STATE_MISMATCH: {label}")

    records = []
    for candidate in registration["outer_candidates"]:
        candidate_baseline = {
            "inner_gains": _gains(registration["inner"]),
            "outer_gains": _gains(candidate),
        }
        for dt_ns in registration["physics_dt_ns"]:
            for label in registration["qualification_cases"]:
                controlled, metrics = qualification._run_case(
                    label,
                    dt_ns,
                    states[label],
                    preparations[label]["speed_fraction"],
                    registration,
                    candidate_baseline,
                )
                records.append(
                    {
                        "candidate_id": candidate["id"],
                        "case": label,
                        "physics_dt_ns": dt_ns,
                        "metrics": metrics,
                    }
                )
                del controlled

    ownership = collect_audit()
    decisions = [
        _candidate_decision(candidate, records)
        for candidate in registration["outer_candidates"]
    ]
    pairwise = _pairwise_uncertainty(decisions)
    selected_id, selection_reason = _select(decisions, pairwise)
    common_startup_blocker = all(
        item["safety_only_failure"] for item in decisions
    ) and all(
        any(
            "ACTUATOR_TRACKING_PENDING" in event[2]
            for record in records
            if record["candidate_id"] == item["candidate_id"]
            for event in record["metrics"]["safety_events"]
        )
        for item in decisions
    )
    ownership_pass = ownership["status"] == "PASS" and all(
        record["metrics"]["ownership_lineage_pass"] for record in records
    )
    conservation_pass = all(
        record["metrics"]["conservation_pass"] for record in records
    )
    invalid_runs = [
        record
        for record in records
        if not record["metrics"]["ownership_lineage_pass"]
        or not record["metrics"]["conservation_pass"]
    ]
    if not ownership_pass or not conservation_pass or invalid_runs:
        gate = "NUMERICAL_OR_OWNERSHIP_FAILURE"
    elif selected_id is not None:
        gate = "R3_SELECTION_CANDIDATE_FOUND"
    elif common_startup_blocker:
        gate = "COMMON_STARTUP_SAFETY_ACCEPTANCE_BLOCKER"
        selection_reason = gate
    else:
        gate = "NO_EXISTING_OUTER_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION"

    evidence = {
        "schema": "phase5-r3-bidirectional-selection-evidence-v1",
        "status": gate,
        "blocking_classification": None if selected_id is not None else gate,
        "registration_sha256": _sha(REGISTRATION),
        "source_r2_baseline_sha256": _sha(R2_BASELINE),
        "integrity": integrity,
        "target_k": registration["target_k"],
        "inner": registration["inner"],
        "outer_candidates": registration["outer_candidates"],
        "preparation": preparations,
        "preparation_state_hashes_match_phase5_1r2": True,
        "run_matrix": records,
        "run_matrix_summary": {
            "expected_runs": 18,
            "completed_runs": len(records),
            "invalid_runs": len(invalid_runs),
        },
        "candidate_decisions": decisions,
        "numerical_uncertainty": pairwise,
        "selection_hierarchy": registration["selection_hierarchy"],
        "selection": {
            "candidate_id": selected_id,
            "reason": selection_reason,
        },
        "safety": {
            "common_startup_safety_acceptance_blocker": common_startup_blocker,
            "rule_unchanged_from_phase5_1r2": True,
        },
        "ownership": ownership,
        "ownership_all_runs_pass": ownership_pass,
        "conservation": {
            "status": "PASS" if conservation_pass else "FAIL",
            "max_mass_residual_kg_s": max(
                record["metrics"]["max_mass_residual_kg_s"] for record in records
            ),
            "max_energy_residual_j": max(
                record["metrics"]["max_energy_residual_j"] for record in records
            ),
        },
        "no_truth_or_future_access": True,
        "holdout_used_in_selection": False,
        "historical_holdout_executed": False,
        "new_gains_created": False,
        "r2_baseline_overwritten": False,
        "phase6_authorized": False,
    }
    EVIDENCE.write_text(
        json.dumps(evidence, indent=2, allow_nan=False, default=lambda item: item.item())
        + "\n",
        encoding="utf-8",
    )

    if selected_id is not None:
        selected = next(
            item for item in registration["outer_candidates"] if item["id"] == selected_id
        )
        candidate_payload = {
            "schema": "phase5-r3-candidate-baseline-v1",
            "status": "CANDIDATE_ONLY_AWAITING_USER_REVIEW_NOT_FROZEN",
            "target_k": registration["target_k"],
            "inner_candidate_id": registration["inner"]["id"],
            "inner_gains": _gains(registration["inner"]),
            "outer_candidate_id": selected_id,
            "outer_gains": _gains(selected),
            "selection_reason": selection_reason,
            "registration_sha256": _sha(REGISTRATION),
            "evidence_sha256": _sha(EVIDENCE),
            "source_r2_baseline_sha256": _sha(R2_BASELINE),
            "phase6_authorized": False,
        }
        CANDIDATE_BASELINE.write_text(
            json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8"
        )
    elif CANDIDATE_BASELINE.exists():
        raise RuntimeError("Refusing to retain a stale Phase 5R3 candidate baseline")

    print(
        json.dumps(
            {
                "status": gate,
                "registration_sha256": _sha(REGISTRATION),
                "evidence_sha256": _sha(EVIDENCE),
                "completed_runs": len(records),
                "invalid_runs": len(invalid_runs),
                "candidate_status": {
                    item["candidate_id"]: item["status"] for item in decisions
                },
                "selected_candidate": selected_id,
                "common_startup_blocker": common_startup_blocker,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
