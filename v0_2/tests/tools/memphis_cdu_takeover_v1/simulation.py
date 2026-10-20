"""One physical clock, two delayed observation lanes and six unchanged M1 engines."""
import json,csv,gc
from dataclasses import asdict
from math import fsum
from pathlib import Path
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import CV,check,rounding_bound
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.streaming import StreamArray
from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.scheduler import MeasurementView
from v0_2.tests.tools.m1_engine_v3.stream_trace import CompletedJournal,read_row
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import IntegrationPLC
from .unit import DualUnit
from .plant import Plant
from .control import RecoveryController,CDUController,CDUPLC,control_options,ProjectProtection,SourcePLC
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,separators=(',',':'))

def run(c,d):
    d.mkdir();save(d/'input.json',c)
    units=[DualUnit(c,i) for i in range(3)];plant=Plant(c)
    for u in units:u.advance(0,0,[313.65+155920/.7/CV,313.65],[110/3600,0.],[155920,0.])
    source_controller=RecoveryController(control_options(c));protection=ProjectProtection(control_options(c));source_plc=SourcePLC();controller=CDUController();cdu_plc=CDUPLC()
    initial=dict(source_tank='A',source_path='W1',source_enable=True,source_valve=1.,pumps=3,recharge_enable=False,fan=.82308,load_tank='A',rc_tank='B',rc_valve=0.)
    issued=dict(data=dict(request=initial),scope='INITIAL_CONDITION_NOT_PLC_EXECUTION_PROOF')
    valves=controller.primary,controller.secondary;pump_commands=[[.9,0.] for _ in range(3)]
    profile=json.loads((ROOT/'phase5_r5_2_2_fixture_tracking_profile.json').read_bytes());classifier=json.loads((ROOT/'phase5_r5_2_silent_tracking_fault_registration.json').read_bytes())['classifier']
    engines=[SplitEngine(profile,classifier) for _ in range(6)];plcs=[IntegrationPLC(.9 if k%2==0 else 0.) for k in range(6)]
    journals=[CompletedJournal(d/f'm1_{i}.zlib') for i in range(6)]
    for e,j in zip(engines,journals):e._completed=j
    phys=StreamArray(d/'physics.json');transactions=StreamArray(d/'m1_transactions.json');sf=StreamArray(d/'source_frames.json');cf=StreamArray(d/'cdu_frames.json')
    timeline=(d/'timeline.csv').open('x',encoding='utf-8',newline='');ports=(d/'tank_ports.csv').open('x',encoding='utf-8',newline='');cw=pw=None
    pending_source=[];pending_cdu=[];last_source=None;last_cdu=None;last_sid=None
    dt_ns=round(c['dt_s']*1e9);duration=round(c['seconds']*1e9);initial_energy=plant.energy()+fsum(u.energy() for u in units)
    energy=dict(initial_J=initial_energy,liquid_J=0.,pump_J=0.,source_J=0.,ambient_J=0.);maximum_residual=maximum_tank=0.
    curves=[];samples=[];pre_second=None;last=None;witnesses=dict(B_command_s=None,B_flow_s=None,B_cold_return_s=None,B_inventory_increase_s=None,B_net_source_J=0.,B_load_volume_m3=0.,A_CDU_heat_J=0.,B_CDU_heat_J=0.,B_load_port_heat_J=0.,B_initial_cold_m3=plant.tanks['B'].cold_volume(),B_min_cold_m3=plant.tanks['B'].cold_volume())
    metrics=[dict(max_C=-1e9,min_primary=1e9,min_secondary=1e9,first90_max_C=-1e9,first90_min_primary=1e9,first90_min_secondary=1e9,second90_max_C=None,second90_min_primary=None,second90_min_secondary=None,secondary_deficit_m3=0.) for _ in units]
    first_cross={};m1_faults=[False]*6
    try:
        for now in range(0,duration+dt_ns,dt_ns):
            if now:
                for i,u in enumerate(units):u.actuate(c['dt_s'],pump_commands[i],(controller.primary[i],controller.secondary[i]))
                last=plant.advance_dual(now-dt_ns,now,units,issued);phys.append(last)
                energy['liquid_J']+=2650500*c['dt_s'];energy['pump_J']+=last['pump_W']*c['dt_s'];energy['source_J']+=last['source_W']*c['dt_s'];energy['ambient_J']+=last['ambient_W']*c['dt_s']
                maximum_residual=max(maximum_residual,abs(last['energy_residual_J']))
                for name,rec in last['tank_records'].items():
                    old=rec['old_k'];new=rec['new_k'];fl=rec['load_m3_s'];fs=rec['source_m3_s'];cap=plant.tanks[name].cap
                    net=CV*(fl*(rec['return_k']-old[0])+fs*(rec['source_in_k']-old[-1]))+rec['environment_heat_w']
                    delta=cap*(fsum(new)-fsum(old));res=delta-c['dt_s']*net;maximum_tank=max(maximum_tank,abs(res))
                    check(abs(res)<=rounding_bound(cap*fsum(new),cap*fsum(old),c['dt_s']*net,operations=2048),'INDEPENDENT_TANK_PORT_ENERGY')
                    row=dict(time_s=now/1e9,tank=name,load_out_kg_s=fl*1009,load_return_kg_s=fl*1009,source_out_kg_s=fs*1009,source_return_kg_s=fs*1009,
                        load_out_C=old[0]-273.15,load_return_C=rec['return_k']-273.15,source_out_C=old[-1]-273.15,source_return_C=rec['source_in_k']-273.15,
                        load_net_W=CV*fl*(rec['return_k']-old[0]),source_net_W=CV*fs*(rec['source_in_k']-old[-1]),ambient_W=rec['environment_heat_w'],delta_U_J=delta,residual_J=res,
                        cold_m3=plant.tanks[name].cold_volume(),extractable_to_41_4448_MJ=CV*plant.tanks[name].volume/plant.tanks[name].n*fsum(max(0,314.5948-t) for t in new)/1e6,profile_bottom_to_top_C=json.dumps([x-273.15 for x in new]))
                    if pw is None:pw=csv.DictWriter(ports,fieldnames=list(row));pw.writeheader()
                    pw.writerow(row)
                for i,r in enumerate(last['unit_records']):
                    m=metrics[i];peak=max(r['rack_inlet_C']);primary=fsum(x['primary_m3_h'] for x in r['cdu']);secondary=r['secondary_total_m3_h']
                    m['max_C']=max(m['max_C'],peak);m['min_primary']=min(m['min_primary'],primary);m['min_secondary']=min(m['min_secondary'],secondary)
                    m['secondary_deficit_m3']+=max(0,68.37-secondary)*c['dt_s']/3600
                    if c['fault_at_s']<now/1e9<=c['fault_at_s']+90:
                        m['first90_max_C']=max(m['first90_max_C'],peak);m['first90_min_primary']=min(m['first90_min_primary'],primary);m['first90_min_secondary']=min(m['first90_min_secondary'],secondary)
                    second=c.get('second_fault_at_s')
                    if second is not None and second<now/1e9<=second+90:
                        m['second90_max_C']=max(m['second90_max_C'] or -1e9,peak);m['second90_min_primary']=min(m['second90_min_primary'] if m['second90_min_primary'] is not None else 1e9,primary);m['second90_min_secondary']=min(m['second90_min_secondary'] if m['second90_min_secondary'] is not None else 1e9,secondary)
                    for label,t in [('tank_A_out',last['tank_records']['A']['old_k'][0]-273.15),('tank_B_out',last['tank_records']['B']['old_k'][0]-273.15),('source_out',last['source_cold_C']),('primary_in',r['cdu'][0]['primary_inlet_C']),('standby_secondary_out',r['cdu'][1]['secondary_outlet_C']),('rack',peak)]:
                        if t>45:first_cross.setdefault(f'U{i}_{label}',now/1e9)
                w=witnesses;w['B_load_volume_m3']+=last['primary_B_m3_h']*c['dt_s']/3600;w['B_min_cold_m3']=min(w['B_min_cold_m3'],last['tank_B_cold_m3'])
                w['A_CDU_heat_J']+=fsum(u['cdu'][0]['hx_W'] for u in last['unit_records'])*c['dt_s'];w['B_CDU_heat_J']+=fsum(u['cdu'][1]['hx_W'] for u in last['unit_records'])*c['dt_s']
                rb=last['tank_records']['B'];w['B_load_port_heat_J']+=CV*rb['load_m3_s']*(rb['return_k']-rb['old_k'][0])*c['dt_s']
                if last['source_tank']=='B' and last['source_flow_m3_h']>1e-8:
                    if w['B_flow_s'] is None:w['B_flow_s']=now/1e9
                    w['B_net_source_J']+=CV*last['source_flow_m3_h']/3600*(last['source_return_C']-(last['tank_records']['B']['old_k'][-1]-273.15))*c['dt_s']
                    if last['source_return_C']<=41.4448 and w['B_cold_return_s'] is None:w['B_cold_return_s']=now/1e9
                    if last['tank_B_cold_m3']>w['B_min_cold_m3']+1e-8 and w['B_inventory_increase_s'] is None:w['B_inventory_increase_s']=now/1e9
                if now%1_000_000_000==0:
                    row=dict(time_s=now/1e9,source_tank=plant.source_tank,source_path=plant.source_path,source_m3_h=last['source_flow_m3_h'],source_C=last['source_cold_C'],source_return_C=last['source_return_C'],source_valve=last['source_valve'],source_head_pa=last['source_head_pa'],cold_A_m3=last['tank_A_cold_m3'],cold_B_m3=last['tank_B_cold_m3'],source_state=source_controller.state,pump_W=last['pump_W'],source_W=last['source_W'])
                    for i,r in enumerate(last['unit_records']):
                        row.update({f'U{i}_rack_C':max(r['rack_inlet_C']),f'U{i}_primary_m3_h':fsum(x['primary_m3_h'] for x in r['cdu']),f'U{i}_secondary_m3_h':r['secondary_total_m3_h'],f'U{i}_state':controller.state[i]})
                        for tag,cd in zip(('A','B'),r['cdu']):
                            for key in ('primary_m3_h','secondary_m3_h','primary_valve','secondary_valve','speed','hx_W','primary_inlet_C','primary_outlet_C','secondary_inlet_C','secondary_outlet_C'):row[f'U{i}_{tag}_{key}']=cd[key]
                    if cw is None:cw=csv.DictWriter(timeline,fieldnames=list(row));cw.writeheader()
                    cw.writerow(row);curves.append(row)
                if now%300_000_000_000==0 or now==duration:samples.append(dict(time_s=now/1e9,profiles={k:list(t.t) for k,t in plant.tanks.items()}))
            # Plant-only faults are applied AFTER the old interval. Neither
            # controller receives c, now's future schedule, or hidden tank arrays.
            seconds=now/1e9;plant.inject(seconds)
            if seconds>=c['fault_at_s']:
                u=units[c['fault_unit']];fault=c['fault']
                if fault=='CDU_FAILURE':u.secondary_failed[0]=True;u.ready[0]=False
                if fault=='PRIMARY_NO_FLOW':u.primary_block[0]=True
                if fault=='SECONDARY_NO_FLOW':u.secondary_failed[0]=True
                if c.get('standby_start_failed'):u.secondary_failed[1]=True
            second=c.get('second_fault_at_s')
            if second is not None and now==round(second*1e9):pre_second=dict(time_s=seconds,profiles={k:list(t.t) for k,t in plant.tanks.items()},pipe_profiles={k:list(p.t) for k,p in plant.pipes.items()},units=[u.latest for u in units],source=plant.source_path,valves=dict(source=plant.valve,primary=[list(u.primary_valve) for u in units],secondary=[list(u.secondary_valve) for u in units]),speeds=[list(u.speed) for u in units],cold_started=dict(plant.cold_started))
            if now%200000000==0:
                so=plant.observation(now,units);pending_source.append(so)
                # Explicit virtual instrument projection. Stored energy, residuals,
                # hidden fluid-node temperatures and the fault schedule are absent.
                observed_units=[]
                keys=('cdu_id','tank','primary_m3_h','secondary_m3_h','primary_inlet_C','primary_outlet_C','secondary_inlet_C','secondary_outlet_C','secondary_head_pa','primary_relative_dp_pa','speed','primary_valve','secondary_valve')
                for i,u in enumerate(units):
                    cdus=[]
                    for j in range(2):
                        measured={key:u.latest['cdu'][j][key] for key in keys};measured['ready']=u.ready[j]
                        measured['hx_W']=CV*measured['primary_m3_h']/3600*(measured['primary_outlet_C']-measured['primary_inlet_C'])
                        cdus.append(measured)
                    observed_units.append(dict(unit=i,rack_inlet_C=list(u.latest['rack_inlet_C']),cdu=cdus))
                co=dict(id='CDU:'+str(now),sample_ns=now,release_ns=now+round(c['cdu_sensor_delay_s']*1e9),units=observed_units)
                pending_cdu.append(co)
            arrived=[o for o in pending_source if o.release_ns<=now];pending_source=[o for o in pending_source if o.release_ns>now]
            if arrived:last_source=max(arrived,key=lambda o:o.sample_ns)
            arrived_c=[o for o in pending_cdu if o['release_ns']<=now];pending_cdu=[o for o in pending_cdu if o['release_ns']>now]
            if arrived_c:last_cdu=max(arrived_c,key=lambda o:o['sample_ns'])
            if last_source is not None and last_source.record_id!=last_sid:
                safety=protection.evaluate(last_source,now);request=source_controller.request(last_source,safety,now);issued=source_plc.issue(request,safety,last_source,now)
                sf.append(dict(time_ns=now,measurement=asdict(last_source),safety=safety,request=request,PLC=issued));last_sid=last_source.record_id
                if request['source_tank']=='B' and witnesses['B_command_s'] is None:witnesses['B_command_s']=now/1e9
            if last_cdu is not None and now%200000000==100000000:
                requested=controller.request(last_cdu,now);receipt=cdu_plc.issue(requested,last_cdu,now);plant.load_targets=requested['load_pump_speeds']
                cf.append(dict(observation=last_cdu,command=requested,PLC=receipt.data(),PLC_sha256=receipt.digest))
            if last_cdu is not None and (now-100000000)%1_000_000_000==0:
                for i in range(3):
                    for j in range(2):
                        k=2*i+j;o=last_cdu['units'][i]['cdu'][j];e=engines[k];plc=plcs[k]
                        fresh=now-last_cdu['sample_ns']<=600000000
                        m=MeasurementView(now,o['speed'] if fresh else None,last_cdu['sample_ns'],last_cdu['release_ns'],'VALID' if fresh else 'MISSING',last_cdu['id']+f':U{i}:{j}')
                        prior=plc.prior;pre=e.pre(m,prior,c['id']+f':{k}:{now}')
                        channels=[]
                        if not fresh:channels.append(dict(code='PROJECT_CDU_MEASUREMENT_STALE',severity='FAULT'))
                        if j==0 and not o['ready']:channels.append(dict(code='PROJECT_CDU_FAULT_MEASURED',severity='FAULT'))
                        if controller.secondary[i][j]>0 and o['secondary_outlet_C']>45:channels.append(dict(code='PROJECT_LIQUID_LIMIT_MEASURED',severity='FAULT'))
                        safety=e.safety(pre,channels);sd=safety.data();m1_faults[k]|=sd['severity'] in ('FAULT','PROTECTED')
                        demand=controller.pumps[i][j];maximum=demand if controller.secondary[i][j]>0 else 0.
                        envelope=Record.make(dict(record_id=sd['record_id']+':project-enclosure',safety_id=sd['record_id'],safety_digest=safety.digest,time_ns=now,minimum_speed=maximum,maximum_speed=maximum,reason_codes=sd['reason_codes'],scope='NEW_PROJECT_ON_OFF_ISOLATION; NOT_FROZEN_PRODUCTION_POLICY'))
                        output,command=plc.issue(demand,envelope,safety,m);e.accept_plc(output);frame=e.post()
                        check(frame['PRE']['old_command']==asdict(prior),'PRE_FUTURE_COMMAND')
                        check(Record.make(frame['PRE']).digest==pre.digest and Record.make(frame['SAFETY']).digest==safety.digest,'IMMUTABLE_M1_PHASES')
                        check(not any(x['kind']=='DENIED_FUTURE_COMMAND_ACCESS' for x in frame['access_log']),'M1_FUTURE_ACCESS')
                        pump_commands[i][j]=command.applied_command_before_actuator_dynamics
                        transactions.append(dict(unit=i,cdu=j,time_ns=now,measurement_id=m.measurement_record_id,PRE=frame['PRE'],SAFETY=frame['SAFETY'],PLC=frame['PLC'],POST=frame['POST'],envelope=envelope.data(),actuator_command=asdict(command)))
            if now and now%60_000_000_000==0:print('CDU_PROGRESS '+c['id']+' '+str(seconds),flush=True)
        for i,j in enumerate(journals):
            for row in j.rows:read_row(j.path,row)
            save(d/f'm1_{i}_index.json',j.rows)
    finally:
        for j in journals:j.close()
        for stream in (phys,transactions,sf,cf):stream.close()
        timeline.close();ports.close()
    energy['final_J']=plant.energy()+fsum(u.energy() for u in units)
    energy['residual_J']=energy['final_J']-energy['initial_J']-energy['liquid_J']-energy['pump_J']+energy['source_J']-energy['ambient_J']
    energy['bound_J']=rounding_bound(*energy.values(),operations=32768*round(c['seconds']/c['dt_s']))
    check(abs(energy['residual_J'])<=energy['bound_J'],'INDEPENDENT_TOTAL_LEDGER')
    result=dict(id=c['id'],source_commit=__import__('os').environ['GITHUB_SHA'],parameters=c,energy=energy,max_step_residual_J=maximum_residual,max_tank_residual_J=maximum_tank,
        units=metrics,CDU_events=controller.events,source_events=source_controller.events,final_CDU_states=controller.state,m1_fault_latched=m1_faults,
        B_path=witnesses,first_45C_crossing_s=first_cross,final_profiles={k:list(t.t) for k,t in plant.tanks.items()},qualification_samples=samples,pre_second=pre_second,scope='CANDIDATE_OFFLINE_PHYSICAL_DEVELOPMENT; NOT_OEM_OR_CUSTOMER_APPROVAL')
    save(d/'result.json',result);save(d/'plot_data.json',curves);gc.collect();return result
