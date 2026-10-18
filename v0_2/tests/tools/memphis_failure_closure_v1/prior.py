"""Read exact original official raw ZIP, not identities guessed from prose."""
import zipfile,json,hashlib,gc
from pathlib import Path
from .checks import need
from .requirements import save,csvout
def run(directory):
    root=Path(__file__).resolve().parents[4];path=root/'artifacts/memphis-failure-closure-v1-prior/official-robust.zip'
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    need(h.hexdigest()=='6103ea42e1b0746991c021a95a664fe212805d0e0e654a23da6785fa529f1e55','ORIGINAL_OFFICIAL_ZIP_SHA')
    zip_sha=h.hexdigest()
    records=[];failures=[]
    with zipfile.ZipFile(path) as z:
        index_name=next(n for n in z.namelist() if n.endswith('/artifact_hashes.json'));index=json.loads(z.read(index_name));base=index_name[:-len('artifact_hashes.json')]
        need(index['source_commit']=='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb','ORIGINAL_SOURCE')
        for rec in index['records']:
            hh=hashlib.sha256()
            with z.open(base+rec['path']) as stream:
                for b in iter(lambda:stream.read(1048576),b''):hh.update(b)
            need(hh.hexdigest()==rec['raw_sha256'],'ORIGINAL_RAW_HASH')
        names=[n for n in z.namelist() if n.endswith('/forward_result.json')]
        need(len(names)==34,'TWO_EXACT17_REGISTRIES')
        for n in names:
            r=json.loads(z.read(n));c=r['parameters'];case=n[:-len('forward_result.json')]+'case/'
            row=dict(id=r['id'],status=r['status'],maximum_inlet_C=r['max_inlet_C'],maximum90_inlet_C=r['max90_inlet_C'],minimum_load_m3_h=r['actual_load_min_m3_h'],cold_return_delay_s=r['cold_return_delay_s'],parameters=c,raw_sha256=r['raw_hashes'],source_commit=index['source_commit'])
            row['stuck_valve_excitation']='NOT_DEMANDED' if c.get('load_valve_stuck') and not any(e.get('load')=='B' for e in r['diagnosis']['actual_selector_events']) else 'SEE_PHYSICAL_EVENTS'
            records.append(row)
            if r['status']=='CONDITIONALLY_FEASIBLE':continue
            physics=json.loads(z.read(case+'physics.json'));frames=json.loads(z.read(case+'source_phases.json'))
            for key,h in r['raw_hashes'].items():need(hashlib.sha256(z.read(case+key)).hexdigest()==h,'ORIGINAL_FOUR_TRACE_HASH')
            first=lambda test:next((p['end_ns']/1e9 for p in physics if test(p)),None)
            temp=lambda p:max(max(u['new_k'][1:7])-273.15 for u in p['unit_records'])
            codes=sorted({code for f in frames for code in f['safety']['data']['codes']})
            classes=[]
            if c.get('capacity_scale',1)<1:classes+=['A_HEAT_REJECTION_SHORTFALL']
            if c.get('source_head_factor',1)<1:classes+=['D_PUMP_NETWORK_SHORTFALL']
            if c.get('sensor_delay_s',.1)>1:classes+=['H_OBSERVATION_STALE_F_RESTRICTION']
            if c.get('second_source_failure'):classes+=['G_REDUNDANCY_LOSS_OWNER_DESIGN_BASIS_PENDING']
            if c.get('standby_initial_c',40.5)>41.6:classes+=['B_WARM_PIPE_AND_JOINT_PARAMETER_INTERACTION']
            timeline=[dict(time_s=p['end_ns']/1e9,temp_C=temp(p),load_m3_h=p['load_flow_m3_h'],source_m3_h=p['source_flow_m3_h'],cold_A_m3=p['tank_A_cold_m3'],cold_B_m3=p['tank_B_cold_m3'],source=p['source_path'],source_speed=p['source_speed'],source_valve=p['source_valve'],load_valve=p['load_valve'],rejected_kW=p['rejected_w']/1000) for p in physics if p['end_ns']%1_000_000_000==0]
            failures.append(dict(**row,classifications=classes,first_thermal_s=first(lambda p:temp(p)>45),first_load_shortfall_s=first(lambda p:p['load_flow_m3_h']<330-1e-8),
                first_source_shortfall_s=first(lambda p:p['source_flow_m3_h']<330-1e-8),first_stale_s=next((f['time_ns']/1e9 for f in frames if 'SOURCE_SENSOR_STALE' in f['safety']['data']['codes']),None),
                cold_inventory_initial={k:physics[0]['tank_'+k+'_cold_m3'] for k in ('A','B')},cold_inventory_final={k:physics[-1]['tank_'+k+'_cold_m3'] for k in ('A','B')},
                maximum_actual_rejected_kW=max(p['rejected_w'] for p in physics)/1000,codes=codes,events=r['diagnosis']['source_events'],timeline=timeline,
                inject_times='capacity/head/measurement variations exist fromt0;W1 loss30s;W2 second loss60s when registered;not all injections start30s',
                numerical_scope='80layer0.1s legacy point; whole joint uncertainty not proven'))
            del physics,frames;gc.collect()
    for prefix in ('ROBUST_B15','ROBUST_C20'):
        need(sum(r['id'].startswith(prefix) for r in records)==17 and sum(r['id'].startswith(prefix) for r in failures)==5,'EXACT_FIVE_FAILS_PER17')
    save(directory/'original17_traceability.json',records);save(directory/'original_five_failures.json',failures)
    csvout(directory/'original17_traceability.csv',[{**{k:v for k,v in r.items() if k not in ('parameters','raw_sha256')},'parameters':json.dumps(r['parameters'],sort_keys=True),'raw_sha256':json.dumps(r['raw_sha256'],sort_keys=True)} for r in records])
    return dict(kind='prior',records=records,failures=failures,official_zip_sha256=zip_sha,verified_original_raw_files=len(index['records']))
