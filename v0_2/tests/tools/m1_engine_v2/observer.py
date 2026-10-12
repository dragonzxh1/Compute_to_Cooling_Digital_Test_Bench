"""Read-only entry/exit observer. Does not replace/wrap reference update."""
from .common import read
from .codec import encode, decode
from v0_2.tests.tools.m1_remote_control_v2.progress import mark

FIELDS = tuple(read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')
               ['state_observer_design']['reference_attributes'])


def observe(qualifier):
    mark('BEGIN','OBSERVE_CORE')
    values = vars(qualifier)
    result = {name: encode(values[name]) if name in values else {'type': 'absent'} for name in FIELDS}
    mark('END','OBSERVE_CORE')
    return result


def reference_rows(rows, profile, classifier, *, observed=True, replay_kind='generic'):
    """Only called by explicitly authorized bounded development self-checks."""
    from v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine import WatchLifecycleTrackingQualifier
    from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
    q = WatchLifecycleTrackingQualifier(profile, classifier)
    frames = []
    causal_history = []
    for tick,row in enumerate(rows):
        if observed:mark('BEGIN','REFERENCE_TICK',tick=tick,time_ns=row['time_ns'])
        before = observe(q) if observed else None
        provenance = 'POST_COMMAND_EFFECT' if replay_kind == 'ST-08' and row['time_ns'] == 600000000 else 'CERTIFIED_INTERVAL_END'
        from .pre_oracle import derive
        derived=derive(q,row,provenance,causal_history) if observed else None
        if observed:
            causal_history=decode(derived['core']['response_history'])
        if observed:mark('BEGIN','REFERENCE_UPDATE',tick=tick,time_ns=row['time_ns'])
        q.update(ReleasedObservation(**row), provenance=provenance)
        if observed:mark('END','REFERENCE_UPDATE',tick=tick,time_ns=row['time_ns'])
        if observed:
            frames.append({'before': before, 'after': observe(q), 'input_provenance': provenance,'derived_pre':derived})
            mark('END','REFERENCE_TICK',tick=tick,time_ns=row['time_ns'])
    return {'frames': frames, 'final': observe(q), 'snapshot': q.snapshot()}



