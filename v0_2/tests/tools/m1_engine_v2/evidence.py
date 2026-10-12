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
    path=Path(path).resolve();raw=path.read_bytes()
    result={'path':str(path.relative_to(ROOT).as_posix()),'raw_sha256':sha(raw),'bytes':len(raw)}
    if path.suffix=='.json':result['canonical_sha256']=sha(canonical(json.loads(raw)))
    return result


def verify(item):
    path=(ROOT/item['path']).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('ARTIFACT_ESCAPE')
    actual=receipt(path)
    if actual!=item:raise ValueError('ARTIFACT_INTEGRITY_DRIFT')
    return json.loads(path.read_bytes()) if path.suffix=='.json' else path.read_bytes()

