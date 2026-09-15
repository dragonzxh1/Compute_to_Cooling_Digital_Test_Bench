def pressure_drop_pa(flow_m3_s: float, resistance_k: float) -> float:
    return max(0.0, resistance_k * flow_m3_s**2)
