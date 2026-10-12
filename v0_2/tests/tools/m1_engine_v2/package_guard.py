"""New remote environment guard. Never changes the sealed local guards."""
import json
from pathlib import Path
from .common import ROOT, sha, guard


def environment():
    from v0_2.tests.tools.m1_remote_control_v2.admission import admit
    return admit()


def sources(lock):
    guard()
    for relative, expected in lock['source_raw_hashes'].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != expected:
            raise ValueError('SOURCE_IDENTITY_MISMATCH: ' + relative)
    return True


def development(lock_path):
    lock = json.loads(Path(lock_path).read_bytes())
    environment()
    sources(lock)
    if lock['mode'] != 'DEVELOPMENT_ONLY_NOT_QUALIFICATION':
        raise ValueError('REMOTE_DEVELOPMENT_MODE_REQUIRED')
    return lock, environment()


def formal_authorization(*args, **kwargs):
    raise ValueError('FORMAL_C3_C_NOT_AUTHORIZED_BY_M1_REMOTE_DEVELOPMENT')
