import math

import pytest
from v0_2.thermal.fixtures import pair
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import Method


@pytest.mark.parametrize("method", list(Method))
def test_two_node_analytic_and_equilibrium(method):
    r = run(pair(), 200_000_000_000, 100_000_000, method)
    difference = 30 * math.exp(-200 * (1 / 100 + 1 / 200) / 0.5)
    expected = (300 + 2 * difference / 3, 300 - difference / 3)
    for n, value in zip(r.final_state.nodes, expected):
        assert n.temperature_k == pytest.approx(value, abs=0.001)
    assert abs(r.metrics()["stored_j"]) < 1e-7
    assert r.metrics()["energy_pass"]


def test_exact_pair_matches_closed_form():
    r = run(pair(), 10_000_000_000, 200_000_000, Method.EXACT_LINEAR)
    d = 30 * math.exp(-0.03 * 10)
    assert r.final_state.nodes[0].temperature_k == pytest.approx(300 + 2 * d / 3, abs=1e-10)
