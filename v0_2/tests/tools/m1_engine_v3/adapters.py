"""Frozen expectation adapters for split DEVELOPMENT snapshots, not goldens."""
from dataclasses import asdict
from .common import read
from .codec import decode
from .engine import SplitEngine
from .scheduler import SimulatedPLC, MeasurementView
from .codec import encode
from .common import canonical, sha
import math
from v0_2.tests.tools.m1_remote_control_v3.progress import mark

STARTUP_DOMAIN_EVENTS = []


def replay(rows, profile, classifier, *, case='generic'):
    engine, plc = SplitEngine(profile,classifier),SimulatedPLC(rows)
    frames=[]
    for index,row in enumerate(rows):
        mark('BEGIN','SPLIT_TICK',tick=index,time_ns=row['time_ns'])
        provenance='POST_COMMAND_EFFECT' if case=='ST-08' and row['time_ns']==600000000 else 'CERTIFIED_INTERVAL_END'
        m=MeasurementView.from_row(row,provenance)
        mark('BEGIN','PRE',tick=index,time_ns=row['time_ns'])
        pre=engine.pre(m,plc.prior,'adapter:'+str(index))
        mark('END','PRE',tick=index,time_ns=row['time_ns'])
        mark('BEGIN','SAFETY',tick=index,time_ns=row['time_ns'])
        safety=engine.safety(pre)
        mark('END','SAFETY',tick=index,time_ns=row['time_ns'])
        mark('BEGIN','PLC_ISSUE_ACCEPT',tick=index,time_ns=row['time_ns'])
        engine.accept_plc(plc.issue(safety,m))
        mark('END','PLC_ISSUE_ACCEPT',tick=index,time_ns=row['time_ns'])
        mark('BEGIN','POST',tick=index,time_ns=row['time_ns'])
        frames.append(engine.post())
        mark('END','POST',tick=index,time_ns=row['time_ns'])
        mark('END','SPLIT_TICK',tick=index,time_ns=row['time_ns'])
    snap=engine.q.snapshot()
    snap['response_history']=decode(frames[-1]['after']['response_history'])
    return {'snapshot':snap,'frames':frames}


def individual(descriptor, snapshot, *, fresh_u_checks=None):
    stage=descriptor['stage_id']
    if stage=='U-fresh':
        from v0_2.tests.data.tracking_qualification.run_r45c_g_frozen_development import u_checks
        return u_checks(snapshot)
    if stage.startswith('ST-'):
        from v0_2.tests.control.test_phase5_r5_2_1r4_5c_lifecycle import checks
        if stage=='ST-12':
            if not fresh_u_checks:raise ValueError('FRESH_STATE_U_REQUIRED')
            from v0_2.tests.data.tracking_qualification.run_r45c_g_frozen_development import v2_checks
            return v2_checks(snapshot,fresh_u_checks)
        return checks(stage,snapshot)
    if stage.startswith('ITQ-'):
        from v0_2.tests.data.tracking_qualification.itq_execution_spec_v101 import compare_snapshot
        number=int(stage.split('-')[1])-1
        entry=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['ITQ_variants'][number]
        fixture,expected=read(entry['input_path']),read(entry['expectation_path'])
        errata=read('phase5_r5_2_1r4_4a1_itq_execution_spec_errata.json')
        result=compare_snapshot(snapshot,expected,errata['all_case_interpretations'][entry['case_id']],fixture)
        if result['status']=='INVALID_EXECUTION':raise ValueError('FROZEN_COMPARATOR_INVALID: '+str(result))
        return {'frozen_ITQ':result['status']=='PASS'}
    if stage=='P15-history':
        starts=[x for x in snapshot['epoch_events'] if x['event']=='START']
        anchors=snapshot['resolved_pair_events'];progress=[r for r in snapshot['records'] if r['qualified_progress']]
        return {'exact_epoch_starts':[x['time_ns'] for x in starts]==[600000000,3400000000],
            'exact_directions':[x['expected_direction'] for x in starts]==[1,1],
            'exact_anchors':[x['new']['resolved_command_anchor'] for x in anchors]==[.35,.51,.67],
            'initial_anchor_direct':bool(anchors) and anchors[0]['reason']=='DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE',
            'stage_progress':len(starts)==2 and len(anchors)==3 and all(any(starts[i]['time_ns']<r['time_ns']<=anchors[i+1]['time_ns'] for r in progress) for i in range(2)),
            'resolved_after_trigger':len(starts)==2 and len(anchors)==3 and all(anchors[i+1]['time_ns']>starts[i]['time_ns'] for i in range(2)),
            'anchor_epoch_provenance':[x['new']['source_epoch_id'] for x in anchors[1:]]==[x['epoch_id'] for x in starts],
            'final_steady':snapshot['state']=='STEADY_TRACKING',
            'no_fault':not snapshot['confirmed_latched'] and all(r['state']!='TRACKING_FAULT_CONFIRMED' for r in snapshot['records'])}
    if stage not in ('C-history','S-history'):raise ValueError('UNREGISTERED_STAGE_ADAPTER')
    return {'deferred_suite_acceptance':True}


def suite_checks(kind, snapshots):
    from v0_2.examples.phase5_r5_2_1r4_3_history_validation import c_acceptance,s_acceptance
    checks=(c_acceptance if kind=='C' else s_acceptance)(snapshots)
    if len(checks)!=(11 if kind=='C' else 17):raise ValueError('HISTORY_ACCEPTANCE_INVENTORY')
    return checks


class StartupSplitAdapter:
    """Inject split lifecycle only; original 50 Startup bodies stay unchanged."""
    def __init__(self,profile,classifier):
        self.engine=SplitEngine(profile,classifier)
        self._profile=profile
        self._classifier=classifier
        self.prior=None
        self.index=0
        self.last_frame=None
        self.raw_rows=[]
        self.legacy=None
        self.legacy_domain=None

    def update(self,item,**kwargs):
        from .scheduler import PriorCommand
        row=asdict(item)
        self.raw_rows.append(row)
        historical=(self.prior is not None
            and (item.plc_command,item.command_timestamp_ns)!=(self.prior.value,self.prior.issue_ns)
            and item.command_timestamp_ns!=item.time_ns)
        malformed=(item.measured_speed is not None and not math.isfinite(item.measured_speed)) or (
            item.sample_ns is not None and item.release_ns is not None and item.sample_ns>item.release_ns)
        if historical or malformed or self.legacy is not None:
            # Quarantined legacy compatibility lane: no PRE/Safety/PLC records
            # or command authority are manufactured. Raw timestamps stay exact.
            if self.legacy is None:
                self.legacy_domain=('LEGACY_ASYNCHRONOUS_OBSERVATION_REPLAY','UNVERIFIED_HISTORICAL_ISSUE') if historical else ('LEGACY_INVALID_PACKET_REJECTION','INCOMPLETE_QUARANTINED_INPUT')
                from v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine import WatchLifecycleTrackingQualifier
                self.legacy=WatchLifecycleTrackingQualifier(self._profile,self._classifier)
                from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
                for previous in self.raw_rows[:-1]:self.legacy.update(ReleasedObservation(**previous))
            self.legacy.update(item,**kwargs)
            STARTUP_DOMAIN_EVENTS.append({'mode':self.legacy_domain[0],
                'causal_status':self.legacy_domain[1],
                'time_ns':item.time_ns,'reported_issue_ns':item.command_timestamp_ns,
                'input_typed_sha256':sha(canonical(encode(row))),
                'PLC_receipts':0,'Safety_commits':0,'Lane_B':'INCOMPLETE','Lane_C':'INCOMPLETE'})
            return self.legacy.records[-1]
        if self.prior is None:
            self.prior=PriorCommand(item.plc_command,item.command_timestamp_ns,'released-command:'+str(item.command_timestamp_ns))
        m=MeasurementView.from_row(row,kwargs.get('provenance','CERTIFIED_INTERVAL_END'))
        pre=self.engine.pre(m,self.prior,'startup:'+str(self.index))
        safety=self.engine.safety(pre)
        plc=SimulatedPLC([row]);plc.prior=self.prior
        output=plc.issue(safety,m);self.engine.accept_plc(output)
        self.last_frame=self.engine.post();self.prior=plc.prior;self.index+=1
        return self.engine.q.records[-1]

    def snapshot(self):
        if self.legacy is not None:return self.legacy.snapshot()
        result=self.engine.q.snapshot()
        result['response_history']=decode(self.last_frame['after']['response_history']) if self.last_frame else []
        return result

    def __getattr__(self,name):return getattr(self.legacy if self.legacy is not None else self.engine.q,name)


