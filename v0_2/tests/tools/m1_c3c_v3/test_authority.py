"""Synthetic authority tests only: no candidate/reference import or execution."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from . import authority as a


def synthetic():
    sources = {name: "1" * 64 for name in a.REQUIRED_BINDINGS}
    sources[a.REQUIRED_BINDINGS[0]] = a.CANDIDATE_SHA
    parts = {kind: "v0_2/tests/tools/m1_c3c_v3/" + kind + ".json"
             for kind in ("runner", "worker", "workflow", "environment_lock", "artifact_schema", "stop_rules")}
    sources.update({name: "2" * 64 for name in parts.values()})
    registrations = {key: "artifacts/m1-c3c-v3-freeze/" + key + ".json" for key in a.DECISIONS}
    sources.update({name: "4" * 64 for name in registrations.values()})
    package = {"schema": "m1-c3c-executable-proposal-v1", "status": "FINALIZED_AWAITING_USER_APPROVAL",
        "scope": a.SCOPE, "candidate_sha256": a.CANDIDATE_SHA, "limitations": dict(a.LIMITATIONS),
        "source_raw_sha256": sources, "inputs": [{"index": i, "row_count": 1,
        "input_canonical_sha256": "3" * 64} for i in range(101)],
        "startup_count": 50, "historical_startup_result": "49/50", "versioned_startup_result_is_separate": True,
        "strict_causal_exclusion_count": 5, "observer_field_count": 56, "comparator_rule_count": 18,
        "complete_only_publication_required": True, "PF06_supplemental_binding_id": "PF06-C8-NORMAL-SUPPLEMENT-v1",
        "prior_pass_credit": False, "registration_raw_sha256": {k: "4" * 64 for k in a.DECISIONS},
        "registration_paths": registrations, "execution": parts}
    raw = a.canonical(package); h = a.digest(raw); source = "5" * 40
    approval = {"schema": "m1-c3c-user-approval-receipt-v1", "status": "FROZEN_USER_APPROVED",
        "scope": a.SCOPE, "package_raw_sha256": h, "package_canonical_sha256": h,
        "decisions": {k: "APPROVED" for k in a.DECISIONS}, "registration_raw_sha256": package["registration_raw_sha256"],
        "candidate_sha256": a.CANDIDATE_SHA, "execution_source_commit": source}
    approval_raw = a.canonical(approval)
    auth = {"schema": "m1-c3c-execution-authorization-v1", "status": "EXECUTION_AUTHORIZED",
        "scope": a.SCOPE, "package_raw_sha256": h, "approval_receipt_raw_sha256": a.digest(approval_raw),
        "execution_source_commit": source, "environment_lock_raw_sha256": "2" * 64}
    return package, approval, auth, source


def check(package, approval, auth, source):
    raws = [a.canonical(x) for x in (package, approval, auth)]
    return a.authorize(raws[0], a.digest(raws[0]), raws[1], a.digest(raws[1]), raws[2], a.digest(raws[2]), source)


class AuthorityTests(unittest.TestCase):
    def test_exact_synthetic_positive(self):
        p, u, x, c = synthetic()
        self.assertEqual(check(p, u, x, c)["scope"], a.SCOPE)

    def test_development_result_cannot_be_promoted(self):
        self.assertRaises(a.IntegrityError, a.validate_package, {"status": "DEVELOPMENT_VALIDATED"})

    def test_self_declared_approval_is_insufficient(self):
        p, u, x, c = synthetic(); u = {"approved": True}
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_missing_executable_component(self):
        p, _, _, _ = synthetic(); del p["execution"]["worker"]
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_unbound_executable_component(self):
        p, _, _, _ = synthetic(); p["execution"]["worker"] = "missing.py"
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_proposal_not_finalized(self):
        p, _, _, _ = synthetic(); p["status"] = "DRAFT"
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_unsigned_scope_decision(self):
        p, u, x, c = synthetic(); u["decisions"]["PF06_supplement"] = "PENDING"
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_approval_wrong_canonical_identity(self):
        p, u, x, c = synthetic(); u["package_canonical_sha256"] = "a" * 64
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_execution_wrong_commit(self):
        p, u, x, c = synthetic(); x["execution_source_commit"] = "a" * 40
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_execution_wrong_environment_lock(self):
        p, u, x, c = synthetic(); x["environment_lock_raw_sha256"] = "a" * 64
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_execution_wrong_approval_receipt(self):
        p, u, x, c = synthetic(); x["approval_receipt_raw_sha256"] = "a" * 64
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_no_execution_authorization(self):
        p, u, x, c = synthetic(); x["status"] = "NOT_AUTHORIZED"
        self.assertRaises(a.IntegrityError, check, p, u, x, c)

    def test_candidate_cannot_be_rebound(self):
        p, _, _, _ = synthetic(); p["candidate_sha256"] = "a" * 64
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_complete_only_obligation_cannot_be_waived(self):
        p, _, _, _ = synthetic(); p["complete_only_publication_required"] = False
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_missing_cases_or_duplicate_index(self):
        p, _, _, _ = synthetic(); p["inputs"].pop()
        self.assertRaises(a.IntegrityError, a.validate_package, p)
        p, _, _, _ = synthetic(); p["inputs"][1]["index"] = 0
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_rows_and_bool_are_not_interchangeable(self):
        p, _, _, _ = synthetic(); p["inputs"][0]["row_count"] = True
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_history_or_limitations_cannot_be_rewritten(self):
        p, _, _, _ = synthetic(); p["historical_startup_result"] = "50/50"
        self.assertRaises(a.IntegrityError, a.validate_package, p)
        p, _, _, _ = synthetic(); p["limitations"]["FULL_P_HISTORY_VALIDATION_AVAILABLE"] = "YES"
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_previous_pass_not_credited(self):
        p, _, _, _ = synthetic(); p["prior_pass_credit"] = True
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_source_path_escape(self):
        for name in ("../escape", "/absolute", "C:/absolute", "a\\b", "a/../b", "a//b", "./a", ""):
            with self.subTest(name=name):
                self.assertRaises(a.IntegrityError, a.local_path, Path.cwd(), name)

    def test_sha_and_commit_shape(self):
        for value in ("a" * 70, "A" * 64, "a" * 63, True, None):
            self.assertRaises(a.IntegrityError, a.sha, value)
        self.assertRaises(a.IntegrityError, a.commit, "a" * 41)

    def test_byte_drift_duplicate_keys_and_nan(self):
        self.assertRaises(a.IntegrityError, a.load_bound, b'{}', "a" * 64)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'[]'):
            self.assertRaises(a.IntegrityError, a.load_bound, raw, a.digest(raw))

    def test_source_file_byte_drift(self):
        p, _, _, _ = synthetic()
        with tempfile.TemporaryDirectory() as td:
            for name in p["source_raw_sha256"]:
                path = Path(td) / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic-only")
            self.assertRaises(a.IntegrityError, a.verify_source_closure, p, td)

    def test_registration_file_must_be_bound(self):
        p, _, _, _ = synthetic(); p["registration_paths"]["SEM01"] = "unbound.json"
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_registration_file_hash_cannot_disagree(self):
        p, _, _, _ = synthetic(); p["registration_raw_sha256"]["SEM01"] = "b" * 64
        self.assertRaises(a.IntegrityError, a.validate_package, p)

    def test_exact_frozen_input_inventory(self):
        p, _, _, _ = synthetic()
        inv = [{"row_count": c["row_count"], "input_canonical_sha256": c["input_canonical_sha256"]} for c in p["inputs"]]
        self.assertTrue(a.verify_input_inventory(p, inv))

    def test_frozen_input_hash_and_row_count_cannot_drift(self):
        p, _, _, _ = synthetic()
        inv = [{"row_count": 1, "input_canonical_sha256": "3" * 64} for _ in range(101)]
        inv[0]["input_canonical_sha256"] = "b" * 64
        self.assertRaises(a.IntegrityError, a.verify_input_inventory, p, inv)
        inv[0]["input_canonical_sha256"] = "3" * 64; inv[0]["row_count"] = 2
        self.assertRaises(a.IntegrityError, a.verify_input_inventory, p, inv)

    def test_environment_requires_exact_registered_fields(self):
        expected = {k: "synthetic" for k in ("python", "system", "version", "machine", "image_os", "image_version", "dependencies")}
        self.assertTrue(a.verify_environment({**expected, "host": "separate-job"}, expected))
        drift = {**expected, "version": "different"}
        self.assertRaises(a.IntegrityError, a.verify_environment, drift, expected)
        incomplete = dict(expected); del incomplete["version"]
        self.assertRaises(a.IntegrityError, a.verify_environment, expected, incomplete)

    def test_integrity_failure_is_not_behavioral_fail(self):
        self.assertEqual(a.classify(False, True, ["bad result"])["behavioral_adjudication"], "NOT_MADE")

    def test_incomplete_is_not_pass(self):
        self.assertEqual(a.classify(True, False, [])["gate"], "C3_C_EXECUTION_INCOMPLETE")

    def test_behavioral_fail_is_not_pass(self):
        self.assertEqual(a.classify(True, True, ["CMP-A01"])["behavioral_adjudication"], "FAIL")

    def test_valid_pass_preserves_scope_and_limitations(self):
        result = a.classify(True, True, [])
        self.assertEqual(result["qualified_scope"], a.SCOPE)
        self.assertEqual(result["limitations"], a.LIMITATIONS)


if __name__ == "__main__":
    unittest.main()
