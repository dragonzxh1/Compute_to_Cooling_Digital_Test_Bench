"""Synthetic/static checks only; never runs a reference/candidate or formal exam."""
import ast
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator, ValidationError
from . import authority as a
from . import final_gate as f
from . import runtime_admission as r
from . import bindings

ROOT = Path(__file__).resolve().parents[4]


def sem02_vector():
    expected = []; actual = []
    for i in range(5):
        reason = "UNVERIFIED_HISTORICAL_ISSUE" if i == 0 else "INCOMPLETE_QUARANTINED_INPUT"
        h = str(i) * 64
        expected.append({"nodeid": "synthetic-only:" + str(i), "reason": reason,
                         "events": 1, "input_typed_hashes": [h]})
        actual.append({"nodeid": "synthetic-only:" + str(i), "causal_reason": reason,
                       "domain_events": [{"input_typed_sha256": h, "PLC_receipts": 0, "Safety_commits": 0}],
                       "strict_P1_Lane_B": "INCOMPLETE", "strict_P1_Lane_C": "INCOMPLETE",
                       "fake_PLC_receipts": False, "fake_Safety_decisions": False, "source_sensor_coerced_valid": False})
    return {"cases": actual}, {"cases": expected}


def pf06_vector():
    d = {"stage_id": "C-history", "case_key": "C8_normal", "input_canonical_sha256": "a" * 64}
    pre = {"state": "TRACKING_PROGRESS", "core_sha256": "b" * 64, "old_command": {"value": 0.7}}
    post = {"state": "HANDOFF_PENDING", "core_sha256": "c" * 64}
    safety = {"severity": "NORMAL", "reason_codes": []}
    phases = {k: "d" * 64 for k in ("PRE", "SAFETY", "PLC", "POST")}
    negatives = [{"stage_id": "synthetic-negative:" + str(i), "input_canonical_sha256": str(i) * 64} for i in range(2)]
    registration = {"binding_id": "PF06-C8-NORMAL-SUPPLEMENT-v1", "source_descriptor": d,
        "row_index_zero_based": 4, "time_ns": 800000000, "source_id": "synthetic-measurement:800ms",
        "independent_expectations": {"PRE": pre, "POST": post, "expected_Safety": safety},
        "phase_record_hashes": phases, "negative_controls": negatives}
    cut = {"source_descriptor": deepcopy(d), "row_index": 4, "time_ns": 800000000,
        "source_id": "synthetic-measurement:800ms", "observed_preconditions": {"PF-06": True},
        "independent_expected_PRE": deepcopy(pre), "independent_expected_POST": deepcopy(post),
        "Safety": deepcopy(safety), "phase_record_hashes": deepcopy(phases), "PLC": {"producer": "SIMULATED_PLC"}}
    proof = {"version": registration["binding_id"], "positive_witness": cut,
        "negative_controls": [{"descriptor": deepcopy(x), "all_PF06_absent": True,
                               "comparison": {"status": "PASS"}} for x in negatives],
        "comparison": {"status": "PASS"}, "self_approved": False}
    return {"PF06_proposal": proof, "original_validated_count": 15, "original_matrix_changed": False}, registration


class AssemblyTests(unittest.TestCase):
    def test_all_owned_python_files_compile_without_execution(self):
        for path in (ROOT / "v0_2/tests/tools/m1_c3c_v1").glob("*.py"):
            compile(path.read_bytes(), str(path), "exec")

    def test_formal_driver_algorithm_ast_is_unchanged(self):
        old = ast.parse((ROOT / "v0_2/tests/tools/m1_engine_v3/stream_worker.py").read_bytes())
        new = ast.parse((ROOT / "v0_2/tests/tools/m1_c3c_v1/stream_worker.py").read_bytes())
        old_fn = next(x for x in old.body if isinstance(x, ast.FunctionDef) and x.name == "execute")
        new_fn = next(x for x in new.body if isinstance(x, ast.FunctionDef) and x.name == "execute")
        class Normalize(ast.NodeTransformer):
            def visit_ImportFrom(self, node):
                # Imports select exact byte-bound helpers; admission is the one
                # intentional replacement, never an assertion/math change.
                node = deepcopy(node)
                if node.module and node.module.startswith("v0_2.tests.tools.m1_engine_v3."):
                    node.module = node.module.rsplit(".", 1)[1]; node.level = 1
                return node
            def visit_Name(self, node):
                if node.id == "verify_lock":
                    return ast.copy_location(ast.Name(id="development", ctx=node.ctx), node)
                return node
        actual = Normalize().visit(deepcopy(new_fn))
        self.assertEqual(ast.dump(old_fn, include_attributes=False), ast.dump(actual, include_attributes=False))

    def test_legacy_driver_and_formal_denial_remain_frozen(self):
        import hashlib
        parent = json.loads((ROOT / "v0_2/tests/tools/m1_campaign_v4/execution_manifest.json").read_bytes())
        bound = {**parent["bundle_entry_raw_hashes"], **parent["remote_source_raw_hashes"]}
        for name in ("stream_worker.py", "package_guard.py", "engine.py", "comparator.py"):
            p = "v0_2/tests/tools/m1_engine_v3/" + name
            self.assertEqual(hashlib.sha256((ROOT / p).read_bytes()).hexdigest(), bound[p])
        self.assertIn("FORMAL_C3_C_NOT_AUTHORIZED_BY_M1_REMOTE_DEVELOPMENT", (ROOT / "v0_2/tests/tools/m1_engine_v3/package_guard.py").read_text())

    def test_formal_driver_does_not_call_development_entry(self):
        tree = ast.parse((ROOT / "v0_2/tests/tools/m1_c3c_v1/stream_worker.py").read_bytes())
        self.assertFalse(any(isinstance(x, ast.Name) and x.id == "development" for x in ast.walk(tree)))
        self.assertTrue(any(isinstance(x, ast.Name) and x.id == "verify_lock" for x in ast.walk(tree)))

    def test_missing_package_denies_before_candidate_import(self):
        with tempfile.TemporaryDirectory(prefix="C3C_SYNTHETIC_ONLY_") as td, patch.object(r, "ROOT", Path(td)):
            self.assertRaises(FileNotFoundError, r.package)
        self.assertNotIn("v0_2.tests.tools.m1_engine_v4.engine", sys.modules)

    def test_bindings_require_authority_before_candidate_import(self):
        with patch.object(r, "admit", side_effect=a.IntegrityError("SYNTHETIC_NOT_APPROVED")):
            with self.assertRaises(a.IntegrityError):
                with bindings.sut_bindings():
                    self.fail("Unsigned binding entered")
        self.assertNotIn("v0_2.tests.tools.m1_engine_v4.engine", sys.modules)

    def test_sem02_exact_synthetic_positive(self):
        actual, expected = sem02_vector()
        self.assertTrue(f.validate_sem02(actual, expected))

    def test_sem02_cannot_grant_strict_p1(self):
        actual, expected = sem02_vector(); actual["cases"][0]["strict_P1_Lane_B"] = "PASS"
        self.assertRaises(a.IntegrityError, f.validate_sem02, actual, expected)

    def test_sem02_cannot_invent_issue_or_alter_input(self):
        actual, expected = sem02_vector(); actual["cases"][0]["domain_events"][0]["PLC_receipts"] = 1
        self.assertRaises(a.IntegrityError, f.validate_sem02, actual, expected)
        actual, expected = sem02_vector(); actual["cases"][0]["domain_events"][0]["input_typed_sha256"] = "f" * 64
        self.assertRaises(a.IntegrityError, f.validate_sem02, actual, expected)

    def test_pf06_synthetic_positive(self):
        actual, expected = pf06_vector()
        self.assertTrue(f.validate_pf06(actual, expected))

    def test_pf06_negative_controls_and_original_scope_not_relabeled(self):
        actual, expected = pf06_vector(); actual["PF06_proposal"]["negative_controls"].pop()
        self.assertRaises(a.IntegrityError, f.validate_pf06, actual, expected)
        actual, expected = pf06_vector(); actual["original_validated_count"] = 16
        self.assertRaises(a.IntegrityError, f.validate_pf06, actual, expected)

    def test_pf06_expected_cuts_and_safety_cannot_drift(self):
        actual, expected = pf06_vector(); actual["PF06_proposal"]["positive_witness"]["Safety"]["severity"] = "FAULT"
        self.assertRaises(a.IntegrityError, f.validate_pf06, actual, expected)
        actual, expected = pf06_vector(); actual["PF06_proposal"]["positive_witness"]["row_index"] = 5
        self.assertRaises(a.IntegrityError, f.validate_pf06, actual, expected)

    def test_stage_schema_accepts_invalid_not_unsigned_pass(self):
        schema = json.loads((ROOT / "v0_2/tests/tools/m1_c3c_v1/artifact_schema.json").read_bytes())
        validator = Draft202012Validator(schema); validator.check_schema(schema)
        sample = {"schema": "m1-c3c-stage-result-v1", "stage_id": "SYNTHETIC_ONLY",
            "status": "INVALID", "behavioral_adjudication": "NOT_MADE", "formal_qualification": True,
            "formal_execution_authorized": False, "github_run_id": "0", "github_run_attempt": "0",
            "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine"}
        validator.validate(sample)
        sample["status"] = "PASS"
        self.assertRaises(ValidationError, validator.validate, sample)

    def test_stage_schema_does_not_make_fail_an_integrity_result(self):
        schema = json.loads((ROOT / "v0_2/tests/tools/m1_c3c_v1/artifact_schema.json").read_bytes())
        sample = {"schema": "m1-c3c-stage-result-v1", "stage_id": "SYNTHETIC_ONLY", "status": "FAIL",
            "behavioral_adjudication": "NOT_MADE", "formal_qualification": True, "formal_execution_authorized": True,
            "github_run_id": "0", "github_run_attempt": "0", "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine",
            "scope": a.SCOPE, "execution_identity": {}, "runtime_identity_before": {}, "runtime_identity_after": {},
            "payload": {}, "sut_constructors": []}
        self.assertRaises(ValidationError, Draft202012Validator(schema).validate, sample)


if __name__ == "__main__":
    unittest.main()
