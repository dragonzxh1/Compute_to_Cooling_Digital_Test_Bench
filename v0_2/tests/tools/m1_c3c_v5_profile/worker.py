"""Finite, read-only DEVELOPMENT timing of unchanged v4 package validation.

No candidate import, replay, final acceptance, approval, or qualification output.
The failed v4 execution is an immutable input identity, not this run's identity.
"""
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCOPE = "DEVELOPMENT_READ_ONLY_FINAL_TIMING"
REFERENCE_SHA = "759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357"
ROUTER = ".github/workflows/m1-remote-long-probe-v2-1.yml"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.read_bytes() == raw, "PROFILE_PERSISTENCE_FAILURE")


def main():
    directory, expected_control = sys.argv[1:]
    folder = Path(directory).resolve()
    require(platform.node().upper() != "HIPPO"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Windows"
            and folder.is_relative_to(ROOT / "artifacts/m1-c3c-v5-profile"),
            "PROFILE_INDEPENDENT_HOST_REQUIRED")
    write(folder / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (folder / "release.json").exists():
        require(time.monotonic() < deadline, "PROFILE_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    require(json.loads((folder / "release.json").read_bytes())["actual_python_pid"] == os.getpid(),
            "PROFILE_ACTUAL_PID_MISMATCH")
    raw_control = (Path(__file__).parent / "control.json").read_bytes()
    require(sha(raw_control) == expected_control, "PROFILE_CONTROL_DRIFT")
    control = json.loads(raw_control)
    require(control["scope"] == SCOPE and control["formal_behavior_authorized"] is False
            and control["sample_count"] == 10, "PROFILE_SCOPE_OR_FINITE_PLAN_DRIFT")
    reference_raw = (ROOT / control["reference_package_path"]).read_bytes()
    require(sha(reference_raw) == REFERENCE_SHA == control["reference_package_raw_sha256"],
            "PROFILE_REFERENCE_PACKAGE_DRIFT")
    definition = json.loads(reference_raw)
    require(len(definition["source_raw_sha256"]) == 797, "PROFILE_REFERENCE_COUNT_DRIFT")

    def sources():
        for name, digest in control["source_hashes"].items():
            require(sha((ROOT / name).read_bytes()) == digest, "PROFILE_SOURCE_DRIFT: " + name)
        for name, digest in definition["source_raw_sha256"].items():
            if name == ROUTER:
                require(control["versioned_entry_difference"]["reference_raw_sha256"] == digest,
                        "PROFILE_UNDECLARED_ENTRY_VERSION")
                continue
            require(sha((ROOT / name).read_bytes()) == digest,
                    "PROFILE_PROTECTED_REFERENCE_SOURCE_DRIFT: " + name)

    sources()
    require(not any(key in os.environ for key in (
        "C2C_C3C_APPROVAL_B64", "C2C_C3C_AUTHORIZATION_B64")),
        "PROFILE_MUST_NOT_CARRY_FORMAL_EXECUTION_CREDENTIALS")
    from v0_2.tests.tools.m1_c3c_v4 import authority as a
    from v0_2.tests.tools.m1_c3c_v4 import runtime_admission as admission
    before = admission.current_identity()
    lock_path = ROOT / definition["execution"]["environment_lock"]
    lock_sha = definition["source_raw_sha256"][definition["execution"]["environment_lock"]]
    expected_environment = a.load_bound(lock_path.read_bytes(), lock_sha)
    admission.enforce_environment(before, expected_environment)
    # A reference manifest is data for this micro-profile. It grants no authority.
    os.environ["C2C_C3C_PACKAGE_SHA256"] = REFERENCE_SHA
    events = folder / "timing.jsonl"

    def mark(event, **values):
        record = {"event": event, "pid": os.getpid(), "monotonic_ns": time.monotonic_ns(),
                  "utc_ns": time.time_ns(), **values}
        with events.open("ab") as stream:
            stream.write(json.dumps(record, sort_keys=True).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())

    path_count = 0
    path_wall = 0.0
    original_local_path = a.local_path

    def counted_path(*args, **kwargs):
        nonlocal path_count, path_wall
        begin = time.perf_counter()
        try:
            return original_local_path(*args, **kwargs)
        finally:
            path_count += 1
            path_wall += time.perf_counter() - begin

    mark("COUNTED_PACKAGE_BEGIN")
    start = time.perf_counter()
    with patch.object(a, "local_path", counted_path):
        admission.package()
    counted_wall = time.perf_counter() - start
    require(path_count == 797, "PROFILE_UNEXPECTED_PACKAGE_PATH_CALL_COUNT")
    mark("COUNTED_PACKAGE_END", wall_s=counted_wall, path_calls=path_count,
         path_wall_s=path_wall)
    samples = []
    for index in range(control["sample_count"]):
        mark("PACKAGE_SAMPLE_BEGIN", index=index)
        start = time.perf_counter()
        admission.package()
        elapsed = time.perf_counter() - start
        samples.append(elapsed)
        mark("PACKAGE_SAMPLE_END", index=index, wall_s=elapsed)
    environment_samples = []
    for index in range(control["sample_count"]):
        start = time.perf_counter()
        expected = a.load_bound(lock_path.read_bytes(), lock_sha)
        a.verify_environment(before, expected)
        environment_samples.append(time.perf_counter() - start)
    # Prove that this DEVELOPMENT source does not earn the old formal grant.
    approval_path = ROOT / "artifacts/m1-c3c-v4-authorization/user_freeze_approval.json"
    authorization_path = ROOT / "artifacts/m1-c3c-v4-authorization/formal_execution_authorization.json"
    approval = approval_path.read_bytes()
    authorization = authorization_path.read_bytes()
    try:
        a.authorize(reference_raw, REFERENCE_SHA, approval, sha(approval),
                    authorization, sha(authorization), os.environ["GITHUB_SHA"])
    except a.IntegrityError as error:
        require(str(error) == "AUTHORIZATION_SOURCE_COMMIT_DRIFT", "PROFILE_WRONG_REFUSAL")
        old_formal_authority_refused = True
    else:
        raise ValueError("PROFILE_SOURCE_WAS_ACCEPTED_AS_FROZEN_FORMAL_SOURCE")
    after = admission.current_identity()
    admission.enforce_environment(after, expected_environment)
    require(before == after, "PROFILE_ENVIRONMENT_DRIFT")
    sources()
    forbidden = ("v0_2.tests.tools.m1_engine_v4.engine",
                 "v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine")
    require(not any(name in sys.modules for name in forbidden), "PROFILE_IMPORTED_CANDIDATE")
    scale = control["reference_native_stage_record_count"]
    require(scale == 1969, "PROFILE_REFERENCE_SCALE_DRIFT")
    failure = json.loads((ROOT / control["reference_failure_evidence_path"]).read_bytes())
    require(failure["run_id"] == 38675166533 and failure["gate"] == "INVALID_C3_C_EXECUTION"
            and failure["upstream_native_evidence"]["completed_stage_records"] == scale,
            "PROFILE_REFERENCE_FAILURE_IDENTITY_DRIFT")
    result = {
        "schema": "m1-c3c-v5-readonly-timing-v1", "status": "TIMING_OBSERVATIONS_CAPTURED",
        "scope": SCOPE, "source_commit": os.environ["GITHUB_SHA"],
        "control_manifest_sha256": expected_control,
        "reference_failed_formal_run": 38675166533,
        "reference_package_raw_sha256": REFERENCE_SHA,
        "package_sample_wall_seconds": samples,
        "package_mean_wall_seconds": statistics.mean(samples),
        "package_median_wall_seconds": statistics.median(samples),
        "counted_package_wall_seconds": counted_wall,
        "counted_package_path_calls": path_count, "counted_path_wall_seconds": path_wall,
        "environment_lock_samples_wall_seconds": environment_samples,
        "reference_stage_records": scale,
        "projected_repeated_package_wall_seconds": statistics.mean(samples) * scale,
        "projection_is_not_full_final_reproduction": True,
        "reference_stage_budget_seconds": 480,
        "environment_before": before, "environment_after": after,
        "candidate_imported": False, "candidate_behavioral_execution": False,
        "formal_qualification": False, "old_formal_source_authority_refused": old_formal_authority_refused,
        "reference_sources_unchanged_except_declared_versioned_transport_entry": True,
        "qualified_result_generated": False, "approval_generated": False}
    write(folder / "result.json", result)
    mark("PROFILE_COMPLETE", projected_repeated_package_wall_seconds=result[
        "projected_repeated_package_wall_seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
