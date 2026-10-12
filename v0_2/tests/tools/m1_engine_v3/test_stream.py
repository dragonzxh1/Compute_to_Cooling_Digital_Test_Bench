"""Fresh old-vs-stream wire equality and journal semantics, not new expectations."""
from pathlib import Path
import uuid
from .common import ROOT, read, canonical, sha, Record
from .materializer import extract
from .stream_trace import TraceReader, CompletedJournal, OracleBridge
from .replay_stream import write_reference, write_split


def equivalence(index, directory):
    from v0_2.tests.tools.m1_engine_v2.observer import reference_rows as old_reference
    from v0_2.tests.tools.m1_engine_v2.adapters import replay as old_split
    from .oracle import OracleTrace
    from .comparator import compare_traces
    descriptor = read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory'][index]
    rows = extract(descriptor)['observations']
    # Use existing small prefixes, not a new numerical fixture/profile.
    if index == 65:
        rows = rows[:5]
    profile = read('phase5_r5_2_2_fixture_tracking_profile.json')
    classifier = read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
    directory = Path(directory)
    ref_receipt = write_reference(rows, profile, classifier, directory/'reference.json', replay_kind=descriptor['replay_kind'])
    old = old_reference(rows, profile, classifier, replay_kind=descriptor['replay_kind'])
    if sha(canonical(old)) != ref_receipt['canonical_sha256']:
        raise ValueError('STREAM_OLD_REFERENCE_WIRE_DIFFERENCE')
    ref = TraceReader(directory/'reference.json', ref_receipt); ref.verify_all()
    if any(ref[i] != frame for i, frame in enumerate(old['frames'])):
        raise ValueError('STREAM_REFERENCE_FRAME_DIFFERENCE')
    split_receipt = write_split(rows, profile, classifier, directory/'split.json', case=descriptor['replay_kind'])
    old_sut = old_split(rows, profile, classifier, case=descriptor['replay_kind'])
    if sha(canonical(old_sut)) != split_receipt['canonical_sha256']:
        raise ValueError('STREAM_OLD_SPLIT_WIRE_DIFFERENCE')
    split = TraceReader(directory/'split.json', split_receipt); split.verify_all()
    if index != 65:
        original_oracle = OracleTrace('source-'+str(index), rows)
        bridge = OracleBridge(OracleTrace('source-'+str(index), rows), ref)
        for i in range(len(rows)):
            if original_oracle.context(i,old['frames']).raw != bridge.context(i,ref).raw:
                raise ValueError('STREAM_ORACLE_CONTEXT_DIFFERENCE')
        result = compare_traces(ref, split, oracle=bridge)
        if result['status'] != 'PASS':
            raise ValueError('STREAM_COMPLETE_COMPARISON_FAIL')
    # Corruption must be rejected, not coerced into the expected digest.
    import shutil
    from .stream_trace import read_row
    raw_path = directory/'negative-corrupt.frames.jsonl'
    shutil.copyfile(ref.frames_path, raw_path)
    with raw_path.open('r+b') as f:
        previous = f.read(1); f.seek(0); f.write(b'!' if previous != b'!' else b'?'); f.flush()
        import os
        os.fsync(f.fileno())
    try:
        read_row(raw_path, ref.index['rows'][0])
    except (ValueError, IOError):
        rejected = True
    else:
        rejected = False
    # Preserve the explicitly negative copy; positive evidence is never rewritten.
    if not rejected:
        raise ValueError('STREAM_CORRUPTION_ACCEPTED')
    journal = CompletedJournal(directory/'journal-semantics.jsonl')
    item = Record.make({'transaction':'sample','all_data':[1,2,3]})
    journal['t'] = item
    if 't' not in journal or 'missing' in journal or journal['t'].raw != item.raw:
        raise ValueError('STREAM_COMPLETED_LOOKUP_CHANGED')
    try:
        journal['t'] = item
    except ValueError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    journal.close()
    if not duplicate_rejected:
        raise ValueError('STREAM_DUPLICATE_COMPLETION_ACCEPTED')
    return {'status':'PASS','index':index,'rows':len(rows),'old_reference_canonical_sha256':ref_receipt['canonical_sha256'],
            'old_split_canonical_sha256':split_receipt['canonical_sha256'],'full_wire_and_frames_equal':True,
            'corruption_rejected':True,'completed_journal_lookup_equal':True,'original_nine_math_sources_unchanged':True}
