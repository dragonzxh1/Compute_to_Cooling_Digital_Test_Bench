"""Read-only R5.1 cold handoff audit; production control modules are untouched."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from math import exp
from pathlib import Path
from unittest.mock import patch

from v0_2.control.directional_outer import DirectionalOuterFeedback
from v0_2.examples import phase5_1r2_qualification as q
from v0_2.examples import phase5_r4_outer_tuning as r4
from v0_2.examples import phase5_r5_directional_pi as r5
from v0_2.plant import controlled_loop
from v0_2.plant.controlled_loop import Disturbance

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_1_safety_handoff_audit_registration.json"
EVIDENCE = ROOT / "phase5_r5_1_safety_handoff_audit_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_1_cold_start_safety_handoff.png"
REPORT = ROOT / "PHASE5_R5_1_COLD_START_SAFETY_HANDOFF_AUDIT_REPORT.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def integrity(reg: dict) -> dict:
    checks = {
        "r5_registration": sha(r5.REGISTRATION) == reg["source_r5_registration_sha256"],
        "r5_evidence": sha(r5.EVIDENCE) == reg["source_r5_evidence_sha256"],
        "r5_candidate": sha(r5.CANDIDATE_BASELINE) == reg["source_r5_candidate_baseline_sha256"],
        "safety_source": sha(ROOT / "v0_2/safety/supervisor.py") == reg["frozen_source_sha256"]["safety_supervisor"],
        "actuator_source": sha(ROOT / "v0_2/actuators/pump.py") == reg["frozen_source_sha256"]["pump_actuator"],
    }
    baseline = json.loads(r5.CANDIDATE_BASELINE.read_text(encoding="utf-8"))
    checks["controller"] = all(baseline[name] == reg["frozen_controller"][name] for name in ("ki_hot", "ki_cold", "kd", "blend_halfwidth_k", "single_integral_state")) and baseline["outer_kp"] == reg["frozen_controller"]["kp"]
    if not all(checks.values()):
        raise RuntimeError(f"R5.1 frozen-source integrity failure: {checks}")
    return checks


def run_case(label: str, state, speed: float, historical: dict, *, stuck: bool = False, duration_ns: int = 5_000_000_000):
    candidate = {"kp": 4500.0, "ki_hot": 110.0, "ki_cold": 130.0, "kd": 0.0}
    plant, controls = q.physical_fixture(branch_count=2, power_each=historical["workload_w_per_device"])
    plant = replace(plant, initial_state=state)
    controls = q._controls(controls, speed)
    configs = list(q.fixture_configs(r4._gains(historical["inner"]), {"kp": candidate["kp"], "ki": candidate["ki_hot"], "kd": 0.0}, 200_000_000))
    configs[3] = replace(configs[3], target_k=historical["target_k"])
    configs[5] = replace(configs[5], control_target_k=historical["target_k"])
    holder = {}

    def factory(config):
        controller = DirectionalOuterFeedback(config, candidate["ki_hot"], candidate["ki_cold"])
        holder["controller"] = controller
        return controller

    disturbances = (Disturbance(0, pump_stuck=True),) if stuck else ()
    with patch.object(controlled_loop, "OuterFeedback", factory):
        run = controlled_loop.run_feedback(plant, controls, duration_ns, *configs, disturbances=disturbances)
    return run, holder["controller"].ticks


def expected_trajectory(run, prepared_speed: float) -> list[dict]:
    """Offline audit sink, fed only after a completed run; never feeds control."""
    cfg = run.actuator_config
    commands = sorted(run.actuator_commands, key=lambda c: c.created_ns)
    due = sorted((c.created_ns + cfg.command_delay_ns, c.applied_command_before_actuator_dynamics, c.command_id) for c in commands)
    current, target, previous = prepared_speed, prepared_speed, 0
    cursor = 0
    result = []

    def segment(value, goal, seconds):
        exact = goal + (value - goal) * exp(-seconds / cfg.tau_s)
        delta = min(cfg.ramp_per_s * seconds, max(-cfg.ramp_per_s * seconds, exact - value))
        return min(cfg.maximum, max(cfg.minimum, value + delta))

    for row in run.rows:
        while cursor < len(due) and due[cursor][0] <= row.time_ns:
            at, new_target, _ = due[cursor]
            if at > previous:
                current = segment(current, target, (at - previous) / 1e9)
                previous = at
            target = new_target
            cursor += 1
        if row.time_ns > previous:
            current = segment(current, target, (row.time_ns - previous) / 1e9)
            previous = row.time_ns
        result.append({"timestamp_ns": row.time_ns, "expected_pump_speed": current, "target_after_delay": target, "actual_pump_speed": row.pump_actual, "absolute_difference": abs(current - row.pump_actual)})
    return result


def trace(run, ticks, prepared_speed: float, stuck: bool) -> dict:
    commands = {x.command_id: x for x in run.actuator_commands}
    cycles = {x.plc_cycle_id: x for x in run.plc_cycles}
    envelopes = {x.envelope_id: x for x in run.safety_envelopes}
    targets = {x.accepted_target_id: x for x in run.accepted_targets}
    intents = {x.intent_id: x for x in run.fb_intents}
    measurements = {x.measurement_record_id: x for x in run.measurements}
    states = {x.actuator_state_id: x for x in run.actuator_states}
    ticks_by_time = {x["time_ns"]: x for x in ticks}
    expected = expected_trajectory(run, prepared_speed)
    records = []
    for row, reference in zip(run.rows, expected):
        if row.time_ns > 5_000_000_000:
            break
        command = commands.get(row.actuator_command_id)
        cycle = cycles.get(row.plc_cycle_id)
        envelope = envelopes[row.safety_envelope_id]
        target = targets[row.accepted_target_id]
        measurement = measurements.get(row.measurement_record_id)
        tick = ticks_by_time.get(row.time_ns)
        links = {
            "fb_intent_to_target": target.fb_intent_id in intents and target.fb_intent_id == row.fb_intent_id,
            "target_to_envelope": envelope.accepted_target_id == target.accepted_target_id,
            "envelope_to_cycle": cycle is not None and cycle.safety_envelope_id in envelopes and cycle.accepted_target_id in targets,
            "cycle_to_command": command is not None and command.plc_cycle_id == cycle.plc_cycle_id and command.safety_envelope_id == cycle.safety_envelope_id and command.accepted_target_id == cycle.accepted_target_id,
            "command_to_state": row.actuator_state_id == "actuator-state:initial" or (row.actuator_state_id in states and (states[row.actuator_state_id].actuator_command_id == "not_applicable" or states[row.actuator_state_id].actuator_command_id in commands)),
            "state_to_measurement": measurement is not None and (measurement.actuator_state_id == "actuator-state:initial" or measurement.actuator_state_id in states),
            "measurement_to_hydraulic": measurement is not None and measurement.hydraulic_solution_id == row.hydraulic_solution_id,
        }
        # A released measurement may legitimately predate the current command/state.
        records.append({
            "timestamp_ns": row.time_ns, "released_measured_temperature_k": row.measured_device_k,
            "temperature_error_k": tick["error_k"] if tick else None,
            "ki_eff": tick["ki_eff"] if tick else None,
            "outer_p_pa": 4500.0 * tick["error_k"] if tick else None,
            "outer_i_pa": tick["integral_after"] if tick else None,
            "outer_requested_dp_pa": row.requested_dp_pa, "accepted_dp_pa": row.accepted_dp_pa,
            "safety_envelope": asdict(envelope), "safety_state": row.safety_state,
            "safety_reason_codes": list(envelope.reason_codes), "plc_cycle_id": row.plc_cycle_id,
            "plc_actuator_command": asdict(command) if command else None,
            "actuator_command_timestamp_ns": command.created_ns if command else None,
            "commanded_pump_speed": row.pump_command, "actual_pump_speed": row.pump_actual,
            "measured_pump_echo": row.pump_measured,
            "tracking_error": row.pump_command - row.pump_actual,
            "measured_tracking_error": row.pump_command - row.pump_measured if row.pump_measured is not None else None,
            "actuator_delay_state": "PENDING" if command and row.time_ns < command.created_ns + run.actuator_config.command_delay_ns else "ELAPSED",
            "actuator_lag_state": reference["target_after_delay"] - reference["expected_pump_speed"],
            "rate_limit_state": abs(row.pump_actual - prepared_speed) <= run.actuator_config.ramp_per_s * row.time_ns / 1e9 + 1e-10,
            "saturation_state": bool(command and abs(command.applied_command_before_actuator_dynamics - row.pump_command) > 1e-12),
            "hydraulic_solution_id": row.hydraulic_solution_id, "flow_kg_s": row.total_flow_kg_s,
            "dp_pa": row.measured_dp_pa,
            "measurement_sample_timestamp_ns": measurement.sample_ns if measurement else None,
            "measurement_release_timestamp_ns": measurement.available_ns if measurement else None,
            "measurement_age_ns": row.time_ns - measurement.sample_ns if measurement else None,
            "measurement_quality": list(measurement.quality) if measurement else None,
            "measurement_pump_fault": measurement.pump_fault if measurement else None,
            "provenance": {name: getattr(row, name) for name in ("fb_intent_id", "accepted_target_id", "safety_envelope_id", "plc_cycle_id", "actuator_command_id", "actuator_state_id", "measurement_record_id", "hydraulic_solution_id")},
            "provenance_links": links, "expected_response": reference,
        })
    first = run.actuator_commands[0]
    first_material = next((c for c in run.actuator_commands if abs(c.applied_command_before_actuator_dynamics - prepared_speed) > 1e-6), None)
    early_rows = [r for r in run.rows if r.time_ns <= 5_000_000_000]
    first_actual = next((r.time_ns for r in early_rows if abs(r.pump_actual - prepared_speed) > 1e-12), None)
    first_measured = next((r.time_ns for r in early_rows if r.pump_measured is not None and abs(r.pump_measured - prepared_speed) > 1e-12), None)
    initial_error = abs(first.applied_command_before_actuator_dynamics - prepared_speed)
    first_decrease = next((r.time_ns for r in early_rows if r.time_ns >= first.created_ns + run.actuator_config.command_delay_ns and abs(r.pump_command - r.pump_actual) < initial_error - 1e-9), None)
    measured_first_decrease = next((r.time_ns for r in early_rows if r.time_ns >= first.created_ns + run.actuator_config.command_delay_ns and r.pump_measured is not None and abs(r.pump_command - r.pump_measured) < initial_error - 0.001), None)
    violations = [r for r in records if not stuck and r["expected_response"]["absolute_difference"] > 1e-9]
    intervals = []
    for r in records:
        if r["measured_pump_echo"] is None:
            label = "INSUFFICIENT_MEASUREMENT"
        elif not stuck and r["expected_response"]["absolute_difference"] > 1e-9:
            label = "TRACKING_ANOMALY"
        elif r["timestamp_ns"] < first.created_ns + run.actuator_config.command_delay_ns:
            label = "EXPECTED_PENDING" if not stuck else "INSUFFICIENT_MEASUREMENT"
        elif stuck and r["timestamp_ns"] > first.created_ns + run.actuator_config.command_delay_ns:
            label = "TRACKING_ANOMALY"
        else:
            label = "EXPECTED_TRACKING"
        intervals.append({"timestamp_ns": r["timestamp_ns"], "classification": label})
    return {
        "case": "COLD_STUCK" if stuck else "COLD_NOMINAL_HANDOFF" if prepared_speed == 0.9 else "WARM_NOMINAL_HANDOFF",
        "prepared_speed": prepared_speed, "first_plc_command": first.applied_command_before_actuator_dynamics,
        "first_plc_command_id": first.command_id, "first_command_timestamp_ns": first.created_ns,
        "command_delta": first.applied_command_before_actuator_dynamics - prepared_speed,
        "first_material_command_timestamp_ns": first_material.created_ns if first_material else None,
        "first_possible_response_ns": first_material.created_ns + run.actuator_config.command_delay_ns if first_material else None,
        "first_actual_response_ns": first_actual, "first_measured_response_ns": first_measured,
        "initial_tracking_error_fraction": initial_error, "initial_tracking_error_sign": "negative" if first.applied_command_before_actuator_dynamics < prepared_speed else "positive",
        "first_tracking_error_decrease_ns": first_decrease,
        "first_measured_tracking_error_decrease_ns": measured_first_decrease,
        "peak_tracking_error_fraction": max(abs(x["tracking_error"]) for x in records),
        "safety_events": [list(x) for x in run.events],
        "safety_final_state": run.rows[-1].safety_state,
        "full_run_duration_ns": run.rows[-1].time_ns,
        "expected_response_max_difference": max(x["expected_response"]["absolute_difference"] for x in records),
        "first_expected_response_violation_ns": violations[0]["timestamp_ns"] if violations else None,
        "provenance_links_pass": all(all(x["provenance_links"].values()) for x in records if x["timestamp_ns"] >= 0),
        "conservation": {"max_mass_residual_kg_s": max(x.ledger.max_mass_volume_residual_kg_s for x in run.steps), "max_energy_residual_j": max(abs(x.ledger.full_loop_residual_j) for x in run.steps)},
        "diagnostic_intervals": intervals, "events": records,
    }


def classify(cold: dict, stuck: dict, warm: dict) -> tuple[str, dict]:
    historical = [200_000_000, "DEGRADED", ["ACTUATOR_TRACKING_PENDING"]]
    reproduced = historical in [[t, state, list(reasons)] for t, state, reasons in cold["safety_events"]]
    measured_nominal = [x for x in cold["events"] if x["measured_pump_echo"] is not None]
    measured_stuck = [x for x in stuck["events"] if x["measured_pump_echo"] is not None]
    nominal_drop = measured_nominal[0]["measured_pump_echo"] - measured_nominal[-1]["measured_pump_echo"]
    stuck_drop = measured_stuck[0]["measured_pump_echo"] - measured_stuck[-1]["measured_pump_echo"]
    separation = nominal_drop > 0.001 and abs(stuck_drop) < 1e-9 and cold["first_measured_tracking_error_decrease_ns"] is not None and stuck["first_measured_tracking_error_decrease_ns"] is None
    measured = {"status": "MEASURED_ONLY_SEPARATION_PASS" if separation else "MEASURED_ONLY_SEPARATION_FAIL", "nominal_measured_speed_drop": nominal_drop, "stuck_measured_speed_drop": stuck_drop, "nominal_first_measured_error_decrease_ns": cold["first_measured_tracking_error_decrease_ns"], "stuck_first_measured_error_decrease_ns": stuck["first_measured_tracking_error_decrease_ns"], "nominal_last_safety_state": cold["safety_final_state"], "stuck_last_safety_state": stuck["safety_final_state"], "stuck_measured_fault": any(x["measurement_pump_fault"] is True for x in measured_stuck)}
    if not reproduced:
        gate = "HISTORICAL_STARTUP_EVENT_NOT_REPRODUCED"
    elif cold["first_expected_response_violation_ns"] is not None:
        gate = "GENUINE_NOMINAL_TRACKING_ANOMALY"
    elif not separation:
        gate = "INSUFFICIENT_MEASURED_INFORMATION_FOR_SAFE_HANDOFF_QUALIFICATION"
    else:
        gate = "NORMAL_HANDOFF_MISCLASSIFIED_AS_DEGRADED"
    return gate, measured


def repeat_signature(result: dict) -> bytes:
    """Hash the pre-registered first-5-s diagnostic window, not full-run ledgers."""
    return canonical({"events": result["events"], "diagnostic_intervals": result["diagnostic_intervals"], "safety_events_first_5s": [x for x in result["safety_events"] if x[0] <= 5_000_000_000], "first_command": result["first_plc_command"], "first_actual_response_ns": result["first_actual_response_ns"], "first_measured_response_ns": result["first_measured_response_ns"]})


def false_positive_checks(cold: dict, policy) -> dict:
    events = cold["events"]
    moving = next((x for x in events if x["timestamp_ns"] == cold["first_actual_response_ns"]), None)
    degraded = [x for x in events if x["safety_state"] == "DEGRADED"]
    return {
        "plc_ownership_valid": cold["provenance_links_pass"] and all(x["plc_actuator_command"]["producer_module"] == "PLC" for x in events),
        "material_command_change": abs(cold["command_delta"]) > 0.15,
        "inside_nominal_delay_lag_ramp_envelope": cold["first_expected_response_violation_ns"] is None and all(x["rate_limit_state"] for x in events),
        "response_direction_correct": moving is not None and moving["actual_pump_speed"] < cold["prepared_speed"],
        "tracking_error_decreases_when_possible": cold["first_tracking_error_decrease_ns"] is not None and cold["first_tracking_error_decrease_ns"] >= cold["first_possible_response_ns"],
        "measured_echo_causal": moving is not None and cold["first_measured_response_ns"] >= cold["first_actual_response_ns"] and abs(moving["measured_pump_echo"] - moving["actual_pump_speed"]) <= 1e-9,
        "no_saturation_or_fault": all(not x["saturation_state"] and x["measurement_pump_fault"] is False for x in events),
        "no_real_thermal_flow_pressure_violation": all(x["released_measured_temperature_k"] < policy.derate_k and x["flow_kg_s"] >= policy.minimum_flow_kg_s and x["dp_pa"] < policy.maximum_dp_pa for x in events),
        "only_degraded_reason_is_tracking_pending": bool(degraded) and all(x["safety_reason_codes"] == ["ACTUATOR_TRACKING_PENDING"] for x in degraded),
    }


def figure(cold: dict, stuck: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    c, s = cold["events"], stuck["events"]
    times = [x["timestamp_ns"] / 1e9 for x in c]
    fig, axes = plt.subplots(6, 1, figsize=(15, 17), sharex=True)
    for field, label in (("commanded_pump_speed", "PLC command"), ("actual_pump_speed", "Actual pump"), ("measured_pump_echo", "Measured echo")):
        axes[0].plot(times, [x[field] for x in c], label=label)
    axes[0].legend(); axes[0].set_ylabel("speed fraction")
    axes[1].plot(times, [abs(x["measured_tracking_error"]) if x["measured_tracking_error"] is not None else None for x in c], label="measured error")
    axes[1].axhline(0.15, color="red", ls="--", label="Safety tolerance")
    axes[1].legend(); axes[1].set_ylabel("fraction")
    for field in ("outer_requested_dp_pa", "accepted_dp_pa"):
        axes[2].plot(times, [x[field] for x in c], label=field)
    axes[2].legend(); axes[2].set_ylabel("Pa")
    axes[3].plot(times, [x["flow_kg_s"] for x in c], label="released flow")
    ax_dp = axes[3].twinx(); ax_dp.plot(times, [x["dp_pa"] for x in c], color="purple", label="released DP")
    axes[3].legend(loc="upper left"); ax_dp.legend(loc="upper right"); axes[3].set_ylabel("kg/s"); ax_dp.set_ylabel("Pa")
    states = {"NORMAL": 0, "FF_DISABLED": 1, "DEGRADED": 2, "FAULT": 3}
    axes[4].step(times, [states.get(x["safety_state"], 4) for x in c], where="post")
    axes[4].set_yticks(list(states.values()), list(states)); axes[4].set_ylabel("Safety state")
    for t, state, reasons in cold["safety_events"]:
        if t <= 5_000_000_000:
            axes[4].annotate(" / ".join(reasons) or state, (t / 1e9, states.get(state, 4)), xytext=(5, 8), textcoords="offset points", fontsize=7, rotation=15)
    axes[5].plot(times, [abs(x["measured_tracking_error"]) if x["measured_tracking_error"] is not None else None for x in c], label="nominal")
    axes[5].plot([x["timestamp_ns"] / 1e9 for x in s], [abs(x["measured_tracking_error"]) if x["measured_tracking_error"] is not None else None for x in s], label="stuck")
    axes[5].legend(); axes[5].set_ylabel("measured error"); axes[5].set_xlabel("time after takeover (s)")
    for axis in axes:
        axis.axvline(cold["first_command_timestamp_ns"] / 1e9, color="black", ls=":", alpha=0.6)
        axis.axvline(cold["first_possible_response_ns"] / 1e9, color="orange", ls=":", alpha=0.6)
        for t, color in ((cold["first_actual_response_ns"], "green"), (cold["first_measured_response_ns"], "blue")):
            if t is not None:
                axis.axvline(t / 1e9, color=color, ls=":", alpha=0.5)
        for t, state, _ in cold["safety_events"]:
            if state in ("DEGRADED", "FF_DISABLED", "NORMAL"):
                axis.axvline(t / 1e9, color={"DEGRADED": "red", "FF_DISABLED": "gray", "NORMAL": "green"}[state], ls="--", alpha=0.35)
    fig.suptitle("R5.1 cold handoff: command | possible response | actual | measured | Safety transitions\nDiagnostic only; not independent validation", y=0.995)
    fig.legend(handles=[Line2D([0], [0], color="black", ls=":", label="command issued"), Line2D([0], [0], color="orange", ls=":", label="response physically allowed"), Line2D([0], [0], color="green", ls=":", label="first actual movement"), Line2D([0], [0], color="blue", ls=":", label="first measured movement"), Line2D([0], [0], color="red", ls="--", label="DEGRADED entry"), Line2D([0], [0], color="gray", ls="--", label="FF_DISABLED recovery"), Line2D([0], [0], color="green", ls="--", label="NORMAL entry")], loc="upper center", bbox_to_anchor=(0.5, 0.96), ncol=4, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    checks = integrity(reg)
    historical = json.loads(r4.REGISTRATION.read_text(encoding="utf-8"))
    preps, states = r4._prepare(historical)
    runs = {}
    for name, prep_case, stuck in (("warm", "WARM_CAPTURE", False), ("cold", "COLD_CAPTURE", False), ("stuck", "COLD_CAPTURE", True)):
        run, ticks = run_case(prep_case, states[prep_case], preps[prep_case]["speed_fraction"], historical, stuck=stuck, duration_ns=reg["observation"]["full_run_ns"])
        runs[name] = trace(run, ticks, preps[prep_case]["speed_fraction"], stuck)
        print(f"{name} diagnostic complete", flush=True)
    gate, measured = classify(runs["cold"], runs["stuck"], runs["warm"])
    repeatability = {}
    for name, prep_case, stuck in (("cold", "COLD_CAPTURE", False), ("stuck", "COLD_CAPTURE", True)):
        hashes = [hashlib.sha256(repeat_signature(runs[name])).hexdigest()]
        for _ in range(9):
            run, ticks = run_case(prep_case, states[prep_case], preps[prep_case]["speed_fraction"], historical, stuck=stuck)
            hashes.append(hashlib.sha256(repeat_signature(trace(run, ticks, preps[prep_case]["speed_fraction"], stuck))).hexdigest())
        repeatability[name] = {"runs": 10, "all_identical": len(set(hashes)) == 1, "diagnostic_result_hash_sha256": hashes[0], "all_hashes": hashes}
        print(f"{name} repeatability 10/10 complete", flush=True)
    policy = q.fixture_configs()[5]
    fp_checks = false_positive_checks(runs["cold"], policy)
    if gate == "NORMAL_HANDOFF_MISCLASSIFIED_AS_DEGRADED" and not all(fp_checks.values()):
        raise RuntimeError(f"R5.1 false-positive gate requires all nine checks: {fp_checks}")
    evidence = {"schema": "phase5-r5-1-safety-handoff-audit-evidence-v1", "registration_sha256": sha(REGISTRATION), "source_r5_registration_sha256": sha(r5.REGISTRATION), "source_r5_evidence_sha256": sha(r5.EVIDENCE), "candidate": reg["frozen_controller"], "integrity": checks, "preparation": preps, "safety_predicate": {"expression": "abs(commanded_speed - released measured pump_speed) > 0.15", "pending_duration_ns": 2_000_000_000, "evaluation_before_new_PLC_command": True, "recovery_samples": 5, "dwell_ns": 2_000_000_000}, "false_positive_checks": fp_checks, "cases": runs, "measured_only_separation": measured, "repeatability": repeatability, "excessive_tracking_fixture": "EXCESSIVE_TRACKING_FAULT_FIXTURE_NOT_AVAILABLE", "ownership_causality_status": "PASS" if all(x["provenance_links_pass"] for x in runs.values()) else "FAIL", "conservation_status": "PASS" if all(x["conservation"]["max_mass_residual_kg_s"] <= 1e-6 and x["conservation"]["max_energy_residual_j"] <= 1e-5 for x in runs.values()) else "FAIL", "root_cause_classification": gate, "status": gate, "production_behavior_changed": False, "final_feedback_baseline_frozen": False, "phase6_authorized": False}
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    figure(runs["cold"], runs["stuck"])
    print(json.dumps({"gate": gate, "registration_sha256": evidence["registration_sha256"], "evidence_sha256": sha(EVIDENCE), "measured_only": measured, "repeatability": {name: x["all_identical"] for name, x in repeatability.items()}, "ownership": evidence["ownership_causality_status"], "conservation": evidence["conservation_status"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
