"""Generate bounded R4.2 evidence and expose inherited startup qualification gaps."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from v0_2.examples.phase5_r5_2_1r4_1_deferred_engine import DeferredDemandTrackingQualifier
from v0_2.examples.phase5_r5_2_1r4_2_directional_engine import DirectionalObligationTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_validation import build_cases, states
from v0_2.tests.control.test_phase5_r5_2_1r4_1_deferred_demand import _cases

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main():
    profile = load("phase5_r5_2_2_fixture_tracking_profile.json")
    classifier = load("phase5_r5_2_silent_tracking_fault_registration.json")["classifier"]

    def replay(engine, source):
        q = engine(profile, classifier)
        for item in source:
            q.update(item)
        return q.snapshot()

    source = _cases()["R41-7"]
    fixed = replay(DirectionalObligationTrackingQualifier, source)
    historical = build_cases(profile, load("phase5_r5_2_silent_tracking_fault_evidence.json"),
                             load("phase5_r5_2_2_tracking_calibration_evidence.json"))
    comparison = {}
    for name, observations in historical.items():
        before = replay(DeferredDemandTrackingQualifier, observations)
        after = replay(DirectionalObligationTrackingQualifier, observations)
        comparison[name] = {
            "r41_states": states(before), "r42_states": states(after),
            "r42_resolved_pair": after["resolved_pair"],
            "input_sha256": hashlib.sha256(json.dumps(
                [asdict(item) for item in observations], sort_keys=True).encode()).hexdigest(),
        }
    must_confirm = ("S2", "S4", "S6", "S8_stuck", "S12", "S15", "S16", "S16_variant")
    missed = [name for name in must_confirm
              if "TRACKING_FAULT_CONFIRMED" not in comparison[name]["r42_states"]]
    evidence = {
        "status": "BLOCKED_INHERITED_STARTUP_BASELINE_GAP" if missed else "FURTHER_QUALIFICATION_REQUIRED",
        "scope": "Offline numerical fixture; not production or hardware validation",
        "r41_7_input": [asdict(item) for item in source],
        "r41_7_candidate": fixed,
        "historical_state_comparison": comparison,
        "mandatory_confirmation_missing": missed,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "phase5_r5_2_2_fixture_tracking_profile.json",
                "v0_2/examples/phase5_r5_2_1r4_paired_engine.py",
                "v0_2/examples/phase5_r5_2_1r4_1_deferred_engine.py",
                "v0_2/examples/phase5_r5_2_1r4_2_directional_engine.py",
            )
        },
        "full_historical_acceptance_completed": False,
        "production_port_performed": False,
    }
    path = ROOT / "phase5_r5_2_1r4_2_directional_obligation_evidence.json"
    path.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "missed": missed,
                      "r41_7_transitions": fixed["transitions"]}, indent=2))


if __name__ == "__main__":
    main()
