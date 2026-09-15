from dataclasses import dataclass

from c2c.controls.guardrails import clamp
from c2c.core.telemetry import HeatLoad


@dataclass(frozen=True)
class SupervisoryIntent:
    timestamp_s: float
    predicted_heat_kw: float
    recommended_supply_temp_setpoint_c: float
    recommended_flow_m3_s: float
    recommended_dp_kpa: float
    predicted_cooling_requirement_kw: float


class ShadowLCI:
    def __init__(self, config: dict, hydraulic_model, density_kg_m3: float, cp_j_kgk: float):
        self.cfg = config
        self.hydraulics = hydraulic_model
        self.rho = density_kg_m3
        self.cp = cp_j_kgk

    def recommend(self, t_s: float, heat: HeatLoad) -> SupervisoryIntent:
        predicted = heat.liquid_heat_w
        target_dt = self.cfg["target_delta_t_k"]
        required_mass_flow = predicted / max(self.cp * target_dt, 1.0)
        required_flow = required_mass_flow / self.rho
        dp_kpa = clamp(
            self.hydraulics.dp_for_flow_kpa(required_flow),
            self.cfg.get("min_dp_setpoint_kpa", 35.0),
            self.cfg.get("max_dp_setpoint_kpa", 95.0),
        )
        load_fraction = clamp(predicted / 110_000.0, 0.0, 1.2)
        supply_sp = clamp(
            30.5 - 4.5 * load_fraction,
            self.cfg["min_supply_setpoint_c"],
            self.cfg["max_supply_setpoint_c"],
        )
        return SupervisoryIntent(
            timestamp_s=t_s,
            predicted_heat_kw=predicted / 1000.0,
            recommended_supply_temp_setpoint_c=supply_sp,
            recommended_flow_m3_s=required_flow,
            recommended_dp_kpa=dp_kpa,
            predicted_cooling_requirement_kw=predicted / 1000.0,
        )
