"""Generate Phase 5 Revision 1 selection, equivalence, and baseline evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from v0_2.control.inner_loop import LocalDPPLC
from v0_2.control.intent import IntentSupervisor
from v0_2.examples.phase5_evidence import collect_evidence
from v0_2.examples.phase5_validation import fixture_configs
from v0_2.measurement.local_sensor import MeasuredSnapshot
from v0_2.safety.supervisor import SafetySupervisor

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs/results"
OLD_EVIDENCE = RESULTS / "phase5_evidence.json"
REVISION_REGISTRATION = ROOT / "phase5_r1_revision_registration.json"
SELECTION = ROOT / "phase5_r1_selection_evidence.json"
BASELINE = ROOT / "phase5_r1_feedback_baseline.json"
ORIGINAL_BASELINE_SHA = "b14281edc630b49de1ddcfbff1894cfe129f75e1c6b891786dbeae02de73b033"
ORIGINAL_CORE_SHA = "092b3ff035da69a95294543cdf716e4a025f506ab213543d1a640ed1d10db6d8"
TRACE_FIELDS = (
    "device_k",
    "accepted_dp_pa",
    "measured_dp_pa",
    "pump_command",
    "pump_actual",
    "total_flow_kg_s",
    "pump_electrical_j",
    "mass_residual_kg_s",
    "energy_residual_j",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_training(evidence: dict, stage: str, candidate_id: str) -> dict:
    return next(
        item for item in evidence[stage] if item["candidate"]["id"] == candidate_id
    )


def _metric_differences(old: dict, new: dict) -> dict[str, float | bool | None]:
    result = {}
    for key in old.keys() & new.keys():
        if isinstance(old[key], (int, float)) and isinstance(new[key], (int, float)):
            result[key] = abs(new[key] - old[key])
        elif old[key] is None or new[key] is None or isinstance(old[key], (str, bool, dict)):
            result[key] = old[key] == new[key]
    return result


def _historical_trace_comparison(old_rows: list[dict], new_rows: list[dict]) -> dict:
    same_grid = [row["time_ns"] for row in old_rows] == [row["time_ns"] for row in new_rows]
    maximum_absolute_difference = {
        field: max(abs(float(a[field]) - float(b[field])) for a, b in zip(old_rows, new_rows))
        for field in TRACE_FIELDS
        if all(row[field] is not None for row in old_rows + new_rows)
    }
    return {
        "same_time_grid": same_grid,
        "same_safety_state_trace": [x["safety_state"] for x in old_rows]
        == [x["safety_state"] for x in new_rows],
        "maximum_absolute_difference": maximum_absolute_difference,
        "status": (
            "PASS"
            if same_grid
            and [x["safety_state"] for x in old_rows]
            == [x["safety_state"] for x in new_rows]
            and max(maximum_absolute_difference.values(), default=0.0) <= 1e-12
            else "FAIL"
        ),
    }


def _measured(*, temperature: float, dp: float, valid: bool = True) -> MeasuredSnapshot:
    quality = tuple(
        (name, "VALID" if valid else "MISSING")
        for name in ("temperature", "dp", "flow", "pump_speed", "pump_status")
    )
    return MeasuredSnapshot(
        0,
        0,
        1,
        (("b0:die", temperature),) if valid else (),
        dp if valid else None,
        0.1 if valid else None,
        0.7 if valid else None,
        True if valid else None,
        True if valid else None,
        False if valid else None,
        quality,
        measurement_record_id="measurement:r1-case",
        actuator_state_id="actuator-state:r1-case",
        hydraulic_solution_id="hydraulic-solution:r1-case",
        source_ids=("actuator-state:r1-case", "hydraulic-solution:r1-case"),
    )


def _safety_active_case(name: str, measured: MeasuredSnapshot) -> dict:
    *_, inner_config, policy = fixture_configs(
        {"kp": 0.000015, "ki": 0.000004, "kd": 0.0},
        {"kp": 3000.0, "ki": 60.0, "kd": 0.0},
    )
    target = IntentSupervisor(policy.fallback_dp_pa).accept_target(None, 0)
    decision = SafetySupervisor(policy).evaluate(
        0,
        measured,
        1_000_000_000,
        target.requested_dp_pa,
        0.7,
        accepted_target_id=target.accepted_target_id,
    )
    result = LocalDPPLC(inner_config).update(
        0,
        measured,
        target,
        decision.envelope,
        1_000_000_000,
    )
    original_expected = policy.fault_speed
    return {
        "scenario": name,
        "state": decision.state.value,
        "original_phase5_expected_speed": original_expected,
        "r1_speed": result.actuator_command.requested_speed,
        "difference": result.actuator_command.requested_speed - original_expected,
        "producer_module": result.actuator_command.producer_module,
        "mode": result.actuator_command.mode,
    }


def collect_r1_evidence() -> tuple[dict, dict]:
    old = json.loads(OLD_EVIDENCE.read_text(encoding="utf-8"))
    current = collect_evidence()
    selected = current["selected"]
    if selected != {"inner": "inner_b", "outer": "outer_c"}:
        raise RuntimeError("BASELINE_SELECTION_CHANGED_AFTER_OWNERSHIP_FIX")

    training_comparison = []
    for stage, candidate_id in (
        ("inner_training", "inner_b"),
        ("outer_training", "outer_c"),
    ):
        old_stage = _selected_training(old, stage, candidate_id)
        new_stage = _selected_training(current, stage, candidate_id)
        for old_run, new_run in zip(old_stage["training"], new_stage["training"]):
            training_comparison.append(
                {
                    "candidate": candidate_id,
                    "scenario": old_run["scenario"],
                    "differences": _metric_differences(
                        old_run["metrics"], new_run["metrics"]
                    ),
                }
            )

    trace_comparison = _historical_trace_comparison(
        old["holdout"]["rows"], current["holdout"]["rows"]
    )
    safety_active = [
        _safety_active_case("PRESSURE_CONFLICT", _measured(temperature=300, dp=61000)),
        _safety_active_case("PROTECTED", _measured(temperature=345, dp=20000)),
        _safety_active_case("FAULT_SENSOR_INVALID", _measured(temperature=300, dp=20000, valid=False)),
    ]
    evidence = {
        "schema": "phase5-r1-selection-evidence-v1",
        "provenance": "GENERIC NUMERICAL FIXTURE; OWNERSHIP CORRECTION ONLY; NOT OEM VALIDATED",
        "revision_registration_sha256": _sha(REVISION_REGISTRATION),
        "original_baseline_file_sha256": ORIGINAL_BASELINE_SHA,
        "original_control_core_sha256": ORIGINAL_CORE_SHA,
        "inner_training": current["inner_training"],
        "outer_training": current["outer_training"],
        "selected": selected,
        "training_metric_comparison": training_comparison,
        "historical_holdout": {
            "role": "HISTORICAL_HOLDOUT_REGRESSION",
            "id": "HOLDOUT-01-combined",
            "original_metrics": old["holdout"]["metrics"],
            "r1_metrics": current["holdout"]["metrics"],
            "metric_differences": _metric_differences(
                old["holdout"]["metrics"], current["holdout"]["metrics"]
            ),
            "trace_comparison": trace_comparison,
        },
        "safety_active_equivalence": safety_active,
        "convergence": current["convergence"],
        "stability": {
            key: current["stability"][key]
            for key in ("runs", "identical_hashes", "hash", "bounded_memory")
        },
    }
    baseline = dict(current["baseline"])
    baseline.update(
        {
            "schema": "phase5-r1-feedback-baseline-v1",
            "status": "FROZEN_GENERIC_TEST_BASELINE_REVISION_1_NOT_OEM",
            "revision": 1,
            "supersedes_status": "SUPERSEDED_DUE_TO_ACTUATION_OWNERSHIP_DEFECT",
            "supersedes_original_baseline_sha256": ORIGINAL_BASELINE_SHA,
            "original_baseline_file_sha256": ORIGINAL_BASELINE_SHA,
            "original_control_core_sha256": ORIGINAL_CORE_SHA,
            "physics_period_ns": 200_000_000,
            "safety_period_ns": 200_000_000,
            "revision_registration_sha256": _sha(REVISION_REGISTRATION),
            "ownership_contract_version": "contracts/14 and 15 revision 1.1",
            "command_provenance_schema_version": "phase5-r1-command-lineage-v1",
            "historical_holdout_id": "HOLDOUT-01-combined",
        }
    )
    return evidence, baseline


def main() -> None:
    evidence, baseline = collect_r1_evidence()
    SELECTION.write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    baseline["selection_evidence_sha256"] = _sha(SELECTION)
    BASELINE.write_text(
        json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "selected": evidence["selected"],
                "holdout_trace": evidence["historical_holdout"]["trace_comparison"]["status"],
                "convergence": evidence["convergence"]["status"],
                "stability": evidence["stability"],
                "new_control_core_sha256": baseline["code_sha256"],
                "selection_evidence_sha256": baseline["selection_evidence_sha256"],
                "new_baseline_sha256": _sha(BASELINE),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
