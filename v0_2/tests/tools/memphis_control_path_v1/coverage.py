"""Independent physical branch witnesses. No controller/plant imports or future feedback."""
import csv,json
from math import fsum
from .checks import require,save,CV
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.streaming import FileArray

def verify_coverage(d,c):
    frames=json.loads((d/'source_phases.json').read_bytes())
    first_command=None;fault_detected=None;prior=None;commands=0;max_budget=0.
    for f in frames:
        o=f['measurement'];r=f['request'];now=f['time_ns']
        require(o['sample_ns']<=o['release_ns']<=now,'COVERAGE_NO_FUTURE_MEASUREMENT')
        require(f['PLC']['data']['request']==r and f['PLC']['data']['measurement_id']==o['record_id'],'COVERAGE_ACTUAL_PLC_BINDING')
        if r['source_tank']=='B':
            commands+=1
            if first_command is None:first_command=now/1e9
        if prior and (r['source_path'],r['source_tank'])!=(prior['source_path'],prior['source_tank']):
            require(o['source_speed']<=1e-9 and o['source_valve']<=1e-9,'INDEPENDENT_SOURCE_CLOSED_ZERO_BEFORE_SELECTION')
        if r.get('shared_segments_requested',0)>(prior or {}).get('shared_segments_requested',0):
            require(r['A_CONTIGUOUS_TT_LOWER_ESTIMATE_m3']>=r['shared_absence_budget_m3'],'SHARED_PERMISSION_BUDGET')
            require(now-o['sample_ns']<=600000000,'SHARED_PERMISSION_STALE')
            max_budget=max(max_budget,r['shared_absence_budget_m3'])
        if not o['w1_available'] and fault_detected is None:fault_detected=now/1e9
        prior=r
    vals=dict(first_B_command_s=first_command,actual_B_selector_s=None,actual_B_open_pair_s=None,
              first_B_flow_s=None,first_B_cold_return_s=None,first_B_inventory_increase_s=None,
              actual_B_flow_duration_s=0.,B_net_source_heat_J=0.,B_source_cooled_J=0.,
              B_actual_volume_m3=0.,minimum_B_positive_m3_h=None,maximum_B_m3_h=0.,maximum_B_cold_m3=0.,
              first_source_return_A_after_B_s=None,actual_load_B_s=None,maximum_energy_residual_J=0.)
    intervals=[];segment=None;first_cold_B=0.;first=True
    timeline=d/'physical_path.csv'
    with timeline.open('x',encoding='utf-8',newline='') as handle:
        writer=None
        for row in FileArray(d/'physics.json',round(c['seconds']/c['dt_s'])):
            start=row['start_ns']/1e9;t=row['end_ns']/1e9;dt=t-start
            if first:first_cold_B=row['tank_B_cold_m3'];first=False
            b=row['source_tank']=='B';q=row['source_flow_m3_h'];tb=row['tank_records']['B'];ta=row['tank_records']['A']
            if b and vals['actual_B_selector_s'] is None:vals['actual_B_selector_s']=t
            if b and row['source_supply_valve']>=1-1e-9 and row['source_return_valve']>=1-1e-9 and vals['actual_B_open_pair_s'] is None:vals['actual_B_open_pair_s']=t
            if b and q>1e-8:
                if vals['first_B_flow_s'] is None:vals['first_B_flow_s']=t
                vals['actual_B_flow_duration_s']+=dt;vals['B_actual_volume_m3']+=q*dt/3600
                vals['maximum_B_m3_h']=max(vals['maximum_B_m3_h'],q)
                old=vals['minimum_B_positive_m3_h'];vals['minimum_B_positive_m3_h']=q if old is None else min(old,q)
                # This is source-port net heat, not merely cooling-unit duty.
                heat=CV*q/3600*(row['source_return_k']-tb['old_k'][-1])
                vals['B_net_source_heat_J']+=heat*dt;vals['B_source_cooled_J']+=max(0.,-heat)*dt
                if row['source_return_k']<=314.5948 and vals['first_B_cold_return_s'] is None:vals['first_B_cold_return_s']=t
                require(row['source_supply_valve']>0 and row['source_return_valve']>0,'PHYSICAL_B_PAIR_NOT_FORMED')
            if b and segment is None:segment=dict(start_s=start,end_s=t,A_cold_start_m3=row['tank_A_cold_m3'],A_cold_end_m3=row['tank_A_cold_m3'],peak_rack_C=-1e9,min_load_m3_h=1e9)
            if segment is not None:
                segment.update(end_s=t,A_cold_end_m3=row['tank_A_cold_m3'])
                segment['peak_rack_C']=max(segment['peak_rack_C'],max(max(u['new_k'][1:7])-273.15 for u in row['unit_records']))
                segment['min_load_m3_h']=min(segment['min_load_m3_h'],row['load_flow_m3_h'])
                if not b:
                    intervals.append(segment);segment=None
                    if vals['first_source_return_A_after_B_s'] is None:vals['first_source_return_A_after_B_s']=t
            vals['maximum_B_cold_m3']=max(vals['maximum_B_cold_m3'],row['tank_B_cold_m3'])
            if row['tank_B_cold_m3']>first_cold_B+1e-9 and vals['first_B_inventory_increase_s'] is None:vals['first_B_inventory_increase_s']=t
            if row['load_tank']=='B' and vals['actual_load_B_s'] is None:vals['actual_load_B_s']=t
            record=dict(time_s=t,source_tank=row['source_tank'],source_path=row['source_path'],load_tank=row['load_tank'],
                source_valve=row['source_valve'],load_valve=row['load_valve'],source_m3_h=q,load_m3_h=row['load_flow_m3_h'],
                source_head_relative_pa=row['source_head_pa'],load_head_relative_pa=row['load_head_pa'],source_pumps=row['actual_source_pumps'],
                source_return_C=row['source_return_k']-273.15,source_pump_W=row['source_pump_heat_w'],load_pump_W=row['load_pump_heat_w'],
                source_rejected_W=row['main_rejected_w'],RC_rejected_W=row['rc_rejected_w'],cold_A_m3=row['tank_A_cold_m3'],cold_B_m3=row['tank_B_cold_m3'],
                A_bottom_C=ta['old_k'][0]-273.15,A_top_C=ta['old_k'][-1]-273.15,B_bottom_C=tb['old_k'][0]-273.15,B_top_C=tb['old_k'][-1]-273.15,
                source_pressure_relative_pa=json.dumps(row['source_pressure_relative_pa'],sort_keys=True),
                source_edge_drops_pa=json.dumps(row['source_edge_drops_pa'],sort_keys=True))
            if writer is None:writer=csv.DictWriter(handle,fieldnames=list(record));writer.writeheader()
            writer.writerow(record)
    if segment:intervals.append(segment)
    valid=bool(vals['actual_B_flow_duration_s']>0 and vals['B_source_cooled_J']>0 and vals['first_B_inventory_increase_s'] is not None)
    vals.update(B_commands=commands,fault_first_released_observation_s=fault_detected,shared_budget_m3=max_budget,
        segments=intervals,B_coverage='ACTUAL_COLD_RECOVERY_PATH_EXERCISED' if valid else 'PATH_FORMED_BUT_NO_COLD_INVENTORY_RECOVERY' if vals['actual_B_flow_duration_s']>0 else 'COMMAND_ONLY_NO_FLOW' if commands else 'UNREACHABLE_WITH_EVIDENCE_IN_REGISTERED_ENVELOPE',
        qualification='PHYSICAL_BRANCH_WITNESS_NOT_90S_RESERVE_PASS',pressure_scope='QUASI_STEADY_RELATIVE_ONLY; NO_STATIC_NPSH_WATERHAMMER',
        source_commit=__import__('os').environ['GITHUB_SHA'])
    if c.get('disable_B_recharge'):require(commands==0 and not valid,'DISABLED_B_FALSE_COVERAGE')
    if c.get('B_source_valve_stuck') or c.get('B_source_pump_no_flow'):
        require(commands>0,'NEGATIVE_B_NOT_EXCITED');require(not valid,'NEGATIVE_B_FALSE_SUCCESS')
    if c.get('source_sensor_delay_s',.1)>1:require(commands==0,'STALE_DATA_ADVANCED_B')
    save(d/'branch_coverage.json',vals)
    return vals
