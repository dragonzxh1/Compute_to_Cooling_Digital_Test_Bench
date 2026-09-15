def cold_plate_heat_w(plate_temp_c: float, coolant_temp_c: float, resistance_k_w: float) -> float:
    return max(0.0, (plate_temp_c - coolant_temp_c) / resistance_k_w)
