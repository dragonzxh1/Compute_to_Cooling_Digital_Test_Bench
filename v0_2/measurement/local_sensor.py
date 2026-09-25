"""Only this module receives physical truth and actuator actual state."""

from dataclasses import dataclass

from v0_2.hydraulics.solver import solve
from v0_2.thermal.validity import require


@dataclass(frozen=True)
class MeasuredSnapshot:
    sample_ns: int
    available_ns: int
    sequence: int
    device_temperatures_k: tuple[tuple[str, float], ...]
    dp_pa: float | None
    flow_kg_s: float | None
    pump_speed: float | None
    pump_running: bool | None
    pump_ready: bool | None
    pump_fault: bool | None
    quality: tuple[tuple[str, str], ...]
    layer: str = "MEASURED"
    measurement_record_id: str = "not_applicable"
    actuator_state_id: str = "not_applicable"
    hydraulic_solution_id: str = "not_applicable"
    producer_module: str = "MEASUREMENT"
    source_ids: tuple[str, ...] = ()

    def qualified(self, channel: str, now_ns: int, max_age_ns: int):
        return (
            self.available_ns <= now_ns
            and now_ns - self.sample_ns <= max_age_ns
            and dict(self.quality).get(channel) == "VALID"
        )


@dataclass(frozen=True)
class SensorConfig:
    sample_ns: int
    local_delay_ns: int
    max_age_ns: int = 1_000_000_000
    source: str = "NUMERICAL_TEST_FIXTURE/UNVALIDATED"

    def __post_init__(self):
        require(type(self.sample_ns) is int and self.sample_ns > 0, "SENSOR_CONFIG", "period")
        require(type(self.local_delay_ns) is int and self.local_delay_ns >= 0, "SENSOR_CONFIG", "delay")
        require(type(self.max_age_ns) is int and self.max_age_ns > 0, "SENSOR_CONFIG", "age")


class LocalMeasurement:
    def __init__(self, config: SensorConfig):
        self.config = config
        self.pending = []
        self.latest = None
        self.sequence = 0
        self.failed = set()

    def sample(self, now_ns, plant, state, controls, actuator):
        """Plant/ACTUAL references end here; consumers see only immutable records."""
        hydraulic = solve(
            plant.hydraulic_graph,
            plant.pump_curve,
            actuator.actual,
            plant.heat_exchanger.secondary_fluid.density.value,
        )
        temps = tuple((n.node_id, n.temperature_k) for n in state.solids if n.node_id.endswith(":die"))
        quality = tuple(
            (name, "MISSING" if name in self.failed else "VALID")
            for name in ("temperature", "dp", "flow", "pump_speed", "pump_status")
        )
        self.sequence += 1
        measurement_id = f"measurement:{now_ns}:{self.sequence}"
        actuator_state_id = actuator.actuator_state_id
        hydraulic_solution_id = f"hydraulic-solution:{now_ns}:{self.sequence}"
        record = MeasuredSnapshot(
            now_ns,
            now_ns + self.config.local_delay_ns,
            self.sequence,
            () if "temperature" in self.failed else temps,
            None if "dp" in self.failed else hydraulic.pump_head_pa,
            None if "flow" in self.failed else hydraulic.total_flow_m3_s * plant.heat_exchanger.secondary_fluid.density.value,
            None if "pump_speed" in self.failed else actuator.actual,
            None if "pump_status" in self.failed else actuator.actual > 0,
            None if "pump_status" in self.failed else not actuator.fault_stuck,
            None if "pump_status" in self.failed else actuator.fault_stuck,
            quality,
            "MEASURED",
            measurement_id,
            actuator_state_id,
            hydraulic_solution_id,
            "MEASUREMENT",
            (actuator_state_id, hydraulic_solution_id),
        )
        self.pending.append(record)

    def release(self, now_ns):
        due = [r for r in self.pending if r.available_ns <= now_ns]
        if due:
            self.latest = max(due, key=lambda r: (r.sample_ns, r.sequence))
        self.pending = [r for r in self.pending if r.available_ns > now_ns]
        return self.latest
