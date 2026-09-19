import math
from dataclasses import replace

import numpy as np
import pytest
from v0_2.thermal.fixtures import insulated, linear_rc, resistor
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import Method, ThermalIntegrator
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.topology import ThermalTopology
from v0_2.thermal.validity import SolverStatus, ThermalError, ValidityStatus


@pytest.mark.parametrize("method", list(Method))
def test_boundary_rc_against_closed_form(method):
    exact = 300 + 20 * math.exp(-2)
    errors = []
    for dt in (200_000_000, 100_000_000, 50_000_000):
        r = run(linear_rc(), 100_000_000_000, dt, method)
        errors.append(abs(r.final_state.nodes[0].temperature_k - exact))
        assert r.metrics()["energy_pass"]
    if method == Method.EXACT_LINEAR:
        assert max(errors) < 1e-9
    else:
        assert errors[2] < errors[1] < errors[0] < 0.02


def test_failed_solver_bounded_retries_no_commit(monkeypatch):
    f = linear_rc()

    def fail(*args):
        raise np.linalg.LinAlgError("injected failure")

    monkeypatch.setattr(np.linalg, "solve", fail)
    solver = ThermalIntegrator(f.topology, f.source_map)
    state = f.topology.initial_state
    result = solver.step(state, (), dict(f.boundaries), f.topology.interfaces, {}, 0, 200_000_000)
    assert result.solver_status == SolverStatus.FAILED
    assert result.next_state is state and result.accepted_substeps == ()
    assert result.iterations == 11
    assert any("SOLVER_RETRIES_EXHAUSTED" in d for d in result.diagnostics)


def test_retry_recovery_stays_backward_euler(monkeypatch):
    f = linear_rc()
    solve = np.linalg.solve
    calls = []

    def first_fails(*args):
        calls.append(1)
        if len(calls) == 1:
            raise np.linalg.LinAlgError("transient")
        return solve(*args)

    monkeypatch.setattr(np.linalg, "solve", first_fails)
    solver = ThermalIntegrator(f.topology, f.source_map)
    result = solver.step(
        f.topology.initial_state, (), dict(f.boundaries), f.topology.interfaces, {}, 0, 200_000_000
    )
    assert result.solver_status == SolverStatus.CONVERGED
    assert len(result.accepted_substeps) == 2
    expected = 300 + 20 / (1 + 0.1 / 50) ** 2
    assert result.next_state.nodes[0].temperature_k == pytest.approx(expected, abs=1e-10)


def test_partial_retry_failure_rolls_back_entire_step(monkeypatch):
    f = linear_rc()
    solver = ThermalIntegrator(f.topology, f.source_map)
    original = solver._attempt

    def attempt(state, sources, bounds, flows, dt):
        if dt == 200_000_000:
            raise ThermalError("SOLVER_RESIDUAL", "retry", ValidityStatus.MODEL_INVALID)
        if state.time_ns > 0:
            raise ThermalError("MODEL_INVALID", "second substep", ValidityStatus.MODEL_INVALID)
        return original(state, sources, bounds, flows, dt)

    monkeypatch.setattr(solver, "_attempt", attempt)
    state = f.topology.initial_state
    result = solver.step(state, (), dict(f.boundaries), f.topology.interfaces, {}, 0, 200_000_000)
    assert result.solver_status == SolverStatus.FAILED and result.next_state is state
    assert not result.accepted_substeps and not result.integrated_interface_energy_j


def test_euler_positivity_uses_declared_substeps():
    f = linear_rc()
    edge = resistor("sink", "die", "ambient", 0.0005, boundary=True, medium="AIR")
    f = replace(
        f, topology=ThermalTopology(f.topology.initial_state, (edge,), f.topology.device_cvs)
    )
    r = run(f, 200_000_000, 200_000_000, Method.EXPLICIT_EULER)
    assert len(r.substeps) >= 4
    assert all(300 <= s.state.nodes[0].temperature_k <= 320 for s in r.substeps)


def test_outside_temperature_range_not_clipped():
    f = insulated()
    f = replace(f, sources=(replace(f.sources[0], power=p("P", 1e9, "W")),))
    solver = ThermalIntegrator(f.topology, f.source_map)
    result = solver.step(f.topology.initial_state, f.sources, {}, (), {}, 0, 1_000_000_000)
    assert result.solver_status == SolverStatus.FAILED
    assert result.validity_status == ValidityStatus.MODEL_OUT_OF_RANGE
    assert result.next_state is f.topology.initial_state
