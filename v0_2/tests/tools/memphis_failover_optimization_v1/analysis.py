"""Event/energy/volume attribution from saved raw records, no plant imports."""
import json
from math import fsum

def read(p):return json.loads(p.read_bytes())
def diagnose(directory,spec):
    rows=read(directory/'physics.json');frames=read(directory/'source_phases.json');result=read(directory/'result.json')
    events=result['source_timeline'];fault=spec.get('fault_at_s');end=rows[-1]['end_ns']/1e9
    def temp(r):return max(max(u['new_k'][1:7])-273.15 for u in r['unit_records'])
    def first(test):return next((r['end_ns']/1e9 for r in rows if (fault is None or r['start_ns']>=round(fault*1e9)) and test(r)),None)
    source_flow=first(lambda r:r['source_available'][r['source_path']] and r['source_flow_m3_h']>=330-1e-8)
    tower_cold=first(lambda r:r['source_available'][r['source_path']] and r['source_flow_m3_h']>=330-1e-8 and r['source_cold_k']<=314.5948)
    return_cold=first(lambda r:r['source_available'][r['source_path']] and r['source_flow_m3_h']>=330-1e-8 and r['source_return_k']<=314.5948)
    segments=[]
    boundaries=sorted(set([fault or 0.,end,*[e['time_ns']/1e9 for e in events if e['time_ns']/1e9>=(fault or 0.)]]))
    for start,stop in zip(boundaries,boundaries[1:]):
        rr=[r for r in rows if start*1e9<=r['start_ns'] and r['end_ns']<=stop*1e9]
        if not rr:continue
        segments.append(dict(start_s=start,end_s=stop,duration_s=stop-start,
            state=next((e['to_state'] for e in reversed(events) if e['time_ns']<=round(start*1e9)),'RUN'),
            source_pumped_m3=fsum(r['source_flow_m3_h']/3600*(r['end_ns']-r['start_ns'])/1e9 for r in rr),
            load_transported_m3=fsum(r['load_flow_m3_h']/3600*(r['end_ns']-r['start_ns'])/1e9 for r in rr),
            heat_rejected_MJ=fsum(r['rejected_w']*(r['end_ns']-r['start_ns'])/1e15 for r in rr),
            cold_A_end_m3=rr[-1]['tank_A_cold_m3'],cold_B_end_m3=rr[-1]['tank_B_cold_m3'],
            max_rack_inlet_c=max(map(temp,rr))))
    plot=[dict(time_s=r['end_ns']/1e9,rack_inlet_c=temp(r),primary_inlet_c=r['primary_inlet_c'],
        source_outlet_c=r['source_cold_k']-273.15,pipe_return_c=r['source_return_k']-273.15,
        source_flow_m3_h=r['source_flow_m3_h'],load_flow_m3_h=r['load_flow_m3_h'],
        cold_A_m3=r['tank_A_cold_m3'],cold_B_m3=r['tank_B_cold_m3'],source_path=r['source_path'],
        source_tank=r['source_tank'],load_tank=r['load_tank'],source_speed=r['source_speed'],
        source_valve=r['source_valve'],load_valve=r['load_valve'],rejected_kw=r['rejected_w']/1000)
        for r in rows if r['end_ns']%1_000_000_000==0]
    (directory/'plot_data.json').write_text(json.dumps(plot,sort_keys=True),encoding='utf-8')
    active=[r for r in rows if fault is None or r['start_ns']>=round(fault*1e9)]
    full_flow=[r for r in active if r['load_flow_m3_h']<330-1e-8]
    changes=[]
    for a,b in zip(rows,rows[1:]):
        if (a['load_tank'],a['source_tank'],a['source_path'])!=(b['load_tank'],b['source_tank'],b['source_path']):
            changes.append(dict(time_s=b['end_ns']/1e9,load=b['load_tank'],source_tank=b['source_tank'],source_path=b['source_path']))
    return dict(source_events=events,actual_selector_events=changes,segments=segments,
        fault_s=fault,first_actual_source_design_flow_s=source_flow,first_tower_cold_at_design_flow_s=tower_cold,
        first_pipe_cold_at_design_flow_s=return_cold,nominal_line_volume_m3=spec.get('header_volume_m3',2.75),
        nominal_volume_over_design_flow_s=spec.get('header_volume_m3',2.75)/(330/3600),
        pipeline_displacement_m3_after_tower_cold_to_first_return=None if tower_cold is None or return_cold is None else
            fsum(r['source_flow_m3_h']/3600*(r['end_ns']-r['start_ns'])/1e9 for r in rows if r['start_ns']>=round(tower_cold*1e9) and r['end_ns']<=round(return_cold*1e9)),
        actual_load_below330_duration_s=fsum((r['end_ns']-r['start_ns'])/1e9 for r in full_flow),
        actual_load_flow_min_m3_h=min(r['load_flow_m3_h'] for r in active),
        strict_uninterrupted_primary330='FAIL' if full_flow else 'PASS',
        source_final_flow_m3_h=rows[-1]['source_flow_m3_h'],
        actual_load_selector_final=rows[-1]['load_tank'],
        engineering_approval='MEMPHIS_ENGINEERING_NOT_APPROVED',
        interpretation='RUN is pump permission, not measured cold readiness; volume integral includes interrupted flow, not pure delay attribution')
