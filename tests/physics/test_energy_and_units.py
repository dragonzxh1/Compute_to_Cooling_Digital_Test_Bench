import pandas as pd
import pytest

from c2c.compute.heat import ComputeToHeatModel
from c2c.core.telemetry import ComputeTelemetry
from c2c.core.units import m3h_to_m3s, m3s_to_m3h
from c2c.reports.metrics import _integrate_kwh


def test_heat_split_closes():
    model = ComputeToHeatModel(
        {"cpu_power_w": 100.0, "other_power_w": 50.0},
        {"alpha_gpu": 0.9, "alpha_cpu": 0.5, "alpha_other": 0.2},
    )
    heat = model.step(ComputeTelemetry(timestamp_s=0, gpu_power_w=1000, gpu_util_pct=50))
    assert heat.liquid_heat_w + heat.air_residual_heat_w == pytest.approx(1150.0)
    assert heat.liquid_heat_w == pytest.approx(960.0)


def test_flow_unit_round_trip():
    assert m3s_to_m3h(m3h_to_m3s(42.0)) == pytest.approx(42.0)


def test_energy_integration_does_not_count_both_interval_endpoints():
    power_kw = pd.Series([1.0, 1.0, 1.0])
    timestamps_s = pd.Series([0.0, 1.0, 2.0])
    assert _integrate_kwh(power_kw, timestamps_s) == pytest.approx(2.0 / 3600.0)
