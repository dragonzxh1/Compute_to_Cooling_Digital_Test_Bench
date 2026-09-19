"""Reproducible, uncalibrated Phase 4 numerical evidence."""

import json
from dataclasses import asdict, replace
from math import exp

from v0_2.cdu.heat_exchanger import evaluate
from v0_2.coolant.advection import AdvectiveLink, solve_implicit
from v0_2.hydraulics.solver import solve
from v0_2.plant.fixtures import generic_fluid, physical_fixture, volume
from v0_2.plant.phase4_harness import PlantEvent, convergence, run
from v0_2.thermal.provenance import fixture_parameter as p


def evidence():
    output = {"hydraulic": [], "transport": [], "hx": {}, "fws": {}, "convergence": {}}
    for branches, multiplier, speed in (
        (1, None, 0.9),
        (2, None, 0.6),
        (2, None, 0.9),
        (2, 2.0, 0.9),
        (4, None, 0.9),
    ):
        plant, _ = physical_fixture(branches, branch_multiplier=multiplier)
        result = solve(plant.hydraulic_graph, plant.pump_curve, speed, 1000)
        output["hydraulic"].append(
            {
                "branches": branches,
                "branch_0_multiplier": multiplier or 1,
                "speed": speed,
                "total_flow_kg_s": result.total_flow_m3_s * 1000,
                "pump_dp_pa": result.pump_head_pa,
                "branch_flows_kg_s": [x * 1000 for x in result.branch_flows_m3_s],
                "manifold_dp_pa": result.manifold_dp_pa,
                "iterations": result.iterations,
                "residual_norm": result.residual_norm,
                "max_mass_residual_kg_s": result.max_mass_residual_kg_s,
                "max_pressure_residual_pa": result.max_pressure_residual_pa,
                "pump_curve_residual_pa": result.pump_curve_residual_pa,
            }
        )
    fluid = generic_fluid()
    links = (
        AdvectiveLink("in", "inlet", "cell", 0.2, "in"),
        AdvectiveLink("out", "cell", "outlet", 0.2, "out"),
    )
    for dt in (0.2, 0.1, 0.05):
        state = volume("cell", fluid, mass=1)
        for _ in range(round(5 / dt)):
            state = solve_implicit(
                (state,), links, dt, {"inlet": fluid.h(310), "outlet": fluid.h(300)}
            ).volumes[0]
        output["transport"].append(
            {
                "dt_s": dt,
                "volume_m3": 0.001,
                "mass_kg": state.mass_kg.value,
                "inlet_k": 310,
                "inlet_h_j_kg": fluid.h(310),
                "outlet_k": state.temperature_k,
                "outlet_h_j_kg": state.specific_enthalpy_j_kg,
                "stored_change_j": state.energy_j - volume("cell", fluid, mass=1).energy_j,
                "residence_s": state.residence_time_s(0.2),
                "analytic_k": 310 - 10 * exp(-1),
                "error_k": abs(state.temperature_k - (310 - 10 * exp(-1))),
            }
        )
    plant, controls = physical_fixture(2)
    output["hx"] = {
        "ua_w_k": plant.heat_exchanger.ua.value,
        **asdict(evaluate(plant.heat_exchanger, 0.2, 0.2, 320, 300)),
    }
    base = run(plant, controls, 10_000_000_000, 200_000_000)
    warm = replace(controls, fws_inlet_temperature=p("FWS_warm", 294, "K"))
    reduced = replace(controls, primary_mass_flow=p("FWS_reduced", 0.28, "kg/s"))
    for name, event_controls in (
        ("base", None),
        ("warm_290_to_294_k", warm),
        ("flow_0.4_to_0.28_kg_s", reduced),
    ):
        result = (
            base
            if event_controls is None
            else run(
                plant,
                controls,
                10_000_000_000,
                200_000_000,
                (PlantEvent(5_000_000_000, event_controls),),
            )
        )
        output["fws"][name] = {
            "cdu_k": result.metrics()["final_cdu_supply_k"],
            "hx_final_w": result.accepted[-1].hx.secondary_out_w,
        }
    for name, n, initial, event in (
        ("one_branch", 1, 120, False),
        ("two_branch", 2, 120, False),
        ("four_branch", 4, 120, False),
        ("source_fws_event", 2, 30, True),
    ):
        fixture, input0 = physical_fixture(n, power_each=initial)
        events = ()
        if event:
            input1 = replace(
                input0,
                electrical_leaves=physical_fixture(n, power_each=120)[1].electrical_leaves,
                fws_inlet_temperature=p("FWS_warm", 294, "K"),
            )
            events = (PlantEvent(2_000_000_000, input1),)
        runs = [
            run(fixture, input0, 5_000_000_000, dt, events)
            for dt in (200_000_000, 100_000_000, 50_000_000)
        ]
        output["convergence"][name] = convergence(runs)
    return output


if __name__ == "__main__":
    print(json.dumps(evidence(), indent=2))
