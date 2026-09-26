"""Registered S1-S16 offline validation; never imports production Safety."""

from __future__ import annotations

import json
from pathlib import Path

from v0_2.examples.phase5_r5_2_1r_semantic_engine import (
    OfflineTrackingQualifier,
    ReleasedObservation,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import observations, run_open_loop, sha

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_2_1r_continuous_tracking_semantics_registration.json"
PROFILE = ROOT / "phase5_r5_2_2_fixture_tracking_profile.json"
R52_REGISTRATION = ROOT / "phase5_r5_2_silent_tracking_fault_registration.json"
R52_EVIDENCE = ROOT / "phase5_r5_2_silent_tracking_fault_evidence.json"
R522_EVIDENCE = ROOT / "phase5_r5_2_2_tracking_calibration_evidence.json"
EVIDENCE = ROOT / "phase5_r5_2_1r_continuous_tracking_semantics_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_1r_continuous_tracking_semantics.png"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def integrity(reg: dict) -> dict:
    sources = {
        "r5_evidence": "phase5_r5_directional_pi_evidence.json",
        "r5_1_evidence": "phase5_r5_1_safety_handoff_audit_evidence.json",
        "r5_2_registration": "phase5_r5_2_silent_tracking_fault_registration.json",
        "r5_2_evidence": "phase5_r5_2_silent_tracking_fault_evidence.json",
        "r5_2_1_registration": "phase5_r5_2_1_continuous_tracking_semantics_registration.json",
        "r5_2_1_spec": "phase5_r5_2_1_continuous_tracking_semantics_spec.json",
        "r5_2_1_evidence": "phase5_r5_2_1_continuous_tracking_semantics_evidence.json",
        "r5_2_2_registration": "phase5_r5_2_2_tracking_calibration_registration.json",
        "r5_2_2_evidence": "phase5_r5_2_2_tracking_calibration_evidence.json",
        "r5_2_2_profile": "phase5_r5_2_2_fixture_tracking_profile.json",
    }
    production = {
        "safety": "v0_2/safety/supervisor.py", "directional_outer": "v0_2/control/directional_outer.py",
        "outer_feedback": "v0_2/control/outer_feedback.py", "inner_loop": "v0_2/control/inner_loop.py",
        "pid": "v0_2/control/pid.py", "actuator": "v0_2/actuators/pump.py",
        "sensor": "v0_2/measurement/local_sensor.py", "plant": "v0_2/plant/controlled_loop.py",
    }
    checks = {
        **{key: sha(ROOT / path) == reg["source_sha256"][key] for key, path in sources.items()},
        **{key: sha(ROOT / path) == reg["frozen_production_sha256"][key] for key, path in production.items()},
    }
    if not all(checks.values()):
        raise RuntimeError(f"Frozen source mismatch: {checks}")
    if sha(PROFILE) != "9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8":
        raise RuntimeError("R5_2_2_TRACKING_PROFILE_HASH_MISMATCH")
    if load(R522_EVIDENCE)["status"] != reg["required_source_gate"]:
        raise RuntimeError("R5.2.2 source gate mismatch")
    return checks


def from_r52(records: list[dict]) -> list[ReleasedObservation]:
    result = []
    for record in records:
        item = record["observation"]
        sample_ns = item["measurement_sample_ns"]
        result.append(ReleasedObservation(
            item["timestamp_ns"], item["current_plc_command"], item["command_timestamp_ns"],
            item["released_measured_pump_speed"], sample_ns, item["measurement_release_ns"],
            item["measurement_quality"], f"measurement:{sample_ns}" if sample_ns is not None else f"missing:{item['timestamp_ns']}",
        ))
    return result


def from_calibration(rows: list[dict]) -> list[ReleasedObservation]:
    result = []
    for item in observations({"rows": rows}):
        result.append(ReleasedObservation(
            item["time_ns"], item["command"], item["command_timestamp_ns"] or 0,
            item["measured_speed"], item["sample_ns"], item["release_ns"],
            item["quality"], item["measurement_record_id"] or f"missing:{item['time_ns']}",
        ))
    return result


def synthetic(profile: dict, commands: dict[int, float], *, duration_ns: int,
              initial_speed: float, speed_changes: dict[int, float] | None = None,
              invalid: tuple[int, int] | None = None) -> list[ReleasedObservation]:
    period = round(profile["SensorObservationProfile"]["measurement_period_s"]["value"] * 1e9)
    speed_changes = speed_changes or {}
    command = initial_speed
    command_time = 0
    speed = initial_speed
    records = []
    for now in range(0, duration_ns + 1, period):
        if now in commands:
            command = commands[now]
            command_time = now
        if now in speed_changes:
            speed = speed_changes[now]
        good = invalid is None or not invalid[0] <= now < invalid[1]
        records.append(ReleasedObservation(now, command, command_time, speed if good else None,
                                           now, now, "VALID" if good else "MISSING", f"synthetic-measurement:{now}"))
    return records


def execute(source: list[ReleasedObservation], profile: dict, classifier: dict) -> dict:
    qualifier = OfflineTrackingQualifier(profile, classifier)
    for item in source:
        qualifier.update(item)
    complete = qualifier.snapshot()
    prefix_pass = True
    for count in range(1, len(source) + 1):
        partial = OfflineTrackingQualifier(profile, classifier)
        for item in source[:count]:
            partial.update(item)
        if partial.records != complete["records"][:count]:
            prefix_pass = False
            break
    complete["prefix_causal"] = prefix_pass
    complete["input_trace"] = [item.__dict__ for item in source]
    return complete


def states(case: dict) -> list[str]:
    result = []
    for record in case["records"]:
        if not result or result[-1] != record["state"]:
            result.append(record["state"])
    return result


def has_order(case: dict, sequence: tuple[str, ...]) -> bool:
    observed = states(case)
    cursor = 0
    for state in observed:
        if state == sequence[cursor]:
            cursor += 1
            if cursor == len(sequence):
                return True
    return False


def _all_oldest_equal(case: dict) -> bool:
    started = [x["watch_start_ns"] for x in case["watch_events"] if x["event"] == "START"]
    carried = [x["watch_start_ns"] for x in case["watch_events"] if x["event"] == "CARRY_ACROSS_REVERSAL"]
    return bool(started) and all(x == started[0] for x in carried)


def build_cases(profile: dict, old: dict, calibration: dict) -> dict:
    cases = {}
    for key, name in (("S1", "NOMINAL_COLD"), ("S2", "SILENT_STUCK"), ("S3", "DELAY_0_6"), ("S4", "DELAY_1_0"), ("S14", "DELAY_0_6")):
        cases[key] = from_r52(old["cases"][name]["speed_only_diagnostic"]["records"])
    cases["S5"] = from_calibration(calibration["post_startup_stuck"]["released_trace"])
    cases["S6"] = synthetic(profile, {0: 0.7, 400_000_000: 0.9}, duration_ns=3_000_000_000, initial_speed=0.5)
    cases["S7"] = synthetic(profile, {0: 0.5, **{time: 0.52 if index % 2 else 0.48 for index, time in enumerate(range(200_000_000, 3_000_000_001, 200_000_000))}}, duration_ns=3_000_000_000, initial_speed=0.5)
    command_schedule = ((0, 0.5), (400_000_000, 0.7), (800_000_000, 0.9))
    cases["S8_normal"] = from_calibration(run_open_loop(0.3, command_schedule, 200_000_000, 3_000_000_000)["rows"])
    cases["S8_stuck"] = from_calibration(run_open_loop(0.3, command_schedule, 200_000_000, 3_000_000_000, stuck_at_ns=0)["rows"])
    cases["S9_up_down"] = from_calibration(calibration["reversals"]["UP_THEN_DOWN"]["released_trace"])
    cases["S9_down_up"] = from_calibration(calibration["reversals"]["DOWN_THEN_UP"]["released_trace"])
    cases["S10"] = from_calibration(calibration["sensor_loss_recovery"]["released_trace"])
    cases["S11"] = synthetic(profile, {0: 0.7}, duration_ns=1_000_000_000, initial_speed=0.5, invalid=(600_000_000, 1_200_000_000))
    cases["S12"] = synthetic(profile, {0: 0.7}, duration_ns=2_000_000_000, initial_speed=0.5, invalid=(600_000_000, 1_200_000_000))
    cases["S13"] = from_calibration(run_open_loop(0.3, ((0, 0.5), (1_600_000_000, 0.7), (3_000_000_000, 0.9)), 200_000_000, 6_000_000_000, stuck_at_ns=3_000_000_000)["rows"])
    cases["S15"] = synthetic(profile, {0: 0.7}, duration_ns=2_400_000_000, initial_speed=0.5,
                             speed_changes={1_800_000_000: 0.54, 2_000_000_000: 0.58, 2_200_000_000: 0.62, 2_400_000_000: 0.65})
    cases["S16"] = synthetic(profile, {time: 0.7 if index % 2 == 0 else 0.3 for index, time in enumerate(range(0, 3_000_000_001, 200_000_000))}, duration_ns=3_000_000_000, initial_speed=0.5)
    cases["S16_variant"] = synthetic(profile, {0: 0.7, 200_000_000: 0.72, 400_000_000: 0.9,
                                               600_000_000: 0.88, 800_000_000: 0.3, 1_000_000_000: 0.32,
                                               1_200_000_000: 0.7, 1_400_000_000: 0.68, 1_600_000_000: 0.3,
                                               1_800_000_000: 0.32, 2_000_000_000: 0.7},
                                    duration_ns=3_000_000_000, initial_speed=0.5)
    return cases


def acceptance(cases: dict) -> dict:
    confirmed = "TRACKING_FAULT_CONFIRMED"
    suspect = "TRACKING_FAULT_SUSPECTED"
    progress = "TRACKING_PROGRESS"
    pending = "HANDOFF_PENDING"
    result = {
        "S1": has_order(cases["S1"], (pending, progress, "STEADY_TRACKING")) and confirmed not in states(cases["S1"]),
        "S2": has_order(cases["S2"], (pending, suspect, confirmed)),
        "S3": has_order(cases["S3"], (suspect, progress)) and confirmed not in states(cases["S3"]),
        "S4": confirmed in states(cases["S4"]),
        "S5": progress in states(cases["S5"]) and "STEADY_TRACKING" in states(cases["S5"]) and confirmed in states(cases["S5"]),
        "S6": confirmed in states(cases["S6"]) and len([x for x in cases["S6"]["watch_events"] if x["event"] == "START"]) == 1,
        "S7": all(x["state"] == "STEADY_TRACKING" and x["epoch_id"] is None for x in cases["S7"]["records"]),
        "S8": progress in states(cases["S8_normal"]) and confirmed not in states(cases["S8_normal"]) and confirmed in states(cases["S8_stuck"]) and len([x for x in cases["S8_stuck"]["watch_events"] if x["event"] == "START"]) == 1,
        "S9": all(progress in states(cases[key]) and confirmed not in states(cases[key]) and len([x for x in cases[key]["epoch_events"] if x["event"] == "START"]) >= 2 for key in ("S9_up_down", "S9_down_up")),
        "S10": "INSUFFICIENT_MEASUREMENT" in states(cases["S10"]) and confirmed not in states(cases["S10"]) and any(x["watch_id"] for x in cases["S10"]["records"] if not x["valid"]),
        "S11": has_order(cases["S11"], (suspect, "INSUFFICIENT_MEASUREMENT")) and confirmed not in states(cases["S11"]) and any(x["watch_id"] for x in cases["S11"]["records"] if not x["valid"]),
        "S12": "INSUFFICIENT_MEASUREMENT" in states(cases["S12"]) and confirmed in states(cases["S12"]) and len([x for x in cases["S12"]["watch_events"] if x["event"] == "START"]) == 1,
        "S13": states(cases["S13"]).count(progress) >= 1 and confirmed in states(cases["S13"]),
        "S14": has_order(cases["S14"], (suspect, progress)) and confirmed not in states(cases["S14"]),
        "S15": confirmed in states(cases["S15"]) and cases["S15"]["confirmed_latched"] and cases["S15"]["restored_motion_after_confirmation"] and cases["S15"]["state"] == confirmed,
        "S16": confirmed in states(cases["S16"]) and _all_oldest_equal(cases["S16"]),
        "S16_variant": confirmed in states(cases["S16_variant"]) and _all_oldest_equal(cases["S16_variant"]),
    }
    return result


def invariants(cases: dict, prefix: dict) -> dict:
    return {
        "1_small_updates_preserve_age": all(x["epoch_id"] is None for x in cases["S7"]["records"]),
        "2_same_direction_cannot_mask_stuck": cases["S6"]["confirmed_latched"] and cases["S8_stuck"]["confirmed_latched"],
        "3_no_permanent_progress_immunity": cases["S5"]["confirmed_latched"] and cases["S13"]["confirmed_latched"],
        "4_no_raw_actual_fallback": all(x["state"] == "INSUFFICIENT_MEASUREMENT" for x in cases["S10"]["records"] if not x["valid"]) and set(ReleasedObservation.__dataclass_fields__).isdisjoint({"actual_speed", "fault_identity", "scenario_label"}),
        "5_no_auto_fault_clear": cases["S15"]["confirmed_latched"] and cases["S15"]["state"] == "TRACKING_FAULT_CONFIRMED",
        "6_reversal_carries_no_motion": _all_oldest_equal(cases["S16"]) and _all_oldest_equal(cases["S16_variant"]),
        "7_prefix_causal": all(prefix.values()),
        "8_no_actuator_command": "actuator_command" not in ReleasedObservation.__dataclass_fields__ and "ActuatorCommand" not in OfflineTrackingQualifier.__dict__,
    }


def make_figure(cases: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 2, figsize=(16, 17))
    panels = axes.flat
    panels[0].text(0.05, 0.9, "STEADY → PENDING → PROGRESS → STEADY", transform=panels[0].transAxes)
    panels[0].text(0.05, 0.7, "PENDING → SUSPECTED → CONFIRMED", transform=panels[0].transAxes)
    panels[0].text(0.05, 0.5, "Any valid state → INSUFFICIENT on invalid speed", transform=panels[0].transAxes)
    panels[0].set_title("A. Internal state paths")
    panels[1].text(0.05, 0.8, "START → ACTIVE → RESOLVED / REPLACED / CONFIRMED", transform=panels[1].transAxes)
    panels[1].set_title("B. Directional epoch")
    panels[2].text(0.05, 0.8, "START → CARRY through commands/reversals", transform=panels[2].transAxes)
    panels[2].text(0.05, 0.6, "→ RESOLVE only on qualified measured motion", transform=panels[2].transAxes)
    panels[2].set_title("C. Unresolved-motion watch")
    for index, name, title in ((3, "S1", "D. Nominal cold handoff"), (4, "S2", "E. Silent stuck"),
                               (5, "S5", "F. Post-startup stuck"), (6, "S8_normal", "G. Moving command"),
                               (7, "S16", "H. Reversal attack")):
        records = cases[name]["records"]
        mapping = {"STEADY_TRACKING": 0, "HANDOFF_PENDING": 1, "TRACKING_PROGRESS": 2,
                   "TRACKING_FAULT_SUSPECTED": 3, "TRACKING_FAULT_CONFIRMED": 4, "INSUFFICIENT_MEASUREMENT": 5}
        panels[index].step([x["time_ns"] / 1e9 for x in records], [mapping[x["state"]] for x in records], where="post")
        panels[index].set_yticks(list(mapping.values()), list(mapping), fontsize=7)
        panels[index].set_title(title)
        panels[index].set_xlabel("time (s)")
    for panel in panels:
        panel.grid(alpha=0.2)
    fig.suptitle("CONTINUOUS TRACKING SEMANTICS — OFFLINE SPECIFICATION VALIDATION — GENERIC NUMERICAL FIXTURE\nNO PRODUCTION SAFETY CHANGE — NOT OEM / NVIDIA / GB300 VALIDATION", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = load(REGISTRATION)
    checks = integrity(reg)
    profile = load(PROFILE)
    classifier = load(R52_REGISTRATION)["classifier"]
    old = load(R52_EVIDENCE)
    calibration = load(R522_EVIDENCE)
    input_cases = build_cases(profile, old, calibration)
    cases = {name: execute(source, profile, classifier) for name, source in input_cases.items()}
    result = acceptance(cases)
    prefix = {name: case["prefix_causal"] for name, case in cases.items()}
    invariant = invariants(cases, prefix)
    cumulative_probe = execute(synthetic(profile, {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7,
                                                   600_000_000: 0.8}, duration_ns=3_000_000_000,
                                         initial_speed=0.5), profile, classifier)
    cumulative_masking = cumulative_probe["state"] == "STEADY_TRACKING" and not cumulative_probe["epoch_events"]
    if cumulative_masking:
        gate = "TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT"
    elif not all(result.values()):
        gate = "TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT" if not result["S16"] or not result["S16_variant"] or not result["S6"] else "CONTINUOUS_TRACKING_SEMANTICS_STILL_UNDERSPECIFIED"
    elif not all(invariant.values()) or not all(prefix.values()):
        gate = "CONTINUOUS_TRACKING_SEMANTICS_STILL_UNDERSPECIFIED"
    else:
        gate = "CONTINUOUS_TRACKING_SEMANTICS_SPECIFIED_AND_VALIDATED"
    evidence = {"schema": "phase5-r5-2-1r-continuous-tracking-semantics-evidence-v1",
                "registration_sha256": sha(REGISTRATION), "source_integrity": checks,
                "source_sha256": reg["source_sha256"], "profile_sha256": sha(PROFILE),
                "frozen_r5_2_classifier": classifier, "case_definitions": reg["sequences"],
                "cases": cases, "sequence_pass": result, "prefix_causality": prefix,
                "invariants": invariant, "all_sequences_pass": all(result.values()),
                "all_invariants_pass": all(invariant.values()),
                "parameter_source": "frozen R5.2.2 profile and frozen R5.2 classifier only",
                "post_validation_audit": {
                    "case": "Cumulative subthreshold same-direction command: stationary released speed 0.5, command 0.5 -> 0.6 -> 0.7 -> 0.8 in 0.2 s steps, held to 3 s",
                    "observed_terminal_state": cumulative_probe["state"],
                    "observed_epoch_count": len([event for event in cumulative_probe["epoch_events"] if event["event"] == "START"]),
                    "masked_silent_fault": cumulative_masking,
                    "registered_rules_modified_after_outcomes": False,
                },
                "unresolved_issues": (["Cumulative same-direction subthreshold updates can mask a silent stuck actuator; S1-S16 did not cover this trajectory."] if cumulative_masking else [key for key, ok in result.items() if not ok]),
                "production_safety_changed": False, "final_feedback_baseline_frozen": False,
                "phase6_started": False, "status": gate}
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(cases)
    print(json.dumps({"status": gate, "registration_sha256": sha(REGISTRATION),
                      "evidence_sha256": sha(EVIDENCE), "sequences": result,
                      "invariants": invariant}, indent=2))


if __name__ == "__main__":
    main()
