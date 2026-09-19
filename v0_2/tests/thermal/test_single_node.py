from dataclasses import replace

import pytest
from v0_2.thermal.fixtures import gpu_chain, insulated, node
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import Method
from v0_2.thermal.nodes import NodeType
from v0_2.thermal.validity import ThermalError


@pytest.mark.parametrize("method", list(Method))
def test_zero_input_equilibrium(method):
    f = gpu_chain(power=0.0)
    r = run(f, 1_000_000_000, 100_000_000, method)
    assert all(n.temperature_k == 300.0 and n.energy_j == 0.0 for n in r.final_state.nodes)
    assert r.metrics()["residual_j"] == 0


@pytest.mark.parametrize("method", list(Method))
def test_insulated_constant_power_analytic(method):
    r = run(insulated(100.0), 10_000_000_000, 200_000_000, method)
    assert r.final_state.nodes[0].temperature_k == pytest.approx(310.0, abs=1e-10)
    assert r.final_state.nodes[0].energy_j == pytest.approx(1000.0, abs=1e-8)
    assert r.metrics()["energy_pass"]


@pytest.mark.parametrize("kind", list(NodeType))
def test_node_kinds_and_reference_energy(kind):
    n = node("n", kind, temperature=310.0)
    assert n.energy_j == 1000.0
    assert n.enthalpy_law.temperature(n.energy_j, 300.0) == 310.0


def test_coolant_storage_mass_cp():
    n = node("water", NodeType.LOCAL_COOLANT, 2000.0)
    assert n.mass_kg.value * n.specific_heat.value == n.thermal_capacitance.value
    with pytest.raises(ThermalError, match="COOLANT_STORAGE"):
        replace(
            n,
            mass_kg=n.mass_kg.__class__(
                "m",
                1.0,
                "kg",
                "ENGINEERING_ASSUMPTION",
                "test",
                0.0,
                "2026-09-18",
                (1.0, 1.0),
                "UNVALIDATED",
            ),
        )


def test_temperature_energy_consistency():
    with pytest.raises(ThermalError, match="INCONSISTENT_ENERGY"):
        replace(node("die"), energy_j=50.0)
