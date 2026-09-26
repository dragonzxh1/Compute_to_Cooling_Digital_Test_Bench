"""Frozen-engine, in-domain C9R fixture validation; historical C9 stays invalid."""

from __future__ import annotations

import json
from itertools import pairwise

from v0_2.examples import phase5_r5_2_1r1_validation as r1
from v0_2.examples.phase5_r5_2_1r_validation import (
    R52_EVIDENCE,
    R52_REGISTRATION,
    R522_EVIDENCE,
    ROOT,
    acceptance,
    build_cases,
    invariants,
    load,
)
from v0_2.examples.phase5_r5_2_2_tracking_calibration import run_open_loop, sha

REGISTRATION = ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json"
PROFILE = ROOT / "phase5_r5_2_2_fixture_tracking_profile.json"
R1_EVIDENCE = ROOT / "phase5_r5_2_1r1_cumulative_command_demand_evidence.json"
EVIDENCE = ROOT / "phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_1r1a_in_domain_anchor_revalidation.png"


def integrity(reg: dict, profile: dict) -> dict:
    checks = {name: sha(ROOT / name) == expected for name, expected in
              {**reg["source_sha256"], **reg["frozen_production_sha256"]}.items()}
    if not all(checks.values()):
        raise RuntimeError(f"Frozen source mismatch: {checks}")
    if sha(PROFILE) != reg["frozen_profile_sha256"]:
        raise RuntimeError("R5_2_2_TRACKING_PROFILE_HASH_MISMATCH")
    if sha(ROOT / "phase5_r5_2_1r1_cumulative_command_demand_registration.json") != reg["r1_registration_sha256"]:
        raise RuntimeError("R1 registration changed")
    prior = load(R1_EVIDENCE)
    if prior["status"] != reg["historical_r1_gate"] or prior["c_pass"]["C9"] is not False:
        raise RuntimeError("Historical invalid C9 changed")
    actuator = profile["ActuatorTrackingProfile"]
    bounds = (actuator["speed_min"]["value"], actuator["speed_max"]["value"])
    if bounds != (reg["frozen_profile_domain"]["speed_min"],
                  reg["frozen_profile_domain"]["speed_max"]):
        raise RuntimeError("Registered profile bounds mismatch")
    return checks


def preregistered_sequence_validity(reg: dict, profile: dict) -> dict:
    actuator = profile["ActuatorTrackingProfile"]
    qualification = profile["TrackingQualificationProfile"]
    low, high = actuator["speed_min"]["value"], actuator["speed_max"]["value"]
    material = qualification["material_command_delta"]["value"]
    commands = reg["replacement_case"]["commands"]
    values = [item["command"] for item in commands]
    timestamps = [item["time_ns"] for item in commands]
    first = values[0]
    middle = values[3]
    final = values[-1]
    qualifier = r1.CumulativeTrackingQualifier(profile, load(R52_REGISTRATION)["classifier"])
    result = {
        "all_commands_in_domain": all(low <= value <= high for value in values),
        "all_commands_strictly_interior": all(low < value < high for value in values),
        "strictly_increasing_command_times": all(a < b for a, b in pairwise(timestamps)),
        "initial_anchor_in_domain": low <= first <= high,
        "all_individual_updates_subthreshold": all(abs(b - a) < material for a, b in pairwise(values)),
        "first_net_material": abs(middle - first) >= material,
        "second_net_material": abs(final - middle) >= material,
        "first_profile_observable": qualifier._response_open(timestamps[3], abs(middle - first)) is not None,
        "second_profile_observable": qualifier._response_open(timestamps[-1], abs(final - middle)) is not None,
        "registered_a_b_c": values[0] == reg["replacement_case"]["expected_anchor_sequence"][0]
            and middle == reg["replacement_case"]["expected_anchor_sequence"][1]
            and final == reg["replacement_case"]["expected_anchor_sequence"][2],
    }
    return result


def c9r_source(reg: dict) -> list:
    case = reg["replacement_case"]
    schedule = tuple((item["time_ns"], item["command"]) for item in case["commands"])
    run = run_open_loop(case["initial_actual_speed"], schedule,
                        case["sensor_period_ns"], case["duration_ns"])
    return r1.from_calibration(run["rows"])


def epoch_starts(case: dict) -> list[dict]:
    return [event for event in case["epoch_events"] if event["event"] == "START"]


def c9r_checks(case: dict, reg: dict, profile: dict) -> dict:
    expected = reg["replacement_case"]["expected_anchor_sequence"]
    anchors = case["anchor_events"]
    starts = epoch_starts(case)
    records = case["records"]
    by_time = {row["time_ns"]: row for row in records}
    first_trigger = reg["replacement_case"]["expected_first_trigger_ns"]
    second_trigger = reg["replacement_case"]["expected_second_trigger_ns"]
    progress = [row for row in records if row["state"] == "TRACKING_PROGRESS"]
    low = profile["ActuatorTrackingProfile"]["speed_min"]["value"]
    high = profile["ActuatorTrackingProfile"]["speed_max"]["value"]
    return {
        "all_commands_in_domain": all(low <= row["plc_command"] <= high for row in records),
        "legitimate_initial_anchor": bool(anchors) and anchors[0]["new_anchor"] == expected[0]
            and anchors[0]["anchor_update_reason"] == "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE",
        "stage_1_net_from_A": by_time[first_trigger]["qualified_command_anchor"] == expected[0]
            and abs(by_time[first_trigger]["net_command_demand"] - (expected[1] - expected[0])) < 1e-9,
        "stage_1_first_epoch_exact": len(starts) >= 1 and starts[0]["time_ns"] == first_trigger,
        "no_premature_first_advance": len(anchors) >= 2 and anchors[1]["time_ns"] > first_trigger
            and anchors[1]["anchor_update_reason"] == "QUALIFIED_EPOCH_RESOLVED_TO_STEADY",
        "stage_1_progress_and_resolution": bool(progress) and len(anchors) >= 2
            and anchors[1]["anchor_source_epoch_id"] == starts[0]["epoch_id"],
        "A_to_B": len(anchors) >= 2 and anchors[1]["previous_anchor"] == expected[0]
            and anchors[1]["new_anchor"] == expected[1],
        "stage_2_net_from_B": by_time[second_trigger]["qualified_command_anchor"] == expected[1]
            and abs(by_time[second_trigger]["net_command_demand"] - (expected[2] - expected[1])) < 1e-9,
        "stage_2_not_from_historical_A": abs(by_time[second_trigger]["net_command_demand"]
            - (expected[2] - expected[0])) > 1e-9,
        "stage_2_new_epoch_exact": len(starts) >= 2 and starts[1]["time_ns"] == second_trigger,
        "stage_2_progress_and_resolution": len(anchors) >= 3 and anchors[2]["anchor_source_epoch_id"] == starts[1]["epoch_id"],
        "B_to_C_only_after_resolution": len(anchors) >= 3 and anchors[2]["time_ns"] > second_trigger
            and anchors[2]["previous_anchor"] == expected[1] and anchors[2]["new_anchor"] == expected[2]
            and anchors[2]["anchor_update_reason"] == "QUALIFIED_EPOCH_RESOLVED_TO_STEADY",
        "no_false_confirmed_fault": all(row["state"] != "TRACKING_FAULT_CONFIRMED" for row in records),
    }


def audit_table(case: dict) -> list[dict]:
    updates = {event["time_ns"]: event for event in case["anchor_events"]}
    return [{"time_ns": row["time_ns"], "plc_command": row["plc_command"],
             "qualified_anchor": row["qualified_command_anchor"],
             "net_demand": row["net_command_demand"], "demand_class": row["net_demand_classification"],
             "epoch_id": row["epoch_id"], "watch_id": row["watch_id"],
             "measured_speed": row["measured_speed"], "tracking_state": row["state"],
             "anchor_update": updates.get(row["time_ns"])} for row in case["records"]]


def anchor_table(case: dict) -> list[dict]:
    return [{"anchor": chr(65 + index), "value": event["new_anchor"],
             "established_at_ns": event["time_ns"],
             "source_obligation": event["anchor_source_epoch_id"],
             "reason": event["anchor_update_reason"]}
            for index, event in enumerate(case["anchor_events"])]


def make_figure(case: dict, bounds: tuple[float, float], regression: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = case["records"]
    time = [row["time_ns"] / 1e9 for row in rows]
    fig, axes = plt.subplots(4, 2, figsize=(16, 16))
    panels = axes.flat
    panels[0].step(time, [row["plc_command"] for row in rows], where="post", label="PLC command")
    panels[0].axhline(bounds[0], color="red", ls="--", label="profile min")
    panels[0].axhline(bounds[1], color="red", ls="--", label="profile max")
    panels[0].legend(fontsize=7)
    panels[0].set_title("C9R command trajectory and frozen bounds")
    panels[1].step(time, [row["qualified_command_anchor"] for row in rows], where="post")
    panels[1].set_title("Qualified anchor")
    panels[2].step(time, [row["net_command_demand"] for row in rows], where="post")
    panels[2].set_title("Signed net demand from active anchor")
    panels[3].step(time, [int(row["epoch_id"] is not None) for row in rows], where="post", label="epoch")
    panels[3].step(time, [int(row["watch_id"] is not None) for row in rows], where="post", label="watch")
    panels[3].legend(fontsize=7)
    panels[3].set_title("Epoch and watch")
    panels[4].step(time, [row["measured_speed"] for row in rows], where="post")
    panels[4].set_title("Released measured pump speed")
    panels[5].plot([event["time_ns"] / 1e9 for event in case["anchor_events"]],
                   [event["new_anchor"] for event in case["anchor_events"]], marker="o")
    panels[5].set_title("A → B → C anchor lifecycle")
    panels[6].axis("off")
    panels[6].text(0.03, 0.8, f"Original C9: INVALID (1.0 > profile max {bounds[1]:g})",
                   transform=panels[6].transAxes)
    panels[6].text(0.03, 0.6, "C9R: separate preregistered in-domain fixture", transform=panels[6].transAxes)
    panels[6].set_title("Historical distinction")
    panels[7].axis("off")
    panels[7].text(0.03, 0.8, f"C regression: {sum(regression['c'].values())}/{len(regression['c'])}", transform=panels[7].transAxes)
    panels[7].text(0.03, 0.65, f"S regression: {sum(regression['s'].values())}/{len(regression['s'])}", transform=panels[7].transAxes)
    panels[7].text(0.03, 0.5, f"Invariants: {sum(regression['invariants'].values())}/14", transform=panels[7].transAxes)
    panels[7].set_title("Regression and invariants")
    for panel in panels[:6]:
        panel.grid(alpha=0.2)
        panel.set_xlabel("time (s)")
    fig.suptitle("IN-DOMAIN VALIDATION FIXTURE — NO TRACKING SEMANTIC RETUNING — NO PRODUCTION SAFETY CHANGE\n"
                 "GENERIC NUMERICAL FIXTURE — NOT OEM / NVIDIA / GB300 VALIDATION")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = load(REGISTRATION)
    profile = load(PROFILE)
    sources = integrity(reg, profile)
    sequence_precheck = preregistered_sequence_validity(reg, profile)
    if not all(sequence_precheck.values()):
        raise RuntimeError(f"NO_IN_DOMAIN_TWO_STAGE_ANCHOR_TEST_SEQUENCE_AVAILABLE: {sequence_precheck}")
    classifier = load(R52_REGISTRATION)["classifier"]
    replacement = r1.execute(c9r_source(reg), profile, classifier)
    replacement_checks = c9r_checks(replacement, reg, profile)
    valid_keys = ("C1", "C2", "C3_normal", "C3_stuck", "C4", "C5", "C6", "C7",
                  "C8_normal", "C8_stuck", "C10", "C11", "C12")
    valid_sources = r1.cases(profile)
    c_cases = {key: r1.execute(valid_sources[key], profile, classifier) for key in valid_keys}
    prior = load(R1_EVIDENCE)
    assessment_input = {**c_cases, "C9": prior["c_cases"]["C9"]}
    c_assessment = r1.assess(assessment_input)
    c_assessment.pop("C9")
    c_assessment["C9R_IN_DOMAIN_ANCHOR_ADVANCEMENT"] = all(replacement_checks.values())
    historical_sources = build_cases(profile, load(R52_EVIDENCE), load(R522_EVIDENCE))
    s_cases = {key: r1.execute(value, profile, classifier) for key, value in historical_sources.items()}
    s_assessment = acceptance(s_cases)
    old_prefix = {key: value["prefix_causal"] for key, value in s_cases.items()}
    original_invariants = invariants(s_cases, old_prefix)
    added_invariants = r1.new_invariants(c_cases)
    bounds = (profile["ActuatorTrackingProfile"]["speed_min"]["value"],
              profile["ActuatorTrackingProfile"]["speed_max"]["value"])
    semantic_cases = {**c_cases, "C9R_IN_DOMAIN_ANCHOR_ADVANCEMENT": replacement, **s_cases}
    domain_checks = {key: all(bounds[0] <= row["plc_command"] <= bounds[1]
                              for row in case["records"])
                     for key, case in semantic_cases.items()}
    expected = reg["replacement_case"]["expected_anchor_sequence"]
    anchor_reference = False
    if len(replacement["anchor_events"]) >= 3:
        after_b = [row for row in replacement["records"]
                   if replacement["anchor_events"][1]["time_ns"] < row["time_ns"]
                   < replacement["anchor_events"][2]["time_ns"]]
        anchor_reference = bool(after_b) and all(
            abs(row["net_command_demand"] - (row["plc_command"] - expected[1])) < 1e-9
            for row in after_b
        )
    invariants_all = {
        **original_invariants, **added_invariants,
        "13_all_semantic_evidence_commands_in_profile": all(domain_checks.values()),
        "14_post_advance_net_uses_latest_anchor": anchor_reference,
    }
    prefix = {key: case["prefix_causal"] for key, case in semantic_cases.items()}
    if not domain_checks["C9R_IN_DOMAIN_ANCHOR_ADVANCEMENT"]:
        gate = "REPLACEMENT_C9_FIXTURE_OUT_OF_PROFILE_DOMAIN"
    elif (not all(replacement_checks.values()) or not all(c_assessment.values())
          or not all(s_assessment.values()) or not all(invariants_all.values())
          or not all(prefix.values())):
        gate = "IN_DOMAIN_ANCHOR_ADVANCEMENT_SEMANTICS_FAIL"
    else:
        gate = "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN"
    evidence = {
        "schema": "phase5-r5-2-1r1a-in-domain-anchor-evidence-v1",
        "registration_sha256": sha(REGISTRATION), "source_sha256": reg["source_sha256"],
        "source_hash_checks": sources, "profile_sha256": sha(PROFILE),
        "profile_bounds": {"speed_min": bounds[0], "speed_max": bounds[1]},
        "historical_original_c9": {"status": reg["historical_c9"],
            "source_evidence_sha256": sha(R1_EVIDENCE), "original_gate": prior["status"]},
        "c9r_exact_sequence": reg["replacement_case"],
        "pre_execution_sequence_validity": sequence_precheck,
        "domain_checks": domain_checks,
        "c9r_case": replacement, "c9r_pass_criteria": replacement_checks,
        "c9r_audit_table": audit_table(replacement), "c9r_anchor_table": anchor_table(replacement),
        "c_regression_cases": c_cases, "c_regression": c_assessment,
        "s_regression_cases": s_cases, "s_regression": s_assessment,
        "invariants_1_to_14": invariants_all, "prefix_causality": prefix,
        "semantic_engine_sha256": sha(ROOT / "v0_2/examples/phase5_r5_2_1r1_cumulative_engine.py"),
        "semantic_rules_changed": False, "recalibration_performed": False,
        "new_numeric_tracking_parameters": False,
        "hardware_portability": "Profile-driven offline semantics only; real hardware needs separate calibration.",
        "production_hashes_unchanged": all(sources.values()),
        "production_safety_changed": False, "phase5_r5_3r_started": False,
        "final_feedback_baseline_frozen": False, "phase6_started": False,
        "blocking_issues": [] if gate == "CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN" else
            [key for key, ok in {**replacement_checks, **c_assessment, **s_assessment, **invariants_all, **prefix}.items() if not ok],
        "status": gate,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(replacement, bounds, {"c": c_assessment, "s": s_assessment,
                                      "invariants": invariants_all})
    print(json.dumps({"status": gate, "registration_sha256": sha(REGISTRATION),
                      "evidence_sha256": sha(EVIDENCE), "precheck": sequence_precheck,
                      "c9r": replacement_checks, "c_regression": c_assessment,
                      "s_regression": s_assessment, "invariants": invariants_all,
                      "prefix_causality": all(prefix.values())}, indent=2))


if __name__ == "__main__":
    main()
