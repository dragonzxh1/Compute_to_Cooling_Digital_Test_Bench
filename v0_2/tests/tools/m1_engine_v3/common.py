"""Immutable records, artifact I/O and frozen baseline guards (development only)."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parents[4]
MODE = 'DEVELOPMENT_ONLY_NOT_QUALIFICATION'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_bytes())


def frozen_source_path(name):
    """Exact-byte portability for five hash-bound historical approval attachments."""
    path = Path(name)
    if path.is_absolute():
        inventory = read('v0_2/tests/tools/m1_remote_control_v1/source_inventory.json')
        alias = inventory['frozen_external_path_aliases'].get(name)
        if alias is None:
            raise ValueError('UNREGISTERED_EXTERNAL_FROZEN_SOURCE')
        resolved = (ROOT / alias['portable_path']).resolve()
        if not resolved.is_relative_to(ROOT) or sha(resolved.read_bytes()) != alias['raw_sha256']:
            raise ValueError('EXTERNAL_FROZEN_SOURCE_IDENTITY_MISMATCH')
        return resolved
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('FROZEN_SOURCE_PATH_ESCAPE')
    return resolved


def persist(path, value):
    """Exclusive runtime artifacts; never replace a previous evidence file."""
    path = Path(path).resolve()
    allowed = [ROOT / 'artifacts/c3b-development', ROOT / 'artifacts/m1-autonomous-development']
    if not any(path.is_relative_to(folder.resolve()) for folder in allowed):
        raise ValueError('DEVELOPMENT_ARTIFACT_PATH_DENIED')
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise IOError('DEVELOPMENT_PERSISTENCE_MISMATCH')
    return {'path': str(path.relative_to(ROOT)), 'raw_sha256': sha(raw),
            'canonical_sha256': sha(canonical(value))}


def guard():
    evidence = read('phase5_r5_2_1r4_7_c3_a_integrity_evidence.json')
    if sha(canonical(evidence['preregistration_aggregate_payload'])) != evidence['preregistration_aggregate_sha256']:
        raise ValueError('SOURCE_IDENTITY_MISMATCH: aggregate')
    bindings = {**evidence['source_hash_bindings'], **evidence['artifact_hashes']}
    bindings['phase5_r5_2_1r4_7_c3_a_integrity_evidence.json'] = {
        'raw_sha256': '14813e652f748b5cf2a50eb69315dd83d4be83bc5edc7ceaf47ffeb305bdafea'}
    for name, expected in bindings.items():
        raw = frozen_source_path(name).read_bytes()
        if sha(raw) != expected['raw_sha256']:
            raise ValueError('SOURCE_IDENTITY_MISMATCH: ' + name)
        if 'canonical_sha256' in expected and sha(canonical(json.loads(raw))) != expected['canonical_sha256']:
            raise ValueError('SOURCE_IDENTITY_MISMATCH: canonical ' + name)
    return bindings


@dataclass(frozen=True)
class Record:
    """Payload bytes cannot be rewritten; data() returns a detached copy."""
    raw: bytes

    @classmethod
    def make(cls, data):
        return cls(canonical(data))

    def data(self):
        return json.loads(self.raw)

    @property
    def digest(self):
        return sha(self.raw)



