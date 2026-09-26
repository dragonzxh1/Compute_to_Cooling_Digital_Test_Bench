"""Test-only open-loop observability calibration; never feeds production Safety."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from itertools import pairwise
from math import exp
from pathlib import Path
from statistics import fmean, pstdev

from v0_2.actuators.pump import PumpActuator, PumpActuatorConfig
from v0_2.control.inner_loop import ActuatorCommand
from v0_2.measurement.local_sensor import LocalMeasurement, SensorConfig
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.loop import step
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import SolverStatus

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_2_2_tracking_calibration_registration.json"
EVIDENCE = ROOT / "phase5_r5_2_2_tracking_calibration_evidence.json"
PROFILE = ROOT / "phase5_r5_2_2_fixture_tracking_profile.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_2_tracking_observability.png"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def source_integrity(reg: dict) -> dict:
    sources = {
        "r5": "phase5_r5_directional_pi_evidence.json",
        "r5_1": "phase5_r5_1_safety_handoff_audit_evidence.json",
        "r5_2": "phase5_r5_2_silent_tracking_fault_evidence.json",
        "r5_2_1_registration": "phase5_r5_2_1_continuous_tracking_semantics_registration.json",
        "r5_2_1_spec": "phase5_r5_2_1_continuous_tracking_semantics_spec.json",
        "r5_2_1_evidence": "phase5_r5_2_1_continuous_tracking_semantics_evidence.json",
    }
    production = {
        "safety": "v0_2/safety/supervisor.py",
        "directional_outer": "v0_2/control/directional_outer.py",
        "outer_feedback": "v0_2/control/outer_feedback.py",
        "inner_loop": "v0_2/control/inner_loop.py",
        "pid": "v0_2/control/pid.py",
        "actuator": "v0_2/actuators/pump.py",
        "sensor": "v0_2/measurement/local_sensor.py",
        "plant": "v0_2/plant/controlled_loop.py",
    }
    checks = {
        **{name: sha(ROOT / path) == reg["source_evidence_sha256"][name] for name, path in sources.items()},
        **{name: sha(ROOT / path) == reg["production_sha256"][name] for name, path in production.items()},
    }
    if not all(checks.values()):
        raise RuntimeError(f"Frozen source hash mismatch: {checks}")
    return checks


def _typed_command(now_ns: int, value: float, number: int) -> ActuatorCommand:
    """Test-harness PLC provenance only; not the production PLC or a Safety output."""
    cycle = f"calibration-plc-cycle:{now_ns}:{number}"
    return ActuatorCommand(
        f"calibration-command:{now_ns}:{number}", now_ns, "PLC", cycle,
        "calibration-target", "calibration-envelope", value, value,
        "TEST_ONLY_OPEN_LOOP", "CALIBRATION", (cycle,),
    )


def run_open_loop(
    initial: float,
    commands: tuple[tuple[int, float], ...],
    dt_ns: int,
    duration_ns: int,
    *,
    stuck_at_ns: int | None = None,
    sensor_loss: tuple[int, int] | None = None,
) -> dict:
    """Physical fixture advances with nominal actuator/sensor classes, no controller."""
    plant, controls = physical_fixture(branch_count=2, power_each=120)
    state = plant.initial_state
    actuator = PumpActuator(PumpActuatorConfig(0.3, 0.9, 1.0, 0.2, 200_000_000), initial)
    sensor = LocalMeasurement(SensorConfig(200_000_000, 0))
    command_map = {time: value for time, value in commands}
    now, sequence = 0, 0
    rows = []
    mass_max = energy_max = 0.0
    while now <= duration_ns:
        if sensor_loss is not None:
            sensor.failed = {"pump_speed"} if sensor_loss[0] <= now < sensor_loss[1] else set()
        if stuck_at_ns is not None and now >= stuck_at_ns:
            actuator.fault_stuck = True
        if now % sensor.config.sample_ns == 0:
            sensor.sample(now, plant, state, controls, actuator)
        measured = sensor.release(now)
        if now in command_map:
            sequence += 1
            actuator.command(_typed_command(now, command_map[now], sequence), now)
        if now % sensor.config.sample_ns == 0:
            rows.append({
                "time_ns": now,
                "command": actuator.commanded,
                "command_timestamp_ns": actuator.last_command.created_ns if actuator.last_command else None,
                "measured_speed": measured.pump_speed if measured else None,
                "tracking_error": abs(actuator.commanded - measured.pump_speed) if measured and measured.pump_speed is not None else None,
                "sample_ns": measured.sample_ns if measured else None,
                "release_ns": measured.available_ns if measured else None,
                "measurement_age_ns": now - measured.sample_ns if measured else None,
                "quality": dict(measured.quality).get("pump_speed") if measured else "MISSING",
                "flow_kg_s": measured.flow_kg_s if measured else None,
                "dp_pa": measured.dp_pa if measured else None,
                "measurement_record_id": measured.measurement_record_id if measured else None,
            })
        if now == duration_ns:
            break
        deadlines = [duration_ns, now + dt_ns, ((now // sensor.config.sample_ns) + 1) * sensor.config.sample_ns]
        deadlines.extend(t for t in command_map if t > now)
        deadlines.extend(t for t, _, _ in actuator.pending if t > now)
        if stuck_at_ns is not None and stuck_at_ns > now:
            deadlines.append(stuck_at_ns)
        if sensor_loss is not None:
            deadlines.extend(t for t in sensor_loss if t > now)
        end = min(deadlines)
        controls_at_speed = replace(controls, speed_actual=p("pump.speed_actual", actuator.actual, "fraction"))
        result = step(plant, state, controls_at_speed, end - now)
        if result.solver_status != SolverStatus.CONVERGED:
            raise RuntimeError(f"Calibration physical solver failure at {now}: {result.diagnostics}")
        mass_max = max(mass_max, result.ledger.max_mass_volume_residual_kg_s)
        energy_max = max(energy_max, abs(result.ledger.full_loop_residual_j))
        state = result.next_state
        actuator.advance(now, end)
        now = end
    return {"rows": rows, "audit_actual": [asdict(x) for x in actuator.state_history], "conservation": {"max_mass_residual_kg_s": mass_max, "max_energy_residual_j": energy_max}}


def static_summary(run: dict, stable_from_ns: int) -> dict:
    rows = [x for x in run["rows"] if x["time_ns"] >= stable_from_ns and x["quality"] == "VALID"]
    speeds = [x["measured_speed"] for x in rows]
    return {
        "mean": fmean(speeds), "minimum": min(speeds), "maximum": max(speeds),
        "peak_to_peak": max(speeds) - min(speeds), "population_std": pstdev(speeds),
        "max_sample_delta": max((abs(b - a) for a, b in pairwise(speeds)), default=0.0),
        "valid_sample_count": len(rows), "first_release_ns": rows[0]["release_ns"],
        "last_release_ns": rows[-1]["release_ns"],
        "speed_trace_sha256": hashlib.sha256(canonical(speeds)).hexdigest(),
    }


def observations(run: dict) -> list[dict]:
    """Exact whitelist passed to the measured-only evaluator; no truth or label."""
    return [{key: row[key] for key in (
        "time_ns", "command", "command_timestamp_ns", "measured_speed", "sample_ns",
        "release_ns", "quality", "measurement_record_id",
    )} for row in run["rows"]]


def qualified_progress(source: list[dict], anchor_ns: int, anchor_speed: float, direction: int, threshold: float, max_age_ns: int) -> list[dict]:
    result = []
    for row in source:
        valid = (
            row["measured_speed"] is not None and row["quality"] == "VALID"
            and row["sample_ns"] is not None and row["release_ns"] is not None
            and row["release_ns"] <= row["time_ns"]
            and 0 <= row["time_ns"] - row["sample_ns"] <= max_age_ns
        )
        displacement = direction * (row["measured_speed"] - anchor_speed) if valid else None
        result.append({"time_ns": row["time_ns"], "valid": valid, "directed_displacement": displacement,
                       "qualified": bool(valid and row["time_ns"] >= anchor_ns and displacement >= threshold)})
    return result


def first_qualified(decisions: list[dict], after_ns: int) -> int | None:
    return next((x["time_ns"] for x in decisions if x["time_ns"] >= after_ns and x["qualified"]), None)


def expected_displacement(step_magnitude: float, elapsed_s: float, cfg: dict) -> float:
    active = max(0.0, elapsed_s - cfg["command_delay_ns"] / 1e9)
    return min(cfg["ramp_per_s"] * active, step_magnitude * (1 - exp(-active / cfg["tau_s"])))


def response_open_ns(command_ns: int, magnitude: float, threshold: float, reg: dict) -> int | None:
    cfg = reg["fixture_actuator"]
    sensor = reg["fixture_sensor"]
    for sample_ns in range(command_ns, command_ns + reg["experiment_set"]["step_duration_ns"] + 1, sensor["sample_ns"]):
        released = sample_ns + sensor["local_delay_ns"]
        if expected_displacement(magnitude, (sample_ns - command_ns) / 1e9, cfg) >= threshold:
            return released
    return None


def _case_summary(run: dict, anchor_ns: int, anchor_speed: float, direction: int, threshold: float, reg: dict) -> dict:
    source = observations(run)
    decisions = qualified_progress(source, anchor_ns, anchor_speed, direction, threshold, reg["fixture_sensor"]["max_age_ns"])
    prefix_causal = all(
        qualified_progress(source[:index], anchor_ns, anchor_speed, direction, threshold, reg["fixture_sensor"]["max_age_ns"])
        == decisions[:index]
        for index in range(1, len(source) + 1)
    )
    actual_first = next((x["created_ns"] for x in run["audit_actual"] if x["created_ns"] >= anchor_ns and direction * (x["actual_speed"] - anchor_speed) > 1e-12), None)
    return {"first_qualified_ns": first_qualified(decisions, anchor_ns), "first_audit_actual_movement_ns": actual_first,
            "decisions": decisions, "prefix_causal": prefix_causal, "conservation": run["conservation"],
            "released_trace": run["rows"]}


def _repeat_signature(run: dict) -> str:
    return hashlib.sha256(canonical({"rows": run["rows"], "conservation": run["conservation"]})).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def parameter(value, unit: str, source_type: str, source_ref: str, method: str, valid_range: str) -> dict:
    return {
        "value": value, "unit": unit, "source_type": source_type, "source_ref": source_ref,
        "method": method, "valid_range": valid_range,
        "calibration_status": "NUMERICAL_TEST_FIXTURE/ENGINEERING_ASSUMPTION/UNVALIDATED/NOT_OEM/NOT_GB300/NOT_HARDWARE_CERTIFICATION",
    }


def make_figure(evidence: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 2, figsize=(17, 18))
    panels = axes.flat
    static = evidence["static"]
    for speed in (0.3, 0.5, 0.7, 0.9):
        item = static[f"{speed:.1f}@200000000"]
        panels[0].scatter([speed], [item["summary"]["peak_to_peak"]], label=f"{speed:.1f}")
    panels[0].set_title("1. Stationary measured-speed peak-to-peak")
    panels[0].set_xlabel("fixed command fraction")
    panels[0].set_ylabel("variation fraction")
    for direction, label in ((1, "UP +0.2"), (-1, "DOWN -0.2")):
        case = evidence["step_cases"][f"200000000:{direction}:0.2"]
        rows = case["released_trace"]
        panels[1].plot([x["time_ns"] / 1e9 for x in rows], [x["measured_speed"] for x in rows], label=label)
    panels[1].set_title("2. Open-loop positive / negative measured step")
    panels[1].set_xlabel("time (s)")
    panels[1].set_ylabel("released measured speed")
    for direction, label in ((1, "UP"), (-1, "DOWN")):
        cases = [evidence["step_cases"][f"200000000:{direction}:{m}"] for m in (0.02, 0.1, 0.2, 0.3)]
        panels[2].plot([x["magnitude"] for x in cases], [x["first_qualified_ns"] / 1e9 if x["first_qualified_ns"] is not None else float("nan") for x in cases], marker="o", label=label)
    panels[2].set_title("3. Step size versus first qualified progress")
    panels[2].set_xlabel("command step fraction")
    panels[2].set_ylabel("time (s)")
    case = evidence["step_cases"]["200000000:1:0.2"]
    panels[3].bar(["command", "delay", "first released / qualified"], [0, 0.2, case["first_qualified_ns"] / 1e9])
    panels[3].set_title("4. Response-opening decomposition; fixture only")
    panels[3].set_ylabel("time from command (s)")
    for name, label in (("NORMAL", "normal"), ("SILENT_STUCK", "silent stuck")):
        rows = evidence["moving_command"][name]["released_trace"]
        panels[4].plot([x["time_ns"] / 1e9 for x in rows], [x["measured_speed"] for x in rows], label=label)
    panels[4].set_title("5. Moving command: nominal versus silent stuck")
    panels[4].set_xlabel("time (s)")
    panels[4].set_ylabel("measured speed")
    rows = evidence["post_startup_stuck"]["released_trace"]
    panels[5].plot([x["time_ns"] / 1e9 for x in rows], [x["measured_speed"] for x in rows], label="measured")
    panels[5].plot([x["time_ns"] / 1e9 for x in rows], [x["command"] for x in rows], ls="--", label="command")
    panels[5].axvline(evidence["post_startup_stuck"]["anchor_ns"] / 1e9, color="red", ls=":")
    panels[5].set_title("6. Normal tracking, then test-only silent stuck")
    panels[5].set_xlabel("time (s)")
    panels[5].set_ylabel("speed fraction")
    for name, item in evidence["reversals"].items():
        rows = item["released_trace"]
        panels[6].plot([x["time_ns"] / 1e9 for x in rows], [x["measured_speed"] for x in rows], label=name)
    panels[6].axvline(1.0, color="black", ls=":")
    panels[6].set_title("7. Material reversal before settlement")
    panels[6].set_xlabel("time (s)")
    panels[6].set_ylabel("measured speed")
    rows = evidence["sensor_loss_recovery"]["released_trace"]
    panels[7].plot([x["time_ns"] / 1e9 for x in rows], [x["measured_speed"] if x["measured_speed"] is not None else float("nan") for x in rows], marker="o", label="valid speed")
    panels[7].axvspan(0.4, 1.2, color="orange", alpha=0.2, label="MISSING")
    panels[7].set_title("8. Pump-speed measurement loss / recovery")
    panels[7].set_xlabel("time (s)")
    panels[7].set_ylabel("released measured speed")
    for panel in panels:
        panel.grid(alpha=0.2)
        handles, _ = panel.get_legend_handles_labels()
        if handles:
            panel.legend(fontsize=8)
    fig.suptitle("GENERIC NUMERICAL FIXTURE CALIBRATION — NOT OEM / NVIDIA / GB300 HARDWARE CALIBRATION", y=0.998)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    checks = source_integrity(reg)
    meshes = reg["experiment_set"]["physics_dt_ns"]
    static = {}
    static_runs = {}
    for speed in reg["experiment_set"]["static_commands"]:
        for dt in meshes:
            key = f"{speed:.1f}@{dt}"
            hashes, results = [], []
            for _ in range(reg["experiment_set"]["static_repeats"]):
                run = run_open_loop(speed, ((0, speed),), dt, reg["experiment_set"]["static_duration_ns"])
                hashes.append(_repeat_signature(run))
                results.append(static_summary(run, reg["experiment_set"]["static_stable_window_start_ns"]))
            static[key] = {"command": speed, "dt_ns": dt, "summary": results[0], "runs": len(hashes),
                           "repeat_hash_sha256": hashes[0], "all_identical": len(set(hashes)) == 1,
                           "conservation": run["conservation"]}
            static_runs[key] = run
    stationary_floor = max(x["summary"]["peak_to_peak"] for x in static.values())
    mesh_floor = max(
        abs(a["measured_speed"] - b["measured_speed"])
        for speed in reg["experiment_set"]["static_commands"]
        for a, b in zip(static_runs[f"{speed:.1f}@{meshes[0]}"]["rows"], static_runs[f"{speed:.1f}@{meshes[-1]}"]["rows"])
    )
    observation_floor = max(stationary_floor, mesh_floor)
    threshold = max(0.01, 2 * observation_floor)
    steps = {}
    for dt in meshes:
        for direction in (1, -1):
            for magnitude in reg["experiment_set"]["step_magnitudes"]:
                initial = reg["experiment_set"]["step_initial_speed"]
                target = initial + direction * magnitude
                run = run_open_loop(initial, ((0, target),), dt, reg["experiment_set"]["step_duration_ns"])
                result = _case_summary(run, 0, initial, direction, threshold, reg)
                result.update({"initial": initial, "target": target, "magnitude": magnitude, "direction": "UP" if direction > 0 else "DOWN",
                               "dt_ns": dt, "first_physically_possible_response_ns": reg["fixture_actuator"]["command_delay_ns"],
                               "response_open_ns": response_open_ns(0, magnitude, threshold, reg),
                               "first_inside_historical_0_15_error_ns": next((x["time_ns"] for x in run["rows"] if x["tracking_error"] is not None and x["tracking_error"] <= 0.15), None),
                               "observable": result["first_qualified_ns"] is not None})
                steps[f"{dt}:{direction}:{magnitude}"] = result
    reversals = {}
    for direction, targets in ((1, (0.7, 0.3)), (-1, (0.3, 0.7))):
        hashes = []
        for _ in range(reg["experiment_set"]["reversal_repeats"]):
            run = run_open_loop(0.5, tuple(zip(reg["experiment_set"]["reversal_command_times_ns"], targets)),
                                meshes[0], reg["experiment_set"]["step_duration_ns"])
            hashes.append(_repeat_signature(run))
        reversal_ns = reg["experiment_set"]["reversal_command_times_ns"][1]
        anchor = next(x["measured_speed"] for x in run["rows"] if x["time_ns"] == reversal_ns)
        result = _case_summary(run, reversal_ns, anchor, -direction, threshold, reg)
        result.update({"direction": "UP_THEN_DOWN" if direction > 0 else "DOWN_THEN_UP", "reversal_ns": reversal_ns,
                       "anchor_measured_speed": anchor, "all_repeat_hashes_identical": len(set(hashes)) == 1})
        reversals[result["direction"]] = result
    moving = {}
    for name, stuck_at in (("NORMAL", None), ("SILENT_STUCK", 0)):
        run = run_open_loop(0.5, tuple(zip(reg["experiment_set"]["moving_command_times_ns"], reg["experiment_set"]["moving_command_targets"])),
                            meshes[0], reg["experiment_set"]["step_duration_ns"], stuck_at_ns=stuck_at)
        moving[name] = _case_summary(run, 0, 0.5, 1, threshold, reg)
    post_hashes = []
    for _ in range(reg["experiment_set"]["post_startup_stuck_repeats"]):
        run = run_open_loop(0.5, tuple(zip(reg["experiment_set"]["post_startup_command_times_ns"], reg["experiment_set"]["post_startup_targets"])),
                            meshes[0], 6_000_000_000, stuck_at_ns=reg["experiment_set"]["post_startup_stuck_at_ns"])
        post_hashes.append(_repeat_signature(run))
    post_anchor_ns = reg["experiment_set"]["post_startup_stuck_at_ns"]
    post_anchor_speed = next(x["measured_speed"] for x in run["rows"] if x["time_ns"] == post_anchor_ns)
    post = _case_summary(run, post_anchor_ns, post_anchor_speed, 1, threshold, reg)
    post.update({"anchor_ns": post_anchor_ns, "anchor_speed": post_anchor_speed,
                 "all_repeat_hashes_identical": len(set(post_hashes)) == 1})
    sensor_run = run_open_loop(0.5, ((0, 0.7),), meshes[0], reg["experiment_set"]["step_duration_ns"],
                               sensor_loss=(reg["experiment_set"]["sensor_loss_start_ns"], reg["experiment_set"]["sensor_recovery_ns"]))
    sensor_case = _case_summary(sensor_run, 0, 0.5, 1, threshold, reg)
    sensor_case["first_valid_after_recovery_ns"] = next((x["time_ns"] for x in sensor_run["rows"] if x["time_ns"] >= reg["experiment_set"]["sensor_recovery_ns"] and x["quality"] == "VALID"), None)
    repeat_steps = {}
    for direction in (1, -1):
        hashes = []
        for _ in range(10):
            run = run_open_loop(0.5, ((0, 0.5 + direction * 0.2),), meshes[0], reg["experiment_set"]["step_duration_ns"])
            hashes.append(_repeat_signature(run))
        repeat_steps["UP" if direction > 0 else "DOWN"] = {"runs": 10, "all_identical": len(set(hashes)) == 1, "sha256": hashes[0]}
    all_runs = [*static.values(), *steps.values(), *reversals.values(), *moving.values(), post, sensor_case]
    conservation = all(x["conservation"]["max_mass_residual_kg_s"] <= 1e-6 and x["conservation"]["max_energy_residual_j"] <= 1e-5 for x in all_runs)
    repeatability = all(x["all_identical"] for x in static.values()) and all(x["all_identical"] for x in repeat_steps.values()) and all(x["all_repeat_hashes_identical"] for x in reversals.values()) and post["all_repeat_hashes_identical"]
    causal = all(x["prefix_causal"] for x in [*steps.values(), *reversals.values(), *moving.values(), post, sensor_case])
    nominal_observable = moving["NORMAL"]["first_qualified_ns"] is not None
    all_steps_observable = all(x["observable"] for x in steps.values())
    stuck_unobservable = moving["SILENT_STUCK"]["first_qualified_ns"] is None and post["first_qualified_ns"] is None
    reversal_observable = all(x["first_qualified_ns"] is not None for x in reversals.values())
    sensor_valid = all(not x["qualified"] for x in sensor_case["decisions"] if not x["valid"])
    mesh_stable = threshold == max(0.01, 2 * stationary_floor)
    gate = (
        "FIXTURE_TRACKING_CALIBRATION_AND_OBSERVABILITY_CLOSED"
        if all((conservation, repeatability, causal, nominal_observable, all_steps_observable, stuck_unobservable, reversal_observable, sensor_valid, mesh_stable))
        else "TRACKING_OBSERVABILITY_INSUFFICIENT"
    )
    evidence = {"schema": "phase5-r5-2-2-tracking-calibration-evidence-v1", "registration_sha256": sha(REGISTRATION),
                "source_hash_checks": checks, "source_evidence_sha256": reg["source_evidence_sha256"],
                "production_source_sha256": reg["production_sha256"],
                "model_audit": {"actuator_config": reg["fixture_actuator"], "sensor_config": reg["fixture_sensor"],
                                "modeled_sensor_noise": 0, "modeled_sensor_noise_basis": "LocalMeasurement.sample copies actuator.actual without stochastic perturbation",
                                "speed_measurement_quantization": "SPEED_MEASUREMENT_QUANTIZATION_NOT_MODELED",
                                "hardware_speed_resolution": "CALIBRATION_REQUIRED"},
                "static": static, "stationary_floor": stationary_floor, "mesh_floor": mesh_floor,
                "minimum_observable_speed_change": threshold, "step_cases": steps, "reversals": reversals,
                "moving_command": moving, "post_startup_stuck": post, "sensor_loss_recovery": sensor_case,
                "uncertainty": {"stationary_speed_peak_to_peak": stationary_floor, "common_sample_mesh_spread": mesh_floor,
                                "modeled_stochastic_noise": 0, "modeled_quantization": "ABSENT",
                                "real_hardware_noise_resolution_and_timing": "CALIBRATION_REQUIRED",
                                "scope": "deterministic generic numerical fixture; not physical confidence interval"},
                "repeat_steps": repeat_steps,
                "checks": {"conservation": conservation, "repeatability": repeatability, "prefix_causality": causal,
                           "normal_moving_observable": nominal_observable, "all_registered_steps_observable": all_steps_observable,
                           "stuck_not_falsely_qualified": stuck_unobservable,
                           "reversal_observable": reversal_observable, "sensor_invalid_not_progress": sensor_valid,
                           "mesh_floor_bounded": mesh_stable},
                "status": gate, "r5_2_1_restarted": False, "r5_3_restarted": False, "production_changed": False,
                "final_feedback_baseline_frozen": False, "phase6_started": False}
    if gate == "FIXTURE_TRACKING_CALIBRATION_AND_OBSERVABILITY_CLOSED":
        actuator_profile = {
            "command_delay_s": parameter(0.2, "s", "MODEL_CONFIG", "PumpActuatorConfig.command_delay_ns", "exact typed fixture", ">=0"),
            "speed_min": parameter(0.3, "fraction", "MODEL_CONFIG", "PumpActuatorConfig.minimum", "exact typed fixture", "0..1"),
            "speed_max": parameter(0.9, "fraction", "MODEL_CONFIG", "PumpActuatorConfig.maximum", "exact typed fixture", "0..1"),
            "speed_rate_limit_per_s": parameter(0.2, "fraction/s", "MODEL_CONFIG", "PumpActuatorConfig.ramp_per_s", "exact typed fixture", ">0"),
            "lag_time_constant_s": parameter(1.0, "s", "MODEL_CONFIG", "PumpActuatorConfig.tau_s", "exact typed fixture", ">0"),
            "command_resolution": parameter(None, "fraction", "NOT_MODELED", "PumpActuator.command", "no command quantization in source", "not applicable"),
            "directional_symmetry": parameter("symmetric nominal lag/ramp", "metadata", "DERIVED_FROM_MODEL", "PumpActuator._advance_segment", "same equation for signed delta", "fixture only"),
        }
        sensor_profile = {
            "measurement_period_s": parameter(0.2, "s", "MODEL_CONFIG", "SensorConfig.sample_ns", "exact typed fixture", ">0"),
            "measurement_release_delay_s": parameter(0.0, "s", "MODEL_CONFIG", "SensorConfig.local_delay_ns", "exact typed fixture", ">=0"),
            "measurement_validity_limit_s": parameter(1.0, "s", "MODEL_CONFIG", "SensorConfig.max_age_ns", "exact typed fixture", ">0"),
            "speed_measurement_resolution": parameter(None, "fraction", "NOT_MODELED", "LocalMeasurement.sample", "no quantization/digitization in source; not float epsilon", "CALIBRATION_REQUIRED for hardware"),
            "speed_measurement_noise_bound": parameter(0.0, "fraction", "DERIVED_FROM_MODEL", "LocalMeasurement.sample", "no stochastic perturbation in source", "fixture only; hardware CALIBRATION_REQUIRED"),
            "speed_measurement_stationary_variation": parameter(stationary_floor, "fraction peak-to-peak", "FIXTURE_CALIBRATION", "phase5_r5_2_2_tracking_calibration_evidence.json/static", "max stable-window peak-to-peak", ">=0; hardware CALIBRATION_REQUIRED"),
            "timestamp_resolution_s": parameter(1e-9, "s representation", "DERIVED_FROM_MODEL", "MeasuredSnapshot.sample_ns/available_ns", "integer nanosecond timestamp representation, not physical clock accuracy", "hardware CALIBRATION_REQUIRED"),
            "quality_semantics": parameter("VALID/MISSING and released by decision time", "metadata", "DERIVED_FROM_MODEL", "MeasuredSnapshot.qualified", "source quality and age audit", "fixture only"),
        }
        qualification_profile = {
            "material_command_delta": parameter(0.15, "fraction", "ENGINEERING_ASSUMPTION", "R5.2 classifier.material_command_change_fraction", "historical diagnostic value; observability audit only", "fixture only; hardware CALIBRATION_REQUIRED"),
            "minimum_observable_speed_change": parameter(threshold, "fraction", "FIXTURE_CALIBRATION", "R5.2 0.01 and R5.2.2 observation floor", "max(0.01,2*floor) registered before fault runs", "fixture only; hardware CALIBRATION_REQUIRED"),
            "minimum_progress_margin": parameter(2.0, "dimensionless floor multiplier", "ENGINEERING_ASSUMPTION", "R5.2.2 registration.estimation_and_uncertainty", "pre-registered factor above stationary/mesh floor", "fixture only; hardware CALIBRATION_REQUIRED"),
            "tracking_error_tolerance": parameter(0.15, "fraction", "ENGINEERING_ASSUMPTION", "SafetySupervisor.evaluate historical mismatch predicate", "provenance audit only; not a progress threshold", "fixture only; hardware CALIBRATION_REQUIRED"),
            "response_opening_rule": parameter(reg["estimation_and_uncertainty"]["response_open"], "rule", "DERIVED_FROM_MODEL", "PumpActuatorConfig + SensorConfig", "sample grid and nominal displacement model", "fixture only; hardware CALIBRATION_REQUIRED"),
            "progress_rule": parameter(reg["estimation_and_uncertainty"]["qualified_progress"], "rule", "FIXTURE_CALIBRATION", "R5.2.2 registration", "released measured-only directional displacement", "fixture only; hardware CALIBRATION_REQUIRED"),
            "suspected_rule_parameters": parameter({"expected_min": 0.03, "ratio_below": 0.5}, "fraction/ratio", "ENGINEERING_ASSUMPTION", "R5.2 classifier", "historical initial-handoff diagnostic only; not continuous Safety", "fixture only"),
            "confirmed_rule_parameters": parameter({"expected_min": 0.12, "ratio_below": 0.35, "qualified_samples": 2}, "fraction/ratio/count", "ENGINEERING_ASSUMPTION", "R5.2 classifier", "historical initial-handoff diagnostic only; not continuous Safety", "fixture only"),
            "measurement_quality_requirements": parameter("VALID, released <= decision time, age <= max_age", "rule", "DERIVED_FROM_MODEL", "MeasuredSnapshot.qualified", "source quality semantics", "fixture only"),
            "reversal_observability_rule": parameter("new-direction released displacement >= calibrated threshold relative to reversal-time measured anchor", "rule", "FIXTURE_CALIBRATION", "R5.2.2 reversal experiment", "test-only observable evidence, not epoch-reset logic", "fixture only; hardware CALIBRATION_REQUIRED"),
            "sensor_recovery_rule": parameter("first released VALID sample is available at recovery sample; do not infer progress from invalid interval", "observation only", "FIXTURE_CALIBRATION", "R5.2.2 sensor-loss experiment", "no production recovery state machine", "fixture only; hardware CALIBRATION_REQUIRED"),
        }
        profile = {"schema": "phase5-r5-2-2-fixture-tracking-profile-v1",
                   "classification": ["GENERIC NUMERICAL FIXTURE ONLY", "NOT OEM", "NOT NVIDIA GB300", "NOT HARDWARE VALIDATION", "REQUIRES RECALIBRATION FOR REAL EQUIPMENT"],
                   "registration_sha256": sha(REGISTRATION),
                   "ActuatorTrackingProfile": actuator_profile,
                   "SensorObservationProfile": sensor_profile,
                   "TrackingQualificationProfile": qualification_profile,
                   "real_hardware": "CALIBRATION_REQUIRED; no fixture value is a hardware default"}
        _write_json(PROFILE, profile)
        evidence["profile_sha256"] = sha(PROFILE)
    else:
        evidence["profile_sha256"] = None
    _write_json(EVIDENCE, evidence)
    make_figure(evidence)
    print(json.dumps({"gate": gate, "registration_sha256": sha(REGISTRATION), "evidence_sha256": sha(EVIDENCE),
                      "profile_sha256": evidence["profile_sha256"], "threshold": threshold, "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()
