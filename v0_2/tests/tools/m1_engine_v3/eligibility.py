"""Authenticate actual available source material; no guessed historical issue."""
import json
from pathlib import Path
from .common import ROOT,sha,canonical


def evaluate(startup):
    path=ROOT/'phase5_r5_3r_a_tune01_released_input_trace.json'
    trace=json.loads(path.read_bytes())
    # The known frozen material contains reported command aliases and Safety
    # state, not an independently authenticated issue/decision transaction ledger.
    available={'path':path.relative_to(ROOT).as_posix(),'raw_sha256':sha(path.read_bytes()),
        'canonical_sha256':sha(canonical(trace)),'provenance':trace['provenance'],
        'failed_trial_prefix_equivalence':trace['failed_trial_prefix_equivalence'],
        'available_fields':list(trace['rows'][0]),
        'independently_authenticated_earlier_PLC_receipt_present':False,
        'reason':'RECONSTRUCTED_RELEASED_TRACE_NOT_ORIGINAL_FAILED_TRIAL_CAPTURE; reported ID/time and baseline Safety state are not an issue-bound decision receipt.'}
    cases=[]
    for item in startup['legacy_or_quarantined_cases']:
        events=item['domain_events']
        cases.append({'nodeid':item['nodeid'],'original_test_identity_preserved':True,
            'domain_events':events,'legacy_replay_or_rejection':'DEVELOPMENT_VALIDATED',
            'strict_P1_Lane_B':'INCOMPLETE','strict_P1_Lane_C':'INCOMPLETE',
            'causal_reason':events[0]['causal_status'],
            'earlier_issue_proof':available if events[0]['causal_status']=='UNVERIFIED_HISTORICAL_ISSUE' else None,
            'source_sensor_coerced_valid':False,'fake_PLC_receipts':False,'fake_Safety_decisions':False})
    return {'STARTUP_ORIGINAL_HISTORICAL':startup['historical_guard']['ORIGINAL_STARTUP_HISTORICAL_RESULT'],
        'STARTUP_VERSIONED_COMPATIBILITY':startup['versioned_compatibility'],
        'STARTUP_STRICT_P1_CAUSAL_ELIGIBILITY':'INCOMPLETE' if cases else 'ELIGIBLE',
        'nonqualified_case_count':len(cases),'cases':cases,'source_provenance_investigation':available,
        'full_original_scope_ready':not cases,'formal_qualified':False}
