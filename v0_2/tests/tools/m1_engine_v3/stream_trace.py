"""Complete canonical traces on disk; bounded frame reads, no history truncation."""
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from .common import ROOT, Record, canonical, sha
from .evidence import write
from .schemas import validate


def scoped(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'artifacts/m1-autonomous-development'):
        raise ValueError('STREAM_ARTIFACT_SCOPE_DENIED')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def digest_file(path, *, omit_last_lf=False):
    path = Path(path)
    left = path.stat().st_size - int(omit_last_lf)
    h = hashlib.sha256()
    with path.open('rb') as f:
        while left:
            raw = f.read(min(left, 65536))
            if not raw:
                raise IOError('STREAM_FILE_TRUNCATED')
            h.update(raw)
            left -= len(raw)
        if omit_last_lf and f.read(1) != b'\n':
            raise ValueError('STREAM_CANONICAL_FINAL_LF_REQUIRED')
    return h.hexdigest()


def plain_receipt(path, *, canonical_document=False):
    path = scoped(path)
    result = {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
              'raw_sha256': digest_file(path)}
    if canonical_document:
        result['canonical_sha256'] = digest_file(path, omit_last_lf=True)
    return result


class CompletedJournal(Mapping):
    """Same immutable Record lookup as _completed; all bytes retained durably.

    Storage backend only, never a PLC receipt or physical-recovery assertion.
    """
    def __init__(self, path):
        self.path = scoped(path)
        self.stream = self.path.open('xb')
        self.entries = {}
        self.rows = []

    def __setitem__(self, key, record):
        if type(key) is not str or type(record) is not Record or key in self.entries:
            raise ValueError('COMPLETED_RECORD_IDENTITY_REQUIRED')
        raw = record.raw + b'\n'
        offset = self.stream.tell()
        self.stream.write(raw); self.stream.flush(); os.fsync(self.stream.fileno())
        row = {'offset': offset, 'bytes': len(raw), 'raw_sha256': sha(raw)}
        if read_row(self.path, row) != raw:
            raise IOError('COMPLETED_RECORD_READBACK_FAILED')
        self.entries[key] = row
        self.rows.append(row)

    def __getitem__(self, key):
        return Record(read_row(self.path, self.entries[key])[:-1])

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def close(self):
        self.stream.close()


def read_row(path, row):
    with Path(path).open('rb') as f:
        f.seek(row['offset']); raw = f.read(row['bytes'])
    if len(raw) != row['bytes'] or not raw.endswith(b'\n') or sha(raw) != row['raw_sha256']:
        raise IOError('STREAM_FRAME_INTEGRITY_DRIFT')
    return raw


def document_parts(metadata, path, rows):
    """Exactly canonical(full old-format result), independent of I/O chunking."""
    yield b'{'
    first = True
    for key in sorted([*metadata, 'frames']):
        if not first:
            yield b','
        first = False
        yield canonical(key) + b':'
        if key != 'frames':
            yield canonical(metadata[key])
            continue
        yield b'['
        for i, row in enumerate(rows):
            if i:
                yield b','
            yield read_row(path, row)[:-1]
        yield b']'
    yield b'}\n'


class TraceWriter:
    def __init__(self, path, kind, *, journal=None):
        self.path = scoped(path)
        self.kind = kind
        self.journal = journal
        self.frames_path = journal.path if journal else self.path.with_suffix('.frames.jsonl')
        self.stream = None if journal else self.frames_path.open('xb')
        self.rows = []

    def append(self, frame):
        validate('reference' if self.kind == 'reference' else 'frame', frame)
        if self.journal:
            if len(self.journal.rows) != len(self.rows) + 1:
                raise ValueError('COMPLETED_FRAME_ORDER_DRIFT')
            row = self.journal.rows[-1]
            # Same bytes created by unchanged core Record.make(result), not a new golden.
            if json.loads(read_row(self.frames_path, row)) != frame:
                raise ValueError('COMPLETED_FRAME_PUBLICATION_DRIFT')
        else:
            raw = canonical(frame) + b'\n'
            row = {'offset': self.stream.tell(), 'bytes': len(raw), 'raw_sha256': sha(raw)}
            self.stream.write(raw); self.stream.flush(); os.fsync(self.stream.fileno())
            if read_row(self.frames_path, row) != raw:
                raise IOError('STREAM_FRAME_READBACK_FAILED')
        self.rows.append(row)

    def finish(self, metadata):
        if not self.rows or 'frames' in metadata:
            raise ValueError('STREAM_METADATA_OR_FRAME_COUNT_INVALID')
        if self.stream:
            self.stream.close()
        if self.journal:
            self.journal.close()
        with self.path.open('xb') as f:
            for raw in document_parts(metadata, self.frames_path, self.rows):
                f.write(raw)
            f.flush(); os.fsync(f.fileno())
        result = plain_receipt(self.path, canonical_document=True)
        index = {'schema': 'm1-complete-stream-trace-v1', 'kind': self.kind,
                 'document_receipt': result, 'frames_receipt': plain_receipt(self.frames_path),
                 'metadata': metadata, 'rows': self.rows, 'frame_count': len(self.rows)}
        write(self.path.with_suffix('.trace_index.json'), index)
        TraceReader(self.path, result).verify_all()
        return result


class TraceReader(Sequence):
    def __init__(self, path, expected=None):
        self.path = scoped(path)
        self.index = json.loads(self.path.with_suffix('.trace_index.json').read_bytes())
        if self.index['schema'] != 'm1-complete-stream-trace-v1':
            raise ValueError('STREAM_SCHEMA_IDENTITY')
        self.receipt = self.index['document_receipt']
        if expected is not None and self.receipt != expected:
            raise ValueError('STREAM_RECEIPT_IDENTITY_DRIFT')
        self.frames_path = scoped(ROOT / self.index['frames_receipt']['path'])
        self.metadata = self.index['metadata']
        if self.index['frame_count'] != len(self.index['rows']):
            raise ValueError('STREAM_FRAME_COUNT_DRIFT')

    def __len__(self):
        return len(self.index['rows'])

    def raw(self, index):
        if type(index) is not int or index < 0 or index >= len(self):
            raise IndexError(index)
        return read_row(self.frames_path, self.index['rows'][index])[:-1]

    def __getitem__(self, index):
        if isinstance(index, slice):
            return TraceSlice(self, range(*index.indices(len(self))))
        if index < 0:
            index += len(self)
        return json.loads(self.raw(index))

    def verify_headers(self):
        if plain_receipt(self.path, canonical_document=True) != self.receipt:
            raise ValueError('STREAM_DOCUMENT_HASH_DRIFT')
        if plain_receipt(self.frames_path) != self.index['frames_receipt']:
            raise ValueError('STREAM_ROWS_FILE_DRIFT')
        offset = 0
        for i, row in enumerate(self.index['rows']):
            if row['offset'] != offset:
                raise ValueError('STREAM_ROW_GAP_OR_OVERLAP')
            self.raw(i)
            offset += row['bytes']
        if offset != self.frames_path.stat().st_size:
            raise ValueError('STREAM_UNINDEXED_BYTES')
        h = hashlib.sha256()
        for raw in document_parts(self.metadata, self.frames_path, self.index['rows']):
            h.update(raw)
        if h.hexdigest() != self.receipt['raw_sha256']:
            raise ValueError('STREAM_FULL_DOCUMENT_REASSEMBLY_DRIFT')
        return True

    def verify_all(self):
        self.verify_headers()
        for i in range(len(self)):
            raw = self.raw(i)
            frame = json.loads(raw)
            if canonical(frame) != raw:
                raise ValueError('STREAM_NONCANONICAL_FRAME')
            validate('reference' if self.index['kind'] == 'reference' else 'frame', frame)
        from .artifact_schemas import check
        check('snapshot', self.metadata['snapshot'])
        if self.index['kind'] == 'reference':
            validate('core', self.metadata['final'])
        return True


class TraceSlice(Sequence):
    def __init__(self, reader, indices):
        self.reader, self.indices = reader, indices
    def __len__(self):
        return len(self.indices)
    def __getitem__(self, index):
        return self.reader[self.indices[index]]


class OracleBridge:
    """Old oracle unchanged; only its three read-only inputs are cached.

    Full comparison still receives every complete frame and every field.
    """
    def __init__(self, oracle, references):
        self.oracle, self.references = oracle, references
        self.projected = []
        for frame in references:
            self.projected.append({'before': {'max_age_ns': frame['before']['max_age_ns']},
                'after': {k: frame['after'][k] for k in ('previous_observation', 'confirmed_latched')}})
    def context(self, index, references):
        if references is not self.references:
            raise ValueError('ORACLE_REFERENCE_VIEW_IDENTITY_DRIFT')
        return self.oracle.context(index, self.projected)
