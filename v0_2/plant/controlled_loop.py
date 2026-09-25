"""Event-time feedback wrapper around the frozen Phase 4 physical plant."""

from dataclasses import dataclass, replace
from math import fsum

from v0_2.actuators.pump import PumpActuator, PumpActuatorConfig
from v0_2.control.inner_loop import InnerConfig, LocalDPPLC
from v0_2.control.intent import IntentSupervisor
from v0_2.control.outer_feedback import OuterConfig, OuterFeedback
from v0_2.measurement.local_sensor import LocalMeasurement, SensorConfig
from v0_2.plant.loop import step
from v0_2.safety.supervisor import SafetyPolicy, SafetySupervisor
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import SolverStatus, ThermalError, require


@dataclass(frozen=True)
class ControlClocks:
    physics_ns: int
    outer_ns: int
    plc_ns: int
    actuator_ns: int
    safety_ns: int

    def __post_init__(self):
        require(all(type(x) is int and x >= 1000 for x in (self.physics_ns, self.outer_ns, self.plc_ns, self.actuator_ns, self.safety_ns)), "CLOCK_CONFIG", "positive integer ns clocks")


@dataclass(frozen=True)
class Disturbance:
    time_ns: int
    power_each_w: float | None = None
    fws_inlet_k: float | None = None
    primary_flow_kg_s: float | None = None
    branch_zero_k_multiplier: float | None = None
    sensor_failures: tuple[str, ...] | None = None
    pump_stuck: bool | None = None


@dataclass(frozen=True)
class ControlledRow:
    time_ns: int
    device_k: float
    measured_device_k: float | None
    requested_dp_pa: float
    accepted_dp_pa: float
    measured_dp_pa: float | None
    pump_command: float
    pump_actual: float
    pump_measured: float | None
    total_flow_kg_s: float | None
    pump_electrical_j: float
    safety_state: str
    mass_residual_kg_s: float
    energy_residual_j: float
    fb_intent_id: str
    accepted_target_id: str
    safety_envelope_id: str
    plc_cycle_id: str
    actuator_command_id: str
    actuator_state_id: str
    measurement_record_id: str
    hydraulic_solution_id: str
    actuator_command_producer: str


@dataclass(frozen=True)
class ControlledRun:
    rows: tuple[ControlledRow, ...]
    steps: tuple
    events: tuple
    outer_config: OuterConfig
    inner_config: InnerConfig
    clocks: ControlClocks
    sensor_config: SensorConfig
    actuator_config: PumpActuatorConfig
    safety_policy: SafetyPolicy
    fb_intents: tuple
    accepted_targets: tuple
    safety_envelopes: tuple
    plc_cycles: tuple
    actuator_commands: tuple
    actuator_states: tuple
    measurements: tuple

    def metrics(self):
        require(bool(self.steps), "CONTROL_RUN", "no physical steps")
        target = self.outer_config.target_k
        peak = max(r.device_k for r in self.rows)
        intervals = [(a, b) for a, b in zip(self.rows, self.rows[1:])]
        temperature_iae = fsum(max(0.0, a.device_k - target) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals)
        temperature_ise = fsum(max(0.0, a.device_k - target) ** 2 * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals)
        dp_iae = fsum(abs(a.accepted_dp_pa - a.measured_dp_pa) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.measured_dp_pa is not None)
        saturation_s = fsum(
            (b.time_ns - a.time_ns) / 1e9
            for a, b in intervals
            if abs(a.pump_command - self.actuator_config.minimum) < 1e-9
            or abs(a.pump_command - self.actuator_config.maximum) < 1e-9
        )
        settled_at = next(
            (r.time_ns / 1e9 for i, r in enumerate(self.rows) if all(
                abs(later.device_k - target) <= 0.5 for later in self.rows[i:])),
            None,
        )
        safety_durations = {}
        for a, b in intervals:
            safety_durations[a.safety_state] = safety_durations.get(a.safety_state, 0.0) + (
                b.time_ns - a.time_ns
            ) / 1e9
        return {
            "peak_device_k": peak,
            "minimum_headroom_k": self.safety_policy.operating_limit_k - peak,
            "temperature_iae_k_s": temperature_iae,
            "temperature_ise_k2_s": temperature_ise,
            "temperature_overshoot_k": max(0.0, peak - target),
            "settling_time_s": settled_at,
            "dp_tracking_iae_pa_s": dp_iae,
            "pump_electrical_j": fsum(s.ledger.pump_electrical_j for s in self.steps),
            "control_total_variation": fsum(abs(b.pump_command - a.pump_command) for a, b in intervals),
            "actuator_tracking_iae_fraction_s": fsum(abs(a.pump_command - a.pump_measured) * (b.time_ns - a.time_ns) / 1e9 for a, b in intervals if a.pump_measured is not None),
            "saturation_duration_s": saturation_s,
            "max_mass_residual_kg_s": max(s.ledger.max_mass_volume_residual_kg_s for s in self.steps),
            "max_energy_residual_j": max(abs(s.ledger.full_loop_residual_j) for s in self.steps),
            "safety_event_count": len(self.events),
            "safety_fault_event_count": sum(1 for _, state, _ in self.events if state == "FAULT"),
            "safety_state_duration_s": safety_durations,
        }


def _with_branch_k(plant, multiplier):
    require(multiplier > 0, "DISTURBANCE", "branch K multiplier")
    graph = plant.hydraulic_graph
    branches = list(graph.branches)
    branch = list(branches[0])
    edge = branch[0]
    branch[0] = replace(edge, coefficient=p(edge.coefficient.name, 1e12 * multiplier, edge.coefficient.unit))
    branches[0] = tuple(branch)
    return replace(plant, hydraulic_graph=replace(graph, branches=tuple(branches)))


def run_feedback(
    plant, controls, duration_ns, clocks: ControlClocks, sensor_config: SensorConfig,
    actuator_config: PumpActuatorConfig, outer_config: OuterConfig,
    inner_config: InnerConfig, safety_policy: SafetyPolicy, disturbances=(),
):
    require(type(duration_ns) is int and duration_ns > 0, "CONTROL_RUN", "duration")
    require(tuple(x.time_ns for x in disturbances) == tuple(sorted({x.time_ns for x in disturbances})), "CONTROL_RUN", "strict disturbance times")
    original_plant = plant
    state = plant.initial_state
    actuator = PumpActuator(actuator_config, controls.speed_actual.value)
    sensor = LocalMeasurement(sensor_config)
    outer = OuterFeedback(outer_config)
    intent_supervisor = IntentSupervisor(safety_policy.fallback_dp_pa)
    plc = LocalDPPLC(inner_config)
    safety = SafetySupervisor(safety_policy)
    accepted_dp = safety_policy.fallback_dp_pa
    requested_dp = outer_config.base_dp_pa
    accepted_target = intent_supervisor.accept_target(None, 0)
    decision = None
    rows, steps = [], []
    cursor = 0
    now = 0
    released_sequence = -1
    held_plc_result = None
    released_measurements = []
    fb_intents = []
    while now <= duration_ns:
        while cursor < len(disturbances) and disturbances[cursor].time_ns == now:
            event = disturbances[cursor]
            if event.power_each_w is not None:
                controls = replace(controls, electrical_leaves=tuple(replace(x, power=p(x.source_id, event.power_each_w, "W")) for x in controls.electrical_leaves))
            if event.fws_inlet_k is not None:
                controls = replace(controls, fws_inlet_temperature=p("fws.inlet", event.fws_inlet_k, "K"))
            if event.primary_flow_kg_s is not None:
                controls = replace(controls, primary_mass_flow=p("fws.primary_m", event.primary_flow_kg_s, "kg/s"))
            if event.branch_zero_k_multiplier is not None:
                plant = _with_branch_k(original_plant, event.branch_zero_k_multiplier)
            if event.sensor_failures is not None:
                sensor.failed = set(event.sensor_failures)
            if event.pump_stuck is not None:
                actuator.fault_stuck = event.pump_stuck
            cursor += 1
        if now % sensor_config.sample_ns == 0:
            sensor.sample(now, plant, state, controls, actuator)
        measured = sensor.release(now)
        new_measurement = measured is not None and measured.sequence != released_sequence
        if new_measurement:
            released_sequence = measured.sequence
            released_measurements.append(measured)
        if now % clocks.outer_ns == 0 and measured is not None and measured.qualified("temperature", now, sensor_config.max_age_ns):
            intent = outer.update(now, measured, accepted_dp, sensor_config.max_age_ns)
            fb_intents.append(intent)
            accepted_target = intent_supervisor.accept_target(intent, now)
            requested_dp = accepted_target.requested_dp_pa
        elif outer.last_intent is not None:
            accepted_target = intent_supervisor.accept_target(outer.last_intent, now)
            requested_dp = accepted_target.requested_dp_pa
        if now % clocks.safety_ns == 0 or decision is None or new_measurement:
            decision = safety.evaluate(
                now,
                measured,
                sensor_config.max_age_ns,
                requested_dp,
                actuator.commanded,
                accepted_target_id=accepted_target.accepted_target_id,
            )
            accepted_dp = decision.accepted_dp_pa
        emergency = (
            new_measurement
            and decision.envelope.minimum_speed_fraction
            == decision.envelope.maximum_speed_fraction
        )
        if now % clocks.plc_ns == 0 or emergency:
            held_plc_result = plc.update(
                now,
                measured,
                accepted_target,
                decision.envelope,
                sensor_config.max_age_ns,
            )
            accepted_dp = held_plc_result.constrained_dp_pa
        if now % clocks.actuator_ns == 0 or emergency:
            require(held_plc_result is not None, "CONFIG_INVALID", "missing PLC command")
            actuator.command(held_plc_result.actuator_command, now)
        command = actuator.last_command
        measurement_id = getattr(measured, "measurement_record_id", "not_applicable")
        hydraulic_id = getattr(measured, "hydraulic_solution_id", "not_applicable")
        rows.append(ControlledRow(
            now,
            max(x.temperature_k for x in state.solids if x.node_id.endswith(":die")),
            max((t for _, t in measured.device_temperatures_k), default=None) if measured is not None else None,
            requested_dp, accepted_dp,
            measured.dp_pa if measured is not None else None,
            actuator.commanded, actuator.actual,
            measured.pump_speed if measured is not None else None,
            measured.flow_kg_s if measured is not None else None,
            steps[-1].ledger.pump_electrical_j if steps else 0.0,
            decision.state.value,
            steps[-1].ledger.max_mass_volume_residual_kg_s if steps else 0.0,
            steps[-1].ledger.full_loop_residual_j if steps else 0.0,
            outer.last_intent.intent_id if outer.last_intent is not None else "not_applicable",
            accepted_target.accepted_target_id,
            decision.envelope.envelope_id,
            held_plc_result.cycle.plc_cycle_id if held_plc_result is not None else "not_applicable",
            command.command_id if command is not None else "not_applicable",
            actuator.actuator_state_id,
            measurement_id,
            hydraulic_id,
            command.producer_module if command is not None else "not_applicable",
        ))
        if now == duration_ns:
            break
        deadlines = [duration_ns, now + clocks.physics_ns]
        for period in (sensor_config.sample_ns, clocks.outer_ns, clocks.plc_ns, clocks.actuator_ns, clocks.safety_ns):
            deadlines.append(((now // period) + 1) * period)
        if sensor.pending:
            deadlines.extend(r.available_ns for r in sensor.pending if r.available_ns > now)
        if actuator.pending:
            deadlines.extend(t for t, _, _ in actuator.pending if t > now)
        if cursor < len(disturbances):
            deadlines.append(disturbances[cursor].time_ns)
        end = min(x for x in deadlines if x > now)
        physical_controls = replace(controls, speed_actual=p("pump.speed_actual", actuator.actual, "fraction"))
        result = step(plant, state, physical_controls, end - now)
        if result.solver_status != SolverStatus.CONVERGED:
            raise ThermalError("CONTROLLED_PLANT_FAILED", "; ".join(result.diagnostics), result.validity_status)
        steps.append(result)
        state = result.next_state
        actuator.advance(now, end)
        now = end
    return ControlledRun(
        tuple(rows),
        tuple(steps),
        tuple(safety.events),
        outer_config,
        inner_config,
        clocks,
        sensor_config,
        actuator_config,
        safety_policy,
        tuple(fb_intents),
        tuple(intent_supervisor.targets),
        tuple(safety.envelopes),
        tuple(plc.cycles),
        tuple(plc.commands),
        tuple(actuator.state_history),
        tuple(released_measurements),
    )
