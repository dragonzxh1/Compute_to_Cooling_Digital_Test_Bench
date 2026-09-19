from dataclasses import dataclass
from math import fsum

from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import ValidityStatus, finite, require


@dataclass(frozen=True)
class PumpCurve:
    shutoff_head_pa: ParameterRecord
    curve_k: ParameterRecord
    speed_range: tuple[float, float]
    flow_range_m3_s: tuple[float, float]
    provenance: ParameterRecord

    def __post_init__(self):
        require(self.shutoff_head_pa.si("Pa") > 0, "PUMP_MAP", "shutoff head")
        require(self.curve_k.si("Pa/(m3/s)^2") >= 0, "PUMP_MAP", "curve K")
        require(0 <= self.speed_range[0] < self.speed_range[1], "PUMP_MAP", "speed range")
        require(0 <= self.flow_range_m3_s[0] < self.flow_range_m3_s[1], "PUMP_MAP", "flow range")

    def head(self, flow_m3_s, actual_speed):
        finite(actual_speed, "pump speed")
        finite(flow_m3_s, "pump flow")
        require(
            self.speed_range[0] <= actual_speed <= self.speed_range[1],
            "PUMP_SPEED_OUT_OF_RANGE",
            str(actual_speed),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        require(
            self.flow_range_m3_s[0] <= flow_m3_s <= self.flow_range_m3_s[1],
            "PUMP_FLOW_OUT_OF_RANGE",
            str(flow_m3_s),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        head = self.shutoff_head_pa.value * actual_speed**2 - self.curve_k.value * flow_m3_s**2
        require(head >= 0, "PUMP_MAP_NEGATIVE", str(head), ValidityStatus.MODEL_INVALID)
        return head


@dataclass(frozen=True)
class PumpDrive:
    vfd_efficiency: ParameterRecord
    motor_efficiency: ParameterRecord
    pump_efficiency: ParameterRecord
    vfd_liquid_fraction: ParameterRecord
    motor_liquid_fraction: ParameterRecord
    internal_liquid_fraction: ParameterRecord
    liquid_receiver_id: str
    provenance: ParameterRecord
    standby_electrical_w: ParameterRecord

    def __post_init__(self):
        for p in (self.vfd_efficiency, self.motor_efficiency, self.pump_efficiency):
            require(0 < p.si("fraction") <= 1, "PUMP_EFFICIENCY", p.name)
        for p in (
            self.vfd_liquid_fraction,
            self.motor_liquid_fraction,
            self.internal_liquid_fraction,
        ):
            require(0 <= p.si("fraction") <= 1, "LOSS_DESTINATION", p.name)
        require(bool(self.liquid_receiver_id), "LOSS_DESTINATION", "pump liquid receiver")
        require(self.standby_electrical_w.si("W") >= 0, "PUMP_STANDBY", "standby power")


@dataclass(frozen=True)
class PumpEnergy:
    electrical_w: float
    hydraulic_w: float
    vfd_loss_w: float
    motor_loss_w: float
    internal_loss_w: float
    efficiency_total: float | None
    loss_to_liquid_w: float
    loss_to_ambient_w: float
    electrical_energy_j: float


def pump_energy(drive, head_pa, flow_m3_s, dt_s):
    finite(head_pa, "pump head")
    finite(flow_m3_s, "pump flow")
    require(
        head_pa >= 0 and flow_m3_s >= 0 and dt_s > 0,
        "PUMP_MAP",
        "motoring only",
        ValidityStatus.MODEL_INVALID,
    )
    hydraulic = head_pa * flow_m3_s
    if hydraulic == 0:
        standby = drive.standby_electrical_w.value
        liquid = standby * drive.vfd_liquid_fraction.value
        return PumpEnergy(
            standby,
            0.0,
            standby,
            0.0,
            0.0,
            0.0 if standby else None,
            liquid,
            standby - liquid,
            standby * dt_s,
        )
    shaft = hydraulic / drive.pump_efficiency.value
    motor_input = shaft / drive.motor_efficiency.value
    electrical = motor_input / drive.vfd_efficiency.value
    internal = shaft - hydraulic
    motor = motor_input - shaft
    vfd = electrical - motor_input
    liquid = fsum(
        (
            vfd * drive.vfd_liquid_fraction.value,
            motor * drive.motor_liquid_fraction.value,
            internal * drive.internal_liquid_fraction.value,
        )
    )
    ambient = fsum((vfd, motor, internal)) - liquid
    require(
        abs(electrical - fsum((hydraulic, vfd, motor, internal))) <= max(1e-6, 1e-9 * electrical),
        "PUMP_ENERGY_BALANCE_FAIL",
        "drive closure",
    )
    return PumpEnergy(
        electrical,
        hydraulic,
        vfd,
        motor,
        internal,
        hydraulic / electrical if electrical else None,
        liquid,
        ambient,
        electrical * dt_s,
    )
