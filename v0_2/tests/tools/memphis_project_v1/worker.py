"""Verified hosted Job entry. No numerical imports before external release."""
import hashlib,importlib.metadata,json,os,platform,sys,time,traceback,subprocess
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[4];stage,location=sys.argv[1:];directory=Path(location).resolve()
    if (platform.node().upper()=='HIPPO' or os.environ.get('GITHUB_ACTIONS')!='true'
        or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted' or os.environ.get('RUNNER_OS')!='Windows'
        or not directory.is_relative_to(root/'artifacts/m1-autonomous-development')):raise RuntimeError('ISOLATED_REMOTE_REQUIRED')
    def save(name,value):
        with (directory/name).open('xb') as f:
            f.write(json.dumps(value,sort_keys=True,allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())
    save('ready.json',dict(pid=os.getpid(),executable=sys.executable));deadline=time.monotonic()+25
    while not(directory/'release.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('EXTERNAL_RELEASE_TIMEOUT')
        time.sleep(.05)
    release=json.loads((directory/'release.json').read_bytes());raw=(directory/'external_job_identity.json').read_bytes();proof=json.loads(raw)
    if (release['actual_python_pid']!=os.getpid() or proof['actual_python_pid']!=os.getpid()
        or not proof['in_target_job'] or proof['cpu_rate']!=2500 or proof['process_mb']!=1024 or proof['job_mb']!=2048
        or release['external_proof_raw_sha256']!=hashlib.sha256(raw).hexdigest()):raise RuntimeError('JOB_IDENTITY_MISMATCH')
    os.environ['MEMPHIS_VERIFIED_PID']=str(os.getpid());os.environ['MEMPHIS_VERIFIED_PARENT_PID']=str(os.getpid())
    from .common import HERE,REG,write,read,case_by_id
    def environment():return dict(python=platform.python_version(),executable=sys.executable,image=os.environ.get('ImageVersion'),
        dependencies={p:importlib.metadata.version(p) for p in ('numpy','pytest','jsonschema')},source_commit=os.environ['GITHUB_SHA'],job_proof_sha256=hashlib.sha256(raw).hexdigest())
    result=dict(stage=stage,status='FAIL',status_scope='SOFTWARE_EXECUTION_AND_EVIDENCE_ONLY_NOT_EQUIPMENT_PASS',environment=environment(),pid=os.getpid(),formal_qualification=False)
    print('MEMPHIS_STAGE_BEGIN '+stage,flush=True)
    try:
        if stage=='NEGATIVE':
            import pytest
            code=pytest.main(['-q','-p','no:cacheprovider',str(HERE/'test_project.py'),str(root/'v0_2/tests/plant/test_hydraulics.py')])
            if code:raise ValueError('DEVELOPMENT_TEST_FAILURE')
            result.update(status='PASS',pytest_exitcode=int(code))
        elif stage=='NODE_PORT':
            node=subprocess.Popen(['node',str(HERE/'bridge.mjs'),str(directory)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            deadline=time.monotonic()+25
            while not(directory/'node_ready.json').exists():
                if node.poll() is not None:raise RuntimeError('NODE_EXITED_BEFORE_JOB_PROOF '+node.stderr.read())
                if time.monotonic()>deadline:raise TimeoutError('NODE_READY_TIMEOUT')
                time.sleep(.05)
            nr=read(directory/'node_ready.json');np=directory/'node_external_job_identity.json'
            subprocess.run([str(root/'artifacts/m1-remote-executor-v1/build/VerifyTarget.exe'),proof['target_job_name'],str(nr['pid']),'1024','2048',str(np),'2500'],check=True,timeout=5)
            nodeproof=read(np)
            if nodeproof['actual_python_pid']!=nr['pid'] or not nodeproof['in_target_job']:raise RuntimeError('NODE_NOT_IN_VERIFIED_JOB')
            save('node_release.json',dict(actual_node_pid=nr['pid'],proof_sha256=hashlib.sha256(np.read_bytes()).hexdigest()))
            out,err=node.communicate(timeout=30)
            if node.returncode:raise RuntimeError('UPSTREAM_NODE_FAILURE '+err)
            data=json.loads(out);write(directory/'upstream_actual_output.json',data)
            from .tank import verify_upstream_vectors
            from .sources import tower_capacity
            from .audit import close
            for v in data['tower']:
                # Upstream function chooses ONE_WET at HOT; PG and capacity
                # rating algebra must agree, not an OEM acceptance gate.
                cap=v['capacity'];expected=tower_capacity('W1',v['flow'],v['hot'])
                actual=cap['qMax'] if 'qMax' in cap else cap.get('qmax_w',cap.get('qmax'))
                if actual is None:raise ValueError('UPSTREAM_TOWER_SCHEMA '+str(cap.keys()))
                close(actual,expected,8192)
            result.update(status='PASS',port=verify_upstream_vectors(data),node=data['node'])
        elif stage=='SOURCE_COMPARISON':
            from .hydraulics import source_comparison
            result.update(status='PASS',comparison=source_comparison());write(directory/'source_comparison.json',result['comparison'])
        else:
            spec=case_by_id(stage);write(directory/'case_spec.json',spec)
            if spec['scope']=='V2_BASE':
                from v0_2.tests.tools.gb300_m1_closed_loop_v2.cases import matrix,config
                from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import run
                from v0_2.tests.tools.gb300_m1_closed_loop_v2.audit import audit
                prior=matrix()['BASE__'+spec['case']];payload=run(config(prior),spec['case'],directory/'case');independent=audit(directory/'case',prior)
                expected=read(HERE.parent/'gb300_m1_closed_loop_v2/v1_regression_hashes.json')[spec['case']]
                hashes={n:hashlib.sha256((directory/'case'/n).read_bytes()).hexdigest() for n in expected}
                if hashes!=expected:raise ValueError('V1_V2_BASELINE_RAW_CHANGED')
                result.update(status='PASS',regression=hashes,baseline_actual=payload,independent_analysis=independent)
            elif spec['ua_w_k'] is None:
                from .simulation import run
                try:run(spec,directory/'case')
                except ValueError as e:
                    if str(e)!='INCOMPLETE_MISSING_EQUIPMENT_UA':raise
                    result.update(status='PASS',expected_refusal=str(e),equipment_suitability='NOT_VERIFIED')
                else:raise ValueError('MISSING_UA_NOT_REFUSED')
            else:
                from .simulation import run
                from .audit import audit
                payload=run(spec,directory/'case');independent=audit(directory/'case',spec)
                write(directory/'independent_analysis.json',independent)
                result.update(status='PASS',model_execution=payload,independent_analysis=independent,
                    status_scope='EXECUTION_AND_INDEPENDENT_EQUATION_CHECKS_ONLY_SEVEN_ENGINEERING_GRADES_SEPARATE')
    except BaseException as e:
        result.update(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc());print(result['traceback'],flush=True)
    result['environment_after']=environment()
    if result['environment']!=result['environment_after']:result.update(status='FAIL',error='ENVIRONMENT_DRIFT')
    save('result.json',result);print('MEMPHIS_STAGE_END '+stage+' '+result['status'],flush=True)
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
