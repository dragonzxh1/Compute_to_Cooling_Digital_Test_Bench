"""Non-vacuous PF witnesses from fresh reference/input, never SUT claims."""
from .common import read
from .codec import decode


def native(core):return {k:decode(v) for k,v in core.items()}


def retained(q):
    return bool(q['confirmed_latched'] or q['carried_suspicion_evidence']>0
        or q['suspected_since_ns'] is not None or q['episode_progress']
        or any(e['logical_episode_id']=='motion-watch:'+str(q['watch_number']) for e in q['response_history']))


def predicates(frame,row):
    before=native(frame['before']);pre=native(frame['derived_pre']['core']);after=native(frame['after'])
    valid=frame['derived_pre']['valid'];eligible=frame['derived_pre']['eligible']
    active=bool(before['epoch'] and before['epoch']['completion_reason'] is None)
    old=frame['derived_pre']['old_command']['value'];changed=old!=row['plc_command']
    anchor=pre['resolved_pair']['resolved_command_anchor'] if pre['resolved_pair'] else (
        pre['startup_observation']['measured_speed'] if pre['startup_observation'] else None)
    net=None if anchor is None else row['plc_command']-anchor
    withdrawal=changed and net is not None and abs(net)<pre['material_delta']
    reversal=changed and net is not None and abs(net)>=pre['material_delta'] and before['direction'] is not None and (1 if net>0 else -1)!=before['direction']
    inactive=not active
    new_direction=bool(after['epoch'] and after['epoch']['completion_reason'] is None)
    new_history=len(pre['response_history'])>len(before['response_history'])
    return {
        'PF-01':active and valid and eligible and withdrawal and not retained(pre),
        'PF-02':active and valid and withdrawal and retained(pre) and not pre['confirmed_latched'],
        'PF-03':valid and eligible and not before['confirmed_latched'] and pre['confirmed_latched'],
        'PF-04':valid and eligible and withdrawal and pre['resolved_pair'] is None and pre['carried_suspicion_evidence']==1 and not pre['confirmed_latched'],
        'PF-05':inactive and retained(before) and before['startup_demand_suspended'] and changed and new_direction,
        'PF-06':active and valid and eligible and reversal and not pre['confirmed_latched'],
        'PF-07':not valid,
        'PF-08':valid and eligible and before['measurement_unavailable_since_ns'] is not None,
        'PF-09':not valid and after['deferred_demand'] is not None and after['deferred_demand']['deferred_demand_active'],
        'PF-10':len(after['resolved_pair_events'])>len(before['resolved_pair_events']),
        'PF-11':len(after['progress_pair_events'])>len(before['progress_pair_events']),
        'PF-12':valid and before['resolved_pair'] is None and before['startup_observation'] is None and after['startup_observation'] is not None,
        'PF-13':changed and retained(pre) and not pre['confirmed_latched'] and new_direction and (inactive or reversal),
        'PF-14':before['oldest_unresolved_demand_ns'] is not None and retained(pre) and changed and (withdrawal or reversal or inactive),
        'PF-15':new_history or any(e['source_measurement_record_id']==row['measurement_record_id'] for e in before['response_history']),
        'PF-16':before['confirmed_latched'] or pre['confirmed_latched']}


def witnesses(descriptor,frames,rows):
    spec=read('phase5_r5_2_1r4_7_c3_a_pf16_comparison_matrix.json')
    eligible={r['id'] for r in spec['rows'] if any(
        s.get('materialized_existing_input',{}).get('stage_id')==descriptor['stage_id']
        and s.get('materialized_existing_input',{}).get('case_key')==descriptor['case_key'] for s in r['sources'])}
    found={key:[] for key in eligible}
    for i,(frame,row) in enumerate(zip(frames,rows)):
        p=predicates(frame,row)
        for key in eligible:
            if p[key]:found[key].append({'row_index':i,'time_ns':row['time_ns'],'source_id':row['measurement_record_id']})
    return found

