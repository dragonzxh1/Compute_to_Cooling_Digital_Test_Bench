import pytest
from v0_2.thermal.fixtures import gpu_chain, linear_rc, with_power
from v0_2.thermal.harness import BoundaryEvent, convergence, run
from v0_2.thermal.integrator import Method
from v0_2.thermal.validity import ThermalError


@pytest.mark.parametrize("case", ["linear", "chain", "step"])
def test_three_distinct_meshes_converge(case):
    f = linear_rc() if case == "linear" else gpu_chain(power=30.0 if case == "step" else 120.0)
    events = ()
    if case == "step":
        events = (
            BoundaryEvent(20_000_000_000, with_power(f, 120.0).sources, f.boundaries, f.flows),
        )
    runs = [
        run(f, 100_000_000_000, dt, events=events) for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    result = convergence(runs)
    assert result["status"] == "PASS", result
    assert [len(r.substeps) for r in runs] == [500, 1000, 2000]
    exact = run(f, 100_000_000_000, 200_000_000, Method.EXACT_LINEAR, events)
    errors = [
        max(
            abs(a.temperature_k - b.temperature_k)
            for a, b in zip(r.final_state.nodes, exact.final_state.nodes)
        )
        for r in runs
    ]
    assert errors[2] < errors[1] < errors[0]


def test_event_masked_mesh_is_not_evaluable():
    f = gpu_chain()
    events = tuple(
        BoundaryEvent(t, f.sources, f.boundaries, f.flows)
        for t in range(50_000_000, 1_000_000_000, 50_000_000)
    )
    runs = [
        run(f, 1_000_000_000, dt, events=events) for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    assert convergence(runs)["status"] == "NOT_EVALUABLE"


def test_changed_inputs_cannot_pass_dt_qualification():
    runs = [
        run(gpu_chain(power=power), 1_000_000_000, dt)
        for power, dt in ((100, 200_000_000), (100, 100_000_000), (101, 50_000_000))
    ]
    with pytest.raises(ThermalError, match="CONVERGENCE_INPUT_MISMATCH"):
        convergence(runs)


def test_non_multiple_source_event_exact_interval_energy():
    f = gpu_chain(power=0.0)
    event = BoundaryEvent(73_000_000, with_power(f, 100.0).sources, f.boundaries, f.flows)
    r = run(f, 1_000_000_000, 200_000_000, events=(event,))
    assert 73_000_000 in r.mesh
    assert r.metrics()["input_j"] == pytest.approx(92.7)
