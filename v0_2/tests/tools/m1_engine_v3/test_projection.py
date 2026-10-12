"""Independent development attacks; never formal C3-C acceptance."""
from copy import deepcopy
import unittest
from .common import read, canonical, sha, guard
from .codec import decode, encode
from .engine import SplitEngine
from .scheduler import SimulatedPLC, MeasurementView, CapabilityError
from .observer import reference_rows, observe
from .materializer import extract
from .selfcheck import pipeline
from .comparator import compare, compare_traces, incomplete_assertions
from .oracle import OracleTrace


class ProjectionAttacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard()
        cls.profile=read('phase5_r5_2_2_fixture_tracking_profile.json')
        cls.classifier=read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
        inv=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
        cls.rows=extract(inv[15])['observations'][:3]
        cls.ref=reference_rows(cls.rows,cls.profile,cls.classifier,replay_kind='ST-15')['frames']
        cls.frames=pipeline(cls.rows,cls.profile,cls.classifier,'attacks',replay_kind='ST-15')
        cls.oracle=OracleTrace('source-15',extract(inv[15])['observations'])

    def at_pre(self, rows, other=()):
        e,p=SplitEngine(self.profile,self.classifier),SimulatedPLC(rows)
        for i,row in enumerate(rows):
            m=MeasurementView.from_row(row)
            pre=e.pre(m,p.prior,'branch:'+str(i))
            if i==len(rows)-1:
                return e,p,m,pre
            s=e.safety(pre,other);e.accept_plc(p.issue(s,m));e.post()

    def compare_last(self, candidate, reference=None, oracle=None):
        ref=reference or self.ref
        return compare(ref[2],candidate,trusted_context=(oracle or self.oracle).context(2,ref))

    def test_01_same_pre_new_issue_projection(self):
        f=self.frames[-1]
        self.assertEqual(self.compare_last(f)['status'],'PASS')
        self.assertEqual(decode(f['pre_core']['response_history'])[-1]['command_timestamp_ns'],self.rows[-2]['command_timestamp_ns'])
        self.assertEqual(decode(f['after']['response_history'])[-1]['command_timestamp_ns'],self.rows[-1]['command_timestamp_ns'])
        self.assertEqual(f['pre_core']['response_history'],f['authoritative_after']['response_history'])
        self.assertEqual(f['PRE']['core_digest'],sha(canonical(f['pre_core'])))

    def test_02_alternate_verified_receipt_same_pre(self):
        held=deepcopy(self.rows);held[-1]['command_timestamp_ns']=held[-2]['command_timestamp_ns']
        a=self.at_pre(self.rows);b=self.at_pre(held)
        self.assertEqual(a[-1].raw,b[-1].raw)
        self.assertEqual(observe(a[0].q),observe(b[0].q))
        outputs=[]
        for e,p,m,pre in (a,b):
            e.accept_plc(p.issue(e.safety(pre),m));outputs.append(e.post())
        self.assertEqual(outputs[0]['pre_core'],outputs[1]['pre_core'])
        self.assertNotEqual(outputs[0]['after']['response_history'],outputs[1]['after']['response_history'])
        self.assertFalse(outputs[1]['legacy_projection_bindings'])

    def test_03_held_command_no_fabrication(self):
        rows=deepcopy(self.rows);rows[-1]['command_timestamp_ns']=rows[-2]['command_timestamp_ns']
        f=pipeline(rows,self.profile,self.classifier,'held')[-1]
        self.assertFalse(f['POST']['enrolled_new_command'])
        self.assertFalse(f['legacy_projection_bindings'])
        self.assertEqual(f['authoritative_after']['response_history'],f['after']['response_history'])

    def incomplete(self,status,issued=False):
        e,p,m,pre=self.at_pre(self.rows)
        s=e.safety(pre)
        if issued:e.accept_plc(p.issue(s,m))
        audit=e.abort(status)
        self.assertTrue(incomplete_assertions(audit)['passed'])
        self.assertFalse(audit['fresh_publication'])
        self.assertFalse(audit['automatic_resend'])
        return e,p,m,pre,audit

    def test_04_unknown_issue_no_completed_transaction(self):
        e,*_=self.incomplete('UNKNOWN')
        with self.assertRaises(CapabilityError):e.post()

    def test_05_not_issued_no_projection(self):
        e,*_=self.incomplete('NOT_ISSUED')
        with self.assertRaises(CapabilityError):e.post()

    def test_06_post_failure_no_second_issue(self):
        e,p,m,pre=self.at_pre(self.rows)
        before=pre.raw;e.accept_plc(p.issue(e.safety(pre),m))
        issued=len(p.outputs);last=e.last_publication
        self.assertIsNone(e.post(fail_before_publication=True))
        audit=e.abort('ISSUED')
        self.assertEqual(len(p.outputs),issued)
        self.assertIs(e.last_publication,last)
        self.assertEqual(pre.raw,before)
        self.assertTrue(incomplete_assertions(audit)['passed'])

    def test_07_wrong_projection_links_rejected(self):
        for key in ('source_id','watch_id','old_command_id','transaction_id','plc_digest'):
            f=deepcopy(self.frames[-1]);f['legacy_projection_bindings'][0][key]='wrong'
            self.assertNotEqual(self.compare_last(f)['status'],'PASS',key)

    def test_08_rewritten_pre_core_rejected(self):
        f=deepcopy(self.frames[-1]);f['pre_core']['response_history']=deepcopy(f['after']['response_history'])
        self.assertNotEqual(self.compare_last(f)['status'],'PASS')

    def test_09_independent_safety_reason_erasure_rejected(self):
        inv=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
        rows=extract(inv[0])['observations'];ref=reference_rows(rows,self.profile,self.classifier)['frames']
        correct=pipeline(rows,self.profile,self.classifier,'pressure',other=({'code':'PRESSURE_FAULT','severity':'FAULT'},))
        oracle=OracleTrace('U-pressure',rows)
        self.assertEqual(compare(ref[6],correct[6],trusted_context=oracle.context(6,ref))['status'],'PASS')
        bad=deepcopy(correct[6]);bad['SAFETY']['reason_codes'].remove('PRESSURE_FAULT')
        self.assertNotEqual(compare(ref[6],bad,trusted_context=oracle.context(6,ref))['status'],'PASS')

    def test_10_changed_value_existing_semantics(self):
        inv=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
        rows=extract(inv[0])['observations'];ref=reference_rows(rows,self.profile,self.classifier)['frames']
        frames=pipeline(rows,self.profile,self.classifier,'StateU')
        self.assertEqual(compare_traces(ref,frames,oracle=OracleTrace('source-0',rows))['status'],'PASS')
        f=frames[6]
        self.assertEqual(f['PRE']['state'],'TRACKING_FAULT_SUSPECTED')
        self.assertEqual(f['POST']['state'],'STEADY_TRACKING')
        self.assertEqual(decode(f['after']['carried_suspicion_evidence']),1)
        self.assertFalse(f['legacy_projection_bindings'])

    def test_11_duplicate_sample_credit_rejected(self):
        f=deepcopy(self.frames[-1]);h=decode(f['authoritative_after']['response_history']);h.append(deepcopy(h[-1]))
        f['authoritative_after']['response_history']=encode(h)
        self.assertNotEqual(self.compare_last(f)['status'],'PASS')

    def test_12_exact_reference_history_remains_gate(self):
        f=deepcopy(self.frames[-1]);h=decode(f['after']['response_history']);h[-1]['command_timestamp_ns']+=1
        f['after']['response_history']=encode(h)
        r=self.compare_last(f)
        self.assertTrue(any(x['rule']=='CMP-A06' for x in r['findings']))


if __name__=='__main__':unittest.main()

