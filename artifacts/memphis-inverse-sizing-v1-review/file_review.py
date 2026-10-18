"""Supplement: independent primary Q-H, tank mass ownership and pump heat.

Pure persisted-file arithmetic. No plant, hydraulic solver or M1 imports.
Existing calculation campaign separately checks secondary/HX/energy/causality.
"""
import os,sys,json,time,hashlib,math,platform
from pathlib import Path
EXEC='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb'
MANIFEST='33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'
def need(x,code):
    if not x:raise ValueError(code)
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False),encoding='utf-8')
def near(a,b):
    need(abs(a-b)<=4096*2**-53/(1-4096*2**-53)*max(1,abs(a)+abs(b)),'INDEPENDENT_PRIMARY_QH_OR_HEAT')
def arrays(p):
    dec=json.JSONDecoder();buf='';pos=0;eof=False
    with Path(p).open(encoding='utf-8-sig') as f:
        def more():
            nonlocal buf,pos,eof
            tail=f.read(262144);buf=buf[pos:]+tail;pos=0;eof=not tail
        def token():
            nonlocal pos
            while True:
                while pos<len(buf) and buf[pos].isspace():pos+=1
                if pos<len(buf):return buf[pos]
                need(not eof,'TRUNCATED_ARRAY');more()
        more();need(token()=='[','ARRAY_ROOT');pos+=1
        if token()==']':pos+=1
        else:
            while True:
                token()
                while True:
                    try:value,end=dec.raw_decode(buf,pos);break
                    except json.JSONDecodeError:need(not eof,'MALFORMED_ARRAY');more()
                pos=end;yield value;c=token();pos+=1
                if c==']':break
                need(c==',','ARRAY_SEPARATOR')
        while not eof:more()
        need(not buf[pos:].strip(),'ARRAY_TAIL')
def check_case(path):
    result=read(path);c=result['parameters'];d=path.parent/'case'
    need(read(d/'input.json')['spec']==c,'INPUT_BINDING')
    for name,h in result['raw_hashes'].items():need(sha(d/name)==h,'FORWARD_RAW_BINDING')
    need(c.get('fault')!='SHARED_HEADER_LOSS','UNREGISTERED_HYDRAULIC_BOUNDARY')
    frames=iter(arrays(d/'source_phases.json'));frame=next(frames,None);pumps=3;n=0;peak=0.
    Q=330/3600;G=9.80665;rho=1009.;eta=c.get('primary_efficiency',.7)
    kp_pid=(rho*G*18-115820)/(110/3600)**2
    for r in arrays(d/'physics.json'):
        while frame is not None and frame['time_ns']<=r['start_ns']:
            pumps=frame['request']['pumps'];frame=next(frames,None)
        v=r['load_valve'];kl=(135920+20000/max(v,.001)**2)/Q**2
        ql=math.sqrt((155920*1.25/.9**2)*.9**2/(kl+155920/Q**2*.25)) if v>1e-9 else 0.
        wet=r['source_path'].startswith('W');dp=96520 if wet else 63210;v=r['source_valve']
        ks=dp*(.8+.2/max(v,.001)**2)/Q**2*(1+c.get('source_extra_dp_kpa',0)/(96.52 if wet else 63.21))
        h0=rho*G*(34*1.2 if c['source_variant']=='V9' else 18)
        kp=(rho*G*34*.2/(115/3600)**2 if c['source_variant']=='V9' else kp_pid)/pumps**2
        qs=math.sqrt(h0*c.get('source_head_factor',1)*r['source_speed']**2/(ks+kp)) if v>1e-9 and r['source_speed']>1e-9 else 0.
        kr=c.get('recharge_dp_kpa',120)*1000/Q**2
        qr=math.sqrt(rho*G*18*c.get('recharge_head_factor',1)*r['recharge_actual_speed']**2/(kr+kp_pid/9)) if r['recharge_actual_speed']>1e-9 else 0.
        for actual,wanted in ((r['load_flow_m3_h'],ql*3600),(r['source_flow_m3_h'],qs*3600),(r['recharge_flow_m3_h'],qr*3600)):near(actual,wanted)
        watts=(ql**3*kl+qs**3*ks+qr**3*kr)/eta
        near(watts,r['primary_pump_electrical_w']);peak=max(peak,watts)
        for tank,t in r['tank_records'].items():
            near(t['load_m3_s'],ql if tank==r['load_tank'] else 0.)
            near(t['source_m3_s'],(qs if tank==r['source_tank'] else 0.)+(qr if tank=='B' else 0.))
        near(sum(u['primary_flow_m3_s'] for u in r['unit_records']),ql)
        n+=1
    need(n==round(c['seconds']/c['dt_s']),'PRIMARY_STEP_COVERAGE')
    return dict(id=result['id'],steps=n,primary_peak_electric_W=peak,physics_sha256=result['raw_hashes']['physics.json'],status='INDEPENDENT_PRIMARY_QH_MASS_AND_PUMP_HEAT_VERIFIED')
def main():
    stage,root_s,out_s=sys.argv[1:];root=Path(root_s);out=Path(out_s)
    need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('RUNNER_OS')=='Windows' and platform.node().upper()!='HIPPO','REMOTE_ONLY')
    write(out/'ready.json',dict(pid=os.getpid()));end=time.monotonic()+25
    while not(out/'release.json').exists():need(time.monotonic()<end,'RELEASE_TIMEOUT');time.sleep(.05)
    p=read(out/'external_job_identity.json');r=read(out/'release.json')
    need(p['actual_python_pid']==os.getpid()==r['actual_python_pid'] and p['in_target_job'] and [p[k] for k in ('cpu_rate','process_mb','job_mb')]==[2500,1024,2048] and r['external_proof_raw_sha256']==sha(out/'external_job_identity.json'),'ACTUAL_JOB')
    need(platform.python_version()=='3.11.9' and os.environ.get('ImageVersion') in ('20261004.326.1','20261012.333.1'),'ENVIRONMENT')
    near(1.,1.);refused=False
    try:near(1.,1.001)
    except ValueError:refused=True
    need(refused,'CORRUPTION_WITNESS')
    indexes=list((root/'full').rglob('artifact_hashes.json'));need(len(indexes)==1,'EXACT_INDEX')
    index=read(indexes[0]);need(index['source_commit']==EXEC,'MODEL_SOURCE')
    base=indexes[0].parent;expected={r['path']:r for r in index['records']}
    persisted=read(base/stage/'result.json')
    need(persisted['stage']==stage and persisted['status']=='PASS' and persisted['environment']['source_commit']==EXEC,'ORIGINAL_STAGE_AUTHORITY')
    files=list((base/stage).rglob('forward_result.json'));need(files,'DYNAMIC_FILES_REQUIRED')
    for path in (base/stage).rglob('*'):
        if path.is_file():
            relative=path.relative_to(base).as_posix();need(relative in expected and sha(path)==expected[relative]['raw_sha256'],'OFFICIAL_INDEX_BINDING')
    results=[check_case(p) for p in files]
    need(len(results)==len(persisted['analysis']['cases']) and {r['id'] for r in results}=={r['id'] for r in persisted['analysis']['cases']},'EXACT_PRIMARY_CASE_COVERAGE')
    need(not any(k.startswith('v0_2') for k in sys.modules),'NO_MODEL_IMPORT')
    write(out/'review.json',dict(stage=stage,source_commit=EXEC,manifest_sha256=MANIFEST,review_commit=os.environ['GITHUB_SHA'],reviewer_sha256=sha(Path(__file__)),pid=os.getpid(),results=results,independent_scope='PRIMARY_QH_TANK_MASS_OWNERSHIP_PUMP_HEAT; existing campaign separately audits HX/secondary/energy/M1',model_rerun=False,status='PASS',formal=False,engineering_approval=False))
if __name__=='__main__':main()
