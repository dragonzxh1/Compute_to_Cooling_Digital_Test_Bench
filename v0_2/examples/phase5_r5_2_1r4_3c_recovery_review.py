"""Read-only P-history provenance review and candidate-freeze manifest builder."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from hashlib import sha256

from v0_2.examples import phase5_r5_2_1r1a_validation as r1a
from v0_2.examples.phase5_r5_2_1r4_3b_validation import run
from v0_2.examples.phase5_r5_2_1r_validation import PROFILE, R52_REGISTRATION, ROOT, load, states
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

R4_REG = ROOT / "phase5_r5_2_1r4_paired_reference_tracking_registration.json"
R1A_EVIDENCE = ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json"
P15_INPUT = ROOT / "v0_2/tests/data/tracking_history/P15_C9R_candidate.json"
PRIOR_RECOVERY = ROOT / "phase5_r5_2_1_p_history_input_recovery_manifest.json"
R43B_EVIDENCE = ROOT / "phase5_r5_2_1r4_3b_observable_progress_evidence.json"
MANIFEST = ROOT / "phase5_r5_2_1_p_history_frozen_candidate_manifest.json"
EVIDENCE = ROOT / "phase5_r5_2_1r4_3c_p_history_recovery_evidence.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def git_lines(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                            text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.splitlines()


def main():
    r4 = load(R4_REG)
    r1a_reg = load(r1a.REGISTRATION)
    old = load(R1A_EVIDENCE)
    p15 = load(P15_INPUT)
    before = load(R43B_EVIDENCE)
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    regenerated = [asdict(item) for item in r1a.c9r_source(r1a_reg)]
    stored_old = old["c9r_case"]["input_trace"]
    input_checks = {
        "r4_registration_explicitly_maps_P15_to_C9R": r4["preregistered_case_matrix"]["P15"] == "C9R A-to-B-to-C",
        "candidate_matches_frozen_generator": p15["observations"] == regenerated,
        "candidate_matches_old_serialized_input": p15["observations"] == stored_old,
        "generator_is_deterministic_10x": all(
            [asdict(item) for item in r1a.c9r_source(r1a_reg)] == regenerated for _ in range(10)
        ),
        "registered_input_math_passes": all(r1a.preregistered_sequence_validity(r1a_reg, profile).values()),
        "old_expected_behavior_independently_passed": all(old["c9r_pass_criteria"].values()),
        "old_evidence_gate_validated": old["status"] == "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN",
        "old_trace_no_false_confirmed_fault": old["c9r_pass_criteria"]["no_false_confirmed_fault"],
    }
    if not all(input_checks.values()):
        raise RuntimeError(f"P15 provenance check failed: {input_checks}")
    input_digest = sha256(canonical(p15)).hexdigest()
    old_trace_digest = sha256(canonical(stored_old)).hexdigest()
    generated_trace_digest = sha256(canonical(regenerated)).hexdigest()
    old_expected_digest = sha256(canonical(old["c9r_pass_criteria"])).hexdigest()
    expected_source = {
        "registration_path": str(r1a.REGISTRATION.relative_to(ROOT)).replace("\\", "/"),
        "registration_sha256": sha(r1a.REGISTRATION),
        "evidence_path": str(R1A_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
        "evidence_sha256": sha(R1A_EVIDENCE),
        "acceptance_function": "v0_2/examples/phase5_r5_2_1r1a_validation.py::c9r_checks",
        "expected_behavior_sha256": old_expected_digest,
        "normative": {
            "stage_1_trigger_ns": 600_000_000,
            "stage_2_trigger_ns": 3_400_000_000,
            "anchor_command_sequence": [0.35, 0.51, 0.67],
            "qualified_progress_and_resolution_both_stages": True,
            "no_tracking_fault_confirmed": True,
            "exact_old_anchor_resolution_ns": "NON_NORMATIVE",
        },
    }
    fixture = {
        "case_id": "P15",
        "recovery_class": "RECONSTRUCTED_DETERMINISTICALLY",
        "input_path": str(P15_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": input_digest,
        "input_file_sha256": sha(P15_INPUT),
        "input_record_count": len(p15["observations"]),
        "generator_path": "v0_2/examples/phase5_r5_2_1r1a_validation.py::c9r_source",
        "generator_file_sha256": sha(ROOT / "v0_2/examples/phase5_r5_2_1r1a_validation.py"),
        "underlying_generator_path": "v0_2/examples/phase5_r5_2_2_tracking_calibration.py::run_open_loop",
        "underlying_generator_file_sha256": sha(ROOT / "v0_2/examples/phase5_r5_2_2_tracking_calibration.py"),
        "generator_parameters": r1a_reg["replacement_case"],
        "randomness": "NONE; deterministic scheduler, actuator and released-sensor fixture",
        "old_serialized_input_trace_sha256": old_trace_digest,
        "expected_behavior_source": expected_source,
        "formal_gate_eligible": True,
        "freeze_status": "CANDIDATE_FOR_USER_APPROVED_FREEZE",
        "provenance_refs": [
            "phase5_r5_2_1r4_paired_reference_tracking_registration.json::preregistered_case_matrix.P15",
            "phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json::replacement_case",
            "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json::c9r_case.input_trace",
            "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json::c9r_pass_criteria",
        ],
        "historical_capture_claim": False,
    }
    eligible = [fixture]
    aggregate = sha256(canonical(eligible)).hexdigest()
    manifest = {
        "schema": "phase5-r5-2-1-p-history-frozen-candidate-manifest-v1",
        "status": "CANDIDATE_FOR_USER_APPROVED_FREEZE",
        "canonicalization": "UTF-8 JSON sort_keys=True separators=(',', ':') ensure_ascii=False allow_nan=False; no trailing newline",
        "eligible_fixture_records": eligible,
        "eligible_fixture_records_sha256": aggregate,
        "unresolved_cases": [f"P{i}" for i in range(1, 21) if i != 15],
        "final_frozen_baseline": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    current = run(r1a.c9r_source(r1a_reg), profile, classifier)
    current_anchors = [(event["time_ns"], event["new"]["resolved_command_anchor"])
                       for event in current["resolved_pair_events"]]
    diagnostic = {
        "classification": "DIAGNOSTIC_PRE_FREEZE_NOT_FORMAL_HISTORICAL_PASS",
        "candidate_engine_sha256": sha(ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py"),
        "anchor_events": current_anchors,
        "qualified_progress_times_ns": [row["time_ns"] for row in current["records"]
                                        if row["qualified_progress"]],
        "confirmed_fault": current["confirmed_latched"],
        "state_sequence": states(current),
        "P15_formal_result": "NOT_RUN_PENDING_USER_FREEZE",
    }
    commits = git_lines("rev-list", "--all")
    branches = git_lines("branch", "-a")
    historical_hits = git_lines("log", "--all", "--oneline", "-G",
                                "P1-P20|P15|plateau then true stuck|continuous-command silent stuck", "--", ".")
    deletions = git_lines("log", "--all", "--diff-filter=DR", "--name-status", "--oneline", "--",
                          "v0_2/tests", "v0_2/examples", "docs/results")
    production = {path: {"registered_sha256": registered,
                         "current_sha256": sha(ROOT / path),
                         "unchanged": sha(ROOT / path) == registered}
                  for path, registered in r4["production_sha256"].items()}
    contract_sha = sha(ROOT / "contracts/15A_tracking_safety_policy_amendment.md")
    engine_sha = sha(ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py")
    cases = []
    for index in range(1, 21):
        case_id = f"P{index}"
        is_p15 = index == 15
        cases.append({
            "case_id": case_id,
            "historical_purpose": r4["preregistered_case_matrix"][case_id],
            "best_available_source": (
                "R4 P15=C9R registration + R1a registration/generator/old serialized input and acceptance"
                if is_p15 else "R4 preregistered narrative purpose only"
            ),
            "input_recovery_class": "RECONSTRUCTED_DETERMINISTICALLY" if is_p15 else "NOT_RECOVERABLE",
            "complete_input_available": is_p15,
            "expected_behavior_available": is_p15,
            "timing_normativity_known": is_p15,
            "generator_available": is_p15,
            "generator_sha256": fixture["generator_file_sha256"] if is_p15 else None,
            "candidate_input_sha256": input_digest if is_p15 else None,
            "formal_gate_eligible": is_p15,
            "missing_evidence": ([] if is_p15 else [
                "No original P-specific executable command/measurement/validity timeline",
                "No frozen P-specific generator parameters or input hash",
                "No P-specific public-state/anchor/fault acceptance oracle",
            ]),
            "notes": ("C9R alias, deterministic reconstruction, not original R4 P15 capture; user freeze pending"
                      if is_p15 else "Narrative intent is known, but no partial executable timeline exists in available local evidence"),
        })
    status_counts = {
        "exact_recovered_count": 0,
        "deterministically_reconstructed_count": 1,
        "partial_count": 0,
        "not_recoverable_count": 19,
        "formal_gate_eligible_count": 1,
    }
    profile_sha = sha(PROFILE)
    evidence = {
        "schema": "phase5-r5-2-1r4-3c-p-history-recovery-v1",
        "r4_3b_engine_sha256": engine_sha,
        "r4_3b_engine_matches_prior_evidence": engine_sha == before["engine_sha256_after"],
        "historical_source_hashes": {
            "R4_registration": sha(R4_REG), "R1a_registration": sha(r1a.REGISTRATION),
            "R1a_evidence": sha(R1A_EVIDENCE),
            "R1a_generator": fixture["generator_file_sha256"],
            "physical_fixture_generator": fixture["underlying_generator_file_sha256"],
            "P15_candidate_file": sha(P15_INPUT), "prior_recovery_manifest": sha(PRIOR_RECOVERY),
            "tracking_profile": profile_sha, "Contract15A": contract_sha,
        },
        "git_history_search": {
            "commits_inspected": commits,
            "branches_inspected": branches,
            "P_specific_or_plateau_diff_hits": historical_hits,
            "hit_adjudication": {
                "caf8807": "Unrelated Phase 4 rendered HTML/base64 content; no P-history executable fixture or input"
            },
            "deleted_or_renamed_relevant_files": deletions,
            "result": "No P1-P20 executable fixture, serialized P input, P generator or P-specific historical hash found in available Git history",
        },
        "P15_input_checks": input_checks,
        "P15_freeze_decision": "APPROVE_RECONSTRUCTED_HISTORICAL_FIXTURE",
        "P15_old_trace_sha256": old_trace_digest,
        "P15_regenerated_trace_sha256": generated_trace_digest,
        "P15_canonical_input_sha256": input_digest,
        "cases": cases,
        "status_counts": status_counts,
        "coverage_percentage_descriptive_only": 5.0,
        "candidate_manifest_path": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "candidate_manifest_sha256": sha(MANIFEST),
        "eligible_records_aggregate_sha256": aggregate,
        "P15_diagnostic": diagnostic,
        "production_source_before_after_hashes": production,
        "contract15a_unchanged": contract_sha == r4["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"],
        "tracking_profile_unchanged": profile_sha == r4["source_sha256"]["phase5_r5_2_2_fixture_tracking_profile.json"],
        "full_P_history_validation_available": False,
        "full_historical_validation_claimed": False,
        "production_port_eligible": False,
        "final_freeze_approved": False,
        "gate": "P15_RECOVERABLE_BUT_P_HISTORY_REMAINS_INCOMPLETE",
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"gate": evidence["gate"], "P15_decision": evidence["P15_freeze_decision"],
                      "counts": status_counts, "P15_checks": input_checks,
                      "candidate_manifest_sha256": evidence["candidate_manifest_sha256"],
                      "aggregate_sha256": aggregate,
                      "production_unchanged": all(x["unchanged"] for x in production.values())}, indent=2))


if __name__ == "__main__":
    main()
