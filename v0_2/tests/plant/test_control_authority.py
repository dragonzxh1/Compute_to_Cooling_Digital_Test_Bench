"""Phase 4.1: prescribed speed must propagate through the *same* coupled plant."""

from dataclasses import replace
from math import fsum

import pytest
from v0_2.examples.phase4_1_validation import evidence
from v0_2.plant import loop
from v0_2.plant.authority import traces_for_run, traces_for_step
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import PlantEvent, run
from v0_2.thermal.coldplate import FlowInput
from v0_2.thermal.fixtures import gpu_chain
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import SolverStatus, ThermalError, ValidityStatus

# Registered before results: uncalibrated numerical-test policy, not an OEM requirement.
DURATION_NS = 120_000_000_000
WINDOW_START_NS = 96_000_000_000  # final 20% of the fixed 120 s run
SPEEDS = (0.50, 0.70, 0.90)
MIN_RELATIVE_FLOW_AND_RTH_CHANGE = 0.001
FLOW_NUMERICAL_TOL_KG_S = 1e-9
RTH_AUDIT_NUMERICAL_TOL_K_W = 1e-12
MIN_Q_CHANGE_W = 0.01
MIN_THERMAL_EFFECT_K = 0.05
DT_NS = (200_000_000, 100_000_000, 50_000_000)


def _input(controls, speed):
    return replace(controls, speed_actual=p("authority.speed_actual", speed, "fraction"))


def _branch_rows(plant, controls, dt_ns=200_000_000, events=()):
    result = run(plant, controls, DURATION_NS, dt_ns, events)
    traces = traces_for_run(result)
    assert all(t.time_ns < t.end_ns for t in traces)
    return result, traces


def _window(rows, branch_id):
    return [t for t in rows if t.branch_id == branch_id and t.time_ns >= WINDOW_START_NS]


def _avg(rows, attr):
    assert rows
    return fsum(getattr(row, attr) for row in rows) / len(rows)


def _assert_physical_ledgers(result):
    m = result.metrics()
    assert m["energy_pass"] and m["mass_pass"]
    assert all(
        step.pump.electrical_w
        == pytest.approx(
            step.pump.hydraulic_w
            + step.pump.vfd_loss_w
            + step.pump.motor_loss_w
            + step.pump.internal_loss_w
        )
        for step in result.accepted
    )
    return m


def test_speed_sweep_propagates_all_links_and_conserves_energy():
    plant, base = physical_fixture(2, power_each=240)
    assert not any(e.external_boundary_id == "bath" for e in plant.interfaces)
    outcomes = []
    for speed in SPEEDS:
        result, rows = _branch_rows(plant, _input(base, speed))
        _assert_physical_ledgers(result)
        branch = _window(rows, "b0")
        first = branch[0]
        assert all(t.pump_speed_actual_fraction == speed for t in rows)
        assert all(
            t.branch_mass_flow_kg_s
            == pytest.approx(result.accepted[0].hydraulic.branch_flows_m3_s[0] * 1000)
            for t in rows
            if t.branch_id == "b0"
        )
        assert all(
            t.coldplate_rth_k_w
            == pytest.approx(1 / result.accepted[0].coldplate_uses[0].conductance_w_k)
            for t in branch
        )
        assert len({t.hydraulic_solution_id for t in rows if t.time_ns == 0}) == 1
        assert first.branch_flow_record_id.startswith(first.hydraulic_solution_id)
        assert first.coldplate_evaluation_id.startswith(first.branch_flow_record_id)
        assert first.hydraulic_solution_id in first.thermal_step_id
        for branch_id in ("b0", "b1"):
            record = _window(rows, branch_id)[0]
            coldplate = next(
                e.resistance_model for e in plant.interfaces if e.interface_id == f"{branch_id}:cp"
            )
            model_flow = FlowInput(
                p("independent.flow", record.branch_mass_flow_kg_s, "kg/s"),
                plant.heat_exchanger.secondary_fluid.fluid_id,
            )
            assert record.coldplate_rth_k_w == pytest.approx(coldplate.resistance(model_flow))
        outcomes.append(
            {
                "flow": first.branch_mass_flow_kg_s,
                "rth": first.coldplate_rth_k_w,
                "q": _avg(branch, "plate_to_coolant_heat_w"),
                "device": _avg(branch, "device_temperature_k"),
                "plate": _avg(branch, "plate_temperature_k"),
                "dp": first.pump_dp_pa,
                "peak_device": max(t.device_temperature_k for t in rows if t.branch_id == "b0"),
            }
        )
    low, mid, high = outcomes
    assert low["dp"] < mid["dp"] < high["dp"]
    assert low["flow"] < mid["flow"] < high["flow"]
    assert low["rth"] > mid["rth"] > high["rth"]
    assert all(
        b["flow"] - a["flow"]
        > max(10 * FLOW_NUMERICAL_TOL_KG_S, MIN_RELATIVE_FLOW_AND_RTH_CHANGE * a["flow"])
        and a["rth"] - b["rth"]
        > max(10 * RTH_AUDIT_NUMERICAL_TOL_K_W, MIN_RELATIVE_FLOW_AND_RTH_CHANGE * a["rth"])
        for a, b in ((low, mid), (mid, high))
    )
    assert abs(high["q"] - low["q"]) > MIN_Q_CHANGE_W
    assert low["device"] > mid["device"] > high["device"]
    assert low["plate"] > mid["plate"] > high["plate"]
    assert low["device"] - high["device"] > MIN_THERMAL_EFFECT_K
    assert low["plate"] - high["plate"] > MIN_THERMAL_EFFECT_K


def test_branch_restriction_changes_its_own_thermal_path():
    baseline, controls = physical_fixture(2, power_each=240)
    restricted, _ = physical_fixture(2, power_each=240, branch_multiplier=1.5)
    # The only fixture parameter changed is branch 0's hydraulic coldplate K.
    assert (
        baseline.hydraulic_graph.branches[0][0].coefficient.value * 1.5
        == restricted.hydraulic_graph.branches[0][0].coefficient.value
    )
    assert baseline.initial_state == restricted.initial_state
    assert baseline.interfaces == restricted.interfaces
    assert baseline.source_map == restricted.source_map
    assert baseline.hydraulic_graph.branches[0][1:] == restricted.hydraulic_graph.branches[0][1:]
    assert baseline.hydraulic_graph.branches[1:] == restricted.hydraulic_graph.branches[1:]
    base_run, base_rows = _branch_rows(baseline, controls)
    restriction_run, restriction_rows = _branch_rows(restricted, controls)
    _assert_physical_ledgers(base_run)
    _assert_physical_ledgers(restriction_run)
    base_0, rest_0 = _window(base_rows, "b0"), _window(restriction_rows, "b0")
    base_1, rest_1 = _window(base_rows, "b1"), _window(restriction_rows, "b1")
    assert rest_0[0].branch_mass_flow_kg_s < base_0[0].branch_mass_flow_kg_s
    assert rest_1[0].branch_mass_flow_kg_s > base_1[0].branch_mass_flow_kg_s
    assert rest_0[0].coldplate_rth_k_w > base_0[0].coldplate_rth_k_w
    assert rest_1[0].coldplate_rth_k_w < base_1[0].coldplate_rth_k_w
    assert _avg(rest_0, "device_temperature_k") > _avg(base_0, "device_temperature_k")
    assert _avg(rest_0, "plate_temperature_k") > _avg(base_0, "plate_temperature_k")
    assert _avg(rest_1, "device_temperature_k") < _avg(base_1, "device_temperature_k")
    assert (
        _avg(rest_0, "device_temperature_k") - _avg(base_0, "device_temperature_k")
        > MIN_THERMAL_EFFECT_K
    )
    assert (
        abs(_avg(rest_0, "plate_to_coolant_heat_w") - _avg(base_0, "plate_to_coolant_heat_w"))
        > MIN_Q_CHANGE_W
    )


def test_runtime_speed_step_changes_hydraulics_immediately_not_thermal_state():
    plant, controls = physical_fixture(2, power_each=240)
    low, high = _input(controls, 0.5), _input(controls, 0.9)
    event_ns = 40_000_000_000
    result, traces = _branch_rows(plant, low, events=(PlantEvent(event_ns, high),))
    _assert_physical_ledgers(result)
    before = next(t for t in traces if t.branch_id == "b0" and t.end_ns == event_ns)
    after = next(t for t in traces if t.branch_id == "b0" and t.time_ns == event_ns)
    assert before.pump_speed_actual_fraction == 0.5
    assert after.pump_speed_actual_fraction == 0.9
    assert after.branch_mass_flow_kg_s > before.branch_mass_flow_kg_s
    assert after.coldplate_rth_k_w < before.coldplate_rth_k_w
    assert after.hydraulic_solution_id != before.hydraulic_solution_id
    event_state = next(s.next_state for s in result.accepted if s.next_state.time_ns == event_ns)
    first_after = next(s for s in result.accepted if s.next_state.time_ns > event_ns)
    assert first_after.next_state.time_ns == event_ns + DT_NS[0]
    assert (
        abs(
            first_after.next_state.by_id["b0:die"].temperature_k
            - event_state.by_id["b0:die"].temperature_k
        )
        < 0.1
    )
    assert after.device_temperature_k == first_after.next_state.by_id["b0:die"].temperature_k
    # The event changes held input at t, but reuses the unchanged thermal state at t.
    assert result.states[result.accepted.index(first_after)].time_ns == event_ns


@pytest.mark.parametrize("fault", ("stale", "future", "wrong_branch"))
def test_wrong_coldplate_flow_is_rejected_transactionally(monkeypatch, fault):
    plant, controls = physical_fixture(
        2, branch_multiplier=1.5 if fault == "wrong_branch" else None
    )
    held = _input(controls, 0.5 if fault == "future" else 0.9)
    if fault == "wrong_branch":
        solution = loop.step(plant, plant.initial_state, held, DT_NS[0])
        injected = solution.coldplate_uses[1].local_mass_flow_kg_s
    else:
        other = _input(controls, 0.9 if fault == "future" else 0.5)
        injected = (
            loop.step(plant, plant.initial_state, other, DT_NS[0])
            .coldplate_uses[0]
            .local_mass_flow_kg_s
        )
    original = loop._coldplate_flow_from_hydraulic

    def wrong_source(edge, branch_index, hydraulic, fluid, model):
        flow = original(edge, branch_index, hydraulic, fluid, model)
        if branch_index != 0:
            return flow
        return replace(
            flow,
            mass_flow=replace(flow.mass_flow, value=injected, valid_range=(injected, injected)),
        )

    monkeypatch.setattr(loop, "_coldplate_flow_from_hydraulic", wrong_source)
    result = loop.step(plant, plant.initial_state, held, DT_NS[0])
    assert result.solver_status == SolverStatus.FAILED
    assert result.validity_status == ValidityStatus.MODEL_INVALID
    assert "CONTROL_AUTHORITY_PATH_INVALID" in result.diagnostics[0]
    assert result.next_state is plant.initial_state and result.ledger is None


def test_coldplate_domain_is_not_clamped_and_no_bath_is_accepted():
    plant, controls = physical_fixture(2)
    invalid = loop.step(plant, plant.initial_state, _input(controls, 0.02), DT_NS[0])
    assert invalid.solver_status == SolverStatus.FAILED
    assert invalid.validity_status == ValidityStatus.MODEL_OUT_OF_RANGE
    assert "FLOW_OUT_OF_RANGE" in invalid.diagnostics[0]
    with pytest.raises(ThermalError, match="THERMAL_PATH_DOUBLE_COUNT"):
        loop.preflight_coolant_path(gpu_chain().topology.interfaces, plant.connections)


def test_audit_rejects_old_matrix_conductance_claim():
    plant, controls = physical_fixture(2)
    accepted = loop.step(plant, plant.initial_state, controls, DT_NS[0])
    assert accepted.solver_status == SolverStatus.CONVERGED
    use = accepted.coldplate_uses[0]
    forged = replace(
        accepted,
        coldplate_uses=(
            replace(
                use,
                endpoint_resistance_k_w=use.endpoint_resistance_k_w * 1.5,
                conductance_w_k=use.conductance_w_k / 1.5,
            ),
            *accepted.coldplate_uses[1:],
        ),
    )
    with pytest.raises(ThermalError, match="CONTROL_AUTHORITY_PATH_INVALID"):
        traces_for_step(plant, plant.initial_state, forged, controls)


@pytest.mark.parametrize("dt_ns", DT_NS)
def test_refinement_for_step_and_restriction(dt_ns):
    plant, controls = physical_fixture(2, power_each=240)
    low, high = _input(controls, 0.5), _input(controls, 0.9)
    stepped, step_rows = _branch_rows(plant, low, dt_ns, (PlantEvent(40_000_000_000, high),))
    restricted, restricted_controls = physical_fixture(2, power_each=240, branch_multiplier=1.5)
    restricted_run, restriction_rows = _branch_rows(restricted, restricted_controls, dt_ns)
    for result, rows in ((stepped, step_rows), (restricted_run, restriction_rows)):
        _assert_physical_ledgers(result)
        assert rows[-1].end_ns == DURATION_NS
        assert len({t.time_ns for t in rows}) == DURATION_NS // dt_ns


def test_registered_qualification_effect_exceeds_fine_mesh_uncertainty():
    results = evidence()
    sweep = results["sweep"]
    policy = results["policy"]
    low, mid, high = (sweep[str(speed)]["b0"] for speed in SPEEDS)
    threshold = policy["min_temperature_effect_k"]
    assert threshold == max(0.05, 5 * policy["fine_pair_temperature_uncertainty_k"])
    assert low["window_device_k"] > mid["window_device_k"] > high["window_device_k"]
    assert low["window_device_k"] - high["window_device_k"] > threshold
    restricted = results["restriction"]["branch0_k_multiplier_1_5"]["b0"]
    assert restricted["window_device_k"] - high["window_device_k"] > threshold
    assert restricted["branch_mass_flow_kg_s"] < high["branch_mass_flow_kg_s"]
    assert restricted["coldplate_rth_k_w"] > high["coldplate_rth_k_w"]
    assert high["branch_mass_flow_kg_s"] - restricted["branch_mass_flow_kg_s"] > max(
        10 * FLOW_NUMERICAL_TOL_KG_S,
        MIN_RELATIVE_FLOW_AND_RTH_CHANGE * high["branch_mass_flow_kg_s"],
    )
    assert restricted["coldplate_rth_k_w"] - high["coldplate_rth_k_w"] > max(
        10 * RTH_AUDIT_NUMERICAL_TOL_K_W,
        MIN_RELATIVE_FLOW_AND_RTH_CHANGE * high["coldplate_rth_k_w"],
    )
    assert (
        abs(restricted["window_plate_to_coolant_w"] - high["window_plate_to_coolant_w"])
        > MIN_Q_CHANGE_W
    )
    unrestricted = results["restriction"]["branch0_k_multiplier_1_5"]["b1"]
    assert unrestricted["branch_mass_flow_kg_s"] > high["branch_mass_flow_kg_s"]
    assert unrestricted["window_device_k"] < high["window_device_k"]
    dynamic = results["dynamic"]
    assert dynamic["first_held_interval"]["time_ns"] == 40_000_000_000
    assert (
        dynamic["first_held_interval"]["branch_flow_kg_s"] > dynamic["before"]["branch_flow_kg_s"]
    )
    assert dynamic["first_held_interval"]["rth_k_w"] < dynamic["before"]["rth_k_w"]
    assert (
        abs(dynamic["first_held_interval"]["device_k"] - dynamic["at_event_continuous_device_k"])
        < 0.1
    )
    for name, qualification in results["mesh"].items():
        assert qualification["gate"] == "PASS", name
        assert [row["dt_s"] for row in qualification["samples"]] == [0.2, 0.1, 0.05]
        assert all(row["mass_pass"] and row["energy_pass"] for row in qualification["samples"])
        for field in (
            "branch_flow_kg_s",
            "rth_k_w",
            "plate_to_liquid_j",
            "final_device_k",
            "final_return_k",
            "hx_export_j",
        ):
            coarse, fine = (row[field] for row in qualification["adjacent"])
            assert fine <= coarse + 1e-9, (name, field, coarse, fine)
