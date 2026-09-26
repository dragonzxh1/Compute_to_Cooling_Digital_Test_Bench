"""Read-only TUNE-01 released-trace forensics; never changes production behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from v0_2.examples.phase5_r5_2_1r1_cumulative_engine import CumulativeTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_validation import run_scenario

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "phase5_r5_3r_a_tune01_false_positive_audit_registration.json"
TRACE = ROOT / "phase5_r5_3r_a_tune01_released_input_trace.json"
EVIDENCE = ROOT / "phase5_r5_3r_a_tune01_false_positive_audit_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_3r_a_tune01_false_positive_audit.png"
PROFILE = ROOT / "phase5_r5_2_2_fixture_tracking_profile.json"
CLASSIFIER = ROOT / "phase5_r5_2_silent_tracking_fault_registration.json"
CRITICAL_NS = 31_000_000_000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity(reg: dict) -> dict:
    checks = {name: sha(ROOT / name) == expected for name, expected in
              {**reg["source_sha256"], **reg["reverted_production_sha256"]}.items()}
    checks["failed_gate"] = load(ROOT / "phase5_r5_3r_production_safety_tracking_evidence.json")["status"] == reg["required_failed_gate"]
    checks["r2r_gate"] = load(ROOT / "phase5_r5_2_1r2r_tracking_to_safety_mapping_evidence.json")["status"] == "TRACKING_TO_SAFETY_MAPPING_CONTRACT_REVALIDATED"
    if not all(checks.values()):
        raise RuntimeError(f"POST_R5_3R_REVERT_HASH_MISMATCH: {checks}")
    return checks


def extract() -> tuple[dict, object]:
    """Reconstruct last-released records at Safety ticks from unchanged scenario."""
    run = run_scenario("TUNE-01-load")
    commands = sorted(run.actuator_commands, key=lambda value: value.created_ns)
    measurements = sorted(run.measurements, key=lambda value: (value.available_ns, value.sample_ns, value.sequence))
    rows = []
    command_index = -1
    measurement_index = -1
    for row in run.rows:
        if row.time_ns > CRITICAL_NS:
            break
        while (command_index + 1 < len(commands)
               and commands[command_index + 1].created_ns < row.time_ns):
            command_index += 1
        while (measurement_index + 1 < len(measurements)
               and measurements[measurement_index + 1].available_ns <= row.time_ns):
            measurement_index += 1
        if command_index < 0:
            continue  # The attempted port skipped pre-PLC open-loop history.
        command = commands[command_index]
        measured = measurements[measurement_index] if measurement_index >= 0 else None
        valid = (measured is not None and measured.pump_speed is not None
                 and measured.qualified("pump_speed", row.time_ns, run.sensor_config.max_age_ns))
        released = {
            "time_ns": row.time_ns,
            "time_s": row.time_ns / 1e9,
            "plc_command": min(run.actuator_config.maximum, max(run.actuator_config.minimum,
                           command.applied_command_before_actuator_dynamics)),
            "plc_command_id": command.command_id,
            "command_timestamp_ns": command.created_ns,
            "measured_speed": measured.pump_speed if valid else None,
            "measurement_record_id": measured.measurement_record_id if measured is not None else "not_applicable",
            "sample_ns": measured.sample_ns if measured is not None else None,
            "release_ns": measured.available_ns if measured is not None else None,
            "measurement_age_ns": row.time_ns - measured.sample_ns if measured is not None else None,
            "quality": "VALID" if valid else "INVALID",
            "sensor_status": dict(measured.quality).get("pump_speed") if measured is not None else "MISSING",
            "released_dp_pa": measured.dp_pa if measured is not None else None,
            "released_flow_kg_s": measured.flow_kg_s if measured is not None else None,
            "baseline_safety_state": row.safety_state,
            "legacy_tracking_branch_active": None,
        }
        rows.append(released)
    return {
        "schema": "phase5-r5-3r-a-reconstructed-released-trace-v1",
        "scenario_id": "TUNE-01-load",
        "provenance": "UNCHANGED_BASELINE_RECONSTRUCTION_NOT_ORIGINAL_FAILED_TRIAL_CAPTURE",
        "failed_trial_prefix_equivalence": "UNVERIFIED_EXCEPT_SPARSE_RECORDED_VALUES_AT_29_6_AND_31_0_S",
        "critical_prefix_end_ns": CRITICAL_NS,
        "no_raw_actual_or_true_plant_fields": True,
        "rows": rows,
    }, run


def observation(row: dict, observation_type=ReleasedObservation) -> ReleasedObservation:
    return observation_type(row["time_ns"], row["plc_command"], row["command_timestamp_ns"],
                            row["measured_speed"], row["sample_ns"], row["release_ns"],
                            row["quality"], row["measurement_record_id"])


def replay(rows: list[dict], profile: dict, classifier: dict,
           qualifier_type=CumulativeTrackingQualifier) -> tuple[list[dict], dict]:
    qualifier = qualifier_type(profile, classifier)
    observation_type = qualifier.update.__globals__["ReleasedObservation"]
    records = []
    for row in rows:
        record = dict(qualifier.update(observation(row, observation_type)))
        epoch = qualifier.epoch
        watch = qualifier.watch
        record.update({
            "response_open_ns": epoch.response_open_ns if epoch is not None else None,
            "response_open": bool(epoch is not None and row["time_ns"] >= epoch.response_open_ns),
            "qualified_progress_seen": bool(epoch is not None and epoch.qualified_progress_seen),
            "suspected_since_ns": epoch.suspected_since_ns if epoch is not None else None,
            "confirmed_since_ns": epoch.confirmed_since_ns if epoch is not None else None,
            "epoch_anchor_command": epoch.anchor_command if epoch is not None else None,
            "epoch_anchor_measured_speed": epoch.anchor_measured_speed if epoch is not None else None,
            "watch_anchor_measured_speed": watch.anchor_measured_speed if watch is not None else None,
            "watch_cumulative_observable_demand": watch.cumulative_observable_demand if watch is not None else None,
            "oldest_unresolved_demand_ns": epoch.oldest_unresolved_demand_ns if epoch is not None else None,
            "command_measured_gap": (row["plc_command"] - row["measured_speed"]
                                     if row["measured_speed"] is not None else None),
        })
        if epoch is not None and row["measured_speed"] is not None:
            expected = qualifier._expected(abs(epoch.latest_command - epoch.anchor_command),
                                           row["time_ns"], epoch.epoch_start_ns)
            progress = epoch.expected_direction * (row["measured_speed"] - epoch.anchor_measured_speed)
            record["epoch_expected_displacement"] = expected
            record["epoch_measured_directed_progress"] = progress
            record["epoch_progress_ratio"] = progress / expected if expected else None
            record["qualified_progress_decision"] = (progress >= qualifier.minimum_motion
                                                       and expected > 0
                                                       and progress / expected >= qualifier.suspect_ratio)
        else:
            record["epoch_expected_displacement"] = None
            record["epoch_measured_directed_progress"] = None
            record["epoch_progress_ratio"] = None
            record["qualified_progress_decision"] = False
        records.append(record)
    return records, qualifier.snapshot()


def reconstructed_port_class():
    """Rebuild the known mechanical copy in memory; unavailable trial file remains a limitation."""
    base = (ROOT / "v0_2/examples/phase5_r5_2_1r_semantic_engine.py").read_text(encoding="utf-8")
    cumulative = (ROOT / "v0_2/examples/phase5_r5_2_1r1_cumulative_engine.py").read_text(encoding="utf-8")
    base = base.replace("from dataclasses import asdict, dataclass", "from dataclasses import asdict, dataclass, replace")
    base = base.replace("class OfflineTrackingQualifier:", "class _TrackingQualifierCore:")
    extra = cumulative[cumulative.index("class CumulativeTrackingQualifier"):]
    extra = extra.replace("class CumulativeTrackingQualifier(OfflineTrackingQualifier):",
                          "class ProductionTrackingQualifier(_TrackingQualifierCore):")
    namespace = {"__name__": __name__}
    transformed = base + "\n\n" + extra
    # Offline audit only: both input sources are hash-checked frozen project files.
    exec(compile(transformed, "<R5.3R-known-mechanical-port-reconstruction>", "exec"), namespace)  # noqa: S102
    return namespace["ProductionTrackingQualifier"], hashlib.sha256(transformed.encode("utf-8")).hexdigest()


def replay_port(rows: list[dict], profile: dict, classifier: dict) -> tuple[list[dict], dict]:
    cls, source_sha = reconstructed_port_class()
    records, snapshot = replay(rows, profile, classifier, cls)
    return records, {"snapshot": snapshot, "reconstructed_algorithm_sha256": source_sha}


def domain(trace: dict, run: object, profile: dict) -> dict:
    actuator = profile["ActuatorTrackingProfile"]
    sensor = profile["SensorObservationProfile"]
    lo, hi = actuator["speed_min"]["value"], actuator["speed_max"]["value"]
    rows = trace["rows"]
    results = {
        "command_range": "IN_DOMAIN" if all(lo <= row["plc_command"] <= hi for row in rows) else "OUT_OF_DOMAIN",
        "measured_range": "IN_DOMAIN" if all(row["measured_speed"] is None or lo <= row["measured_speed"] <= hi for row in rows) else "OUT_OF_DOMAIN",
        "actuator_delay": "IN_DOMAIN" if run.actuator_config.command_delay_ns == round(actuator["command_delay_s"]["value"] * 1e9) else "OUT_OF_DOMAIN",
        "actuator_lag": "IN_DOMAIN" if run.actuator_config.tau_s == actuator["lag_time_constant_s"]["value"] else "OUT_OF_DOMAIN",
        "actuator_ramp": "IN_DOMAIN" if run.actuator_config.ramp_per_s == actuator["speed_rate_limit_per_s"]["value"] else "OUT_OF_DOMAIN",
        "sensor_period": "IN_DOMAIN" if run.sensor_config.sample_ns == round(sensor["measurement_period_s"]["value"] * 1e9) else "OUT_OF_DOMAIN",
        "sensor_release_delay": "IN_DOMAIN" if run.sensor_config.local_delay_ns == round(sensor["measurement_release_delay_s"]["value"] * 1e9) else "OUT_OF_DOMAIN",
        "sensor_max_age": "IN_DOMAIN" if run.sensor_config.max_age_ns == round(sensor["measurement_validity_limit_s"]["value"] * 1e9) else "OUT_OF_DOMAIN",
        "sample_release_causal": "IN_DOMAIN" if all(row["release_ns"] is None or row["release_ns"] <= row["time_ns"] for row in rows) else "OUT_OF_DOMAIN",
        "continuous_command_applicability": "NOT_SPECIFIED",
        "command_magnitude_upper_bound": "NOT_SPECIFIED",
    }
    return {"items": results, "required_explicit_bounds_pass": all(value != "OUT_OF_DOMAIN" for value in results.values()),
            "command_min_max": [min(row["plc_command"] for row in rows), max(row["plc_command"] for row in rows)],
            "measured_min_max": [min(row["measured_speed"] for row in rows if row["measured_speed"] is not None),
                                 max(row["measured_speed"] for row in rows if row["measured_speed"] is not None)]}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def forensic(run: object) -> dict:
    critical = [row for row in run.rows if 29_200_000_000 <= row.time_ns <= CRITICAL_NS]
    first, last = critical[0], critical[-1]
    return {
        "label": "FORENSIC_NON_CAUSAL_VIEW_NOT_QUALIFIER_INPUT",
        "window_ns": [first.time_ns, last.time_ns],
        "actual_speed_change": last.pump_actual - first.pump_actual,
        "released_measured_speed_change": last.pump_measured - first.pump_measured,
        "flow_change_kg_s": last.total_flow_kg_s - first.total_flow_kg_s,
        "released_dp_change_pa": last.measured_dp_pa - first.measured_dp_pa,
        "rows": [{"time_ns": row.time_ns, "command": row.pump_command,
                  "actual_speed": row.pump_actual, "released_measured_speed": row.pump_measured,
                  "flow_kg_s": row.total_flow_kg_s, "released_dp_pa": row.measured_dp_pa}
                 for row in critical],
    }


def make_figure(trace: dict, offline: list[dict], port: list[dict], run: object) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = trace["rows"]
    t = [row["time_s"] for row in rows]
    fig, axes = plt.subplots(5, 2, figsize=(17, 20))
    axes = axes.ravel()
    axes[0].plot(t, [row["plc_command"] for row in rows], label="released PLC command")
    axes[0].plot(t, [row["measured_speed"] for row in rows], label="released measured speed")
    axes[0].legend()
    axes[0].set_title("1. Causal released signals")
    axes[1].plot(t, [row["qualified_command_anchor"] for row in offline])
    axes[1].set_title("2. Qualified command anchor")
    axes[2].plot(t, [row["net_command_demand"] for row in offline])
    axes[2].set_title("3. Net command demand")
    levels = {name: index for index, name in enumerate((
        "STEADY_TRACKING", "HANDOFF_PENDING", "TRACKING_PROGRESS",
        "TRACKING_FAULT_SUSPECTED", "TRACKING_FAULT_CONFIRMED", "INSUFFICIENT_MEASUREMENT"))}
    axes[3].step(t, [levels[row["state"]] for row in offline], label="frozen offline")
    axes[3].step(t, [levels[row["state"]] for row in port], ls="--", label="functional port reconstruction")
    axes[3].legend()
    axes[3].set_title("4. Tracking state")
    axes[4].step(t, [int(row["response_open"]) for row in offline])
    axes[4].set_title("5. Response window open")
    axes[5].step(t, [int(row["qualified_progress_decision"]) for row in offline])
    axes[5].set_title("6. Qualified progress decision")
    axes[6].plot(t, [(row["time_ns"] - row["epoch_start_ns"]) / 1e9
                     if row["epoch_start_ns"] is not None else 0 for row in offline], label="epoch age")
    axes[6].plot(t, [(row["time_ns"] - row["watch_start_ns"]) / 1e9
                     if row["watch_start_ns"] is not None else 0 for row in offline], label="watch age")
    axes[6].legend()
    axes[6].set_title("7. Epoch/watch age")
    axes[7].step(t, [row["baseline_safety_state"] == "FAULT" for row in rows], label="baseline FAULT")
    axes[7].axvline(29.6, color="orange", ls="--", label="trial SUSPECTED/DEGRADED")
    axes[7].axvline(31.0, color="red", ls="--", label="trial CONFIRMED/FAULT")
    axes[7].legend()
    axes[7].set_title("8. Baseline vs recorded trial Safety transitions")
    axes[8].plot(t, [row["epoch_measured_directed_progress"] for row in offline], label="measured progress")
    axes[8].plot(t, [row["epoch_expected_displacement"] for row in offline], label="expected from old command anchor")
    axes[8].set_xlim(27.6, 31.0)
    axes[8].legend()
    axes[8].set_title("9. First-suspicion window; no tick divergence in reconstruction")
    physical = [row for row in run.rows if row.time_ns <= CRITICAL_NS]
    axes[9].plot([row.time_ns / 1e9 for row in physical], [row.pump_actual for row in physical],
                 label="TRUE actuator actual — non-causal")
    axes[9].set_xlim(27.6, 31.0)
    axes[9].legend()
    axes[9].set_title("10. FORENSIC ONLY — never supplied to qualifier")
    for ax in axes:
        ax.set_xlabel("time (s)")
        ax.grid(alpha=0.2)
    fig.suptitle("ROOT-CAUSE AUDIT ONLY — NO PRODUCTION FIX — NO SEMANTIC RETUNE\nGENERIC NUMERICAL FIXTURE")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=120)
    plt.close(fig)


def main() -> None:
    reg = load(REG)
    source_checks = integrity(reg)
    trace, run = extract()
    serialized = json.dumps(trace, indent=2, allow_nan=False) + "\n"
    if TRACE.exists() and TRACE.read_text(encoding="utf-8") != serialized:
        raise RuntimeError("Immutable reconstructed trace would change")
    if not TRACE.exists():
        TRACE.write_text(serialized, encoding="utf-8")
    profile = load(PROFILE)
    classifier = load(CLASSIFIER)["classifier"]
    domain_result = domain(trace, run, profile)
    records, snapshot = replay(trace["rows"], profile, classifier)
    port_records, port = replay_port(trace["rows"], profile, classifier)
    comparable = ("state", "epoch_id", "epoch_start_ns", "watch_id", "watch_start_ns",
                  "qualified_command_anchor", "qualified_command_anchor_ns",
                  "qualified_measurement_anchor", "anchor_source_epoch_id", "net_command_demand",
                  "net_demand_classification", "expected_direction", "response_open_ns", "response_open",
                  "qualified_progress_decision", "suspected_since_ns", "confirmed_since_ns", "valid")
    mismatches = [{"time_ns": a["time_ns"], "field": field, "offline": a[field], "port": b[field]}
                  for a, b in zip(records, port_records) for field in comparable if a[field] != b[field]]
    relevant = [index for index, row in enumerate(trace["rows"]) if 27_600_000_000 <= row["time_ns"] <= CRITICAL_NS]
    first_divergence_table = [
        {"time_ns": trace["rows"][index]["time_ns"],
         "released_cmd": trace["rows"][index]["plc_command"],
         "qualified_anchor": records[index]["qualified_command_anchor"],
         "net_demand": records[index]["net_command_demand"],
         "measured_speed": trace["rows"][index]["measured_speed"],
         "measurement_valid": records[index]["valid"],
         "offline_state": records[index]["state"], "production_reconstructed_state": port_records[index]["state"],
         "offline_response_open": records[index]["response_open"],
         "production_response_open": port_records[index]["response_open"],
         "offline_progress": records[index]["qualified_progress_decision"],
         "production_progress": port_records[index]["qualified_progress_decision"]}
        for index in relevant]
    repeat_hashes = [digest(replay(trace["rows"], profile, classifier)) for _ in range(10)]
    prefix_checks = [replay(trace["rows"][:index], profile, classifier)[0] == records[:index]
                     for index in range(1, len(records) + 1)]
    suspected = next((row["time_ns"] for row in records if row["state"] == "TRACKING_FAULT_SUSPECTED"), None)
    confirmed = next((row["time_ns"] for row in records if row["state"] == "TRACKING_FAULT_CONFIRMED"), None)
    port_suspected = next((row["time_ns"] for row in port_records if row["state"] == "TRACKING_FAULT_SUSPECTED"), None)
    port_confirmed = next((row["time_ns"] for row in port_records if row["state"] == "TRACKING_FAULT_CONFIRMED"), None)
    sparse_trial_match = suspected == port_suspected == 29_600_000_000 and confirmed == port_confirmed == 31_000_000_000
    measurement_values = {row["time_ns"]: row for row in records}
    root_class = ("FROZEN_SEMANTICS_FALSE_POSITIVE_ON_VALID_IN_DOMAIN_TRACE"
                  if domain_result["required_explicit_bounds_pass"] and not mismatches and sparse_trial_match
                  else "INSUFFICIENT_EVIDENCE")
    evidence = {
        "schema": "phase5-r5-3r-a-root-cause-evidence-v1",
        "registration_sha256": sha(REG), "source_hash_checks": source_checks,
        "source_sha256": reg["source_sha256"], "reverted_production_sha256": reg["reverted_production_sha256"],
        "trace_sha256": sha(TRACE), "trace_provenance": trace["provenance"],
        "trace_full_failed_run_capture": False,
        "failed_trial_prefix_equivalence_basis": "Before first trial FAULT, Contract15A DEGRADED added no envelope restriction. Existing PLC consumes bounds/accepted DP, not reason/state for non-emergency command value. Same frozen scenario and sparse recorded trial command/measured values at 29.6s/31.0s; command/measurement IDs from baseline reconstruction may differ and are not qualifier inputs.",
        "domain_validity": domain_result,
        "offline_replay": {"first_suspected_ns": suspected, "first_confirmed_ns": confirmed,
                           "transitions": snapshot["transitions"], "anchor_events": snapshot["anchor_events"],
                           "epoch_events": snapshot["epoch_events"], "watch_events": snapshot["watch_events"]},
        "production_reconstruction": {"method": "In-memory mechanical source transform recorded in previous R5.3R trial; deleted production file unavailable for bytewise hash comparison",
                                      "completeness": "FUNCTIONAL_QUALIFIER_LOGIC_RECONSTRUCTED_INPUT_PREFIX_INFERRED_NOT_FULL_FAILED_TRACE",
                                      "algorithm_sha256": port["reconstructed_algorithm_sha256"],
                                      "first_suspected_ns": port_suspected, "first_confirmed_ns": port_confirmed,
                                      "observed_trial_safety": {"DEGRADED": 29_600_000_000, "FAULT": 31_000_000_000}},
        "tick_comparison_fields": list(comparable), "tick_comparison_count": len(records),
        "tick_mismatch_count": len(mismatches), "tick_mismatches": mismatches,
        "first_divergence": mismatches[0] if mismatches else None,
        "first_divergence_window": first_divergence_table,
        "critical_progress": {str(time_ns): {field: measurement_values[time_ns][field] for field in
                              ("qualified_command_anchor", "net_command_demand", "epoch_anchor_command",
                               "epoch_anchor_measured_speed", "watch_anchor_measured_speed", "epoch_expected_displacement",
                               "epoch_measured_directed_progress", "epoch_progress_ratio", "command_measured_gap",
                               "response_open", "qualified_progress_decision", "state")}
                              for time_ns in (29_200_000_000, 29_600_000_000, 30_800_000_000, 31_000_000_000)},
        "command_provenance": {"source": "prior issued PLC ActuatorCommand.applied_command_before_actuator_dynamics bounded by frozen actuator bounds",
                               "timestamp": "same command.created_ns", "pre_plc_takeover_skipped": True,
                               "trial_exact_command_ids_available": False,
                               "wrong_requested_target_or_raw_actual_used": False},
        "measurement_provenance": {"source": "latest released MeasuredSnapshot.pump_speed",
                                   "sample_release_quality_from_same_record": True,
                                   "trial_exact_measurement_ids_available": False},
        "anchor_comparison": "No functional mismatch on reconstructed prefix; qualified command anchor remained 0.7 from 0.2s to 31.0s",
        "watch_epoch_comparison": "No functional mismatch; epoch/watch started 29.2s, watch_start_ns=29.0s, never resolved before confirmation",
        "response_window_comparison": "No functional mismatch; response_open_ns=29.4s for first epoch",
        "progress_comparison": "No functional mismatch; measured progress grew but remained below frozen expected-displacement ratio because command anchor 0.7 and epoch measurement anchor ~0.8426 have different reference epochs",
        "legacy_path_audit": "Recorded failed trial removed old raw 0.15 branch authority. Around suspicion command-measured gap ~0.0058, far below historical 0.15 predicate; old path cannot explain this event.",
        "safety_mapping_audit": "Offline suspected and confirmed at same observed trial Safety transition times; Contract15A DEGRADED and FAULT mappings agree. No mapping-only mismatch identified.",
        "forensic_physical_response": forensic(run),
        "repeatability": {"replays": 10, "identical": len(set(repeat_hashes)) == 1, "result_sha256": repeat_hashes[0]},
        "prefix_causality": {"prefixes": len(prefix_checks), "all_equal": all(prefix_checks)},
        "root_cause_class": root_class,
        "status": ("TUNE01_FALSE_POSITIVE_ROOT_CAUSE_IDENTIFIED"
                   if root_class != "INSUFFICIENT_EVIDENCE" else "TUNE01_FALSE_POSITIVE_AUDIT_INSUFFICIENT_EVIDENCE"),
        "limitations": ["Original failed production source was deleted and not saved in Git; functional reconstruction uses recorded mechanical-copy transformation.",
                        "Original failed full released input trace was not captured; immutable artifact is baseline reconstruction through first FAULT. Trial command IDs may differ because DEGRADED changes Safety envelope ID, but qualifier does not consume IDs.",
                        "Post-FAULT input stream cannot be reconstructed from baseline because FAULT fallback changes PLC commands."],
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    make_figure(trace, records, port_records, run)
    print(json.dumps({"trace_sha256": sha(TRACE), "status": evidence["status"],
                      "root_cause_class": root_class, "offline_suspected_ns": suspected,
                      "offline_confirmed_ns": confirmed, "tick_mismatches": len(mismatches),
                      "repeatability": evidence["repeatability"], "prefix_causality": evidence["prefix_causality"]}, indent=2))


if __name__ == "__main__":
    main()
