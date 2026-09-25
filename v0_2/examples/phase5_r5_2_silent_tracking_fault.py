"""R5.2 test-only physical faults and causal measured-only handoff audit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from math import exp
from pathlib import Path
from unittest.mock import patch

from v0_2.actuators.pump import PumpActuator
from v0_2.control.directional_outer import DirectionalOuterFeedback
from v0_2.examples import phase5_1r2_qualification as q
from v0_2.examples import phase5_r4_outer_tuning as r4
from v0_2.examples import phase5_r5_1_safety_handoff_audit as r51
from v0_2.examples import phase5_r5_directional_pi as r5
from v0_2.plant import controlled_loop
from v0_2.plant.controlled_loop import Disturbance

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_r5_2_silent_tracking_fault_registration.json"
EVIDENCE = ROOT / "phase5_r5_2_silent_tracking_fault_evidence.json"
FIGURE = ROOT / "docs/results/phase5_r5_2_silent_tracking_fault_qualification.png"
REPORT = ROOT / "PHASE5_R5_2_SILENT_TRACKING_FAULT_QUALIFICATION_REPORT.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def integrity(reg: dict) -> dict:
    checks = {
        "r5_1_registration": sha(r51.REGISTRATION) == reg["source_r5_1_registration_sha256"],
        "r5_1_evidence": sha(r51.EVIDENCE) == reg["source_r5_1_evidence_sha256"],
        "r5_candidate": sha(r5.CANDIDATE_BASELINE) == reg["source_r5_candidate_sha256"],
        "production_safety": sha(ROOT / "v0_2/safety/supervisor.py") == reg["source_safety_sha256"],
        "production_actuator": sha(ROOT / "v0_2/actuators/pump.py") == reg["source_actuator_sha256"],
    }
    candidate = json.loads(r5.CANDIDATE_BASELINE.read_text(encoding="utf-8"))
    checks["candidate"] = all(candidate["outer_kp" if key == "kp" else key] == value for key, value in reg["frozen_controller"].items())
    if not all(checks.values()):
        raise RuntimeError(f"R5.2 source integrity failure: {checks}")
    return checks


@dataclass(frozen=True)
class PermittedObservation:
    timestamp_ns: int
    current_plc_command: float
    previous_plc_command: float | None
    command_timestamp_ns: int
    released_measured_pump_speed: float | None
    measurement_sample_ns: int | None
    measurement_release_ns: int | None
    measurement_age_ns: int | None
    measurement_quality: str
    measured_dp_pa: float | None
    measured_flow_kg_s: float | None
    released_temperature_k: float | None
    current_safety_state: str
    current_safety_reasons: tuple[str, ...]


class MeasuredOnlyClassifier:
    """Online audit sink. Its input type cannot carry raw truth or fault identity."""

    def __init__(self, registered: dict, nominal_contract: dict, *, with_hydraulics: bool = False):
        self.cfg = registered
        self.nominal = nominal_contract
        self.with_hydraulics = with_hydraulics
        self.anchor_ns = None
        self.anchor_speed = None
        self.anchor_dp = None
        self.anchor_flow = None
        self.anchor_step = None
        self.direction = None
        self.previous_observation = None
        self.previous_error = None
        self.deficient_samples = 0
        self.state = "HANDOFF_PENDING"
        self.handoff_qualified = False
        self.transitions = []

    def update(self, item: PermittedObservation) -> dict:
        if not isinstance(item, PermittedObservation):
            raise TypeError("Only the permitted measured observation is accepted")
        if self.previous_observation is not None and item.timestamp_ns <= self.previous_observation.timestamp_ns:
            raise ValueError("Observations must arrive strictly in event-time order")
        good = (
            item.released_measured_pump_speed is not None
            and item.measurement_sample_ns is not None
            and item.measurement_release_ns is not None
            and item.measurement_release_ns <= item.timestamp_ns
            and item.measurement_age_ns is not None
            and 0 <= item.measurement_age_ns <= self.cfg["max_measurement_age_ns"]
            and item.measurement_quality == "VALID"
        )
        previous_step = None if item.previous_plc_command is None else item.current_plc_command - item.previous_plc_command
        measured_step = None if not good else item.current_plc_command - item.released_measured_pump_speed
        material_reference = item.previous_plc_command if previous_step is not None and abs(previous_step) >= self.cfg["material_command_change_fraction"] else item.released_measured_pump_speed if measured_step is not None and abs(measured_step) >= self.cfg["material_command_change_fraction"] else None
        if self.anchor_ns is None and good and material_reference is not None:
            self.anchor_ns = item.command_timestamp_ns
            self.anchor_speed = item.released_measured_pump_speed
            self.anchor_dp = item.measured_dp_pa
            self.anchor_flow = item.measured_flow_kg_s
            self.anchor_step = abs(item.current_plc_command - material_reference)
            self.direction = 1 if item.current_plc_command > material_reference else -1
        elapsed_s = None if self.anchor_ns is None else max(0, item.timestamp_ns - self.anchor_ns) / 1e9
        available_s = None if elapsed_s is None else max(0.0, elapsed_s - self.nominal["command_delay_ns"] / 1e9)
        expected = 0.0 if available_s is None else min(self.nominal["ramp_per_s"] * available_s, self.anchor_step * (1 - exp(-available_s / self.nominal["tau_s"])))
        progress = None if not good or self.anchor_speed is None else self.direction * (item.released_measured_pump_speed - self.anchor_speed)
        error = None if not good else abs(item.current_plc_command - item.released_measured_pump_speed)
        prior = self.previous_observation
        slope = None if not good or prior is None or prior.released_measured_pump_speed is None or prior.measurement_quality != "VALID" else (item.released_measured_pump_speed - prior.released_measured_pump_speed) / ((item.timestamp_ns - prior.timestamp_ns) / 1e9)
        error_change = None if error is None or self.previous_error is None else error - self.previous_error
        error_slope = None if error_change is None or prior is None else error_change / ((item.timestamp_ns - prior.timestamp_ns) / 1e9)
        started = progress is not None and progress >= self.cfg["minimum_measured_response_fraction"]
        direction_ok = progress is not None and progress >= 0 and (slope is None or self.direction * slope >= -1e-6)
        ratio = None if progress is None or expected <= 0 else progress / expected
        if self.state == "TRACKING_FAULT_CONFIRMED":
            state = self.state
        elif not good:
            state = "INSUFFICIENT_MEASUREMENT"
            self.deficient_samples = 0
        elif self.handoff_qualified:
            state = "TRACKING_PROGRESS"
            self.deficient_samples = 0
        elif self.anchor_ns is None or expected < self.cfg["suspect_min_expected_progress_fraction"]:
            state = "HANDOFF_PENDING"
            self.deficient_samples = 0
        elif started and direction_ok and ratio >= self.cfg["suspect_progress_ratio_below"]:
            state = "TRACKING_PROGRESS"
            self.deficient_samples = 0
            self.handoff_qualified = True
        else:
            deficient = expected >= self.cfg["confirm_min_expected_progress_fraction"] and (not direction_ok or ratio is None or ratio < self.cfg["confirm_progress_ratio_below"])
            self.deficient_samples = self.deficient_samples + 1 if deficient else 0
            state = "TRACKING_FAULT_CONFIRMED" if self.deficient_samples >= self.cfg["confirm_consecutive_qualified_samples"] else "TRACKING_FAULT_SUSPECTED"
        if state != self.state:
            self.transitions.append({"timestamp_ns": item.timestamp_ns, "state": state})
        self.state = state
        self.previous_observation = item
        if error is not None:
            self.previous_error = error
        flow_change = None if item.measured_flow_kg_s is None or self.anchor_flow is None else item.measured_flow_kg_s - self.anchor_flow
        dp_change = None if item.measured_dp_pa is None or self.anchor_dp is None else item.measured_dp_pa - self.anchor_dp
        interval_s = None if prior is None else (item.timestamp_ns - prior.timestamp_ns) / 1e9
        flow_trend = None if interval_s is None or item.measured_flow_kg_s is None or prior.measured_flow_kg_s is None else (item.measured_flow_kg_s - prior.measured_flow_kg_s) / interval_s
        dp_trend = None if interval_s is None or item.measured_dp_pa is None or prior.measured_dp_pa is None else (item.measured_dp_pa - prior.measured_dp_pa) / interval_s
        return {
            "timestamp_ns": item.timestamp_ns, "diagnostic_state": state,
            "previous_measured_pump_speed": prior.released_measured_pump_speed if prior else None,
            "command_delta": previous_step,
            "command_age_ns": item.timestamp_ns - item.command_timestamp_ns,
            "command_step_magnitude": self.anchor_step,
            "time_since_material_command_change_s": elapsed_s,
            "expected_nominal_measured_progress": expected,
            "measured_speed_change_since_command": progress,
            "measured_speed_slope": slope,
            "tracking_error": error,
            "tracking_error_change": error_change,
            "tracking_error_slope": error_slope,
            "flow_change_since_command": flow_change,
            "dp_change_since_command": dp_change,
            "flow_trend_kg_s2": flow_trend,
            "dp_trend_pa_s": dp_trend,
            "direction_consistency": direction_ok,
            "response_started": started,
            "response_progressing": state == "TRACKING_PROGRESS",
            "qualified_measurement": good,
            "hydraulic_corroboration_available": self.with_hydraulics and flow_change is not None and dp_change is not None,
        }


def fixture_class(case: str, registration: dict):
    """Construct a local physical-only override; never touch the production class."""
    if case == "SILENT_STUCK":
        class SilentStuck(PumpActuator):
            def _advance_segment(self, seconds):
                return

        return SilentStuck
    if case.startswith("DELAY_"):
        delay_ns = {"DELAY_0_6": 600_000_000, "DELAY_1_0": 1_000_000_000, "DELAY_2_0": 2_000_000_000}[case]

        class ExcessiveDelay(PumpActuator):
            def command(self, command, now_ns):
                super().command(command, now_ns)
                _, value, command_id = self.pending[-1]
                self.pending[-1] = (now_ns + delay_ns, value, command_id)

        return ExcessiveDelay
    if case.startswith("SLOW_"):
        severity = {"SLOW_RAMP_0_1": (0.1, 2.0), "SLOW_RAMP_0_05": (0.05, 4.0)}[case]

        class Sluggish(PumpActuator):
            def _advance_segment(self, seconds):
                if seconds <= 0:
                    return
                exact = self.target + (self.actual - self.target) * exp(-seconds / severity[1])
                delta = min(severity[0] * seconds, max(-severity[0] * seconds, exact - self.actual))
                self.actual = min(self.config.maximum, max(self.config.minimum, self.actual + delta))

        return Sluggish
    return PumpActuator


def run_case(case: str, state, speed: float, historical: dict, registration: dict, *, duration_ns: int):
    plant, controls = q.physical_fixture(branch_count=2, power_each=historical["workload_w_per_device"])
    plant = replace(plant, initial_state=state)
    controls = q._controls(controls, speed)
    inner = r4._gains(historical["inner"])
    outer = {"kp": 4500.0, "ki": 110.0, "kd": 0.0}
    configs = list(q.fixture_configs(inner, outer, 200_000_000))
    configs[3] = replace(configs[3], target_k=historical["target_k"])
    configs[5] = replace(configs[5], control_target_k=historical["target_k"])
    controller = {}

    def outer_factory(config):
        controller["object"] = DirectionalOuterFeedback(config, 110.0, 130.0)
        return controller["object"]

    disturbances = (Disturbance(0, sensor_failures=("pump_speed",)),) if case == "SENSOR_QUALITY_INVALID" else ()
    with patch.object(controlled_loop, "OuterFeedback", outer_factory), patch.object(controlled_loop, "PumpActuator", fixture_class(case, registration)):
        run = controlled_loop.run_feedback(plant, controls, duration_ns, *configs, disturbances=disturbances)
    return run, controller["object"].ticks


def observations(run, prepared_speed: float, early_ns: int) -> list[PermittedObservation]:
    commands = {x.command_id: x for x in run.actuator_commands}
    envelopes = {x.envelope_id: x for x in run.safety_envelopes}
    measurements = {x.measurement_record_id: x for x in run.measurements}
    result = []
    previous_command = None
    previous_id = None
    for row in run.rows:
        if row.time_ns > early_ns:
            break
        command = commands[row.actuator_command_id]
        measurement = measurements.get(row.measurement_record_id)
        if command.command_id != previous_id:
            prior_for_this_command = previous_command
            previous_command = command.applied_command_before_actuator_dynamics
            previous_id = command.command_id
        else:
            prior_for_this_command = previous_command
        quality = dict(measurement.quality).get("pump_speed", "MISSING") if measurement else "MISSING"
        result.append(PermittedObservation(
            timestamp_ns=row.time_ns,
            current_plc_command=command.applied_command_before_actuator_dynamics,
            previous_plc_command=prior_for_this_command,
            command_timestamp_ns=command.created_ns,
            released_measured_pump_speed=measurement.pump_speed if measurement else None,
            measurement_sample_ns=measurement.sample_ns if measurement else None,
            measurement_release_ns=measurement.available_ns if measurement else None,
            measurement_age_ns=row.time_ns - measurement.sample_ns if measurement else None,
            measurement_quality=quality,
            measured_dp_pa=measurement.dp_pa if measurement else None,
            measured_flow_kg_s=measurement.flow_kg_s if measurement else None,
            released_temperature_k=max((temp for _, temp in measurement.device_temperatures_k), default=None) if measurement else None,
            current_safety_state=row.safety_state,
            current_safety_reasons=envelopes[row.safety_envelope_id].reason_codes,
        ))
    return result


def delayed_observations(source: list[PermittedObservation], delay_ns: int) -> list[PermittedObservation]:
    """Auditor-only telemetry withholding; the production loop is already complete."""
    result = []
    for index, current in enumerate(source):
        released = next((old for old in reversed(source[: index + 1]) if old.measurement_sample_ns is not None and old.measurement_release_ns + delay_ns <= current.timestamp_ns), None)
        if released is None:
            result.append(replace(current, released_measured_pump_speed=None, measurement_sample_ns=None, measurement_release_ns=None, measurement_age_ns=None, measurement_quality="MISSING", measured_dp_pa=None, measured_flow_kg_s=None, released_temperature_k=None))
        else:
            result.append(replace(current, released_measured_pump_speed=released.released_measured_pump_speed, measurement_sample_ns=released.measurement_sample_ns, measurement_release_ns=released.measurement_release_ns + delay_ns, measurement_age_ns=current.timestamp_ns - released.measurement_sample_ns, measurement_quality=released.measurement_quality, measured_dp_pa=released.measured_dp_pa, measured_flow_kg_s=released.measured_flow_kg_s, released_temperature_k=released.released_temperature_k))
    return result


def audit_observations(source: list[PermittedObservation], reg: dict, *, with_hydraulics: bool) -> dict:
    classifier = MeasuredOnlyClassifier(reg["classifier"], reg["nominal_actuator_contract"], with_hydraulics=with_hydraulics)
    records = []
    for item in source:
        features = classifier.update(item)
        records.append({"observation": asdict(item), "features": features})
    state_times = {name: next((x["timestamp_ns"] for x in classifier.transitions if x["state"] == name), None) for name in reg["classifier"]["states"]}
    return {"records": records, "transitions": classifier.transitions, "first_state_times_ns": state_times, "final_state": classifier.state, "anchor_command_time_ns": classifier.anchor_ns, "fault_confirmation_ns": state_times["TRACKING_FAULT_CONFIRMED"]}


def summarize(case: str, run, source: list[PermittedObservation], reg: dict) -> dict:
    speed_only = audit_observations(source, reg, with_hydraulics=False)
    augmented = audit_observations(source, reg, with_hydraulics=True)
    measured = run.measurements
    first_speed = source[0].released_measured_pump_speed
    first_response = next((x.timestamp_ns for x in source if first_speed is not None and x.released_measured_pump_speed is not None and abs(x.released_measured_pump_speed - first_speed) >= reg["classifier"]["minimum_measured_response_fraction"]), None)
    first_command = run.actuator_commands[0]
    measured_fault_bits = [m.pump_fault for m in measured if m.available_ns <= reg["observation"]["early_trace_ns"]]
    ownership = all(c.producer_module == "PLC" and bool(c.plc_cycle_id) for c in run.actuator_commands)
    return {
        "case": case, "fixture_tags": reg["test_only_fault_fixtures"]["tags"] if case != "NOMINAL_COLD" else [],
        "first_command_ns": first_command.created_ns,
        "first_command_speed": first_command.applied_command_before_actuator_dynamics,
        "first_command_delta": first_command.applied_command_before_actuator_dynamics - reg["preparation"]["open_loop_pump_speed"],
        "first_physically_plausible_response_ns": first_command.created_ns + reg["nominal_actuator_contract"]["command_delay_ns"],
        "first_measured_response_ns": first_response,
        "measured_fault_bit_all_false": all(bit is False for bit in measured_fault_bits),
        "sensor_quality": [dict(m.quality).get("pump_speed") for m in measured if m.available_ns <= reg["observation"]["early_trace_ns"]],
        "speed_only_diagnostic": speed_only,
        "speed_dp_flow_diagnostic": augmented,
        "safety_events": [list(x) for x in run.events],
        "current_safety_final_state": run.rows[-1].safety_state,
        "full_run_duration_ns": run.rows[-1].time_ns,
        "ownership_pass": ownership,
        "conservation": {"max_mass_residual_kg_s": max(x.ledger.max_mass_volume_residual_kg_s for x in run.steps), "max_energy_residual_j": max(abs(x.ledger.full_loop_residual_j) for x in run.steps)},
    }


def repeat_signature(case: dict) -> bytes:
    diagnostic = case["speed_only_diagnostic"]
    return canonical({"records": diagnostic["records"], "transitions": diagnostic["transitions"], "fault_confirmation_ns": diagnostic["fault_confirmation_ns"], "safety_events_first_10s": [x for x in case["safety_events"] if x[0] <= 10_000_000_000], "first_measured_response_ns": case["first_measured_response_ns"]})


def figure(cases: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    selected = ("NOMINAL_COLD", "SILENT_STUCK", "DELAY_0_6", "DELAY_1_0", "DELAY_2_0")
    safety_map = {"NORMAL": 0, "FF_DISABLED": 1, "DEGRADED": 2, "DERATE_REQUESTED": 3, "PROTECTED": 4, "FAULT": 5}
    diagnostic_map = {name: index for index, name in enumerate(("HANDOFF_PENDING", "TRACKING_PROGRESS", "TRACKING_FAULT_SUSPECTED", "TRACKING_FAULT_CONFIRMED", "INSUFFICIENT_MEASUREMENT"))}
    fig, axes = plt.subplots(8, 1, figsize=(17, 24), sharex=True)
    for name in selected:
        records = cases[name]["speed_only_diagnostic"]["records"]
        t = [r["observation"]["timestamp_ns"] / 1e9 for r in records]
        measured = [r["observation"]["released_measured_pump_speed"] for r in records]
        command = [r["observation"]["current_plc_command"] for r in records]
        axes[0].plot(t, measured, label=f"{name} measured")
        if name == "NOMINAL_COLD":
            axes[0].plot(t, command, color="black", ls="--", label="PLC command")
        axes[1].plot(t, [r["features"]["tracking_error"] for r in records], label=name)
        axes[2].plot(t, [r["features"]["tracking_error_slope"] for r in records], label=name)
        axes[3].plot(t, [r["observation"]["measured_flow_kg_s"] for r in records], label=name)
        axes[4].plot(t, [r["observation"]["measured_dp_pa"] for r in records], label=name)
        axes[5].step(t, [safety_map.get(r["observation"]["current_safety_state"], 6) for r in records], where="post", label=name)
        axes[6].step(t, [diagnostic_map[r["features"]["diagnostic_state"]] for r in records], where="post", label=name)
        confirmed = cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"]
        if confirmed is not None:
            axes[7].scatter([confirmed / 1e9], [selected.index(name)], s=90, label=name)
    for axis, label in zip(axes, ("PLC / measured speed", "tracking error", "error slope (/s)", "measured flow (kg/s)", "measured DP (Pa)", "current Safety", "R5.2 diagnostic", "confirmation timing")):
        axis.set_ylabel(label)
        axis.grid(alpha=0.18)
    axes[0].legend(ncol=3, fontsize=8)
    axes[1].legend(ncol=5, fontsize=7)
    axes[5].set_yticks(list(safety_map.values()), list(safety_map), fontsize=7)
    axes[6].set_yticks(list(diagnostic_map.values()), list(diagnostic_map), fontsize=7)
    axes[7].set_yticks(range(len(selected)), list(selected), fontsize=7)
    axes[7].set_xlim(0, 10)
    axes[7].set_xlabel("time after controller takeover (s)")
    fig.suptitle("PHASE 5R5.2 — DIAGNOSTIC EVIDENCE ONLY — NO PRODUCTION SAFETY CHANGE — NOT HARDWARE VALIDATION", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main() -> None:
    reg = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    checks = integrity(reg)
    historical = json.loads(r4.REGISTRATION.read_text(encoding="utf-8"))
    preparations, states = r4._prepare(historical)
    cold_prep = preparations["COLD_CAPTURE"]
    if cold_prep["speed_fraction"] != 0.9 or cold_prep["duration_s"] != 180 or cold_prep["controller_prehistory"] != "none" or cold_prep["integrator_warm_start"]:
        raise RuntimeError("R5.2 cold preparation is not historical COLD_CAPTURE")
    physical_cases = ("NOMINAL_COLD", "SILENT_STUCK", "DELAY_0_6", "DELAY_1_0", "DELAY_2_0", "SLOW_RAMP_0_1", "SLOW_RAMP_0_05", "SENSOR_QUALITY_INVALID")
    cases = {}
    for case in physical_cases:
        run, _ = run_case(case, states["COLD_CAPTURE"], 0.9, historical, reg, duration_ns=reg["observation"]["full_run_ns"])
        source = observations(run, 0.9, reg["observation"]["early_trace_ns"])
        cases[case] = summarize(case, run, source, reg)
        print(f"{case} full 180 s + 10 s diagnostic complete", flush=True)
    nominal_source = [PermittedObservation(**x["observation"]) for x in cases["NOMINAL_COLD"]["speed_only_diagnostic"]["records"]]
    delayed = delayed_observations(nominal_source, reg["test_only_fault_fixtures"]["auditor_telemetry_delay_ns"])
    delayed_speed = audit_observations(delayed, reg, with_hydraulics=False)
    cases["AUDITOR_TELEMETRY_DELAY_0_4"] = {"case": "AUDITOR_TELEMETRY_DELAY_0_4", "fixture_tags": reg["test_only_fault_fixtures"]["tags"], "source": "post-run auditor-only delayed replay of nominal measurements", "speed_only_diagnostic": delayed_speed, "current_safety_events": cases["NOMINAL_COLD"]["safety_events"], "production_output_unchanged": True}
    historical_events = [[200_000_000, "DEGRADED", ["ACTUATOR_TRACKING_PENDING"]], [600_000_000, "FF_DISABLED", ["RECOVERY_QUALIFICATION"]], [2_600_000_000, "NORMAL", []]]
    nominal_safety = [[t, state, list(reasons)] for t, state, reasons in cases["NOMINAL_COLD"]["safety_events"]]
    nominal_reproduced = all(x in nominal_safety for x in historical_events) and cases["NOMINAL_COLD"]["first_command_speed"] == 0.648 and cases["NOMINAL_COLD"]["first_measured_response_ns"] == 400_000_000
    repeated = {}
    for case in ("NOMINAL_COLD", "SILENT_STUCK", "DELAY_1_0"):
        hashes = [hashlib.sha256(repeat_signature(cases[case])).hexdigest()]
        for _ in range(9):
            run, _ = run_case(case, states["COLD_CAPTURE"], 0.9, historical, reg, duration_ns=reg["observation"]["early_trace_ns"])
            source = observations(run, 0.9, reg["observation"]["early_trace_ns"])
            record = summarize(case, run, source, reg)
            hashes.append(hashlib.sha256(repeat_signature(record)).hexdigest())
        repeated[case] = {"runs": 10, "all_identical": len(set(hashes)) == 1, "hash_sha256": hashes[0], "all_hashes": hashes}
        print(f"{case} repeatability 10/10 complete", flush=True)
    nominal = cases["NOMINAL_COLD"]["speed_only_diagnostic"]
    silent = cases["SILENT_STUCK"]["speed_only_diagnostic"]
    large_delays_confirmed = all(cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"] is not None for name in ("DELAY_1_0", "DELAY_2_0"))
    stale_insufficient = all(record["features"]["diagnostic_state"] == "INSUFFICIENT_MEASUREMENT" for record in cases["SENSOR_QUALITY_INVALID"]["speed_only_diagnostic"]["records"])
    delayed_safe = delayed_speed["fault_confirmation_ns"] is None
    ownership = all(cases[name]["ownership_pass"] for name in physical_cases)
    conservation = all(cases[name]["conservation"]["max_mass_residual_kg_s"] <= 1e-6 and cases[name]["conservation"]["max_energy_residual_j"] <= 1e-5 for name in physical_cases)
    causality = all(record["observation"]["measurement_release_ns"] is None or record["observation"]["measurement_release_ns"] <= record["observation"]["timestamp_ns"] for name in (*physical_cases, "AUDITOR_TELEMETRY_DELAY_0_4") for record in cases[name]["speed_only_diagnostic"]["records"])
    repeat_pass = all(item["all_identical"] for item in repeated.values())
    silent_bit_absent = cases["SILENT_STUCK"]["measured_fault_bit_all_false"]
    if not nominal_reproduced or nominal["fault_confirmation_ns"] is not None:
        gate = "MEASURED_ONLY_TRACKING_LOGIC_FALSE_POSITIVE"
    elif not stale_insufficient or not delayed_safe:
        gate = "MEASUREMENT_ARCHITECTURE_INSUFFICIENT_FOR_TRACKING_QUALIFICATION"
    elif silent["fault_confirmation_ns"] is None or not silent_bit_absent or not large_delays_confirmed:
        gate = "SILENT_STUCK_NOT_MEASURED_ONLY_DETECTABLE"
    elif not ownership or not conservation or not causality or not repeat_pass:
        gate = "MEASUREMENT_ARCHITECTURE_INSUFFICIENT_FOR_TRACKING_QUALIFICATION"
    else:
        gate = "MEASURED_ONLY_SILENT_TRACKING_FAULT_SEPARATION_PASS"
    matrix = []
    for case in physical_cases:
        record = cases[case]
        confirmation = record["speed_only_diagnostic"]["fault_confirmation_ns"]
        matrix.append({"case": case, "final_diagnostic": record["speed_only_diagnostic"]["final_state"], "false_positive": (confirmation is not None) if case == "NOMINAL_COLD" else None, "false_negative": (confirmation is None) if case == "SILENT_STUCK" else None, "detection_latency_ns": None if confirmation is None else confirmation - record["first_command_ns"], "current_safety_final_state": record["current_safety_final_state"]})
    hydraulic_comparison = {name: {"speed_only_confirmation_ns": cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"], "augmented_confirmation_ns": cases[name]["speed_dp_flow_diagnostic"]["fault_confirmation_ns"], "earlier_with_flow_dp": cases[name]["speed_dp_flow_diagnostic"]["fault_confirmation_ns"] is not None and (cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"] is None or cases[name]["speed_dp_flow_diagnostic"]["fault_confirmation_ns"] < cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"])} for name in physical_cases}
    evidence = {"schema": "phase5-r5-2-silent-tracking-fault-evidence-v1", "registration_sha256": sha(REGISTRATION), "source_r5_1_registration_sha256": sha(r51.REGISTRATION), "source_r5_1_evidence_sha256": sha(r51.EVIDENCE), "frozen_controller": reg["frozen_controller"], "integrity": checks, "preparation": cold_prep, "fault_fixture_definitions": reg["test_only_fault_fixtures"], "nominal_reproduced": nominal_reproduced, "cases": cases, "false_positive_negative_matrix": matrix, "flow_dp_comparison": hydraulic_comparison, "sensor_quality_insufficient": stale_insufficient, "measurement_delay_no_false_confirmation": delayed_safe, "silent_stuck_no_measured_fault_bit": silent_bit_absent, "ownership_status": "PASS" if ownership else "FAIL", "causality_status": "PASS" if causality else "FAIL", "conservation_status": "PASS" if conservation else "FAIL", "repeatability": repeated, "root_classification": gate, "status": gate, "production_safety_changed": False, "final_feedback_baseline_frozen": False, "phase6_authorized": False}
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    figure(cases)
    print(json.dumps({"gate": gate, "registration_sha256": evidence["registration_sha256"], "evidence_sha256": sha(EVIDENCE), "nominal_confirm_ns": nominal["fault_confirmation_ns"], "silent_confirm_ns": silent["fault_confirmation_ns"], "delay_confirm_ns": {name: cases[name]["speed_only_diagnostic"]["fault_confirmation_ns"] for name in ("DELAY_0_6", "DELAY_1_0", "DELAY_2_0")}, "stale_insufficient": stale_insufficient, "delayed_safe": delayed_safe, "repeatability": {name: x["all_identical"] for name, x in repeated.items()}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
