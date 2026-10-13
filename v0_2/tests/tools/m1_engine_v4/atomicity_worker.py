"""Remote-only failure-witness collector. No formal qualification authority."""
import hashlib
import importlib
import json
import os
import platform
import sys
import time
import traceback
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise OSError("EVIDENCE_READBACK_FAILURE")


class RecordedResults(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test.id(), "outcome": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test.id(), "outcome": "FAIL", "exception": err[0].__name__,
                             "traceback": "".join(traceback.format_exception(*err))})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test.id(), "outcome": "ERROR", "exception": err[0].__name__,
                             "traceback": "".join(traceback.format_exception(*err))})


def verify_sources(manifest):
    for rel, expected in manifest["source_hashes"].items():
        p = (ROOT / rel).resolve()
        if not p.is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError("DEVELOPMENT_SOURCE_DRIFT: " + rel)


def main():
    target, directory, expected_manifest = sys.argv[1:]
    directory = Path(directory).resolve()
    if (os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows" or platform.node().upper() == "HIPPO"):
        raise ValueError("INDEPENDENT_HOSTED_WINDOWS_ONLY")
    if target not in {"v3", "v4"} or not directory.is_relative_to(ROOT / "artifacts/m1-post-atomicity"):
        raise ValueError("EXECUTION_SCOPE_DENIED")
    write(directory / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (directory / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("PID_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    release = json.loads((directory / "release.json").read_bytes())
    if release["actual_python_pid"] != os.getpid():
        raise ValueError("PID_JOB_RELEASE_MISMATCH")
    manifest_path = ROOT / "v0_2/tests/tools/m1_engine_v4/development_manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected_manifest:
        raise ValueError("CONTROL_MANIFEST_DRIFT")
    manifest = json.loads(manifest_path.read_bytes())
    verify_sources(manifest)
    from v0_2.tests.tools.m1_remote_control_v3.admission import current_identity
    before = current_identity()
    if before["python"] != "3.11.9" or before["system"] != "Windows" or before["machine"] != "AMD64":
        raise ValueError("ENVIRONMENT_IDENTITY_MISMATCH")
    lock = json.loads((ROOT / "v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json").read_bytes())
    if before["dependencies"] != lock["dependencies"]:
        raise ValueError("ENVIRONMENT_DEPENDENCY_DRIFT")
    os.environ["M1_POST_TEST_TARGET"] = target
    module = importlib.import_module("v0_2.tests.tools.m1_engine_v4.test_post_atomicity")
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    run = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RecordedResults).run(suite)
    ids = {x["id"] for x in run.records}
    failures = {x["id"] for x in run.records if x["outcome"] == "FAIL"}
    errors = [x for x in run.records if x["outcome"] == "ERROR"]
    expected = manifest["baseline_expected_failure_ids"] if target == "v3" else []
    after = current_identity()
    verify_sources(manifest)
    valid = (before == after and run.testsRun == 4 and len(run.records) == 4 and len(ids) == 4
             and ids == set(manifest["test_ids"]) and not errors and not run.skipped
             and failures == set(expected))
    status = ("BASELINE_DEFECT_REPRODUCED" if target == "v3" else "DEVELOPMENT_REGRESSION_PASS") if valid else "STOP"
    result = {"status": status, "target": target, "tests_run": run.testsRun,
              "tests_passed": sum(x["outcome"] == "PASS" for x in run.records),
              "tests_failed": len(failures), "tests_errors": len(errors), "records": run.records,
              "expected_baseline_failures": expected, "source_commit": os.environ["GITHUB_SHA"],
              "control_manifest_sha256": expected_manifest, "environment_before": before,
              "environment_after": after, "development_only": True, "formal_qualification": False,
              "baseline_failure_scores_not_relabelled_PASS": True}
    write(directory / "result.json", result)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
