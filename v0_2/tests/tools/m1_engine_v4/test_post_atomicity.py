"""Independent failure witnesses for M1-DEF-POST-001.

Run ONLY on a separately authorized isolated development runner. The v3
baseline must fail these assertions; no frozen test body or expectation changes.
The v4 target is not validated merely because this file exists.
"""
import importlib
import os
import unittest
from copy import deepcopy
from unittest.mock import patch

from v0_2.tests.tools.m1_engine_v3.common import Record, canonical, guard, read
from v0_2.tests.tools.m1_engine_v3.materializer import extract
from v0_2.tests.tools.m1_engine_v3.observer import observe
from v0_2.tests.tools.m1_engine_v3.scheduler import MeasurementView, SimulatedPLC


class RejectingStore(dict):
    """Fail before storing a new completed transaction; not hardware I/O."""

    def __setitem__(self, key, value):
        raise OSError("INJECTED_COMPLETED_STORE_FAILURE")


class PostFailureAtomicity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard()
        target = os.environ.get("M1_POST_TEST_TARGET", "v3")
        if target not in {"v3", "v4"}:
            raise ValueError("EXPLICIT_REGISTERED_TEST_TARGET_REQUIRED")
        cls.module = importlib.import_module(
            "v0_2.tests.tools.m1_engine_" + target + ".engine"
        )
        cls.profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
        cls.classifier = read("phase5_r5_2_silent_tracking_fault_registration.json")["classifier"]
        inventory = read("phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json")["input_inventory"]
        # Protected ST-15 supplies a genuine same-value new-issue projection.
        # Historical result contributes INPUTS ONLY, never saved PASS/expected.
        cls.rows = extract(inventory[15])["observations"][:3]

    def issued_transaction(self):
        engine = self.module.SplitEngine(self.profile, self.classifier)
        plc = SimulatedPLC(self.rows)
        for index, row in enumerate(self.rows):
            measurement = MeasurementView.from_row(row)
            pre = engine.pre(measurement, plc.prior, "atomicity:" + str(index))
            safety = engine.safety(pre)
            engine.accept_plc(plc.issue(safety, measurement))
            if index + 1 == len(self.rows):
                return engine, plc, pre, safety
            engine.post()
        raise AssertionError("FINAL_ISSUED_TRANSACTION_MISSING")

    def snapshot(self, engine, plc, pre, safety):
        return {
            "qualifier": canonical(observe(engine.q)),
            "publication": engine.last_publication.raw if engine.last_publication else None,
            "legacy_view": canonical(engine.legacy_response_history),
            "pre": pre.raw,
            "safety": safety.raw,
            "plc_count": len(plc.outputs),
            "plc_receipt": engine._transaction["plc"].data(),
            "commits": list(engine._transaction["commits"]),
            "completed_ids": set(engine._completed),
        }

    def assert_no_false_publication(self, engine, plc, pre, safety, before):
        self.assertEqual(canonical(observe(engine.q)), before["qualifier"])
        self.assertEqual(engine.last_publication.raw, before["publication"])
        self.assertEqual(canonical(engine.legacy_response_history), before["legacy_view"])
        self.assertEqual(pre.raw, before["pre"])
        self.assertEqual(safety.raw, before["safety"])
        self.assertEqual(len(plc.outputs), before["plc_count"])
        self.assertEqual(engine._transaction["plc"].data(), before["plc_receipt"])
        self.assertEqual(engine._transaction["commits"], before["commits"])
        self.assertEqual(set(engine._completed), before["completed_ids"])
        audit = engine.abort("ISSUED")
        self.assertFalse(audit["fresh_publication"])
        self.assertFalse(audit["automatic_resend"])
        self.assertEqual(audit["status"], "INCOMPLETE")
        self.assertEqual(audit["command_issue_status"], "ISSUED")

    def test_projection_rejection_does_not_commit_publication(self):
        engine, plc, pre, safety = self.issued_transaction()
        before = self.snapshot(engine, plc, pre, safety)
        during = []

        def reject(*args, **kwargs):
            during.append(self.snapshot(engine, plc, pre, safety))
            raise ValueError("INJECTED_PROJECTION_PRE_LINK_MISMATCH")

        with patch.object(self.module, "project", side_effect=reject):
            with self.assertRaisesRegex(ValueError, "INJECTED_PROJECTION_PRE_LINK_MISMATCH"):
                engine.post()
        self.assertEqual(len(during), 1)
        # Also reject publication *during* validation, not only a rollback after.
        self.assertEqual(during[0], before)
        self.assert_no_false_publication(engine, plc, pre, safety, before)

    def test_completed_result_serialization_failure_does_not_publish(self):
        engine, plc, pre, safety = self.issued_transaction()
        before = self.snapshot(engine, plc, pre, safety)
        make = Record.make

        def reject_result(data):
            if isinstance(data, dict) and data.get("status") == "COMPLETE" and "authoritative_after" in data:
                raise ValueError("INJECTED_COMPLETED_SERIALIZATION_FAILURE")
            return make(data)

        with patch.object(Record, "make", side_effect=reject_result):
            with self.assertRaisesRegex(ValueError, "INJECTED_COMPLETED_SERIALIZATION_FAILURE"):
                engine.post()
        self.assert_no_false_publication(engine, plc, pre, safety, before)

    def test_completed_store_failure_does_not_publish(self):
        engine, plc, pre, safety = self.issued_transaction()
        # Preserve already-completed IDs; fail only a subsequent insert.
        engine._completed = RejectingStore(engine._completed)
        before = self.snapshot(engine, plc, pre, safety)
        with self.assertRaisesRegex(OSError, "INJECTED_COMPLETED_STORE_FAILURE"):
            engine.post()
        self.assert_no_false_publication(engine, plc, pre, safety, before)

    def test_success_has_exactly_one_publication_and_idempotent_readback(self):
        engine, plc, pre, safety = self.issued_transaction()
        transaction = engine._transaction["id"]
        issued = len(plc.outputs)
        result = engine.post()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["commits"], [
            "PRE_EVIDENCE_COMMIT", "SAFETY_DECISION_COMMIT", "PLC_COMMAND_ISSUE",
            "POST_FINAL_PUBLICATION_COMMIT",
        ])
        self.assertEqual(engine.reconcile_known_issue(transaction), result)
        self.assertEqual(len(plc.outputs), issued)
        self.assertEqual(result["immutable_pre_digest"], pre.digest)
        self.assertEqual(result["immutable_safety_digest"], safety.digest)
        self.assertEqual(deepcopy(result["pre_core"]["response_history"]),
                         result["authoritative_after"]["response_history"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
