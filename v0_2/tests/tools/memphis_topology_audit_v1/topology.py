"""Code-bound directed functional netlist. No invented installed ISA tags."""
import inspect,hashlib,json
from pathlib import Path
from html import escape

def location(module,needle):
    path=Path(module.__file__);lines=path.read_text(encoding='utf-8-sig').splitlines()
    line=next(i+1 for i,s in enumerate(lines) if needle in s)
    return dict(path=path.relative_to(Path(__file__).resolve().parents[4]).as_posix(),line=line,
        raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),expression=needle)

def build():
    from v0_2.tests.tools.memphis_hydraulic_continuity_v1 import plant,coordination
    from v0_2.tests.tools.memphis_failure_closure_v1.group_model import tank,sources
    edges=[];nodes={}
    def path(path_id,components,domain,loc,provenance):
        for j,(a,b) in enumerate(zip(components,components[1:])):
            ca,pa=a.split(':');cb,pb=b.split(':')
            if j>0:pa='OUT'
            if j<len(components)-2:pb='IN'
            nodes.setdefault(ca,dict(tag=ca,tag_authority='AUDIT_DERIVED_CODE_ID_NOT_INSTALLED_ISA_TAG'))
            nodes.setdefault(cb,dict(tag=cb,tag_authority='AUDIT_DERIVED_CODE_ID_NOT_INSTALLED_ISA_TAG'))
            edges.append(dict(id=path_id+'_'+str(len(edges)),path=path_id,source_component=ca,source_port=pa,
                destination_component=cb,destination_port=pb,fluid_domain=domain,nominal_flow_direction='SOURCE_TO_DESTINATION',
                actual_flow_direction='PER_KEYFRAME; STOPPED_IF_ZERO',flow_m3_h=None,temperature_C=None,pressure_kPa=None,
                pressure_status='ABSOLUTE_NOT_MODELED; differential available on loop only',heat_transfer_kW=None,pump_heat_kW=None,
                sensor_id=None,valve_id=None,source_code_location=loc,design_provenance=provenance,
                evidence=['SOURCE_CONFIRMED_BY_CODE','ASSUMED_GEOMETRY_NOT_OEM']))
    p1=location(plant,'transfer_in=tank.t[0]');p2=location(plant,'inlet=self.tanks[self.source_tank]');p3=location(plant,"rc_hot=self.tanks['B']")
    for name in ('A','B'):
        path('TRANSFER_'+name,['TANK_'+name+':BOTTOM_OUT','PUMP_TRANSFER_'+name+':IN','HX_'+name+'_TRANSFER:IN','TANK_'+name+':TOP_IN'],name+'_PG25',p1,'NEW_T2_CANDIDATE_NOT_CUSTOMER00_01')
        path('SOURCE_'+name,['TANK_'+name+':TOP_OUT','SOURCE_SELECTOR:RETURN','PUMP_SOURCE:IN','COOLER_SELECTED:IN','PIPE_SELECTED:IN','SOURCE_SELECTOR:SUPPLY','TANK_'+name+':BOTTOM_IN'],name+'_PG25_SELECTED_ONLY',p2,'TOP_BOTTOM_PORT_ROLE_MATCH00-P724; common pump/manifold simplified')
    path('RC_B',['TANK_B:TOP_OUT','PUMP_RC:IN','RC_SINK:IN','PIPE_RC:IN','TANK_B:BOTTOM_IN'],'B_PG25',p3,'ADDED_INDEPENDENT_RC_NOT00_01')
    path('NEUTRAL',['BUFFER:OUT','PUMP_MAIN:IN','CDU_PRIMARY_MANIFOLD:IN','HX_A_NEUTRAL:IN','HX_B_NEUTRAL:IN','BUFFER:IN'],'NEW_NEUTRAL_PG25',location(plant,'Both neutral sides stay in FIXED SERIES'),'NEW_T2_CANDIDATE_NOT_CUSTOMER00_01')
    for i in range(1,4):
        path('CDU_PRIMARY_'+str(i),['CDU_PRIMARY_MANIFOLD:SUPPLY','CDU'+str(i)+'_PRIMARY:IN','CDU_PRIMARY_MANIFOLD:RETURN'],'NEW_NEUTRAL_PG25',location(plant,'records=[u.advance_project'),'3activeCDU only; 3backupCDU not explicitly instantiated')
        path('SECONDARY_'+str(i),['CDU'+str(i)+'_SECONDARY:OUT','PUMP_SECONDARY_'+str(i)+':IN','RACKS_6_'+str(i)+':IN','CDU'+str(i)+'_SECONDARY:IN'],'SECONDARY_'+str(i)+'_PG25',location(sources,'records=[u.advance_project'),'00/01 each6rack two loops; model one active only')
    thermal=[dict(id='HX_'+n,hot_domain='NEW_NEUTRAL_PG25',cold_domain=n+'_PG25',type='HEAT_ONLY_NO_MASS',inactive_heat_W=0.) for n in ('A','B')]
    thermal += [dict(id='CDU'+str(i),hot_domain='SECONDARY_'+str(i)+'_PG25',cold_domain='NEW_NEUTRAL_PG25',type='HEAT_ONLY_NO_MASS') for i in range(1,4)]
    instruments=[dict(id='TT_'+n+'_'+str(i),location='TANK_'+n+': layer round(i*(N-1)/16)',type='OBSERVED_VIRTUAL_17TT',installed='NOT_VERIFIED') for n in ('A','B') for i in range(17)]
    instruments += [dict(id='SOURCE_PAIRED_TT_FT',location='near/far selected standby pipe',type='RELEASED_DELAYED_SIMULATED',installed='NOT_VERIFIED'),dict(id='PT_ABSOLUTE',location=None,type='NOT_MODELED',installed='NOT_VERIFIED')]
    return dict(schema='FUNCTIONAL-PID-NETLIST-v1',nodes=list(nodes.values()),edges=edges,thermal_edges=thermal,instruments=instruments,
        controls=[dict(id='SOURCE_COORDINATOR',source=location(coordination,'class ContinuityCoordinator')),dict(id='A_B_TANK_FV',source=location(tank,'net=source-load'))],
        valve_semantics='Paired source supply/return share one modeled valve fraction. Transfer supply/return share one fraction. Individual Kv/valve dynamics not resolved.',
        pump_semantics='Source parallel QH group explicit; load/transfer/RC equivalent pumps; redundant load pump motor transfer not modeled.',
        pressure='Quasi-steady differential only; no absolute/static/waterhammer or NPSH verification',
        boundary='As-built SIMULATION, not as-built installation; NOT ISA-certified construction P&ID')

def check_graph(graph):
    ids=[e['id'] for e in graph['edges']]
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_NETLIST_EDGE')
    tags={n['tag'] for n in graph['nodes']}
    for e in graph['edges']:
        if e['source_component'] not in tags or e['destination_component'] not in tags:raise ValueError('MISSING_NETLIST_NODE')
        if e['source_component']=='TANK_A' and e['destination_component']=='TANK_B':raise ValueError('ILLEGAL_AB_MASS_EDGE')
    if len(graph['thermal_edges'])!=5:raise ValueError('HEAT_BOUNDARY_COUNT')
    return dict(edges=len(ids),nodes=len(tags),heat_boundaries=5,status='NETLIST_ID_ENDPOINT_AND_THERMAL_DOMAIN_CHECKED',
        limitation='Static code extraction + runtime selector/flow binding; not a general executable graph solver')

def runtime(graph,frame):
    result=json.loads(json.dumps(graph))
    for e in result['edges']:
        p=e['path'];name='A' if p.endswith('_A') else 'B'
        q=0.;temp=None;pump=0.;heat=0.;valve=None;sensor=None
        if p.startswith('TRANSFER_'):
            active=name==frame['load_tank'];q=frame['transfer_m3_h'] if active else 0.
            t=frame['tanks'][name];temp=t['old_k'][0]-273.15 if e['source_component']=='TANK_'+name else t['return_k']-273.15 if e['destination_component']=='TANK_'+name else None
            pump=frame['transfer_pump_kW'] if 'PUMP' in e['source_component'] else 0.;heat=frame['transfer_heat_kW'] if 'HX' in e['source_component'] and active else 0.;valve='TRANSFER_PAIR_'+name
        elif p.startswith('SOURCE_'):
            q=frame['source_m3_h'] if name==frame['source_tank'] else 0.;t=frame['tanks'][name]
            temp=t['old_k'][-1]-273.15 if e['source_component']=='TANK_'+name else t['source_in_k']-273.15 if e['destination_component']=='TANK_'+name else None
            pump=frame['source_pump_kW'] if 'PUMP' in e['source_component'] and q else 0.;heat=-frame['source_heat_kW'] if 'COOLER' in e['source_component'] and q else 0.;valve='SOURCE_PAIR_'+name
        elif p=='RC_B':
            q=frame['recharge_m3_h'];t=frame['tanks']['B'];temp=t['old_k'][-1]-273.15 if e['source_component']=='TANK_B' else None
            pump=frame['rc_pump_kW'] if 'PUMP' in e['source_component'] else 0.;heat=-frame['rc_heat_kW'] if 'SINK' in e['source_component'] else 0.
        elif p=='NEUTRAL':q=frame['main_m3_h']
        elif p.startswith('CDU_PRIMARY_'):q=frame['main_m3_h']/3
        # Secondary flow is in actual raw unit_records; not copied from a design target.
        e.update(flow_m3_h=q if not p.startswith('SECONDARY_') else None,temperature_C=temp,pump_heat_kW=pump,heat_transfer_kW=heat,
            valve_id=valve,sensor_id=sensor,actual_flow_direction='SOURCE_TO_DESTINATION' if q>0 else 'STOPPED' if not p.startswith('SECONDARY_') else 'SEE_RAW_UNIT_RECORD',
            evidence=e['evidence']+['CONFIRMED_BY_RUNTIME'] if not p.startswith('SECONDARY_') else e['evidence'])
    result['runtime_time_s']=frame['time_s'];return result

def svg(graph,title,paths=None):
    grouped={}
    for e in graph['edges']:
        if paths is None or e['path'] in paths:grouped.setdefault(e['path'],[]).append(e)
    width=1460;height=150+len(grouped)*128
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>',
         '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#334155"/></marker></defs>',
         '<rect width="100%" height="100%" fill="#fff"/>',
         f'<text x="24" y="30" font-family="Arial,Microsoft YaHei" font-size="21">{escape(title)}</text>',
         '<text x="24" y="56" font-family="Arial,Microsoft YaHei" font-size="15">仿真实际功能连接 · 非施工图 · 派生Tag非现场设备编号 · 接口及绝对压力未知处不填假值</text>']
    for row,(path,edges) in enumerate(grouped.items()):
        y=112+128*row;out.append(f'<text x="24" y="{y}" font-family="Arial" font-size="16">{path} / {escape(edges[0]["fluid_domain"])}</text>')
        count=len(edges)+1;step=1360/count;nodes=[(edges[0]['source_component'],edges[0]['source_port'])]+[(e['destination_component'],e['destination_port']) for e in edges]
        for i,(tag,port) in enumerate(nodes):
            x=24+i*step
            out.append(f'<rect x="{x}" y="{y+17}" width="{step-32}" height="43" rx="2" fill="#f1f5f9" stroke="#475569"/><text x="{x+6}" y="{y+34}" font-family="Arial" font-size="12">{escape(tag)}</text><text x="{x+6}" y="{y+51}" font-family="Arial" font-size="12">{escape(port)}</text>')
            if i<len(edges):
                e=edges[i];q=e.get('flow_m3_h');label='Q未展开' if q is None else f'{q:.3f} m³/h'
                temp=e.get('temperature_C');label+=f' / {temp:.3f}°C' if temp is not None else ''
                out.append(f'<g data-edge-id="{e["id"]}"><path d="M{x+step-32} {y+38}H{x+step}" stroke="#334155" fill="none" marker-end="url(#arrow)"/><text x="{x+3}" y="{y+84}" font-family="Arial,Microsoft YaHei" font-size="12">{escape(label)}</text></g>')
    out.append('</svg>');return ''.join(out)
