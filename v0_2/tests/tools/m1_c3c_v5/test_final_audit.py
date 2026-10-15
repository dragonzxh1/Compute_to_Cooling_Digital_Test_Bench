"""Finite static regression checks for the v5 FINAL optimization only."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def function(version, name):
    source = ROOT / ("v0_2/tests/tools/m1_c3c_" + version + "/final_gate.py")
    return next(n for n in ast.parse(source.read_bytes()).body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == name]


class FinalAuditTests(unittest.TestCase):
    def test_all_per_stage_requirements_identical(self):
        old = calls(function("v4", "execution_audit"), "require")
        new = calls(function("v5", "execution_audit"), "require")
        self.assertEqual([ast.dump(n, include_attributes=False) for n in old],
                         [ast.dump(n, include_attributes=False) for n in new])

    def test_package_and_lock_loading_are_once_outside_stage_loops(self):
        f = function("v5", "execution_audit")
        self.assertEqual(len(calls(f, "package")), 1)
        self.assertEqual(len(calls(f, "load_bound")), 1)
        for node in ast.walk(f):
            if isinstance(node, (ast.For, ast.While)):
                self.assertEqual(calls(node, "package"), [])
                self.assertEqual(calls(node, "load_bound"), [])

    def test_final_acceptance_predicates_and_classification_identical(self):
        old, new = function("v4", "finalize"), function("v5", "finalize")
        for name in ("require", "classify", "admit"):
            self.assertEqual([ast.dump(n, include_attributes=False) for n in calls(old, name)],
                             [ast.dump(n, include_attributes=False) for n in calls(new, name)])
        self.assertEqual(len(calls(new, "admit")), 1)

    def test_final_progress_boundaries_and_frozen_policy_bytes(self):
        f = function("v5", "finalize")
        phases = {}
        for call in calls(f, "mark"):
            event, phase = [n.value for n in call.args[:2]]
            phases.setdefault(phase, set()).add(event)
        self.assertEqual(len(phases), 11)
        self.assertTrue(all({"BEGIN", "END"}.issubset(events) for events in phases.values()))
        for name in ("environment_lock.json", "artifact_schema.json", "stop_rules.json"):
            self.assertEqual((ROOT / "v0_2/tests/tools/m1_c3c_v4" / name).read_bytes(),
                             (ROOT / "v0_2/tests/tools/m1_c3c_v5" / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
