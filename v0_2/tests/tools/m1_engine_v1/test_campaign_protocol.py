"""Default-deny, pre-split seal and bounded-resource protocol checks."""
import unittest
import uuid
from pathlib import Path
from .common import ROOT,read,canonical,sha
from .evidence import write
from .runner import source_lock
from .worker import execute


class CampaignProtocolTests(unittest.TestCase):
    def test_split_requires_presealed_inventory(self):
        root=ROOT/'artifacts/m1-autonomous-development'/('protocol-'+uuid.uuid4().hex)
        lock=write(root/'source_lock.json',source_lock())
        directory=root/'000'
        reference=execute('REFERENCE',0,directory,ROOT/lock['path'])
        with self.assertRaises(FileNotFoundError):
            execute('SPLIT',0,directory,ROOT/lock['path'],expected_reference_sha=reference['receipt']['raw_sha256'])
        selection=execute('SELECT',0,directory,ROOT/lock['path'],expected_reference_sha=reference['receipt']['raw_sha256'])
        self.assertEqual(selection['selected_count'],21)
        with self.assertRaises(ValueError):
            execute('SPLIT',0,directory,ROOT/lock['path'],expected_reference_sha=reference['receipt']['raw_sha256'],expected_stage_sha='0'*64)

    def test_original_PF06_precondition_unchanged(self):
        from .pf16 import predicates
        from v0_2.tests.tools.c3b_v9.pf16 import predicates as baseline
        self.assertEqual(predicates.__code__.co_code,baseline.__code__.co_code)
        self.assertEqual(predicates.__code__.co_consts,baseline.__code__.co_consts)

    def test_resource_revision_does_not_change_phase_math(self):
        from .engine import SplitEngine
        from v0_2.tests.tools.c3b_v10.engine import SplitEngine as previous
        for name in ('pre','safety','accept_plc','post'):
            current=getattr(SplitEngine,name).__code__;old=getattr(previous,name).__code__
            self.assertEqual(current.co_code,old.co_code,name)
            self.assertEqual(current.co_consts,old.co_consts,name)

    def test_oracle_pin_is_raw_not_canonical(self):
        from .oracle import PATH,REGISTRATION_SHA256,registration
        self.assertEqual(sha((ROOT/PATH).read_bytes()),REGISTRATION_SHA256)
        self.assertEqual(registration(),read(PATH))


if __name__=='__main__':unittest.main()
