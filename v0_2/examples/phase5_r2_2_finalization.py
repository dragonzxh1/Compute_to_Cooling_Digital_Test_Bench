"""Complete validation and freeze the user-authorized Phase 5R2 baseline."""

from __future__ import annotations

import gc
import hashlib
import json
import tracemalloc
from dataclasses import asdict
from pathlib import Path

from v0_2.examples.phase5_r1_ownership_audit import collect_audit, static_audit
from v0_2.examples.phase5_r2_1_robustness import (
    _control_core_sha,
    _convergence,
    _plant_sha,
)
from v0_2.examples.phase5_r2_evidence import run_r2_scenario

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "phase5_r2_2_finalization_evidence.json"
FINAL_BASELINE = ROOT / "phase5_r2_feedback_baseline.json"
R1_BASELINE = ROOT / "phase5_r1_feedback_baseline.json"
R2_TARGET_REGISTRATION = ROOT / "phase5_r2_target_registration.json"
R2_SELECTION = ROOT / "phase5_r2_selection_evidence.json"
R2_CANDIDATE = ROOT / "phase5_r2_candidate_baseline.json"
R2_1_REGISTRATION = ROOT / "phase5_r2_1_selection_robustness_registration.json"
R2_1_EVIDENCE = ROOT / "phase5_r2_1_selection_robustness_evidence.json"
OWNERSHIP_AUDIT = ROOT / "docs/results/phase5_r1_ownership_audit.json"
EXPECTED = {
    "phase5_r1_baseline_sha256": "24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d",
    "phase5_r2_target_registration_sha256": "8b2bda84c6591e678d0fde972562e1f0dc7a10d0b22c82b76a10f34372c860a2",
    "phase5_r2_selection_evidence_sha256": "94bd66cf9c66602ca37fd16d65f92b93536d7ff36974a8d10153723897c93e37",
    "phase5_r2_candidate_baseline_sha256": "2f97cc36ff10d81be7a3a74a9c8d94cd2099222e5cd5c22ba09fad8f458f9a0a",
    "phase5_r2_1_robustness_registration_sha256": "4942860bf06d991942b4ae5fbe1d8bfd9a28ded3263e77c716bfabaa5481f735",
    "phase5_r2_1_robustness_evidence_sha256": "dafa0034206912172901de8655c147886cfb7296a3c24601dcc64e3696fa2052",
    "r1_control_core_sha256": "b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579",
    "frozen_plant_sha256": "d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254",
}
TARGET_K = 313.71072595542387
INNER = {"id": "inner_b", "kp": 0.000015, "ki": 0.000004, "kd": 0.0}
OUTER = {"id": "outer_a", "kp": 1000.0, "ki": 20.0, "kd": 0.0}
MESHES_NS = (200_000_000, 100_000_000, 50_000_000)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _row_digest(run) -> str:
    return hashlib.sha256(_canonical([asdict(row) for row in run.rows])).hexdigest()


def _gains(candidate: dict) -> dict:
    return {key: candidate[key] for key in ("kp", "ki", "kd")}


def _integrity() -> dict:
    actual = {
        "phase5_r1_baseline_sha256": _sha(R1_BASELINE),
        "phase5_r2_target_registration_sha256": _sha(R2_TARGET_REGISTRATION),
        "phase5_r2_selection_evidence_sha256": _sha(R2_SELECTION),
        "phase5_r2_candidate_baseline_sha256": _sha(R2_CANDIDATE),
        "phase5_r2_1_robustness_registration_sha256": _sha(R2_1_REGISTRATION),
        "phase5_r2_1_robustness_evidence_sha256": _sha(R2_1_EVIDENCE),
        "r1_control_core_sha256": _control_core_sha(),
        "frozen_plant_sha256": _plant_sha(),
    }
    if actual != EXPECTED:
        raise RuntimeError(f"PHASE5_R2_2_BASELINE_INTEGRITY_FAILURE: {actual!r}")
    robustness = _load(R2_1_EVIDENCE)
    if robustness["target_k"] != TARGET_K:
        raise RuntimeError("PHASE5_R2_2_BASELINE_INTEGRITY_FAILURE: target changed")
    if robustness["selection"]["candidate_id"] != "outer_a":
        raise RuntimeError("PHASE5_R2_2_BASELINE_INTEGRITY_FAILURE: selection changed")
    return {"status": "PASS", "expected": EXPECTED, "actual": actual}


def _closure(records: list[dict]) -> dict:
    return {
        "max_mass_residual_kg_s": max(item["max_mass_residual_kg_s"] for item in records),
        "max_energy_residual_j": max(item["max_energy_residual_j"] for item in records),
        "status": (
            "PASS"
            if max(item["max_mass_residual_kg_s"] for item in records) <= 1e-8
            and max(item["max_energy_residual_j"] for item in records) <= 0.001
            else "FAIL"
        ),
    }


def _baseline(evidence: dict) -> dict:
    candidate = _load(R2_CANDIDATE)
    candidate.update(
        {
            "schema": "phase5-r2-feedback-baseline-v1",
            "revision": 2,
            "status": "FROZEN_GENERIC_TEST_BASELINE_REVISION_2_NOT_OEM",
            "target_k": TARGET_K,
            "thermal_control_target_k": TARGET_K,
            "target_derivation_rule": "AUTHORITY_MIDPOINT",
            "target_derivation_load_w_per_device": 120.0,
            "inner_candidate_id": "inner_b",
            "outer_candidate_id": "outer_a",
            "inner_gains": _gains(INNER),
            "outer_gains": _gains(OUTER),
            "safety": {**candidate["safety"], "control_target_k": TARGET_K},
            "supersedes_r1_baseline_sha256": EXPECTED["phase5_r1_baseline_sha256"],
            "supersedes": "phase5_r1_feedback_baseline.json",
            "r1_baseline_sha256": EXPECTED["phase5_r1_baseline_sha256"],
            "r2_target_registration_sha256": EXPECTED["phase5_r2_target_registration_sha256"],
            "r2_selection_evidence_sha256": EXPECTED["phase5_r2_selection_evidence_sha256"],
            "r2_1_robustness_registration_sha256": EXPECTED[
                "phase5_r2_1_robustness_registration_sha256"
            ],
            "r2_1_robustness_evidence_sha256": EXPECTED["phase5_r2_1_robustness_evidence_sha256"],
            "historical_stress_id": "HOLDOUT-01-combined",
            "historical_stress_classification": "HISTORICAL STRESS CHARACTERIZATION",
            "ownership_schema_version": "SafetyEnvelope-to-PLC-ActuatorCommand-v1",
            "command_provenance_schema_version": "phase5-r1-command-lineage-v1",
            "code_sha256": EXPECTED["r1_control_core_sha256"],
            "user_authorized_final_selection": {
                "target_k": TARGET_K,
                "inner_candidate_id": "inner_b",
                "outer_candidate_id": "outer_a",
                "reason": "R2.1 thermal IAE numerically indistinguishable; control-TV tie-break",
            },
            "finalization_evidence_summary": {
                "historical_stress_status": evidence["historical_stress"]["status"],
                "selected_baseline_convergence_status": evidence["selected_baseline_convergence"][
                    "status"
                ],
                "ownership_status": evidence["ownership"]["status"],
                "repeated_stability_status": evidence["repeated_stability"]["status"],
                "mass_energy_status": evidence["mass_energy"]["status"],
            },
        }
    )
    payload_sha = hashlib.sha256(_canonical(candidate)).hexdigest()
    candidate["final_baseline_sha256"] = payload_sha
    candidate["final_baseline_sha256_scope"] = (
        "SHA-256 of canonical baseline payload before adding final_baseline_sha256 and its scope; "
        "the complete file SHA is reported in Phase 5R2.2 evidence/report"
    )
    return candidate


def main() -> None:
    integrity = _integrity()
    stress = run_r2_scenario(
        "HOLDOUT-01-combined", TARGET_K, inner=_gains(INNER), outer=_gains(OUTER)
    )
    stress_metrics = stress.metrics()
    convergence_runs = [
        run_r2_scenario(
            "TUNE-01-load",
            TARGET_K,
            inner=_gains(INNER),
            outer=_gains(OUTER),
            physics_ns=dt_ns,
        )
        for dt_ns in MESHES_NS
    ]
    convergence_metrics = [run.metrics() for run in convergence_runs]
    tolerances = _load(R2_1_REGISTRATION)["selected_baseline_convergence_policy"][
        "fine_pair_tolerances"
    ]
    convergence = _convergence(convergence_metrics, tolerances)
    audit = collect_audit()
    static = static_audit()
    matrix_lineage = all(
        command.producer_module == "PLC" and command.plc_cycle_id
        for run in [stress, *convergence_runs]
        for command in run.actuator_commands
    )
    ownership = {
        "status": (
            "PASS"
            if static["status"] == "PASS"
            and audit["runtime"]["status"] == "PASS"
            and matrix_lineage
            else "FAIL"
        ),
        "static": static,
        "runtime": audit["runtime"],
        "validated_run_lineage_pass": matrix_lineage,
        "frozen_r1_audit_sha256": _sha(OWNERSHIP_AUDIT),
    }

    tracemalloc.start()
    hashes = []
    retained = []
    repeated_metrics = []
    for _ in range(10):
        repeated = run_r2_scenario(
            "TUNE-01-load", TARGET_K, inner=_gains(INNER), outer=_gains(OUTER)
        )
        hashes.append(_row_digest(repeated))
        repeated_metrics.append(repeated.metrics())
        del repeated
        gc.collect()
        retained.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    stability = {
        "status": (
            "PASS"
            if len(set(hashes)) == 1 and max(retained) - min(retained) < 3_000_000
            else "FAIL"
        ),
        "runs": len(hashes),
        "identical_hashes": len(set(hashes)) == 1,
        "hash": hashes[0],
        "bounded_retained_memory": max(retained) - min(retained) < 3_000_000,
        "retained_memory_span_bytes": max(retained) - min(retained),
    }
    closure = _closure([stress_metrics, *convergence_metrics, *repeated_metrics])
    evidence = {
        "schema": "phase5-r2-2-finalization-evidence-v1",
        "status": "PENDING_BASELINE_WRITE",
        "integrity": integrity,
        "user_authorized_selection": {
            "target_k": TARGET_K,
            "inner": INNER,
            "outer": OUTER,
        },
        "historical_stress": {
            "status": "PASS",
            "scenario_id": "HOLDOUT-01-combined",
            "classification": "HISTORICAL STRESS CHARACTERIZATION",
            "selection_input": False,
            "metrics": stress_metrics,
        },
        "selected_baseline_convergence": convergence,
        "ownership": ownership,
        "repeated_stability": stability,
        "mass_energy": closure,
    }
    gates_pass = (
        convergence["status"] == "PASS"
        and ownership["status"] == "PASS"
        and stability["status"] == "PASS"
        and closure["status"] == "PASS"
    )
    if not gates_pass:
        evidence["status"] = "PHASE5_R2_2_VALIDATION_FAILURE"
        EVIDENCE.write_text(
            json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        raise RuntimeError("PHASE5_R2_2_VALIDATION_FAILURE")

    baseline = _baseline(evidence)
    FINAL_BASELINE.write_text(
        json.dumps(baseline, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    evidence["status"] = "PASS_FINAL_R2_BASELINE_FROZEN_AWAITING_USER_REVIEW"
    evidence["final_baseline"] = {
        "path": FINAL_BASELINE.name,
        "file_sha256": _sha(FINAL_BASELINE),
        "payload_sha256": baseline["final_baseline_sha256"],
        "supersedes_r1_baseline_sha256": EXPECTED["phase5_r1_baseline_sha256"],
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "final_baseline_sha256": _sha(FINAL_BASELINE),
                "finalization_evidence_sha256": _sha(EVIDENCE),
                "stress": stress_metrics,
                "convergence": convergence,
                "ownership_status": ownership["status"],
                "stability": stability,
                "mass_energy": closure,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
