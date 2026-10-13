"""Outside-checkout source SDK smoke, in an externally verified venv Python Job."""
import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise OSError("INSTALL_EVIDENCE_READBACK_FAILURE")


def main():
    _, directory, expected_control = sys.argv[1:]
    directory = Path(directory).resolve()
    if (platform.node().upper() == "HIPPO" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted" or os.environ.get("RUNNER_OS") != "Windows"
            or not directory.is_relative_to(ROOT / "artifacts/m1-sdk-install")):
        raise ValueError("INSTALL_HOST_SCOPE_DENIED")
    write(directory / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (directory / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("INSTALL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    if json.loads((directory / "release.json").read_bytes())["actual_python_pid"] != os.getpid():
        raise ValueError("INSTALL_PID_RELEASE_MISMATCH")
    control = ROOT / "v0_2/tests/tools/m1_release_v1/delivery_control.json"
    if hashlib.sha256(control.read_bytes()).hexdigest() != expected_control:
        raise ValueError("INSTALL_CONTROL_IDENTITY")
    definition = json.loads(control.read_bytes())
    for name, digest in definition["source_hashes"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("INSTALL_SOURCE_DRIFT: " + name)
    lock = json.loads((ROOT / "v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json").read_bytes())
    dependencies = {name: importlib.metadata.version(name) for name in lock["dependencies"]}
    if platform.python_version() != "3.11.9" or dependencies != lock["dependencies"]:
        raise ValueError("INSTALL_NEW_VENV_DEPENDENCY_DRIFT")
    sdk = Path(os.environ["C2C_SDK_ROOT"]).resolve()
    workspace = Path(os.environ["C2C_SDK_WORKSPACE"]).resolve()
    archive = Path(os.environ["C2C_SDK_ZIP"]).resolve()
    if sdk.is_relative_to(ROOT) or workspace.is_relative_to(ROOT) or sdk == workspace:
        raise ValueError("INSTALL_REQUIRES_OUTSIDE_CHECKOUT")
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    delivery = json.loads((sdk / "DELIVERY_MANIFEST.json").read_bytes())
    for entry in delivery["files"]:
        p = (sdk / entry["path"]).resolve()
        if not p.is_relative_to(sdk) or hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("UNPACKED_SDK_BYTE_DRIFT")
    os.chdir(workspace)
    # Remove checkout import paths and cached repository namespace packages.
    sys.path[:] = [p for p in sys.path if p and not Path(p).resolve().is_relative_to(ROOT)]
    for name in list(sys.modules):
        if name == "v0_2" or name.startswith("v0_2."):
            del sys.modules[name]
    importlib.invalidate_caches()
    outputs = []
    for arguments in (["--describe", "--verify"], ["--run", "--input-index", "15", "--rows", "3"]):
        stream = io.StringIO()
        sys.argv = [str(sdk / "sdk_cli.py"), *arguments]
        with contextlib.redirect_stdout(stream):
            runpy.run_path(str(sdk / "sdk_cli.py"), run_name="__main__")
        outputs.append(json.loads(stream.getvalue()))
    source = Path(sys.modules["v0_2.tests.tools.m1_engine_v4.engine"].__file__).resolve()
    if not source.is_relative_to(sdk) or outputs[1]["comparison"]["status"] != "PASS" or outputs[1]["example_prefix_rows"] != 3:
        raise ValueError("INSTALLED_SDK_WRONG_SUT_OR_RESULT")
    after = {name: importlib.metadata.version(name) for name in lock["dependencies"]}
    if dependencies != after:
        raise ValueError("INSTALL_ENVIRONMENT_AFTER_DRIFT")
    write(directory / "result.json", {"status": "SDK_OUTSIDE_CHECKOUT_SMOKE_PASS", "source_commit": os.environ["GITHUB_SHA"],
          "control_manifest_sha256": expected_control, "archive_sha256": archive_sha,
          "venv_python": sys.executable, "dependencies": dependencies, "imported_sut_file": str(source),
          "working_directory": str(workspace), "outputs": outputs, "full_campaign_credit": False,
          "formal_qualification": False, "production": False, "hardware": "CALIBRATION_REQUIRED"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
