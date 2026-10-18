"""Remote, streaming, pure-file independent review. NEVER imports the model."""
import os,sys,json,time,hashlib,zlib,re,gc,math
from pathlib import Path

EXEC='6031e0ef7d32bec0109f328f85ebd5dfef8fe048'
MANIFEST='5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16'
def need(ok,why):
    if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False),encoding='utf-8')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def arrays(p):
    """Decode one array element at a time; never retain an 87MB JSON tree."""
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
                need(not eof,'TRUNCATED_JSON_ARRAY');more()
        more();need(token()=='[','ARRAY_ROOT');pos+=1
        if token()==']':pos+=1
        else:
            while True:
                token()
                while True:
                    try:value,end=dec.raw_decode(buf,pos);break
                    except json.JSONDecodeError:
                        need(not eof,'MALFORMED_JSON_ELEMENT');more()
                pos=end;yield value
                c=token();pos+=1
                if c==']':break
                need(c==',','ARRAY_SEPARATOR')
        while not eof:more()
        need(not buf[pos:].strip(),'JSON_UNREGISTERED_TAIL')
def near(a,b,scale=None,ops=4096):
    s=abs(a)+abs(b) if scale is None else scale
    need(abs(a-b)<=ops*2**-53/(1-ops*2**-53)*max(1,s),'NUMERIC_RECOMPUTATION')
def source_ready(s,q):return s['source_available'][s['source_path']] and s['source_flow_m3_h']>=q-1e-8 and s['source_return_k']<=314.5948
def stored(r):
    cv=1009*4000;v=[.1]+[.025]*6+[.15]*6+[.15]
    total=math.fsum(cv*x*t for u in r['units'] for x,t in zip(v,[u['supply_header_k'],*u['inlet_k'],*u['rack_return_k'],u['return_k']]))
    total+=math.fsum(cv*15/len(r[k])*t for k in ('tank_A_k','tank_B_k') for t in r[k])
    return total+math.fsum(cv*2.75/len(ts)*t for ts in r['source_pipe_k'].values() for t in ts)
def energy(d,spec,a):
    kind=spec['kind'];rows=read(d/'case/series.json') if kind!='buffer' else None
    path=d/'buffer_steps.json' if kind=='buffer' else d/'case/physics.json'
    c=read(d/'case/input.json')['config'] if kind=='unit' else None
    initial=stored(rows[0]) if kind=='group' else None;previous=initial
    heat=pump=reject=0.;count=0;peak=-math.inf;peak90=-math.inf;first330=first264=None;terminal=True
    tail_end=rows[-1]['time_ns'] if rows else 90e9
    for s in arrays(path):
        count+=1
        if kind=='buffer':
            cap=1009*4000*15/len(s['old_k']);old=math.fsum(t*cap for t in s['old_k']);new=math.fsum(t*cap for t in s['new_k'])
            if count==1:initial=old;start_t=s['old_k'][0];prior_time=0.
            dt=s['end_s']-prior_time;prior_time=s['end_s'];h=1009*4000*s['load_m3_s']*(s['return_k']-s['old_k'][0])*dt;p=x=0.
            near(s['load_m3_s']*3600,330);need(s['source_m3_s']==0 and s['return_k']==321.44 and s['pump_loss_w']==0,'BUFFER_BOUNDARY')
            peak=max(peak,s['new_k'][0]-start_t)
        elif kind=='unit':
            dt=(s['end_ns']-s['start_ns'])/1e9;caps=[c['density_kg_m3']*c['cp_j_kg_k']*v for v in c['volumes_m3']]
            old=math.fsum(t*v for t,v in zip(s['old_k'],caps));new=math.fsum(t*v for t,v in zip(s['new_k'],caps))
            if count==1:initial=old
            h=.95*math.fsum(s['rack_it_w'])*dt;p=s['pump_electrical_w']*dt;x=s['hx_w']*dt
            near(math.fsum(s['branch_flows_m3_s']),s['flow_m3_s'])
            for t,u,cap,rate in zip(s['old_k'],s['new_k'],caps,s['rates_w']):near((u-t)*cap,dt*rate,abs(u*cap)+abs(t*cap)+abs(dt*rate))
            near(math.fsum(s['rates_w']),h/dt+p/dt-x/dt,math.fsum(abs(v) for v in s['rates_w'])+abs(h/dt)+abs(p/dt)+abs(x/dt))
            peak=max(peak,s['new_k'][0]-273.15)
        else:
            dt=(s['end_ns']-s['start_ns'])/1e9;old=previous;new=s['stored_j'];h=2650500*dt;p=(s['primary_pump_electrical_w']+s['secondary_pump_electrical_w'])*dt;x=s['rejected_w']*dt
            mx=max(max(u['new_k'][1:7])-273.15 for u in s['unit_records']);peak=max(peak,mx)
            if 30e9<s['end_ns']<=120e9:peak90=max(peak90,mx)
            if s['start_ns']>=30e9:
                if first330 is None and source_ready(s,330):first330=s['end_ns']/1e9-30
                if first264 is None and source_ready(s,264):first264=s['end_ns']/1e9-30
            if s['end_ns']>tail_end-5e9:terminal=terminal and source_ready(s,330)
            if count>1:
                if (prior['source_tank'],prior['source_path'])!=(s['source_tank'],s['source_path']):need(max(prior['source_supply_valve'],prior['source_return_valve'],prior['source_speed'],s['source_speed'])<=1e-9,'SOURCE_PRE_SELECTION_CUT')
                if prior['load_tank']!=s['load_tank']:need(max(s['load_supply_valve'],s['load_return_valve'])<=1e-9,'LOAD_AB_ISOLATION')
            prior=s
        near(new-old,h+p-x,abs(new)+abs(old)+abs(h)+abs(p)+abs(x));previous=new;heat+=h;pump+=p;reject+=x
    if kind=='group':near(previous,stored(rows[-1]));peak=max(peak,max(max(u['inlet_k'])-273.15 for r in rows for u in r['units']))
    if kind=='unit':peak=max(peak,rows[0]['supply_k']-273.15);need(count==c['duration_ns']//c['dt_ns'] and len(rows)==count+1,'PHYSICS_COVERAGE')
    near(previous-initial,heat+pump-reject,abs(previous)+abs(initial)+heat+pump+abs(reject),8192*(count+1))
    grade='PASS' if peak<=(.5 if kind=='buffer' else 45) else 'FAIL'
    near(peak,a['maximum_outlet_rise_K' if kind=='buffer' else 'maximum_inlet_c']);need(a['grades']['90_SECOND_BUFFER_COMPLIANCE' if kind=='buffer' else 'RACK_THERMAL_COMPLIANCE']==grade,'HIDDEN_THERMAL_FAILURE')
    if kind=='buffer':need(prior_time==90,'BUFFER_HORIZON')
    if kind=='group':
        near(peak90,a['first90_maximum_inlet_c']);fault=bool(spec.get('fault'));expected=first330 if fault else None
        need(a['first_cold_return_330_delay_s']==expected and a['historical_264_threshold_delay_s']==(first264 if fault else None),'POST_FAULT_RETURN_CUT')
        need(a['terminal_source_recovery_maintained']==terminal,'SECOND_FAILURE_HIDDEN')
        recovery='INCOMPLETE' if not fault else 'PASS' if expected is not None and expected<=90 and terminal else 'FAIL'
        need(a['grades']['FAILOVER_RECOVERY']==recovery,'RECOVERY_GRADE')
    return dict(steps=count,maximum=peak,residual_j=previous-initial-heat-pump+reject,heat_j=heat,pump_j=pump,rejected_j=reject)
def plots(d,spec,report):
    if spec['kind'] not in ('unit','group'):return 0
    actual=report['plots'][spec['id']];i=0
    for r in arrays(d/'case/series.json'):
        if spec['kind']=='unit':
            if r['time_ns']%1000000000:continue
            e=dict(t=r['time_ns']/1e9,inlet=r['supply_k']-273.15,outlet=max(r['rack_return_k'])-273.15,mixed=r['return_k']-273.15,flow=r['flow_m3_s']*3600,head=r['dp_pa']/1000,main=r['main_speed'],backup=r['backup_speed'],cdu=r['active_cdu'],valve=r['valve_opening'])
        else:e=dict(t=r['time_ns']/1e9,inlet=max(max(u['inlet_k']) for u in r['units'])-273.15,primary=r['primary_inlet_c'],flow=r['source_flow_m3_h'],A=r['cold_A_m3'],B=r['cold_B_m3'],load=r['actual_load_selector'],valve=r['actual_load_valve'],sourceSpeed=r['source_actual_speed'],state=r['source_state'])
        need(actual[i]==e,'PLOT_NOT_ACTUAL_PHYSICS');i+=1
    need(i==len(actual),'PLOT_COVERAGE');return i
def phases_and_journals(base):
    count=frames=0
    for p in base.rglob('phases.json'):
        prev={};latch=set()
        for r in arrays(p):
            u=r.get('unit',0);m=r['PRE']['measurement'];safe=r['SAFETY'];plc=r['PLC'];post=r['POST']
            need(m['sample_ns']<=m['release_ns']<=r['time_ns'],'FUTURE_OBSERVATION')
            need(digest(r['PRE'])==r['immutable_pre_digest']==safe['pre_digest'] and digest(safe)==r['immutable_safety_digest']==plc['safety_digest'],'IMMUTABILITY')
            need(post['plc_id']==plc['record_id'] and post['pre_id']==r['PRE']['record_id'] and r['actuator_command']['producer_module']=='PLC','PLC_BINDING')
            if u in prev:need(r['PRE']['old_command']['value']==prev[u]['command'] and r['PRE']['old_command']['issue_ns']==prev[u]['issue_ns'],'FUTURE_COMMAND')
            if u in latch:need(safe['severity']=='FAULT','LATCH_CLEARED')
            if safe['severity']=='FAULT':latch.add(u)
            prev[u]=plc;count+=1
    for ix in base.rglob('m1_*_index.json'):
        data=ix.with_name(ix.name.replace('_index.json','.zlib'))
        if not data.exists():continue
        with data.open('rb') as f:
            for r in arrays(ix):
                need(f.tell()==r['offset'] and r['compression']=='zlib','JOURNAL_LAYOUT')
                blob=f.read(r['stored_bytes']);need(len(blob)==r['stored_bytes'],'TRUNCATED_JOURNAL')
                raw=zlib.decompress(blob);need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['raw_sha256'],'JOURNAL_RAW_HASH');frames+=1
            need(f.read(1)==b'','JOURNAL_EXTRA_TAIL')
    need(count==frames,'PHASE_JOURNAL_COVERAGE');return count,frames
def group_review(root,group,repo):
    base=next(p.parent for p in (root/'full').rglob('artifact_hashes.json'));inv=read(base/'artifact_hashes.json')
    need(inv['source_commit']==EXEC and inv['group']==group,'RAW_SOURCE')
    manifest=next((root/'full').rglob('source_manifest.json'));need(sha(manifest)==MANIFEST,'RAW_MANIFEST')
    for b in inv['records']:
        p=(base/b['path']).resolve();need(p.is_relative_to(base.resolve()),'PATH_ESCAPE');need(p.stat().st_size==b['bytes'] and sha(p)==b['raw_sha256'],'RAW_FILE_HASH')
    reg=read(repo/'v0_2/tests/tools/memphis_equipment_validation_v2/registration.json');report=read(root/'consolidated_report.json')
    out=dict(group=group,source_commit=EXEC,raw_files=len(inv['records']),stages=[],energy=[],plots=0,unchanged_physics=0,inputs={},physics_hashes={},timeline=[])
    prior={b['path']:b['raw_sha256'] for b in read(root/'prior_inventory.json')['records']}
    envreg=read(base/'environment_registration.json');need(envreg['commit']==EXEC and envreg['manifest_raw_sha256']==MANIFEST and [envreg[k] for k in ('cpu_rate','process_mb','job_mb','wall_seconds')]==[2500,1024,2048,480],'RESOURCE_REGISTRATION')
    for spec in reg['cases']:
        if spec['group']!=group:continue
        d=base/spec['id'];r=read(d/'result.json');proof=read(d/'external_job_identity.json');ready=read(d/'ready.json');release=read(d/'release.json');status=read(d/'job_status.json');env=r['environment']
        need(r['status']=='PASS' and r['stage']==spec['id'] and r['pid']==ready['pid']==proof['actual_python_pid']==release['actual_python_pid'],'ACTUAL_PYTHON_PID')
        need(proof['in_target_job'] and [proof[k] for k in ('cpu_rate','process_mb','job_mb')]==[2500,1024,2048] and status['assigned_before_resume'] and status['cleanup_complete'] and status['active_after_cleanup']==status['child_exitcode']==0 and status['outcome']=='EXITED','JOB_CLEANUP')
        ph=sha(d/'external_job_identity.json');need(release['external_proof_raw_sha256']==ph==env['job_proof_sha256'],'RELEASE_PROOF')
        need(env==r['environment_after'] and env['source_commit']==EXEC and env['python']=='3.11.9' and env['image'] in ('20261004.326.1','20261012.333.1') and env['dependencies']==dict(numpy='2.4.6',pytest='9.1.1',jsonschema='4.26.0'),'ENVIRONMENT')
        a=read(d/'independent_analysis.json');need(a==r['analysis']==next(s['analysis'] for s in report['stages'] if s['stage']==spec['id']),'REPORT_ANALYSIS')
        if spec['kind'] in ('unit','group','buffer'):
            out['energy'].append(dict(case=spec['id'],recomputed=energy(d,spec,a)));out['plots']+=plots(d,spec,report)
            for name in ('case/series.json','case/physics.json') if spec['kind']!='buffer' else ('buffer_steps.json',):
                rawhash=sha(d/name);need(rawhash==prior[spec['id']+'/'+name],'AUDIT_ONLY_CHANGE_ALTERED_PHYSICS');out['unchanged_physics']+=1;out['physics_hashes'][spec['id']+'/'+name]=rawhash
        if spec['kind']=='unit':
            fault=fast=None
            for f in arrays(d/'case/phases.json'):
                if fault is None and f['SAFETY']['severity']=='FAULT':fault=f['time_ns']/1e9
                if fast is None and 'FAST_LOW_FLOW' in f.get('fast_permission',{}).get('data',{}).get('codes',[]):fast=f['time_ns']/1e9
            event=lambda name:next((e['time_ns']/1e9 for e in a['events'] if e['event']==name),None)
            out['timeline'].append(dict(case=spec['id'],first_safety_fault_s=fault,first_fast_low_flow_s=fast,M1_confirmed_s=a['causal']['tracking_confirmed_s'],backup_requested_s=event('BACKUP_REQUESTED'),backup_started_s=event('BACKUP_STARTED'),flow_recovered_s=a['flow_recovered_s'],pressure_recovered_s=a['pressure_recovered_s'],temperature_recovered_s=a['temperature_recovered_s'],terminal_recovery_maintained=a['terminal_recovery_maintained'],full_load_continuity=a['grades']['FULL_LOAD_CONTINUITY']))
        if spec['kind']=='group':
            prev=None
            for f in arrays(d/'case/source_phases.json'):
                o=f['measurement'];q=f['request'];need(o['sample_ns']<=o['release_ns']<=f['time_ns'] and q['permission']==f['safety']['sha256']==f['PLC']['data']['safety_sha256'] and q['observation_id']==o['record_id']==f['PLC']['data']['measurement_id'],'SOURCE_PLC_BINDING')
                if prev and prev['load_tank']!=q['load_tank'] and q['load_tank']=='B' and not o['leak_A']:
                    reserve=sum(5 for x,y in zip(o['tank_B_tt_k'],o['tank_B_tt_k'][1:]) if x<=314.5948 and y<=314.5948)
                    need(reserve>=8.25 and f['time_ns']-o['sample_ns']<=1e9 and o['maximum_secondary_inlet_c']>=44.5,'B_MEASURED_RESERVE')
                prev=q
            if spec['id'] in ('G_B_WARM','G_VALVE_STUCK'):need(not a['actual_AB_switches'],'INVALID_B_ACCEPTED')
        if spec['id'] in ('BASELINE','NEGATIVE'):
            n=12 if spec['id']=='BASELINE' else 31;m=re.findall(r'^([.]+)\s+\[100%\]\s*$',(d/'stdout.raw').read_text(),re.M);need(len(m)==1 and len(m[0])==n,'PYTEST_ACTUAL_COVERAGE')
        ip=d/'case/input.json'
        if ip.exists():out['inputs'][spec['id']]=sha(ip)
        out['stages'].append(dict(stage=spec['id'],actual_python_pid=r['pid'],environment=env,result_raw_sha256=sha(d/'result.json'),job_proof_raw_sha256=ph,cleanup_raw_sha256=sha(d/'job_status.json'),active_after_cleanup=0,child_exitcode=0))
        gc.collect();print('INDEPENDENT_STAGE_VERIFIED',spec['id'],flush=True)
    out['phases'],out['journal_frames']=phases_and_journals(base);return out
def final_review(root,repo):
    import zipfile
    reg=read(repo/'v0_2/tests/tools/memphis_equipment_validation_v2/registration.json');groups=[read(p) for p in (root/'group-results').rglob('review.json')]
    need({g['group'] for g in groups}=={s['group'] for s in reg['cases']} and len(groups)==7,'EXACT_REVIEW_GROUPS')
    stages=[s for g in groups for s in g['stages']];need(len(stages)==50 and {s['stage'] for s in stages}=={s['id'] for s in reg['cases']},'EXACT_STAGE_COVERAGE')
    need(all(g['review_execution_commit']==os.environ['GITHUB_SHA'] and g['verifier_raw_sha256']==sha(Path(__file__)) for g in groups),'REVIEW_SOURCE_IDENTITY')
    physical={k:v for g in groups for k,v in g['physics_hashes'].items()}
    for f in ('series.json','physics.json'):need(physical['SIX_REPEAT/case/'+f]==physical['SIX_UA220/case/'+f],'FRESH_REPEAT')
    need(sum(g['unchanged_physics'] for g in groups)==82,'UNCHANGED_PHYSICS_COVERAGE')
    for d in (root/'group-results').rglob('job_status.json'):
        s=read(d);need(s['cleanup_complete'] and s['active_after_cleanup']==s['child_exitcode']==0 and s['outcome']=='EXITED','REVIEW_GROUP_CLEANUP')
    need(len(list((root/'group-results').rglob('job_status.json')))==7,'REVIEW_GROUP_JOB_COUNT')
    index=read(root/'official_artifact_index.json');prep=read(root/'prepared_receipt.json');all_zips=list(prep['verified_current_zips'])
    for p in (root/'group-results').rglob('download_receipt.json'):all_zips.append(read(p)['current_zip'])
    expected={a['name']:a['digest'] for a in index['artifacts']};actual={a['name']:a['digest'] for a in all_zips};need(actual==expected and len(actual)==15,'ALL_OFFICIAL_ZIPS')
    with zipfile.ZipFile(root/'raw_logs.zip') as z:logs='\n'.join(z.read(n).decode('utf-8-sig') for n in z.namelist() if not n.endswith('/'))
    for s in reg['cases']:need('INTEGRATION_STAGE_END '+s['id']+' PASS' in logs,'RAW_STAGE_END')
    need('EQUIPMENT_REPORT_COMPLETE 50' in logs,'RAW_REPORT_END')
    source=read(root/'source_closure.json');inputs={k:v for g in groups for k,v in g['inputs'].items()};energy_rows=[s for g in groups for s in g['energy']]
    result=dict(status='OFFICIAL_ARTIFACT_AND_PERSISTED_EVIDENCE_VERIFIED',source_commit=EXEC,manifest_raw_sha256=MANIFEST,review_execution_commit=os.environ['GITHUB_SHA'],verifier_raw_sha256=sha(Path(__file__)),source_bindings=source['source_bindings'],unique_source_files=len(source['source_file_raw_sha256']),official_zips=15,raw_files=sum(g['raw_files'] for g in groups),stage_count=50,groups=7,pytest_counts=dict(BASELINE=12,NEGATIVE=31),verified_plot_points=sum(g['plots'] for g in groups),unchanged_physics_files_vs_build4=82,phases=sum(g['phases'] for g in groups),journal_frames=sum(g['journal_frames'] for g in groups),images=sorted({s['environment']['image'] for s in stages}),input_raw_hashes=inputs,independent_energy=energy_rows,raw_logs_sha256=sha(root/'raw_logs.zip'),report_raw_sha256=sha(root/'consolidated_report.json'),repeat='BYTE_IDENTICAL_SERIES_AND_PHYSICS',engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',hardware='CALIBRATION_REQUIRED',formal=False,phase6=False)
    write(root/'independent_verification.json',result)
    write(root/'remote_causal_timeline.json',[s for g in groups for s in g['timeline']])
    write(root/'source_input_environment_manifest.json',dict(schema='MEMPHIS-V2-SOURCE-INPUT-ENVIRONMENT-CLOSURE',source_commit=EXEC,run_id=39088951176,run_attempt=1,source_manifest_raw_sha256=MANIFEST,candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce',source_file_raw_sha256=source['source_file_raw_sha256'],customer_document_raw_sha256=reg['input_hashes'],customer_local_hash_receipt=read(repo/'artifacts/memphis-equipment-v2-review/local_original_hashes.json'),scenario_input_raw_sha256=inputs,stages=stages,official_artifacts=index['artifacts'],raw_logs_sha256=result['raw_logs_sha256'],review_source_commit=os.environ['GITHUB_SHA']))
    return result
def main():
    need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('RUNNER_OS')=='Windows','REMOTE_ONLY')
    stage,root_s,out_s=sys.argv[1:];root=Path(root_s);out=Path(out_s);out.mkdir(exist_ok=True);write(out/'ready.json',dict(pid=os.getpid(),runtime='Python3.11.9-pure-file-review'))
    limit=time.monotonic()+30
    while not (out/'release.json').exists():need(time.monotonic()<limit,'REVIEW_RELEASE_TIMEOUT');time.sleep(.05)
    proof=read(out/'external_job_identity.json');release=read(out/'release.json');need(proof['actual_python_pid']==os.getpid()==release['actual_python_pid'] and proof['in_target_job'] and [proof[k] for k in ('cpu_rate','process_mb','job_mb')]==[2500,1024,2048] and release['external_proof_raw_sha256']==sha(out/'external_job_identity.json'),'REVIEW_ACTUAL_JOB')
    need(sys.version.split()[0]=='3.11.9','REVIEW_PYTHON_VERSION')
    original=sha(Path(__file__));result=final_review(root,Path.cwd()) if stage=='FINAL' else group_review(root,stage,Path.cwd())
    need(sha(Path(__file__))==original and not any(k.startswith('v0_2') for k in sys.modules),'REVIEW_SOURCE_OR_MODEL_IMPORT')
    result['review_execution_commit']=os.environ['GITHUB_SHA'];result['verifier_raw_sha256']=original;result['review_pid']=os.getpid();result['review_job_proof_sha256']=sha(out/'external_job_identity.json');write(out/'review.json',result)
if __name__=='__main__':main()
