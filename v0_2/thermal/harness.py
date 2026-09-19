from dataclasses import dataclass
from math import fsum

import numpy as np

from .energy_ledger import cumulative_balances
from .integrator import Method, ThermalIntegrator
from .validity import SolverStatus, ThermalError, ValidityStatus, require


@dataclass(frozen=True)
class BoundaryEvent:
    time_ns: int
    sources: tuple
    boundaries: tuple
    flows: tuple


@dataclass(frozen=True)
class Run:
    initial_state: object
    substeps: tuple
    qualification_inputs: tuple

    @property
    def final_state(self):
        return self.substeps[-1].state

    @property
    def mesh(self):
        return tuple(s.end_ns for s in self.substeps)

    @property
    def states(self):
        return (self.initial_state, *(s.state for s in self.substeps))

    def metrics(self, reference_limit_k=400.0):
        temperatures = [n.temperature_k for s in self.states for n in s.nodes]
        ledgers = [s.ledger for s in self.substeps]
        balance = cumulative_balances(ledgers)
        fluxes = [f for ledger in ledgers for f in ledger.interfaces]
        equivalent_w = [
            abs(b.residual_j) / ((s.end_ns - s.start_ns) / 1e9)
            for s in self.substeps
            for b in s.ledger.balances
        ]
        return {
            "peak_k": max(temperatures),
            "min_headroom_k": reference_limit_k - max(temperatures),
            "reference_limit_kind": "NUMERICAL_TEST_REFERENCE",
            "final_k": self.final_state.nodes[0].temperature_k,
            "input_j": fsum(r.energy_j for ledger in ledgers for r in ledger.sources),
            "stored_j": fsum(n.energy_j for n in self.final_state.nodes)
            - fsum(n.energy_j for n in self.initial_state.nodes),
            "air_j": fsum(f.energy_j for f in fluxes if f.boundary_medium == "AIR"),
            "liquid_j": fsum(f.energy_j for f in fluxes if f.boundary_medium == "LIQUID"),
            "plate_to_liquid_j": fsum(
                f.energy_j for f in fluxes if f.mechanism == "COLDPLATE_FLOW_DEPENDENT"
            ),
            "residual_j": balance["subsystem"]["signed_residual_j"],
            "max_cv_residual_j": max(abs(b.residual_j) for l in ledgers for b in l.balances),
            "sum_abs_residual_j": balance["subsystem"]["absolute_residual_j"],
            "max_residual_w": max(equivalent_w),
            "p95_residual_w": float(np.percentile(equivalent_w, 95)),
            "energy_pass": all(v["passed"] for v in balance.values()),
            "substeps": len(self.substeps),
        }


def run(fixture, duration_ns, dt_ns, method=Method.BACKWARD_EULER, events=()):
    require(
        type(duration_ns) is int and duration_ns > 0 and type(dt_ns) is int and dt_ns > 0,
        "INVALID_TIME",
        "run duration/dt",
    )
    require(
        all(type(e.time_ns) is int and 0 < e.time_ns < duration_ns for e in events)
        and tuple(e.time_ns for e in events) == tuple(sorted({e.time_ns for e in events})),
        "INVALID_TIME",
        "strictly ordered unique internal events",
    )
    state = fixture.topology.initial_state
    require(state.time_ns == 0, "INVALID_TIME", "fixture starts at0")
    solver = ThermalIntegrator(fixture.topology, fixture.source_map, method)
    active = BoundaryEvent(0, fixture.sources, fixture.boundaries, fixture.flows)
    cursor, accepted = 0, []
    while state.time_ns < duration_ns:
        if cursor < len(events) and events[cursor].time_ns == state.time_ns:
            active = events[cursor]
            cursor += 1
        next_event = events[cursor].time_ns if cursor < len(events) else duration_ns
        end = min(state.time_ns + dt_ns, next_event, duration_ns)
        result = solver.step(
            state,
            active.sources,
            dict(active.boundaries),
            fixture.topology.interfaces,
            dict(active.flows),
            state.time_ns,
            end - state.time_ns,
        )
        if result.solver_status != SolverStatus.CONVERGED:
            raise ThermalError("RUN_FAILED", "; ".join(result.diagnostics), result.validity_status)
        accepted.extend(result.accepted_substeps)
        state = result.next_state
    return Run(
        fixture.topology.initial_state,
        tuple(accepted),
        (fixture, duration_ns, method, tuple(events)),
    )


def convergence(runs):
    """Frozen thermal gates; no pump/control metrics in Phase3. Extra heat tolerance is explicit."""
    require(len(runs) == 3, "CONVERGENCE", "three refinements required")
    require(
        all(r.qualification_inputs == runs[0].qualification_inputs for r in runs[1:]),
        "CONVERGENCE_INPUT_MISMATCH",
        "only dt may differ: topology, inputs, events, duration and method must match",
    )
    if len({r.mesh for r in runs}) != 3:
        return {"status": "NOT_EVALUABLE", "reason": "identical effective meshes"}
    metrics = [r.metrics() for r in runs]
    differences = []
    for coarse, fine, cm, fm in zip(runs, runs[1:], metrics, metrics[1:]):
        times = sorted({0, *coarse.mesh} | {0, *fine.mesh})
        node_error = 0.0
        for i in range(len(coarse.initial_state.nodes)):
            a = np.interp(
                times,
                [s.time_ns for s in coarse.states],
                [s.nodes[i].temperature_k for s in coarse.states],
            )
            b = np.interp(
                times,
                [s.time_ns for s in fine.states],
                [s.nodes[i].temperature_k for s in fine.states],
            )
            node_error = max(node_error, float(np.max(np.abs(a - b))))
        d = {
            "peak_k": abs(cm["peak_k"] - fm["peak_k"]),
            "headroom_k": abs(cm["min_headroom_k"] - fm["min_headroom_k"]),
            "node_temperature_k": node_error,
        }
        for key in ("air_j", "liquid_j", "plate_to_liquid_j"):
            d[key] = abs(cm[key] - fm[key])
        differences.append(d)
    # Additional heat-export numerical fixture criterion, not an amendment to frozen Contract11:
    # max(1J, 1% finest heat), declared before executing examples/tests.
    tolerances = {"peak_k": 0.1, "headroom_k": 0.1, "node_temperature_k": 0.1}
    tolerances.update(
        {
            k: max(1.0, 0.01 * abs(metrics[-1][k]))
            for k in ("air_j", "liquid_j", "plate_to_liquid_j")
        }
    )
    ok = all(m["energy_pass"] for m in metrics)
    for key, tol in tolerances.items():
        a, b = differences[0][key], differences[1][key]
        ok &= a <= tol and b <= tol and (b <= a or max(a, b) <= 0.1 * tol)
    return {
        "status": "PASS" if ok else "FAIL",
        "adjacent_differences": differences,
        "tolerances": tolerances,
        "metrics": metrics,
        "validity": ValidityStatus.VALID.value,
    }
