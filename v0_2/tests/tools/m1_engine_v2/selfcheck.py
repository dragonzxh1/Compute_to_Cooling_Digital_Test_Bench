"""Bounded DEVELOPMENT_ONLY checks; no full ITQ qualification entry point."""
import argparse
from copy import deepcopy
import datetime
import json
from pathlib import Path
import traceback
import uuid

from .common import ROOT, MODE, canonical, sha, read, persist, guard, Record
from .codec import encode, decode
from .observer import observe, reference_rows, FIELDS
from .engine import SplitEngine
from .scheduler import MeasurementView, SimulatedPLC, CapabilityError
from .materializer import extract, materialize_all
from .comparator import compare, compare_traces, incomplete_assertions, repeat_fingerprint
from .oracle import OracleTrace


def pipeline(rows, profile, classifier, case, *, other=(), replay_kind='generic'):
    engine, plc = SplitEngine(profile, classifier), SimulatedPLC(rows)
    frames = []
    for index, row in enumerate(rows):
        provenance = 'POST_COMMAND_EFFECT' if replay_kind == 'ST-08' and row['time_ns'] == 600000000 else 'CERTIFIED_INTERVAL_END'
        m = MeasurementView.from_row(row, provenance)
        pre = engine.pre(m, plc.prior, case + ':' + str(index))
        safety = engine.safety(pre, other)
        output = plc.issue(safety, m)
        engine.accept_plc(output)
        frames.append(engine.post())
    return frames


def _mutation_checks(reference, correct, pressure_reference, pressure_correct, confirmed_reference, confirmed_correct, output, context, pressure_context, confirmed_context):
    results = []

    def trial(name, mutate, expected_rule, *, ref=reference, data=correct, artifacts=()):
        candidate = deepcopy(data)
        mutate(candidate)
        trusted = pressure_context if data is pressure_correct else confirmed_context if data is confirmed_correct else context
        result = compare(ref, candidate, artifacts=artifacts, trusted_context=trusted)
        ok = result['status'] == 'BEHAVIORAL_DIFFERENCE' and any(x['rule'] == expected_rule for x in result['findings'])
        if expected_rule == 'INTEGRITY':
            ok = result['status'] == 'EVIDENCE_INTEGRITY_INVALID'
        if expected_rule == 'CMP-A08':
            # Missing required evidence is rejected before behavioral grading.
            # Still require the exact registered presence rule to catch it.
            ok = result['status'] in ('BEHAVIORAL_DIFFERENCE','EVIDENCE_INTEGRITY_INVALID') and any(x['rule']=='CMP-A08' for x in result['findings'])
        results.append({'name': name, 'expected_rule': expected_rule, 'matched': ok, 'result': result})

    def set_attr(name, value):
        return lambda x: x['after'].__setitem__(name, encode(value))

    trial('changed-state', set_attr('state', 'HANDOFF_PENDING'), 'CMP-A01')
    trial('missing-field', lambda x: x['after'].pop('last_time_ns'), 'CMP-A08')

    def event_time(x):
        events = decode(x['after']['transitions'])
        events[-1]['time_ns'] += 1
        x['after']['transitions'] = encode(events)
    trial('event-time', event_time, 'CMP-A02')
    trial('event-count', lambda x: x['after']['transitions']['items'].append(deepcopy(x['after']['transitions']['items'][-1])), 'CMP-A02')
    trial('watch-lineage', set_attr('oldest_unresolved_demand_ns', 200000000), 'CMP-A03')
    trial('evidence-count', set_attr('carried_suspicion_evidence', 2), 'CMP-A04')
    trial('pair-identity', lambda x: x['after']['progress_pair']['fields'].__setitem__('progress_pair_id', encode('wrong-pair')), 'CMP-A05')
    trial('startup-suspension-lost', set_attr('startup_demand_suspended', False), 'CMP-A07')
    trial('duplicate-source-credit', lambda x: x['after']['response_history']['items'].append(deepcopy(x['after']['response_history']['items'][-1])), 'CMP-A06')
    trial('stale-PRE-reason', lambda x: x['SAFETY'].__setitem__('pre_record_id', 'previous-cycle:PRE'), 'CMP-B03')
    trial('wrong-PRE-mapping', lambda x: x['PRE']['contribution'].__setitem__('severity', 'NORMAL'), 'CMP-B02')
    trial('wrong-PRE-source', lambda x: x['PRE']['measurement'].__setitem__('measured_speed', 0.6), 'CMP-B01')
    trial('wrong-old-obligation', lambda x: x['PRE'].__setitem__('old_epoch_id', 'wrong-epoch'), 'CMP-B01')
    trial('committed-record-rewrite', lambda x: x['PRE'].__setitem__('evidence_commit_id', 'rewritten'), 'CMP-B05')
    trial('dropped-independent-reason', lambda x: x['SAFETY']['reason_codes'].remove('PRESSURE_FAULT'), 'CMP-B04',
          ref=pressure_reference, data=pressure_correct)
    trial('PRE-future-command-access', lambda x: x['access_log'].append({'actor': 'PRE', 'kind': 'DENIED_FUTURE_COMMAND_ACCESS', 'name': 'future_command'}), 'CMP-C02')
    trial('unauthorized-PLC-producer', lambda x: x['PLC'].__setitem__('producer', 'CONTROLLER'), 'CMP-C01')
    trial('duplicated-POST-publication', lambda x: x.__setitem__('publication_count', 2), 'CMP-C03')
    trial('wrong-PLC-output', lambda x: x['PLC'].__setitem__('command', 0.8), 'CMP-C03')
    trial('confirmed-latch-loss', set_attr('confirmed_latched', False), 'CMP-A04',
          ref=confirmed_reference, data=confirmed_correct)
    trial('POST-context-evidence', set_attr('credited_motion', 0.01), 'CMP-C04')
    trial('UNKNOWN-coerced-ISSUED', lambda x: x.__setitem__('unknown_coerced_to_issued', True), 'CMP-C05')
    trial('signed-zero', set_attr('credited_motion', -0.0), 'CMP-A04')
    trial('bool-as-int', set_attr('carried_suspicion_evidence', True), 'CMP-A04')
    receipt = persist(Path(output) / 'synthetic-persisted.json', {'payload': 'known'})
    trial('corrupted-persisted-evidence', lambda x: None, 'INTEGRITY',
          artifacts=[{**receipt, 'raw_sha256': '0' * 64}])
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', default='artifacts/c3b-development/v011')
    args = parser.parse_args()
    guard()
    run_id = 'c3b-v011-' + uuid.uuid4().hex
    output = ROOT / args.output_root / run_id
    sources = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))}
    persist(output / 'source-before.json', {'version': 'v011', 'sources': sources, 'mode': MODE})
    evidence = {'mode': MODE, 'version': 'v011', 'execution_id': run_id,
        'started_at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sources_before': sources, 'checks': [], 'formal_qualification_executed': False,
        'PF_qualified_promotions': [], 'production_implementation': False}

    def note(name, passed, detail):
        evidence['checks'].append({'name': name, 'passed': bool(passed), 'detail': detail})

    try:
        materialized = materialize_all(output / 'inputs')
        evidence['materialized_inputs'] = materialized
        note('input-first-materializer', materialized['count'] == 101 and materialized['ITQ_variants'] == 51 and materialized['ITQ_cases'] == 23, materialized['count'])
        inventory = read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
        rows = extract(next(t for t in inventory if t['stage_id'] == 'U-fresh'))['observations'][:21]
        profile = read('phase5_r5_2_2_fixture_tracking_profile.json')
        classifier = read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
        plain = reference_rows(rows[:3], profile, classifier, observed=False)
        observed = reference_rows(rows[:3], profile, classifier, observed=True)
        noninterference = plain['final'] == observed['final'] and canonical(plain['snapshot']) == canonical(observed['snapshot'])
        note('observer-56-field-noninterference', noninterference and len(observed['final']) == 56, len(observed['final']))
        if not noninterference:
            raise RuntimeError('STOP_OBSERVER_INTERFERENCE')
        note('typed-codec', encode(0.0) != encode(-0.0) and encode(True) != encode(1)
             and {'type': 'absent'} != encode(None), 'signedzero/type/presence exact')
        view = MeasurementView.from_row(rows[0])
        denied = []
        try:
            view.request('plc_command', denied)
        except CapabilityError:
            pass
        note('restricted-measurement-capability', bool(denied) and not hasattr(view, 'plc_command'), denied)
        future_packet = deepcopy(rows[0])
        future_packet['release_ns'] = future_packet['time_ns'] + 1
        try:
            MeasurementView.from_row(future_packet)
            future_denied = False
        except CapabilityError:
            future_denied = True
        note('unreleased-measurement-denied', future_denied, 'no future packet payload enters PRE')
        try:
            SplitEngine(profile, classifier).pre(rows[0], SimulatedPLC(rows).prior, 'bad-full-row')
            rejected = False
        except CapabilityError:
            rejected = True
        note('PRE-rejects-full-row', rejected, 'no raw command/schedule capability')
        role_engine, role_plc = SplitEngine(profile, classifier), SimulatedPLC(rows)
        role_pre = role_engine.pre(view, role_plc.prior, 'role-capability')
        role_safety = role_engine.safety(role_pre)
        role_output = role_plc.issue(role_safety, view)
        try:
            role_engine.accept_plc(Record.make(role_output.data()))
            rejected_plain = False
        except CapabilityError:
            rejected_plain = True
        role_engine.accept_plc(role_output)
        note('PLC-owned-token-not-producer-string', rejected_plain, 'forged Record withcorrectproducer denied; genuine issuedtoken accepted')
        try:
            role_engine.accept_plc(role_output)
            duplicate_denied = False
        except CapabilityError:
            duplicate_denied = True
        note('duplicate-PLC-token-denied', duplicate_denied, 'same transaction phase token cannotbeaccepted twice')
        reference = reference_rows(rows, profile, classifier)['frames']
        oracle = OracleTrace('U-none', rows)
        pressure_oracle = OracleTrace('U-pressure', rows)
        actual = pipeline(rows, profile, classifier, 'dev-U')
        comparison = compare_traces(reference, actual, oracle=oracle)
        evidence['bounded_U'] = {'row_count': len(rows), 'reference_frames': reference,
                               'split_frames': actual, 'comparison': comparison}
        note('bounded-U-fullcore-3lanes', comparison['status'] == 'PASS', comparison)
        at = actual[6]
        core = {k: decode(v) for k, v in at['after'].items()}
        witness = (at['PRE']['state'] == 'TRACKING_FAULT_SUSPECTED' and at['POST']['state'] == 'STEADY_TRACKING'
                   and core['carried_suspicion_evidence'] == 1 and not core['confirmed_latched']
                   and core['startup_demand_suspended'] and not core['records'][-1]['current_direction_active'])
        note('known-StateU-1p2s', witness, {'PRE': at['PRE']['state'], 'POST': at['POST']['state'], 'count': core['carried_suspicion_evidence']})
        pressure = pipeline(rows, profile, classifier, 'dev-pressure', other=({'code': 'PRESSURE_FAULT', 'severity': 'FAULT'},))
        note('pressure-reasons-and-numeric-OUT_OF_SCOPE', compare(reference[6], pressure[6], trusted_context=pressure_oracle.context(6, reference))['status'] == 'PASS'
             and pressure[6]['PLC']['command'] == rows[6]['plc_command']
             and pressure[6]['PLC']['numeric_hardware_authorization'] == 'OUT_OF_SCOPE', pressure[6]['SAFETY'])
        confirmed_index = next(i for i, frame in enumerate(reference) if decode(frame['after']['confirmed_latched']))
        mutations = _mutation_checks(reference[6], at, reference[6], pressure[6],
                                     reference[confirmed_index], actual[confirmed_index], output,
                                     oracle.context(6, reference), pressure_oracle.context(6, reference),
                                     oracle.context(confirmed_index, reference))
        evidence['comparator_mutations'] = mutations
        note('independent-comparator-negatives', all(t['matched'] for t in mutations), len(mutations))
        caught = {t['expected_rule'] for t in mutations if t['matched']}
        note('all-18-rules-negative-coverage', set(comparison['rules']).issubset(caught), sorted(caught))

        def pre_prefix(schedule):
            engine, plc = SplitEngine(profile, classifier), SimulatedPLC(schedule)
            for i, row in enumerate(schedule[:7]):
                m = MeasurementView.from_row(row)
                pre = engine.pre(m, plc.prior, 'causality:' + str(i))
                if i == 6:
                    return pre.digest, observe(engine.q)
                safety = engine.safety(pre)
                engine.accept_plc(plc.issue(safety, m))
                engine.post()
        future = deepcopy(rows)
        future[6]['plc_command'] = 0.8  # synthetic private future output only; original fixture untouched
        note('future-suffix-PRE-noninterference', pre_prefix(rows) == pre_prefix(future), 'private same-cycle command changed, identical PRE prefix')
        repeated = pipeline(rows, profile, classifier, 'repeat-U')
        normalized = [repeat_fingerprint(r, a, 'dev-U', trusted_context=oracle.context(i, reference)) for i, (r, a) in enumerate(zip(reference, actual))]
        normalized_repeat = [repeat_fingerprint(r, a, 'repeat-U', trusted_context=oracle.context(i, reference)) for i, (r, a) in enumerate(zip(reference, repeated))]
        evidence['repeat_evidence'] = {'repeat_frames': repeated, 'first_hashes': normalized,
                                     'repeat_hashes': normalized_repeat}
        note('bounded-development-repeat', normalized == normalized_repeat, 'new metadata only; raw immutable bindings checked before normalization')

        faults = []
        for cut in ('PRE', 'SAFETY', 'PLC', 'POST'):
            e, plc = SplitEngine(profile, classifier), SimulatedPLC(rows)
            m = MeasurementView.from_row(rows[0])
            pre = e.pre(m, plc.prior, 'fault-' + cut)
            if cut in ('SAFETY', 'PLC', 'POST'):
                safety = e.safety(pre)
            if cut in ('PLC', 'POST'):
                e.accept_plc(plc.issue(safety, m))
            if cut == 'POST':
                e.post(fail_before_publication=True)
            audit = e.abort('ISSUED' if cut in ('PLC', 'POST') else 'UNKNOWN')
            faults.append({'cut': cut, 'audit': audit, 'policy_check': incomplete_assertions(audit)})
            if cut in ('PLC', 'POST'):
                one = e.reconcile_known_issue('fault-' + cut)
                again = e.reconcile_known_issue('fault-' + cut)
                faults[-1]['idempotent'] = one == again and len(e.q.records) == 1
                one['POST']['state'] = 'caller-modified-copy'
                faults[-1]['immutable_history'] = e.reconcile_known_issue('fault-' + cut)['POST']['state'] != 'caller-modified-copy'
            else:
                try:
                    e.reconcile_known_issue('fault-' + cut)
                    faults[-1]['unknown_rejected'] = False
                except CapabilityError:
                    faults[-1]['unknown_rejected'] = True
        evidence['in_memory_fault_models'] = faults
        note('T09-memory-model-only', all(x['policy_check']['passed'] and (x.get('idempotent') or x.get('unknown_rejected')) for x in faults), 'durability NOT qualified')
        negative_audits = []
        for name, mutate in [
            ('fake-complete-commit', lambda x: x['commits'].append('POST_FINAL_PUBLICATION_COMMIT')),
            ('unknown-coerced-no-journal', lambda x: x.__setitem__('command_issue_status', 'ISSUED')),
            ('automatic-resend', lambda x: x.__setitem__('automatic_resend', True)),
            ('fake-fresh-publication', lambda x: x.__setitem__('fresh_publication', True))]:
            mutated = deepcopy(faults[0]['audit'])
            mutate(mutated)
            negative_audits.append({'name': name, 'rejected': not incomplete_assertions(mutated)['passed']})
        evidence['T09_negative_audits'] = negative_audits
        note('T09-incomplete-negative-guards', all(x['rejected'] for x in negative_audits)
             and all(x.get('immutable_history', True) for x in faults), negative_audits)
    except Exception as ex:
        note('development-exception', False, type(ex).__name__ + ': ' + str(ex))
        evidence['exception_trace'] = traceback.format_exc()
    guard()
    after = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))}
    note('version-source-integrity', sources == after, 'no source edit during development execution')
    evidence['sources_after'] = after
    evidence['finished_at_UTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    evidence['passed'] = all(c['passed'] for c in evidence['checks'])
    evidence['gate'] = 'C3_B_DEVELOPMENT_READY_FOR_FREEZE_REVIEW' if evidence['passed'] else 'C3_B_DEVELOPMENT_INCOMPLETE'
    evidence['C3_C_EXECUTION_AUTHORIZED'] = 'NO'
    evidence['UP04_FULL_SPLIT_EQUIVALENCE'] = 'UNRESOLVED'
    receipt = persist(output / 'development-evidence.json', evidence)
    print(json.dumps({'mode': MODE, 'execution_id': run_id, 'gate': evidence['gate'],
                      'checks': evidence['checks'], 'evidence': receipt}, ensure_ascii=True))


if __name__ == '__main__':
    main()


