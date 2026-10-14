"""Read-only pre-sign proposal audit. No approval generation or model imports."""
import argparse
import json
import os
from pathlib import Path
from .authority import canonical, digest, load_bound, require, validate_package, verify_source_closure
from .preflight_worker import write

ROOT = Path(__file__).resolve().parents[4]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-raw-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = ROOT / "artifacts/m1-c3c-v2-freeze/executable_proposal.json"
    raw = path.read_bytes()
    proposal = validate_package(load_bound(raw, args.expected_raw_sha256))
    bound = verify_source_closure(proposal, ROOT)
    def registration(name):
        p = ROOT / proposal["registration_paths"][name]
        return load_bound(p.read_bytes(), proposal["registration_raw_sha256"][name])
    scope = registration("limited_scope")
    sem01 = registration("SEM01")
    sem02 = registration("SEM02")
    pf06 = registration("PF06_supplement")
    require(all(x["status"] == "PROPOSED_NOT_USER_APPROVED" for x in (scope, sem01, sem02, pf06)), "PROPOSAL_SELF_APPROVAL")
    require(sem01["complete_only_publication_required"] is True
            and sem01["ARBITRARY_POST_EXCEPTION_ATOMICITY"] == "NOT_PROVEN"
            and sem01["unfulfilled_mandatory_requirement_is_not_waived"] is True, "SEM01_SCOPE_WAIVER")
    require(len(sem02["cases"]) == 5 and [c["events"] for c in sem02["cases"]] == [154, 1, 1, 1, 1]
            and all(c["strict_P1_Lane_B"] == c["strict_P1_Lane_C"] == "INCOMPLETE" for c in sem02["cases"]), "SEM02_EXCLUSION_DRIFT")
    require(pf06["binding_id"] == "PF06-C8-NORMAL-SUPPLEMENT-v1" and pf06["row_index_zero_based"] == 4
            and pf06["time_ns"] == 800000000 and len(pf06["negative_controls"]) == 2
            and pf06["PF06_ORIGINAL_SCOPE"] == "INCOMPLETE"
            and pf06["PF06_SUPPLEMENTAL_SCOPE"] == "DEVELOPMENT_VALIDATED_PENDING_APPROVAL", "PF06_SCOPE_DRIFT")
    require(proposal["PF06_phase_hash_normativity"].startswith("Original phase hashes are historical diagnostic"), "SUT_GOLDEN_PROHIBITION_MISSING")
    spec = json.loads((ROOT / "phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json").read_bytes())
    expected = set(proposal["check_stage_ids"])
    snapshots = 0
    for i, d in enumerate(spec["input_inventory"]):
        expected.update("CASE-%03d-%s" % (i, k) for k in ("REFERENCE", "SELECT", "SPLIT", "SEAL", "SCHEMA"))
        count = 11 if d["stage_id"] in ("C-history", "S-history", "P15-history") else 2
        snapshots += count
        expected.update("CASE-%03d-REPEAT-%d" % (i, j) for j in range(1, count))
    expected.update("STARTUP-" + str(i) for i in range(50))
    expected.add("REFERENCE_GROUPS")
    require(scope["required_static_stage_ids"] == sorted(expected), "STATIC_STAGE_INVENTORY_DRIFT")
    require(scope["final_current_stage"] == "FINAL_ACCEPTANCE"
            and scope["final_current_batch_post_cleanup_readback_required"] is True, "FINAL_POST_CLEANUP_AUDIT_MISSING")
    require(proposal["approval_generated"] is False and proposal["formal_execution_started"] is False, "FALSE_EXECUTION_OR_APPROVAL")
    result = {"schema": "m1-c3c-proposal-pre-sign-readback-v1", "status": "PRE_SIGN_STATIC_VALIDATION_PASS",
        "source_commit": os.environ["GITHUB_SHA"], "package_raw_sha256": digest(raw),
        "package_canonical_sha256": digest(canonical(proposal)), "source_bindings_verified": bound,
        "inputs": 101, "input_rows": sum(x["row_count"] for x in proposal["inputs"]),
        "expected_full_snapshots": snapshots, "required_static_stages_before_final": len(expected),
        "registration_hashes": proposal["registration_raw_sha256"], "candidate_imported": False,
        "candidate_behavioral_execution": False, "formal_qualification": False, "approval_generated": False,
        "limitations": proposal["limitations"]}
    output = Path(args.output).resolve()
    require(output.is_relative_to(ROOT / "artifacts/m1-c3c-pre-sign"), "PRE_SIGN_OUTPUT_SCOPE")
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
