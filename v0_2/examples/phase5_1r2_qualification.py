"""Execute the pre-registered final R2 nominal feedback qualification."""

from __future__ import annotations

import gc
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict, replace
from itertools import pairwise
from math import fsum
from pathlib import Path

from v0_2.examples.phase5_1r_qualification import _controls, _window_mean_max_device
from v0_2.examples.phase5_r1_ownership_audit import collect_audit
from v0_2.examples.phase5_r2_1_robustness import _control_core_sha, _plant_sha
from v0_2.examples.phase5_validation import fixture_configs
from v0_2.plant.authority import traces_for_run
from v0_2.plant.controlled_loop import run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import run

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_1r2_qualification_registration.json"
RESULT = ROOT / "phase5_1r2_nominal_result.json"
BASELINE = ROOT / "phase5_r2_feedback_baseline.json"
FINALIZATION = ROOT / "phase5_r2_2_finalization_evidence.json"
OWNERSHIP_AUDIT = ROOT / "docs/results/phase5_r1_ownership_audit.json"
EXPECTED_REGISTRATION_SHA = "a7466babe2cd32a016db138dc83ccd1c9b9367ca6a3fd43af0f67490cab33c5b"
EXPECTED_BASELINE_SHA = "891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1"
EXPECTED_FINALIZATION_SHA = "f33eb500ee224fbbd4a80b88affcaa77902ea08c33714c10ae4493c76d576208"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=lambda item: item.item(),
    ).encode()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _finite(value) -> bool:
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def _integrity(registration: dict, baseline: dict) -> dict:
    r1 = _load(ROOT / "phase5_r1_feedback_baseline.json")
    payload = dict(baseline)
    payload.pop("final_baseline_sha256")
    payload.pop("final_baseline_sha256_scope")
    hash_fields = {key for key in baseline if key.endswith("sha256")}
    accounted_hash_fields = {
        "tuning_registration_sha256", "code_sha256", "supersedes_original_baseline_sha256",
        "original_baseline_file_sha256", "original_control_core_sha256",
        "revision_registration_sha256", "selection_evidence_sha256",
        "supersedes_r1_baseline_sha256", "source_r1_control_core_sha256",
        "r2_target_registration_sha256",
        "r1_baseline_sha256", "r2_selection_evidence_sha256",
        "r2_1_robustness_registration_sha256", "r2_1_robustness_evidence_sha256",
        "final_baseline_sha256",
    }
    checks = {
        "registration_sha256": _sha(REGISTRATION) == EXPECTED_REGISTRATION_SHA,
        "baseline_sha256": _sha(BASELINE) == EXPECTED_BASELINE_SHA,
        "finalization_evidence_sha256": _sha(FINALIZATION) == EXPECTED_FINALIZATION_SHA,
        "control_core_sha256": _control_core_sha() == baseline["code_sha256"],
        "plant_sha256": _plant_sha() == "d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254",
        "target_frozen": baseline["target_k"] == registration["target_k"],
        "inner_frozen": baseline["inner_candidate_id"] == registration["inner"]["id"]
        and baseline["inner_gains"] == {k: registration["inner"][k] for k in ("kp", "ki", "kd")},
        "outer_frozen": baseline["outer_candidate_id"] == registration["outer"]["id"]
        and baseline["outer_gains"] == {k: registration["outer"][k] for k in ("kp", "ki", "kd")},
        "finalization_points_to_baseline": _load(FINALIZATION)["final_baseline"]["file_sha256"]
        == EXPECTED_BASELINE_SHA,
        "tuning_registration_reference": _sha(ROOT / "phase5_tuning_registration.json") == baseline["tuning_registration_sha256"],
        "r1_revision_registration_reference": _sha(ROOT / "phase5_r1_revision_registration.json") == baseline["revision_registration_sha256"],
        "original_baseline_reference": _sha(ROOT / "phase5_feedback_baseline.json") == baseline["original_baseline_file_sha256"] == baseline["supersedes_original_baseline_sha256"],
        "original_control_core_provenance": baseline["original_control_core_sha256"] == r1["original_control_core_sha256"],
        "r1_baseline_reference": _sha(ROOT / "phase5_r1_feedback_baseline.json") == baseline["r1_baseline_sha256"] == baseline["supersedes_r1_baseline_sha256"],
        "r1_control_core_reference": _control_core_sha() == baseline["source_r1_control_core_sha256"],
        "r2_target_registration_reference": _sha(ROOT / "phase5_r2_target_registration.json") == baseline["r2_target_registration_sha256"],
        "r2_selection_reference": _sha(ROOT / "phase5_r2_selection_evidence.json") == baseline["r2_selection_evidence_sha256"] == baseline["selection_evidence_sha256"],
        "r2_1_registration_reference": _sha(ROOT / "phase5_r2_1_selection_robustness_registration.json") == baseline["r2_1_robustness_registration_sha256"],
        "r2_1_evidence_reference": _sha(ROOT / "phase5_r2_1_selection_robustness_evidence.json") == baseline["r2_1_robustness_evidence_sha256"],
        "baseline_payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest() == baseline["final_baseline_sha256"],
        "all_baseline_hash_fields_accounted": hash_fields == accounted_hash_fields,
    }
    if not all(checks.values()):
        raise RuntimeError(f"PHASE5_1R2_BASELINE_INTEGRITY_FAILURE: {checks!r}")
    return {
        "status": "PASS",
        "checks": checks,
        "registration_sha256": _sha(REGISTRATION),
        "baseline_sha256": _sha(BASELINE),
        "finalization_evidence_sha256": _sha(FINALIZATION),
        "control_core_sha256": _control_core_sha(),
        "plant_sha256": _plant_sha(),
    }


def _state_payload(state) -> dict:
    return {
        "time_ns": state.time_ns,
        "solids": [
            {
                "node_id": item.node_id,
                "temperature_k": item.temperature_k,
                "energy_j": item.energy_j,
            }
            for item in state.solids
        ],
        "volumes": [
            {
                "volume_id": item.volume_id,
                "specific_enthalpy_j_kg": item.specific_enthalpy_j_kg,
                "temperature_k": item.temperature_k,
                "pressure_pa": item.pressure_pa,
            }
            for item in state.volumes
        ],
    }


def _prepare(label: str, speed: float, registration: dict) -> tuple[dict, object]:
    plant, controls = physical_fixture(branch_count=2, power_each=registration["workload_w_per_device"])
    prep = registration["preparation"]
    prepared = run(plant, _controls(controls, speed), prep["duration_ns"], prep["physics_dt_ns"])
    rows = traces_for_run(prepared)
    endpoint = _window_mean_max_device(rows, prep["endpoint_window_start_ns"])
    expected = prep[f"historical_{label.lower().split('_')[0]}_endpoint_k"]
    reproduction_error = abs(endpoint - expected)
    normalized = replace(prepared.final_state, time_ns=0)
    payload = _state_payload(normalized)
    record = {
        "case": label,
        "speed_fraction": speed,
        "duration_s": prep["duration_ns"] / 1e9,
        "qualified_window_mean_max_device_k": endpoint,
        "historical_endpoint_k": expected,
        "reproduction_error_k": reproduction_error,
        "reproduction_tolerance_k": prep["endpoint_reproduction_tolerance_k"],
        "reproduction_status": "PASS" if reproduction_error <= prep["endpoint_reproduction_tolerance_k"] else "FAIL",
        "normalized_initial_state_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
        "normalized_initial_state": payload,
        "controller_prehistory": "none",
        "integrator_warm_start": False,
    }
    if record["reproduction_status"] != "PASS":
        raise RuntimeError(f"PHASE5_1R2_PREPARATION_REPRODUCTION_FAILURE: {record!r}")
    return record, normalized


def _settling_time(rows, target: float, band: float, dwell_s: float):
    measured = [row for row in rows if row.measured_device_k is not None]
    end_s = measured[-1].time_ns / 1e9
    for index, row in enumerate(measured):
        at_s = row.time_ns / 1e9
        if end_s - at_s < dwell_s:
            continue
        if all(abs(later.measured_device_k - target) <= band for later in measured[index:]):
            return at_s
    return None


def _metrics(controlled, registration: dict, label: str, initial_speed: float) -> dict:
    rows = controlled.rows
    intervals = tuple(pairwise(rows))
    measured = [row for row in rows if row.measured_device_k is not None]
    target = registration["target_k"]
    final_start = registration["final_window_start_ns"]
    final = [row for row in measured if row.time_ns >= final_start]
    sat = registration["saturation"]
    tol = sat["bound_tolerance_fraction"]

    def at_bound(value):
        return abs(value - sat["minimum_speed_fraction"]) <= tol or abs(
            value - sat["maximum_speed_fraction"]
        ) <= tol

    def duration(predicate):
        return fsum((b.time_ns - a.time_ns) / 1e9 for a, b in intervals if predicate(a))

    safety_durations: dict[str, float] = defaultdict(float)
    for a, b in intervals:
        safety_durations[a.safety_state] += (b.time_ns - a.time_ns) / 1e9
    direction_rows = [row for row in rows if row.time_ns <= registration["control_direction"]["evaluation_window_ns"]]
    if label == "WARM_CAPTURE":
        direction_pass = max(row.accepted_dp_pa for row in direction_rows) > rows[0].accepted_dp_pa + registration["control_direction"]["minimum_dp_change_pa"] and max(row.pump_actual for row in direction_rows) > initial_speed + registration["control_direction"]["minimum_actual_speed_change_fraction"]
    else:
        direction_pass = min(row.accepted_dp_pa for row in direction_rows) < rows[0].accepted_dp_pa - registration["control_direction"]["minimum_dp_change_pa"] and min(row.pump_actual for row in direction_rows) < initial_speed - registration["control_direction"]["minimum_actual_speed_change_fraction"]
    settling = _settling_time(
        rows, target, registration["settling"]["band_k"], registration["settling"]["continuous_dwell_ns"] / 1e9
    )
    lineage_pass = all(
        command.producer_module == "PLC"
        and command.plc_cycle_id
        and command.accepted_target_id
        and command.safety_envelope_id
        for command in controlled.actuator_commands
    )
    result = {
        "initial_measured_device_k": measured[0].measured_device_k,
        "peak_device_k": max(row.measured_device_k for row in measured),
        "minimum_device_k": min(row.measured_device_k for row in measured),
        "final_window_mean_measured_k": fsum(row.measured_device_k for row in final) / len(final),
        "final_window_minimum_measured_k": min(row.measured_device_k for row in final),
        "final_window_maximum_measured_k": max(row.measured_device_k for row in final),
        "final_measured_device_k": measured[-1].measured_device_k,
        "temperature_iae_k_s": fsum(abs(a.measured_device_k - target) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.measured_device_k is not None),
        "temperature_ise_k2_s": fsum((a.measured_device_k - target) ** 2 * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.measured_device_k is not None),
        "settling_time_s": settling,
        "dp_tracking_iae_pa_s": fsum(abs(a.accepted_dp_pa - a.measured_dp_pa) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.measured_dp_pa is not None),
        "pump_electrical_j": fsum(step.ledger.pump_electrical_j for step in controlled.steps),
        "control_total_variation": fsum(abs(b.pump_command - a.pump_command) for a, b in intervals),
        "actuator_tracking_iae_fraction_s": fsum(abs(a.pump_command - a.pump_measured) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.pump_measured is not None),
        "command_saturation_duration_s": duration(lambda row: at_bound(row.pump_command)),
        "actual_saturation_duration_s": duration(lambda row: at_bound(row.pump_actual)),
        "command_minimum_bound_time_s": duration(lambda row: abs(row.pump_command - sat["minimum_speed_fraction"]) <= tol),
        "command_maximum_bound_time_s": duration(lambda row: abs(row.pump_command - sat["maximum_speed_fraction"]) <= tol),
        "actual_minimum_bound_time_s": duration(lambda row: abs(row.pump_actual - sat["minimum_speed_fraction"]) <= tol),
        "actual_maximum_bound_time_s": duration(lambda row: abs(row.pump_actual - sat["maximum_speed_fraction"]) <= tol),
        "final_window_command_bound_time_s": duration(lambda row: row.time_ns >= final_start and at_bound(row.pump_command)),
        "final_window_actual_bound_time_s": duration(lambda row: row.time_ns >= final_start and at_bound(row.pump_actual)),
        "final_pump_command": rows[-1].pump_command,
        "final_pump_actual": rows[-1].pump_actual,
        "final_pump_measured": rows[-1].pump_measured,
        "safety_state_duration_s": dict(safety_durations),
        "safety_states": sorted(safety_durations),
        "safety_event_count": len(controlled.events),
        "safety_events": [list(event) for event in controlled.events],
        "max_mass_residual_kg_s": max(step.ledger.max_mass_volume_residual_kg_s for step in controlled.steps),
        "max_energy_residual_j": max(abs(step.ledger.full_loop_residual_j) for step in controlled.steps),
        "ownership_lineage_pass": lineage_pass,
        "control_direction_pass": direction_pass,
    }
    result["settling_pass"] = settling is not None
    result["final_window_pass"] = result["final_window_minimum_measured_k"] >= target - registration["settling"]["band_k"] and result["final_window_maximum_measured_k"] <= target + registration["settling"]["band_k"]
    result["final_saturation_pass"] = result["final_window_command_bound_time_s"] == 0 and result["final_window_actual_bound_time_s"] == 0 and sat["minimum_speed_fraction"] < result["final_pump_actual"] < sat["maximum_speed_fraction"]
    result["safety_pass"] = set(result["safety_states"]) <= {"FF_DISABLED", "NORMAL"} and not any(state != "NORMAL" and time > 2.000000001 for state, time in safety_durations.items())
    result["conservation_pass"] = result["max_mass_residual_kg_s"] < registration["conservation_limits"]["max_mass_residual_kg_s"] and result["max_energy_residual_j"] < registration["conservation_limits"]["max_absolute_step_energy_residual_j"]
    result["status"] = "PASS" if _finite(result) and all(result[key] for key in ("settling_pass", "final_window_pass", "final_saturation_pass", "safety_pass", "conservation_pass", "control_direction_pass", "ownership_lineage_pass")) else "FAIL"
    return result


def _run_case(label: str, dt_ns: int, initial_state, initial_speed: float, registration: dict, baseline: dict):
    plant, controls = physical_fixture(branch_count=2, power_each=registration["workload_w_per_device"])
    plant = replace(plant, initial_state=initial_state)
    controls = _controls(controls, initial_speed)
    configs = list(fixture_configs(baseline["inner_gains"], baseline["outer_gains"], dt_ns))
    configs[3] = replace(configs[3], target_k=registration["target_k"])
    configs[5] = replace(configs[5], control_target_k=registration["target_k"])
    controlled = run_feedback(plant, controls, registration["qualification_duration_ns"], *configs)
    return controlled, _metrics(controlled, registration, label, initial_speed)


def _convergence(records: list[dict], registration: dict) -> dict:
    tolerances = registration["continuous_metric_tolerances"]
    by_case = {}
    for label in registration["qualification_cases"]:
        case = {record["physics_dt_ns"]: record["metrics"] for record in records if record["case"] == label}
        dts = registration["physics_dt_ns"]
        adjacent_settling = [
            abs(case[a]["settling_time_s"] - case[b]["settling_time_s"])
            if case[a]["settling_time_s"] is not None and case[b]["settling_time_s"] is not None
            else None
            for a, b in pairwise(dts)
        ]
        medium, fine = case[dts[1]], case[dts[2]]
        differences = {
            "peak_device_k": abs(medium["peak_device_k"] - fine["peak_device_k"]),
            "minimum_device_k": abs(medium["minimum_device_k"] - fine["minimum_device_k"]),
            "final_window_mean_measured_k": abs(medium["final_window_mean_measured_k"] - fine["final_window_mean_measured_k"]),
            "temperature_iae_k_s": abs(medium["temperature_iae_k_s"] - fine["temperature_iae_k_s"]),
            "dp_tracking_iae_pa_s": abs(medium["dp_tracking_iae_pa_s"] - fine["dp_tracking_iae_pa_s"]),
            "pump_electrical_relative": abs(medium["pump_electrical_j"] - fine["pump_electrical_j"]) / max(abs(fine["pump_electrical_j"]), 1e-12),
            "control_total_variation": abs(medium["control_total_variation"] - fine["control_total_variation"]),
            "actuator_tracking_iae_fraction_s": abs(medium["actuator_tracking_iae_fraction_s"] - fine["actuator_tracking_iae_fraction_s"]),
            "saturation_duration_s": abs(medium["command_saturation_duration_s"] - fine["command_saturation_duration_s"]),
        }
        status = all(item["metrics"]["status"] == "PASS" for item in records if item["case"] == label) and all(value is not None and value <= registration["settling"]["adjacent_mesh_settling_time_tolerance_s"] for value in adjacent_settling) and all(differences[key] <= tolerances[key] for key in differences)
        by_case[label] = {"status": "PASS" if status else "FAIL", "adjacent_settling_time_differences_s": adjacent_settling, "fine_pair_differences": differences, "tolerances": tolerances}
    return {"status": "PASS" if all(item["status"] == "PASS" for item in by_case.values()) else "FAIL", "cases": by_case}


def _trace(controlled) -> list[dict]:
    flows = {step.next_state.time_ns: step.coldplate_uses[0] for step in controlled.steps}
    output = []
    for row in controlled.rows:
        use = flows.get(row.time_ns)
        output.append({
            "time_s": row.time_ns / 1e9,
            "measured_device_k": row.measured_device_k,
            "requested_dp_pa": row.requested_dp_pa,
            "accepted_dp_pa": row.accepted_dp_pa,
            "measured_dp_pa": row.measured_dp_pa,
            "pump_command": row.pump_command,
            "pump_actual": row.pump_actual,
            "pump_measured": row.pump_measured,
            "total_flow_kg_s": row.total_flow_kg_s,
            "branch_flow_kg_s": use.local_mass_flow_kg_s if use else None,
            "coldplate_rth_k_w": use.endpoint_resistance_k_w if use else None,
            "safety_state": row.safety_state,
        })
    return output


def _classifications(records: list[dict], convergence: dict, ownership: dict) -> list[str]:
    failures = []
    for label, code in (("WARM_CAPTURE", "A_WARM_SIDE_CANNOT_SETTLE"), ("COLD_CAPTURE", "B_COLD_SIDE_CANNOT_SETTLE")):
        if any(record["metrics"]["status"] != "PASS" for record in records if record["case"] == label):
            failures.append(code)
    if any(not record["metrics"]["final_saturation_pass"] for record in records):
        failures.append("C_CAPACITY_BOUND_REGULATION")
    if any(not record["metrics"]["safety_pass"] for record in records):
        failures.append("E_SAFETY_RESTRICTION_REQUIRED")
    if convergence["status"] != "PASS":
        failures.append("F_NUMERICAL_CONVERGENCE_FAILURE")
    if ownership["status"] != "PASS" or any(not record["metrics"]["ownership_lineage_pass"] for record in records):
        failures.append("G_OWNERSHIP_OR_PROVENANCE_REGRESSION")
    return failures


def main() -> None:
    registration = _load(REGISTRATION)
    baseline = _load(BASELINE)
    integrity = _integrity(registration, baseline)
    preparations = {}
    states = {}
    for label, speed in (("WARM_CAPTURE", registration["preparation"]["warm_speed_fraction"]), ("COLD_CAPTURE", registration["preparation"]["cold_speed_fraction"])):
        preparations[label], states[label] = _prepare(label, speed, registration)

    records = []
    trace_data = {}
    for label in registration["qualification_cases"]:
        speed = preparations[label]["speed_fraction"]
        for dt_ns in registration["physics_dt_ns"]:
            controlled, metrics = _run_case(label, dt_ns, states[label], speed, registration, baseline)
            records.append({"case": label, "physics_dt_ns": dt_ns, "metrics": metrics})
            if dt_ns == 200_000_000:
                trace_data[label] = _trace(controlled)
    convergence = _convergence(records, registration)
    ownership = collect_audit()
    ownership["frozen_r1_audit_sha256"] = _sha(OWNERSHIP_AUDIT)

    hashes, live_memory = [], []
    for _ in range(registration["repeatability"]["runs"]):
        repeated, metrics = _run_case("WARM_CAPTURE", 200_000_000, states["WARM_CAPTURE"], preparations["WARM_CAPTURE"]["speed_fraction"], registration, baseline)
        hashes.append(hashlib.sha256(_canonical({"rows": [asdict(row) for row in repeated.rows], "metrics": metrics})).hexdigest())
        del repeated
        gc.collect()
        live_memory.append(sum(sys.getsizeof(item) for item in gc.get_objects()))
        print(f"repeatability run {len(hashes)}/{registration['repeatability']['runs']}", flush=True)
    stability = {
        "runs": len(hashes),
        "identical_hashes": len(set(hashes)) == 1,
        "result_sha256": hashes[0],
        "retained_memory_span_bytes": max(live_memory) - min(live_memory),
        "retained_memory_measurement": "post-GC shallow size of all GC-tracked live objects",
        "bounded_retained_memory": max(live_memory) - min(live_memory) < registration["repeatability"]["retained_memory_span_limit_bytes"],
    }
    stability["status"] = "PASS" if stability["identical_hashes"] and stability["bounded_retained_memory"] else "FAIL"
    classifications = _classifications(records, convergence, ownership)
    if stability["status"] != "PASS":
        classifications.append("REPEATED_STABILITY_FAILURE")
    status = "PASS_FINAL_FROZEN_FEEDBACK_NOMINAL_REGULATION_QUALIFIED" if not classifications else "BLOCKED_FINAL_FROZEN_FEEDBACK_NOMINAL_REGULATION_NOT_QUALIFIED"
    result = {
        "schema": "phase5-1r2-final-frozen-feedback-nominal-qualification-v1",
        "status": status,
        "integrity": integrity,
        "baseline": {"target_k": registration["target_k"], "inner": registration["inner"], "outer": registration["outer"]},
        "preparation": preparations,
        "run_matrix": records,
        "convergence": convergence,
        "ownership": ownership,
        "conservation": {"status": "PASS" if all(record["metrics"]["conservation_pass"] for record in records) else "FAIL", "max_mass_residual_kg_s": max(record["metrics"]["max_mass_residual_kg_s"] for record in records), "max_energy_residual_j": max(record["metrics"]["max_energy_residual_j"] for record in records)},
        "stability": stability,
        "failure_classifications": classifications,
        "retuning_performed": False,
        "phase6_authorized": False,
        "figure_traces": trace_data,
    }
    RESULT.write_text(
        json.dumps(
            result,
            indent=2,
            allow_nan=False,
            default=lambda item: item.item(),
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "result_sha256": _sha(RESULT), "classifications": classifications, "convergence": convergence["status"], "stability": stability["status"], "runs": len(records)}, indent=2))


if __name__ == "__main__":
    main()
