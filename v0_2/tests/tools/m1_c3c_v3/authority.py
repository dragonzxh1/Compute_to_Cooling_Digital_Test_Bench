"""Fail-closed, byte-bound authority for a future user-signed C3-C package.

This module never runs a model, invents PLC receipts, promotes development results,
or modifies a sealed guard. Synthetic unit tests do not constitute user approval.
The final package and behavioral runner are separate, not finalized by this file.
"""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

SCOPE = "M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN"
CANDIDATE_SHA = "70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce"
LIMITATIONS = {
    "ARBITRARY_POST_EXCEPTION_ATOMICITY": "NOT_PROVEN",
    "PF06_ORIGINAL_SCOPE": "INCOMPLETE",
    "FULL_P_HISTORY_VALIDATION_AVAILABLE": "NO",
    "T09": "IMPLEMENTATION_HOLD",
    "REAL_HARDWARE": "CALIBRATION_REQUIRED",
    "PRODUCTION_IMPLEMENTATION_AUTHORIZED": "NO",
    "HARDWARE_CONTROL_AUTHORIZED": "NO",
    "PHASE6": "NO",
}
DECISIONS = ("limited_scope", "SEM01", "SEM02", "PF06_supplement")
REQUIRED_BINDINGS = (
    "v0_2/tests/tools/m1_engine_v4/engine.py",
    "v0_2/tests/tools/m1_engine_v3/comparator.py",
    "phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json",
    "phase5_r5_2_1r4_7_c3_a_comparator_registration.json",
    "phase5_r5_2_1r4_7_c3_a_split_interface_spec.json",
    "phase5_r5_2_1r4_7_c2_r1_timing_policy_registration.json",
    "contracts/14_control_input_permission_contract.md",
    "contracts/15_safety_supervisor_contract.md",
    "contracts/15A_tracking_safety_policy_amendment.md",
    "phase5_r5_2_2_fixture_tracking_profile.json",
)


class IntegrityError(ValueError):
    """No behavioral adjudication is possible under this authority failure."""


def require(condition, reason):
    if not condition:
        raise IntegrityError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "INVALID_SHA256_IDENTITY")
    return value


def commit(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value) is not None,
            "INVALID_EXECUTION_COMMIT")
    return value


def load_bound(raw, expected_raw_sha256):
    require(type(raw) is bytes and digest(raw) == sha(expected_raw_sha256), "RAW_BYTE_IDENTITY_DRIFT")
    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def invalid_constant(value):
        raise IntegrityError("NONFINITE_JSON_CONSTANT: " + value)
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    require(type(result) is dict, "JSON_OBJECT_REQUIRED")
    return result


def local_path(root, name):
    require(type(name) is str and "\\" not in name and ":" not in name,
            "UNREGISTERED_SOURCE_PATH")
    p = PurePosixPath(name)
    require(not p.is_absolute() and name == p.as_posix() and
            bool(p.parts) and not any(x in (".", "..") for x in p.parts), "SOURCE_PATH_ESCAPE")
    resolved = (Path(root).resolve() / name).resolve()
    require(resolved.is_relative_to(Path(root).resolve()), "SOURCE_SYMLINK_ESCAPE")
    return resolved


def validate_package(package):
    require(package.get("schema") == "m1-c3c-executable-proposal-v1", "PACKAGE_SCHEMA")
    require(package.get("status") == "FINALIZED_AWAITING_USER_APPROVAL", "PACKAGE_NOT_FINALIZED")
    require(package.get("scope") == SCOPE, "SCOPE_NOT_APPROVED_FOR_THIS_ENTRY")
    require(package.get("candidate_sha256") == CANDIDATE_SHA, "CANDIDATE_IDENTITY_DRIFT")
    require(package.get("limitations") == LIMITATIONS, "SCOPED_LIMITATIONS_HIDDEN_OR_CHANGED")
    sources = package.get("source_raw_sha256")
    require(type(sources) is dict and all(name in sources for name in REQUIRED_BINDINGS), "INCOMPLETE_SOURCE_CLOSURE")
    for name, value in sources.items():
        local_path(Path.cwd(), name)
        sha(value)
    require(sources[REQUIRED_BINDINGS[0]] == CANDIDATE_SHA, "SOURCE_CANDIDATE_MISMATCH")
    inputs = package.get("inputs")
    require(type(inputs) is list and len(inputs) == 101, "INPUT_INVENTORY_INCOMPLETE")
    for i, case in enumerate(inputs):
        require(type(case) is dict and case.get("index") == i and type(case.get("index")) is int
                and type(case.get("row_count")) is int and case["row_count"] > 0, "INPUT_INDEX_OR_ROW_COUNT")
        sha(case.get("input_canonical_sha256"))
    require(package.get("startup_count") == 50 and package.get("historical_startup_result") == "49/50"
            and package.get("versioned_startup_result_is_separate") is True, "STARTUP_HISTORY_REWRITE")
    require(package.get("strict_causal_exclusion_count") == 5, "EXCLUSION_SCOPE_CHANGED")
    require(package.get("observer_field_count") == 56 and package.get("comparator_rule_count") == 18,
            "COMPARISON_SCOPE_WEAKENED")
    require(package.get("complete_only_publication_required") is True,
            "MANDATORY_PUBLICATION_OBLIGATION_WAIVED")
    require(package.get("PF06_supplemental_binding_id") == "PF06-C8-NORMAL-SUPPLEMENT-v1",
            "PF06_SUPPLEMENT_NOT_REGISTERED")
    require(package.get("prior_pass_credit") is False, "PREVIOUS_RESULT_CREDIT_FORBIDDEN")
    registrations = package.get("registration_raw_sha256")
    require(type(registrations) is dict and set(registrations) == set(DECISIONS), "DECISION_REGISTRATION_MISSING")
    for value in registrations.values():
        sha(value)
    registration_paths = package.get("registration_paths")
    require(type(registration_paths) is dict and set(registration_paths) == set(DECISIONS), "DECISION_FILES_MISSING")
    for key, name in registration_paths.items():
        require(name in sources and sources[name] == registrations[key], "DECISION_FILE_NOT_BYTE_BOUND")
    execution = package.get("execution")
    require(type(execution) is dict and set(execution) == {"runner", "worker", "workflow", "environment_lock", "artifact_schema", "stop_rules"}, "EXECUTABLE_BINDINGS_INCOMPLETE")
    for name in execution.values():
        require(name in sources, "UNBOUND_EXECUTABLE_COMPONENT")
    return package


def verify_source_closure(package, root):
    validate_package(package)
    for name, expected in package["source_raw_sha256"].items():
        require(digest(local_path(root, name).read_bytes()) == expected, "PROTECTED_SOURCE_DRIFT: " + name)
    spec = json.loads(local_path(root, REQUIRED_BINDINGS[2]).read_bytes())
    verify_input_inventory(package, spec["input_inventory"])
    return len(package["source_raw_sha256"])


def verify_input_inventory(package, frozen_inventory):
    expected = [{"index": i, "row_count": item["row_count"],
                 "input_canonical_sha256": item["input_canonical_sha256"]}
                for i, item in enumerate(frozen_inventory)]
    require(package["inputs"] == expected, "FROZEN_INPUT_METADATA_DRIFT")
    return True


def authorize(package_raw, package_sha, approval_raw, approval_sha,
              authorization_raw, authorization_sha, actual_commit):
    package = validate_package(load_bound(package_raw, package_sha))
    approval = load_bound(approval_raw, approval_sha)
    authorization = load_bound(authorization_raw, authorization_sha)
    # Trusted hashes must come from the separately authorized dispatch, never
    # from a document's self-declared approved=True or a previous dev run.
    require(approval.get("schema") == "m1-c3c-user-approval-receipt-v1"
            and approval.get("status") == "FROZEN_USER_APPROVED", "NO_EXACT_USER_FREEZE_APPROVAL")
    require(approval.get("package_raw_sha256") == package_sha
            and approval.get("package_canonical_sha256") == digest(canonical(package)), "APPROVAL_PACKAGE_DRIFT")
    require(approval.get("decisions") == {name: "APPROVED" for name in DECISIONS}, "UNRESOLVED_USER_SCOPE_DECISION")
    require(approval.get("registration_raw_sha256") == package["registration_raw_sha256"], "APPROVAL_REGISTRATION_DRIFT")
    require(approval.get("candidate_sha256") == CANDIDATE_SHA, "APPROVED_CANDIDATE_DRIFT")
    require(authorization.get("schema") == "m1-c3c-execution-authorization-v1"
            and authorization.get("status") == "EXECUTION_AUTHORIZED", "FORMAL_EXECUTION_NOT_AUTHORIZED")
    require(authorization.get("scope") == SCOPE and approval.get("scope") == SCOPE, "AUTHORIZATION_SCOPE_DRIFT")
    require(authorization.get("package_raw_sha256") == package_sha
            and authorization.get("approval_receipt_raw_sha256") == approval_sha, "AUTHORIZATION_FREEZE_DRIFT")
    actual_commit = commit(actual_commit)
    require(authorization.get("execution_source_commit") == actual_commit
            and approval.get("execution_source_commit") == actual_commit, "AUTHORIZATION_SOURCE_COMMIT_DRIFT")
    sha(authorization.get("environment_lock_raw_sha256"))
    require(authorization["environment_lock_raw_sha256"] ==
            package["source_raw_sha256"][package["execution"]["environment_lock"]], "AUTHORIZATION_ENVIRONMENT_DRIFT")
    return {"scope": SCOPE, "package_raw_sha256": package_sha,
            "approval_receipt_raw_sha256": approval_sha, "authorization_raw_sha256": authorization_sha,
            "candidate_sha256": CANDIDATE_SHA, "execution_source_commit": actual_commit}


def verify_environment(actual, expected):
    # Per-job host/PID/path remain raw evidence. Machine-independent identities
    # are frozen explicitly, not recomputed from whichever host happens to run.
    keys = ("python", "system", "version", "machine", "image_os", "image_version", "dependencies")
    require(type(actual) is dict and type(expected) is dict and set(expected) == set(keys), "ENVIRONMENT_SPEC_INCOMPLETE")
    images = expected["image_version"]
    if type(images) is list:
        require(images == ["20261004.326.1", "20261012.333.1"], "IMAGE_ALLOWLIST_NOT_APPROVED")
        require(type(actual.get("image_version")) is str and actual["image_version"] in images,
                "QUALIFICATION_ENVIRONMENT_DRIFT")
        keys = tuple(k for k in keys if k != "image_version")
    require(all(actual.get(k) == expected[k] for k in keys), "QUALIFICATION_ENVIRONMENT_DRIFT")
    return True


def classify(integrity_complete, complete_scope, behavioral_failures):
    require(type(integrity_complete) is bool and type(complete_scope) is bool
            and type(behavioral_failures) is list, "INVALID_ADJUDICATION_ARGUMENTS")
    if not integrity_complete:
        return {"gate": "INVALID_C3_C_EXECUTION", "behavioral_adjudication": "NOT_MADE"}
    if behavioral_failures:
        return {"gate": "C3_C_LIMITED_SOFTWARE_QUALIFICATION_FAIL", "behavioral_adjudication": "FAIL"}
    if not complete_scope:
        return {"gate": "C3_C_EXECUTION_INCOMPLETE", "behavioral_adjudication": "NOT_MADE"}
    return {"gate": "C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS", "behavioral_adjudication": "PASS",
            "qualified_scope": SCOPE, "limitations": dict(LIMITATIONS)}
