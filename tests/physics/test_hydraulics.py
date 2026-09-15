import pytest

from c2c.hydraulics.pump import PumpSystem

CFG = {
    "system_k_pa_s2_m6": 2.0e9,
    "pump_k_pa_s2_m6": 5.0e8,
    "pump_shutoff_dp_pa": 130_000,
    "pump_efficiency": 0.72,
}


def test_affinity_law_scaling_and_positive_power():
    pump = PumpSystem(CFG)
    half, full = pump.operating_point(50), pump.operating_point(100)
    assert full.flow_m3_s / half.flow_m3_s == pytest.approx(2.0)
    assert full.dp_pa / half.dp_pa == pytest.approx(4.0)
    assert full.pump_power_w / half.pump_power_w == pytest.approx(8.0)
    assert half.pump_power_w >= 0
