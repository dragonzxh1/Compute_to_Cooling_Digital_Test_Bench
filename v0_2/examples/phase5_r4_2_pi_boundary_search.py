"""Deterministic, preregistered PI feasibility-boundary search."""

from __future__ import annotations

import json
import math
from pathlib import Path

from v0_2.examples import phase5_r4_1_local_pi_refinement as r41
from v0_2.examples import phase5_r4_outer_tuning as r4
from v0_2.examples.phase5_r1_ownership_audit import collect_audit

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r4_2_pi_boundary_search_registration.json"
EVIDENCE = ROOT / "phase5_r4_2_pi_boundary_search_evidence.json"
CANDIDATE_BASELINE = ROOT / "phase5_r4_2_candidate_baseline.json"
FIGURE = ROOT / "docs/results/phase5_r4_2_pi_feasibility_boundaries.png"
EXPECTED_REGISTRATION_SHA256 = "6c24855e76b4967c9fa3327a57dfcf796a54e58447208c233dff0b07820b1070"
EXPECTED_KP = [2500, 3000, 3500, 4000, 4500, 5000]
EXPECTED_INITIAL_KI = [95.0, 100.0, 105.0, 110.0, 115.0, 120.0, 125.0]
EXPECTED_COLD_SIGNATURE = (
    (200_000_000, "DEGRADED", ("ACTUATOR_TRACKING_PENDING",)),
    (600_000_000, "FF_DISABLED", ("RECOVERY_QUALIFICATION",)),
    (2_600_000_000, "NORMAL", ()),
)


def _gain_text(ki: float) -> str:
    return f"{ki:.10f}".rstrip("0").rstrip(".")


def _candidate(kp: int, ki: float) -> dict:
    return {"id": f"R42-KP{kp}-KI{_gain_text(ki)}", "kp": float(kp), "ki": float(ki), "kd": 0.0}


def _integrity(registration: dict, source_registration: dict, source_evidence: dict) -> dict:
    checks = {
        "registration_sha": r41._sha(REGISTRATION) == EXPECTED_REGISTRATION_SHA256,
        "source_registration_sha": r41._sha(r41.REGISTRATION) == registration["source_r4_1_registration_sha256"],
        "source_evidence_sha": r41._sha(r41.EVIDENCE) == registration["source_r4_1_evidence_sha256"],
        "source_r2_baseline_sha": r41._sha(r4.SOURCE_R2) == registration["source_r2_baseline_sha256"],
        "source_integrity": r41._integrity(source_registration)["status"] == "PASS",
        "source_gate": source_evidence["status"] == "NO_LOCAL_PI_OVERLAP_REGION_FOUND",
        "source_run_count": source_evidence["stage_a"]["completed_runs"] == 60 and source_evidence["stage_a"]["invalid_runs"] == 0,
        "frozen_target_inner": registration["target_k"] == source_registration["target_k"] and registration["inner"] == source_registration["inner"],
        "fixed_kp": registration["kp_values"] == EXPECTED_KP,
        "domain": registration["ki_domain"] == [95.0, 125.0] and registration["kd"] == 0.0,
        "initial_probes": registration["boundary_algorithm"]["initial_probe_ki"] == EXPECTED_INITIAL_KI,
        "boundary_tolerance": registration["boundary_algorithm"]["bracket_tolerance_ki"] == 0.10,
        "meshes": registration["canonical_physics_dt_ns"] == 200_000_000 and registration["near_gap_policy"]["physics_dt_ns"] == [100_000_000, 50_000_000],
        "training_only": registration["training_cases"] == source_registration["training_cases"] and registration["holdout_used_for_search"] is False,
        "no_structure_or_phase6": registration["controller_structure_changes_authorized"] is False and registration["phase6_authorized"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_R4_2_INTEGRITY_FAILURE: {checks!r}")
    return {"status": "PASS", "checks": checks}


class Search:
    def __init__(self, registration: dict, source_registration: dict, source_evidence: dict):
        self.registration = registration
        self.source_registration = source_registration
        self.preparations, self.states = r4._prepare(source_registration)
        self.cache: dict[tuple[int, float, int, str], dict] = {}
        self.new_records: list[dict] = []
        for record in source_evidence["stage_a"]["run_matrix"]:
            kp = int(float(record["candidate_id"].split("-KP")[1].split("-KI")[0]))
            ki = float(record["candidate_id"].split("-KI")[1])
            key = (kp, ki, 200_000_000, record["case"])
            self.cache[key] = {**record, "kp": kp, "ki": ki, "provenance": "R4_1_FROZEN_EVIDENCE", "attempt_count": 1}

    def evaluate(self, kp: int, ki: float, dt_ns: int, case: str) -> dict:
        if kp not in EXPECTED_KP or not 95 <= ki <= 125 or dt_ns not in (200_000_000, 100_000_000, 50_000_000) or case not in ("WARM_CAPTURE", "COLD_CAPTURE"):
            raise ValueError("Probe lies outside preregistered Kp/Ki/mesh/case domain")
        key = (kp, ki, dt_ns, case)
        if key not in self.cache:
            candidate = _candidate(kp, ki)
            attempts = []
            for _ in range(self.registration["boundary_algorithm"]["invalid_run_attempts_at_same_exact_gain"]):
                record, _ = r41._run(candidate, case, dt_ns, self.states[case], self.preparations[case]["speed_fraction"], self.source_registration)
                attempts.append(record)
                if record["status"] == "EXECUTED" and record["metrics"] is not None:
                    break
            record = {**attempts[-1], "kp": kp, "ki": ki, "provenance": "R4_2_NEW_EXECUTION", "attempt_count": len(attempts), "prior_attempt_errors": [item.get("error") for item in attempts[:-1]]}
            self.cache[key] = record
            self.new_records.append(record)
        return self.cache[key]

    @staticmethod
    def classify(record: dict) -> dict:
        if record["status"] != "EXECUTED" or record["metrics"] is None:
            return {"status": "INVALID", "pass": None, "reasons": ["SOLVER_OR_RUN_INVALID"]}
        metrics = record["metrics"]
        common = record["case"] != "COLD_CAPTURE" or r4._safety_signature(metrics) == EXPECTED_COLD_SIGNATURE
        reasons = r41._reasons(record, common)
        if record["case"] == "COLD_CAPTURE" and not common:
            reasons.append("NONCOMMON_STARTUP_SIGNATURE")
        return {"status": "PASS" if not reasons else "FAIL", "pass": not reasons, "reasons": sorted(set(reasons)), "startup_safety_blocker_pending": record["case"] == "COLD_CAPTURE" and common}

    def probe(self, kp: int, ki: float, dt_ns: int, case: str) -> dict:
        record = self.evaluate(kp, ki, dt_ns, case)
        classification = self.classify(record)
        if classification["status"] == "INVALID":
            raise RuntimeError(f"INVALID_BOUNDARY_RUN: {(kp, ki, dt_ns, case)} {record.get('error')}")
        if record["case"] == "COLD_CAPTURE" and "NONCOMMON_STARTUP_SIGNATURE" in classification["reasons"]:
            raise RuntimeError(f"UNEXPECTED_STARTUP_SAFETY_SIGNATURE: {(kp, ki, dt_ns, case)}")
        return classification


def _monotonicity(points: dict[float, bool], case: str) -> dict:
    ordered = sorted(points.items())
    violations = []
    for i, (lower_ki, lower_pass) in enumerate(ordered):
        for upper_ki, upper_pass in ordered[i + 1 :]:
            if case == "WARM_CAPTURE" and not lower_pass and upper_pass:
                violations.append({"lower_ki": lower_ki, "lower_pass": lower_pass, "upper_ki": upper_ki, "upper_pass": upper_pass})
            if case == "COLD_CAPTURE" and lower_pass and not upper_pass:
                violations.append({"lower_ki": lower_ki, "lower_pass": lower_pass, "upper_ki": upper_ki, "upper_pass": upper_pass})
    return {"status": "FAIL" if violations else "PASS", "violations": violations}


def _boundary(search: Search, kp: int, dt_ns: int, case: str, points: dict[float, bool]) -> dict:
    ordered = sorted(points.items())
    check = _monotonicity(points, case)
    if check["status"] == "FAIL":
        return {"status": "NON_MONOTONIC_PI_FEASIBILITY", "monotonicity": check}
    if case == "WARM_CAPTURE":
        if all(passed for _, passed in ordered):
            return {"status": "WARM_BOUNDARY_ABOVE_DOMAIN", "pass_bound": 125.0, "fail_bound": None, "width_ki": None, "midpoint_estimate_ki": None, "monotonicity": check}
        if not any(passed for _, passed in ordered):
            return {"status": "WARM_BOUNDARY_BELOW_DOMAIN", "pass_bound": None, "fail_bound": 95.0, "width_ki": None, "midpoint_estimate_ki": None, "monotonicity": check}
        low = max(ki for ki, passed in ordered if passed)
        high = min(ki for ki, passed in ordered if not passed)
    else:
        if all(passed for _, passed in ordered):
            return {"status": "COLD_BOUNDARY_BELOW_DOMAIN", "pass_bound": 95.0, "fail_bound": None, "width_ki": None, "midpoint_estimate_ki": None, "monotonicity": check}
        if not any(passed for _, passed in ordered):
            return {"status": "COLD_BOUNDARY_ABOVE_DOMAIN", "pass_bound": None, "fail_bound": 125.0, "width_ki": None, "midpoint_estimate_ki": None, "monotonicity": check}
        low = max(ki for ki, passed in ordered if not passed)
        high = min(ki for ki, passed in ordered if passed)
    for _ in range(search.registration["boundary_algorithm"]["maximum_bisection_steps_per_boundary"]):
        if high - low <= search.registration["boundary_algorithm"]["bracket_tolerance_ki"]:
            break
        midpoint = (low + high) / 2
        passed = search.probe(kp, midpoint, dt_ns, case)["pass"]
        points[midpoint] = passed
        check = _monotonicity(points, case)
        if check["status"] == "FAIL":
            return {"status": "NON_MONOTONIC_PI_FEASIBILITY", "monotonicity": check}
        if case == "WARM_CAPTURE":
            low, high = (midpoint, high) if passed else (low, midpoint)
        else:
            low, high = (low, midpoint) if passed else (midpoint, high)
    if high - low > search.registration["boundary_algorithm"]["bracket_tolerance_ki"]:
        raise RuntimeError("PRE_REGISTERED_BISECTION_STEP_LIMIT_EXHAUSTED")
    if case == "WARM_CAPTURE":
        pass_bound, fail_bound = low, high
    else:
        fail_bound, pass_bound = low, high
    return {"status": "BRACKETED", "pass_bound": pass_bound, "fail_bound": fail_bound, "width_ki": high - low, "midpoint_estimate_ki": (low + high) / 2, "monotonicity": check}


def _overlap(warm: dict, cold: dict, tolerance: float) -> dict:
    if "NON_MONOTONIC" in (warm["status"] + cold["status"]):
        return {"classification": "NON_MONOTONIC_PI_FEASIBILITY", "confirmed_overlap_width_ki": None, "confirmed_gap_width_ki": None}
    if warm["status"] == "WARM_BOUNDARY_BELOW_DOMAIN" or cold["status"] == "COLD_BOUNDARY_ABOVE_DOMAIN":
        return {"classification": "DOMAIN_NO_OVERLAP", "confirmed_overlap_width_ki": None, "confirmed_gap_width_ki": None}
    warm_pass = warm["pass_bound"]
    warm_fail = warm["fail_bound"]
    cold_pass = cold["pass_bound"]
    cold_fail = cold["fail_bound"]
    if warm_pass is not None and cold_pass is not None:
        overlap_width = warm_pass - cold_pass
        if overlap_width > tolerance:
            return {"classification": "CONFIRMED_OVERLAP", "confirmed_overlap_width_ki": overlap_width, "confirmed_gap_width_ki": None, "overlap_candidate_interval": [cold_pass, warm_pass]}
    if warm_fail is not None and cold_fail is not None:
        gap_width = cold_fail - warm_fail
        if gap_width > tolerance:
            return {"classification": "CONFIRMED_GAP", "confirmed_overlap_width_ki": None, "confirmed_gap_width_ki": gap_width, "gap_interval": [warm_fail, cold_fail]}
    return {"classification": "BOUNDARY_AMBIGUOUS_WITHIN_SEARCH_TOLERANCE", "confirmed_overlap_width_ki": None, "confirmed_gap_width_ki": None}


def _search_one(search: Search, kp: int, dt_ns: int) -> dict:
    points = {case: {} for case in ("WARM_CAPTURE", "COLD_CAPTURE")}
    for ki in EXPECTED_INITIAL_KI:
        for case, values in points.items():
            values[ki] = search.probe(kp, ki, dt_ns, case)["pass"]
    initial = {case: _monotonicity(values, case) for case, values in points.items()}
    if any(item["status"] == "FAIL" for item in initial.values()):
        return {"kp": kp, "physics_dt_ns": dt_ns, "initial_monotonicity": initial, "monotonicity_status": "FAIL", "warm_boundary": None, "cold_boundary": None, "overlap": {"classification": "NON_MONOTONIC_PI_FEASIBILITY"}, "probes": {case: [{"ki": ki, "pass": value} for ki, value in sorted(values.items())] for case, values in points.items()}}
    warm = _boundary(search, kp, dt_ns, "WARM_CAPTURE", points["WARM_CAPTURE"])
    if warm["status"] == "NON_MONOTONIC_PI_FEASIBILITY":
        cold = None
        overlap = {"classification": "NON_MONOTONIC_PI_FEASIBILITY"}
    else:
        cold = _boundary(search, kp, dt_ns, "COLD_CAPTURE", points["COLD_CAPTURE"])
        overlap = _overlap(warm, cold, search.registration["boundary_algorithm"]["bracket_tolerance_ki"])
    return {"kp": kp, "physics_dt_ns": dt_ns, "initial_monotonicity": initial, "monotonicity_status": "FAIL" if overlap["classification"] == "NON_MONOTONIC_PI_FEASIBILITY" else "PASS", "warm_boundary": warm, "cold_boundary": cold, "overlap": overlap, "probes": {case: [{"ki": ki, "pass": value} for ki, value in sorted(values.items())] for case, values in points.items()}}


def _figure(canonical: list[dict], fine: list[dict], registration: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 7))
    kps = [item["kp"] for item in canonical]
    warm = [item["warm_boundary"]["midpoint_estimate_ki"] if item["warm_boundary"] else None for item in canonical]
    cold = [item["cold_boundary"]["midpoint_estimate_ki"] if item["cold_boundary"] else None for item in canonical]
    ax.plot(kps, [value if value is not None else math.nan for value in warm], "o-", label="Warm-pass maximum boundary", color="#d55e00")
    ax.plot(kps, [value if value is not None else math.nan for value in cold], "o-", label="Cold-pass minimum boundary", color="#0072b2")
    for item in canonical:
        kp = item["kp"]
        wb, cb = item["warm_boundary"], item["cold_boundary"]
        if wb and wb["status"] == "BRACKETED":
            ax.vlines(kp - 18, wb["pass_bound"], wb["fail_bound"], color="#d55e00", linewidth=5, alpha=0.6)
        if cb and cb["status"] == "BRACKETED":
            ax.vlines(kp + 18, cb["fail_bound"], cb["pass_bound"], color="#0072b2", linewidth=5, alpha=0.6)
        kind = item["overlap"]["classification"]
        if kind == "CONFIRMED_GAP":
            a, b = item["overlap"]["gap_interval"]
            ax.vlines(kp, a, b, color="#999999", linewidth=14, alpha=0.5)
        elif kind == "CONFIRMED_OVERLAP":
            a, b = item["overlap"]["overlap_candidate_interval"]
            ax.vlines(kp, a, b, color="#009e73", linewidth=14, alpha=0.5)
        if wb and wb["status"] != "BRACKETED":
            ax.annotate(wb["status"].replace("_", " "), (kp, 123), rotation=90, fontsize=7, ha="center")
        if cb and cb["status"] != "BRACKETED":
            ax.annotate(cb["status"].replace("_", " "), (kp, 97), rotation=90, fontsize=7, ha="center")
    for item in fine:
        wb, cb = item["warm_boundary"], item["cold_boundary"]
        if wb and cb and wb["midpoint_estimate_ki"] is not None and cb["midpoint_estimate_ki"] is not None:
            marker = "s" if item["physics_dt_ns"] == 100_000_000 else "^"
            ax.scatter([item["kp"] - 40, item["kp"] + 40], [wb["midpoint_estimate_ki"], cb["midpoint_estimate_ki"]], marker=marker, color="black", s=35)
    ax.set_xlim(min(kps) - 180, max(kps) + 180)
    ax.set_ylim(*registration["ki_domain"])
    ax.set_xticks(kps)
    ax.set_xlabel("Fixed outer Kp")
    ax.set_ylabel("Outer Ki")
    ax.set_title("PI feasibility boundaries; bars show ≤0.10 Ki search uncertainty")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.22)
    fig.text(0.5, 0.01, "TUNING / FEASIBILITY EVIDENCE — NOT INDEPENDENT HARDWARE VALIDATION", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=160)
    plt.close(fig)


def main() -> None:
    registration = r41._load(REGISTRATION)
    source_registration = r41._load(r41.REGISTRATION)
    source_evidence = r41._load(r41.EVIDENCE)
    integrity = _integrity(registration, source_registration, source_evidence)
    search = Search(registration, source_registration, source_evidence)
    canonical = []
    for kp in registration["kp_values"]:
        result = _search_one(search, kp, 200_000_000)
        canonical.append(result)
        print(f"Canonical Kp={kp}: {result['overlap']['classification']}", flush=True)
    classifications = [item["overlap"]["classification"] for item in canonical]
    fine, selected_candidate, candidate_mesh = [], None, []
    repeatability = {"status": "NOT_EXECUTED", "reason": "no robust selected candidate"}
    if "NON_MONOTONIC_PI_FEASIBILITY" in classifications:
        gate = "NON_MONOTONIC_PI_FEASIBILITY_FOUND"
    elif "CONFIRMED_OVERLAP" in classifications:
        overlaps = [item for item in canonical if item["overlap"]["classification"] == "CONFIRMED_OVERLAP"]
        centers = []
        for item in overlaps:
            lower, upper = item["overlap"]["overlap_candidate_interval"]
            ki = (lower + upper) / 2
            kp = item["kp"]
            warm = search.probe(kp, ki, 200_000_000, "WARM_CAPTURE")
            cold = search.probe(kp, ki, 200_000_000, "COLD_CAPTURE")
            score = r4._score({case: search.evaluate(kp, ki, 200_000_000, case)["metrics"] for case in registration["training_cases"]}) if warm["pass"] and cold["pass"] else None
            centers.append({"kp": kp, "ki": ki, "id": _candidate(kp, ki)["id"], "width_ki": upper - lower, "minimum_margin_ki": min(ki - lower, upper - ki), "canonical_warm_pass": warm["pass"], "canonical_cold_pass": cold["pass"], "score": score})
        eligible = [item for item in centers if item["score"] is not None]
        if eligible:
            chosen = min(eligible, key=lambda item: (-item["width_ki"], -item["minimum_margin_ki"], *r4._score_key({"score": item["score"], "candidate_id": item["id"]})))
            kp, ki = chosen["kp"], chosen["ki"]
            for dt_ns in (100_000_000, 50_000_000):
                for case in registration["training_cases"]:
                    search.probe(kp, ki, dt_ns, case)
            candidate_mesh = [{**search.evaluate(kp, ki, dt_ns, case), "candidate_id": chosen["id"]} for dt_ns in (200_000_000, 100_000_000, 50_000_000) for case in registration["training_cases"]]
            convergence = r4._fine_convergence(candidate_mesh, source_registration, chosen["id"], True)
            all_pass = all(search.classify(item)["pass"] for item in candidate_mesh)
            if all_pass and convergence["status"] == "PASS":
                selected_candidate = {**chosen, "all_mesh_convergence": convergence}
                candidate = _candidate(kp, ki)
                repeated = [r4._repeat_case(candidate, case, source_registration, search.states[case], search.preparations[case]["speed_fraction"]) for case in registration["training_cases"]]
                repeatability = {"status": "PASS" if all(item["status"] == "PASS" for item in repeated) else "FAIL", "cases": repeated}
                gate = "ROBUST_PI_OVERLAP_FOUND" if repeatability["status"] == "PASS" else "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
            else:
                gate = "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
        else:
            gate = "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
    elif "BOUNDARY_AMBIGUOUS_WITHIN_SEARCH_TOLERANCE" in classifications:
        gate = "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
    else:
        gaps = sorted((item for item in canonical if item["overlap"]["classification"] == "CONFIRMED_GAP"), key=lambda item: (item["overlap"]["confirmed_gap_width_ki"], item["kp"]))
        if len(gaps) < 2:
            gate = "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
        else:
            for item in gaps[:2]:
                kp = item["kp"]
                for dt_ns in registration["near_gap_policy"]["physics_dt_ns"]:
                    result = _search_one(search, kp, dt_ns)
                    fine.append(result)
                    print(f"Near-gap Kp={kp}, dt={dt_ns / 1e9:g}: {result['overlap']['classification']}", flush=True)
            gate = "NO_PI_OVERLAP_CONFIRMED_IN_R42_DOMAIN" if all(item["overlap"]["classification"] in ("CONFIRMED_GAP", "DOMAIN_NO_OVERLAP") for item in fine) else "NON_MONOTONIC_PI_FEASIBILITY_FOUND" if any(item["overlap"]["classification"] == "NON_MONOTONIC_PI_FEASIBILITY" for item in fine) else "PI_BOUNDARY_AMBIGUOUS_AT_CURRENT_SEARCH_RESOLUTION"
    new = search.new_records
    all_records = list(search.cache.values())
    ownership_audit = collect_audit()
    ownership_pass = ownership_audit["status"] == "PASS" and all(item["metrics"]["ownership_lineage_pass"] for item in all_records if item["metrics"] is not None)
    conservation_pass = all(item["metrics"]["conservation_pass"] for item in all_records if item["metrics"] is not None)
    startup_pass = all(r4._safety_signature(item["metrics"]) == EXPECTED_COLD_SIGNATURE for item in all_records if item["case"] == "COLD_CAPTURE" and item["metrics"] is not None)
    if not ownership_pass or not conservation_pass or not startup_pass or any(item["status"] == "INVALID" for item in new):
        raise RuntimeError("R4_2_OWNERSHIP_CONSERVATION_OR_STARTUP_INTEGRITY_FAILURE")
    evidence = {
        "schema": "phase5-r4-2-pi-boundary-evidence-v1", "status": gate,
        "registration_sha256": r41._sha(REGISTRATION), "source_r4_1_registration_sha256": r41._sha(r41.REGISTRATION), "source_r4_1_evidence_sha256": r41._sha(r41.EVIDENCE), "source_r2_baseline_sha256": r41._sha(r4.SOURCE_R2),
        "integrity": integrity, "target_k": registration["target_k"], "inner": registration["inner"], "kp_values": registration["kp_values"], "ki_domain": registration["ki_domain"], "boundary_tolerance_ki": registration["boundary_algorithm"]["bracket_tolerance_ki"],
        "preparation": search.preparations, "historical_reused_run_count": len(all_records) - len(new), "new_executed_run_count": len(new), "all_boundary_search_points": sorted(all_records, key=lambda item: (item["physics_dt_ns"], item["kp"], item["ki"], item["case"])),
        "canonical_boundaries": canonical, "near_gap_fine_mesh": fine, "selected_candidate": selected_candidate, "candidate_all_mesh_runs": candidate_mesh,
        "startup_safety": {"status": "STARTUP_SAFETY_BLOCKER_PENDING", "candidate_independent": startup_pass, "cold_degraded_duration_s": 0.4, "full_feedback_qualification_blocked": True},
        "ownership": {"status": "PASS" if ownership_pass else "FAIL", "audit": ownership_audit},
        "conservation": {"status": "PASS" if conservation_pass else "FAIL", "max_mass_residual_kg_s": max(item["metrics"]["max_mass_residual_kg_s"] for item in all_records if item["metrics"] is not None), "max_energy_residual_j": max(item["metrics"]["max_energy_residual_j"] for item in all_records if item["metrics"] is not None)},
        "repeatability": repeatability, "holdout_used_for_search": False, "independent_validation_claim_allowed": False, "phase6_authorized": False,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False, default=lambda item: item.item()) + "\n", encoding="utf-8")
    _figure(canonical, fine, registration)
    if gate == "ROBUST_PI_OVERLAP_FOUND" and selected_candidate is not None:
        baseline = {"schema": "phase5-r4-2-candidate-baseline-v1", "status": "CANDIDATE_AWAITING_USER_REVIEW_NOT_FROZEN", "target_k": registration["target_k"], "inner": registration["inner"], "outer": _candidate(selected_candidate["kp"], selected_candidate["ki"]), "boundary_margins": {"confirmed_overlap_width_ki": selected_candidate["width_ki"], "minimum_margin_ki": selected_candidate["minimum_margin_ki"]}, "canonical_score": selected_candidate["score"], "all_mesh_convergence": selected_candidate["all_mesh_convergence"], "startup_safety_blocker": "STARTUP_SAFETY_BLOCKER_PENDING", "ownership_status": "PASS", "conservation_status": "PASS", "repeatability_status": repeatability["status"], "registration_sha256": r41._sha(REGISTRATION), "evidence_sha256": r41._sha(EVIDENCE), "source_r4_1_evidence_sha256": r41._sha(r41.EVIDENCE), "phase6_authorized": False}
        CANDIDATE_BASELINE.write_text(json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    elif CANDIDATE_BASELINE.exists():
        raise RuntimeError("Stale R4.2 candidate baseline exists after no-selection result")
    print(json.dumps({"status": gate, "registration_sha256": r41._sha(REGISTRATION), "evidence_sha256": r41._sha(EVIDENCE), "canonical_classifications": {str(item["kp"]): item["overlap"]["classification"] for item in canonical}, "near_gap_kp": sorted({item["kp"] for item in fine}), "new_executed_run_count": len(new), "selected_candidate": selected_candidate["id"] if selected_candidate else None}, indent=2))


if __name__ == "__main__":
    main()
