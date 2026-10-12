"""Independent remote DEVELOPMENT authority; sealed local guards are not imported."""
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def manifest():
    path = ROOT / 'v0_2/tests/tools/m1_remote_control_v3/execution_manifest.json'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != os.environ.get('C2C_M1_EXECUTION_MANIFEST_SHA256'):
        raise ValueError('M1_REMOTE_MANIFEST_IDENTITY_DRIFT')
    return json.loads(raw)


def current_identity():
    lock = json.loads((ROOT / 'v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json').read_bytes())
    return {'host': platform.node(), 'python': platform.python_version(), 'executable': sys.executable,
            'system': platform.system(), 'version': platform.version(), 'machine': platform.machine(),
            'image_os': os.environ.get('ImageOS'), 'image_version': os.environ.get('ImageVersion'),
            'dependencies': {name: importlib.metadata.version(name) for name in lock['dependencies']}}


def admit():
    if (platform.node().upper() == 'HIPPO' or os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'
            or os.environ.get('RUNNER_OS') != 'Windows'):
        raise ValueError('M1_REQUIRES_INDEPENDENT_HOSTED_WINDOWS')
    path = os.environ.get('C2C_M1_REMOTE_ENVIRONMENT_PATH')
    expected = os.environ.get('C2C_M1_REMOTE_ENVIRONMENT_SHA256')
    if not path or not expected:
        raise ValueError('M1_NEW_ENVIRONMENT_NOT_REGISTERED')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('M1_NEW_ENVIRONMENT_REGISTRATION_DRIFT')
    record = json.loads(raw)
    if record.get('scope') != 'M1_REMOTE_DEVELOPMENT_ONLY' or record.get('status') != 'MECHANICALLY_ADMITTED_FOR_REMOTE_DEVELOPMENT':
        raise ValueError('M1_REMOTE_AUTHORITY_SCOPE_DENIED')
    actual = current_identity()
    if actual != record['runtime_identity']:
        raise ValueError('M1_REMOTE_ENVIRONMENT_IDENTITY_DRIFT')
    data = manifest()
    if record['execution_manifest_raw_sha256'] != os.environ['C2C_M1_EXECUTION_MANIFEST_SHA256']:
        raise ValueError('M1_ENVIRONMENT_SOURCE_MANIFEST_MISMATCH')
    for name, expected_hash in record.get('runtime_input_raw_hashes', {}).items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError('M1_FRESH_BASE_EVIDENCE_DRIFT: ' + name)
    for name, expected_hash in {**data['bundle_entry_raw_hashes'], **data['remote_source_raw_hashes']}.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError('M1_REMOTE_PROTECTED_SOURCE_DRIFT: ' + name)
    return {'environment': actual, 'registration_raw_sha256': expected,
            'mode': 'DEVELOPMENT_ONLY_NOT_QUALIFICATION'}
