"""Freeze the approved reconstructed P15 input and validate it against R4.3B."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256

from v0_2.examples import phase5_r5_2_1r1_validation as r1
from v0_2.examples import phase5_r5_2_1r1a_validation as r1a
from v0_2.examples import phase5_r5_2_1r4_3b_validation as r43b
from v0_2.examples.phase5_r5_2_1r4_3_history_validation import c_acceptance, s_acceptance
from v0_2.examples.phase5_r5_2_1r4_3c_recovery_review import canonical
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_r5_2_1r_validation import (
    PROFILE,
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    build_cases,
    load,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

CANDIDATE = ROOT / "phase5_r5_2_1_p_history_frozen_candidate_manifest.json"
INPUT = ROOT / "v0_2/tests/data/tracking_history/P15_C9R_candidate.json"
R4 = ROOT / "phase5_r5_2_1r4_paired_reference_tracking_registration.json"
R43A = ROOT / "phase5_r5_2_1r4_3a_historical_timing_p_recovery_evidence.json"
R43B = ROOT / "phase5_r5_2_1r4_3b_observable_progress_evidence.json"
R43C = ROOT / "phase5_r5_2_1r4_3c_p_history_recovery_evidence.json"
OLD_EVIDENCE = ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json"
ENGINE = ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py"
FINAL = ROOT / "phase5_r5_2_1_p15_reconstructed_history_freeze.json"
EVIDENCE = ROOT / "phase5_r5_2_1r4_3d_p15_freeze_evidence.json"
EXPECTED_CANDIDATE_SHA = "c485debbaf7af75be8208884012b036f02ab8dd01cd97b46d6b829bdbd4cb22c"


def digest(value):
    return sha256(canonical(value)).hexdigest()


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    return result.stdout.strip()


def require(condition, gate):
    if not condition:
        raise RuntimeError(gate)


def protected_hashes(registered):
    paths = list(registered["production_sha256"]) + [
        "contracts/15A_tracking_safety_policy_amendment.md",
        "phase5_r5_2_2_fixture_tracking_profile.json",
        "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py",
    ]
    return {path: sha(ROOT / path) for path in paths}


def main():
    # No artifact is written before all source/provenance checks succeed.
    require(sha(CANDIDATE) == EXPECTED_CANDIDATE_SHA, "P15_FREEZE_BASELINE_MISMATCH")
    candidate = load(CANDIDATE)
    require(candidate["status"] == "CANDIDATE_FOR_USER_APPROVED_FREEZE"
            and not candidate["final_frozen_baseline"]
            and len(candidate["eligible_fixture_records"]) == 1,
            "P15_FREEZE_BASELINE_MISMATCH")
    record = candidate["eligible_fixture_records"][0]
    p15 = load(INPUT)
    r1a_reg = load(r1a.REGISTRATION)
    old = load(OLD_EVIDENCE)
    r4 = load(R4)
    r43a = load(R43A)
    r43b_evidence = load(R43B)
    r43c = load(R43C)
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    before_hashes = protected_hashes(r4)
    registered_hashes = dict(r4["production_sha256"])
    registered_hashes["contracts/15A_tracking_safety_policy_amendment.md"] = (
        r4["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"])
    registered_hashes["phase5_r5_2_2_fixture_tracking_profile.json"] = (
        r4["source_sha256"]["phase5_r5_2_2_fixture_tracking_profile.json"])
    registered_hashes["v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py"] = (
        r43b_evidence["engine_sha256_after"])
    require(all(before_hashes[path] == expected for path, expected in registered_hashes.items()),
            "P15_FREEZE_BASELINE_MISMATCH")

    require(record["case_id"] == "P15"
            and record["recovery_class"] == "RECONSTRUCTED_DETERMINISTICALLY"
            and record["formal_gate_eligible"]
            and r4["preregistered_case_matrix"]["P15"] == "C9R A-to-B-to-C"
            and r43c["P15_freeze_decision"] == "APPROVE_RECONSTRUCTED_HISTORICAL_FIXTURE"
            and r43c["candidate_manifest_sha256"] == EXPECTED_CANDIDATE_SHA,
            "P15_FREEZE_BASELINE_MISMATCH")
    regenerated = [asdict(item) for item in r1a.c9r_source(r1a_reg)]
    fixture_checks = {
        "candidate_input_file_hash": sha(INPUT) == record["input_file_sha256"],
        "canonical_input_hash": digest(p15) == record["input_sha256"],
        "record_count_31": len(p15["observations"]) == record["input_record_count"] == 31,
        "generator_hash": sha(ROOT / "v0_2/examples/phase5_r5_2_1r1a_validation.py")
                          == record["generator_file_sha256"],
        "underlying_generator_hash": sha(ROOT / "v0_2/examples/phase5_r5_2_2_tracking_calibration.py")
                                     == record["underlying_generator_file_sha256"],
        "parameters_equal_registration": record["generator_parameters"] == r1a_reg["replacement_case"],
        "old_serialized_trace_equal": p15["observations"] == old["c9r_case"]["input_trace"],
        "generator_output_equal": p15["observations"] == regenerated,
        "generator_ten_regenerations_equal": all(
            [asdict(item) for item in r1a.c9r_source(r1a_reg)] == regenerated for _ in range(10)),
        "historical_registration_hash": sha(r1a.REGISTRATION)
                                        == record["expected_behavior_source"]["registration_sha256"],
        "historical_evidence_hash": sha(OLD_EVIDENCE)
                                   == record["expected_behavior_source"]["evidence_sha256"],
        "historical_expectation_hash": digest(old["c9r_pass_criteria"])
                                      == record["expected_behavior_source"]["expected_behavior_sha256"],
    }
    require(all(fixture_checks.values()), "P15_GENERATOR_PROVENANCE_MISMATCH")
    require(old["status"] == "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN"
            and all(old["c9r_pass_criteria"].values())
            and r43a["c9r"]["verdict"]
            == "TIMING_SHIFT_ACCEPTABLE_BUT_SPEC_UPDATE_REQUIRED",
            "P15_HISTORICAL_EXPECTATION_AMBIGUOUS")

    head = git("rev-parse", "HEAD")
    status_at_freeze_start = git("status", "--porcelain=v1", "--untracked-files=all")
    observations = [ReleasedObservation(**row) for row in p15["observations"]]
    pre_freeze_confirmation = r43b.run(observations, profile, classifier)
    pre_freeze_hash = digest(pre_freeze_confirmation)

    # Freeze boundary: the approved input identity and expectation below are fixed
    # before the ten formal executions. No fixture or engine source is rewritten.
    normative = [
        {"property": "P15 registration aliases C9R A-to-B-to-C", "class": "EXACT_NORMATIVE",
         "expected": "C9R A-to-B-to-C"},
        {"property": "input record count and canonical content", "class": "EXACT_NORMATIVE",
         "expected": {"count": 31, "sha256": digest(p15)}},
        {"property": "material-demand epoch start times", "class": "EXACT_NORMATIVE",
         "expected_ns": [600_000_000, 3_400_000_000]},
        {"property": "direction of both demands", "class": "EXACT_NORMATIVE",
         "expected": [1, 1]},
        {"property": "qualified command anchors", "class": "EXACT_NORMATIVE",
         "expected": [0.35, 0.51, 0.67]},
        {"property": "progress then resolution in each stage", "class": "ORDER_NORMATIVE",
         "expected": "positive qualified progress and resolved A→B→C after respective trigger"},
        {"property": "final public state and no erroneous fault", "class": "ORDER_NORMATIVE",
         "expected": "eventual STEADY_TRACKING; no TRACKING_FAULT_CONFIRMED"},
        {"property": "old B/C anchor resolution timestamps", "class": "NON_NORMATIVE",
         "old_observed_ns": [1_200_000_000, 4_000_000_000]},
        {"property": "current R4.3B B/C resolution timestamps", "class": "NON_NORMATIVE",
         "diagnostic_observed_ns": [1_000_000_000, 3_800_000_000]},
    ]

    repetitions = [r43b.run(observations, profile, classifier) for _ in range(10)]
    hashes = [digest(result) for result in repetitions]
    result = repetitions[0]
    starts = [event for event in result["epoch_events"] if event["event"] == "START"]
    anchors = result["resolved_pair_events"]
    progress = [row for row in result["records"] if row["qualified_progress"]]
    checks = {
        "ten_identical_repeats": len(set(hashes)) == 1,
        "pre_freeze_confirmation_equal": pre_freeze_hash == hashes[0],
        "prefix_causal": r43b.prefix_causal(observations, profile, classifier),
        "exact_registered_epoch_starts": [x["time_ns"] for x in starts]
                                          == [600_000_000, 3_400_000_000],
        "both_expected_upward": [x["expected_direction"] for x in starts] == [1, 1],
        "registered_anchor_sequence": [x["new"]["resolved_command_anchor"] for x in anchors]
                                      == [0.35, 0.51, 0.67],
        "initial_anchor_directly_observed": anchors[0]["reason"]
                                              == "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE",
        "both_progress_milestones": len(progress) >= 2
                                    and any(starts[0]["time_ns"] < row["time_ns"] <= anchors[1]["time_ns"]
                                            for row in progress)
                                    and any(starts[1]["time_ns"] < row["time_ns"] <= anchors[2]["time_ns"]
                                            for row in progress),
        "resolved_after_each_trigger": anchors[1]["time_ns"] > starts[0]["time_ns"]
                                       and anchors[2]["time_ns"] > starts[1]["time_ns"],
        "anchor_epoch_provenance": [x["new"]["source_epoch_id"] for x in anchors[1:]]
                                   == [x["epoch_id"] for x in starts],
        "eventual_steady": result["state"] == "STEADY_TRACKING",
        "no_confirmed_fault": not result["confirmed_latched"]
                              and all(row["state"] != "TRACKING_FAULT_CONFIRMED"
                                      for row in result["records"]),
    }

    # Existing, separate regressions are rerun but cannot fill missing P history.
    s_sources = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    c_sources = {key: source for key, source in r1.cases(profile).items() if key != "C9"}
    s_results = s_acceptance({key: r43b.run(source, profile, classifier)
                              for key, source in s_sources.items()})
    c_results = c_acceptance({key: r43b.run(source, profile, classifier)
                              for key, source in c_sources.items()})
    tests = subprocess.run([sys.executable, "-m", "pytest",
                            "v0_2/tests/control/test_phase5_r5_2_1r4_3_startup.py", "-q"],
                           cwd=ROOT, text=True, capture_output=True, check=False)
    startup_count = sum(len(line.split()[0]) for line in tests.stdout.splitlines()
                        if line.split() and set(line.split()[0]) == {"."})
    regressions = {
        "S_pass": sum(s_results.values()), "S_total": len(s_results),
        "C_pass": sum(c_results.values()), "C_total": len(c_results),
        "startup_pass": startup_count,
        "startup_returncode": tests.returncode,
        "startup_stdout": tests.stdout, "startup_stderr": tests.stderr,
    }
    require(len(s_results) == 17 and all(s_results.values())
            and len(c_results) == 11 and all(c_results.values())
            and tests.returncode == 0 and regressions["startup_pass"] == 50,
            "P15_FROZEN_REGRESSION_FAILURE")

    after_hashes = protected_hashes(r4)
    immutability = {path: {"before_sha256": before_hashes[path],
                           "after_sha256": after_hashes[path],
                           "registered_sha256": registered_hashes[path],
                           "unchanged": before_hashes[path] == after_hashes[path]
                                        == registered_hashes[path]}
                    for path in before_hashes}
    checks["protected_sources_unchanged"] = all(x["unchanged"] for x in immutability.values())
    checks["fixture_file_unchanged"] = sha(INPUT) == record["input_file_sha256"]
    checks["generator_file_unchanged"] = (
        sha(ROOT / "v0_2/examples/phase5_r5_2_1r1a_validation.py")
        == record["generator_file_sha256"])
    formal_status = "PASS" if all(checks.values()) else "FAIL"
    gate = ("P15_RECONSTRUCTED_HISTORICAL_FIXTURE_FROZEN_AND_VALIDATED"
            if formal_status == "PASS" else "P15_FROZEN_REGRESSION_FAILURE")
    formal_result = {
        "status": formal_status, "checks": checks, "repeatability_sha256_10x": hashes,
        "pre_freeze_confirmation_sha256": pre_freeze_hash,
        "epoch_starts_ns": [x["time_ns"] for x in starts],
        "qualified_progress_ns": [x["time_ns"] for x in progress],
        "anchor_events": [{"time_ns": x["time_ns"],
                           "command_anchor": x["new"]["resolved_command_anchor"],
                           "source_epoch_id": x["new"]["source_epoch_id"]} for x in anchors],
        "final_state": result["state"], "confirmed_fault": result["confirmed_latched"],
        "result_snapshot_sha256": hashes[0],
    }
    freeze_date = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema": "phase5-r5-2-1-p15-reconstructed-history-freeze-v1",
        "freeze_status": "FROZEN_RECONSTRUCTED_HISTORICAL_FIXTURE",
        "freeze_date_utc": freeze_date,
        "case_id": "P15", "recovery_class": "RECONSTRUCTED_DETERMINISTICALLY",
        "original_historical_capture_recovered": False, "formal_gate_eligible": True,
        "input_path": record["input_path"], "input_canonical_sha256": digest(p15),
        "input_file_sha256": record["input_file_sha256"], "record_count": 31,
        "generator_path": record["generator_path"],
        "generator_file_sha256": record["generator_file_sha256"],
        "underlying_generator_path": record["underlying_generator_path"],
        "underlying_generator_file_sha256": record["underlying_generator_file_sha256"],
        "generator_parameters": record["generator_parameters"],
        "randomness": record["randomness"],
        "generation_procedure": "Run c9r_source(replacement_case registration); it calls deterministic run_open_loop, then from_calibration; serialize all ReleasedObservation dataclass fields in order",
        "canonical_serialization": "UTF-8 JSON sort_keys=True separators=(',', ':') ensure_ascii=False allow_nan=False; hash full input object; no trailing newline",
        "historical_registration_source": {"path": "phase5_r5_2_1r4_paired_reference_tracking_registration.json",
                                           "sha256": sha(R4), "P15_alias": "C9R A-to-B-to-C"},
        "historical_expectation_source": record["expected_behavior_source"],
        "C9R_relationship": "P15 is the R4-registered C9R alias, not an independent original capture",
        "R4_3A_timing_adjudication": {"path": str(R43A.relative_to(ROOT)).replace("\\", "/"),
                                      "sha256": sha(R43A),
                                      "verdict": "TIMING_SHIFT_ACCEPTABLE_BUT_SPEC_UPDATE_REQUIRED"},
        "normativity_table": normative,
        "R4_3B_engine_sha256": sha(ENGINE),
        "formal_execution_result": formal_result,
        "formal_execution_result_sha256": digest(formal_result),
        "repeatability_sha256_10x": hashes,
        "candidate_manifest_source_sha256": EXPECTED_CANDIDATE_SHA,
        "Git_HEAD": head,
        "working_tree_status_at_freeze_start": status_at_freeze_start.splitlines(),
        "P1_P20_coverage": {"formal_eligible": 1, "required": 20,
                             "remaining_case_status": "NOT_RECOVERABLE_FROM_CURRENT_EVIDENCE",
                             "remaining_case_ids": candidate["unresolved_cases"]},
        "FULL_P_HISTORY_VALIDATION_AVAILABLE": "NO",
        "FULL_P_HISTORY_VALIDATION_PASSED": "NOT_EVALUABLE",
        "CAN_PRODUCTION_PORT_START": "NO",
    }
    if FINAL.exists() or EVIDENCE.exists():
        require(FINAL.exists() and EVIDENCE.exists(), "P15_FROZEN_BASELINE_MISMATCH")
        frozen = load(FINAL)
        frozen_evidence = load(EVIDENCE)
        require(frozen["input_canonical_sha256"] == digest(p15)
                and frozen["formal_execution_result_sha256"] == digest(formal_result)
                and frozen["R4_3B_engine_sha256"] == sha(ENGINE)
                and frozen_evidence["final_freeze_manifest_sha256"] == sha(FINAL)
                and frozen_evidence["formal_P15_result_sha256"] == digest(formal_result)
                and frozen_evidence["gate"] == gate,
                "P15_FROZEN_BASELINE_MISMATCH")
        print(json.dumps({"gate": gate, "P15_result": formal_status,
                          "frozen_manifest_verified_without_rewrite": True,
                          "freeze_manifest_sha256": sha(FINAL)}, indent=2))
        return
    FINAL.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                     encoding="utf-8")
    evidence = {
        "schema": "phase5-r5-2-1r4-3d-p15-freeze-evidence-v1",
        "P15_history_fixture_status": manifest["freeze_status"],
        "P15_historical_regression_status": formal_status,
        "gate": gate,
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_SHA,
        "final_freeze_manifest_sha256": sha(FINAL),
        "P15_input_canonical_sha256": digest(p15),
        "P15_input_file_sha256": sha(INPUT),
        "historical_source_hashes": {
            "R4_registration": sha(R4), "R1a_registration": sha(r1a.REGISTRATION),
            "R1a_evidence": sha(OLD_EVIDENCE), "R4_3A_timing": sha(R43A),
            "R4_3B_evidence": sha(R43B), "R4_3C_evidence": sha(R43C),
            "generator": record["generator_file_sha256"],
            "underlying_generator": record["underlying_generator_file_sha256"],
            "R4_3B_engine": sha(ENGINE),
        },
        "fixture_provenance_checks": fixture_checks,
        "formal_P15_result": formal_result,
        "formal_P15_result_sha256": digest(formal_result),
        "existing_regression_checks": regressions,
        "source_immutability": immutability,
        "Git_HEAD": head,
        "working_tree_status_at_freeze_start": status_at_freeze_start.splitlines(),
        "FULL_P_HISTORY_VALIDATION_AVAILABLE": "NO",
        "FULL_P_HISTORY_VALIDATION_PASSED": "NOT_EVALUABLE",
        "CAN_PRODUCTION_PORT_START": "NO",
        "Phase_6_started": False,
        "Git_committed_or_pushed": False,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"gate": gate, "P15_result": formal_status,
                      "fixture_checks": all(fixture_checks.values()),
                      "formal_checks": all(checks.values()),
                      "repeat_hashes_identical": len(set(hashes)) == 1,
                      "S": f"{regressions['S_pass']}/{regressions['S_total']}",
                      "C": f"{regressions['C_pass']}/{regressions['C_total']}",
                      "startup": regressions["startup_pass"],
                      "freeze_manifest_sha256": sha(FINAL)}, indent=2))


if __name__ == "__main__":
    main()
