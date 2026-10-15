"""Formal stage entry. No model work before exact approval and actual Job proof."""
import json
import os
import platform
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from .authority import IntegrityError, require
from .preflight_worker import write

ROOT = Path(__file__).resolve().parents[4]


def main():
    stage, name = sys.argv[1:]
    folder = Path(name).resolve()
    require(platform.node().upper() != "HIPPO" and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Windows"
            and folder.is_relative_to(ROOT / "artifacts/liquid-recovery-v1"), "C3C_STAGE_HOST_OR_PATH")
    write(folder / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (folder / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("C3C_EXTERNAL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    release = json.loads((folder / "release.json").read_bytes())
    require(release["actual_python_pid"] == os.getpid(), "C3C_RELEASE_ACTUAL_PID_DRIFT")
    from .runtime_admission import admit, current_identity, manifest
    result = {"schema": "m1-c3c-stage-result-v1", "stage_id": stage,
              "status": "INVALID", "behavioral_adjudication": "NOT_MADE",
              "formal_qualification": True, "formal_execution_authorized": False,
              "github_run_id": os.environ["GITHUB_RUN_ID"],
              "github_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine"}
    # An unsigned/malformed package cannot proceed even to candidate import.
    try:
        checked = admit(bootstrap=(stage == "ENVIRONMENT"))
        result["scope"] = checked["execution_identity"]["scope"]
        result["formal_execution_authorized"] = True
        result["execution_identity"] = checked["execution_identity"]
        before = checked["environment"]
        result["runtime_identity_before"] = before
        from v0_2.tests.tools.m1_remote_control_v3 import admission as legacy_admission
        from . import stage_worker
        from v0_2.tests.tools.m1_remote_control_v3.progress import initialize, mark, close
        from .bindings import sut_bindings
        initialize(folder / "progress.jsonl", stage_id=stage, sut_version="v4-c3c")
        try:
            with ExitStack() as stack:
                # New, stronger authority is used at library call boundaries;
                # sealed source files/guards and original result metadata stay intact.
                stack.enter_context(patch.object(legacy_admission, "admit", admit))
                stack.enter_context(patch.object(legacy_admission, "manifest", manifest))
                stack.enter_context(patch.object(stage_worker, "admit", admit))
                if stage == "ENVIRONMENT":
                    payload = {"status": "PASS", "runtime_identity": before}
                    constructed = []
                else:
                    with sut_bindings() as constructed:
                        mark("BEGIN", "C3C_STAGE")
                        if stage in ("C3_AUTHORITY_UNIT", "V4_ATOMICITY_UNIT"):
                            import unittest
                            count = 31 if stage == "C3_AUTHORITY_UNIT" else 4
                            module = ("v0_2.tests.tools.m1_c3c_v5.test_authority" if stage == "C3_AUTHORITY_UNIT"
                                      else "v0_2.tests.tools.m1_engine_v4.test_post_atomicity")
                            os.environ["M1_POST_TEST_TARGET"] = "v4"
                            tests = unittest.defaultTestLoader.loadTestsFromName(module)
                            require(tests.countTestCases() == count, "C3C_UNIT_INVENTORY_DRIFT")
                            run = unittest.TextTestRunner(verbosity=2).run(tests)
                            payload = {"status": "PASS" if run.wasSuccessful() and run.testsRun == count else "FAIL",
                                       "tests_run": run.testsRun, "failures": len(run.failures), "errors": len(run.errors)}
                        elif stage == "FINAL_ACCEPTANCE":
                            from .final_gate import finalize
                            payload = finalize(Path(os.environ["C2C_M1_REFERENCE_ROOT"]).parent)
                        else:
                            payload = stage_worker.execute(stage, os.environ["C2C_M1_CASE_ROOT"])
                executes_sut = (stage.startswith("STARTUP-") or (stage.startswith("CASE-") and any(
                    x in stage for x in ("-SPLIT", "-REPEAT-", "-PREFIX_ONE-", "-PREFIX_BATCH-"))))
                require(not executes_sut or bool(constructed), "C3C_MISSING_ACTUAL_SUT_CONSTRUCTOR")
                require(all(x["class"] == result["sut"] and x["post_module"] ==
                            "v0_2.tests.tools.m1_engine_v4.engine" for x in constructed), "C3C_WRONG_SUT_CONSTRUCTOR")
                require(payload["status"] in ("PASS", "FAIL", "INCOMPLETE", "INVALID"), "C3C_RESULT_CATEGORY")
                after = current_identity()
                require(before == after, "C3C_ENVIRONMENT_BEFORE_AFTER_DRIFT")
                admit(bootstrap=(stage == "ENVIRONMENT"))
                result.update(status=payload["status"], payload=payload, sut_constructors=constructed,
                              runtime_identity_after=after,
                              behavioral_adjudication="FAIL" if payload["status"] == "FAIL" else "NOT_MADE")
                mark("END" if result["status"] == "PASS" else "ERROR", "C3C_STAGE")
                write(folder / "result.json", result)
                # Valid FAIL is durable, with exit0 so the parent can distinguish
                # behavioral assertions from native crashes/missing evidence.
                return 0
        finally:
            close()
    except BaseException as error:
        result.update(status="INVALID", behavioral_adjudication="NOT_MADE",
                      error_type=type(error).__name__, error=str(error))
        if hasattr(error, "actual_environment"):
            result["runtime_identity_before"] = error.actual_environment
            result["expected_environment"] = error.expected_environment
            result["environment_differences"] = error.environment_differences
        if "runtime_identity_before" in result:
            result["runtime_identity_after"] = current_identity()
        # The frozen repeat driver has already persisted the divergent output
        # before raising this exact predicate. Do not mislabel it as mere
        # infrastructure failure when all authority/source/env checks still hold.
        if type(error) is ValueError and str(error) == "REPEAT_NONDETERMINISTIC" and result["formal_execution_authorized"]:
            try:
                admit()
                require(result["runtime_identity_before"] == result["runtime_identity_after"], "C3C_REPEAT_ENV_DRIFT")
                require(bool(constructed), "C3C_REPEAT_MISSING_SUT_PROOF")
                result.update(status="FAIL", behavioral_adjudication="FAIL", sut_constructors=constructed,
                              payload={"status": "FAIL", "registered_predicate": "REPEAT_NONDETERMINISTIC",
                                       "divergent_output_retained": True})
            except BaseException as validation_error:
                result.update(status="INVALID", behavioral_adjudication="NOT_MADE",
                              post_failure_integrity_error=str(validation_error))
        write(folder / "result.json", result)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
