"""Replay immutable S/C sources against the offline R4.3 candidate.

P1-P20 have names in the R4 registration but no executable frozen traces.
They are deliberately reported as unverified, not silently counted as passes.
"""

from __future__ import annotations

import json

from v0_2.examples import phase5_r5_2_1r1_validation as r1
from v0_2.examples import phase5_r5_2_1r1a_validation as r1a
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_r5_2_1r_validation import (
    PROFILE,
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    build_cases,
    load,
    states,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import sha

EVIDENCE = ROOT / "phase5_r5_2_1r4_3_full_history_evidence.json"


def replay(source, profile, classifier):
    qualifier = StartupTrackingQualifier(profile, classifier)
    for item in source:
        qualifier.update(item)
    return qualifier.snapshot()


def starts(case):
    return [event for event in case["epoch_events"] if event["event"] == "START"]


def watch_starts(case):
    return [event for event in case["watch_events"] if event["event"] == "START"]


def ordered(case, *wanted):
    cursor = 0
    for state in states(case):
        if state == wanted[cursor]:
            cursor += 1
            if cursor == len(wanted):
                return True
    return False


def s_acceptance(c):
    confirmed = "TRACKING_FAULT_CONFIRMED"
    progress = "TRACKING_PROGRESS"
    suspected = "TRACKING_FAULT_SUSPECTED"
    return {
        "S1": ordered(c["S1"], "HANDOFF_PENDING", progress, "STEADY_TRACKING") and not c["S1"]["confirmed_latched"],
        "S2": ordered(c["S2"], "HANDOFF_PENDING", suspected, confirmed),
        "S3": ordered(c["S3"], suspected, progress) and not c["S3"]["confirmed_latched"],
        "S4": c["S4"]["confirmed_latched"],
        "S5": progress in states(c["S5"]) and "STEADY_TRACKING" in states(c["S5"]) and c["S5"]["confirmed_latched"],
        "S6": c["S6"]["confirmed_latched"] and len(watch_starts(c["S6"])) == 1,
        "S7": all(row["state"] == "STEADY_TRACKING" and row["epoch_id"] is None for row in c["S7"]["records"]),
        "S8": progress in states(c["S8_normal"]) and not c["S8_normal"]["confirmed_latched"]
              and c["S8_stuck"]["confirmed_latched"] and len(watch_starts(c["S8_stuck"])) == 1,
        "S9": all(progress in states(c[k]) and not c[k]["confirmed_latched"] and len(starts(c[k])) >= 2
                  for k in ("S9_up_down", "S9_down_up")),
        "S10": "INSUFFICIENT_MEASUREMENT" in states(c["S10"]) and not c["S10"]["confirmed_latched"]
               and any(row["watch_id"] for row in c["S10"]["records"] if not row["valid"]),
        "S11": ordered(c["S11"], suspected, "INSUFFICIENT_MEASUREMENT") and not c["S11"]["confirmed_latched"]
               and any(row["watch_id"] for row in c["S11"]["records"] if not row["valid"]),
        "S12": "INSUFFICIENT_MEASUREMENT" in states(c["S12"]) and c["S12"]["confirmed_latched"]
               and len(watch_starts(c["S12"])) == 1,
        "S13": progress in states(c["S13"]) and c["S13"]["confirmed_latched"],
        "S14": ordered(c["S14"], suspected, progress) and not c["S14"]["confirmed_latched"],
        "S15": c["S15"]["confirmed_latched"] and c["S15"]["state"] == confirmed
               and any(row["measured_speed"] > c["S15"]["records"][0]["measured_speed"]
                       for row in c["S15"]["records"] if row["state"] == confirmed),
        "S16": c["S16"]["confirmed_latched"] and len({x["watch_start_ns"] for x in watch_starts(c["S16"])}) == 1,
        "S16_variant": c["S16_variant"]["confirmed_latched"]
                       and len({x["watch_start_ns"] for x in watch_starts(c["S16_variant"])}) == 1,
    }


def c_acceptance(c):
    return {
        "C1": bool(starts(c["C1"])) and c["C1"]["confirmed_latched"],
        "C2": bool(starts(c["C2"])) and "TRACKING_PROGRESS" in states(c["C2"])
              and not c["C2"]["confirmed_latched"] and c["C2"]["resolved_pair"]["resolved_command_anchor"] == 0.8,
        "C3": bool(starts(c["C3_normal"])) and not c["C3_normal"]["confirmed_latched"]
              and c["C3_stuck"]["confirmed_latched"],
        "C4": not starts(c["C4"]) and not c["C4"]["confirmed_latched"],
        "C5": bool(starts(c["C5"])) and starts(c["C5"])[0]["time_ns"] == 400_000_000,
        "C6": not starts(c["C6"]) and c["C6"]["resolved_pair"]["resolved_command_anchor"] == 0.5,
        "C7": bool(starts(c["C7"])) and any(row["watch_id"] for row in c["C7"]["records"]
              if row["time_ns"] >= 1_600_000_000),
        "C8": len(starts(c["C8_normal"])) >= 2 and not c["C8_normal"]["confirmed_latched"]
              and len(starts(c["C8_stuck"])) >= 2 and c["C8_stuck"]["confirmed_latched"],
        "C10": "TRACKING_PROGRESS" in states(c["C10"])
               and c["C10"]["resolved_pair"]["resolved_command_anchor"] == 0.5,
        "C11": "INSUFFICIENT_MEASUREMENT" in states(c["C11"])
               and c["C11"]["resolved_pair"]["resolved_command_anchor"] == 0.5
               and c["C11"]["confirmed_latched"],
        "C12": bool(starts(c["C12"])) and c["C12"]["confirmed_latched"],
    }


def main():
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    s_source = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    c_source = {name: source for name, source in r1.cases(profile).items() if name != "C9"}
    c9r_source = r1a.c9r_source(load(r1a.REGISTRATION))
    s = {name: replay(source, profile, classifier) for name, source in s_source.items()}
    c = {name: replay(source, profile, classifier) for name, source in c_source.items()}
    c9r = replay(c9r_source, profile, classifier)
    s_pass, c_pass = s_acceptance(s), c_acceptance(c)
    low = profile["ActuatorTrackingProfile"]["speed_min"]["value"]
    high = profile["ActuatorTrackingProfile"]["speed_max"]["value"]
    sources = {**s_source, **c_source, "C9R": c9r_source}
    domain = {name: all(low <= item.plc_command <= high for item in source)
              for name, source in sources.items()}
    prefix = {}
    repeatability = {}
    for name, source in sources.items():
        complete = (s | c | {"C9R": c9r})[name]
        prefix[name] = all(replay(source[:n], profile, classifier)["records"] == complete["records"][:n]
                           for n in range(1, len(source) + 1))
        repeatability[name] = all(replay(source, profile, classifier) == complete for _ in range(10))
    c9r_anchors = [(event["time_ns"], event["new"]["resolved_command_anchor"])
                    for event in c9r["resolved_pair_events"]]
    c9r_frozen = [(0, 0.35), (1_200_000_000, 0.51), (4_000_000_000, 0.67)]
    invariants = {
        "1_small_updates_preserve_age": not starts(s["S7"]),
        "2_same_direction_cannot_mask_stuck": s["S6"]["confirmed_latched"] and s["S8_stuck"]["confirmed_latched"],
        "3_no_permanent_progress_immunity": s["S5"]["confirmed_latched"] and s["S13"]["confirmed_latched"],
        "4_no_raw_actual_fallback": all(row["state"] == "INSUFFICIENT_MEASUREMENT"
                                     for row in s["S10"]["records"] if not row["valid"])
                                     and "actual_speed" not in ReleasedObservation.__dataclass_fields__,
        "5_no_auto_fault_clear": s["S15"]["confirmed_latched"] and s["S15"]["state"] == "TRACKING_FAULT_CONFIRMED",
        "6_reversal_carries_no_motion": all(len(watch_starts(s[k])) == 1 for k in ("S16", "S16_variant")),
        "7_prefix_causal": all(prefix.values()),
        "8_no_actuator_command": "actuator_command" not in ReleasedObservation.__dataclass_fields__
                                 and not hasattr(StartupTrackingQualifier, "set_pump_command"),
        "9_net_material_demand_cannot_hide": bool(starts(c["C1"])) and bool(starts(c["C12"])),
        "10_no_path_length_false_accumulation": not starts(c["C4"])
                                                and c["C4"]["resolved_pair"]["resolved_command_anchor"] == 0.5,
        "11_anchor_advance_only_after_resolution": c["C10"]["resolved_pair"]["resolved_command_anchor"] == 0.5
                                                    and all(event["reason"] in (
                                                        "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE",
                                                        "QUALIFIED_EPOCH_RESOLVED_TO_STEADY")
                                                        for case in (s | c | {"C9R": c9r}).values()
                                                        for event in case["resolved_pair_events"]),
        "12_return_reversal_preserves_evidence": bool(starts(c["C7"]))
                                                 and any(row["watch_id"] for row in c["C7"]["records"]
                                                         if row["time_ns"] >= 1_600_000_000)
                                                 and c["C8_stuck"]["confirmed_latched"],
        "13_all_commands_in_profile": all(domain.values()),
        "14_post_advance_net_uses_latest_anchor": all(
            abs(row["gross_command_demand"] - (row["plc_command"] - 0.51)) < 1e-9
            for row in c9r["records"] if 1_000_000_000 < row["time_ns"] < 3_800_000_000
        ),
    }
    evidence = {
        "schema": "phase5-r5-2-1r4-3-history-v1",
        "status": "INCOMPLETE_OR_FAIL",
        "s_c_invariant_gate": all(s_pass.values()) and all(c_pass.values()) and all(invariants.values())
                              and all(prefix.values()) and all(repeatability.values()),
        "engine_sha256": sha(ROOT / "v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py"),
        "profile_sha256": sha(PROFILE),
        "frozen_input_sha256": {path.name: sha(path) for path in (R52_EVIDENCE, R522_EVIDENCE, r1a.REGISTRATION)},
        "s_acceptance": s_pass, "c_acceptance": c_pass,
        "original_C9": "INVALID_OUT_OF_PROFILE_DOMAIN; not counted",
        "c9r_anchor_events": c9r_anchors, "c9r_frozen_anchor_events": c9r_frozen,
        "c9r_exact_timing_pass": c9r_anchors == c9r_frozen,
        "command_domain": domain, "prefix_causality": prefix, "repeatability_10x": repeatability,
        "invariants": invariants,
        "p1_p20": "UNVERIFIED: registration has descriptions only; no executable frozen traces/acceptance",
        "production_safety_changed": False,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
