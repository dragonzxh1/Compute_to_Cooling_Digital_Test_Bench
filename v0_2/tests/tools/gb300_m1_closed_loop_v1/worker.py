"""Only executes inside a separately verified hosted Windows Job."""
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[4]
    stage, location = sys.argv[1:]
    directory = Path(location).resolve()
    if (platform.node().upper() == 'HIPPO' or os.environ.get('GITHUB_ACTIONS') != 'true'
        or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('RUNNER_OS') != 'Windows'
        or not directory.is_relative_to(root/'artifacts/m1-autonomous-development')):
        raise RuntimeError('ISOLATED_REMOTE_JOB_REQUIRED_NO_LOCAL_MODEL_EXECUTION')
    def save(name, value):
        with (directory/name).open('xb') as f:
            f.write(json.dumps(value, sort_keys=True, allow_nan=False).encode()+b'\n'); f.flush(); os.fsync(f.fileno())
    save('ready.json', dict(pid=os.getpid(), executable=sys.executable))
    deadline = time.monotonic()+25
    while not (directory/'release.json').exists():
        if time.monotonic() > deadline: raise TimeoutError('EXTERNAL_IDENTITY_RELEASE_TIMEOUT')
        time.sleep(.05)
    release = json.loads((directory/'release.json').read_bytes())
    proof_raw = (directory/'external_job_identity.json').read_bytes()
    proof = json.loads(proof_raw)
    if (release['actual_python_pid'] != os.getpid() or proof['actual_python_pid'] != os.getpid()
        or not proof['in_target_job'] or proof['cpu_rate'] != 2500
        or proof['process_mb'] != 1024 or proof['job_mb'] != 2048
        or release['external_proof_raw_sha256'] != hashlib.sha256(proof_raw).hexdigest()):
        raise RuntimeError('ACTUAL_PROCESS_RESOURCE_PROOF_MISMATCH')
    # Native/numerical libraries and the candidate are imported ONLY after release.
    from .simulation import run, read, write, HERE
    result = dict(stage=stage, status='FAIL', pid=os.getpid(), formal_qualification=False)
    result['environment'] = dict(python=platform.python_version(), executable=sys.executable,
        system=platform.system(), machine=platform.machine(), image=os.environ.get('ImageVersion'),
        dependencies={p:importlib.metadata.version(p) for p in ('numpy','pytest','jsonschema')},
        job_proof_sha256=hashlib.sha256(proof_raw).hexdigest(), source_commit=os.environ['GITHUB_SHA'])
    print(json.dumps(dict(event='STAGE_BEGIN', stage=stage, pid=os.getpid())), flush=True)
    try:
        c = read(HERE/'scenario.json')
        if stage == 'NEGATIVE':
            import pytest
            code = pytest.main(['-q','-p','no:cacheprovider',str(HERE/'test_integration.py'),
                str(root/'v0_2/tests/plant/test_hydraulics.py')])
            result.update(status='PASS' if code == 0 else 'FAIL', pytest_exitcode=int(code))
        elif stage in ('LOAD_STEP','PUMP_STUCK','REPEAT_LOAD_STEP','REPEAT_PUMP_STUCK','REFINE_50','REFINE_25'):
            case = 'PUMP_STUCK' if 'PUMP_STUCK' in stage else 'LOAD_STEP'
            if stage.startswith('REFINE'): c['physics_dt_ns'] = int(stage.split('_')[1])*1_000_000
            payload = run(c, case, directory/'case')
            result.update(status=payload['status'], payload=payload)
        else:
            raise ValueError('UNREGISTERED_DEVELOPMENT_STAGE')
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        print(result['traceback'], flush=True)
    result['environment_after'] = dict(python=platform.python_version(), executable=sys.executable,
        system=platform.system(), machine=platform.machine(), image=os.environ.get('ImageVersion'),
        dependencies={p:importlib.metadata.version(p) for p in ('numpy','pytest','jsonschema')},
        job_proof_sha256=hashlib.sha256(proof_raw).hexdigest(), source_commit=os.environ['GITHUB_SHA'])
    if result['environment'] != result['environment_after']:
        result.update(status='FAIL', error='ENVIRONMENT_DRIFT')
    save('result.json', result)
    print(json.dumps(dict(event='STAGE_END', stage=stage, status=result['status'])), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
