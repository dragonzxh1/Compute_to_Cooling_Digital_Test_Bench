"""No numerical imports until externally proven controlled Windows Job release."""
import os,sys,json,time,platform,hashlib,importlib.metadata,traceback
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[4];stage,location=sys.argv[1:];directory=Path(location).resolve()
    if (platform.node().upper()=='HIPPO' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted'
        or os.environ.get('RUNNER_OS')!='Windows' or not directory.is_relative_to(root/'artifacts/m1-autonomous-development')):raise RuntimeError('ISOLATED_REMOTE_REQUIRED')
    def save(name,value):
        with (directory/name).open('xb') as f:f.write(json.dumps(value,sort_keys=True,allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())
    save('ready.json',dict(pid=os.getpid(),executable=sys.executable));deadline=time.monotonic()+25
    while not(directory/'release.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('RELEASE_TIMEOUT')
        time.sleep(.05)
    release=json.loads((directory/'release.json').read_bytes());raw=(directory/'external_job_identity.json').read_bytes();proof=json.loads(raw)
    if (release['actual_python_pid']!=os.getpid() or proof['actual_python_pid']!=os.getpid() or not proof['in_target_job']
        or proof['cpu_rate']!=2500 or proof['process_mb']!=1024 or proof['job_mb']!=2048 or release['external_proof_raw_sha256']!=hashlib.sha256(raw).hexdigest()):raise RuntimeError('ACTUAL_JOB_REQUIRED')
    os.environ['MEMPHIS_VERIFIED_PID']=str(os.getpid())
    def environment():return dict(python=platform.python_version(),executable=sys.executable,image=os.environ.get('ImageVersion'),
        dependencies={k:importlib.metadata.version(k) for k in ('numpy','pytest','jsonschema')},source_commit=os.environ['GITHUB_SHA'],job_proof_sha256=hashlib.sha256(raw).hexdigest())
    env=environment()
    if env['image'] not in ('20261004.326.1','20261012.333.1') or env['python']!='3.11.9' or env['dependencies']!={'numpy':'2.4.6','pytest':'9.1.1','jsonschema':'4.26.0'}:raise RuntimeError('EXACT_ENVIRONMENT_REQUIRED')
    result=dict(stage=stage,status='FAIL',pid=os.getpid(),environment=env,scope='DEVELOPMENT_EXECUTION_NOT_EQUIPMENT_PASS',formal_C3C=False)
    print('RACK_STAGE_BEGIN '+stage,flush=True)
    try:
        from .cases import HERE,registration,config
        from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import read,write
        spec=next(s for s in registration()['cases'] if s['id']==stage)
        if stage=='BASELINE':
            import pytest
            code=pytest.main(['-q','-p','no:cacheprovider',str(HERE.parent/'gb300_m1_closed_loop_v1/test_integration.py')])
            if code:raise ValueError('EXISTING_INTEGRATION_BASELINE_FAIL')
            from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import run
            expected=read(HERE.parent/'gb300_m1_closed_loop_v2/v1_regression_hashes.json');evidence={}
            for name in ('LOAD_STEP','PUMP_STUCK'):
                out=run(read(HERE.parent/'gb300_m1_closed_loop_v1/scenario.json'),name,directory/name)
                if out['status']!='PASS':raise ValueError('FRESH_ORIGINAL_BASELINE_FAIL')
                actual={k:hashlib.sha256((directory/name/k).read_bytes()).hexdigest() for k in expected[name]}
                if actual!=expected[name]:raise ValueError('FRESH_ORIGINAL_BYTES_DRIFT')
                evidence[name]=actual
            result.update(status='PASS',fresh_regression=evidence)
        elif stage=='NEGATIVE':
            import pytest
            code=pytest.main(['-q','-p','no:cacheprovider',str(HERE/'test_baseline.py')])
            if code:raise ValueError('NEW_UNIT_REFUSAL_FAIL')
            result.update(status='PASS',pytest_exitcode=code)
        elif stage=='COMPONENT':
            from math import exp
            rows=[]
            # Constant-inlet finite rack CV, no HX/closed-loop capacity claim.
            cv=1009*4000;capacity=cv*.05;q=11.395/3600;power=147250.;inlet=44.
            steady=inlet+power/(cv*q);errors=[]
            for dt in (.1,.05,.025):
                t=inlet;steps=round(30/dt);ledger=0.
                for _ in range(steps):
                    rate=cv*q*(inlet-t)+power;t+=dt*rate;ledger+=dt*rate
                exact=steady+(inlet-steady)*exp(-q*30/.05);error=abs(t-exact);errors.append(error)
                if abs(capacity*(t-inlet)-ledger)>1e-5:raise ValueError('COMPONENT_ENERGY_CLOSURE')
                rows.append(dict(dt_s=dt,final_C=t,analytic_C=exact,error_K=error))
            if not(errors[2]<errors[1]<errors[0]):raise ValueError('COMPONENT_REFINEMENT_FAIL')
            result.update(status='PASS',scope='FIXED_BOUNDARY_COMPONENT_ONLY_NOT_CLOSED_LOOP',ideal_return_C=steady,step_refinement=rows)
        else:
            from .simulation import run
            from .audit import audit
            model=run(config(spec),directory/'case');analysis=audit(directory/'case',spec)
            write(directory/'independent_analysis.json',analysis)
            result.update(status='PASS',model=model,independent_analysis=analysis)
    except BaseException as e:
        result.update(error=str(e),error_type=type(e).__name__,traceback=traceback.format_exc());print(result['traceback'],flush=True)
    result['environment_after']=environment()
    if result['environment_after']!=env:result.update(status='FAIL',error='ENVIRONMENT_DRIFT')
    save('result.json',result);print('RACK_STAGE_END '+stage+' '+result['status'],flush=True)
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
