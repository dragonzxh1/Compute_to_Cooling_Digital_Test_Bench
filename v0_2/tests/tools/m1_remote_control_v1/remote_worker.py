"""Remote-only bounded startup handshake and generic smoke, never M1 campaign."""
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
    from .admission import current_identity
    return current_identity()


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
    from .progress import initialize, mark, close
    initialize(directory / 'progress.jsonl', stage_id=stage)
    try:
        mark('BEGIN','M1_REMOTE_STAGE')
        if stage == "ENVIRONMENT":
            result.update(status="PASS", runtime_identity=identity())
        else:
            from .pilot_worker import execute
            payload = execute(stage, os.environ['C2C_M1_CASE_ROOT'])
            result.update(status=payload['status'], payload=payload)
        result["runtime_identity_after"] = identity()
        mark('END' if result['status']=='PASS' else 'ERROR','M1_REMOTE_STAGE')
        write(directory / "result.json", result)
        return 0 if result["status"] == "PASS" else 1
    except BaseException as error:
        # Native crash cannot fake this file; absence is an integrity failure.
        result["error_type"] = type(error).__name__
        mark('ERROR','M1_REMOTE_STAGE')
        write(directory / "result.json", result)
        raise
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
