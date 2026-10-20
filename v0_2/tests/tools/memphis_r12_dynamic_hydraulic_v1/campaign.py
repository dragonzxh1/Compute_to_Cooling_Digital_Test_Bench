"""Finite remote case runner. Full step data, not only a conclusion-driven UI."""
import csv
import json
import time
from pathlib import Path
from .plant import Plant
from .control import Measurements,Controller


def dump(path,value):
    raw=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode()+b'\n'
    with path.open('xb') as f:f.write(raw);f.flush()


def run_case(graph,reg,case,out):
    start=time.monotonic();out.mkdir();plant=Plant(graph,reg,case)
    sensors=Measurements(reg['assumptions'],case);control=Controller(reg)
    dt=reg['resources']['dt_s'];samples=[];cdu_rows=[];rack_rows=[];ledger=[];audit=[]
    injected=False;max_mass=0.;max_energy=0.;initial_fault=case['fault_s']
    raw=(out/'trace.ndjson').open('x',encoding='utf8')
    try:
        for tick in range(round(reg['resources']['physical_seconds_per_case']/dt)):
            now=round(tick*dt,8)
            if time.monotonic()-start>440:raise TimeoutError('CASE_SOFT_BOUND_440S')
            # PRE contains only observations from prior completed physical steps.
            pre=plant.physical(now);sensors.sample(pre,now,dt);frame=sensors.release(now)
            command=control.command(frame,now,dt)
            if case['kind']=='PRESSURE_MISMATCH' and now>=initial_fault:
                command['speeds']['G01-C01B-P2-PM1']=.1
            # Negative command injection is test infrastructure, outside the controller inputs.
            if not injected and now>=initial_fault and case['kind'] in ('MASTER_CONFLICT','PRIMARY_AB_REQUEST'):
                if case['kind']=='MASTER_CONFLICT':command['master']=['A','B']
                else:command['valves'].update({'G01-C01B-P1-CV-BS':1.,'G01-C01B-P1-CV-BR':1.,'G01-C01B-P1-CV-AS':1.,'G01-C01B-P1-CV-AR':1.})
                injected=True
            refusal=plant.issue(command,now)
            # Fault schedule is delivered to plant only, after PRE and control evaluation.
            plant.actuate(dt,now);plant.solve();plant.thermal_step(dt);post=plant.physical(round(now+dt,8))
            max_mass=max(max_mass,post['secondary_mass_residual'],post['primary_mass_residual'])
            max_energy=max(max_energy,abs(post['energy']['energy_step_error_J']))
            record=dict(t=now,state=control.state,pre_sampled_at=frame['sampled_at'] if frame else None,
                pre_release_at=frame['release_at'] if frame else None,released_measurements=frame,command=command,
                simulated_command_refusal=refusal,post=post)
            raw.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
            row=dict(t=post['t'],state=control.state,master=plant.master or 'NONE',
                unit_flow_m3_h=post['unit_flow_m3_h'],min_rack_flow_m3_h=min(r['flow_m3_h'] for r in post['racks'].values()),
                max_rack_inlet_C=max(r['supply_C'] for r in post['racks'].values()),
                A_secondary_m3_h=post['cdus']['A']['secondary_flow_m3_h'],B_secondary_m3_h=post['cdus']['B']['secondary_flow_m3_h'],
                A_outlet_C=post['cdus']['A']['supply_C'],B_outlet_C=post['cdus']['B']['supply_C'],
                master_count=int(plant.master is not None),safety_latch=control.fault_latch)
            samples.append(row);ledger.append(dict(t=post['t'],**post['energy']))
            for side,data in post['cdus'].items():cdu_rows.append(dict(t=post['t'],cdu=side,**data))
            for rack,data in post['racks'].items():rack_rows.append(dict(t=post['t'],rack=rack,**data))
            audit.append(dict(t=now,source_sample=frame['sampled_at'] if frame else None,
                released=frame['release_at'] if frame else None,state=control.state,refusal=refusal))
        raw.flush()
    except BaseException:
        dump(out/'numerical_failure.json',dict(t=now,state=control.state,
            secondary=getattr(plant.sec,'failure',None),primary=getattr(plant.pri,'failure',None)))
        raise
    finally:raw.close()
    def write_csv(name,rows):
        with (out/name).open('x',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write_csv('summary.csv',samples);write_csv('cdus.csv',cdu_rows);write_csv('racks.csv',rack_rows);write_csv('energy.csv',ledger)
    relevant=[s for s in samples if s['t']>=initial_fault]
    minimum=min(s['min_rack_flow_m3_h'] for s in relevant);maximum=max(s['max_rack_inlet_C'] for s in relevant)
    deficit=sum(max(0.,reg['requirements']['each_rack_flow_hot_m3_h']-r['flow_m3_h'])*dt/3600 for r in rack_rows if r['t']>=initial_fault)
    zero_duration=sum(dt for s in relevant if s['min_rack_flow_m3_h']<.001)
    result=dict(case=case,execution_status='COMPLETED',scope=reg['scope'],wall_seconds=time.monotonic()-start,
        physical_seconds=reg['resources']['physical_seconds_per_case'],dt_s=dt,steps=len(samples),
        controller_terminal=control.state,complete_at=control.completed_at,events=control.events,
        min_rack_flow_m3_h=minimum,min_unit_flow_m3_h=min(s['unit_flow_m3_h'] for s in relevant),
        max_rack_inlet_C=maximum,near_zero_flow_duration_s=zero_duration,flow_deficit_volume_m3=deficit,
        thermal_verdict='PASS' if maximum<=reg['requirements']['rack_inlet_max_C'] else 'FAIL',
        hydraulic_verdict='PASS' if minimum+1e-7>=reg['requirements']['each_rack_flow_hot_m3_h'] else 'FAIL',
        takeover_verdict='PASS' if control.completed_at is not None else 'INCOMPLETE',
        max_mass_relative_residual=max_mass,max_energy_step_error_J=max_energy,
        final_energy_cumulative_error_J=ledger[-1]['energy_cumulative_error_J'],
        simulated_guard_refusals=plant.guard_refusals,safety_latch=control.fault_latch,
        primary_boundary_rejection_energy_J=sum(e['primary_boundary_rejection_W']*dt for e in ledger),
        capability_missing=reg['capability_missing'],engineering_status=reg['engineering_status'])
    # Derive primary-B isolation directly from actual saved records, not identity or commands.
    primary_b=0.;maximum_hx_dp=0.;minimum_suction=1e9;max_overlap=0.;overlap_start=None
    with (out/'trace.ndjson').open(encoding='utf8') as f:
        for line in f:
            p=json.loads(line)['post']
            primary_b=max(primary_b,max(v for tag,v in p['valves'].items() if '-P1-CV-B' in tag))
            maximum_hx_dp=max(maximum_hx_dp,max(c['hx_inlet_gauge_difference_kPa'] for c in p['cdus'].values()))
            minimum_suction=min(minimum_suction,min(c['suction_kPa_g'] for c in p['cdus'].values()))
            overlap=any(p['valves'][f'G01-U1-R{r:02d}-CV-AS']>.001 and p['valves'][f'G01-U1-R{r:02d}-CV-BS']>.001 for r in range(1,7))
            if overlap and overlap_start is None:overlap_start=p['t']
            if overlap:max_overlap=max(max_overlap,p['t']-overlap_start+dt)
            else:overlap_start=None
    result.update(primary_B_max_valve_position=primary_b,max_hx_inlet_gauge_difference_kPa=maximum_hx_dp,
        min_suction_kPa_g=minimum_suction,max_actual_overlap_s=max_overlap,
        hx_pressure_verdict='PASS' if maximum_hx_dp<=reg['requirements']['hx_inlet_gauge_difference_max_kPa'] else 'FAIL',
        suction_verdict='PASS' if minimum_suction>=reg['requirements']['pump_suction_min_kPa_g'] else 'FAIL')
    if primary_b>1e-9:raise RuntimeError('PRIMARY_B_UNAUTHORIZED_ACTUAL_OPEN')
    if max_mass>reg['assumptions']['mass_relative_tolerance']:raise RuntimeError('MASS_BALANCE_FAILURE')
    dump(out/'case_result.json',result);dump(out/'causality_audit.json',audit)
    print(json.dumps({k:result[k] for k in ('execution_status','wall_seconds','controller_terminal','thermal_verdict','hydraulic_verdict','takeover_verdict')},ensure_ascii=False),flush=True)
    return result,samples
