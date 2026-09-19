from dataclasses import dataclass
from math import fsum

import numpy as np

from v0_2.plant.loop import step
from v0_2.thermal.validity import SolverStatus, ThermalError, require


@dataclass(frozen=True)
class PlantEvent:
    time_ns: int
    controls: object


@dataclass(frozen=True)
class PlantRun:
    initial_state: object
    accepted: tuple
    qualification_inputs: tuple

    @property
    def final_state(self):
        return self.accepted[-1].next_state

    @property
    def mesh(self):
        return tuple(s.next_state.time_ns for s in self.accepted)

    @property
    def states(self):
        return (self.initial_state, *(s.next_state for s in self.accepted))

    def metrics(self):
        ledgers = [s.ledger for s in self.accepted]
        total_residual = fsum(l.full_loop_residual_j for l in ledgers)
        sum_abs_residual = fsum(abs(l.full_loop_residual_j) for l in ledgers)
        source = fsum(l.source_j for l in ledgers)
        storage = fsum(l.stored_change_j for l in ledgers)
        air = fsum(l.air_export_j for l in ledgers)
        hx = fsum(l.hx_export_j for l in ledgers)
        pump_heat = fsum(l.pump_heat_liquid_j for l in ledgers)
        scale = fsum(
            abs(l.stored_change_j)
            + abs(l.source_j)
            + abs(l.air_export_j)
            + abs(l.hx_export_j)
            + abs(l.pump_heat_liquid_j)
            for l in ledgers
        )
        tol = 1e-6 + 1e-6 * scale
        node_energy_pass = True
        for name, _ in ledgers[0].node_residuals_j:
            signed = fsum(dict(l.node_residuals_j)[name] for l in ledgers)
            absolute = fsum(abs(dict(l.node_residuals_j)[name]) for l in ledgers)
            node_tol = 1e-6 + 1e-6 * fsum(dict(l.node_scales_j)[name] for l in ledgers)
            node_energy_pass &= abs(signed) <= node_tol and absolute <= node_tol
        mass_pass = True
        for name, _ in ledgers[0].volume_mass_residuals_kg_s:
            signed = fsum(
                dict(l.volume_mass_residuals_kg_s)[name]
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s, l in zip(self.states, self.accepted, ledgers)
            )
            absolute = fsum(
                abs(dict(l.volume_mass_residuals_kg_s)[name])
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s, l in zip(self.states, self.accepted, ledgers)
            )
            mass_tol = 1e-9 + 1e-8 * fsum(
                dict(l.volume_mass_incident_kg_s)[name]
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s, l in zip(self.states, self.accepted, ledgers)
            )
            mass_pass &= abs(signed) <= mass_tol and absolute <= mass_tol
        for name, _ in self.accepted[0].hydraulic.node_mass_residual_kg_s:
            signed = fsum(
                dict(s.hydraulic.node_mass_residual_kg_s)[name]
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s in zip(self.states, self.accepted)
            )
            absolute = fsum(
                abs(dict(s.hydraulic.node_mass_residual_kg_s)[name])
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s in zip(self.states, self.accepted)
            )
            mass_tol = 1e-9 + 1e-8 * fsum(
                dict(s.hydraulic.node_mass_incident_kg_s)[name]
                * (s.next_state.time_ns - before.time_ns)
                / 1e9
                for before, s in zip(self.states, self.accepted)
            )
            mass_pass &= abs(signed) <= mass_tol and absolute <= mass_tol
        all_t = [x.temperature_k for s in self.states for x in (*s.solids, *s.volumes)]
        return {
            "peak_k": max(all_t),
            "final_die_k": self.final_state.solids[0].temperature_k,
            "final_cdu_supply_k": self.final_state.by_id["cdu"].temperature_k,
            "final_return_k": self.final_state.by_id["return_1"].temperature_k,
            "source_j": source,
            "stored_j": storage,
            "air_j": air,
            "hx_j": hx,
            "pump_heat_liquid_j": pump_heat,
            "pump_electrical_j": fsum(l.pump_electrical_j for l in ledgers),
            "pump_hydraulic_j": fsum(l.pump_hydraulic_j for l in ledgers),
            "signed_energy_residual_j": total_residual,
            "sum_abs_energy_residual_j": sum_abs_residual,
            "max_node_energy_residual_j": max(
                abs(r) for l in ledgers for _, r in l.node_residuals_j
            ),
            "max_mass_node_residual_kg_s": max(l.max_mass_node_residual_kg_s for l in ledgers),
            "max_mass_volume_residual_kg_s": max(l.max_mass_volume_residual_kg_s for l in ledgers),
            "max_residual_w": max(
                abs(s.ledger.full_loop_residual_j) / ((s.next_state.time_ns - before.time_ns) / 1e9)
                for before, s in zip(self.states, self.accepted)
            ),
            "p95_residual_w": float(
                np.percentile(
                    [
                        abs(s.ledger.full_loop_residual_j)
                        / ((s.next_state.time_ns - before.time_ns) / 1e9)
                        for before, s in zip(self.states, self.accepted)
                    ],
                    95,
                )
            ),
            "energy_pass": abs(total_residual) <= tol
            and sum_abs_residual <= tol
            and node_energy_pass,
            "mass_pass": mass_pass,
            "steps": len(self.accepted),
            "final_total_flow_kg_s": self.accepted[-1].hydraulic.total_flow_m3_s
            * self.qualification_inputs[0].heat_exchanger.secondary_fluid.density.value,
            "final_pump_dp_pa": self.accepted[-1].hydraulic.pump_head_pa,
        }


def run(plant, controls, duration_ns, dt_ns, events=()):
    require(
        type(duration_ns) is int and duration_ns > 0 and type(dt_ns) is int and dt_ns >= 1000,
        "INVALID_TIME",
        "run",
    )
    require(
        tuple(e.time_ns for e in events) == tuple(sorted({e.time_ns for e in events}))
        and all(0 < e.time_ns < duration_ns for e in events),
        "INVALID_TIME",
        "strict event times",
    )
    state = plant.initial_state
    require(state.time_ns == 0, "INVALID_TIME", "initial epoch")
    current, cursor, accepted = controls, 0, []
    while state.time_ns < duration_ns:
        if cursor < len(events) and state.time_ns == events[cursor].time_ns:
            current = events[cursor].controls
            cursor += 1
        next_event = events[cursor].time_ns if cursor < len(events) else duration_ns
        end = min(state.time_ns + dt_ns, next_event, duration_ns)
        result = step(plant, state, current, end - state.time_ns)
        if result.solver_status != SolverStatus.CONVERGED:
            raise ThermalError("RUN_FAILED", "; ".join(result.diagnostics), result.validity_status)
        accepted.append(result)
        state = result.next_state
    return PlantRun(
        plant.initial_state, tuple(accepted), (plant, controls, duration_ns, tuple(events))
    )


def convergence(runs):
    require(len(runs) == 3, "CONVERGENCE", "three dt required")
    require(
        all(r.qualification_inputs == runs[0].qualification_inputs for r in runs[1:]),
        "CONVERGENCE_INPUT_MISMATCH",
        "only physics dt may change",
    )
    if len({r.mesh for r in runs}) != 3:
        return {"status": "NOT_EVALUABLE", "reason": "identical effective meshes"}
    metrics = [r.metrics() for r in runs]
    # Frozen predeclared scales come from generic configuration ranges, never observed maxima.
    plant = runs[0].qualification_inputs[0]
    flow_scale = (
        plant.pump_curve.flow_range_m3_s[1] * plant.heat_exchanger.secondary_fluid.density.value
    )
    dp_scale = plant.pump_curve.shutoff_head_pa.value
    require(flow_scale > 0 and dp_scale > 0, "CONVERGENCE", "declared positive scales")
    differences = []
    for coarse, fine, cm, fm in zip(runs, runs[1:], metrics, metrics[1:]):
        times = sorted({0, *coarse.mesh} | {0, *fine.mesh})
        node_error, enthalpy_error = 0.0, 0.0
        for name in coarse.initial_state.by_id:
            a = np.interp(
                times,
                [s.time_ns for s in coarse.states],
                [s.by_id[name].temperature_k for s in coarse.states],
            )
            b = np.interp(
                times,
                [s.time_ns for s in fine.states],
                [s.by_id[name].temperature_k for s in fine.states],
            )
            node_error = max(node_error, float(np.max(np.abs(a - b))))
        for name in (v.volume_id for v in coarse.initial_state.volumes):
            a = np.interp(
                times,
                [s.time_ns for s in coarse.states],
                [s.by_id[name].specific_enthalpy_j_kg for s in coarse.states],
            )
            b = np.interp(
                times,
                [s.time_ns for s in fine.states],
                [s.by_id[name].specific_enthalpy_j_kg for s in fine.states],
            )
            enthalpy_error = max(enthalpy_error, float(np.max(np.abs(a - b))))
        flow_error = max(abs(_held_flow(coarse, t) - _held_flow(fine, t)) for t in times[:-1])
        branch_error = max(
            abs(_held_branch(coarse, t, i) - _held_branch(fine, t, i))
            for t in times[:-1]
            for i in range(len(plant.hydraulic_graph.branches))
        )
        dp_error = max(abs(_held_dp(coarse, t) - _held_dp(fine, t)) for t in times[:-1])
        differences.append(
            {
                "peak_k": abs(cm["peak_k"] - fm["peak_k"]),
                "node_k": node_error,
                "enthalpy_j_kg": enthalpy_error,
                "flow_kg_s": flow_error,
                "branch_flow_kg_s": branch_error,
                "dp_pa": dp_error,
                "pump_electrical_j": abs(cm["pump_electrical_j"] - fm["pump_electrical_j"]),
                "pump_hydraulic_j": abs(cm["pump_hydraulic_j"] - fm["pump_hydraulic_j"]),
                "hx_j": abs(cm["hx_j"] - fm["hx_j"]),
                "stored_j": abs(cm["stored_j"] - fm["stored_j"]),
            }
        )
    tolerances = {
        "peak_k": 0.1,
        "node_k": 0.1,
        "enthalpy_j_kg": 0.1 * plant.heat_exchanger.secondary_fluid.specific_heat.value,
        "flow_kg_s": max(1e-9, 0.01 * flow_scale),
        "branch_flow_kg_s": max(1e-9, 0.01 * flow_scale),
        "dp_pa": max(1e-3, 0.01 * dp_scale),
        "pump_electrical_j": max(1.0, 0.01 * abs(metrics[-1]["pump_electrical_j"])),
        "pump_hydraulic_j": max(1.0, 0.01 * abs(metrics[-1]["pump_hydraulic_j"])),
        "hx_j": max(1.0, 0.01 * abs(metrics[-1]["hx_j"])),
        "stored_j": max(1.0, 0.01 * abs(metrics[-1]["stored_j"])),
    }
    ok = all(m["energy_pass"] and m["mass_pass"] for m in metrics)
    for key, tol in tolerances.items():
        a, b = differences[0][key], differences[1][key]
        ok &= a <= tol and b <= tol and (b <= a or max(a, b) <= 0.1 * tol)
    return {
        "status": "PASS" if ok else "FAIL",
        "metrics": metrics,
        "adjacent_differences": differences,
        "tolerances": tolerances,
        "coarse_vs_finest": {
            k: abs(metrics[0][m] - metrics[-1][m])
            for k, m in (
                ("peak_k", "peak_k"),
                ("pump_electrical_j", "pump_electrical_j"),
                ("hx_j", "hx_j"),
                ("stored_j", "stored_j"),
            )
        },
    }


def _held_flow(run, time_ns):
    density = run.qualification_inputs[0].heat_exchanger.secondary_fluid.density.value
    return density * next(
        s.hydraulic.total_flow_m3_s for s in run.accepted if s.next_state.time_ns > time_ns
    )


def _held_branch(run, time_ns, index):
    density = run.qualification_inputs[0].heat_exchanger.secondary_fluid.density.value
    return density * next(
        s.hydraulic.branch_flows_m3_s[index] for s in run.accepted if s.next_state.time_ns > time_ns
    )


def _held_dp(run, time_ns):
    return next(s.hydraulic.pump_head_pa for s in run.accepted if s.next_state.time_ns > time_ns)
