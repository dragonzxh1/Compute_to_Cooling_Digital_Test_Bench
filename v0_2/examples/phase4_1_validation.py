"""Reproduce Phase 4.1 evidence on fixed, uncalibrated coupled-plant fixtures."""

import json
from dataclasses import replace
from itertools import pairwise
from math import fsum

from v0_2.plant.authority import traces_for_run
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import PlantEvent, convergence, run
from v0_2.thermal.provenance import fixture_parameter as p

# Pre-registered numerical-test policy, never an OEM equipment limit.
DURATION_NS = 120_000_000_000
WINDOW_START_NS = 96_000_000_000
STEP_NS = 40_000_000_000
SPEEDS = (0.5, 0.7, 0.9)
MESHES_NS = (200_000_000, 100_000_000, 50_000_000)
POWER_EACH_W = 240
RESTRICTION_MULTIPLIER = 1.5


def _controls(base, speed):
    return replace(base, speed_actual=p("authority.speed_actual", speed, "fraction"))


def _window(rows, branch):
    return [r for r in rows if r.branch_id == branch and r.time_ns >= WINDOW_START_NS]


def _avg(rows, field):
    return fsum(getattr(row, field) for row in rows) / len(rows)


def _branch_summary(result, rows, branch):
    selected = [r for r in rows if r.branch_id == branch]
    window = _window(rows, branch)
    last = selected[-1]
    return {
        "branch": branch,
        "speed": last.pump_speed_actual_fraction,
        "pump_dp_pa": last.pump_dp_pa,
        "total_mass_flow_kg_s": last.total_mass_flow_kg_s,
        "branch_mass_flow_kg_s": last.branch_mass_flow_kg_s,
        "coldplate_rth_k_w": last.coldplate_rth_k_w,
        "window_plate_to_coolant_w": _avg(window, "plate_to_coolant_heat_w"),
        "window_device_k": _avg(window, "device_temperature_k"),
        "window_plate_k": _avg(window, "plate_temperature_k"),
        "peak_device_k": max(r.device_temperature_k for r in selected),
        "final_device_k": last.device_temperature_k,
        "peak_plate_k": max(r.plate_temperature_k for r in selected),
        "final_plate_k": last.plate_temperature_k,
        "final_return_k": last.branch_return_temperature_k,
        "pump_electrical_w": last.pump_electrical_w,
        "hx_final_w": last.hx_secondary_heat_w,
        "plate_to_coolant_integral_j": fsum(
            dict(s.ledger.interface_heat_j)[f"{branch}:cp"] for s in result.accepted
        ),
    }


def _qualification_run(plant, controls, dt_ns, events=()):
    result = run(plant, controls, DURATION_NS, dt_ns, events)
    return result, traces_for_run(result)


def _mesh_summary(runs, branch="b0"):
    metrics = [r.metrics() for r in runs]
    rows = [traces_for_run(r) for r in runs]
    branch_rows = [[t for t in all_rows if t.branch_id == branch] for all_rows in rows]
    samples = []
    for result, m, sample in zip(runs, metrics, branch_rows):
        samples.append(
            {
                "dt_s": (result.accepted[0].next_state.time_ns - result.initial_state.time_ns)
                / 1e9,
                "branch_flow_kg_s": sample[-1].branch_mass_flow_kg_s,
                "rth_k_w": sample[-1].coldplate_rth_k_w,
                "plate_to_liquid_j": fsum(
                    dict(s.ledger.interface_heat_j)[f"{branch}:cp"] for s in result.accepted
                ),
                "final_device_k": sample[-1].device_temperature_k,
                "final_return_k": sample[-1].branch_return_temperature_k,
                "hx_export_j": m["hx_j"],
                "max_mass_residual_kg_s": max(
                    m["max_mass_node_residual_kg_s"], m["max_mass_volume_residual_kg_s"]
                ),
                "signed_energy_residual_j": m["signed_energy_residual_j"],
                "sum_abs_energy_residual_j": m["sum_abs_energy_residual_j"],
                "energy_pass": m["energy_pass"],
                "mass_pass": m["mass_pass"],
            }
        )
    fields = (
        "branch_flow_kg_s",
        "rth_k_w",
        "plate_to_liquid_j",
        "final_device_k",
        "final_return_k",
        "hx_export_j",
    )
    adjacent = [{field: abs(a[field] - b[field]) for field in fields} for a, b in pairwise(samples)]
    return {"gate": convergence(runs)["status"], "samples": samples, "adjacent": adjacent}


def evidence():
    plant, base = physical_fixture(2, power_each=POWER_EACH_W)
    sweep = {}
    for speed in SPEEDS:
        result, rows = _qualification_run(plant, _controls(base, speed), MESHES_NS[0])
        sweep[str(speed)] = {
            "b0": _branch_summary(result, rows, "b0"),
            "b1": _branch_summary(result, rows, "b1"),
            "energy_pass": result.metrics()["energy_pass"],
            "mass_pass": result.metrics()["mass_pass"],
        }
    restricted, restricted_controls = physical_fixture(
        2, power_each=POWER_EACH_W, branch_multiplier=RESTRICTION_MULTIPLIER
    )
    restricted_run, restricted_rows = _qualification_run(
        restricted, restricted_controls, MESHES_NS[0]
    )
    restriction = {
        "baseline": sweep["0.9"],
        "branch0_k_multiplier_1_5": {
            "b0": _branch_summary(restricted_run, restricted_rows, "b0"),
            "b1": _branch_summary(restricted_run, restricted_rows, "b1"),
            "energy_pass": restricted_run.metrics()["energy_pass"],
            "mass_pass": restricted_run.metrics()["mass_pass"],
        },
    }
    low, high = _controls(base, 0.5), _controls(base, 0.9)
    events = (PlantEvent(STEP_NS, high),)
    stepped_run, stepped_rows = _qualification_run(plant, low, MESHES_NS[0], events)
    before = next(r for r in stepped_rows if r.branch_id == "b0" and r.end_ns == STEP_NS)
    first = next(r for r in stepped_rows if r.branch_id == "b0" and r.time_ns == STEP_NS)
    late = [r for r in stepped_rows if r.branch_id == "b0"][-1]
    event_state = next(
        s.next_state for s in stepped_run.accepted if s.next_state.time_ns == STEP_NS
    )
    dynamic = {
        "before": _trace_fields(before),
        "at_event_continuous_device_k": event_state.by_id["b0:die"].temperature_k,
        "first_held_interval": _trace_fields(first),
        "late": _trace_fields(late),
    }
    # Summarize each three-mesh group before allocating the next one.
    mesh = {}
    for name, model, held, event_schedule in (
        ("speed_step", plant, low, events),
        ("restriction_baseline", plant, high, ()),
        ("restriction_1_5", restricted, restricted_controls, ()),
    ):
        runs = [run(model, held, DURATION_NS, dt, event_schedule) for dt in MESHES_NS]
        mesh[name] = _mesh_summary(runs)
        del runs
    temp_uncertainty = max(
        mesh["restriction_baseline"]["adjacent"][1]["final_device_k"],
        mesh["restriction_1_5"]["adjacent"][1]["final_device_k"],
    )
    return {
        "policy": {
            "duration_s": DURATION_NS / 1e9,
            "window_start_s": WINDOW_START_NS / 1e9,
            "dt_s": [x / 1e9 for x in MESHES_NS],
            "power_each_w": POWER_EACH_W,
            "restriction_multiplier": RESTRICTION_MULTIPLIER,
            "min_temperature_effect_k": max(0.05, 5 * temp_uncertainty),
            "fine_pair_temperature_uncertainty_k": temp_uncertainty,
        },
        "sweep": sweep,
        "restriction": restriction,
        "dynamic": dynamic,
        "mesh": mesh,
    }


def _trace_fields(trace):
    return {
        "time_ns": trace.time_ns,
        "end_ns": trace.end_ns,
        "speed": trace.pump_speed_actual_fraction,
        "dp_pa": trace.pump_dp_pa,
        "branch_flow_kg_s": trace.branch_mass_flow_kg_s,
        "rth_k_w": trace.coldplate_rth_k_w,
        "plate_to_liquid_w": trace.plate_to_coolant_heat_w,
        "device_k": trace.device_temperature_k,
        "hydraulic_solution_id": trace.hydraulic_solution_id,
        "thermal_step_id": trace.thermal_step_id,
    }


if __name__ == "__main__":
    print(json.dumps(evidence(), indent=2))
