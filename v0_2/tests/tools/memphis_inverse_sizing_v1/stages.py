"""Registered inverse studies, explicit finite grids and non-monotonic edge searches."""
import json,hashlib,itertools,gc
from pathlib import Path
from math import fsum,exp
from .requirements import save
from .audit import need,group
HERE=Path(__file__).resolve().parent

def full_recovery_label(fault_required,conditions):
    return ('CONDITIONALLY_FEASIBLE' if conditions else 'NOT_VERIFIED') if fault_required else 'NOT_APPLICABLE_NO_FAULT'

def forward(options,directory,baseline=False):
    from .group_model.simulation import run
    from .analysis import diagnose
    c=dict(scope='GROUP18',ua_w_k=220000.,dt_s=.1,seconds=240.,source_variant='V9',tank_kind='STRATIFIED',
        fault='W1_LOSS',fault_at_s=30.,recharge_at_s=120.)
    c.update(options)
    if c.get('standby_outage_s'):
        from .requirements import CV
        c['standby_initial_c']=46-(46-c.get('standby_before_outage_C',40.5))*exp(-c.get('pipe_ambient_UA_kW_K',.5)*1000*c['standby_outage_s']/(CV*c.get('header_volume_m3',2.75)))
    if c.pop('no_fault',False):c.pop('fault',None);c.pop('fault_at_s',None)
    need(c['dt_s'] in (.1,.05) and c['seconds']<=900 and c['ua_w_k']>0,'BOUNDED_FORWARD_INPUT')
    run(c,directory/'case');a=group(directory/'case',c);diag=diagnose(directory/'case',c)
    # Keep exact actual numeric and causal checks, not controller-written verdicts.
    steps=json.loads((directory/'case/physics.json').read_bytes())
    def first(test):return next((r['end_ns']/1e9 for r in steps if r['start_ns']>=30e9 and test(r)),None)
    def rack(r):return max(max(u['new_k'][1:7])-273.15 for u in r['unit_records'])
    def hyd(r):return r['source_flow_m3_h']>=330-1e-8 and r['load_flow_m3_h']>=330-1e-8
    codes=set()
    for f in json.loads((directory/'case/source_phases.json').read_bytes()):codes.update(f['safety']['data']['codes'])
    ready=dict(SOURCE_READY_s=first(lambda r:r['source_available'][r['source_path']] and r['source_valve']>=1-1e-9 and r['source_speed']>0),
        COLD_WATER_READY_s=None if a['first_cold_return_330_delay_s'] is None else 30+a['first_cold_return_330_delay_s'],
        HYDRAULIC_READY_s=first(hyd),THERMAL_READY_s=first(lambda r:rack(r)<=45),
        FULL_LOAD_RECOVERED=full_recovery_label(bool(c.get('fault')),a['grades']['FULL_LOAD_CONTINUITY']=='PASS' and diag['strict_uninterrupted_primary330']=='PASS' and not (codes&{'SOURCE_SENSOR_STALE'})),
        note='Separate physical analysis cuts; first temperature<=45 alone is not failure recovery; installed far-end cold TT absent')
    energy=a['independent']['independent_energy'];pump=energy['pump_j']/c['seconds']/1000
    final_pump=(steps[-1]['primary_pump_electrical_w']+steps[-1]['secondary_pump_electrical_w'])/1000
    peak_pump=max(r['primary_pump_electrical_w']+r['secondary_pump_electrical_w'] for r in steps)/1000
    synthetic_cap=(3200. if c.get('initial_path','W1').startswith('D') else 6500. if c.get('hybrid_series') else 3300.)*c.get('capacity_scale',1.)*c.get('wet_derating',1.)
    if c.get('module_loss'):synthetic_cap*=2/3 if c.get('initial_path','W1').startswith('D') else .8
    steady_possible=synthetic_cap>=2650.5+max(pump,final_pump)
    valid=(a['maximum_inlet_c']<=45 and a['terminal_source_recovery_maintained'] and diag['strict_uninterrupted_primary330']=='PASS'
        and (c.get('no_fault') or not c.get('fault') or (a['first_cold_return_330_delay_s'] is not None and a['first_cold_return_330_delay_s']<=90))
        and 'SOURCE_SENSOR_STALE' not in codes and steady_possible)
    result=dict(id=c['id'],parameters=c,status='CONDITIONALLY_FEASIBLE' if valid else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',
        engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',max_inlet_C=a['maximum_inlet_c'],max90_inlet_C=a['first90_maximum_inlet_c'],
        cold_return_delay_s=a['first_cold_return_330_delay_s'],actual_load_min_m3_h=diag['actual_load_flow_min_m3_h'],
        actual_source_final_m3_h=diag['source_final_flow_m3_h'],actual_pump_heat_kW=pump,actual_required_reject_kW=2650.5+pump,
        final_pump_heat_kW=final_pump,peak_pump_heat_kW=peak_pump,restored_state_required_reject_kW=2650.5+final_pump,
        reference_budget_difference_kW=2650.5+pump-2716.15,
        synthetic_capacity_ceiling_kW=synthetic_cap,steady_energy_necessary_condition=steady_possible,
        normal40C_target_met=a['maximum_inlet_c']<=40 if c.get('primary_target_c')==37 else None,
        hot44C_target_met=a['maximum_inlet_c']<=44,
        inventory_restore_s=a['reserve_ready_absolute_s'],recharge=a['recharge_flow_comparison'],
        thermal=a['grades']['RACK_THERMAL_COMPLIANCE'],load330=diag['strict_uninterrupted_primary330'],
        source_recovered=a['terminal_source_recovery_maintained'],ready=ready,protection_codes=sorted(codes),
        diagnosis=diag,independent_energy=energy,independent_causal=a['independent']['grades']['M1_CAUSAL_VALIDITY'],
        raw_hashes={f:hashlib.sha256((directory/'case'/f).read_bytes()).hexdigest() for f in ('physics.json','series.json','phases.json','source_phases.json')},
        OEM_GUARANTEED_VALUE=None,standalone_tank_guarantee='NOT_VERIFIED')
    if baseline:need(result['raw_hashes']==json.loads((HERE/'baseline_hashes.json').read_bytes()),'EXACT_PARENT_BASELINE_RAW_DRIFT')
    save(directory/'forward_result.json',result);del steps;gc.collect();return result

def stage(spec,directory):
    kind=spec['kind']
    if kind=='final':
        from .report import finalize
        return finalize(directory)
    if kind=='negative':
        import ast
        for path in HERE.rglob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
        from .negative import run
        out=run()
        need(full_recovery_label(False,True)=='NOT_APPLICABLE_NO_FAULT','NOFAULT_WRONGLY_QUALIFIED_AS_RECOVERY')
        need(full_recovery_label(True,False)=='NOT_VERIFIED','FAILED_RECOVERY_LABEL')
        out['refusal_and_positive_witnesses']+=2
        return out
    if kind=='analytic':
        from .requirements import analytic
        return analytic(directory)
    if kind=='buffer':
        from .buffer import run
        return run(spec,directory)
    if kind=='precool':
        from .precool import run
        return run(spec,directory)
    if kind=='unit':
        from v0_2.tests.tools.memphis_equipment_validation_v2.unit import run
        from v0_2.tests.tools.memphis_equipment_validation_v2.audit import unit
        results=[]
        for normal,ua in itertools.product((True,False),(137481.,183295.,209284.,220000.,260000.)):
            c=dict(id=spec['id']+str(normal)+str(ua),normal=normal,ua=ua)
            d=directory/c['id'];d.mkdir();run(c,d/'case');a=unit(d/'case');a['parameters']=c
            save(d/'unit_result.json',a);results.append(a);gc.collect()
        return dict(kind='unit',cases=results,scope='fresh existing one-six-rack fixed-primary37/41 boundary, not inherited integrated qualification')
    if kind=='group':return dict(kind='group',cases=[forward(dict(spec['parameters'],id=spec['id']),directory,baseline=spec.get('baseline',False))])
    if kind=='critical':
        results=[];layers=spec['layers'];axis=spec['axis']
        values={'standby_initial_c':[40.9448,41.,41.2,41.4,41.6,42.,43.,44.,46.,48.29],
            'startup_s':[0.,20.,40.,54.,70.,80.],
            'header_volume_m3':[.25,.5,1.,2.75,5.],
            'valve_s':[1.,2.,5.,10.,15.,20.]}[axis]
        fixed=dict(layers=layers,standby_initial_c=40.9448)
        if axis=='header_volume_m3':fixed['standby_initial_c']=48.29
        def evaluate(v,index):
            options=dict(fixed,**{axis:v},id=spec['id']+f'_{index:02}')
            d=directory/options['id'];d.mkdir();r=forward(options,d);results.append(r);print('INVERSE_TRIAL '+options['id']+' '+r['status'],flush=True);return r
        first=[evaluate(v,i) for i,v in enumerate(values)]
        # Refine EVERY observed success/failure edge, do not presume monotonicity.
        edges=[]
        for i,(a,b) in enumerate(zip(first,first[1:])):
            if a['status']!=b['status']:
                left,right=values[i:i+2];edges.append([left,right])
                for v in (left+(right-left)*j/4 for j in (1,2,3)):evaluate(v,len(results))
        feasible=[r['parameters'][axis] for r in results if r['status']=='CONDITIONALLY_FEASIBLE']
        return dict(kind='critical',axis=axis,layers=layers,cases=results,observed_edges=edges,
            largest_tested_feasible=max(feasible) if feasible else None,
            smallest_tested_infeasible=min((r['parameters'][axis] for r in results if r['status']!='CONDITIONALLY_FEASIBLE'),default=None),
            global_minimum='NOT_VERIFIED',assumption='No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven')
    if kind=='joint':
        results=[]
        for i,(startup,volume,scale) in enumerate(itertools.product((20.,54.,80.),(15.,20.),(.8,1.))):
            p=dict(id=spec['id']+f'_{i:02}',layers=80,standby_initial_c=spec['standby_C'],startup_s=startup,tank_volume_m3=volume,capacity_scale=scale)
            d=directory/p['id'];d.mkdir();results.append(forward(p,d));print('JOINT_TRIAL '+p['id'],flush=True)
        return dict(kind='joint',cases=results,global_optimality='NOT_VERIFIED_NO_COST_OR_GLOBAL_CONTINUOUS_PROOF')
    if kind=='robust':
        base=dict(layers=80,standby_initial_c=40.5,startup_s=20.,tank_volume_m3=spec['volume'],cold_fraction=.85)
        scenarios=[{},dict(wet_bulb_c=32.),dict(capacity_scale=.8),dict(cold_initial_c=41.2),dict(standby_initial_c=42.),
            dict(mixing_m3_s=.005,short_circuit=.05),dict(source_head_factor=.97),dict(primary_efficiency=.6),dict(valve_s=10.),
            dict(sensor_bias_K=-.2),dict(sensor_bias_K=.2,sensor_delay_s=.4),dict(sensor_delay_s=1.2),
            dict(second_source_failure=True),dict(load_valve_stuck=True),dict(layers=160),dict(layers=160,dt_s=.05),
            dict(wet_bulb_c=32.,capacity_scale=.8,cold_initial_c=41.2,standby_initial_c=42.,mixing_m3_s=.001,source_head_factor=.97,primary_efficiency=.6,valve_s=10.,sensor_bias_K=-.2,sensor_delay_s=.4)]
        results=[]
        for i,s in enumerate(scenarios):
            p=dict(base,**s,id=spec['id']+f'_{i:02}')
            d=directory/p['id'];d.mkdir();results.append(forward(p,d));print('ROBUST_TRIAL '+p['id'],flush=True)
        return dict(kind='robust',cases=results,
            status='ROBUST_WITHIN_TESTED_ENVELOPE' if all(r['status']=='CONDITIONALLY_FEASIBLE' for r in results) else 'NOT_VERIFIED',
            scope='Only registered finite joint cases; no uncertainty probabilities, no untested Nminus2 guarantee')
    raise ValueError('UNREGISTERED_STAGE')
