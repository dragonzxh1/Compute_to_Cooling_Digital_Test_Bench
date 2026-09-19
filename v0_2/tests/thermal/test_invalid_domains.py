from dataclasses import replace

import pytest
from v0_2.thermal.fixtures import coldplate_model, gpu_chain, insulated, node, resistor
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import ThermalIntegrator
from v0_2.thermal.interfaces import InterfaceKind
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.state import ThermalState
from v0_2.thermal.topology import ThermalTopology
from v0_2.thermal.validity import SolverStatus, ThermalError


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_capacitance(value):
    with pytest.raises((ThermalError, ValueError)):
        node("bad", capacity=value)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_resistance(value):
    with pytest.raises(ThermalError):
        resistor("bad", "a", "b", value)


def test_duplicate_node_and_unknown_endpoint():
    n = node("n")
    with pytest.raises(ThermalError, match="DUPLICATE_STORAGE_OR_NODE"):
        ThermalState((n, n))
    f = gpu_chain()
    with pytest.raises(ThermalError, match="MISSING_ENDPOINT"):
        ThermalTopology(
            f.topology.initial_state,
            (*f.topology.interfaces, resistor("missing", "die", "absent", 0.1)),
            (),
        )


@pytest.mark.parametrize("bounds", [(0.0, 0.0), (0.5, 0.01), (-0.1, 0.5)])
def test_invalid_flow_range(bounds):
    with pytest.raises(ThermalError, match="INVALID_RANGE"):
        replace(coldplate_model(), flow_range=bounds)


def test_material_temperature_range():
    with pytest.raises(ThermalError, match="INVALID_RANGE"):
        replace(node("n"), valid_temperature_range=(500.0, 200.0))


@pytest.mark.parametrize("medium", ["AIR", "LIQUID", "OTHER"])
def test_internal_flux_cannot_be_mislabeled_external(medium):
    with pytest.raises(ThermalError, match="INTERFACE"):
        replace(resistor("ab", "a", "b", 0.1), boundary_medium=medium)


def test_prescribed_boundary_cannot_own_dynamic_endpoint():
    with pytest.raises(ThermalError, match="INTERFACE"):
        replace(resistor("ab", "a", "b", 0.1), kind=InterfaceKind.PRESCRIBED_BOUNDARY)


def test_no_provenance_promotion_after_success():
    f = insulated()
    result = run(f, 1_000_000_000, 100_000_000)
    assert result.final_state.nodes[0].calibration_status == "UNVALIDATED"
    assert f.sources[0].power.source_type == "ENGINEERING_ASSUMPTION"
    with pytest.raises(ThermalError, match="PROVENANCE"):
        replace(f.sources[0].power, source_type="GB300_OFFICIAL")


@pytest.mark.parametrize("dt", [0, -1, 999, 1.5])
def test_bad_time_does_not_commit(dt):
    f = insulated()
    result = ThermalIntegrator(f.topology, f.source_map).step(
        f.topology.initial_state, f.sources, {}, (), {}, 0, dt
    )
    assert result.solver_status == SolverStatus.FAILED
    assert result.next_state is f.topology.initial_state


def test_missing_or_wrong_unit_boundary():
    f = gpu_chain()
    solver = ThermalIntegrator(f.topology, f.source_map)
    result = solver.step(
        f.topology.initial_state,
        f.sources,
        {},
        f.topology.interfaces,
        dict(f.flows),
        0,
        100_000_000,
    )
    assert result.solver_status == SolverStatus.FAILED


def test_wrong_unit_boundary_rejected():
    f = gpu_chain()
    solver = ThermalIntegrator(f.topology, f.source_map)
    bounds = dict(f.boundaries)
    bounds["bath"] = p("wrong", 300, "degC")
    result = solver.step(
        f.topology.initial_state,
        f.sources,
        bounds,
        f.topology.interfaces,
        dict(f.flows),
        0,
        100_000_000,
    )
    assert result.solver_status == SolverStatus.FAILED


def test_node_properties_cannot_change_between_steps():
    f = insulated()
    changed = ThermalState((replace(f.topology.initial_state.nodes[0], storage_owner_id="other"),))
    result = ThermalIntegrator(f.topology, f.source_map).step(
        changed, f.sources, {}, (), {}, 0, 1000
    )
    assert result.solver_status == SolverStatus.FAILED
    assert result.next_state is changed
    assert any("STATE_TOPOLOGY" in message for message in result.diagnostics)
