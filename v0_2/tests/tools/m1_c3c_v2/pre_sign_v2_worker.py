"""Actual-Job pre-sign byte/schema audit only; no candidate or formal behavior."""
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from .preflight_worker import write
ROOT = Path(__file__).resolve().parents[4]


def main():
    target, directory, expected = sys.argv[1:]
    folder = Path(directory).resolve()
    if (target != "CHECKS" or platform.node().upper() == "HIPPO"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or not folder.is_relative_to(ROOT / "artifacts/m1-c3c-pre-sign")):
        raise ValueError("PRE_SIGN_SCOPE_DENIED")
    write(folder / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (folder / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("PRE_SIGN_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    if json.loads((folder / "release.json").read_bytes())["actual_python_pid"] != os.getpid():
        raise ValueError("PRE_SIGN_ACTUAL_PID_DRIFT")
    raw = (ROOT / "v0_2/tests/tools/m1_c3c_v2/pre_sign_v2_control.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("PRE_SIGN_CONTROL_DRIFT")
    control = json.loads(raw)
    def verify():
        for name, h in control["source_hashes"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != h:
                raise ValueError("PRE_SIGN_SOURCE_DRIFT: " + name)
    verify()
    from v0_2.tests.tools.m1_remote_control_v3.admission import current_identity
    before = current_identity()
    from .verify_proposal import main as audit
    sys.argv = ["verify_proposal", "--expected-raw-sha256", control["proposal_raw_sha256"],
                "--output", str(folder / "proposal_readback.json")]
    audit()
    after = current_identity()
    verify()
    if before != after:
        raise ValueError("PRE_SIGN_ENVIRONMENT_DRIFT")
    if "v0_2.tests.tools.m1_engine_v4.engine" in sys.modules:
        raise ValueError("PRE_SIGN_CANDIDATE_IMPORT_FORBIDDEN")
    result = json.loads((folder / "proposal_readback.json").read_bytes())
    result.update(status="C3C_PRE_SIGN_READBACK_PASS", control_manifest_sha256=expected,
                  environment_before=before, environment_after=after)
    write(folder / "result.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
