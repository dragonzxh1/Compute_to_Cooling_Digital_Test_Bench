import math

import pytest
from v0_2.coolant.advection import AdvectiveLink, solve_implicit
from v0_2.plant.fixtures import generic_fluid, volume
from v0_2.thermal.validity import ThermalError, ValidityStatus


def test_single_volume_exponential_and_energy():
    fluid = generic_fluid()
    state = volume("cell", fluid, mass=1.0)
    links = (
        AdvectiveLink("in", "inlet", "cell", 0.2, "in"),
        AdvectiveLink("out", "cell", "outlet", 0.2, "out"),
    )
    for _ in range(100):
        result = solve_implicit(
            (state,), links, 0.05, {"inlet": fluid.h(310), "outlet": fluid.h(300)}
        )
        assert max(abs(x[1]) for x in result.volume_energy_residual_j) < 1e-6
        assert result.volume_mass_residual_kg_s == (("cell", 0.0),)
        state = result.volumes[0]
    exact = 310 - 10 * math.exp(-0.2 * 5)
    assert abs(state.temperature_k - exact) < 0.02
    assert state.mass_kg.value == 1
    assert state.residence_time_s(0.2) == 5.0
    assert state.residence_time_s(0.4) == 2.5


def test_single_volume_mesh_converges_to_independent_exponential():
    fluid = generic_fluid()
    links = (
        AdvectiveLink("in", "inlet", "cell", 0.2, "in"),
        AdvectiveLink("out", "cell", "outlet", 0.2, "out"),
    )
    exact = 310 - 10 * math.exp(-1)
    errors = []
    for dt in (0.2, 0.1, 0.05):
        state = volume("cell", fluid, mass=1.0)
        for _ in range(round(5 / dt)):
            state = solve_implicit(
                (state,), links, dt, {"inlet": fluid.h(310), "outlet": fluid.h(300)}
            ).volumes[0]
        errors.append(abs(state.temperature_k - exact))
    assert errors[2] < errors[1] < errors[0]


def test_series_volumes_step_has_causal_delay_and_closed_form():
    fluid = generic_fluid()
    states = (volume("one", fluid, mass=1.0), volume("two", fluid, mass=1.0))
    links = (
        AdvectiveLink("in", "inlet", "one", 0.2, "in"),
        AdvectiveLink("middle", "one", "two", 0.2, "middle"),
        AdvectiveLink("out", "two", "outlet", 0.2, "out"),
    )
    first = solve_implicit(states, links, 0.05, {"inlet": fluid.h(310), "outlet": 0})
    assert first.volumes[0].temperature_k > first.volumes[1].temperature_k > 300
    states = first.volumes
    for _ in range(99):
        states = solve_implicit(states, links, 0.05, {"inlet": fluid.h(310), "outlet": 0}).volumes
    exact_first = 310 - 10 * math.exp(-1)
    exact_second = 310 - 10 * math.exp(-1) * (1 + 1)
    assert abs(states[0].temperature_k - exact_first) < 0.02
    assert abs(states[1].temperature_k - exact_second) < 0.02
    assert all(v.mass_kg.value == 1 for v in states)


def test_zero_flow_keeps_mass_and_enthalpy():
    state = volume("still", generic_fluid(), temperature=306)
    result = solve_implicit((state,), (), 0.2)
    assert result.volumes == (state,)
    assert state.residence_time_s(0) is None


def test_reverse_flow_changes_upstream_donor():
    fluid = generic_fluid()
    a, b = volume("a", fluid, temperature=310), volume("b", fluid, temperature=300)
    links = (
        AdvectiveLink("reverse", "a", "b", -0.1, "reverse", True),
        AdvectiveLink("forward", "a", "b", 0.1, "forward"),
    )
    result = solve_implicit((a, b), links, 0.1)
    by_id = {t.link_id: t for t in result.transfers}
    assert by_id["reverse"].donor_id == "b"
    assert by_id["reverse"].receiver_id == "a"
    assert by_id["forward"].donor_id == "a"
    assert by_id["reverse"].energy_j < by_id["forward"].energy_j
    assert sum(t.energy_j for t in result.transfers if t.link_id == "reverse") == pytest.approx(
        0.01 * result.volumes[1].specific_enthalpy_j_kg
    )
    with pytest.raises(ThermalError) as error:
        AdvectiveLink("bad", "a", "b", -0.1, "bad")
    assert error.value.status == ValidityStatus.MODEL_INVALID


def test_mass_imbalance_and_duplicate_owner_fail():
    fluid = generic_fluid()
    a, b = volume("a", fluid), volume("b", fluid)
    with pytest.raises(ThermalError, match="MASS_BALANCE_FAIL"):
        solve_implicit((a, b), (AdvectiveLink("ab", "a", "b", 0.1, "owner"),), 0.1)
    from dataclasses import replace

    with pytest.raises(ThermalError, match="VOLUME_OWNERSHIP_DUPLICATE"):
        solve_implicit((a, replace(b, storage_owner_id=a.storage_owner_id)), (), 0.1)
