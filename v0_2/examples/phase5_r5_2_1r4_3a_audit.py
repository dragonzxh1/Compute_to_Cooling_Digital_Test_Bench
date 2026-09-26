"""Read-only semantic replay and P-input provenance audit; no candidate engine edits."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

from v0_2.examples import phase5_r5_2_1r1_validation as r1
from v0_2.examples import phase5_r5_2_1r1a_validation as r1a
from v0_2.examples.phase5_r5_2_1r4_1_deferred_engine import DeferredDemandTrackingQualifier
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier
from v0_2.examples.phase5_r5_2_1r4_paired_engine import PairedReferenceTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import (
    PROFILE,
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    build_cases,
    has_order,
    load,
    synthetic,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

REGISTRATION = ROOT / "phase5_r5_2_1r4_paired_reference_tracking_registration.json"
MANIFEST = ROOT / "phase5_r5_2_1_p_history_input_recovery_manifest.json"
EVIDENCE = ROOT / "phase5_r5_2_1r4_3a_historical_timing_p_recovery_evidence.json"
P15_INPUT = ROOT / "v0_2/tests/data/tracking_history/P15_C9R_candidate.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def candidate(source, kind, profile, classifier):
    qualifier = kind(profile, classifier)
    for item in source:
        qualifier.update(item)
    return qualifier.snapshot()


def prefix_causal(source, profile, classifier):
    complete = candidate(source, StartupTrackingQualifier, profile, classifier)["records"]
    return all(candidate(source[:length], StartupTrackingQualifier, profile, classifier)["records"]
               == complete[:length] for length in range(1, len(source) + 1))


def events_at(case, field, time_ns):
    return [event for event in case[field] if event["time_ns"] == time_ns]


def s_timeline(source, old, current):
    rows = []
    for index, item in enumerate(source):
        before_old = old["records"][index - 1]["state"] if index else "STEADY_TRACKING"
        before_new = current["records"][index - 1]["state"] if index else "STEADY_TRACKING"
        old_row, new_row = old["records"][index], current["records"][index]
        rows.append({
            "time_ns": item.time_ns, "command": item.plc_command,
            "measured_speed": item.measured_speed, "measurement_valid": old_row["valid"] and new_row["valid"],
            "old": {
                "state_before": before_old, "state_after": old_row["state"],
                "resolved_command_anchor": old_row["qualified_command_anchor"],
                "direction": old_row["expected_direction"], "watch_id": old_row["watch_id"],
                "watch_start_ns": old_row["watch_start_ns"],
                "qualified_progress_observable": old_row["state"] == "TRACKING_PROGRESS"
                    or bool(events_at(old, "watch_events", item.time_ns)
                            and any(e["event"] == "RESOLVE" for e in events_at(old, "watch_events", item.time_ns))),
                "transition_reasons": events_at(old, "watch_events", item.time_ns)
                    + events_at(old, "epoch_events", item.time_ns)
                    + events_at(old, "anchor_events", item.time_ns),
            },
            "r4_3": {
                "state_before": before_new, "state_after": new_row["state"],
                "resolved_command_anchor": new_row["resolved_command_anchor"],
                "resolved_measurement_anchor": new_row["resolved_measurement_anchor"],
                "direction": new_row["epoch_expected_direction"],
                "watch_id": new_row["watch_id"],
                "watch_start_ns": new_row["oldest_unresolved_demand_ns"],
                "qualified_progress": new_row["qualified_progress"],
                "carried_suspicion_evidence": new_row["carried_suspicion_evidence"],
                "transition_reasons": events_at(current, "watch_events", item.time_ns)
                    + events_at(current, "epoch_events", item.time_ns)
                    + events_at(current, "resolved_pair_events", item.time_ns),
            },
        })
    return rows


def c9r_timeline(source, cases):
    rows = []
    for index, item in enumerate(source):
        by_kind = {}
        for name, case in cases.items():
            row = case["records"][index]
            old = name == "R1a"
            anchor_event = events_at(case, "anchor_events" if old else "resolved_pair_events", item.time_ns)
            by_kind[name] = {
                "state": row["state"], "measurement_valid": row["valid"],
                "command_anchor": row["qualified_command_anchor"] if old else row["resolved_command_anchor"],
                "measurement_anchor": None if old else row["resolved_measurement_anchor"],
                "qualified_progress": row["state"] == "TRACKING_PROGRESS" if old else row["qualified_progress"],
                "watch_id": row["watch_id"],
                "watch_age_start_ns": row["watch_start_ns"] if old else row["oldest_unresolved_demand_ns"],
                "direction": row["expected_direction"] if old else row.get("epoch_expected_direction"),
                "anchor_advanced": bool(anchor_event),
                "anchor_reason": anchor_event[0]["anchor_update_reason" if old else "reason"] if anchor_event else None,
                "resolved": row["state"] == "STEADY_TRACKING" and bool(anchor_event),
            }
        rows.append({"time_ns": item.time_ns, "command": item.plc_command,
                     "measured_speed": item.measured_speed, "versions": by_kind})
    return rows


def withdrawal_diagnostic(profile, classifier):
    schedules = {
        "withdraw_before_evidence": {0: 0.7, 200_000_000: 0.5, 1_400_000_000: 0.7},
        "withdraw_after_evidence": {0: 0.7, 1_400_000_000: 0.5, 1_600_000_000: 0.7,
                                     3_000_000_000: 0.5},
        "short_repeated_pulses": {0: 0.7, 1_400_000_000: 0.5, 1_600_000_000: 0.7,
                                  1_800_000_000: 0.5, 2_000_000_000: 0.7,
                                  2_200_000_000: 0.5, 2_400_000_000: 0.7,
                                  2_600_000_000: 0.5, 2_800_000_000: 0.7},
    }
    results = {}
    for name, commands in schedules.items():
        source = synthetic(profile, commands, duration_ns=5_000_000_000, initial_speed=0.5)
        result = candidate(source, StartupTrackingQualifier, profile, classifier)
        results[name] = {
            "kind": "DIAGNOSTIC_ONLY_SYNTHETIC_NOT_HISTORICAL_GATE",
            "commands": commands,
            "first_confirmed_ns": next((row["time_ns"] for row in result["records"]
                                        if row["state"] == "TRACKING_FAULT_CONFIRMED"), None),
            "watch_starts": [event for event in result["watch_events"] if event["event"] == "START"],
            "at_command_events": [{"time_ns": row["time_ns"], "state": row["state"],
                                   "evidence": row["carried_suspicion_evidence"],
                                   "oldest_unresolved_demand_ns": row["oldest_unresolved_demand_ns"]}
                                  for row in result["records"] if row["time_ns"] in commands],
            "prefix_causal": prefix_causal(source, profile, classifier),
        }
    return results


def main():
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    s_sources = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    s = {}
    for name in ("S3", "S14"):
        old = r1.execute(s_sources[name], profile, classifier)
        current = candidate(s_sources[name], StartupTrackingQualifier, profile, classifier)
        expected = ("TRACKING_FAULT_SUSPECTED", "TRACKING_PROGRESS")
        old_sequence = has_order(old, expected)
        current_sequence = has_order(current, expected)
        s[name] = {
            "source_is_same_as_other_delay_case": s_sources[name] == s_sources["S14" if name == "S3" else "S3"],
            "timeline": s_timeline(s_sources[name], old, current),
            "prefix_causal": prefix_causal(s_sources[name], profile, classifier),
            "old_public_states": list(dict.fromkeys(row["state"] for row in old["records"])),
            "r4_3_public_states": list(dict.fromkeys(row["state"] for row in current["records"])),
            "old_sequence_required_pass": old_sequence,
            "r4_3_sequence_pass": current_sequence,
            "qualified_on_steady_sample": any(row["qualified_progress"] and row["state"] == "STEADY_TRACKING"
                                              for row in current["records"]),
            "verdict": "HISTORICAL_REGRESSION" if old_sequence and not current_sequence
                       else "VALID_SEMANTIC_EQUIVALENCE" if old_sequence and current_sequence
                       else "INSUFFICIENT_HISTORICAL_EVIDENCE",
        }

    c_source = r1a.c9r_source(load(r1a.REGISTRATION))
    c_cases = {"R1a": r1.execute(c_source, profile, classifier)}
    for name, kind in (("R4", PairedReferenceTrackingQualifier),
                       ("R4.1", DeferredDemandTrackingQualifier),
                       ("R4.3", StartupTrackingQualifier)):
        c_cases[name] = candidate(c_source, kind, profile, classifier)
    c9r_rows = c9r_timeline(c_source, c_cases)
    anchors = {
        "R1a": [{"time_ns": event["time_ns"], "command": event["new_anchor"],
                 "measurement": None,
                 "observed_measurement_at_event": next(
                     row.measured_speed for row in c_source if row.time_ns == event["time_ns"]
                 )}
                for event in c_cases["R1a"]["anchor_events"]],
    }
    for name in ("R4", "R4.1", "R4.3"):
        anchors[name] = [{"time_ns": event["time_ns"],
                          "command": event["new"]["resolved_command_anchor"],
                          "measurement": event["new"]["resolved_measurement_anchor"]}
                         for event in c_cases[name]["resolved_pair_events"]]
    suffix = []
    for row in c9r_rows:
        if row["time_ns"] >= 3_800_000_000:
            suffix.append({"time_ns": row["time_ns"],
                           "old_state": row["versions"]["R1a"]["state"],
                           "r4_3_state": row["versions"]["R4.3"]["state"],
                           "old_watch": row["versions"]["R1a"]["watch_id"],
                           "r4_3_watch": row["versions"]["R4.3"]["watch_id"],
                           "old_direction": row["versions"]["R1a"]["direction"],
                           "r4_3_direction": row["versions"]["R4.3"]["direction"]})

    p15 = {
        "schema": "P_HISTORY_RECOVERY_CANDIDATE-v1",
        "case_id": "P15", "basis": "R4 registration P15 = C9R A-to-B-to-C; R1a frozen generator",
        "observations": [asdict(item) for item in c_source],
    }
    P15_INPUT.parent.mkdir(parents=True, exist_ok=True)
    P15_INPUT.write_text(json.dumps(p15, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    p15_digest = sha256(canonical(p15)).hexdigest()
    registration = load(REGISTRATION)
    manifest = {
        "schema": "P_HISTORY_RECOVERY_CANDIDATE-v1",
        "canonical_hash_rule": "SHA-256 of UTF-8 JSON sort_keys=True separators=(',', ':') ensure_ascii=False; no trailing newline",
        "source_registration_sha256": sha(REGISTRATION),
        "cases": [],
    }
    for index in range(1, 21):
        case_id = f"P{index}"
        exact = index == 15
        manifest["cases"].append({
            "case_id": case_id,
            "purpose": registration["preregistered_case_matrix"][case_id],
            "recovery_status": "RECONSTRUCTED_DETERMINISTICALLY" if exact else "PARTIALLY_RECOVERED",
            "source_evidence": ["phase5_r5_2_1r4_paired_reference_tracking_registration.json"]
                + (["phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json",
                    "v0_2/examples/phase5_r5_2_1r1a_validation.py",
                    "v0_2/examples/phase5_r5_2_2_tracking_calibration.py"] if exact else []),
            "input_file": str(P15_INPUT.relative_to(ROOT)).replace("\\", "/") if exact else None,
            "input_sha256": p15_digest if exact else None,
            "expected_behavior_source": "phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json"
                if exact else None,
            "timing_normative": "TRIGGER_EXACT; ANCHOR_ORDER_ONLY" if exact else "UNKNOWN",
            "known_ambiguities": (
                ["P15 is named C9R but no independent R4 P15 capture exists; candidate requires manifest review"]
                if exact else [(
                    "No frozen P-specific executable input timeline, measurement sequence, "
                    "validity/fault fixture, or exact public-state oracle exists"
                )]
            ),
            "formal_gate_eligible": False,
        })
    manifest_digest = sha256(canonical(manifest)).hexdigest()
    MANIFEST.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    production = {name: sha(ROOT / name) == expected for name, expected in registration["production_sha256"].items()}
    prior_history = load(ROOT / "phase5_r5_2_1r4_3_full_history_evidence.json")
    contract_hash = sha(ROOT / "contracts/15A_tracking_safety_policy_amendment.md")
    current_engine_hash = sha(ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py")
    evidence = {
        "schema": "phase5-r5-2-1r4-3a-audit-v1",
        "source_hashes": {name: sha(ROOT / name) for name in (
            "phase5_r5_2_1r4_paired_reference_tracking_registration.json",
            "phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json",
            "v0_2/examples/phase5_r5_2_1r1_validation.py",
            "v0_2/examples/phase5_r5_2_1r1a_validation.py",
            "v0_2/examples/phase5_r5_2_2_tracking_calibration.py",
            "phase5_r5_2_silent_tracking_fault_evidence.json",
            "phase5_r5_2_2_tracking_calibration_evidence.json",
            "phase5_r5_2_2_fixture_tracking_profile.json",
            "contracts/15A_tracking_safety_policy_amendment.md",
        )},
        "r4_3_engine_sha256": current_engine_hash,
        "r4_3_engine_matches_prior_evidence": current_engine_hash == prior_history["engine_sha256"],
        "contract15a_matches_registration": contract_hash == registration["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"],
        "production_source_hash_matches_registration": production,
        "s3_s14": s,
        "c9r": {
            "source_trace_sha256": sha256(canonical([asdict(item) for item in c_source])).hexdigest(),
            "anchor_updates": anchors, "timeline": c9r_rows, "suffix_after_second_shift": suffix,
            "prefix_causal": prefix_causal(c_source, profile, classifier),
            "cause": "SAME_SAMPLE_RESOLUTION",
            "timing_normativity": "ANCHOR_ORDER_ONLY_NORMATIVE; trigger times exact",
            "verdict": "TIMING_SHIFT_ACCEPTABLE_BUT_SPEC_UPDATE_REQUIRED",
        },
        "p_statuses": {item["case_id"]: item["recovery_status"] for item in manifest["cases"]},
        "candidate_input_hashes": {"P15": p15_digest},
        "aggregate_manifest_sha256": manifest_digest,
        "diagnostic_test_results": {"P15_prefix_causal": prefix_causal(c_source, profile, classifier),
                                    "P15_formal_gate": "NOT_RUN_CANDIDATE_ONLY"},
        "withdrawal_reissue_diagnostics": withdrawal_diagnostic(profile, classifier),
        "gate": "R4_3A_HISTORICAL_TIMING_REGRESSION_FOUND",
        "production_safety_changed": False,
        "r4_3_engine_changed": current_engine_hash != prior_history["engine_sha256"],
        "contract15a_changed": contract_hash != registration["source_sha256"]["contracts/15A_tracking_safety_policy_amendment.md"],
        "phase6_started": False,
        "git_commit_or_push": False,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"gate": evidence["gate"], "s_verdicts": {k: v["verdict"] for k, v in s.items()},
                      "c9r_verdict": evidence["c9r"]["verdict"],
                      "p_statuses": evidence["p_statuses"],
                      "manifest_sha256": manifest_digest,
                      "production_hashes_ok": all(production.values())}, indent=2))


if __name__ == "__main__":
    main()
