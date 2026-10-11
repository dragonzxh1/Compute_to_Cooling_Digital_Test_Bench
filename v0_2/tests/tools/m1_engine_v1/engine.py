"""v014_1 scheduling implementation; reuses frozen math, not lifecycle.update()."""
from copy import deepcopy
from dataclasses import asdict, replace
from v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine import WatchLifecycleTrackingQualifier
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier, StartupObservation
from v0_2.examples.phase5_r5_2_1r4_2_directional_engine import DirectionalTrackingObligation
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from .common import Record, read
from .observer import observe
from .projection import project
from .codec import decode, encode
from .state_copy import clone_qualifier
from .scheduler import MeasurementView, PriorCommand, CapabilityError, IssuedOutput


def contribution(state):
    rules = read('phase5_r5_2_1r4_7_c2_r1_timing_policy_registration.json')['safety_mapping']
    return {k: v for k, v in rules[state].items() if k in ('severity', 'reason_codes', 'restriction')}


class SplitEngine:
    """New driver over immutable qualified parent math; never calls q.update()."""
    def __init__(self, profile, classifier):
        self.q = WatchLifecycleTrackingQualifier(profile, classifier)
        self._transaction = None
        self._completed = {}
        self._fault_reasons = set()
        self.last_publication = None
        self.legacy_response_history = []

    def pre(self, measurement, prior, transaction_id):
        if type(measurement) is not MeasurementView or type(prior) is not PriorCommand:
            raise CapabilityError('PRE_RESTRICTED_VIEW_REQUIRED')
        if self._transaction is not None:
            raise CapabilityError('INVALID_CONTINUATION')
        q = self.q
        if q.last_time_ns is not None and measurement.time_ns <= q.last_time_ns:
            raise ValueError('STRICT_CAUSAL_TIME_REQUIRED')
        access = [{'actor': 'PRE', 'kind': 'PRIOR_COMMAND_READ', 'command_id': prior.identity}]
        values = {name: measurement.request(name, access) for name in measurement.__dataclass_fields__}
        provenance = values.pop('provenance')
        item = ReleasedObservation(plc_command=prior.value, command_timestamp_ns=prior.issue_ns, **values)
        entering = q.state
        before = observe(q)
        history_start = len(q.response_history)
        before['response_history'] = encode(self.legacy_response_history)
        active = q.epoch is not None and q.epoch.completion_reason is None
        epoch = replace(q.epoch) if active else None
        start, demand = q.oldest_unresolved_demand_ns, q.latest_demand
        valid = StartupTrackingQualifier._valid(q, item)
        old_credit = valid and provenance == 'CERTIFIED_INTERVAL_END' and item.measurement_record_id not in {
            e['source_measurement_record_id'] for e in q.response_history}
        transitions_before = len(q.transitions)
        deferred = not valid or (q.resolved_pair is None and q.startup_observation is None)
        if deferred:
            # No valid old directional evidence exists. Command-sensitive
            # context hooks are deferred to POST without measurement credit.
            q.state = 'TRACKING_FAULT_CONFIRMED' if q.confirmed_latched else (
                'STEADY_TRACKING' if valid else 'INSUFFICIENT_MEASUREMENT')
            record = None
        else:
            q._evaluation_allowed = not valid or old_credit
            try:
                record = StartupTrackingQualifier.update(q, item)
            finally:
                q._evaluation_allowed = True
            q._consume(item, record, epoch, start, demand)
            if valid and not old_credit:
                q.state = 'TRACKING_FAULT_CONFIRMED' if q.confirmed_latched else entering
            if record['qualified_progress'] and q.oldest_unresolved_demand_ns is not None:
                q.episode_progress = True
        after_pre = observe(q)
        record_pre = Record.make({'phase': 'PRE', 'record_id': transaction_id + ':PRE',
            'transaction_id': transaction_id, 'time_ns': item.time_ns,
            'measurement': asdict(measurement), 'old_command': asdict(prior),
            'old_epoch_id': epoch.tracking_epoch_id if epoch else None,
            'state': q.state, 'contribution': contribution(q.state),
            'evidence_commit_id': transaction_id + ':E', 'source_id': item.measurement_record_id,
            'core_digest': Record.make(after_pre).digest})
        self._transaction = {'id': transaction_id, 'stage': 'PRE', 'item': item,
            'measurement': measurement, 'prior': prior, 'valid': valid, 'old_credit': old_credit,
            'active': active, 'deferred': deferred, 'entering': entering,
            'transitions_before': transitions_before, 'record': record,
            'before': before, 'pre_core': after_pre, 'pre': record_pre, 'access': access,
            'commits': ['PRE_EVIDENCE_COMMIT'], 'history_start': history_start,
            'old_context_activated': (not active and q.epoch is not None and q.epoch.completion_reason is None)}
        return record_pre

    def safety(self, pre_record, other_channels=()):
        tx = self._require('PRE')
        if pre_record is not tx['pre']:
            raise CapabilityError('PRE_DECISION_BINDING_MISMATCH')
        pre = pre_record.data()
        independent = [dict(c) for c in other_channels]
        if not tx['valid']:
            independent.append({'code': 'SENSOR_INVALID', 'severity': 'FAULT'})
        hierarchy = ['NORMAL', 'FF_DISABLED', 'DEGRADED', 'DERATE_REQUESTED', 'PROTECTED', 'FAULT']
        reasons = set(pre['contribution']['reason_codes']) | {c['code'] for c in independent}
        severities = [pre['contribution']['severity']] + [c['severity'] for c in independent]
        for c in independent:
            if c['severity'] == 'FAULT':
                self._fault_reasons.add(c['code'])
        if pre['contribution']['severity'] == 'FAULT':
            self._fault_reasons.update(pre['contribution']['reason_codes'])
        reasons |= self._fault_reasons
        if self._fault_reasons:
            severities.append('FAULT')
        record = Record.make({'phase': 'SAFETY', 'transaction_id': tx['id'],
            'record_id': tx['id'] + ':SAFETY', 'time_ns': pre['time_ns'],
            'pre_record_id': pre['record_id'], 'pre_digest': pre_record.digest,
            'severity': max(severities, key=hierarchy.index), 'reason_codes': sorted(reasons),
            'independent_channels': independent, 'retained_fault_reasons': sorted(self._fault_reasons),
            'scope': 'SAFETY_MAPPING_POLICY_ASSERTION', 'numeric_envelope_authorization': 'OUT_OF_SCOPE'})
        tx.update(stage='SAFETY', safety=record)
        tx['commits'].append('SAFETY_DECISION_COMMIT')
        return record

    def accept_plc(self, output):
        tx = self._require('SAFETY')
        if type(output) is not IssuedOutput or not output.authenticated():
            raise CapabilityError('PLC_PRODUCER_TOKEN_REQUIRED')
        data = output.data()
        if (data['producer'] != 'SIMULATED_PLC' or data['transaction_id'] != tx['id']
                or data['safety_id'] != tx['safety'].data()['record_id']
                or data['safety_digest'] != tx['safety'].digest
                or data['numeric_hardware_authorization'] != 'OUT_OF_SCOPE'):
            raise CapabilityError('PLC_AUTHORITY_BOUNDARY')
        tx.update(stage='PLC', plc=output)
        tx['access'].append({'actor': 'SIMULATED_PLC', 'kind': 'VERIFIED_OUTPUT_TOKEN', 'record_id': data['record_id']})
        tx['commits'].append('PLC_COMMAND_ISSUE')

    def _context(self, q, item, tx):
        """No evidence evaluator here: reference creation and command lifecycle only."""
        changed = q.last_command is not None and item.plc_command != q.last_command
        pair_before = q.progress_pair.progress_pair_id if q.progress_pair else None
        if not tx['valid']:
            q._process_invalid(item)
            if q.epoch is not None and q.epoch.completion_reason is None:
                q.epoch.latest_command = item.plc_command
            q.state = 'TRACKING_FAULT_CONFIRMED' if q.confirmed_latched else 'INSUFFICIENT_MEASUREMENT'
            return pair_before
        if tx['active'] and changed:
            anchor = q.resolved_pair.resolved_command_anchor if q.resolved_pair else q.startup_observation.measured_speed
            net = item.plc_command - anchor
            if not q.confirmed_latched:
                if abs(net) < q.material_delta:
                    if q.oldest_unresolved_demand_ns is not None:
                        q._withdraw(item)
                    q.state = 'TRACKING_PROGRESS' if tx['record']['qualified_progress'] else 'STEADY_TRACKING'
                elif q.epoch is None or q.epoch.completion_reason is not None or (1 if net > 0 else -1) != q.direction:
                    reason = 'MATERIAL_REVERSAL' if q.epoch is not None else 'REISSUE_RETAINED_HISTORY'
                    q._close_epoch(item, reason)
                    q._start_epoch(item, 1 if net > 0 else -1, reason)
                    q.state = 'HANDOFF_PENDING'
                else:
                    q.epoch.latest_command = item.plc_command
                    q.latest_demand = max(q.latest_demand, abs(net))
                    q.epoch_events.append({'time_ns': item.time_ns, 'event': 'SAME_DIRECTION_UPDATE',
                        'epoch_id': q.epoch.tracking_epoch_id, 'oldest_unresolved_demand_ns': q.oldest_unresolved_demand_ns})
            return pair_before
        if not tx['active'] and not q.confirmed_latched:
            if (tx['record'] is not None and tx['old_context_activated']
                    and not changed):
                # PRE has already evaluated the recovered, previously issued
                # obligation. Do not replace its result with a fresh handoff.
                return pair_before
            if q.resolved_pair is None:
                if q.startup_observation is None:
                    error = item.plc_command - item.measured_speed
                    if abs(error) >= q.material_delta:
                        q.startup_observation = StartupObservation(item.plc_command, item.measured_speed,
                                                                  item.sample_ns, item.measurement_record_id)
                        observed = replace(item, command_timestamp_ns=max(item.command_timestamp_ns, item.sample_ns))
                        q._start_epoch(observed, 1 if error > 0 else -1, 'UNRESOLVED_STARTUP_DEMAND')
                        q.epoch.anchor_command = item.plc_command
                    else:
                        q._set_resolved_pair(item, 'DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE')
                else:
                    net = item.plc_command - q.startup_observation.measured_speed
                    if abs(net) >= q.material_delta:
                        q._start_epoch(item, 1 if net > 0 else -1, 'MATERIAL_REVERSAL')
                        q.epoch.anchor_command = item.plc_command
                        if q.startup_demand_suspended:
                            q.directional_obligation = DirectionalTrackingObligation(
                                1 if net > 0 else -1, item.command_timestamp_ns, item.plc_command,
                                'startup-unresolved:' + q.startup_observation.measurement_record_id,
                                q.progress_pair.progress_pair_id if q.progress_pair else None)
                            q.startup_demand_suspended = False
                pair_before = q.progress_pair.progress_pair_id if q.progress_pair else None
            else:
                gross = item.plc_command - q.resolved_pair.resolved_command_anchor
                if changed and abs(gross) >= q.material_delta:
                    q._start_epoch(item, 1 if gross > 0 else -1, 'OBSERVABLE_MATERIAL_DEMAND')
            q.state = 'HANDOFF_PENDING' if q.epoch is not None and q.epoch.completion_reason is None else 'STEADY_TRACKING'
            q.last_valid_state = q.state
        return pair_before

    def _context_record(self, q, item, pair_before, valid):
        """Context diagnostics, not qualification or evidence consumption."""
        resolved = q.resolved_pair
        pair = q.progress_pair
        gross = item.plc_command - resolved.resolved_command_anchor if resolved else None
        record = {'time_ns': item.time_ns, 'state': q.state, 'demand_class': 'IMMATERIAL_UPDATE',
            'valid': valid, 'plc_command': item.plc_command, 'measured_speed': item.measured_speed,
            'measurement_record_id': item.measurement_record_id, 'qualified_progress': False,
            'checkpoint_command_displacement': None, 'checkpoint_measured_displacement': None,
            'expected_motion': None, 'credited_motion': q.credited_motion,
            'progress_pair_id_before_evaluation': pair_before,
            'fault_evidence_before_evaluation': q.carried_suspicion_evidence,
            'recovery_reevaluated': False}
        if valid and not q.confirmed_latched and q.oldest_unresolved_demand_ns is not None and q.epoch and pair:
            cd = q.direction * (item.plc_command - pair.progress_command_reference)
            md = q.direction * (item.measured_speed - pair.progress_measurement_reference)
            demand = max(0.0, cd + max(0.0, q.direction * (pair.progress_command_reference - pair.progress_measurement_reference)))
            record.update(checkpoint_command_displacement=cd, checkpoint_measured_displacement=md,
                          expected_motion=q._expected(demand, item.time_ns, q.oldest_unresolved_demand_ns))
        if q.last_command != item.plc_command and gross is not None and abs(gross) >= q.material_delta:
            record['demand_class'] = 'OBSERVABLE_MATERIAL_DEMAND' if valid else 'NOT_OBSERVABLE_FOR_TRACKING_QUALIFICATION'
        record.update(resolved_anchor_pair_id=resolved.resolved_anchor_pair_id if resolved else None,
            resolved_command_anchor=resolved.resolved_command_anchor if resolved else None,
            resolved_measurement_anchor=resolved.resolved_measurement_anchor if resolved else None,
            progress_pair_id=pair.progress_pair_id if pair else None,
            progress_command_reference=pair.progress_command_reference if pair else None,
            progress_measurement_reference=pair.progress_measurement_reference if pair else None,
            gross_command_demand=gross, deferred_demand_active=bool(q.deferred_demand and q.deferred_demand.deferred_demand_active),
            deferred_demand_id=q.deferred_demand.deferred_demand_id if q.deferred_demand else None,
            first_observable_demand_ns=q.deferred_demand.first_observable_demand_ns if q.deferred_demand else None,
            measurement_unavailable_since_ns=q.measurement_unavailable_since_ns)
        return record

    def post(self, *, fail_before_publication=False):
        tx = self._require('PLC')
        command = tx['plc'].data()
        item = replace(tx['item'], plc_command=command['command'], command_timestamp_ns=command['issue_ns'])
        # A local working copy cannot roll back the earlier real PRE/PLC facts.
        q = clone_qualifier(self.q)
        before_credit = (q.carried_suspicion_evidence, q.credited_motion, q.confirmed_latched,
                         len(q.response_history), set(q.consumed_samples))
        pair_before = self._context(q, item, tx)
        if before_credit != (q.carried_suspicion_evidence, q.credited_motion, q.confirmed_latched,
                             len(q.response_history), set(q.consumed_samples)):
            raise CapabilityError('POST_CONTEXT_ONLY_EVIDENCE_VIOLATION')
        record = q.records[-1] if tx['record'] is not None else self._context_record(q, item, pair_before, tx['valid'])
        if tx['record'] is None:
            q.records.append(record)
        elif (not tx['active'] and tx['valid'] and q.epoch is not None
              and q.epoch.completion_reason is None and not tx['old_context_activated']):
            diagnostics = self._context_record(q, item, pair_before, tx['valid'])
            record.update(diagnostics)
        if tx['valid'] and tx['old_credit']:
            q.last_measurement_id = item.measurement_record_id
        q.last_command = item.plc_command
        q.last_time_ns = item.time_ns
        q.previous_observation = item
        del q.transitions[tx['transitions_before']:]
        if q.state != tx['entering']:
            q.transitions.append({'time_ns': item.time_ns, 'from': tx['entering'], 'to': q.state,
                                  'measurement_record_id': item.measurement_record_id})
        record.update(state=q.state, plc_command=item.plc_command, valid=tx['valid'],
            measurement_attribution='OLD_OBLIGATION' if tx['active'] and tx['old_credit'] else 'NO_OLD_CREDIT',
            epoch_id=q.epoch.tracking_epoch_id if q.epoch else None,
            epoch_expected_direction=q.epoch.expected_direction if q.epoch else None,
            directional_obligation=asdict(q.directional_obligation) if q.directional_obligation else None,
            watch_id='motion-watch:' + str(q.watch_number) if q.oldest_unresolved_demand_ns is not None else None,
            oldest_unresolved_demand_ns=q.oldest_unresolved_demand_ns,
            carried_suspicion_evidence=q.carried_suspicion_evidence, confirmed_latched=q.confirmed_latched,
            progress_pair_id=q.progress_pair.progress_pair_id if q.progress_pair else None,
            gross_command_demand=item.plc_command-q.resolved_pair.resolved_command_anchor if q.resolved_pair else None,
            startup_demand_suspended=q.startup_demand_suspended,
            startup_observation=asdict(q.startup_observation) if q.startup_observation else None,
            baseline_resolved=q.resolved_pair is not None,
            startup_outage_direction=q.startup_outage_direction,
            opportunity_consumed=any(e['logical_episode_id']=='motion-watch:' + str(q.watch_number)
                for e in q.response_history) and q.oldest_unresolved_demand_ns is not None,
            history_retained=q.oldest_unresolved_demand_ns is not None,
            current_direction_active=q.epoch is not None and q.epoch.completion_reason is None)
        if fail_before_publication:
            self.abort('ISSUED')
            return None
        publication = Record.make({'phase': 'POST', 'record_id': tx['id'] + ':POST',
            'transaction_id': tx['id'], 'time_ns': item.time_ns, 'pre_id': tx['pre'].data()['record_id'],
            'plc_id': command['record_id'], 'state': q.state, 'confirmed_latched': q.confirmed_latched,
            'enrolled_new_command': (command['command'], command['issue_ns']) != (tx['prior'].value, tx['prior'].issue_ns)})
        self.q = q
        self.last_publication = publication
        tx['commits'].append('POST_FINAL_PUBLICATION_COMMIT')
        authoritative = observe(q)
        legacy = dict(authoritative)
        legacy['response_history'], links = project(self.legacy_response_history, authoritative,
            tx['pre'], tx['plc'], tx['history_start'])
        self.legacy_response_history = decode(legacy['response_history'])
        result = {'before': tx['before'], 'pre_core': tx['pre_core'], 'after': legacy,
            'authoritative_after': authoritative, 'legacy_projection_bindings': links,
            'PRE': tx['pre'].data(), 'SAFETY': tx['safety'].data(), 'PLC': command, 'POST': publication.data(),
            'immutable_pre_digest': tx['pre'].digest, 'immutable_safety_digest': tx['safety'].digest,
            'access_log': tx['access'], 'commits': list(tx['commits']), 'status': 'COMPLETE', 'command_issue_status': 'ISSUED'}
        self._completed[tx['id']] = Record.make(result)
        self._transaction = None
        return result

    def abort(self, issue_status='UNKNOWN'):
        if self._transaction is None:
            raise CapabilityError('NO_TRANSACTION')
        tx = self._transaction
        if issue_status == 'ISSUED' and 'plc' not in tx:
            raise CapabilityError('ISSUED_CLAIM_REQUIRES_JOURNAL')
        tx.update(incomplete=True, command_issue_status=issue_status)
        return {'transaction_id': tx['id'], 'time_ns': tx['item'].time_ns,
                'status': 'INCOMPLETE', 'command_issue_status': issue_status,
                'commits': list(tx['commits']), 'last_publication': self.last_publication.data() if self.last_publication else None,
                'command_record': tx['plc'].data() if 'plc' in tx else None,
                'automatic_resend': False, 'fresh_publication': False,
                'integrity': 'INVALID_CONTINUATION', 'durability': 'NOT_PROVEN_IN_MEMORY_ONLY'}

    def reconcile_known_issue(self, transaction_id):
        if transaction_id in self._completed:
            return self._completed[transaction_id].data()
        tx = self._require('PLC')
        if tx['id'] != transaction_id or tx.get('command_issue_status') != 'ISSUED':
            raise CapabilityError('UNKNOWN_ISSUE_NO_AUTOMATIC_ENROLLMENT')
        return self.post()

    def _require(self, stage):
        if self._transaction is None or self._transaction['stage'] != stage:
            raise CapabilityError('PHASE_ORDER_REQUIRED: ' + stage)
        return self._transaction



