"""Versioned POST commit repair. Frozen math/PRE/Safety/PLC remain inherited."""
from dataclasses import asdict, replace
from v0_2.tests.tools.m1_engine_v3.engine import SplitEngine as BaselineSplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.observer import observe
from v0_2.tests.tools.m1_engine_v3.projection import project
from v0_2.tests.tools.m1_engine_v3.codec import decode
from v0_2.tests.tools.m1_engine_v3.state_copy import clone_qualifier
from v0_2.tests.tools.m1_engine_v3.scheduler import CapabilityError


class SplitEngine(BaselineSplitEngine):
    """Only POST publication ordering changes; not a hardware crash transaction."""

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
        authoritative = observe(q)
        legacy = dict(authoritative)
        legacy['response_history'], links = project(self.legacy_response_history, authoritative,
            tx['pre'], tx['plc'], tx['history_start'])
        prepared_history = decode(legacy['response_history'])
        prepared_commits = [*tx['commits'], 'POST_FINAL_PUBLICATION_COMMIT']
        result = {'before': tx['before'], 'pre_core': tx['pre_core'], 'after': legacy,
            'authoritative_after': authoritative, 'legacy_projection_bindings': links,
            'PRE': tx['pre'].data(), 'SAFETY': tx['safety'].data(), 'PLC': command, 'POST': publication.data(),
            'immutable_pre_digest': tx['pre'].digest, 'immutable_safety_digest': tx['safety'].digest,
            'access_log': tx['access'], 'commits': prepared_commits, 'status': 'COMPLETE', 'command_issue_status': 'ISSUED'}
        completed = Record.make(result)
        # Everything that validates, serializes or persists can fail here.
        # Those failures leave the real PRE/Safety/PLC facts and previous
        # publication intact. Never roll back a command or repeat PRE credit.
        self._completed[tx['id']] = completed
        # Successful completed-store insertion is the commit boundary. No
        # remaining validator, serializer or I/O runs after public assignment.
        self.q = q
        self.last_publication = publication
        self.legacy_response_history = prepared_history
        tx['commits'] = prepared_commits
        self._transaction = None
        return result
