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
        revised["image_version"] = ["20261004.326.1", "20261012.333.1"]
        self.assertEqual(self.expected, revised)
        for version in revised["image_version"]:
            actual = deepcopy(self.expected)
            actual["image_version"] = version
            enforce_environment(actual, self.expected)

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
        for key in ("python", "system", "version", "machine", "image_os", "dependencies"):
            with self.subTest(key=key):
                actual = deepcopy(self.expected)
                actual["image_version"] = "20261012.333.1"
                actual[key] = "synthetic-wrong-identity"
                with self.assertRaises(IntegrityError) as caught:
                    enforce_environment(actual, self.expected)
                self.assertEqual(set(caught.exception.environment_differences), {key})

    def test_allowlist_cannot_grow_or_use_wildcards(self):
        actual = deepcopy(self.expected)
        actual["image_version"] = "20261004.326.1"
        for images in (["*"], self.expected["image_version"] + ["synthetic-third-image"],
                       ["20261004.326.1", "20261004.326.1"]):
            expected = deepcopy(self.expected)
            expected["image_version"] = images
            with self.assertRaises(IntegrityError) as caught:
                enforce_environment(actual, expected)
            self.assertEqual(str(caught.exception), "IMAGE_ALLOWLIST_NOT_APPROVED")

    def test_per_job_equality_guards_remain_exact(self):
        worker = (HERE / "worker.py").read_text()
        admission = (HERE / "runtime_admission.py").read_text()
        self.assertIn('require(before == after, "C3C_ENVIRONMENT_BEFORE_AFTER_DRIFT")', worker)
        self.assertIn('require(bindings["runtime_identity"] == actual, "PER_JOB_RUNTIME_IDENTITY_DRIFT")', admission)

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
