"""Finite synthetic environment failures only; no models or native launches."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from jsonschema import Draft202012Validator
from .authority import IntegrityError
from .runtime_admission import enforce_environment

HERE = Path(__file__).resolve().parent


class EnvironmentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((HERE / "environment_lock.json").read_bytes())

    def test_exact_new_environment_passes(self):
        old = json.loads((HERE.parent / "m1_c3c_v1/environment_lock.json").read_bytes())
        revised = deepcopy(old)
        revised["image_version"] = "20261012.333.1"
        self.assertEqual(self.expected, revised)
        enforce_environment(deepcopy(self.expected), self.expected)

    def test_image_drift_preserves_rejected_identity(self):
        actual = deepcopy(self.expected)
        actual["image_version"] = "synthetic-unapproved-image"
        with self.assertRaises(IntegrityError) as caught:
            enforce_environment(actual, self.expected)
        error = caught.exception
        self.assertEqual(str(error), "QUALIFICATION_ENVIRONMENT_DRIFT")
        self.assertEqual(error.actual_environment, actual)
        self.assertEqual(error.expected_environment, self.expected)
        self.assertEqual(set(error.environment_differences), {"image_version"})

    def test_other_identity_drift_is_still_rejected(self):
        actual = deepcopy(self.expected)
        actual["python"] = "synthetic-wrong-python"
        with self.assertRaises(IntegrityError) as caught:
            enforce_environment(actual, self.expected)
        self.assertEqual(set(caught.exception.environment_differences), {"python"})

    def test_invalid_envelope_with_diagnostics_is_not_pass(self):
        schema = json.loads((HERE / "artifact_schema.json").read_bytes())
        value = {"schema": "m1-c3c-stage-result-v1", "stage_id": "ENVIRONMENT",
                 "status": "INVALID", "behavioral_adjudication": "NOT_MADE",
                 "formal_qualification": True, "formal_execution_authorized": False,
                 "github_run_id": "1", "github_run_attempt": "1",
                 "sut": "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine",
                 "expected_environment": self.expected,
                 "environment_differences": {"image_version": {"actual": "synthetic-wrong"}}}
        Draft202012Validator(schema).validate(value)
        value["status"] = "PASS"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(value)))
