"""R4.3B candidate-only observable-progress compatibility evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256

from v0_2.examples import phase5_r5_2_1r1_validation as r1
from v0_2.examples import phase5_r5_2_1r1a_validation as r1a
from v0_2.examples.phase5_r5_2_1r4_3_history_validation import c_acceptance, s_acceptance
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import (
    PROFILE,
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    build_cases,
    load,
    synthetic,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha
from v0_2.tests.control import test_phase5_r5_2_1r4_1_deferred_demand as r41

EVIDENCE = ROOT / "phase5_r5_2_1r4_3b_observable_progress_evidence.json"
R4_REGISTRATION = ROOT / "phase5_r5_2_1r4_paired_reference_tracking_registration.json"
R43A_EVIDENCE = ROOT / "phase5_r5_2_1r4_3a_historical_timing_p_recovery_evidence.json"


def run(source, profile, classifier):
    qualifier = StartupTrackingQualifier(profile, classifier)
    for item in source:
        qualifier.update(item)
    return qualifier.snapshot()


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def prefix_causal(source, profile, classifier):
    complete = run(source, profile, classifier)["records"]
    return all(run(source[:n], profile, classifier)["records"] == complete[:n]
               for n in range(1, len(source) + 1))


def repeat_hashes(source, profile, classifier, count=10):
    return [digest(run(source, profile, classifier)) for _ in range(count)]


def row_at(case, ns):
    return next(row for row in case["records"] if row["time_ns"] == ns)


def main():
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    before = load(R43A_EVIDENCE)
    s_source = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    c_source = {key: value for key, value in r1.cases(profile).items() if key != "C9"}
    c9r_source = r1a.c9r_source(load(r1a.REGISTRATION))
    s = {key: run(value, profile, classifier) for key, value in s_source.items()}
    c = {key: run(value, profile, classifier) for key, value in c_source.items()}
    c9r = run(c9r_source, profile, classifier)
    s_result = s_acceptance(s)
    c_result = c_acceptance(c)
    s3 = s["S3"]
    s14 = s["S14"]
    anchors = [(event["time_ns"], event["new"]["resolved_command_anchor"])
               for event in c9r["resolved_pair_events"]]
    anchor_expected = [(0, 0.35), (1_000_000_000, 0.51), (3_800_000_000, 0.67)]
    same_sample = {
        key: {"qualified_progress": row_at(s[key], 1_000_000_000)["qualified_progress"],
              "public_state": row_at(s[key], 1_000_000_000)["state"],
              "internal_anchor_event_at_ns": next(event["time_ns"] for event in s[key]["resolved_pair_events"]
                                                   if event["new"]["source_epoch_id"] is not None),
              "next_public_state": row_at(s[key], 1_200_000_000)["state"]}
        for key in ("S3", "S14")
    }
    changed_command = list(s_source["S3"][:7])
    changed_command[-1] = replace(changed_command[-1], plc_command=0.5,
                                  command_timestamp_ns=1_200_000_000)
    invalid_measurement = list(s_source["S3"][:7])
    invalid_measurement[-1] = replace(invalid_measurement[-1], measured_speed=None, quality="MISSING")
    withdrawal = run(changed_command, profile, classifier)
    invalid = run(invalid_measurement, profile, classifier)
    startup_cancel = run(synthetic(profile, {0: 0.7, 200_000_000: 0.5,
                                            1_400_000_000: 0.7},
                                   duration_ns=3_000_000_000, initial_speed=0.5), profile, classifier)
    evidence_pause = run(synthetic(profile, {0: 0.7, 1_400_000_000: 0.5,
                                            2_600_000_000: 0.7},
                                   duration_ns=4_000_000_000, initial_speed=0.5), profile, classifier)
    r41_source = r41._cases()["R41-7"]
    r41_old = r41._run(r41_source)
    r41_new = run(r41_source, profile, classifier)
    r41_old_pass = any(event["event"] == "START" and event["expected_direction"] == -1
                       for event in r41_old["epoch_events"] if event["time_ns"] >= 1_200_000_000)
    r41_new_pass = any(event["event"] == "START" and event["expected_direction"] == -1
                       for event in r41_new["epoch_events"] if event["time_ns"] >= 1_200_000_000)
    sources = {**s_source, **c_source, "C9R": c9r_source, "R41-7": r41_source,
               "same_sample_withdrawal": changed_command,
               "same_sample_invalid": invalid_measurement}
    prefix = {key: prefix_causal(value, profile, classifier) for key, value in sources.items()}
    repeats = {key: repeat_hashes(sources[key], profile, classifier)
               for key in ("S3", "S14", "C9R", "R41-7", "same_sample_withdrawal", "same_sample_invalid")}
    repeat_pass = all(len(set(values)) == 1 for values in repeats.values())
    pytest_cmd = [sys.executable, "-m", "pytest",
                  "v0_2/tests/control/test_phase5_r5_2_1r4_3_startup.py", "-q"]
    tests = subprocess.run(pytest_cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    test_dots = sum(len(line.split()[0]) for line in tests.stdout.splitlines()
                    if line.split() and set(line.split()[0]) == {"."})
    registered = load(R4_REGISTRATION)
    production = {path: sha(ROOT / path) == frozen for path, frozen in registered["production_sha256"].items()}
    contract15a = sha(ROOT / "contracts/15A_tracking_safety_policy_amendment.md")
    current_engine_hash = sha(ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py")
    diagnostics = {
        "same_sample_withdrawal": {
            "state_at_resolution": row_at(withdrawal, 1_000_000_000)["state"],
            "state_after_new_command": row_at(withdrawal, 1_200_000_000)["state"],
            "confirmed": withdrawal["confirmed_latched"],
        },
        "same_sample_invalid": {
            "state_at_resolution": row_at(invalid, 1_000_000_000)["state"],
            "state_after_invalid": row_at(invalid, 1_200_000_000)["state"],
            "anchor_event_ns": invalid["resolved_pair_events"][-1]["time_ns"],
        },
        "cancel_before_evidence": {
            "watch_starts": [event["watch_start_ns"] for event in startup_cancel["watch_events"]
                             if event["event"] == "START"],
            "canceled": any(event["event"] == "CANCEL" for event in startup_cancel["watch_events"]),
        },
        "pause_after_evidence": {
            "evidence_before_pause": row_at(evidence_pause, 1_200_000_000)["carried_suspicion_evidence"],
            "evidence_at_reissue": row_at(evidence_pause, 2_600_000_000)["carried_suspicion_evidence"],
            "watch_start_at_reissue": row_at(evidence_pause, 2_600_000_000)["oldest_unresolved_demand_ns"],
            "state_at_reissue": row_at(evidence_pause, 2_600_000_000)["state"],
            "confirmed_later": evidence_pause["confirmed_latched"],
        },
        "R41-7": {"old_R4_1_expected_direction_pass": r41_old_pass,
                    "R4_3B_expected_direction_pass": r41_new_pass,
                    "R4_3B_recovery_state": row_at(r41_new, 1_200_000_000)["state"]},
    }
    checks = {
        "S3_state_sequence": s_result["S3"],
        "S14_state_sequence": s_result["S14"],
        "S_all_17": len(s_result) == 17 and all(s_result.values()),
        "C_all_11": len(c_result) == 11 and all(c_result.values()),
        "C9R_anchors_unchanged": anchors == anchor_expected,
        "same_sample_internal_anchor_and_public_progress": all(
            value["qualified_progress"] and value["public_state"] == "TRACKING_PROGRESS"
            and value["internal_anchor_event_at_ns"] == 1_000_000_000
            and value["next_public_state"] == "STEADY_TRACKING" for value in same_sample.values()),
        "intervening_command_reevaluated": diagnostics["same_sample_withdrawal"]["state_after_new_command"]
                                           != "STEADY_TRACKING" and not withdrawal["confirmed_latched"],
        "intervening_invalid_reevaluated": diagnostics["same_sample_invalid"]["state_after_invalid"]
                                           == "INSUFFICIENT_MEASUREMENT",
        "withdrawal_and_reissue_preserved": diagnostics["cancel_before_evidence"]["watch_starts"]
                                            == [0, 1_400_000_000]
                                            and diagnostics["pause_after_evidence"]["evidence_before_pause"] >= 1
                                            and diagnostics["pause_after_evidence"]["evidence_at_reissue"] >= 1
                                            and diagnostics["pause_after_evidence"]["watch_start_at_reissue"] == 0
                                            and diagnostics["pause_after_evidence"]["state_at_reissue"]
                                            != "TRACKING_FAULT_CONFIRMED",
        "R41_7_candidate": r41_new_pass,
        "prefix_causal": all(prefix.values()),
        "ten_repeat_deterministic": repeat_pass,
        "startup_suite_50": tests.returncode == 0 and test_dots == 50,
        "profile_frozen": sha(PROFILE) == registered["source_sha256"]["phase5_r5_2_2_fixture_tracking_profile.json"],
        "contract15a_frozen": contract15a == registered["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"],
        "production_frozen": all(production.values()),
    }
    if not checks["S3_state_sequence"] or not checks["S14_state_sequence"]:
        gate = "OBSERVABLE_PROGRESS_REGRESSION_REMAINS"
    elif not checks["C9R_anchors_unchanged"]:
        gate = "OBSERVABLE_PROGRESS_FIX_ALTERS_ANCHOR_SEMANTICS"
    elif not checks["withdrawal_and_reissue_preserved"]:
        gate = "STARTUP_TRACKING_REGRESSION_REINTRODUCED"
    elif not all(checks.values()):
        gate = "TRACKING_SAFETY_REGRESSION_FOUND"
    else:
        gate = "OBSERVABLE_PROGRESS_COMPATIBILITY_RESTORED"
    evidence = {
        "schema": "phase5-r5-2-1r4-3b-observable-progress-v1",
        "engine_sha256_before": before["r4_3_engine_sha256"],
        "engine_sha256_after": current_engine_hash,
        "historical_source_sha256": {path.name: sha(path) for path in
                                     (R52_EVIDENCE, R522_EVIDENCE, r1a.REGISTRATION, R43A_EVIDENCE)},
        "S3_states": [row["state"] for row in s3["records"]],
        "S14_states": [row["state"] for row in s14["records"]],
        "S_acceptance": s_result, "C_acceptance": c_result,
        "same_sample_resolution": same_sample,
        "C9R_anchors": anchors, "C9R_expected_candidate_anchors": anchor_expected,
        "diagnostics": diagnostics, "prefix_causality": prefix,
        "repeatability_hashes_10x": repeats,
        "startup_suite": {"original_cases": 46, "expanded_cases": test_dots,
                          "returncode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr},
        "production_safety_sha256": sha(ROOT / "v0_2/safety/supervisor.py"),
        "production_source_hash_checks": production,
        "contract15a_sha256": contract15a,
        "checks": checks,
        "P_history_status": "P15 deterministic reconstruction candidate; remaining 19 partial; no formal P gate",
        "full_historical_validation": False,
        "production_port_eligible": False,
        "gate": gate,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"gate": gate, "checks": checks, "S_pass": sum(s_result.values()),
                      "C_pass": sum(c_result.values()), "C9R_anchors": anchors,
                      "startup_tests": test_dots}, indent=2))


if __name__ == "__main__":
    main()
