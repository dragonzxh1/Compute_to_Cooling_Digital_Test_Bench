from c2c.cdu.heat_exchanger import counterflow_effectiveness, exchange


def test_effectiveness_is_bounded_and_increases_with_ua():
    low = counterflow_effectiveness(10_000, 15_000, 2_000)
    high = counterflow_effectiveness(10_000, 15_000, 8_000)
    assert 0 <= low < high <= 1


def test_outlet_temperatures_are_physical():
    result = exchange(40, 20, 4, 5, 4180, 4180, 15_000)
    assert 20 <= result.secondary_outlet_temp_c <= 40
    assert 20 <= result.primary_outlet_temp_c <= 40
    assert result.heat_rejected_w <= 4 * 4180 * 20 + 1e-9


def test_no_flow_means_no_heat_rejection():
    result = exchange(40, 20, 0, 5, 4180, 4180, 15_000)
    assert result.heat_rejected_w == 0
    assert result.secondary_outlet_temp_c == 40
