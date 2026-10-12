"""Independent old-interval evaluator over a trusted entry-state copy.

Only immutable qualified reference parent rules are used; never calls split code.
This is newly derived policy evidence, NOT a historical production PRE golden.
The original reference instance is never advanced by this evaluator.
"""
from copy import deepcopy
from dataclasses import replace
from v0_2.examples.phase5_r5_2_1r4_3_startup_engine import StartupTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from .observer import observe
from .state_copy import clone_qualifier


def derive(reference, row, provenance, causal_history=None):
    q=clone_qualifier(reference)
    if causal_history is not None:
        q.response_history=deepcopy(causal_history)
    prior=reference.previous_observation
    command=reference.last_command if reference.last_command is not None else row['plc_command']
    issued=prior.command_timestamp_ns if prior is not None else row['command_timestamp_ns']
    item=ReleasedObservation(**{**row,'plc_command':command,'command_timestamp_ns':issued})
    active=q.epoch is not None and q.epoch.completion_reason is None
    epoch=replace(q.epoch) if active else None
    start,demand=q.oldest_unresolved_demand_ns,q.latest_demand
    entering=q.state
    valid=StartupTrackingQualifier._valid(q,item)
    eligible=valid and provenance=='CERTIFIED_INTERVAL_END' and item.measurement_record_id not in {
        r['source_measurement_record_id'] for r in q.response_history}
    no_old_reference=q.resolved_pair is None and q.startup_observation is None
    result = None
    if not valid or no_old_reference:
        q.state='TRACKING_FAULT_CONFIRMED' if q.confirmed_latched else 'STEADY_TRACKING' if valid else 'INSUFFICIENT_MEASUREMENT'
    else:
        q._evaluation_allowed=not valid or eligible
        try: result=StartupTrackingQualifier.update(q,item)
        finally:q._evaluation_allowed=True
        q._consume(item,result,epoch,start,demand)
        if valid and not eligible:q.state='TRACKING_FAULT_CONFIRMED' if q.confirmed_latched else entering
        if result['qualified_progress'] and q.oldest_unresolved_demand_ns is not None:q.episode_progress=True
    return {'kind':'DERIVED_INDEPENDENT_OLD_INTERVAL_EXPECTATION_NOT_HISTORICAL_GOLDEN',
            'core':observe(q),'old_command':{'value':command,'issue_ns':issued,
                                           'identity':'released-command:'+str(issued)},
            'valid':valid,'eligible':eligible,'active':active,'source_id':row['measurement_record_id'],
            'evaluation':result}


