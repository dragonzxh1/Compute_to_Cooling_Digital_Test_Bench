from dataclasses import dataclass
from math import exp


@dataclass(frozen=True)
class CDUExchange:
    effectiveness: float
    heat_rejected_w: float
    secondary_outlet_temp_c: float
    primary_outlet_temp_c: float


def counterflow_effectiveness(capacity_hot_w_k: float, capacity_cold_w_k: float, ua_w_k: float):
    if capacity_hot_w_k <= 0 or capacity_cold_w_k <= 0 or ua_w_k <= 0:
        return 0.0
    c_min = min(capacity_hot_w_k, capacity_cold_w_k)
    c_max = max(capacity_hot_w_k, capacity_cold_w_k)
    ratio = c_min / c_max
    ntu = ua_w_k / c_min
    if abs(1.0 - ratio) < 1e-9:
        return ntu / (1.0 + ntu)
    decay = exp(-ntu * (1.0 - ratio))
    return (1.0 - decay) / (1.0 - ratio * decay)


def exchange(
    secondary_inlet_c: float,
    primary_inlet_c: float,
    secondary_mass_flow_kg_s: float,
    primary_mass_flow_kg_s: float,
    secondary_cp: float,
    primary_cp: float,
    ua_w_k: float,
) -> CDUExchange:
    c_hot = max(0.0, secondary_mass_flow_kg_s) * secondary_cp
    c_cold = max(0.0, primary_mass_flow_kg_s) * primary_cp
    epsilon = counterflow_effectiveness(c_hot, c_cold, ua_w_k)
    c_min = min(c_hot, c_cold)
    delta = max(0.0, secondary_inlet_c - primary_inlet_c)
    heat = min(epsilon * c_min * delta, c_hot * delta if c_hot else 0.0)
    secondary_out = secondary_inlet_c - heat / c_hot if c_hot else secondary_inlet_c
    primary_out = primary_inlet_c + heat / c_cold if c_cold else primary_inlet_c
    secondary_out = min(secondary_inlet_c, max(primary_inlet_c, secondary_out))
    primary_out = max(primary_inlet_c, min(secondary_inlet_c, primary_out))
    return CDUExchange(epsilon, max(0.0, heat), secondary_out, primary_out)
