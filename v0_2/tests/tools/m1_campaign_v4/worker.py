"""Verified-job-only full campaign worker with an explicit repaired SUT binding."""
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def main():
    stage, directory = sys.argv[1:]
    directory = Path(directory).resolve()
    if (platform.node().upper() == "HIPPO" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows"
            or not directory.is_relative_to(ROOT / "artifacts/liquid-recovery-v1")):
        raise ValueError("REMOTE_DEVELOPMENT_SCOPE_DENIED")
    from v0_2.tests.tools.m1_remote_control_v3.remote_worker import write, identity
    write(directory / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (directory / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("EXTERNAL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    release = json.loads((directory / "release.json").read_bytes())
    if release["actual_python_pid"] != os.getpid():
        raise ValueError("EXTERNAL_JOB_PID_MISMATCH")
    from contextlib import ExitStack
    from unittest.mock import patch
    from .admission import admit, manifest
    from v0_2.tests.tools.m1_remote_control_v3 import admission as dependency_admission
    from v0_2.tests.tools.m1_remote_control_v3 import stage_worker
    from v0_2.tests.tools.m1_remote_control_v3.progress import initialize, mark, close
    from v0_2.tests.tools.m1_engine_v4.integration_bindings import sut_bindings
    before = identity()
    result = {"stage_id": stage, "status": "FAIL", "formal_qualification": False,
              "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine",
              "parent_core_identity_role": "FROZEN_V3_PARENT_ONLY_NOT_V4_POST_IDENTITY",
              "runtime_identity_before": before}
    initialize(directory / "progress.jsonl", stage_id=stage, sut_version="v4")
    try:
        # Select a versioned, stronger source-closure admission. All original
        # checks remain; only the bound manifest file changes to this campaign.
        with ExitStack() as stack:
            stack.enter_context(patch.object(dependency_admission, "manifest", manifest))
            stack.enter_context(patch.object(dependency_admission, "admit", admit))
            stack.enter_context(patch.object(stage_worker, "admit", admit))
            with sut_bindings() as constructed:
                mark("BEGIN", "V4_CAMPAIGN_STAGE")
                if stage == "ENVIRONMENT":
                    result.update(status="PASS", runtime_identity=before)
                elif stage == "V4_ATOMICITY_UNIT":
                    import unittest
                    os.environ["M1_POST_TEST_TARGET"] = "v4"
                    tests = unittest.defaultTestLoader.loadTestsFromName(
                        "v0_2.tests.tools.m1_engine_v4.test_post_atomicity")
                    if tests.countTestCases() != 4:
                        raise ValueError("V4_ATOMICITY_CASE_COUNT")
                    run = unittest.TextTestRunner(verbosity=2).run(tests)
                    result.update(status="PASS" if run.wasSuccessful() and run.testsRun == 4 else "FAIL",
                                  payload={"tests_run": run.testsRun, "failures": len(run.failures),
                                           "errors": len(run.errors), "old_test_body_unchanged": True})
                else:
                    payload = stage_worker.execute(stage, os.environ["C2C_M1_CASE_ROOT"])
                    result.update(status=payload["status"], payload=payload)
                executes_sut = (stage.startswith("STARTUP-") or
                                (stage.startswith("CASE-") and any(x in stage for x in
                                 ("-SPLIT", "-REPEAT-", "-PREFIX_ONE-", "-PREFIX_BATCH-"))))
                if executes_sut and not constructed:
                    raise ValueError("CAMPAIGN_MISSING_ACTUAL_V4_SUT_CONSTRUCTOR")
                if any(x["class"] != "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine"
                       or x["post_module"] != "v0_2.tests.tools.m1_engine_v4.engine" for x in constructed):
                    raise ValueError("CAMPAIGN_WRONG_SUT_BINDING")
                result["sut_constructors"] = constructed
                result["runtime_identity_after"] = identity()
                if before != result["runtime_identity_after"]:
                    raise ValueError("CAMPAIGN_ENVIRONMENT_BEFORE_AFTER_DRIFT")
                if stage != "ENVIRONMENT":
                    admit()
                mark("END" if result["status"] == "PASS" else "ERROR", "V4_CAMPAIGN_STAGE")
                write(directory / "result.json", result)
                return 0 if result["status"] == "PASS" else 1
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error),
                      runtime_identity_after=identity())
        mark("ERROR", "V4_CAMPAIGN_STAGE")
        write(directory / "result.json", result)
        raise
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
