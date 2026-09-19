from dataclasses import replace
from math import exp

import pytest
from v0_2.cdu.heat_exchanger import Arrangement, evaluate
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import PlantEvent, run
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.validity import ThermalError


def test_counterflow_equal_capacity_independent_reference():
    hx = physical_fixture()[0].heat_exchanger
    result = evaluate(hx, 0.2, 0.2, 320, 300)
    c = 0.2 * 4000
    ntu = 100 / c
    expected_effectiveness = ntu / (1 + ntu)
    expected_q = expected_effectiveness * c * 20
    assert result.effectiveness == pytest.approx(expected_effectiveness, abs=1e-12)
    assert result.secondary_out_w == pytest.approx(expected_q, abs=1e-10)
    assert result.secondary_outlet_k == pytest.approx(320 - expected_q / c)
    assert result.primary_outlet_k == pytest.approx(300 + expected_q / c)
    assert result.secondary_out_w - result.primary_in_w == pytest.approx(0, abs=1e-12)


def test_counterflow_unequal_and_parallel_independent_reference():
    hx = physical_fixture()[0].heat_exchanger
    actual = evaluate(hx, 0.2, 0.4, 320, 300)
    cmin, cmax = 800, 1600
    cr, ntu = cmin / cmax, 100 / cmin
    expected = (1 - exp(-ntu * (1 - cr))) / (1 - cr * exp(-ntu * (1 - cr)))
    assert actual.effectiveness == pytest.approx(expected)
    parallel = evaluate(replace(hx, arrangement=Arrangement.PARALLEL), 0.2, 0.4, 320, 300)
    expected_parallel = (1 - exp(-ntu * (1 + cr))) / (1 + cr)
    assert parallel.effectiveness == pytest.approx(expected_parallel)
    assert parallel.effectiveness < actual.effectiveness


def test_fws_hotter_and_flow_reduction_reduce_cooling():
    hx = physical_fixture()[0].heat_exchanger
    base = evaluate(hx, 0.25, 0.4, 310, 290)
    hot = evaluate(hx, 0.25, 0.4, 310, 294)
    low_flow = evaluate(hx, 0.25, 0.28, 310, 290)
    assert hot.secondary_out_w < base.secondary_out_w
    assert low_flow.secondary_out_w < base.secondary_out_w
    zero = evaluate(hx, 0.25, 0, 310, 290)
    assert zero.secondary_out_w == 0
    assert zero.primary_outlet_k == 290


def test_fws_disturbances_change_finite_cdu_supply_dynamically():
    plant, controls = physical_fixture()
    warmer = replace(controls, fws_inlet_temperature=p("FWS_warm", 294, "K"))
    reduced = replace(controls, primary_mass_flow=p("FWS_reduced", 0.28, "kg/s"))
    end = 10_000_000_000
    event_time = 5_000_000_000
    base = run(plant, controls, end, 200_000_000)
    hot = run(plant, controls, end, 200_000_000, (PlantEvent(event_time, warmer),))
    less = run(plant, controls, end, 200_000_000, (PlantEvent(event_time, reduced),))
    assert hot.final_state.by_id["cdu"].temperature_k > base.final_state.by_id["cdu"].temperature_k
    assert less.final_state.by_id["cdu"].temperature_k > base.final_state.by_id["cdu"].temperature_k
    assert hot.final_state.by_id["cdu"].temperature_k < 300
    assert hot.accepted[-1].hx.secondary_out_w < base.accepted[-1].hx.secondary_out_w
    assert hot.metrics()["energy_pass"] and less.metrics()["energy_pass"]


def test_hx_rated_capacity_and_primary_isolation():
    hx = physical_fixture()[0].heat_exchanger
    with pytest.raises(ThermalError, match="HX_CAPACITY_OUT_OF_RANGE"):
        evaluate(replace(hx, rated_capacity_w=p("rated", 10, "W")), 0.3, 0.4, 320, 290)
    with pytest.raises(ThermalError, match="PRIMARY_SECONDARY_MIX"):
        replace(hx, primary_fluid=hx.secondary_fluid)
    with pytest.raises(ThermalError, match="HX_FLOW_OUT_OF_RANGE"):
        evaluate(hx, 0.3, 2.1, 320, 290)
