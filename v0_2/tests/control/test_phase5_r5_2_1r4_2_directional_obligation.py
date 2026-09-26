"""Candidate acceptance controls: immutable R41 inputs plus reversal counterexamples."""

import json

import pytest

from v0_2.examples.phase5_r5_2_1r4_2_directional_engine import DirectionalObligationTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import synthetic
from v0_2.tests.control import test_phase5_r5_2_1r4_1_deferred_demand as historical


def run(source):
    qualifier = DirectionalObligationTrackingQualifier(historical.PROFILE, historical.CLASSIFIER)
    for item in source:
        qualifier.update(item)
    return qualifier.snapshot()


@pytest.mark.parametrize("name", sorted(name for name in vars(historical) if name.startswith("test_r41_")))
def test_frozen_r41_assertions(name, monkeypatch):
    monkeypatch.setattr(historical, "DeferredDemandTrackingQualifier", DirectionalObligationTrackingQualifier)
    getattr(historical, name)()


def test_watch_and_pair_survive_direction_change():
    rows = run(historical._cases()["R41-7"])["records"]
    before = rows[1]
    for row in rows[2:6]:
        assert row["watch_id"] == before["watch_id"]
        assert row["oldest_unresolved_demand_ns"] == before["oldest_unresolved_demand_ns"]
        assert row["progress_pair_id"] == before["progress_pair_id"]
        assert row["carried_suspicion_evidence"] == before["carried_suspicion_evidence"]
        assert not row["qualified_progress"]
    assert rows[3]["directional_obligation"]["direction"] == -1
    assert rows[6]["directional_obligation"]["established_ns"] == 600_000_000
    assert rows[6]["epoch_expected_direction"] == -1


def test_negative_derivative_without_net_reversal_keeps_direction():
    source = synthetic(historical.PROFILE, {0: 0.5, 200_000_000: 0.8, 600_000_000: 0.7},
                       duration_ns=3_000_000_000, initial_speed=0.5,
                       invalid=(400_000_000, 1_200_000_000))
    result = run(source)
    assert not result["direction_events"]
    assert result["confirmed_latched"]


@pytest.mark.parametrize("reversal_ns", [600_000_000, 1_000_000_000])
def test_healthy_outage_reversal_not_confirmed(reversal_ns):
    source = historical._blackout(historical._normal(
        {0: 0.5, 200_000_000: 0.7, reversal_ns: 0.3}, 4_000_000_000),
        400_000_000, 1_200_000_000)
    result = run(source)
    assert not result["confirmed_latched"]
    assert any(row["qualified_progress"] for row in result["records"])
    recovery = result["records"][6]
    if reversal_ns == 1_000_000_000:
        assert recovery["expected_motion"] == 0
        assert recovery["carried_suspicion_evidence"] == 0


def test_multiple_reversals_preserve_watch():
    source = synthetic(historical.PROFILE,
                       {0: 0.5, 200_000_000: 0.7, 600_000_000: 0.3, 800_000_000: 0.7},
                       duration_ns=4_000_000_000, initial_speed=0.5,
                       invalid=(400_000_000, 1_200_000_000))
    result = run(source)
    assert [event["obligation"]["direction"] for event in result["direction_events"]] == [-1, 1]
    assert result["records"][6]["oldest_unresolved_demand_ns"] == 200_000_000
    assert result["confirmed_latched"]


def test_deferred_only_demand_reverses_before_any_epoch():
    source = synthetic(historical.PROFILE,
                       {0: 0.5, 200_000_000: 0.6, 400_000_000: 0.7, 600_000_000: 0.3},
                       duration_ns=4_000_000_000, initial_speed=0.5,
                       invalid=(400_000_000, 1_200_000_000))
    result = run(source)
    recovery = result["records"][6]
    assert recovery["oldest_unresolved_demand_ns"] == 400_000_000
    assert recovery["directional_obligation"]["established_ns"] == 600_000_000
    assert recovery["epoch_expected_direction"] == -1
    assert recovery["watch_id"] == "motion-watch:1"
    assert result["confirmed_latched"]


def test_prior_suspicion_survives_reversal():
    source = synthetic(historical.PROFILE,
                       {0: 0.5, 200_000_000: 0.7, 1_600_000_000: 0.3},
                       duration_ns=4_000_000_000, initial_speed=0.5,
                       invalid=(1_400_000_000, 2_000_000_000))
    rows = run(source)["records"]
    prior = rows[6]["carried_suspicion_evidence"]
    # This original control is suspected, but has not yet reached the frozen
    # confirmation-evidence motion threshold. Preserve it as a zero-count case.
    assert rows[6]["state"] == "TRACKING_FAULT_SUSPECTED"
    assert prior == 0
    assert all(row["carried_suspicion_evidence"] == prior for row in rows[7:10])


def test_nonzero_suspicion_count_survives_reversal():
    source = synthetic(historical.PROFILE,
                       {0: 0.5, 200_000_000: 0.7, 1_800_000_000: 0.3},
                       duration_ns=4_000_000_000, initial_speed=0.5,
                       invalid=(1_600_000_000, 2_400_000_000))
    rows = run(source)["records"]
    prior = rows[7]["carried_suspicion_evidence"]
    assert prior == 1
    assert all(row["carried_suspicion_evidence"] == prior for row in rows[8:12])
    assert rows[12]["oldest_unresolved_demand_ns"] == 200_000_000


def test_repeatability_and_prefix_causality():
    source = historical._cases()["R41-7"]
    result = run(source)
    assert json.dumps(result, sort_keys=True) == json.dumps(run(source), sort_keys=True)
    for stop in range(1, len(source) + 1):
        assert run(source[:stop])["records"] == result["records"][:stop]
