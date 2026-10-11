"""POST-only detached legacy view; authoritative ledger is never changed."""
from copy import deepcopy
from .common import canonical, sha
from .codec import decode, encode

POLICY = 'M1-SEM01-POST-LEGACY-HISTORY-v1'


def project(previous, core, pre_record, plc_record, start_index):
    history = decode(core['response_history'])
    view = deepcopy(previous) + deepcopy(history[start_index:])
    bindings = []
    pre, plc = pre_record.data(), plc_record.data()
    old = pre['old_command']
    applies = (plc['command'] == old['value'] and plc['issue_ns'] != old['issue_ns'])
    if applies:
        if plc['issue_ns'] != pre['time_ns']:
            raise ValueError('PROJECTION_NEW_ISSUE_PROOF_REQUIRED')
        for index in range(start_index, len(history)):
            original = history[index]
            if (original['source_measurement_record_id'] != pre['source_id']
                    or original['evaluation_tick_ns'] != pre['time_ns']
                    or original['command_timestamp_ns'] != old['issue_ns']):
                raise ValueError('PROJECTION_PRE_LINK_MISMATCH')
            projected = {**original, 'command_timestamp_ns': plc['issue_ns']}
            view[index] = projected
            bindings.append({'policy': POLICY, 'entry_index': index,
                'transaction_id': pre['transaction_id'], 'pre_id': pre['record_id'],
                'pre_digest': pre_record.digest, 'pre_core_digest': pre['core_digest'],
                'plc_id': plc['record_id'], 'plc_digest': plc_record.digest,
                'source_id': pre['source_id'], 'watch_id': original['logical_episode_id'],
                'obligation_id': original['directional_obligation_id'],
                'old_command_id': old['identity'], 'new_command_id': plc['command_id'],
                'old_issue_ns': old['issue_ns'], 'new_issue_ns': plc['issue_ns'],
                'authoritative_entry_digest': sha(canonical(original)),
                'projected_entry_digest': sha(canonical(projected))})
    return encode(view), bindings

