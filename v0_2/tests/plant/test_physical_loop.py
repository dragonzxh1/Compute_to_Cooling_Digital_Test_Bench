from dataclasses import replace
from math import fsum

import pytest
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.loop import PlantState, TopologyMode, preflight_coolant_path, step
from v0_2.plant.phase4_harness import PlantEvent, convergence, run
from v0_2.thermal.fixtures import gpu_chain, resistor
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import SolverStatus, ThermalError, ValidityStatus


def test_validation_bath_and_physical_advection_are_mutually_exclusive():
    f = gpu_chain()
    plant, _ = physical_fixture()
    assert preflight_coolant_path(f.topology.interfaces, ()) == TopologyMode.THERMAL_VALIDATION_BATH
    assert (
        preflight_coolant_path(plant.interfaces, plant.connections)
        == TopologyMode.PHYSICAL_COOLANT_LOOP
    )
    assert not any(e.external_boundary_id == "bath" for e in plant.interfaces)
    with pytest.raises(ThermalError, match="THERMAL_PATH_DOUBLE_COUNT") as error:
        preflight_coolant_path(f.topology.interfaces, plant.connections)
    assert error.value.status == ValidityStatus.CONFIG_INVALID
    forbidden = resistor("test_bath", "b0:local", "bath", 0.02, boundary=True, medium="LIQUID")
    with pytest.raises(ThermalError, match="THERMAL_PATH_DOUBLE_COUNT"):
        replace(plant, interfaces=(*plant.interfaces, forbidden))


def test_phase3_standalone_fixture_remains_runnable():
    from v0_2.thermal.harness import run as run_phase3

    f = gpu_chain()
    result = run_phase3(f, 1_000_000_000, 100_000_000)
    assert result.metrics()["energy_pass"]
    assert result.metrics()["liquid_j"] > 0


def test_no_fifo_and_no_pump_hydraulic_heat_duplicate():
    plant, _ = physical_fixture()
    with pytest.raises(ThermalError, match="TRANSPORT_DOUBLE_COUNT"):
        preflight_coolant_path(plant.interfaces, plant.connections, legacy_fifo_enabled=True)
    with pytest.raises(ThermalError, match="PUMP_HEAT_DOUBLE_COUNT"):
        preflight_coolant_path(
            plant.interfaces, plant.connections, pump_hydraulic_heat_at_pump=True
        )
    with pytest.raises(ThermalError, match="TRANSPORT_DOUBLE_COUNT"):
        replace(plant, legacy_fifo_enabled=True)
    with pytest.raises(ThermalError, match="PUMP_HEAT_DOUBLE_COUNT"):
        replace(plant, pump_hydraulic_heat_at_pump=True)


@pytest.mark.parametrize("branches", [1, 2, 4])
def test_full_secondary_loop_mass_energy_and_storage(branches):
    plant, controls = physical_fixture(branches)
    result = run(plant, controls, 5_000_000_000, 100_000_000)
    m = result.metrics()
    assert m["energy_pass"]
    assert m["max_mass_node_residual_kg_s"] < 1e-12
    assert m["max_mass_volume_residual_kg_s"] < 1e-12
    assert m["max_node_energy_residual_j"] < 1e-6
    assert abs(m["signed_energy_residual_j"]) < 1e-6
    assert m["source_j"] + m["pump_heat_liquid_j"] - m["air_j"] - m["hx_j"] == pytest.approx(
        m["stored_j"], abs=1e-6
    )
    for old, new in zip(plant.initial_state.volumes, result.final_state.volumes):
        assert old.mass_kg == new.mass_kg
        assert old.storage_owner_id == new.storage_owner_id
    assert result.final_state.by_id["cdu"].temperature_k < 300
    assert (
        result.final_state.by_id["cdu"].temperature_k
        != result.final_state.by_id["return_1"].temperature_k
    )
    assert result.accepted[-1].hx.secondary_out_w == pytest.approx(
        result.accepted[-1].hx.primary_in_w
    )


def test_thermal_advective_coupling_uses_single_local_coolant_owner():
    plant, controls = physical_fixture(1)
    assert "b0:local" not in {n.node_id for n in plant.initial_state.solids}
    assert "b0:local" in {v.volume_id for v in plant.initial_state.volumes}
    r = step(plant, plant.initial_state, controls, 200_000_000)
    assert r.solver_status == SolverStatus.CONVERGED
    assert "b0:cp" in dict(r.ledger.interface_heat_j)
    assert any(t.receiver_id == "b0:local" for t in r.ledger.advective_heat)
    assert any(t.donor_id == "b0:local" for t in r.ledger.advective_heat)
    assert len({t.link_id for t in r.ledger.advective_heat}) == len(r.ledger.advective_heat)
    assert fsum(t.energy_j for t in r.ledger.advective_heat if t.receiver_id == "b0:local") != 0


def test_pump_accounting_separates_electricity_hydraulic_and_heat():
    plant, controls = physical_fixture()
    result = step(plant, plant.initial_state, controls, 200_000_000)
    pump, hydraulic, ledger = result.pump, result.hydraulic, result.ledger
    assert pump.electrical_w == pytest.approx(
        pump.hydraulic_w + pump.vfd_loss_w + pump.motor_loss_w + pump.internal_loss_w
    )
    assert pump.hydraulic_w == pytest.approx(sum(d.total_w for d in hydraulic.dissipations))
    assert ledger.pump_heat_liquid_j + ledger.pump_heat_ambient_j == pytest.approx(
        ledger.pump_electrical_j
    )
    assert ledger.pump_heat_liquid_j < ledger.pump_electrical_j
    assert ledger.source_j == pytest.approx(48)


def test_duplicate_inventory_and_invalid_input_do_not_commit():
    plant, controls = physical_fixture()
    original = plant.initial_state
    with pytest.raises(ThermalError, match="VOLUME_OWNERSHIP_DUPLICATE"):
        PlantState(
            original.solids,
            (
                original.volumes[0],
                replace(original.volumes[1], storage_owner_id=original.volumes[0].storage_owner_id),
                *original.volumes[2:],
            ),
        )
    bad = replace(controls, speed_actual=p("bad_speed", -0.1, "fraction"))
    result = step(plant, original, bad, 200_000_000)
    assert result.solver_status == SolverStatus.FAILED
    assert result.next_state is original and result.ledger is None
    assert result.validity_status == ValidityStatus.MODEL_OUT_OF_RANGE
    changed = replace(
        original,
        volumes=(replace(original.volumes[0], storage_owner_id="other"), *original.volumes[1:]),
    )
    result = step(plant, changed, controls, 200_000_000)
    assert result.solver_status == SolverStatus.FAILED and result.next_state is changed


@pytest.mark.parametrize("branches", [1, 2, 4])
def test_real_mesh_refinement_for_full_coupled_plant(branches):
    plant, controls = physical_fixture(branches)
    runs = [
        run(plant, controls, 5_000_000_000, dt) for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    result = convergence(runs)
    assert result["status"] == "PASS", result
    assert [len(r.mesh) for r in runs] == [25, 50, 100]
    reference = run(plant, controls, 5_000_000_000, 25_000_000)
    errors = [
        abs(
            r.final_state.by_id["cdu"].temperature_k
            - reference.final_state.by_id["cdu"].temperature_k
        )
        for r in runs
    ]
    assert errors[2] < errors[1] < errors[0]


def test_refinement_with_fws_event_and_source_step():
    plant, controls = physical_fixture(2, power_each=30)
    updated = replace(
        controls,
        electrical_leaves=physical_fixture(2, power_each=120)[1].electrical_leaves,
        fws_inlet_temperature=p("fws_warm", 294, "K"),
    )
    events = (PlantEvent(2_000_000_000, updated),)
    runs = [
        run(plant, controls, 5_000_000_000, dt, events)
        for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    result = convergence(runs)
    assert result["status"] == "PASS", result
    assert [len(r.mesh) for r in runs] == [25, 50, 100]


def test_same_events_cannot_forge_three_meshes():
    plant, controls = physical_fixture()
    events = tuple(PlantEvent(t, controls) for t in range(50_000_000, 1_000_000_000, 50_000_000))
    runs = [
        run(plant, controls, 1_000_000_000, dt, events)
        for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    assert convergence(runs)["status"] == "NOT_EVALUABLE"
