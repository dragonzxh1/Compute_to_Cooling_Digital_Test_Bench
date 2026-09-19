from v0_2.thermal.fixtures import gpu_chain
from v0_2.thermal.harness import run


def test_same_power_different_network_changes_split_and_storage():
    fixtures = (gpu_chain(), gpu_chain(conduction_r=0.2), gpu_chain(air_r=0.2))
    runs = [run(f, 100_000_000_000, 100_000_000) for f in fixtures]
    results = [r.metrics() for r in runs]
    assert all(f.sources == fixtures[0].sources for f in fixtures)
    assert all(m["input_j"] == 12000.0 for m in results)
    a, b, c = results
    assert b["plate_to_liquid_j"] < a["plate_to_liquid_j"]
    assert c["air_j"] > a["air_j"]
    assert len({round(m["stored_j"], 4) for m in results}) == 3
    assert all(m["energy_pass"] for m in results)
