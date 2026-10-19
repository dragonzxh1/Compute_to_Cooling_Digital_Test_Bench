"""Hosted Job entry: numerical imports follow external identity release."""
import os,sys,json,time,platform,hashlib,importlib.metadata,traceback
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[4];name,location=sys.argv[1:];directory=Path(location).resolve()
    if platform.node().upper()=='HIPPO' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted' or os.environ.get('RUNNER_OS')!='Windows' or not directory.is_relative_to(root/'artifacts/m1-autonomous-development'):raise RuntimeError('ISOLATED_REMOTE_REQUIRED')
    def save(name,value):
        with (directory/name).open('xb') as f:f.write(json.dumps(value,sort_keys=True,allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())
    save('ready.json',dict(pid=os.getpid(),executable=sys.executable));deadline=time.monotonic()+25
    while not(directory/'release.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('RELEASE_TIMEOUT')
        time.sleep(.05)
    release=json.loads((directory/'release.json').read_bytes());raw=(directory/'external_job_identity.json').read_bytes();proof=json.loads(raw)
    if release['actual_python_pid']!=os.getpid() or proof['actual_python_pid']!=os.getpid() or not proof['in_target_job'] or proof['cpu_rate']!=2500 or proof['process_mb']!=1024 or proof['job_mb']!=2048 or release['external_proof_raw_sha256']!=hashlib.sha256(raw).hexdigest():raise RuntimeError('ACTUAL_JOB_REQUIRED')
    os.environ['MEMPHIS_VERIFIED_PID']=str(os.getpid())
    def environment():return dict(python=platform.python_version(),executable=sys.executable,image=os.environ.get('ImageVersion'),dependencies={k:importlib.metadata.version(k) for k in ('numpy','pytest','jsonschema')},source_commit=os.environ['GITHUB_SHA'],job_proof_sha256=hashlib.sha256(raw).hexdigest())
    env=environment()
    if env['image'] not in ('20261004.326.1','20261012.333.1') or env['python']!='3.11.9' or env['dependencies']!={'numpy':'2.4.6','pytest':'9.1.1','jsonschema':'4.26.0'}:raise RuntimeError('EXACT_ENVIRONMENT_REQUIRED')
    result=dict(stage=name,status='FAIL',pid=os.getpid(),environment=env,scope='DEVELOPMENT_EXECUTION_NOT_ENGINEERING_AGGREGATE_PASS',formal_C3C=False)
    print('EQUIPMENT_STAGE_BEGIN '+name,flush=True)
    try:
        from .stages import HERE,stage
        reg=json.loads((HERE/'registration.json').read_bytes());spec=next(s for s in reg['cases'] if s['id']==name)
        result['analysis']=stage(spec,directory);result['status']='PASS';save('independent_analysis.json',result['analysis'])
    except BaseException as e:
        result.update(error=str(e),error_type=type(e).__name__,traceback=traceback.format_exc());print(result['traceback'],flush=True)
    result['environment_after']=environment()
    if result['environment_after']!=env:result.update(status='FAIL',error='ENVIRONMENT_DRIFT')
    save('result.json',result);print('EQUIPMENT_STAGE_END '+name+' '+result['status'],flush=True)
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
