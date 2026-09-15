from c2c.thermal.rc_network import RCThermalModel, ThermalState

CFG = {
    "c_die_j_k": 18_000,
    "c_package_j_k": 108_000,
    "c_cold_plate_j_k": 500_000,
    "c_coolant_j_k": 1_250_000,
    "r_die_package_k_w": 0.00042,
    "r_package_plate_k_w": 0.00021,
    "r_plate_coolant_k_w": 0.00014,
}


def test_more_heat_initially_increases_die_temperature_more():
    initial = ThermalState(60, 50, 40, 32)
    low = RCThermalModel(CFG, initial).step(40_000, 30, 5, 4180, 1)
    high = RCThermalModel(CFG, initial).step(80_000, 30, 5, 4180, 1)
    assert high.gpu_die_temp_c > low.gpu_die_temp_c
