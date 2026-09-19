from dataclasses import replace
from math import fsum, sqrt

import pytest
from v0_2.hydraulics.pump import PumpDrive, pump_energy
from v0_2.hydraulics.solver import solve
from v0_2.plant.fixtures import physical_fixture
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import ThermalError, ValidityStatus


def test_single_edge_signed_quadratic_pressure():
    edge = physical_fixture()[0].hydraulic_graph.branches[0][0]
    edge = replace(edge, reverse_supported=True)
    q = 0.0001
    assert edge.drop_pa(q) == pytest.approx(1e4)
    assert edge.drop_pa(-q) == pytest.approx(-1e4)
    with pytest.raises(ThermalError, match="REVERSE_FLOW"):
        replace(edge, reverse_supported=False).drop_pa(-q)


@pytest.mark.parametrize("count", [1, 2, 4])
def test_equal_parallel_branches_share_pressure_and_close_mass(count):
    plant, controls = physical_fixture(count)
    result = solve(plant.hydraulic_graph, plant.pump_curve, controls.speed_actual.value, 1000)
    assert max(result.branch_flows_m3_s) - min(result.branch_flows_m3_s) == 0
    assert sum(result.branch_flows_m3_s) == pytest.approx(result.total_flow_m3_s)
    assert all(r == pytest.approx(0, abs=1e-12) for _, r in result.node_mass_residual_kg_s)
    assert result.max_pressure_residual_pa < 1e-8
    assert result.pump_curve_residual_pa < 1e-8
    assert sum(d.total_w for d in result.dissipations) == pytest.approx(
        result.total_flow_m3_s * result.pump_head_pa
    )


def test_unequal_branch_and_restriction_change_operating_point():
    equal, controls = physical_fixture()
    unequal, _ = physical_fixture(branch_multiplier=1.5)
    a = solve(equal.hydraulic_graph, equal.pump_curve, controls.speed_actual.value, 1000)
    b = solve(unequal.hydraulic_graph, unequal.pump_curve, controls.speed_actual.value, 1000)
    assert b.branch_flows_m3_s[0] < a.branch_flows_m3_s[0]
    assert b.branch_flows_m3_s[1] > a.branch_flows_m3_s[1]
    assert b.total_flow_m3_s < a.total_flow_m3_s
    assert b.branch_flows_m3_s[0] < b.branch_flows_m3_s[1]
    assert b.max_mass_residual_kg_s < 1e-12


def test_pump_curve_intersection_and_speed_trend():
    plant, _ = physical_fixture(2)
    low = solve(plant.hydraulic_graph, plant.pump_curve, 0.6, 1000)
    high = solve(plant.hydraulic_graph, plant.pump_curve, 0.9, 1000)
    k_branch = 2e12 / 2**2
    k_system = 4 * 5e10 + k_branch
    exact = sqrt(60000 * 0.9**2 / (k_system + 1e11))
    assert high.total_flow_m3_s == pytest.approx(exact, rel=1e-12)
    assert high.pump_head_pa == pytest.approx(k_system * exact**2)
    assert high.total_flow_m3_s > low.total_flow_m3_s
    assert high.pump_head_pa > low.pump_head_pa
    assert high.iterations == 1 and high.residual_norm < 1e-7


def test_pump_energy_contract_100w_example_and_no_hydraulic_double_heat():
    drive = PumpDrive(
        p("vfd_eta", 0.9, "fraction"),
        p("motor_eta", 70 / 90, "fraction"),
        p("pump_eta", 60 / 70, "fraction"),
        p("vfd_liquid", 0, "fraction"),
        p("motor_liquid", 0.5, "fraction"),
        p("internal_liquid", 1, "fraction"),
        "cdu",
        p("model", 1, "count"),
        p("standby", 0, "W"),
    )
    account = pump_energy(drive, 60000, 0.001, 10)
    assert account.hydraulic_w == pytest.approx(60)
    assert account.vfd_loss_w == pytest.approx(10)
    assert account.motor_loss_w == pytest.approx(20)
    assert account.internal_loss_w == pytest.approx(10)
    assert account.electrical_w == pytest.approx(100)
    assert account.loss_to_liquid_w + account.hydraulic_w == pytest.approx(80)
    assert account.loss_to_ambient_w == pytest.approx(20)
    assert account.electrical_energy_j == pytest.approx(1000)


def test_pump_off_has_only_explicit_standby_consumption():
    plant, _ = physical_fixture()
    off = solve(plant.hydraulic_graph, plant.pump_curve, 0.0, 1000)
    assert off.total_flow_m3_s == 0
    assert off.pump_head_pa == 0
    assert pump_energy(plant.pump_drive, off.pump_head_pa, off.total_flow_m3_s, 2).electrical_w == 0
    drive = replace(plant.pump_drive, standby_electrical_w=p("standby", 5, "W"))
    standby = pump_energy(drive, 0, 0, 2)
    assert standby.electrical_w == 5
    assert standby.hydraulic_w == 0
    assert standby.vfd_loss_w == 5
    assert standby.loss_to_liquid_w == 0
    assert standby.loss_to_ambient_w == 5
    assert standby.electrical_energy_j == 10


def test_invalid_map_speed_k_and_flow_fail_without_clipping():
    plant, _ = physical_fixture()
    with pytest.raises(ThermalError) as error:
        solve(plant.hydraulic_graph, plant.pump_curve, -0.1, 1000)
    assert error.value.status == ValidityStatus.MODEL_OUT_OF_RANGE
    with pytest.raises(ThermalError, match="INVALID_K"):
        replace(plant.hydraulic_graph.branches[0][0], coefficient=p("bad", 0, "Pa/(m3/s)^2"))
    with pytest.raises(ThermalError, match="PUMP_MAP"):
        replace(plant.pump_curve, curve_k=p("bad", -1, "Pa/(m3/s)^2"))
    with pytest.raises(ThermalError, match="FLOW_OUT_OF_RANGE"):
        replace(plant.hydraulic_graph.branches[0][0], valid_q_m3_s=(0, 1e-8)).drop_pa(0.001)


def test_all_passive_dissipations_have_one_owner():
    plant, _ = physical_fixture(4)
    result = solve(plant.hydraulic_graph, plant.pump_curve, 0.9, 1000)
    assert len({d.edge_id for d in result.dissipations}) == len(result.dissipations)
    assert fsum(d.total_w for d in result.dissipations) == pytest.approx(
        result.pump_head_pa * result.total_flow_m3_s
    )
