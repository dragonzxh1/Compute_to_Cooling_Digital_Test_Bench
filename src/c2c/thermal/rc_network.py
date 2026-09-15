from dataclasses import dataclass


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

    def smallest_time_constant_s(self) -> float:
        c = self.cfg
        return min(
            c["c_die_j_k"] * c["r_die_package_k_w"],
            c["c_package_j_k"] * c["r_package_plate_k_w"],
            c["c_cold_plate_j_k"] * c["r_plate_coolant_k_w"],
        )

    def step(
        self,
        heat_w: float,
        supply_temp_c: float,
        mass_flow_kg_s: float,
        cp_j_kgk: float,
        dt_s: float,
    ) -> ThermalState:
        if dt_s > self.smallest_time_constant_s() / 2.0:
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
        self.state = next_state
        return next_state


def steady_initial_state(heat_w: float, supply_c: float, mass_flow: float, cp: float, cfg: dict):
    coolant = supply_c + heat_w / max(mass_flow * cp, 1.0)
    plate = coolant + heat_w * cfg["r_plate_coolant_k_w"]
    package = plate + heat_w * cfg["r_package_plate_k_w"]
    die = package + heat_w * cfg["r_die_package_k_w"]
    return ThermalState(die, package, plate, coolant)
