from dataclasses import replace
from math import fsum

import pytest
from v0_2.thermal.energy_ledger import cumulative_balances
from v0_2.thermal.fixtures import gpu_chain, insulated, resistor
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import Method
from v0_2.thermal.state import ThermalState
from v0_2.thermal.topology import ThermalTopology
from v0_2.thermal.validity import ThermalError


@pytest.mark.parametrize("method", list(Method))
def test_all_node_device_subsystem_ledgers(method):
    r = run(gpu_chain(with_hbm=True), 10_000_000_000, 100_000_000, method)
    for s in r.substeps:
        assert all(b.passed for b in s.ledger.balances)
        parts = [s.ledger.balance(cv) for cv in ("device", "node:plate", "node:coolant")]
        subsystem = s.ledger.balance("subsystem")
        for field in ("stored_change_j", "source_energy_j", "exported_energy_j", "residual_j"):
            assert fsum(getattr(p, field) for p in parts) == pytest.approx(
                getattr(subsystem, field), abs=1e-10
            )
        for flux in s.ledger.interfaces:
            if flux.cold_node_id is not None:
                assert fsum(value for _, value in flux.node_postings) == 0.0
    assert all(v["passed"] for v in cumulative_balances([s.ledger for s in r.substeps]).values())
    m = r.metrics()
    assert m["input_j"] == 1500.0
    assert m["stored_j"] + m["air_j"] + m["liquid_j"] == pytest.approx(1500.0, abs=1e-6)
    assert m["plate_to_liquid_j"] != m["liquid_j"]  # local water stores the difference


def test_duplicate_storage_owner_rejected():
    nodes = gpu_chain().topology.initial_state.nodes
    with pytest.raises(ThermalError, match="DUPLICATE_STORAGE_OR_NODE"):
        ThermalState((nodes[0], replace(nodes[1], storage_owner_id=nodes[0].storage_owner_id)))


@pytest.mark.parametrize("duplicate", ["interface_id", "owner_id"])
def test_duplicate_interface_identity_rejected(duplicate):
    f = gpu_chain()
    edge = replace(
        f.topology.interfaces[1],
        **{duplicate: getattr(f.topology.interfaces[0], duplicate)},
    )
    with pytest.raises(ThermalError, match="DUPLICATE_INTERFACE_OWNER"):
        replace(f.topology, interfaces=(f.topology.interfaces[0], edge, *f.topology.interfaces[2:]))


def test_prescribed_boundary_cannot_also_be_dynamic():
    f = gpu_chain()
    edge = resistor("bad", "die", "coolant", 0.1, boundary=True, medium="LIQUID")
    with pytest.raises(ThermalError, match="BOUNDARY_STORAGE_CONFLICT"):
        ThermalTopology(
            f.topology.initial_state, (*f.topology.interfaces, edge), f.topology.device_cvs
        )


def test_explicit_air_reverse_flux_enters_node():
    f = insulated(power=0)
    edge = resistor("warm_air", "die", "air", 0.5, boundary=True, medium="AIR")
    from v0_2.thermal.provenance import fixture_parameter as p

    f = replace(
        f,
        topology=ThermalTopology(f.topology.initial_state, (edge,), f.topology.device_cvs),
        boundaries=(("air", p("warm_air", 320.0, "K")),),
    )
    m = run(f, 1_000_000_000, 100_000_000).metrics()
    assert m["air_j"] < 0 and m["stored_j"] > 0 and abs(m["residual_j"]) < 1e-7
