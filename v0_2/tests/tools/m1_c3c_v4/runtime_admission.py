"""Independent formal admission, never a replacement for a sealed dev guard."""
import base64
import json
import os
import platform
from pathlib import Path
from .authority import (authorize, digest, load_bound, local_path, require,
                        validate_package, verify_environment, verify_source_closure)

ROOT = Path(__file__).resolve().parents[4]
PACKAGE_PATH = "artifacts/m1-c3c-v4-freeze/executable_proposal.json"


def package():
    expected = os.environ.get("C2C_C3C_PACKAGE_SHA256")
    raw = (ROOT / PACKAGE_PATH).read_bytes()
    return raw, validate_package(load_bound(raw, expected))


def authority_record():
    require(platform.node().upper() != "HIPPO" and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Windows", "C3C_INDEPENDENT_HOST_REQUIRED")
    raw, data = package()
    approval = base64.b64decode(os.environ["C2C_C3C_APPROVAL_B64"], validate=True)
    authorization = base64.b64decode(os.environ["C2C_C3C_AUTHORIZATION_B64"], validate=True)
    record = authorize(raw, os.environ["C2C_C3C_PACKAGE_SHA256"],
        approval, os.environ["C2C_C3C_APPROVAL_SHA256"], authorization,
        os.environ["C2C_C3C_AUTHORIZATION_SHA256"], os.environ["GITHUB_SHA"])
    verify_source_closure(data, ROOT)
    return data, record


def current_identity():
    # Metadata helper only; it imports no models and grants no dev/formal scope.
    from v0_2.tests.tools.m1_remote_control_v3.admission import current_identity as read_identity
    return read_identity()


def enforce_environment(actual, expected):
    """Retain rejected metadata without admitting it or importing any model."""
    from .authority import IntegrityError
    try:
        verify_environment(actual, expected)
    except IntegrityError as error:
        error.actual_environment = actual
        error.expected_environment = expected
        error.environment_differences = {
            key: {"expected": value, "actual": actual.get(key)}
            for key, value in expected.items()
            if (actual.get(key) not in value if key == "image_version" and type(value) is list
                else actual.get(key) != value)
        }
        raise


def manifest():
    data, _ = authority_record()
    name = "v0_2/tests/tools/m1_campaign_v4/execution_manifest.json"
    require(name in data["source_raw_sha256"], "UNBOUND_LEGACY_TRANSPORT_MANIFEST")
    return load_bound(local_path(ROOT, name).read_bytes(), data["source_raw_sha256"][name])


def admit(*, bootstrap=False):
    data, record = authority_record()
    actual = current_identity()
    name = data["execution"]["environment_lock"]
    expected = load_bound(local_path(ROOT, name).read_bytes(), data["source_raw_sha256"][name])
    enforce_environment(actual, expected)
    if not bootstrap:
        path = Path(os.environ["C2C_C3C_RUNTIME_BINDINGS_PATH"]).resolve()
        require(path.is_relative_to(ROOT / "artifacts/liquid-recovery-v1"), "RUNTIME_BINDINGS_SCOPE")
        bindings = load_bound(path.read_bytes(), os.environ["C2C_C3C_RUNTIME_BINDINGS_SHA256"])
        require(bindings["scope"] == record["scope"] and bindings["execution_identity"] == record,
                "RUNTIME_APPROVAL_BINDING_DRIFT")
        require(bindings["runtime_identity"] == actual, "PER_JOB_RUNTIME_IDENTITY_DRIFT")
        for key in ("runtime_input_raw_hashes", "runtime_binary_raw_hashes"):
            for name, expected_sha in bindings[key].items():
                require(digest(local_path(ROOT, name).read_bytes()) == expected_sha,
                        "FRESH_RUNTIME_BINDING_DRIFT: " + name)
    return {"environment": actual, "execution_identity": record}
