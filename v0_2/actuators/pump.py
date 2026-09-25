"""Deterministic actuator delay, first-order lag, ramp and faults."""

from dataclasses import dataclass
from math import exp

from v0_2.control.inner_loop import ActuatorCommand
from v0_2.thermal.validity import finite, require


@dataclass(frozen=True)
class PumpActuatorConfig:
    minimum: float
    maximum: float
    tau_s: float
    ramp_per_s: float
    command_delay_ns: int
    owner_id: str = "fixture_pump_vfd"
    meaning: str = "physical actuator response, not network/telemetry delay"
    source: str = "NUMERICAL_TEST_FIXTURE"
    provenance: str = "ENGINEERING_ASSUMPTION/UNVALIDATED"

    def __post_init__(self):
        for name in ("minimum", "maximum", "tau_s", "ramp_per_s"):
            finite(getattr(self, name), name)
        require(0 <= self.minimum < self.maximum <= 1, "ACTUATOR_CONFIG", "bounds")
        require(self.tau_s > 0 and self.ramp_per_s > 0, "ACTUATOR_CONFIG", "dynamics")
        require(type(self.command_delay_ns) is int and self.command_delay_ns >= 0, "ACTUATOR_CONFIG", "delay")
        require(bool(self.owner_id and self.meaning and self.source and self.provenance), "ACTUATOR_CONFIG", "delay provenance")


@dataclass(frozen=True)
class ActuatorState:
    actuator_state_id: str
    created_ns: int
    producer_module: str
    actuator_command_id: str
    commanded_speed: float
    actual_speed: float
    source_ids: tuple[str, ...]


class PumpActuator:
    def __init__(self, config: PumpActuatorConfig, initial: float):
        self.config = config
        self.actual = min(config.maximum, max(config.minimum, initial))
        self.commanded = self.actual
        self.target = self.actual
        self.pending = []
        self.saturation_events = []
        self.fault_stuck = False
        self.state_sequence = 0
        self.last_command = None
        self.state_history = []
        self.actuator_state_id = "actuator-state:initial"
        self.active_command_id = "not_applicable"

    def command(self, command: ActuatorCommand, now_ns: int):
        require(isinstance(command, ActuatorCommand), "ACTUATION_OWNERSHIP_VIOLATION", "typed PLC command required")
        require(command.producer_module == "PLC", "ACTUATION_OWNERSHIP_VIOLATION", command.command_id)
        require(command.created_ns == now_ns, "INVALID_TIME", "command creation/enqueue mismatch")
        value = command.applied_command_before_actuator_dynamics
        finite(value, "pump command")
        require(type(now_ns) is int and now_ns >= 0, "INVALID_TIME", "actuator command")
        bounded = min(self.config.maximum, max(self.config.minimum, value))
        if bounded != value:
            self.saturation_events.append((now_ns, value, bounded))
        self.commanded = bounded
        self.last_command = command
        self.pending.append((now_ns + self.config.command_delay_ns, bounded, command.command_id))

    def advance(self, start_ns: int, end_ns: int):
        require(type(start_ns) is int and type(end_ns) is int and end_ns > start_ns, "INVALID_TIME", "actuator interval")
        cursor = start_ns
        command_id = self.active_command_id
        for due, target, pending_command_id in sorted(self.pending):
            if due > end_ns:
                break
            if due > cursor:
                self._advance_segment((due - cursor) / 1e9)
                cursor = due
            self.target = target
            command_id = pending_command_id
            self.active_command_id = pending_command_id
        self.pending = [(t, v, command) for t, v, command in self.pending if t > end_ns]
        self._advance_segment((end_ns - cursor) / 1e9)
        self.state_sequence += 1
        self.actuator_state_id = f"actuator-state:{end_ns}:{self.state_sequence}"
        self.state_history.append(
            ActuatorState(
                self.actuator_state_id,
                end_ns,
                "ACTUATOR",
                command_id,
                self.commanded,
                self.actual,
                (command_id,) if command_id != "not_applicable" else (),
            )
        )
        return self.actual

    def _advance_segment(self, seconds: float):
        if self.fault_stuck or seconds <= 0:
            return
        exact = self.target + (self.actual - self.target) * exp(-seconds / self.config.tau_s)
        delta = min(self.config.ramp_per_s * seconds, max(-self.config.ramp_per_s * seconds, exact - self.actual))
        self.actual = min(self.config.maximum, max(self.config.minimum, self.actual + delta))
