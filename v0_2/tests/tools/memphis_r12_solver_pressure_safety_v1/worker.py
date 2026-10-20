"""Native Windows Job admission before importing NumPy or the model."""
import os
import sys
import json
import time
import hashlib
import platform
import traceback
from pathlib import Path


def main():
    here=Path(__file__).resolve().parent;repo=here.parents[3];out=Path(sys.argv[1]).resolve();stage=sys.argv[2]
    if (os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted'
        or os.environ.get('RUNNER_OS')!='Windows' or platform.node().upper()=='HIPPO'
        or not out.is_relative_to(repo/'artifacts/memphis-r12-solver-pressure-safety-v1')):raise RuntimeError('REMOTE_ONLY')
    def save(name,value):
        with (out/name).open('xb') as f:
            f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())
    save('ready.json',dict(pid=os.getpid(),executable=sys.executable))
    end=time.monotonic()+25
    while not (out/'release.json').exists():
        if time.monotonic()>end:raise TimeoutError('RELEASE_TIMEOUT')
        time.sleep(.05)
    release=json.loads((out/'release.json').read_bytes());raw=(out/'external_job_identity.json').read_bytes();proof=json.loads(raw)
    if (release['actual_python_pid']!=os.getpid() or proof['actual_python_pid']!=os.getpid() or not proof['in_target_job']
        or proof['cpu_rate']!=2500 or proof['process_mb']!=256 or proof['job_mb']!=512
        or release['external_proof_raw_sha256']!=hashlib.sha256(raw).hexdigest()):raise RuntimeError('ACTUAL_JOB_REQUIRED')
    manifest=json.loads((here/'source_manifest.json').read_bytes())
    def verify():
        for r in manifest['source_files']:
            if hashlib.sha256((repo/r['path']).read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('SOURCE_DRIFT '+r['path'])
    verify()
    if platform.python_version()!='3.11.9':raise RuntimeError('PYTHON_VERSION_DRIFT')
    import numpy
    if numpy.__version__!='2.4.6':raise RuntimeError('DEPENDENCY_VERSION_DRIFT')
    env=dict(source_commit=os.environ['GITHUB_SHA'],image=os.environ.get('ImageVersion'),os=platform.platform(),
        python=platform.python_version(),numpy=numpy.__version__,executable=sys.executable,pid=os.getpid(),stage=stage,
        cpu_rate=2500,process_mb=256,job_mb=512,wall_seconds=480,scope='NEW_RESEARCH_SHORT_DEVELOPMENT_NOT_FORMAL_M1',
        external_job_sha256=hashlib.sha256(raw).hexdigest(),long_run=False)
    save('environment_before.json',env)
    started=time.monotonic();result=dict(status='FAIL',stage=stage,environment=env)
    try:
        from .validation import execute
        details=execute(out/'delivery', stage)
        result.update(status='PASS', meaning='BOUNDED_EXECUTION_NOT_ENGINEERING_APPROVAL',
            elapsed_s=time.monotonic()-started, suite_admitted=True, details=details)
        verify()
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc(),elapsed_s=time.monotonic()-started)
        print(result['traceback'],flush=True)
    save('environment_after.json',env);save('result.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
