from dataclasses import dataclass
from enum import StrEnum
from math import fsum

import numpy as np

from .energy_ledger import EnergyLedger, InterfaceEnergy, cumulative_balances
from .state import ThermalState
from .validity import SolverStatus, ThermalError, ValidityStatus, interval, require


class Method(StrEnum):
    EXPLICIT_EULER = "EXPLICIT_EULER"
    BACKWARD_EULER = "CONSERVATIVE_BACKWARD_EULER"
    EXACT_LINEAR = "EXACT_LINEAR_REFERENCE"


@dataclass(frozen=True)
class AcceptedSubstep:
    start_ns: int
    end_ns: int
    state: ThermalState
    ledger: EnergyLedger


@dataclass(frozen=True)
class StepResult:
    next_state: ThermalState
    integrated_interface_energy_j: tuple[tuple[str, float], ...]
    source_energy_j: float
    energy_residual_j: tuple[tuple[str, float], ...]
    solver_status: SolverStatus
    validity_status: ValidityStatus
    iterations: int
    accepted_substeps: tuple[AcceptedSubstep, ...]
    diagnostics: tuple[str, ...]


class ThermalIntegrator:
    """Constant-C, interval-held linear conductances. No nonlinear/variable-C solver implied."""

    MAX_ITERATIONS = 25
    MAX_STEP_HALVINGS = 10
    MIN_DT_NS = 1000

    def __init__(self, topology, source_map, method=Method.BACKWARD_EULER):
        require(isinstance(method, Method), "INTEGRATOR", "unknown method")
        self.topology, self.source_map, self.method = topology, source_map, method

    def step(self, state, sources, boundaries, interfaces, flow_inputs, t_ns, dt_ns):
        diagnostics, attempts = [], [0]
        try:
            interval(t_ns, dt_ns)
            require(t_ns == state.time_ns, "INVALID_TIME", "state/start mismatch")
            require(dt_ns >= self.MIN_DT_NS, "MINIMUM_DT", "minimum is 1 microsecond")
            require(tuple(interfaces) == self.topology.interfaces, "TOPOLOGY", "interface mismatch")
            self.topology.validate_state(state)
            boundary_ids = {e.external_boundary_id for e in interfaces if e.external_boundary_id}
            require(set(boundaries) == boundary_ids, "BOUNDARY_CONFIG", "missing/extra boundary")
            flow_ids = {
                e.interface_id for e in interfaces if e.kind.value == "COLDPLATE_FLOW_DEPENDENT"
            }
            require(set(flow_inputs) == flow_ids, "FLOW_CONFIG", "missing/extra local flow")
            for record in boundaries.values():
                require(record.si("K") > 0, "BOUNDARY_CONFIG", "temperature must be positive")
            self.source_map.receipts(sources, state.by_id(), t_ns, dt_ns)
            accepted = self._advance(
                state, tuple(sources), boundaries, flow_inputs, dt_ns, 0, attempts, diagnostics
            )
            totals = cumulative_balances([s.ledger for s in accepted])
            require(
                all(v["passed"] for v in totals.values()),
                "ENERGY_BALANCE_FAIL",
                "cumulative",
                ValidityStatus.MODEL_INVALID,
            )
            energies = tuple(
                (
                    e.interface_id,
                    fsum(
                        next(
                            f.energy_j
                            for f in s.ledger.interfaces
                            if f.interface_id == e.interface_id
                        )
                        for s in accepted
                    ),
                )
                for e in interfaces
            )
            return StepResult(
                accepted[-1].state,
                energies,
                fsum(r.energy_j for s in accepted for r in s.ledger.sources),
                tuple((k, v["signed_residual_j"]) for k, v in totals.items()),
                SolverStatus.CONVERGED,
                ValidityStatus.VALID,
                attempts[0],
                tuple(accepted),
                tuple(diagnostics),
            )
        except ThermalError as error:
            return StepResult(
                state,
                (),
                0.0,
                (),
                SolverStatus.FAILED,
                error.status,
                attempts[0],
                (),
                (*diagnostics, str(error)),
            )

    def _advance(self, state, sources, boundaries, flows, dt_ns, depth, attempts, diagnostics):
        try:
            attempts[0] += 1
            return [self._attempt(state, sources, boundaries, flows, dt_ns)]
        except (np.linalg.LinAlgError, FloatingPointError) as error:
            diagnostics.append(f"linear solve failed: {error}")
        except ThermalError as error:
            if error.code not in {"EULER_STABILITY", "SOLVER_RESIDUAL", "ENERGY_BALANCE_FAIL"}:
                raise
            diagnostics.append(str(error))
        left = dt_ns // 2
        require(
            depth < self.MAX_STEP_HALVINGS and left >= self.MIN_DT_NS,
            "SOLVER_RETRIES_EXHAUSTED",
            f"halvings={depth}; dt_ns={dt_ns}",
            ValidityStatus.MODEL_INVALID,
        )
        diagnostics.append(f"retry depth={depth + 1}; substeps={left},{dt_ns - left}")
        first = self._advance(
            state, sources, boundaries, flows, left, depth + 1, attempts, diagnostics
        )
        second = self._advance(
            first[-1].state,
            sources,
            boundaries,
            flows,
            dt_ns - left,
            depth + 1,
            attempts,
            diagnostics,
        )
        return first + second

    def _attempt(self, state, sources, boundaries, flows, dt_ns):
        self.topology.validate_state(state)
        nodes, edges = state.nodes, self.topology.interfaces
        index = {n.node_id: i for i, n in enumerate(nodes)}
        old_t = np.array([n.temperature_k for n in nodes], dtype=float)
        c = np.array([n.thermal_capacitance.value for n in nodes], dtype=float)
        anchor = old_t[0]
        x = old_t - anchor
        dt = dt_ns / 1e9
        lap = np.zeros((len(nodes), len(nodes)))
        forcing = np.zeros(len(nodes))
        receipts = self.source_map.receipts(sources, state.by_id(), state.time_ns, dt_ns)
        for receipt in receipts:
            forcing[index[receipt.thermal_node_id]] += receipt.power_w
        conductances = []
        for edge in edges:
            i = index[edge.hot_node_id]
            j = index.get(edge.cold_node_id)
            cold = old_t[j] if j is not None else boundaries[edge.external_boundary_id].value
            g = edge.conductance(old_t[i], cold, flows.get(edge.interface_id))
            conductances.append(g)
            lap[i, i] += g
            if j is not None:
                lap[j, j] += g
                lap[i, j] -= g
                lap[j, i] -= g
            else:
                forcing[i] += g * (cold - anchor)
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            if self.method == Method.EXPLICIT_EULER:
                require(
                    np.all(dt * np.diag(lap) / c <= 1),
                    "EULER_STABILITY",
                    "RC positivity bound exceeded",
                    ValidityStatus.MODEL_INVALID,
                )
                nx = x + dt * (forcing - lap @ x) / c
                integrated_x = dt * x
            elif self.method == Method.BACKWARD_EULER:
                # Solve temperature increments to avoid subtracting large absolute temperatures.
                delta = np.linalg.solve(np.diag(c) + dt * lap, dt * (forcing - lap @ x))
                nx = x + delta
                integrated_x = dt * nx
            else:
                # Symmetric capacitance transform gives an independent exact linear reference.
                sqrt_c = np.sqrt(c)
                eigenvalues, vectors = np.linalg.eigh(-lap / sqrt_c[:, None] / sqrt_c[None, :])
                y0 = vectors.T @ (sqrt_c * x)
                drive = vectors.T @ (forcing / sqrt_c)
                z = eigenvalues * dt
                phi, psi = np.empty_like(z), np.empty_like(z)
                small = np.abs(z) < 1e-4
                zs = z[small]
                phi[small] = dt * (1 + zs / 2 + zs**2 / 6 + zs**3 / 24 + zs**4 / 120)
                psi[small] = dt**2 * (0.5 + zs / 6 + zs**2 / 24 + zs**3 / 120 + zs**4 / 720)
                phi[~small] = np.expm1(z[~small]) / eigenvalues[~small]
                psi[~small] = (np.expm1(z[~small]) - z[~small]) / eigenvalues[~small] ** 2
                nx = (vectors @ (np.exp(z) * y0 + phi * drive)) / sqrt_c
                integrated_x = (vectors @ (phi * y0 + psi * drive)) / sqrt_c
        new_t = nx + anchor
        require(
            np.all(np.isfinite(new_t)) and np.all(np.isfinite(integrated_x)),
            "SOLVER_RESIDUAL",
            "nonfinite numerical result",
            ValidityStatus.MODEL_INVALID,
        )
        after = ThermalState(
            tuple(n.at_temperature(t) for n, t in zip(nodes, new_t)), state.time_ns + dt_ns
        )
        fluxes = []
        for edge, g in zip(edges, conductances):
            i, j = index[edge.hot_node_id], index.get(edge.cold_node_id)
            cold_new = new_t[j] if j is not None else boundaries[edge.external_boundary_id].value
            # Check accepted constitutive domain as well as the interval start.
            edge.conductance(new_t[i], cold_new, flows.get(edge.interface_id))
            cold_integral = integrated_x[j] if j is not None else dt * (cold_new - anchor)
            energy = float(g * (integrated_x[i] - cold_integral))
            fluxes.append(
                InterfaceEnergy(
                    edge.interface_id,
                    edge.hot_node_id,
                    edge.cold_node_id,
                    edge.external_boundary_id,
                    energy,
                    state.time_ns,
                    after.time_ns,
                    edge.owner_id,
                    edge.kind.value,
                    edge.boundary_medium,
                )
            )
        ledger = EnergyLedger.build(state, after, receipts, fluxes, self.topology.device_cvs)
        require(
            all(b.passed for b in ledger.balances),
            "ENERGY_BALANCE_FAIL",
            "interval CV",
            ValidityStatus.MODEL_INVALID,
        )
        # Frozen state residual normalization applies to every node, including reference-zero E.
        for node in nodes:
            b = ledger.balance(f"node:{node.node_id}")
            exchange = fsum(
                abs(f.energy_j) for f in fluxes if node.node_id in (f.hot_node_id, f.cold_node_id)
            )
            scale = max(1e-6, 1e-9 * max(abs(b.stored_change_j), abs(b.source_energy_j) + exchange))
            require(
                abs(b.residual_j) <= scale,
                "SOLVER_RESIDUAL",
                node.node_id,
                ValidityStatus.MODEL_INVALID,
            )
        return AcceptedSubstep(state.time_ns, after.time_ns, after, ledger)
