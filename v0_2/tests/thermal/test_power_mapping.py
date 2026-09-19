from dataclasses import replace

import pytest
from v0_2.thermal.fixtures import insulated, leaf, node
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import ThermalIntegrator
from v0_2.thermal.nodes import NodeType
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.source_mapping import PowerLeaf, PowerSourceMap, allocate_parent
from v0_2.thermal.state import ThermalState
from v0_2.thermal.topology import ThermalTopology
from v0_2.thermal.validity import ThermalError


def budget(hbm_w=200.0):
    parent = PowerLeaf(
        "board", "BOARD_POWER", p("board", 1200.0, "W"), frozenset({"gpu", "hbm", "vrm"})
    )
    hbm = PowerLeaf(
        "hbm", "HBM", p("hbm", hbm_w, "W"), frozenset({"hbm"}), ("board",), "MEASURED_DIRECT"
    )
    specs = (
        ("gpu", "GPU_DIE", frozenset({"gpu"}), p("gpu_fraction", 0.8, "fraction")),
        ("vrm", "VRM_BOARD", frozenset({"vrm"}), p("vrm_fraction", 0.2, "fraction")),
    )
    return parent, hbm, specs


def test_board_parent_hbm_child_single_receipts():
    parent, hbm, specs = budget()
    leaves = allocate_parent(parent, (hbm,), specs)
    assert sum(l.power.value for l in leaves) == 1200.0
    assert next(l for l in leaves if l.source_id == "gpu").value_origin == "ALLOCATED_FROM_PARENT"
    nodes = {
        n.node_id: n
        for n in (node("gpu"), node("hbm", NodeType.HBM), node("vrm", NodeType.VRM_BOARD))
    }
    mapping = PowerSourceMap(tuple((l.source_id, l.source_id) for l in leaves))
    receipts = mapping.receipts(leaves, nodes, 0, 200_000_000)
    assert sum(r.energy_j for r in receipts) == 240.0
    with pytest.raises(ThermalError, match="POWER_DOMAIN_OVERLAP|BOARD_REQUIRES_ALLOCATION"):
        PowerSourceMap((*(mapping.assignments), ("board", "gpu"))).validate(
            (parent, *leaves), nodes
        )


def test_board_not_die_even_without_children():
    parent, _, _ = budget()
    with pytest.raises(ThermalError, match="BOARD_REQUIRES_ALLOCATION"):
        PowerSourceMap((("board", "die"),)).validate((parent,), {"die": node("die")})


def test_child_exceeds_parent_fails():
    parent, hbm, specs = budget(1300.0)
    with pytest.raises(ThermalError, match="POWER_DOMAIN_BALANCE_FAIL"):
        allocate_parent(parent, (hbm,), specs)


def test_stale_child_window_fails():
    parent, hbm, specs = budget()
    with pytest.raises(ThermalError, match="time mismatch"):
        allocate_parent(parent, (replace(hbm, sample_time_ns=1),), specs)


@pytest.mark.parametrize(
    "assignments", [(("power", "die"), ("power", "die")), (), (("power", "missing"),)]
)
def test_duplicate_missing_or_bad_target(assignments):
    f = insulated()
    with pytest.raises(ThermalError):
        PowerSourceMap(assignments).validate(f.sources, f.topology.initial_state.by_id())


def test_extra_mapping_is_rejected():
    f = insulated()
    with pytest.raises(ThermalError, match="INCOMPLETE_SOURCE_MAP"):
        PowerSourceMap((("power", "die"), ("unexpected", "die"))).validate(
            f.sources, f.topology.initial_state.by_id()
        )


def test_alias_coverage_and_wrong_node_kind_rejected():
    f = insulated()
    with pytest.raises(ThermalError, match="POWER_DOMAIN_OVERLAP"):
        PowerSourceMap((("power", "die"), ("alias", "die"))).validate(
            (*f.sources, replace(f.sources[0], source_id="alias")), f.topology.initial_state.by_id()
        )
    with pytest.raises(ThermalError, match="SOURCE_DOMAIN_MISMATCH"):
        f.source_map.validate((leaf(kind="HBM"),), f.topology.initial_state.by_id())


def test_small_gpu_cpu_topology():
    f = insulated()
    state = ThermalState(
        (node("gpu", adiabatic=True), node("cpu", NodeType.CPU_DIE, capacity=200, adiabatic=True))
    )
    f = replace(
        f,
        topology=ThermalTopology(state, (), (("gpu_cv", ("gpu",)), ("cpu_cv", ("cpu",)))),
        sources=(leaf("gpu_p", 100), leaf("cpu_p", 50, "CPU_DIE")),
        source_map=PowerSourceMap((("gpu_p", "gpu"), ("cpu_p", "cpu"))),
    )
    result = run(f, 1_000_000_000, 100_000_000)
    assert result.final_state.nodes[0].temperature_k == pytest.approx(301.0)
    assert result.final_state.nodes[1].temperature_k == pytest.approx(300.25)
    assert result.metrics()["input_j"] == 150.0


def test_future_source_failure_does_not_commit():
    f = insulated()
    solver = ThermalIntegrator(f.topology, f.source_map)
    state = f.topology.initial_state
    result = solver.step(state, (replace(f.sources[0], sample_time_ns=1),), {}, (), {}, 0, 1000)
    assert result.next_state is state and not result.accepted_substeps
