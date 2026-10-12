import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from jsonschema.exceptions import ValidationError
from .common import ROOT,read,canonical,sha
from .schemas import validate,selfcheck
from .evidence import write,verify
from .adapters import StartupSplitAdapter,STARTUP_DOMAIN_EVENTS,replay
from .observer import reference_rows
from .materializer import extract
from .codec import encode


class InfrastructureTests(unittest.TestCase):
    def test_schema_definitions_and_full_phase_frame(self):
        self.assertTrue(selfcheck())
        spec=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')
        rows=extract(spec['input_inventory'][0])['observations'][:3]
        p=read('phase5_r5_2_2_fixture_tracking_profile.json');c=read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
        s=replay(rows,p,c);r=reference_rows(rows,p,c)
        for f in s['frames']:validate('frame',f)
        for f in r['frames']:validate('reference',f)

    def test_missing_core_field_and_bad_typed_values_rejected(self):
        with self.assertRaises(ValidationError):validate('core',{})
        for value in ({'type':'int','value':True},{'type':'float64','bits':'wrong'},{'type':'none','value':None},{'type':'bad'}):
            with self.assertRaises(ValidationError):validate('typed',value)
        for value in (None,True,1,'x',.4,float('nan'),float('inf'),[1],{'x':2}):validate('typed',encode(value))

    def test_fast_typed_validator_matches_standard_schema(self):
        from jsonschema import Draft202012Validator
        from .schemas import schema
        samples=[encode(x) for x in (1,True,0.0,-0.0,[],{'a':[1,None]},float('nan'))]+[{'type':'int','value':True},{'type':'none','bits':'x'}]
        for value in samples:
            expected=Draft202012Validator(schema('typed')).is_valid(value)
            try:validate('typed',value);actual=True
            except ValidationError:actual=False
            self.assertEqual(actual,expected)

    def test_artifact_exclusive_write_and_corruption_detected(self):
        root=ROOT/'artifacts/m1-autonomous-development'/('synthetic-'+uuid.uuid4().hex)
        r=write(root/'data.json',{'value':1});self.assertEqual(verify(r),{'value':1})
        with self.assertRaises(FileExistsError):write(root/'data.json',{'value':2})
        with self.assertRaises(ValueError):verify({**r,'raw_sha256':'0'*64})
        with self.assertRaises(ValueError):write(ROOT/'not-an-artifact.json',{'a':1})

    def test_formal_entry_denied_before_candidate_import(self):
        code="import sys,runpy; sys.argv=['runner'];\ntry:runpy.run_module('v0_2.tests.tools.m1_engine_v3.runner',run_name='__main__')\nexcept SystemExit as e:print(e.code,'v0_2.tests.tools.m1_engine_v3.engine' in sys.modules)"
        p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.stdout.strip(),'2 False')

    def test_formal_unfrozen_authorization_rejected(self):
        from .package_guard import formal_authorization
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/m1-autonomous-development') as folder:
            # Synthetic unapproved inputs only; no positive formal authorization.
            m=Path(folder)/'manifest.json';a=Path(folder)/'authorization.json'
            with m.open('x') as f:json.dump({'status':'CANDIDATE_FOR_USER_FREEZE_REVIEW'},f)
            with a.open('x') as f:json.dump({'scope':'C3-C_FULL_M1_FROZEN_PACKAGE','user_execution_authorization':'NO'},f)
            with self.assertRaises(ValueError):formal_authorization(m,a,sha(m.read_bytes()))

    def test_asynchronous_replay_never_mints_receipts(self):
        from v0_2.tests.control.test_phase5_r5_2_1r4_1_deferred_demand import _cases
        from v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine import WatchLifecycleTrackingQualifier
        p=read('phase5_r5_2_2_fixture_tracking_profile.json');c=read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
        adapter=StartupSplitAdapter(p,c);reference=WatchLifecycleTrackingQualifier(p,c)
        STARTUP_DOMAIN_EVENTS.clear()
        for item in _cases()['R41-8'][:3]:adapter.update(item);reference.update(item)
        self.assertEqual(adapter.snapshot(),reference.snapshot())
        self.assertEqual(STARTUP_DOMAIN_EVENTS[0]['reported_issue_ns'],200000000)
        self.assertEqual(STARTUP_DOMAIN_EVENTS[0]['time_ns'],400000000)
        self.assertTrue(all(e['PLC_receipts']==e['Safety_commits']==0 and e['Lane_B']==e['Lane_C']=='INCOMPLETE' for e in STARTUP_DOMAIN_EVENTS))
        self.assertEqual(STARTUP_DOMAIN_EVENTS[0]['causal_status'],'UNVERIFIED_HISTORICAL_ISSUE')

    def test_malformed_and_nonfinite_samples_not_validated_as_measurements(self):
        from v0_2.examples.phase5_r5_2_1r_validation import synthetic
        from dataclasses import replace
        p=read('phase5_r5_2_2_fixture_tracking_profile.json');c=read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
        first=synthetic(p,{0:.7},duration_ns=0,initial_speed=.5)[0]
        for change in ({'sample_ns':200000000,'release_ns':0},{'sample_ns':0,'release_ns':-1},{'measured_speed':float('nan')},{'measured_speed':float('inf')}):
            a=StartupSplitAdapter(p,c);STARTUP_DOMAIN_EVENTS.clear();a.update(replace(first,**change));s=a.snapshot()
            self.assertEqual(s['state'],'INSUFFICIENT_MEASUREMENT');self.assertIsNone(s['resolved_pair']);self.assertFalse(s['records'][0]['qualified_progress'])
            self.assertEqual(STARTUP_DOMAIN_EVENTS[-1]['Lane_B'],'INCOMPLETE');self.assertEqual(STARTUP_DOMAIN_EVENTS[-1]['PLC_receipts'],0)


if __name__=='__main__':unittest.main()
