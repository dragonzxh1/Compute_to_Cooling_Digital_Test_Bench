"""Remote verified-Job synthetic authority checks; NOT C3-C behavior."""
import hashlib
import json
import os
import platform
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise OSError("PREFLIGHT_PERSISTENCE_FAILURE")


def main():
    target, folder, expected = sys.argv[1:]
    folder = Path(folder).resolve()
    if (target != "CHECKS" or platform.node().upper() == "HIPPO"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows"
            or not folder.is_relative_to(ROOT / "artifacts/m1-c3c-assembly-v3")):
        raise ValueError("SYNTHETIC_PREFLIGHT_SCOPE_DENIED")
    write(folder / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (folder / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("ACTUAL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    if json.loads((folder / "release.json").read_bytes())["actual_python_pid"] != os.getpid():
        raise ValueError("ACTUAL_PYTHON_PID_DRIFT")
    control_path = ROOT / "v0_2/tests/tools/m1_c3c_v1/assembly_v3_control.json"
    if hashlib.sha256(control_path.read_bytes()).hexdigest() != expected:
        raise ValueError("PREFLIGHT_CONTROL_DRIFT")
    control = json.loads(control_path.read_bytes())
    if (control.get("scope") != "DEVELOPMENT_INFRASTRUCTURE_ONLY"
            or control.get("formal_behavior_authorized") is not False
            or control.get("synthetic_test_count") != 47):
        raise ValueError("PREFLIGHT_AUTHORITY_SCOPE_DRIFT")
    def verify():
        for name, digest in control["source_hashes"].items():
            p = (ROOT / name).resolve()
            if not p.is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise ValueError("PREFLIGHT_SOURCE_DRIFT: " + name)
        parent = json.loads((ROOT / control["protected_parent_manifest_path"]).read_bytes())
        for name, digest in {**parent["bundle_entry_raw_hashes"], **parent["remote_source_raw_hashes"]}.items():
            p = (ROOT / name).resolve()
            if not p.is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise ValueError("SEALED_PARENT_SOURCE_DRIFT: " + name)
    verify()
    from v0_2.tests.tools.m1_remote_control_v3.remote_worker import identity
    before = identity()
    tests = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName("v0_2.tests.tools.m1_c3c_v1.test_authority"),
        unittest.defaultTestLoader.loadTestsFromName("v0_2.tests.tools.m1_c3c_v1.test_assembly")])
    if tests.countTestCases() != control["synthetic_test_count"]:
        raise ValueError("SYNTHETIC_TEST_COUNT_DRIFT")
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    after = identity()
    verify()
    if before != after:
        raise ValueError("PREFLIGHT_ENVIRONMENT_DRIFT")
    # No model or candidate modules are imported by this preflight.
    forbidden = [name for name in sys.modules if name in (
        "v0_2.tests.tools.m1_engine_v4.engine",
        "v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine")]
    if forbidden:
        raise ValueError("SYNTHETIC_PREFLIGHT_IMPORTED_CANDIDATE")
    passed = result.wasSuccessful() and result.testsRun == control["synthetic_test_count"]
    write(folder / "result.json", {"status": "C3C_ASSEMBLY_V3_SYNTHETIC_PASS" if passed else "C3C_ASSEMBLY_V3_SYNTHETIC_FAIL",
        "scope": "DEVELOPMENT_INFRASTRUCTURE_ONLY", "source_commit": os.environ["GITHUB_SHA"],
        "control_manifest_sha256": expected, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "environment_before": before, "environment_after": after,
        "candidate_imported": False, "candidate_behavioral_execution": False,
        "formal_qualification": False, "user_freeze_approval_generated": False})
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
