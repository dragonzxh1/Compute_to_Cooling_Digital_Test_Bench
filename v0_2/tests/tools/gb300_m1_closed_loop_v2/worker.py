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
    os.environ['SIX_RACK_V2_VERIFIED_PID']=str(os.getpid())
    from .simulation import run, read, write, HERE
    from .cases import matrix,config,V1
    from .audit import audit
    result = dict(stage=stage, status='FAIL', pid=os.getpid(), formal_qualification=False)
    result['environment'] = dict(python=platform.python_version(), executable=sys.executable,
        system=platform.system(), machine=platform.machine(), image=os.environ.get('ImageVersion'),
        dependencies={p:importlib.metadata.version(p) for p in ('numpy','pytest','jsonschema')},
        job_proof_sha256=hashlib.sha256(proof_raw).hexdigest(), source_commit=os.environ['GITHUB_SHA'])
    print(json.dumps(dict(event='STAGE_BEGIN', stage=stage, pid=os.getpid())), flush=True)
    try:
        if stage == 'NEGATIVE':
            import pytest
            code = pytest.main(['-q','-p','no:cacheprovider',str(V1/'test_integration.py'),str(HERE/'test_study.py'),
                str(root/'v0_2/tests/plant/test_hydraulics.py')])
            result.update(status='PASS' if code == 0 else 'FAIL', pytest_exitcode=int(code))
        else:
            spec=matrix()[stage];c=config(spec)
            write(directory/'case_spec.json',spec)
            if stage.startswith('BASE__') or stage.startswith('REFINE_STUCK'):
                from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import run as baseline_run
                payload=baseline_run(c,spec['case'],directory/'case')
            else:
                payload=run(c,spec['case'],directory/'case',setting=spec['setting'],fault=spec['fault'])
            independent=audit(directory/'case',spec)
            write(directory/'independent_analysis.json',independent)
            regression=None
            if stage.startswith('BASE__'):
                expectations=read(HERE/'v1_regression_hashes.json')[spec['case']]
                regression={name:hashlib.sha256((directory/'case'/name).read_bytes()).hexdigest()==digest for name,digest in expectations.items()}
                if not all(regression.values()): raise ValueError('V1_FRESH_REGRESSION_CHANGED')
            integrity=('energy','heat_sources','pump_energy','transactions','mass','load_step_affects_heat','commands_observation_bound','thermal_response')
            if not all(payload['checks'][k] for k in integrity): raise ValueError('MANDATORY_INTEGRATION_INTEGRITY')
            # A completed sensitivity experiment is NOT a behavioral PASS.
            # Preserve contrary findings under payload unchanged and report
            # non-robust conclusions instead of adjusting rules/expectations.
            status=payload['status'] if stage.startswith('BASE__') or spec.get('fault') else 'PASS'
            result.update(status=status,payload=payload,independent_analysis=independent,regression=regression,
                status_scope='STUDY_EXECUTION_AND_EQUATION_AUDIT_NOT_UNCONDITIONAL_BEHAVIORAL_PASS')
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
