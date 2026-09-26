"""Pre-registered C1-C12 offline validation and frozen historical regression."""

from __future__ import annotations

import json

from v0_2.examples.phase5_r5_2_1r1_cumulative_engine import CumulativeTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import (
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    acceptance,
    build_cases,
    from_calibration,
    invariants,
    load,
    states,
    synthetic,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import run_open_loop, sha

REGISTRATION = ROOT / "phase5_r5_2_1r1_cumulative_command_demand_registration.json"
PROFILE = ROOT / "phase5_r5_2_2_fixture_tracking_profile.json"
PRIOR_EVIDENCE = ROOT / "phase5_r5_2_1r_continuous_tracking_semantics_evidence.json"
EVIDENCE = ROOT / "phase5_r5_2_1r1_cumulative_command_demand_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_1r1_cumulative_command_demand.png"


def verify_sources(reg: dict) -> dict:
    checks = {name: sha(ROOT / name) == expected for name, expected in
              {**reg["source_sha256"], **reg["frozen_production_sha256"]}.items()}
    if sha(PROFILE) != "9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8":
        raise RuntimeError("R5_2_2_TRACKING_PROFILE_HASH_MISMATCH")
    if load(PRIOR_EVIDENCE)["status"] != reg["prior_gate"] or not all(checks.values()):
        raise RuntimeError(f"Frozen historical source mismatch: {checks}")
    return checks


def execute(source: list, profile: dict, classifier: dict) -> dict:
    qualifier = CumulativeTrackingQualifier(profile, classifier)
    for item in source:
        qualifier.update(item)
    result = qualifier.snapshot()
    prefix_pass = True
    for length in range(1, len(source) + 1):
        prefix = CumulativeTrackingQualifier(profile, classifier)
        for item in source[:length]:
            prefix.update(item)
        if prefix.records != result["records"][:length]:
            prefix_pass = False
            break
    result["prefix_causal"] = prefix_pass
    result["input_trace"] = [item.__dict__ for item in source]
    return result


def _normal(initial: float, commands: dict[int, float], duration_ns: int) -> list:
    return from_calibration(run_open_loop(initial, tuple(commands.items()),
                                          200_000_000, duration_ns)["rows"])


def cases(profile: dict) -> dict:
    up = {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7, 600_000_000: 0.8}
    down = {0: 0.8, 200_000_000: 0.7, 400_000_000: 0.6, 600_000_000: 0.5}
    duration = 3_000_000_000
    return {
        "C1": synthetic(profile, up, duration_ns=duration, initial_speed=0.5),
        "C2": _normal(0.5, up, 5_000_000_000),
        "C3_normal": _normal(0.8, down, 5_000_000_000),
        "C3_stuck": synthetic(profile, down, duration_ns=duration, initial_speed=0.8),
        "C4": synthetic(profile, {0: 0.5, **{t: 0.6 if i % 2 == 0 else 0.5
                             for i, t in enumerate(range(200_000_000, duration + 1, 200_000_000))}},
                        duration_ns=duration, initial_speed=0.5),
        "C5": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7},
                        duration_ns=duration, initial_speed=0.5),
        "C6": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.5},
                        duration_ns=duration, initial_speed=0.5),
        "C7": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                  1_600_000_000: 0.5}, duration_ns=duration, initial_speed=0.5),
        "C8_normal": _normal(0.5, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                    800_000_000: 0.3}, 5_000_000_000),
        "C8_stuck": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                        800_000_000: 0.3}, duration_ns=duration, initial_speed=0.5),
        "C9": synthetic(profile, {**up, 3_000_000_000: 0.9, 3_200_000_000: 1.0},
                        duration_ns=6_000_000_000, initial_speed=0.5,
                        speed_changes={800_000_000: 0.55, 1_000_000_000: 0.60,
                                       1_200_000_000: 0.65, 1_400_000_000: 0.70,
                                       1_600_000_000: 0.75, 1_800_000_000: 0.80,
                                       3_600_000_000: 0.85, 3_800_000_000: 0.90,
                                       4_000_000_000: 0.95, 4_200_000_000: 1.0}),
        "C10": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                   1_000_000_000: 0.8}, duration_ns=1_200_000_000,
                         initial_speed=0.5, speed_changes={800_000_000: 0.54}),
        "C11": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7},
                         duration_ns=duration, initial_speed=0.5,
                         invalid=(400_000_000, 1_200_000_000)),
        "C12": synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.5,
                                   600_000_000: 0.6, 800_000_000: 0.7,
                                   1_000_000_000: 0.8}, duration_ns=4_000_000_000,
                         initial_speed=0.5),
    }


def _starts(case: dict) -> list[dict]:
    return [event for event in case["epoch_events"] if event["event"] == "START"]


def assess(c: dict) -> dict:
    confirmed = "TRACKING_FAULT_CONFIRMED"
    suspect = "TRACKING_FAULT_SUSPECTED"
    return {
        "C1": bool(_starts(c["C1"])) and suspect in states(c["C1"]) and confirmed in states(c["C1"]),
        "C2": bool(_starts(c["C2"])) and "TRACKING_PROGRESS" in states(c["C2"]) and
              confirmed not in states(c["C2"]) and c["C2"]["qualified_command_anchor"] == 0.8,
        "C3": bool(_starts(c["C3_normal"])) and confirmed not in states(c["C3_normal"]) and
              confirmed in states(c["C3_stuck"]),
        "C4": not _starts(c["C4"]) and confirmed not in states(c["C4"]),
        "C5": bool(_starts(c["C5"])) and _starts(c["C5"])[0]["time_ns"] == 400_000_000,
        "C6": not _starts(c["C6"]) and c["C6"]["qualified_command_anchor"] == 0.5,
        "C7": bool(_starts(c["C7"])) and any(row["watch_id"] for row in c["C7"]["records"]
              if row["time_ns"] >= 1_600_000_000),
        "C8": len(_starts(c["C8_normal"])) >= 2 and confirmed not in states(c["C8_normal"]) and
              len(_starts(c["C8_stuck"])) >= 2 and confirmed in states(c["C8_stuck"]),
        "C9": len(c["C9"]["anchor_events"]) >= 2 and c["C9"]["anchor_events"][1]["new_anchor"] == 0.8 and
              any(row["time_ns"] == 3_200_000_000 and abs(row["net_command_demand"] - 0.2) < 1e-9
                  for row in c["C9"]["records"]),
        "C10": "TRACKING_PROGRESS" in states(c["C10"]) and c["C10"]["qualified_command_anchor"] == 0.5,
        "C11": "INSUFFICIENT_MEASUREMENT" in states(c["C11"]) and
               c["C11"]["qualified_command_anchor"] == 0.5 and confirmed in states(c["C11"]),
        "C12": bool(_starts(c["C12"])) and confirmed in states(c["C12"]),
    }


def new_invariants(c: dict) -> dict:
    c1, c4, c7, c10, c12 = (c[key] for key in ("C1", "C4", "C7", "C10", "C12"))
    return {
        "9_net_material_demand_cannot_hide": bool(_starts(c1)) and bool(_starts(c12)),
        "10_no_path_length_false_accumulation": not _starts(c4) and c4["qualified_command_anchor"] == 0.5,
        "11_anchor_advance_only_after_resolution": c10["qualified_command_anchor"] == 0.5 and
            all(event["anchor_update_reason"] in ("DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE",
                                                  "QUALIFIED_EPOCH_RESOLVED_TO_STEADY")
                for case in c.values() for event in case["anchor_events"]),
        "12_return_reversal_preserves_evidence": bool(_starts(c7)) and
            any(row["watch_id"] for row in c7["records"] if row["time_ns"] >= 1_600_000_000) and
            c["C8_stuck"]["confirmed_latched"],
    }


def _audit_rows(case: dict) -> list[dict]:
    return [{"time_ns": row["time_ns"], "plc_command": row["plc_command"],
             "qualified_anchor": row["qualified_command_anchor"],
             "net_demand": row["net_command_demand"], "demand_class": row["net_demand_classification"],
             "epoch_active": row["epoch_id"] is not None and row["state"] != "STEADY_TRACKING",
             "watch_active": row["watch_active"], "measured_speed": row["measured_speed"],
             "tracking_state": row["state"]} for row in case["records"]]


def make_figure(c: dict, historical: dict, invariants_all: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 2, figsize=(16, 16))
    for index, (key, title) in enumerate((("C1", "C1 stuck: command / anchor / net"),
                                          ("C1", "C1 tracking state"),
                                          ("C2", "C2 normal actuator"),
                                          ("C4", "C4 back-and-forth chatter"),
                                          ("C7", "C7 return after opportunity"),
                                          ("C9", "C9 anchor advancement"),
                                          ("C12", "C12 cumulative-step attack"))):
        rows = c[key]["records"]
        t = [row["time_ns"] / 1e9 for row in rows]
        ax = axes.flat[index]
        if index == 1:
            mapping = {name: n for n, name in enumerate(("STEADY_TRACKING", "HANDOFF_PENDING",
                        "TRACKING_PROGRESS", "TRACKING_FAULT_SUSPECTED",
                        "TRACKING_FAULT_CONFIRMED", "INSUFFICIENT_MEASUREMENT"))}
            ax.step(t, [mapping[row["state"]] for row in rows], where="post")
            ax.set_yticks(list(mapping.values()), list(mapping), fontsize=6)
        else:
            for field, label in (("plc_command", "PLC command"),
                                 ("qualified_command_anchor", "qualified anchor"),
                                 ("net_command_demand", "signed net demand"),
                                 ("measured_speed", "released speed")):
                ax.step(t, [row[field] for row in rows], where="post", label=label)
            ax.legend(fontsize=6)
        ax.set_title(title)
        ax.set_xlabel("time (s)")
        ax.grid(alpha=0.2)
    ax = axes.flat[7]
    ax.axis("off")
    ax.text(0.03, 0.85, f"Historical S1-S16 + variant pass: {sum(historical.values())}/{len(historical)}",
            transform=ax.transAxes)
    ax.text(0.03, 0.70, f"Invariants pass: {sum(invariants_all.values())}/{len(invariants_all)}",
            transform=ax.transAxes)
    ax.set_title("Historical and invariant regression")
    fig.suptitle("OFFLINE CONTINUOUS TRACKING SEMANTICS — GENERIC NUMERICAL FIXTURE\n"
                 "NO PRODUCTION SAFETY CHANGE — NOT OEM / NVIDIA / GB300 VALIDATION")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = load(REGISTRATION)
    source_checks = verify_sources(reg)
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    input_cases = cases(profile)
    c = {key: execute(source, profile, classifier) for key, source in input_cases.items()}
    c_pass = assess(c)
    historical_inputs = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    historical = {key: execute(source, profile, classifier) for key, source in historical_inputs.items()}
    s_pass = acceptance(historical)
    historical_prefix = {key: case["prefix_causal"] for key, case in historical.items()}
    original_invariants = invariants(historical, historical_prefix)
    added = new_invariants(c)
    all_invariants = {**original_invariants, **added}
    all_prefix = {**historical_prefix, **{key: case["prefix_causal"] for key, case in c.items()}}
    command_min = profile["ActuatorTrackingProfile"]["speed_min"]["value"]
    command_max = profile["ActuatorTrackingProfile"]["speed_max"]["value"]
    domain_violations = {
        key: [{"time_ns": row["time_ns"], "plc_command": row["plc_command"]}
              for row in case["records"]
              if not command_min <= row["plc_command"] <= command_max]
        for key, case in c.items()
    }
    domain_violations = {key: rows for key, rows in domain_violations.items() if rows}
    semantic_c_pass = dict(c_pass)
    if "C9" in domain_violations:
        c_pass["C9"] = False
    if domain_violations:
        gate = "CUMULATIVE_COMMAND_DEMAND_VALIDATION_FIXTURE_OUT_OF_PROFILE_DOMAIN"
    elif not c_pass["C1"] or not c_pass["C3"] or not c_pass["C12"]:
        gate = "CUMULATIVE_COMMAND_DEMAND_CAN_STILL_MASK_SILENT_FAULT"
    elif not c_pass["C4"] or not added["10_no_path_length_false_accumulation"]:
        gate = "COMMAND_PATH_LENGTH_FALSE_ACCUMULATION"
    elif (not c_pass["C10"] or not added["11_anchor_advance_only_after_resolution"]
          or not all(c_pass.values()) or not all(s_pass.values())
          or not all(all_invariants.values()) or not all(all_prefix.values())):
        gate = "QUALIFIED_COMMAND_ANCHOR_CAN_ERASE_UNRESOLVED_FAULT_EVIDENCE"
    else:
        gate = "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED"
    evidence = {
        "schema": "phase5-r5-2-1r1-evidence-v1", "registration_sha256": sha(REGISTRATION),
        "source_sha256": reg["source_sha256"], "source_hash_checks": source_checks,
        "profile_sha256": sha(PROFILE), "profile_recalibrated": False,
        "new_numeric_tracking_parameters": False,
        "profile_command_domain": {"min": command_min, "max": command_max},
        "post_validation_domain_audit": domain_violations,
        "case_definitions": reg["cases"], "c_cases": c,
        "semantic_c_pass_before_domain_audit": semantic_c_pass, "c_pass": c_pass,
        "historical_cases": historical, "historical_pass": s_pass,
        "original_invariants": original_invariants, "added_invariants": added,
        "prefix_causality": all_prefix,
        "audit_tables": {key: _audit_rows(c[key]) for key in ("C1", "C2", "C4", "C7", "C9", "C12")},
        "profile_portability": "State machine uses frozen profile fields; hardware requires separate calibration.",
        "production_hashes_unchanged": all(source_checks.values()),
        "production_safety_changed": False, "phase5_r5_3r_started": False,
        "final_feedback_baseline_frozen": False, "phase6_started": False,
        "blocking_issues": ([] if gate == "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED" else
                            (["Registered C9 command 1.0 exceeds frozen profile speed_max 0.9; C9 anchor advancement is outside fixture validity."]
                             if domain_violations else
                             [key for key, ok in {**c_pass, **s_pass, **all_invariants, **all_prefix}.items() if not ok])),
        "status": gate,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(c, s_pass, all_invariants)
    print(json.dumps({"status": gate, "registration_sha256": sha(REGISTRATION),
                      "evidence_sha256": sha(EVIDENCE), "c_pass": c_pass,
                      "historical_pass": s_pass, "invariants": all_invariants,
                      "prefix_causality": all(all_prefix.values())}, indent=2))


if __name__ == "__main__":
    main()
