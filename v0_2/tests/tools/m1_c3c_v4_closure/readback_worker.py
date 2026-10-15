"""Review delivered bytes under a verified Job; never run a candidate/model."""
import hashlib
import json
import os
import platform
import re
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "C3_C_V4_FINAL_FREEZE_PACKAGE"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def write(path, value):
    raw = canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    require(path.read_bytes() == raw, "READBACK_RESULT_PERSISTENCE_FAILURE")


def verify_payload(folder, inventory):
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    require(actual == set(inventory["payload_files"]), "UNAUTHORIZED_EXTRA_OR_MISSING_PACKAGE_FILE")
    for name, expected in inventory["payload_raw_sha256"].items():
        require(sha((folder / name).read_bytes()) == expected, "DELIVERED_PAYLOAD_HASH_DRIFT: " + name)


def verify_transport(workflow):
    final = workflow[workflow.index("  final:\n"):]
    targets = re.findall(r"^          (?:name|pattern): (.+)$", final, re.M)
    expected = {"schema-*", "startup-*", "prepare", "ref-*", "reference-gate",
                "select-*", "split-*", "prefix-*", "plan", "final"}
    require(len(targets) == 10 and set(targets) == expected, "FINAL_NATIVE_ARTIFACT_FAMILY_INCOMPLETE")
    return True


def refusal_checks():
    # These synthetic vectors are explicitly NOT user authorization for the
    # real package. Nothing writes a FROZEN_USER_APPROVED receipt for it.
    from v0_2.tests.tools.m1_c3c_v4 import authority as a
    from v0_2.tests.tools.m1_c3c_v4.test_authority import synthetic
    p, u, x, commit = synthetic()
    checks = []
    def denied(name, action, types=(a.IntegrityError,)):
        try:
            action()
        except types as error:
            checks.append({"id": name, "status": "PASS", "rejection": str(error)})
        else:
            raise ValueError("REFUSAL_CHECK_ACCEPTED: " + name)
    def authorize(approval=u, authorization=x, source=commit):
        raws = [a.canonical(v) for v in (p, approval, authorization)]
        return a.authorize(raws[0], a.digest(raws[0]), raws[1], a.digest(raws[1]),
                           raws[2], a.digest(raws[2]), source)
    denied("MISSING_APPROVAL", lambda: authorize(approval={}))
    denied("WRONG_EXECUTION_COMMIT", lambda: authorize(source="6" * 40))
    denied("WRONG_PACKAGE_RAW_HASH", lambda: a.load_bound(a.canonical(p), "0" * 64))
    wrong = deepcopy(x); wrong["scope"] = "UNAPPROVED_SCOPE"
    denied("WRONG_SCOPE", lambda: authorize(authorization=wrong))
    with tempfile.TemporaryDirectory(prefix="C3C_CLOSURE_SYNTHETIC_ONLY_") as td:
        denied("MISSING_SOURCE_ARTIFACT", lambda: a.verify_source_closure(p, Path(td)),
               types=(FileNotFoundError, a.IntegrityError))
    # Exercise package inventory refusal without modifying reviewed files.
    inv = json.loads((PACKAGE / "EXACT_HASH_INVENTORY.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="C3C_PAYLOAD_SYNTHETIC_ONLY_") as td:
        denied("MISSING_DELIVERY_ARTIFACT", lambda: verify_payload(Path(td), inv), types=(ValueError,))
        root = Path(td)
        for name in inv["payload_files"]:
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((PACKAGE / name).read_bytes())
        (root / "UNAUTHORIZED_SYNTHETIC_ONLY.txt").write_bytes(b"not registered")
        denied("EXTRA_UNAUTHORIZED_DELIVERY_FILE", lambda: verify_payload(root, inv), types=(ValueError,))
    workflow = (ROOT / ".github/workflows/m1-c3c-full-v4.yml").read_text(encoding="utf-8")
    verify_transport(workflow)
    denied("MISSING_UPSTREAM_REFERENCE_DELIVERY", lambda: verify_transport(
        workflow.replace("          pattern: ref-*", "          pattern: omitted-ref-*")), types=(ValueError,))
    denied("MISSING_UPSTREAM_PREFIX_NATIVE_DELIVERY", lambda: verify_transport(
        workflow.replace("          pattern: prefix-*", "          pattern: omitted-prefix-*")), types=(ValueError,))
    return checks


def main():
    target, directory, expected = sys.argv[1:]
    folder = Path(directory).resolve()
    require(target == "CHECKS" and platform.node().upper() != "HIPPO"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Windows"
            and folder.is_relative_to(ROOT / "artifacts/m1-c3c-v4-closure"), "READONLY_REVIEW_SCOPE_DENIED")
    write(folder / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (folder / "release.json").exists():
        require(time.monotonic() <= deadline, "READBACK_ACTUAL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    require(json.loads((folder / "release.json").read_bytes())["actual_python_pid"] == os.getpid(),
            "READBACK_ACTUAL_PID_DRIFT")
    control_raw = (Path(__file__).parent / "control.json").read_bytes()
    require(sha(control_raw) == expected, "READBACK_CONTROL_DRIFT")
    control = json.loads(control_raw)
    require(control["scope"] == "DEVELOPMENT_PRE_SIGN_READ_ONLY"
            and control["formal_behavior_authorized"] is False, "READBACK_CONTROL_AUTHORITY")
    def source_check():
        for name, h in control["source_hashes"].items():
            require(sha((ROOT / name).read_bytes()) == h, "READONLY_REVIEW_SOURCE_DRIFT: " + name)
    source_check()
    from v0_2.tests.tools.m1_c3c_v4 import authority as a
    from v0_2.tests.tools.m1_c3c_v4.runtime_admission import current_identity, enforce_environment
    before = current_identity()
    definition_raw = (PACKAGE / "EXECUTABLE_FREEZE_MANIFEST.json").read_bytes()
    require(sha(definition_raw) == control["proposal_raw_sha256"], "DELIVERED_MANIFEST_DRIFT")
    definition = a.validate_package(a.load_bound(definition_raw, control["proposal_raw_sha256"]))
    require(definition_raw == (ROOT / "artifacts/m1-c3c-v4-freeze/executable_proposal.json").read_bytes(),
            "DELIVERED_AND_ACTIVE_MANIFEST_DIFFER")
    bound = a.verify_source_closure(definition, ROOT)
    require(bound == control["expected_source_binding_count"], "BOUND_SCOPE_COUNT_DRIFT")
    expected_environment = a.load_bound((ROOT / definition["execution"]["environment_lock"]).read_bytes(),
        definition["source_raw_sha256"][definition["execution"]["environment_lock"]])
    enforce_environment(before, expected_environment)
    inventory_raw = (PACKAGE / "EXACT_HASH_INVENTORY.json").read_bytes()
    inventory = json.loads(inventory_raw)
    require(inventory["source_raw_sha256"] == definition["source_raw_sha256"], "DELIVERY_HASH_INVENTORY_DRIFT")
    verify_payload(PACKAGE, inventory)
    verify_transport((ROOT / definition["execution"]["workflow"]).read_text(encoding="utf-8"))
    index = json.loads((PACKAGE / "SCOPE_SEMANTIC_REGISTRATION_INDEX.json").read_bytes())
    require(index["registration_raw_sha256"] == definition["registration_raw_sha256"], "DELIVERY_REGISTRATION_INDEX_DRIFT")
    for key, path in index["package_registration_paths"].items():
        require((PACKAGE / path).read_bytes() == (ROOT / definition["registration_paths"][key]).read_bytes(),
                "DELIVERED_REGISTRATION_CHANGED: " + key)
    # Reuse the independent byte/schema inventory auditor, not a candidate run.
    from v0_2.tests.tools.m1_c3c_v4.verify_proposal import main as audit
    sys.argv = ["verify_proposal", "--expected-raw-sha256", control["proposal_raw_sha256"],
                "--output", str(ROOT / "artifacts/m1-c3c-pre-sign" / folder.name / "proposal_readback.json")]
    audit()
    audit_result = json.loads(Path(sys.argv[-1]).read_bytes())
    require(audit_result["package_canonical_sha256"] == control["proposal_canonical_sha256"], "CANONICAL_PACKAGE_DRIFT")
    negatives = refusal_checks()
    require(len(negatives) == control["expected_refusal_check_count"], "READBACK_REFUSAL_INVENTORY_DRIFT")
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / definition["execution"]["artifact_schema"]).read_bytes())
    Draft202012Validator.check_schema(schema)
    stops = json.loads((ROOT / definition["execution"]["stop_rules"]).read_bytes())
    require(stops["scope"] == definition["scope"], "STOP_SCOPE_DRIFT")
    after = current_identity(); enforce_environment(after, expected_environment)
    require(before == after, "READBACK_ENVIRONMENT_BEFORE_AFTER_DRIFT")
    source_check(); a.verify_source_closure(definition, ROOT); verify_payload(PACKAGE, inventory)
    forbidden = {"v0_2.tests.tools.m1_engine_v4.engine", "v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine"}
    require(not forbidden.intersection(sys.modules), "READONLY_REVIEW_IMPORTED_CANDIDATE")
    result = {"schema": "m1-c3c-v4-final-package-readback-v1", "status": "C3C_V4_FINAL_PACKAGE_READBACK_PASS",
        "scope": "DEVELOPMENT_PRE_SIGN_READ_ONLY", "source_commit": os.environ["GITHUB_SHA"],
        "control_manifest_sha256": expected, "execution_source_commit": os.environ["GITHUB_SHA"],
        "delivery_commit": os.environ["GITHUB_SHA"], "commits_distinct_roles_may_share_exact_tree": True,
        "proposal_raw_sha256": sha(definition_raw), "proposal_canonical_sha256": sha(canonical(definition)),
        "source_bindings_verified": bound, "inputs": audit_result["inputs"], "input_rows": audit_result["input_rows"],
        "expected_full_snapshots": audit_result["expected_full_snapshots"],
        "required_static_stages_before_final": audit_result["required_static_stages_before_final"],
        "registration_hashes": definition["registration_raw_sha256"], "inventory_raw_sha256": sha(inventory_raw),
        "payload_files": inventory["payload_files"], "payload_raw_sha256": inventory["payload_raw_sha256"],
        "refusal_checks": negatives, "environment_before": before, "environment_after": after,
        "schema_and_stop_policy_verified": True, "candidate_imported": False, "candidate_behavioral_execution": False,
        "all_final_native_delivery_families_verified": True,
        "formal_qualification": False, "approval_generated": False, "limitations": definition["limitations"],
        "post_cleanup_external_attestation_required": True}
    write(folder / "result.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
