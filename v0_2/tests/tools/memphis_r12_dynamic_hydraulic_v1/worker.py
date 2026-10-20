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
        or not out.is_relative_to(repo/'artifacts/memphis-r12-dynamic-hydraulic-v1')):raise RuntimeError('REMOTE_ONLY')
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
        from .campaign import run_case
        from .report import package
        reg=json.loads((here/'registration.json').read_bytes());b=(here/reg['topology_file']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=reg['topology_sha256']:raise RuntimeError('TOPOLOGY_RAW_HASH')
        graph=json.loads(b)
        if graph['input_sha256']!=reg['topology_authoring_sha256']:raise RuntimeError('TOPOLOGY_AUTHORING_HASH')
        delivery=out/'delivery';delivery.mkdir();cases=reg['cases'][:1] if stage=='baseline' else reg['cases'][1:]
        results=[];series=[]
        for case in cases:
            if time.monotonic()-started>420:raise TimeoutError('CAMPAIGN_SOFT_LIMIT_420S')
            print('BEGIN '+case['id'],flush=True)
            r,rows=run_case(graph,reg,case,delivery/case['id']);results.append(r);series.append(rows)
            print('END '+case['id'],flush=True)
        if stage=='suite':
            import csv
            import shutil
            origin=out.parent/'baseline';old=json.loads((origin/'result.json').read_bytes())
            if old['environment']['source_commit']!=env['source_commit'] or old['status']!='PASS':raise RuntimeError('SAME_RUN_BASELINE_REQUIRED')
            cid=reg['cases'][0]['id'];source=origin/'delivery'/cid
            baseline=json.loads((source/'case_result.json').read_bytes())
            with (source/'summary.csv').open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            numeric=('t','unit_flow_m3_h','min_rack_flow_m3_h','max_rack_inlet_C','A_secondary_m3_h','B_secondary_m3_h','A_outlet_C','B_outlet_C')
            for row in rows:
                for key in numeric:row[key]=float(row[key])
            shutil.copytree(source,delivery/cid)
            results.insert(0,baseline);series.insert(0,rows)
            save('baseline_origin.json',dict(run_id=os.environ['GITHUB_RUN_ID'],source_commit=env['source_commit'],
                result_raw_sha256=hashlib.sha256((origin/'result.json').read_bytes()).hexdigest(),
                policy='FRESH_SAME_RUN_BASELINE_COPIED_BYTE_FOR_BYTE_NOT_REEXECUTED'))
        package(delivery,reg,results,series,env)
        elapsed=time.monotonic()-started;projection=elapsed*len(reg['cases'])*1.35 if stage=='baseline' else None
        result.update(status='PASS',meaning='BOUNDED_MODEL_EXECUTION_AND_CONSERVATION_ONLY_NOT_ENGINEERING_PASS',
            elapsed_s=elapsed,projected_suite_s=projection,suite_admitted=projection is not None and projection<=420,
            case_results=results)
        verify()
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc(),elapsed_s=time.monotonic()-started)
        print(result['traceback'],flush=True)
    save('environment_after.json',env);save('result.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
