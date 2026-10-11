"""Fail closed until a separate environment has been registered and reviewed."""
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCOPE = "GENERIC_LIQUID_COOLING_DEVELOPMENT_SMOKE"


def admit():
    # This is a workload hold, not a claim that MachineName proves isolation.
    if platform.node().upper() == "HIPPO":
        raise RuntimeError("HARD_HANG_HOST_WORKLOAD_HOLD")
    path = os.environ.get("C2C_RECOVERY_REGISTRATION_PATH")
    expected = os.environ.get("C2C_RECOVERY_REGISTRATION_SHA256")
    if not path or not expected:
        raise RuntimeError("INDEPENDENT_ENVIRONMENT_NOT_REGISTERED")
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("ENVIRONMENT_REGISTRATION_DRIFT")
    record = json.loads(raw)
    if record.get("scope") != SCOPE or record.get("status") != "REVIEWED_FOR_SMOKE_EXECUTION":
        raise RuntimeError("ENVIRONMENT_REVIEW_REQUIRED")
    if record.get("independent_execution_location") != "GITHUB_HOSTED_WINDOWS":
        raise RuntimeError("INDEPENDENT_LOCATION_NOT_SUPPORTED_BY_THIS_ADAPTER")
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows"):
        raise RuntimeError("GITHUB_HOSTED_WINDOWS_REQUIRED")
    lock = json.loads(
        (ROOT / "v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json").read_bytes()
    )
    actual = {
        "host": platform.node(), "python": platform.python_version(),
        "executable": sys.executable, "system": platform.system(),
        "version": platform.version(), "machine": platform.machine(),
        "image_os": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion"),
        "dependencies": {name: importlib.metadata.version(name) for name in lock["dependencies"]},
    }
    if actual != record.get("runtime_identity"):
        raise RuntimeError("INDEPENDENT_ENVIRONMENT_IDENTITY_DRIFT")
    if actual["python"] != "3.11.9" or actual["dependencies"] != lock["dependencies"]:
        raise RuntimeError("PINNED_RUNTIME_OR_DEPENDENCY_MISMATCH")
    source_manifest = ROOT / "v0_2/tests/tools/liquid_recovery_v1/source_inventory.json"
    source_bytes = source_manifest.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != record.get("source_inventory_raw_sha256"):
        raise RuntimeError("RECOVERY_SOURCE_INVENTORY_DRIFT")
    manifest = json.loads(source_bytes)
    if not manifest.get("source_raw_hashes"):
        raise RuntimeError("EMPTY_SOURCE_INVENTORY_REJECTED")
    for relative, source_hash in manifest["source_raw_hashes"].items():
        file_path = (ROOT / relative).resolve()
        if not file_path.is_relative_to(ROOT) or hashlib.sha256(file_path.read_bytes()).hexdigest() != source_hash:
            raise RuntimeError("RECOVERY_PROTECTED_SOURCE_DRIFT")
    # Reviewed location and identity are necessary, not proof of host stability.
    return expected
