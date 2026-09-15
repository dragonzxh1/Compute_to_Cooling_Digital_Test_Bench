from dataclasses import dataclass
from math import sqrt

from c2c.hydraulics.resistance import pressure_drop_pa


@dataclass(frozen=True)
class HydraulicState:
    flow_m3_s: float
    dp_pa: float
    pump_power_w: float


class PumpSystem:
    def __init__(self, config: dict):
        self.system_k = float(config["system_k_pa_s2_m6"])
        self.pump_k = float(config["pump_k_pa_s2_m6"])
        self.shutoff_pa = float(config["pump_shutoff_dp_pa"])
        self.efficiency = float(config["pump_efficiency"])

    def operating_point(self, speed_pct: float) -> HydraulicState:
        speed = min(1.0, max(0.0, speed_pct / 100.0))
        flow = speed * sqrt(self.shutoff_pa / (self.system_k + self.pump_k))
        dp = pressure_drop_pa(flow, self.system_k)
        power = dp * flow / max(self.efficiency, 1e-6)
        return HydraulicState(flow, dp, max(0.0, power))

    def dp_for_flow_kpa(self, flow_m3_s: float) -> float:
        return pressure_drop_pa(flow_m3_s, self.system_k) / 1000.0
