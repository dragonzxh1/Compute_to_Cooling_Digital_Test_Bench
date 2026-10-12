"""External stage regrouping only; sealed v2 engine/tests remain byte-identical."""
import unittest

from v0_2.tests.tools.m1_remote_control_v2.admission import ROOT, admit
from v0_2.tests.tools.m1_remote_control_v2.progress import mark

UNIT_GROUPS = {
    'CORE_UNIT_PROJECTION': ('test_projection', 12),
    'CORE_UNIT_STATE_COPY': ('test_state_copy', 3),
    'CORE_UNIT_INFRASTRUCTURE': ('test_infrastructure', 8),
    'CORE_UNIT_CAMPAIGN_PROTOCOL': ('test_campaign_protocol', 4),
}


class BoundaryResult(unittest.TextTestResult):
    def startTest(self, test):
        mark('BEGIN', 'UNIT_TEST', test_id=test.id())
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        mark('END', 'UNIT_TEST', test_id=test.id())


def execute(stage, root):
    admit()
    if stage == 'CORE_IDENTITY':
        from v0_2.tests.tools.m1_engine_v2.schemas import selfcheck
        selfcheck()
        for name in ('engine.py', 'codec.py', 'comparator.py', 'scheduler.py',
                     'state_copy.py', 'pre_oracle.py', 'projection.py', 'pf16.py', 'schemas.py'):
            if (ROOT / 'v0_2/tests/tools/m1_engine_v2' / name).read_bytes() != (
                    ROOT / 'v0_2/tests/tools/c3b_v14_1' / name).read_bytes():
                raise ValueError('M1_CORE_BYTE_DRIFT: ' + name)
        return {'status': 'PASS', 'nine_core_files_identical': True}
    if stage in UNIT_GROUPS:
        module, expected_count = UNIT_GROUPS[stage]
        tests = unittest.defaultTestLoader.loadTestsFromName('v0_2.tests.tools.m1_engine_v2.' + module)
        if tests.countTestCases() != expected_count:
            raise ValueError('ORIGINAL_UNIT_CASE_COUNT_DRIFT')
        result = unittest.TextTestRunner(verbosity=2, resultclass=BoundaryResult).run(tests)
        return {'status': 'PASS' if result.wasSuccessful() and result.testsRun == expected_count else 'FAIL',
                'tests_run': result.testsRun, 'expected_count': expected_count,
                'failures': len(result.failures), 'errors': len(result.errors),
                'original_test_body_unchanged': True}
    if stage == 'CORE_SELF_CHECK':
        raise ValueError('MONOLITHIC_UNIT_STAGE_NOT_ADMITTED')
    from v0_2.tests.tools.m1_remote_control_v2.stage_worker import execute as original
    return original(stage, root)
