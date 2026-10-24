"""Remote-only, bounded research adapters; no modification to accepted model sources."""
import csv
import hashlib
import json
import math
import os
import time
from pathlib import Path
from .request_contract import check_request, parse

HERE = Path(__file__).resolve().parent


def require_remote():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('RUNNER_OS') != 'Windows':
        raise RuntimeError('REMOTE_NUMERICAL_EXECUTION_ONLY')


def tank_study(d):
    # Use the accepted conservative flux function, not a redrawn visual curve.
    from v0_2.tests.tools.memphis_equipment_validation_v2.group_model.tank import primary_rates
    from v0_2.tests.tools.memphis_equipment_validation_v2.group_model.common import CV
    p = lambda k: d['parameters'][k]['value']
    keys = ('rho', 'cp', 'tank_volume', 'primary_flow', 'cold_c', 'hot_c', 'cold_fraction', 'mixing')
    if any(p(k) is None for k in keys):
        raise ValueError('TANK_INPUT_MISSING')
    if p('hot_c') <= p('cold_c'):
        raise ValueError('INITIAL_HOT_COLD_ORDER')
    cv, volume, flow = p('rho') * p('cp'), p('tank_volume'), p('primary_flow') / 3600
    studies = []
    for n in (80, 160):
        cell, dt = volume / n, .1
        if dt * (flow + 2 * p('mixing')) / cell > .5:
            raise ValueError('TANK_CFL_CAPABILITY_MISSING_NO_AUTO_SUBSTEP')
        # A fractional interface cell preserves the requested initial energy.
        temps = [(p('cold_c') * max(0., min(1., p('cold_fraction') * n - i)) + p('hot_c') * (1 - max(0., min(1., p('cold_fraction') * n - i)))) + 273.15 for i in range(n)]
        start = temps[:];initial = cv * cell * math.fsum(temps);hin = hout = 0.;frames = [];outlets = []
        def frame(t):
            cold = sum(x <= p('cold_c') + 273.65 for x in temps) * cell
            return dict(t_s=t, A=[x-273.15 for x in temps], B=[x-273.15 for x in temps], cold_A_m3=cold, cold_B_m3=cold,
                        outlet_c=temps[0]-273.15, inlet_c=p('hot_c'), flow_m3_h=p('primary_flow'),
                        inlet_enthalpy_kw=cv*flow*(p('hot_c')+273.15)/1000, outlet_enthalpy_kw=cv*flow*temps[0]/1000,
                        conservation_residual_j=cv*cell*math.fsum(temps)-initial-hin+hout)
        frames.append(frame(0))
        for step in range(900):
            old = temps[:];outlets.append(old[0]-273.15)
            rates = primary_rates(old, flow, 0., p('hot_c')+273.15, p('cold_c')+273.15, p('mixing'))
            temps = [a + dt*(r*cv/CV)/(cv*cell) for a, r in zip(old, rates)]
            hin += dt*cv*flow*(p('hot_c')+273.15);hout += dt*cv*flow*old[0]
            if not all(math.isfinite(x) and 273.15 <= x <= 373.15 for x in temps):
                raise ValueError('TANK_MODEL_RANGE_STOP')
            if (step+1) % 10 == 0:
                frames.append(frame((step+1)/10))
        outlets.append(temps[0]-273.15)
        residual = cv*cell*math.fsum(temps)-initial-hin+hout
        tolerance = 2e-10 * max(initial, abs(hin), abs(hout), 1.)
        if abs(residual) > tolerance:
            raise ValueError('TANK_CONSERVATION_STOP')
        rise = max(outlets)-(start[0]-273.15)
        studies.append(dict(layers=n,frames=frames,outlet_max_c=max(outlets),outlet_rise_k=rise,
                            verdict='CONDITIONAL_MET' if rise <= .5 else 'FAIL',residual_j=residual,tolerance_j=tolerance))
    return dict(frames=studies[0]['frames'], mesh_checks=[{k:v for k,v in s.items() if k!='frames'} for s in studies],
        fine_mesh_frames=studies[1]['frames'],tank_volume_m3=volume,rho=p('rho'),cp=p('cp'),reference_c=p('hot_c'),cold_threshold_c=p('cold_c')+.5,
        layer_order='BOTTOM_TO_TOP', scope='两个相同初态的独立罐放冷试验；A/B并排不是切换或系统恢复试验。无冷源回充，无外部泵热输入。80/160层均报告，不挑选有利网格。',
        assumptions=['恒定330或研究流量边界，不是源泵动态','显式混合参数未标定','无壁面损失/布水器实测/短路标定','初态界面单元为体积加权温度；阈值体积受网格影响'])


def six_study(d, step):
    from v0_2.tests.tools.memphis_single_rack_v1.cases import config
    from v0_2.tests.tools.memphis_single_rack_v1.plant import RackLoop
    p = lambda k: d['parameters'][k]['value']
    needed = ('rack_kw','liquid_fraction','rho','cp','primary_flow','secondary_flow','primary_c','secondary_target','ua','pump_speed','external_drop','rack_drop','hx_drop','internal_drop')
    if any(p(k) is None for k in needed):
        raise ValueError('SIX_INPUT_MISSING')
    if p('liquid_fraction') != .95:
        raise ValueError('MODEL_CAPABILITY_MISSING_LIQUID_FRACTION_NOT_0_95')
    baseline = parse((HERE/'data/baseline.json').read_bytes())
    if d['topology'] != baseline['topology']:
        raise ValueError('MODEL_CAPABILITY_MISSING_EDITED_TOPOLOGY_NOT_MAPPED')
    c = config(dict(id='MVP_SIX_STEP' if step else 'MVP_SIX_CONSTANT',rack_count=6,boundary='HOT'))
    dp = sum(p(k) for k in ('external_drop','rack_drop','hx_drop','internal_drop'))*1000
    c.update(density_kg_m3=p('rho'),cp_j_kg_k=p('cp'),design_flow_m3_s=p('secondary_flow')/3600,
             primary_flow_m3_s=p('primary_flow')/3/3600,hx_ua_w_k=p('ua')*1000,design_dp_pa=dp,branch_dp_pa=p('rack_drop')*1000,
             initial_supply_k=p('secondary_target')+273.15,initial_speed=p('pump_speed'))
    curve_note = '沿用已登记的未标定研究曲线形状1.25、参考速比0.9；不是OEM曲线'
    if p('pump_h0') is not None or p('pump_k') is not None:
        if p('pump_h0') is None or p('pump_k') is None:
            raise ValueError('QH_BOTH_PARAMETERS_REQUIRED')
        c['quadratic_shutoff_factor'] = 1 + p('pump_k')*p('secondary_flow')**2*1000/dp
        c['design_speed'] = math.sqrt(dp*c['quadratic_shutoff_factor']/(p('pump_h0')*1000))
        curve_note = '由用户H0/K恢复的二次研究曲线；不是厂家性能保证'
    full = p('rack_kw')*1000;initial = full*.25 if step else full
    c['load_profile'] = [dict(time_ns=0,rack_it_w=[initial]*6)]
    model = RackLoop(c);frames=[];records=[]
    def frame(t, r=None):
        snap=model.snapshot(round(t*1e9),p('pump_speed'),'PRESCRIBED_SPEED_NO_CONTROL_QUALIFICATION')
        return dict(t_s=t,rack_inlet_c=[snap.supply_k-273.15]*6,rack_return_c=[x-273.15 for x in model.t[1:-1]],
                    rack_flow_m3_h=[x*3600 for x in snap.branch_flows_m3_s],unit_flow_m3_h=[snap.flow_m3_s*3600],
                    dp_kpa=[snap.dp_pa/1000],hx_kw=None if r is None else r['hx_w']/1000,
                    pump_kw=None if r is None else r['pump_electrical_w']/1000,
                    mass_residual_kg_s=snap.mass_residual_kg_s)
    frames.append(frame(0))
    for i in range(600):
        loads=[full if not step or i>=100 else initial]*6
        r=model.advance(i*100000000,(i+1)*100000000,p('pump_speed'),loads,p('primary_c')+273.15)
        records.append(r)
        if (i+1)%10==0:frames.append(frame((i+1)/10,r))
    ledger=model.ledger();max_temp=max([max(frames[0]['rack_inlet_c']),*[r['new_k'][0]-273.15 for r in records]])
    return dict(frames=frames, raw_steps=records,ledger=ledger,temperature_verdict='CONDITIONAL_MET' if max_temp<=45 else 'FAIL',
        peak_rack_inlet_c=max_temp,min_rack_flow_m3_h=min([min(frames[0]['rack_flow_m3_h']),*[min(r['branch_flows_m3_s'])*3600 for r in records]]),integration_dt_s=.1,display_dt_s=1,
        scope='单六柜60秒约简热水力回路；一次温度/流量为边界；给定泵速、非控制闭环、非CDU接管、非18柜动态。',
        assumptions=[curve_note,'机柜共用供液集管，逐柜支路分别求流量','内部容积/支路阻力/效率沿用未标定研究输入','全部泵电功最终入液一次；不表示现场电机热分配'],events=[dict(t_s=10,event='25%→100%研究负载阶跃')] if step else [])


def execute(out, stage):
    require_remote()
    if stage != 'baseline':raise ValueError('ONE_BOUNDED_TASK_NO_AUTOMATIC_SUITE')
    started=time.monotonic();req=parse((HERE/'request.json').read_bytes());d=check_request(req)
    out.mkdir(parents=True,exist_ok=False)
    try:
        result=tank_study(d) if req['model']=='tank90' else six_study(d,req['model']=='six_step')
        raw=result.pop('raw_steps',None)
        result.update(schema='C2C-RESEARCH-RESULT-1',model=req['model'],design_sha256=req['design_sha256'],
            source_commit=os.environ['GITHUB_SHA'],request_sha256=hashlib.sha256((HERE/'request.json').read_bytes()).hexdigest(),
            manifest_sha256=hashlib.sha256((HERE/'source_manifest.json').read_bytes()).hexdigest(),
            physical_seconds=90 if req['model']=='tank90' else 60,actual_elapsed_s=time.monotonic()-started,
            engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED',complete_system=False)
        (out/'research_result.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        if raw is not None:(out/'raw_steps.json').write_text(json.dumps(raw,allow_nan=False),encoding='utf-8')
        with (out/'timeseries.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(['t_s','outlet_c','rack_inlet_max_c','unit_flow_m3_h','hx_kw','pump_dp_kpa','conservation_residual_j'])
            for r in result['frames']:w.writerow([r['t_s'],r.get('outlet_c'),max(r['rack_inlet_c']) if 'rack_inlet_c'in r else None,(r.get('unit_flow_m3_h')or[None])[0],r.get('hx_kw'),(r.get('dp_kpa')or[None])[0],r.get('conservation_residual_j')])
        return dict(model=req['model'],design_sha256=req['design_sha256'],scope=result['scope'],elapsed_s=result['actual_elapsed_s'])
    except BaseException as e:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(e),model=req['model'],design_sha256=req['design_sha256'],engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED')),encoding='utf-8')
        raise
