"""Fresh, independently scoped C3-C acceptance; never renames a dev result."""
import json
import os
from pathlib import Path
from .authority import SCOPE, LIMITATIONS, classify, digest, load_bound, require
from .runtime_admission import ROOT, admit, package


def execution_audit(root, identity):
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "v0_2/tests/tools/m1_c3c_v1/artifact_schema.json").read_bytes())
    validator = Draft202012Validator(schema)
    native_root = ROOT / "artifacts/liquid-recovery-v1" / Path(root).name
    batches = list(native_root.rglob("batch_complete.json"))
    require(bool(batches) and not list(native_root.rglob("batch_stop.json")), "C3C_BATCH_INCOMPLETE_OR_STOPPED")
    stage_ids = []; captures = 0; constructors = 0
    for path in batches:
        batch = json.loads(path.read_bytes())
        require(batch["status"] == "COMPLETE" and batch["scope"] == SCOPE
                and batch["execution_identity"] == identity and batch["formal_execution_authorized"] is True,
                "C3C_BATCH_AUTHORITY_MISMATCH")
        for i, stage in enumerate(batch["stages"]):
            require(stage["status"] == "PASS", "C3C_NONPASS_STAGE_IN_BATCH")
            outer_path = path.parent / ("stage-%03d-result.json" % i)
            require(digest(outer_path.read_bytes()) == batch["receipts"][i]["result_raw_sha256"], "C3C_STAGE_RECEIPT_DRIFT")
            folder = path.parent / stage["stage_id"]
            native = json.loads((folder / "job_status.json").read_bytes())
            start = json.loads((folder / "job_start.json").read_bytes())
            proof = json.loads((folder / "external_job_identity.json").read_bytes())
            ready = json.loads((folder / "ready.json").read_bytes())
            release = json.loads((folder / "release.json").read_bytes())
            require(native["outcome"] == "EXITED" and native["child_exitcode"] == 0
                    and native["cleanup_complete"] and native["active_after_cleanup"] == 0
                    and native["assigned_before_resume"] and native["resumed"]
                    and native["pid"] == start["pid"] and proof["in_target_job"]
                    and proof["actual_python_pid"] == ready["pid"] == release["actual_python_pid"]
                    and proof["target_job_name"] == start["job_name"], "C3C_ACTUAL_PYTHON_JOB_OR_CLEANUP")
            require(proof["cpu_rate"] == 2500 and proof["cpu_flags"] == 5 and proof["max_active_processes"] == 4
                    and proof["process_mb"] == 1024 and proof["job_mb"] == 2048
                    and start["wall_ms"] == 480000 and start["kill_on_close"], "C3C_RESOURCE_POLICY_DRIFT")
            require(release["external_proof_raw_sha256"] == digest((folder / "external_job_identity.json").read_bytes()),
                    "C3C_RELEASE_PROOF_DRIFT")
            raw = json.loads((folder / "raw_evidence_receipts.json").read_bytes())
            require(set(raw) == {"stdout.raw", "stderr.raw", "verify_stdout.raw", "verify_stderr.raw"}, "C3C_RAW_LOG_SET")
            for name, receipt in raw.items():
                require(receipt["status"] == "PERSISTED" and digest((folder / name).read_bytes()) == receipt["raw_sha256"], "C3C_RAW_LOG_HASH")
                captures += 1
            result = json.loads((folder / "result.json").read_bytes())
            validator.validate(result)
            require(result["status"] == "PASS" and result["execution_identity"] == identity
                    and result["github_run_id"] == os.environ["GITHUB_RUN_ID"]
                    and result["github_run_attempt"] == os.environ["GITHUB_RUN_ATTEMPT"], "C3C_FRESH_STAGE_IDENTITY")
            require(result["runtime_identity_before"] == result["runtime_identity_after"], "C3C_STAGE_ENVIRONMENT_DRIFT")
            from .authority import verify_environment
            _, definition = package()
            lock_name = definition["execution"]["environment_lock"]
            expected = load_bound((ROOT / lock_name).read_bytes(), definition["source_raw_sha256"][lock_name])
            verify_environment(result["runtime_identity_before"], expected)
            constructors += len(result["sut_constructors"])
            stage_ids.append(stage["stage_id"])
    # The FINAL stage's own batch is not complete until this function returns.
    # Its before/after source/Job/raw evidence is independently checked by the
    # parent and mandatory delivery readback, not fictitiously pre-counted here.
    return {"status": "PASS", "completed_batches": len(batches), "completed_stages": len(stage_ids),
            "raw_captures": captures, "actual_sut_constructors": constructors,
            "stage_ids": stage_ids, "final_current_batch_post_audit_required": True}


def validate_sem02(eligibility, registration):
    expected = registration["cases"]
    actual = eligibility["cases"]
    require(len(expected) == len(actual) == 5, "C3C_FIVE_CAUSAL_EXCLUSIONS_NOT_EXACT")
    lookup = {x["nodeid"]: x for x in actual}
    require(set(lookup) == {x["nodeid"] for x in expected}, "C3C_EXCLUDED_NODE_ID_DRIFT")
    for frozen in expected:
        case = lookup[frozen["nodeid"]]
        events = case["domain_events"]
        require(case["causal_reason"] == frozen["reason"] and len(events) == frozen["events"]
                and [e["input_typed_sha256"] for e in events] == frozen["input_typed_hashes"], "C3C_EXCLUSION_INPUT_DRIFT")
        require(case["strict_P1_Lane_B"] == case["strict_P1_Lane_C"] == "INCOMPLETE"
                and not case["fake_PLC_receipts"] and not case["fake_Safety_decisions"]
                and not case["source_sensor_coerced_valid"]
                and all(e["PLC_receipts"] == 0 and e["Safety_commits"] == 0 for e in events), "C3C_FALSE_CAUSAL_PROMOTION")
    return True


def validate_pf06(matrix, registration):
    proof = matrix["PF06_proposal"]
    require(proof is not None and proof["version"] == registration["binding_id"], "C3C_PF06_BINDING_MISSING")
    cut = proof["positive_witness"]
    require(cut["source_descriptor"] == registration["source_descriptor"]
            and cut["row_index"] == registration["row_index_zero_based"]
            and cut["time_ns"] == registration["time_ns"]
            and cut["source_id"] == registration["source_id"] and cut["observed_preconditions"]["PF-06"] is True,
            "C3C_PF06_SOURCE_OR_TIME_DRIFT")
    independent = registration["independent_expectations"]
    require(cut["independent_expected_PRE"] == independent["PRE"]
            and cut["independent_expected_POST"] == independent["POST"], "C3C_PF06_INDEPENDENT_EXPECTATION_DRIFT")
    expected_safety = independent["expected_Safety"]
    require(all(cut["Safety"][key] == value for key, value in expected_safety.items()), "C3C_PF06_SAFETY_EXPECTATION")
    require(cut["phase_record_hashes"] == registration["phase_record_hashes"]
            and cut["PLC"]["producer"] == "SIMULATED_PLC", "C3C_PF06_PHASE_GRAPH_DRIFT")
    expected = {(x["stage_id"], x["input_canonical_sha256"]) for x in registration["negative_controls"]}
    actual = {(x["descriptor"]["stage_id"], x["descriptor"]["input_canonical_sha256"]) for x in proof["negative_controls"]}
    require(actual == expected and len(actual) == 2
            and all(x["all_PF06_absent"] and x["comparison"]["status"] == "PASS" for x in proof["negative_controls"]),
            "C3C_PF06_NEGATIVE_CONTROLS_DRIFT")
    require(proof["comparison"]["status"] == "PASS" and matrix["original_validated_count"] == 15
            and not matrix["original_matrix_changed"] and not proof["self_approved"], "C3C_ORIGINAL_PF_SCOPE_REWRITE")
    return True


def finalize(root):
    from v0_2.tests.tools.m1_engine_v3.common import read
    from v0_2.tests.tools.m1_engine_v3.evidence import write, receipt, verify
    from v0_2.tests.tools.m1_engine_v3.final_validation import groups
    from v0_2.tests.tools.m1_engine_v3.startup_execution import aggregate
    from v0_2.tests.tools.m1_engine_v3.witness_matrix import collect
    from v0_2.tests.tools.m1_engine_v3.eligibility import evaluate
    from v0_2.tests.tools.m1_engine_v3.artifact_schemas import validate_run
    checked = admit(); _, definition = package()
    root = Path(root); case_root = root / "cases"
    audit = execution_audit(root, checked["execution_identity"])
    descriptors = read("phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json")["input_inventory"]
    stages = {}; prefixes = {}
    for i in range(101):
        folder = case_root / ("%03d" % i)
        stage = verify(receipt(folder / "stage_result.json"))
        require(stage["status"] == "PASS" and stage["repeat_pass"]
                and stage["comparison"]["status"] == "PASS", "C3C_CASE_NOT_VALID_PASS")
        require(verify(receipt(folder / "schema_readback.json"))["status"] == "PASS", "C3C_CASE_SCHEMA_NOT_PASS")
        stages[i] = {**stage, "stage_receipt": receipt(folder / "stage_result.json")}
        prefixes[i] = verify(receipt(folder / "prefix_result.json"))
        require(prefixes[i]["status"] == "PASS", "C3C_SELECTED_PREFIX_INCOMPLETE")
    reference_groups = groups(case_root, reference=True); split_groups = groups(case_root)
    startup = aggregate(root / "startup", root / "startup_inventory.json", case_root)
    matrix = collect(root, descriptors, stages); eligibility = evaluate(startup)
    write(root / "startup_eligibility.json", eligibility)
    write(root / "PF16_witness_matrix.json", matrix)
    schema = validate_run(root)
    def registration(name):
        p = definition["registration_paths"][name]
        return load_bound((ROOT / p).read_bytes(), definition["registration_raw_sha256"][name])
    validate_sem02(eligibility, registration("SEM02"))
    validate_pf06(matrix, registration("PF06_supplement"))
    require(startup["historical_guard"]["ORIGINAL_STARTUP_HISTORICAL_RESULT"] == "49/50"
            and startup["versioned_compatibility"] == "PASS", "C3C_STARTUP_NOT_EXACT")
    expected = registration("limited_scope")["required_static_stage_ids"]
    require(set(expected).issubset(set(audit["stage_ids"])), "C3C_REQUIRED_STAGE_COVERAGE_MISSING")
    decision = classify(True, True, [])
    result = {"schema": "m1-c3c-final-result-v1", **decision,
        "execution_identity": checked["execution_identity"], "github_run_id": os.environ["GITHUB_RUN_ID"],
        "github_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"], "fresh_descriptor_count": 101,
        "selected_prefixes": sum(x["selected_count"] for x in prefixes.values()),
        "original_startup_historical": "49/50", "versioned_startup_compatibility": "PASS",
        "strict_causal_exclusions": eligibility, "original_PF06_scope": "INCOMPLETE",
        "supplemental_PF06_scope": "FORMALLY_VALIDATED_UNDER_SEPARATELY_APPROVED_REGISTRATION",
        "legacy_library_metadata_not_rewritten": True, "prior_pass_credit": False,
        "reference_groups": reference_groups, "split_groups": split_groups,
        "execution_audit": audit, "schema_readback": schema, "limitations": dict(LIMITATIONS),
        "final_current_batch_post_audit_required": True}
    item = write(root / "c3c_qualification_result.json", result)
    return {"status": "PASS", "result_receipt": item, "qualification_gate": decision["gate"]}
