"""Synthetic CHECKER tests, never actual execution/PLC evidence or qualification.

Files are explicitly synthetic and temporary. The hosting worker's real PID/Job
proof is separate. Neither function below runs a candidate or finalizes C3-C.
"""
import ast
import copy
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from v0_2.tests.tools.m1_c3c_v4 import final_gate as legacy
from v0_2.tests.tools.m1_c3c_v4 import runtime_admission
from . import audit as revised


def run_checks(output, progress):
    root = runtime_admission.ROOT
    original = root / "v0_2/tests/tools/m1_c3c_v4/final_gate.py"
    newer = Path(revised.__file__)

    def requirements(path):
        tree = ast.parse(path.read_bytes())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "execution_audit")
        return [ast.dump(n, include_attributes=False) for n in ast.walk(function)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "require"]

    if requirements(original) != requirements(newer):
        raise AssertionError("PER_STAGE_REQUIREMENTS_CHANGED")
    progress("ASSERTIONS_AST_IDENTICAL")
    _, definition = runtime_admission.package()
    env_name = definition["execution"]["environment_lock"]
    environment = json.loads((root / env_name).read_bytes())
    environment["image_version"] = environment["image_version"][0]
    identity = {"SYNTHETIC_CHECKER_FIXTURE_ONLY": True}
    results = []
    with tempfile.TemporaryDirectory(prefix="SYNTHETIC_CHECKER_ONLY-", dir=output) as temp:
        fixture = Path(temp)

        def save(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = json.dumps(value, sort_keys=True).encode()
            path.write_bytes(raw)
            return legacy.digest(raw)

        schema_name = "v0_2/tests/tools/m1_c3c_v4/artifact_schema.json"
        save(fixture / schema_name, json.loads((root / schema_name).read_bytes()))
        save(fixture / env_name, json.loads((root / env_name).read_bytes()))
        # Environment lock is byte-bound, so preserve original bytes exactly.
        (fixture / env_name).write_bytes((root / env_name).read_bytes())
        native = fixture / "artifacts/liquid-recovery-v1/SYNTHETIC_CHECKER_ONLY/batch"
        native.mkdir(parents=True)
        stages = []
        receipts = []
        for i in range(3):
            name = "SYNTHETIC_%02d" % i
            stages.append({"stage_id": name, "status": "PASS"})
            folder = native / name
            folder.mkdir()
            receipts.append({"result_raw_sha256": save(native / ("stage-%03d-result.json" % i),
                                                        {"SYNTHETIC_CHECKER_ONLY": i})})
            save(folder / "job_status.json", {"outcome": "EXITED", "child_exitcode": 0,
                "cleanup_complete": True, "active_after_cleanup": 0,
                "assigned_before_resume": True, "resumed": True, "pid": 123})
            save(folder / "job_start.json", {"pid": 123, "job_name": "SYNTHETIC_NOT_ACTUAL_JOB",
                "wall_ms": 480000, "kill_on_close": True})
            proof_hash = save(folder / "external_job_identity.json", {
                "in_target_job": True, "actual_python_pid": 123,
                "target_job_name": "SYNTHETIC_NOT_ACTUAL_JOB", "cpu_rate": 2500,
                "cpu_flags": 5, "max_active_processes": 4, "process_mb": 1024, "job_mb": 2048})
            save(folder / "ready.json", {"pid": 123})
            save(folder / "release.json", {"actual_python_pid": 123,
                "external_proof_raw_sha256": proof_hash})
            captures = {}
            for filename in ("stdout.raw", "stderr.raw", "verify_stdout.raw", "verify_stderr.raw"):
                (folder / filename).write_bytes(b"")
                captures[filename] = {"status": "PERSISTED", "raw_sha256": legacy.digest(b"")}
            save(folder / "raw_evidence_receipts.json", captures)
            save(folder / "result.json", {"schema": "m1-c3c-stage-result-v1", "stage_id": name,
                "status": "PASS", "behavioral_adjudication": "NOT_MADE", "formal_qualification": True,
                "formal_execution_authorized": True, "scope": legacy.SCOPE,
                "execution_identity": identity, "github_run_id": os.environ["GITHUB_RUN_ID"],
                "github_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine",
                "sut_constructors": [], "runtime_identity_before": environment,
                "runtime_identity_after": environment, "payload": {}})
        save(native / "batch_complete.json", {"status": "COMPLETE", "scope": legacy.SCOPE,
            "execution_identity": identity, "formal_execution_authorized": True,
            "stages": stages, "receipts": receipts})

        def execute(module):
            with patch.object(module, "ROOT", fixture), patch.object(
                    module, "package", wraps=runtime_admission.package) as calls:
                start = time.perf_counter()
                try:
                    value = module.execution_audit(Path("SYNTHETIC_CHECKER_ONLY"), identity)
                    return "ACCEPTED_SYNTHETIC_CHECKER_INPUT", value, calls.call_count, time.perf_counter() - start
                except Exception as error:
                    return "REJECTED_SYNTHETIC_CHECKER_INPUT", (type(error).__name__, str(error)), calls.call_count, time.perf_counter() - start

        old = execute(legacy)
        new = execute(revised)
        if old[0] != "ACCEPTED_SYNTHETIC_CHECKER_INPUT" or old[:2] != new[:2]:
            raise AssertionError("AUDIT_POSITIVE_EQUIVALENCE_FAILED: " + repr((old, new)))
        if old[2] != 3 or new[2] != 1:
            raise AssertionError("REPEATED_PACKAGE_VALIDATION_NOT_ELIMINATED")
        results.append({"id": "POSITIVE_EQUIVALENCE_AND_CALL_COUNT", "status": "PASS",
            "legacy_package_calls": old[2], "revised_package_calls": new[2],
            "legacy_wall_s": old[3], "revised_wall_s": new[3]})
        progress("POSITIVE_EQUIVALENCE", legacy_calls=old[2], revised_calls=new[2])
        folder = native / "SYNTHETIC_00"
        # Every corruption is isolated and restored; none changes historical evidence.
        mutations = [
            (native / "batch_complete.json", lambda x: x.update(scope="INVALID_SCOPE")),
            (native / "batch_complete.json", lambda x: x["stages"][0].update(status="FAIL")),
            (native / "stage-000-result.json", lambda x: x.update(tampered=True)),
            (folder / "job_status.json", lambda x: x.update(outcome="TIMEOUT")),
            (folder / "job_status.json", lambda x: x.update(active_after_cleanup=1)),
            (folder / "job_status.json", lambda x: x.update(assigned_before_resume=False)),
            (folder / "external_job_identity.json", lambda x: x.update(actual_python_pid=124)),
            (folder / "external_job_identity.json", lambda x: x.update(cpu_rate=1)),
            (folder / "external_job_identity.json", lambda x: x.update(process_mb=1)),
            (folder / "release.json", lambda x: x.update(external_proof_raw_sha256="0" * 64)),
            (folder / "raw_evidence_receipts.json", lambda x: x.pop("stderr.raw")),
            (folder / "raw_evidence_receipts.json", lambda x: x["stdout.raw"].update(raw_sha256="0" * 64)),
            (folder / "result.json", lambda x: x.update(schema="INVALID_SCHEMA")),
            (folder / "result.json", lambda x: x.update(github_run_id="1")),
            (folder / "result.json", lambda x: x["runtime_identity_after"].update(python="0.0")),
            (folder / "result.json", lambda x: (x["runtime_identity_before"].update(python="0.0"),
                                               x["runtime_identity_after"].update(python="0.0"))),
        ]
        for index, (path, mutate) in enumerate(mutations):
            before = path.read_bytes()
            try:
                value = copy.deepcopy(json.loads(before))
                mutate(value)
                save(path, value)
                old = execute(legacy)
                new = execute(revised)
                if old[0] != "REJECTED_SYNTHETIC_CHECKER_INPUT" or old[:2] != new[:2]:
                    raise AssertionError("REJECTION_EQUIVALENCE_FAILED: " + repr((index, old, new)))
                results.append({"id": "CORRUPTION_%02d" % index, "status": "PASS", "rejection": new[1]})
                progress("REJECTION_EQUIVALENCE", index=index, reason=new[1])
            finally:
                path.write_bytes(before)
    return {"scope": "SYNTHETIC_CHECKER_TESTS_ONLY", "assertion_ast_identical": True,
            "checks": results, "candidate_execution": False,
            "full_final_reproduction": False, "formal_qualification": False}
