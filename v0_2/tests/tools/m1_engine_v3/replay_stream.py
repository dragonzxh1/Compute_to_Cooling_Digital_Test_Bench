"""Original loop order and math; complete frames emitted instead of retained."""
from .observer import observe
from .codec import decode
from .engine import SplitEngine
from .scheduler import SimulatedPLC, MeasurementView
from .stream_trace import CompletedJournal, TraceWriter
from v0_2.tests.tools.m1_remote_control_v3.progress import mark


def reference_frames(rows, profile, classifier, *, replay_kind='generic', state=None):
    from v0_2.examples.phase5_r5_2_1r4_5c_lifecycle_engine import WatchLifecycleTrackingQualifier
    from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
    from .pre_oracle import derive
    q = WatchLifecycleTrackingQualifier(profile, classifier)
    if state is not None:
        state['q'] = q
    causal_history = []
    for tick, row in enumerate(rows):
        mark('BEGIN', 'REFERENCE_TICK', tick=tick, time_ns=row['time_ns'])
        before = observe(q)
        provenance = 'POST_COMMAND_EFFECT' if replay_kind == 'ST-08' and row['time_ns'] == 600000000 else 'CERTIFIED_INTERVAL_END'
        derived = derive(q, row, provenance, causal_history)
        causal_history = decode(derived['core']['response_history'])
        mark('BEGIN', 'REFERENCE_UPDATE', tick=tick, time_ns=row['time_ns'])
        q.update(ReleasedObservation(**row), provenance=provenance)
        mark('END', 'REFERENCE_UPDATE', tick=tick, time_ns=row['time_ns'])
        frame = {'before': before, 'after': observe(q), 'input_provenance': provenance, 'derived_pre': derived}
        mark('END', 'REFERENCE_TICK', tick=tick, time_ns=row['time_ns'])
        yield frame
        del frame, before, derived


def split_frames(rows, profile, classifier, journal_path, *, case='generic', state=None):
    engine, plc = SplitEngine(profile, classifier), SimulatedPLC(rows)
    journal = CompletedJournal(journal_path)
    engine._completed = journal
    if state is not None:
        state.update(engine=engine, journal=journal)
    try:
        for index, row in enumerate(rows):
            mark('BEGIN', 'SPLIT_TICK', tick=index, time_ns=row['time_ns'])
            provenance = 'POST_COMMAND_EFFECT' if case == 'ST-08' and row['time_ns'] == 600000000 else 'CERTIFIED_INTERVAL_END'
            m = MeasurementView.from_row(row, provenance)
            mark('BEGIN', 'PRE', tick=index, time_ns=row['time_ns'])
            pre = engine.pre(m, plc.prior, 'adapter:' + str(index))
            mark('END', 'PRE', tick=index, time_ns=row['time_ns'])
            mark('BEGIN', 'SAFETY', tick=index, time_ns=row['time_ns'])
            safety = engine.safety(pre)
            mark('END', 'SAFETY', tick=index, time_ns=row['time_ns'])
            mark('BEGIN', 'PLC_ISSUE_ACCEPT', tick=index, time_ns=row['time_ns'])
            engine.accept_plc(plc.issue(safety, m))
            mark('END', 'PLC_ISSUE_ACCEPT', tick=index, time_ns=row['time_ns'])
            mark('BEGIN', 'POST', tick=index, time_ns=row['time_ns'])
            frame = engine.post()
            mark('END', 'POST', tick=index, time_ns=row['time_ns'])
            mark('END', 'SPLIT_TICK', tick=index, time_ns=row['time_ns'])
            yield frame
            del frame
    finally:
        # TraceWriter may already have closed it on successful finish.
        journal.close()


def write_reference(rows, profile, classifier, path, *, replay_kind='generic'):
    state = {}
    writer = TraceWriter(path, 'reference')
    for frame in reference_frames(rows, profile, classifier, replay_kind=replay_kind, state=state):
        writer.append(frame)
    q = state['q']
    metadata = {'final': observe(q), 'snapshot': q.snapshot()}
    # Original observer-interference check remains: plain independent full replay.
    from .observer import reference_rows
    plain = reference_rows(rows, profile, classifier, observed=False, replay_kind=replay_kind)
    if plain['final'] != metadata['final'] or plain['snapshot'] != metadata['snapshot']:
        raise ValueError('OBSERVER_INTERFERENCE')
    return writer.finish(metadata)


def write_split(rows, profile, classifier, path, *, case='generic'):
    state = {}
    iterator = split_frames(rows, profile, classifier, path.with_suffix('.completed.jsonl'), case=case, state=state)
    # Generator creation does not execute its initialization; retain just first frame.
    first = next(iterator)
    writer = TraceWriter(path, 'split', journal=state['journal'])
    writer.append(first)
    last_after = first['after']['response_history']
    del first
    for frame in iterator:
        writer.append(frame)
        last_after = frame['after']['response_history']
    snapshot = state['engine'].q.snapshot()
    snapshot['response_history'] = decode(last_after)
    return writer.finish({'snapshot': snapshot})
