"""Remote-only bounded startup handshake and generic smoke, never M1 campaign."""
import importlib.metadata
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise RuntimeError("REMOTE_EVIDENCE_READBACK_FAILED")


def identity():
    lock = json.loads((ROOT / "v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json").read_bytes())
    return {
        "host": platform.node(), "python": platform.python_version(), "executable": sys.executable,
        "system": platform.system(), "version": platform.version(), "machine": platform.machine(),
        "image_os": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion"),
        "dependencies": {name: importlib.metadata.version(name) for name in lock["dependencies"]},
    }


def main():
    stage, directory = sys.argv[1:]
    directory = Path(directory).resolve()
    if (platform.node().upper() == "HIPPO" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows"):
        raise RuntimeError("REMOTE_HOST_ADMISSION_DENIED")
    if not directory.is_relative_to(ROOT / "artifacts/liquid-recovery-v1"):
        raise RuntimeError("REMOTE_ARTIFACT_SCOPE_DENIED")
    write(directory / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    # Sleep-only admission wait. No FFI, watchdog thread or primitive stress.
    deadline = time.monotonic() + 25
    while not (directory / "release.json").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("EXTERNAL_IDENTITY_RELEASE_TIMEOUT")
        time.sleep(0.05)
    release = json.loads((directory / "release.json").read_bytes())
    if release["actual_python_pid"] != os.getpid():
        raise RuntimeError("RELEASE_PID_MISMATCH")
    result = {"stage_id": stage, "status": "FAIL", "formal_qualification": False}
    try:
        if stage == "ENVIRONMENT":
            result.update(status="PASS", runtime_identity=identity())
        elif stage == "PHYSICAL_PROBE":
            from v0_2.tests.tools.liquid_recovery_v1.physical_probe import main as probe
            if probe() != 0:
                raise RuntimeError("PHYSICAL_PROBE_NONZERO")
            result["status"] = "PASS"
        else:
            plan = json.loads((ROOT / "v0_2/tests/tools/liquid_recovery_v1/plan.json").read_bytes())
            selected = [case for case in plan["smoke_stages"] if case["stage_id"] == stage]
            if len(selected) != 1:
                raise RuntimeError("UNKNOWN_SMOKE_STAGE")
            import pytest
            code = int(pytest.main(["-c", "v0_2/pyproject.toml", "-x", "-W", "error",
                                   "-p", "v0_2.tests.tools.liquid_recovery_v1.pytest_plugin",
                                   *selected[0]["pytest_node_ids"]]))
            result.update(status="PASS" if code == 0 else "FAIL", pytest_exitcode=code,
                          expected_item_count=sum(plan["expected_collection_counts"][node]
                                                  for node in selected[0]["pytest_node_ids"]))
        result["runtime_identity_after"] = identity()
        write(directory / "result.json", result)
        return 0 if result["status"] == "PASS" else 1
    except BaseException as error:
        # Native crash cannot fake this file; absence is an integrity failure.
        result["error_type"] = type(error).__name__
        write(directory / "result.json", result)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
