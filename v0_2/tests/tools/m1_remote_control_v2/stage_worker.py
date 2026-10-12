"""Long-case development only; selected prefixes remain original frozen policy."""
import json
import os
import unittest
from pathlib import Path

from .admission import ROOT, admit
from .progress import mark


def case_directory(root, index):
    return Path(root) / ('%03d' % index)


def execute(stage, root):
    admit()
    from v0_2.tests.tools.m1_engine_v2.common import read, guard, sha, canonical
    from v0_2.tests.tools.m1_engine_v2.runner import source_lock
    from v0_2.tests.tools.m1_engine_v2.evidence import write, receipt
    from v0_2.tests.tools.m1_engine_v2.materializer import extract, materialize_all
    if stage == 'INPUT_INTEGRITY':
        guard()
        mark('BEGIN', 'ALL_FROZEN_INPUTS')
        inventory = materialize_all(Path(root) / 'inputs')
        if inventory['count'] != 101 or inventory['ITQ_variants'] != 51 or inventory['ITQ_cases'] != 23:
            raise ValueError('M1_FULL_INPUT_INVENTORY_MISMATCH')
        lock = source_lock()
        saved = write(Path(root) / 'source_lock.json', lock)
        mark('END', 'ALL_FROZEN_INPUTS', descriptor_count=101)
        return {'status': 'PASS', 'input_inventory': inventory, 'source_lock_receipt': saved,
                'historical_scores_borrowed': False}
    if stage == 'CORE_SELF_CHECK':
        from v0_2.tests.tools.m1_engine_v2.schemas import selfcheck
        selfcheck()
        # Exact source-byte preservation, independent of namespace/host.
        fields = ('engine.py','codec.py','comparator.py','scheduler.py','state_copy.py',
                  'pre_oracle.py','projection.py','pf16.py','schemas.py')
        for name in fields:
            if (ROOT / 'v0_2/tests/tools/m1_engine_v2' / name).read_bytes() != (
                ROOT / 'v0_2/tests/tools/c3b_v14_1' / name
            ).read_bytes():
                raise ValueError('M1_CORE_BYTE_DRIFT: ' + name)
        tests = unittest.defaultTestLoader.loadTestsFromNames([
            'v0_2.tests.tools.m1_engine_v2.test_projection',
            'v0_2.tests.tools.m1_engine_v2.test_state_copy',
            'v0_2.tests.tools.m1_engine_v2.test_infrastructure',
            'v0_2.tests.tools.m1_engine_v2.test_campaign_protocol',
        ])
        result = unittest.TextTestRunner(verbosity=2).run(tests)
        return {'status': 'PASS' if result.wasSuccessful() and result.testsRun > 0 else 'FAIL',
                'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                'nine_core_files_identical': True}
    if stage == 'CMP_NEGATIVE':
        from v0_2.tests.tools.m1_engine_v2.selfcheck import main
        # Selfcheck performs immutable-byte guard and preregistered negative mutations.
        import sys
        original = sys.argv
        sys.argv = ['selfcheck', '--output-root', str(Path(root) / 'CMP' / 'artifacts')]
        try:
            main()
        finally:
            sys.argv = original
        # main emits a summary; authoritative evidence checked below.
        candidates = list((Path(root) / 'CMP').rglob('development-evidence.json'))
        if len(candidates) != 1:
            raise ValueError('CMP_NEGATIVE_EVIDENCE_INCOMPLETE')
        data = json.loads(candidates[0].read_bytes())
        if not data['checks'] or not all(check['passed'] for check in data['checks']):
            raise ValueError('CMP_NEGATIVE_SELF_CHECK_FAIL')
        return {'status': 'PASS', 'check_count': len(data['checks']),
                'evidence_raw_sha256': sha(candidates[0].read_bytes())}
    pieces = stage.split('-')
    if len(pieces) < 3 or pieces[0] != 'CASE':
        raise ValueError('UNKNOWN_M1_PILOT_STAGE')
    index, kind = int(pieces[1]), pieces[2]
    if index not in (65, 66, 92):
        raise ValueError('LONG_CASE_NOT_PREREGISTERED')
    reference_root = os.environ['C2C_M1_REFERENCE_ROOT']
    folder = case_directory(reference_root, index)
    from v0_2.tests.tools.m1_engine_v2.worker import execute as run_stage
    lock_path = Path(root) / 'source_lock.json'
    reference_sha = receipt(folder / 'reference.json')['raw_sha256'] if kind != 'REFERENCE' else None
    stage_sha = None
    prefix_length = None
    if kind == 'SPLIT':
        stage_sha = receipt(folder / 'prefix_inventory.json')['raw_sha256']
    if kind == 'PREFIX_ONE':
        if len(pieces) != 4:
            raise ValueError('PREFIX_LENGTH_REQUIRED')
        prefix_length = int(pieces[3])
        stage_sha = receipt(folder / 'stage_result.json')['raw_sha256']
    mark('BEGIN', 'M1_CASE_STAGE', descriptor_index=index, kind=kind, prefix_length=prefix_length)
    result = run_stage(kind, index, folder, lock_path, expected_reference_sha=reference_sha,
                       expected_stage_sha=stage_sha, prefix_length=prefix_length)
    mark('END', 'M1_CASE_STAGE', descriptor_index=index, kind=kind, prefix_length=prefix_length)
    return result
