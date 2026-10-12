"""Exclusive durable artifacts; immutable evidence cannot be overwritten."""
import json
import os
from pathlib import Path
from .common import ROOT,canonical,sha


def write(path,data):
    path=Path(path).resolve()
    if not path.is_relative_to((ROOT/'artifacts/m1-autonomous-development').resolve()):
        raise ValueError('ARTIFACT_SCOPE_DENIED')
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=data if type(data) is bytes else canonical(data)+b'\n'
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    if path.read_bytes()!=raw:raise IOError('EVIDENCE_READBACK_MISMATCH')
    return receipt(path)


def receipt(path):
    path=Path(path).resolve()
    if path.with_suffix('.trace_index.json').exists():
        from .stream_trace import plain_receipt
        return plain_receipt(path,canonical_document=True)
    raw=path.read_bytes()
    result={'path':str(path.relative_to(ROOT).as_posix()),'raw_sha256':sha(raw),'bytes':len(raw)}
    if path.suffix=='.json':result['canonical_sha256']=sha(canonical(json.loads(raw)))
    return result


def verify(item):
    path=(ROOT/item['path']).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('ARTIFACT_ESCAPE')
    actual=receipt(path)
    if actual!=item:raise ValueError('ARTIFACT_INTEGRITY_DRIFT')
    if path.with_suffix('.trace_index.json').exists():
        from .stream_trace import TraceReader
        # Writer validates every full frame before publishing the receipt; later
        # uses recheck all bytes/reassembly. Final campaign performs fresh schema
        # readback per case, avoiding repeated full JSON decoding per PF witness.
        frames=TraceReader(path,item);frames.verify_headers()
        return {**frames.metadata,'frames':frames}
    return json.loads(path.read_bytes()) if path.suffix=='.json' else path.read_bytes()

