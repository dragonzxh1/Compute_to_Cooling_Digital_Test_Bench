from dataclasses import dataclass
from math import isfinite


@dataclass
class ThermalState:
    gpu_die_temp_c: float
    package_temp_c: float
    cold_plate_temp_c: float
    coolant_return_temp_c: float


class RCThermalModel:
    """Four-node aggregate heat path with coolant advection to supply."""

    def __init__(self, config: dict, initial: ThermalState):
        self.cfg = config
        self.state = initial

    def smallest_time_constant_s(self, mass_flow_kg_s: float = 0, cp_j_kgk: float = 0) -> float:
        c = self.cfg
        g1 = 1 / c["r_die_package_k_w"]
        g2 = 1 / c["r_package_plate_k_w"]
        g3 = 1 / c["r_plate_coolant_k_w"]
        return min(
            c["c_die_j_k"] / g1,
            c["c_package_j_k"] / (g1 + g2),
            c["c_cold_plate_j_k"] / (g2 + g3),
            c["c_coolant_j_k"] / (g3 + mass_flow_kg_s * cp_j_kgk),
        )

    def step(
        self,
        heat_w: float,
        supply_temp_c: float,
        mass_flow_kg_s: float,
        cp_j_kgk: float,
        dt_s: float,
    ) -> ThermalState:
        if not all(isfinite(v) for v in (heat_w, supply_temp_c, mass_flow_kg_s, cp_j_kgk, dt_s)):
            raise ValueError("thermal inputs must be finite")
        if dt_s <= 0 or mass_flow_kg_s < 0 or cp_j_kgk <= 0:
            raise ValueError("dt and heat capacity must be positive; flow must be non-negative")
        if dt_s > self.smallest_time_constant_s(mass_flow_kg_s, cp_j_kgk) / 2.0:
            raise ValueError("dt_s is too large for stable explicit RC integration")
        s, c = self.state, self.cfg
        q_die_package = (s.gpu_die_temp_c - s.package_temp_c) / c["r_die_package_k_w"]
        q_package_plate = (s.package_temp_c - s.cold_plate_temp_c) / c["r_package_plate_k_w"]
        q_plate_coolant = (s.cold_plate_temp_c - s.coolant_return_temp_c) / c["r_plate_coolant_k_w"]
        q_advected = max(0.0, mass_flow_kg_s) * cp_j_kgk * (s.coolant_return_temp_c - supply_temp_c)
        next_state = ThermalState(
            gpu_die_temp_c=s.gpu_die_temp_c + dt_s * (heat_w - q_die_package) / c["c_die_j_k"],
            package_temp_c=s.package_temp_c
            + dt_s * (q_die_package - q_package_plate) / c["c_package_j_k"],
            cold_plate_temp_c=s.cold_plate_temp_c
            + dt_s * (q_package_plate - q_plate_coolant) / c["c_cold_plate_j_k"],
            coolant_return_temp_c=s.coolant_return_temp_c
            + dt_s * (q_plate_coolant - q_advected) / c["c_coolant_j_k"],
        )
        if not all(isfinite(v) for v in vars(next_state).values()):
            raise ValueError("thermal integration produced non-finite temperatures")
        self.state = next_state
        return next_state


def steady_initial_state(heat_w: float, supply_c: float, mass_flow: float, cp: float, cfg: dict):
    coolant = supply_c + heat_w / max(mass_flow * cp, 1.0)
    plate = coolant + heat_w * cfg["r_plate_coolant_k_w"]
    package = plate + heat_w * cfg["r_package_plate_k_w"]
    die = package + heat_w * cfg["r_die_package_k_w"]
    return ThermalState(die, package, plate, coolant)
