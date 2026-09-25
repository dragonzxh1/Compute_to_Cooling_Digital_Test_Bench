"""Local measured-DP PLC controller."""

from dataclasses import dataclass

from v0_2.control.intent import AcceptedTarget
from v0_2.control.pid import PIDConfig, TrackingPID
from v0_2.safety.supervisor import SafetyEnvelope
from v0_2.thermal.validity import require


@dataclass(frozen=True)
class InnerConfig:
    pid: PIDConfig


@dataclass(frozen=True)
class ActuatorCommand:
    command_id: str
    created_ns: int
    producer_module: str
    plc_cycle_id: str
    accepted_target_id: str
    safety_envelope_id: str
    requested_speed: float
    applied_command_before_actuator_dynamics: float
    reason: str
    mode: str
    source_ids: tuple[str, ...]

    def __post_init__(self):
        require(self.producer_module == "PLC", "ACTUATION_OWNERSHIP_VIOLATION", self.command_id)
        require(bool(self.plc_cycle_id), "CONFIG_INVALID", "missing plc_cycle_id")


@dataclass(frozen=True)
class PLCCycle:
    plc_cycle_id: str
    created_ns: int
    producer_module: str
    accepted_target_id: str
    safety_envelope_id: str
    measurement_record_id: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class PLCCommandResult:
    cycle: PLCCycle
    actuator_command: ActuatorCommand
    constrained_dp_pa: float


class LocalDPPLC:
    def __init__(self, config: InnerConfig):
        self.config = config
        self.pid = TrackingPID(config.pid)
        self.command = 0.0
        self.sequence = 0
        self.cycles = []
        self.commands = []

    def update(
        self,
        now_ns,
        measured,
        accepted_target: AcceptedTarget,
        envelope: SafetyEnvelope,
        max_age_ns,
    ) -> PLCCommandResult:
        require(envelope.accepted_target_id == accepted_target.accepted_target_id, "CONFIG_INVALID", "target/envelope provenance")
        constrained_dp_pa = min(
            envelope.maximum_dp_pa,
            max(envelope.minimum_dp_pa, accepted_target.requested_dp_pa),
        )
        exact_safe_speed = (
            envelope.minimum_speed_fraction
            if envelope.minimum_speed_fraction == envelope.maximum_speed_fraction
            else None
        )
        if exact_safe_speed is not None:
            error = 0.0 if measured is None or measured.dp_pa is None else constrained_dp_pa - measured.dp_pa
            self.command = self.pid.update(error, exact_safe_speed, automatic=False)
            requested_speed = exact_safe_speed
            reason = "SAFETY_EXACT_SPEED_ENVELOPE"
            mode = "EMERGENCY" if envelope.state.value in ("FAULT", "PROTECTED") else "RESTRICTED"
        else:
            require(
                measured is not None
                and measured.qualified("dp", now_ns, max_age_ns)
                and measured.qualified("pump_speed", now_ns, max_age_ns)
                and measured.dp_pa is not None
                and measured.pump_speed is not None,
                "PLC_MEASUREMENT", "released local DP/speed required",
            )
            unconstrained = self.pid.update(constrained_dp_pa - measured.dp_pa, measured.pump_speed)
            requested_speed = min(
                envelope.maximum_speed_fraction,
                max(envelope.minimum_speed_fraction, unconstrained),
            )
            self.command = requested_speed
            reason = "NORMAL_DP_FEEDBACK"
            mode = "NORMAL"
        self.sequence += 1
        cycle_id = f"plc-cycle:{now_ns}:{self.sequence}"
        measurement_id = getattr(measured, "measurement_record_id", "not_applicable")
        cycle = PLCCycle(
            cycle_id,
            now_ns,
            "PLC",
            accepted_target.accepted_target_id,
            envelope.envelope_id,
            measurement_id,
            (
                accepted_target.accepted_target_id,
                envelope.envelope_id,
                measurement_id,
            ),
        )
        command = ActuatorCommand(
            f"actuator-command:{now_ns}:{self.sequence}",
            now_ns,
            "PLC",
            cycle_id,
            accepted_target.accepted_target_id,
            envelope.envelope_id,
            requested_speed,
            requested_speed,
            reason,
            mode,
            (cycle_id, accepted_target.accepted_target_id, envelope.envelope_id),
        )
        self.cycles.append(cycle)
        self.commands.append(command)
        return PLCCommandResult(cycle, command, constrained_dp_pa)
