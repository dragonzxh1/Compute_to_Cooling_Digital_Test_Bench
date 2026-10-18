"""One source-bound engineering delivery from actual persisted forward trials."""
import json,hashlib,os,html,shutil
from pathlib import Path
from math import fsum
from .requirements import save,csvout,CV
from .audit import need
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verified_inputs():
    root=ROOT/'artifacts/memphis-failure-closure-v1-analysis';found={};groups=[]
    for index in root.rglob('artifact_hashes.json'):
        doc=read(index);need(doc['source_commit']==os.environ['GITHUB_SHA'],'FINAL_SOURCE');base=index.parent;bound={x['path']:x for x in doc['records']}
        for f in base.rglob('*'):
            if f.is_file() and f.name!='artifact_hashes.json':
                key=f.relative_to(base).as_posix();need(key in bound and sha(f)==bound[key]['raw_sha256'],'FINAL_RAW_HASH_BINDING')
        receipts=read(base/'execution_receipts.json')
        for r in receipts['stages']:
            d=base/r['stage'];s=read(d/'result.json');p=read(d/'external_job_identity.json');n=read(d/'job_status.json');start=read(d/'job_start.json')
            need(s['status']=='PASS' and s['pid']==p['actual_python_pid']==start['pid'] and p['in_target_job'],'FINAL_ACTUAL_PYTHON')
            need(p['target_job_name']==start['job_name'] and p['cpu_rate']==2500 and p['process_mb']==1024 and p['job_mb']==2048,'FINAL_RESOURCE_IDENTITY')
            need(n['cleanup_complete'] and n['active_after_cleanup']==0 and n['child_exitcode']==0 and n['outcome']=='EXITED','FINAL_POST_EXIT_CLEANUP')
            need(s['environment']==s['environment_after'] and s['environment']['source_commit']==os.environ['GITHUB_SHA'],'FINAL_ENVIRONMENT')
            need(r['stage'] not in found and s['analysis']==read(d/'independent_analysis.json'),'FINAL_DUPLICATE_OR_PERSISTENCE')
            found[r['stage']]=(s['analysis'],d)
        groups.append(dict(group=doc['group'],index_sha256=sha(index),raw_file_count=len(bound)))
    expected={s['id'] for s in read(HERE/'registration.json')['cases'] if s['kind']!='final'}
    need(set(found)==expected,'FINAL_REGISTERED_STAGE_COVERAGE');return found,groups

def plot(points,x,y,title,limit=None):
    points=[r for r in points if isinstance(r.get(x),(int,float)) and isinstance(r.get(y),(int,float))]
    if not points:return '<p>无可验证数值；NOT_VERIFIED</p>'
    xs=[r[x] for r in points];ys=[r[y] for r in points]+([] if limit is None else [limit]);xmin=min(xs);xmax=max(xs);ymin=min(ys);ymax=max(ys)
    dx=max(1e-8,xmax-xmin);dy=max(.1,ymax-ymin);ymin-=.08*dy;ymax+=.08*dy
    def xy(a,b):return 70+680*(a-xmin)/dx,200-165*(b-ymin)/(ymax-ymin)
    out=[f'<h3>{html.escape(title)}</h3><svg viewBox="0 0 800 250" role="img" aria-label="{html.escape(title)}">']
    for i in range(5):
        a=xmin+dx*i/4;b=ymin+(ymax-ymin)*i/4;xx,_=xy(a,b);_,yy=xy(a,b)
        out.append(f'<path d="M70 {yy}H750" stroke="#d6e1e7"/><text x="62" y="{yy+4}" text-anchor="end">{b:.2f}</text><text x="{xx}" y="221" text-anchor="middle">{a:.2f}</text>')
    for r in points:
        a,b=xy(r[x],r[y]);status=r.get('status','');col='#b75e24' if 'NO_FEASIBLE' in status else '#167885'
        label=f"{r.get('id',r.get('case_id',''))}: {x}={r[x]}, {y}={r[y]} {status}"
        out.append(f'<circle cx="{a}" cy="{b}" r="3" fill="{col}"><title>{html.escape(label)}</title></circle>')
    if limit is not None:
        _,yy=xy(xmin,limit);out.append(f'<path d="M70 {yy}H750" stroke="#bd3939" stroke-dasharray="4 3"/>')
    out.append(f'<text x="70" y="16">{html.escape(y)}</text><text x="750" y="243" text-anchor="end">{html.escape(x)}</text></svg>');return ''.join(out)

def finalize(directory):
    found,groups=verified_inputs();analytic=found['ANALYTIC'][0];dynamic=[];buffers=[];pre=[];critical=[];robust=[];units=[];locations={}
    for name,(a,d) in found.items():
        kind=a.get('kind')
        if kind in ('group','critical','joint','robust'):
            for r in a['cases']:dynamic.append(r);locations[r['id']]=d/(r['id']+'/case') if kind!='group' else d/'case'
        if kind=='buffer':buffers+=a['cases']
        if kind=='precool':pre+=a['cases']
        if kind=='critical':critical.append({k:v for k,v in a.items() if k!='cases'})
        if kind=='robust':robust.append(dict(stage=name,status=a['status'],tested=len(a['cases']),failed=sum(r['status']!='CONDITIONALLY_FEASIBLE' for r in a['cases'])))
        if kind=='unit':units+=a['cases']
    # Deduplicate exact repeated parameter configurations, never pick favorable mesh.
    buffer_by={}
    for r in buffers:
        key=(r['tank'],json.dumps(r['parameters'],sort_keys=True));buffer_by.setdefault(key,{})[(r['layers'],r['dt_s'])]=r
    convergence=[]
    for (tank,key),grid in buffer_by.items():
        need(all((n,.1) in grid for n in (20,40,80,160)) and (160,.05) in grid,'BUFFER_GRID_COVERAGE')
        errs=[abs(grid[80,.1]['outlet_rise_K']-grid[160,.1]['outlet_rise_K']),abs(grid[160,.1]['outlet_rise_K']-grid[160,.05]['outlet_rise_K'])]
        convergence.append(dict(tank=tank,parameters=json.loads(key),all_tested_grids_meet_0_5K=all(r['outlet_rise_K']<=.5 for r in grid.values()),
            numerical_status='NUMERICALLY_CONVERGED' if max(errs)<=.05 else 'NOT_VERIFIED',
            error80_160_K=errs[0],error160_dt_K=errs[1],rise20_K=grid[20,.1]['outlet_rise_K'],rise40_K=grid[40,.1]['outlet_rise_K'],rise80_K=grid[80,.1]['outlet_rise_K'],rise160_K=grid[160,.1]['outlet_rise_K']))
    tank_bounds={}
    for tank in ('A','B'):
        c=[r for r in convergence if r['tank']==tank and r['parameters']['fraction']==.7 and r['parameters']['mixing']==0 and r['parameters']['cold_C']==40.9448 and r['parameters']['short']==0 and r['parameters']['wall']==0]
        ok=[r['parameters']['volume'] for r in c if r['all_tested_grids_meet_0_5K']]
        fractions=[r['parameters']['fraction'] for r in convergence if r['tank']==tank and r['parameters']['volume']==15 and r['parameters']['mixing']==0 and r['parameters']['cold_C']==40.9448 and r['parameters']['short']==0 and r['parameters']['wall']==0 and r['all_tested_grids_meet_0_5K']]
        tank_bounds[tank]=dict(ideal_necessary_cold_m3=8.25,ideal_necessary_energy_MJ=analytic['tank']['usable_energy_MJ_at_registered_return'],
            smallest_tested_total_volume_at70pct_all_grids_m3=min(ok) if ok else None,
            smallest_tested_cold_fraction_in15_all_grids=min(fractions) if fractions else None,
            minimum_added_volume_from15_on_tested_grid_m3=max(0,min(ok)-15) if ok else None,
            actual_OEM_minimum=None,global_continuous_minimum='NOT_VERIFIED',
            condition='constant48.29C return330m3/h90s, no source flow, stated mixing/wall; coarse diffusion retained; actual dynamic source trials separate')
    # Pareto over VERIFIED FORWARD finite joint points, not a fictitious monetary optimum.
    joint=[r for r in dynamic if r['id'].startswith('JOINT') and r['status']=='CONDITIONALLY_FEASIBLE']
    def costs(r):
        p=r['parameters'];return (p.get('tank_volume_m3',15),p.get('capacity_scale',1),CV*2.75*max(0,48.29-p.get('standby_initial_c',48.29))/1e6,max(0,54-p.get('startup_s',54)))
    pareto=[r for r in joint if not any(all(a<=b for a,b in zip(costs(s),costs(r))) and any(a<b for a,b in zip(costs(s),costs(r))) for s in joint)]
    temp=[r for r in critical if r['axis']=='standby_initial_c'];start=[r for r in critical if r['axis']=='startup_s']
    volume_limits=[r for r in critical if r['axis']=='header_volume_m3'];valve_limits=[r for r in critical if r['axis']=='valve_s']
    feasible_temp=[r['largest_tested_feasible'] for r in temp if r['largest_tested_feasible'] is not None]
    tested_temp=min(feasible_temp) if len(feasible_temp)==2 else None
    req=analytic['recharge'];tank=analytic['tank']
    devices=[]
    def device(name,existing,flow,minimum,target,temperature,energy,response,dp,boundary,sensitivity,evidence):
        devices.append(dict(device=name,existing_selection=existing,design_flow_m3_h=flow,current_thermal_performance='CUSTOMER_DESIGN_OR_SYNTHETIC_NOT_OEM',
            MODEL_REQUIRED_MINIMUM=minimum,CONDITIONAL_DESIGN_TARGET=target,OEM_GUARANTEED_VALUE=None,
            worst_condition='18x155kW95% liquid;DB46/WB30 hot; registered fault and interval',required_inlet_outlet_C=temperature,
            minimum_effective_cold_MJ=energy,maximum_response_s=response,actual_or_required_dp_kPa=dp,
            permitted_boundary=boundary,recommended_margin='No arbitrary guaranteed margin; registered sensitivity and OEM tolerances must support final margin',
            calculation_evidence=evidence,parameter_sensitivity=sensitivity,OEM_data=None,procurement='FROZEN_NOT_RELEASED'))
    for t in ('A','B'):
        b=tank_bounds[t]
        device(t+'储罐','15m3,70% cold assumed',330,'ideal8.25m3;'+str(tank['usable_energy_MJ_at_registered_return'])+'MJ',json.dumps(b,ensure_ascii=False),
            'initial40.9448;return48.29;outlet rise<=0.5K',tank['usable_energy_MJ_at_registered_return'],90,None,'All20/40/80/160+dt.05; no wall baseline','fraction/mixing/short-circuit/mesh/temp', 'buffer_convergence.csv;buffer_trials.json')
    device('分层/布水器','unknown OEM geometry',330,'No unique allowable mixing coefficient','Use all-grid passing fraction/mixing combinations only',None,None,90,None,'Lumped wall sensitivity not real wall calibration','mix0/0.001/0.005m3/s;short0/.05/.2','buffer_convergence.csv')
    device('备用管预冷','2.75m3, historical48.29C stagnation',None,'Max sampled joint-grid feasible initialC='+str(tested_temp),
        '81.524375MJ removal from48.29 to40.9448; ideal679.37kW/120s or90.58kW/900s BEFORE gains/pump',
        'floor40.9448;far-end ready<=41.4448',81.5243748,None,20,'Closed-loop flow/heat/ambient/cold readiness jointly required','flow5--90m3/h;25--750kW;UA0/.5kW/K','precool_results.json;critical_ranges.json')
    device('D1/D2干冷器','3200kW reference,3 modules each',330,f'{analytic["dry"]["single_duty_kW"]}kW actual reject at required temperatures',
        f'normalDB29Tout37Tin{analytic["dry"]["DB29_Tout37_Tin"]:.6f};Nminus1 each>=1358.075kW',
        'DB29,37C supply;DB46 cannot directly produce41C',None,None,63.21,'Effective ambient conductance surface only, air-flow/UA/fan unknown','DB20--46,flow264--400,source3modules','dry_performance_surface.csv')
    device('W1/W2湿冷源','3300kW reference,5 modules each',330,'2716.15kW at actual design fluids/weather plus actual pump reconciliation',
        '5modules each>=543.23kW;one lost each of4>=679.0375kW',
        f'WB30,Tout41,Tin{analytic["wet"]["WB30_Tout41_Tin"]:.6f};Tout35 requiresTin{analytic["wet"]["WB30_Tout35_Tin"]:.6f}',
        None, start[0]['largest_tested_feasible'] if start else None,96.52,'Assumed5K wet approach not OEM maximumWB;fan/spray/airflow UNKNOWN','WB20--46,capacity,module loss,startup','wet_performance_surface.csv;forward_trials.json')
    device('源泵组','V9 115m3/h34m vsR10 whole curve<=18m',330,'3 pumps each110m3/h at loop96.52kPa; selection115.82kPa',
        'V9/R10 separate synthetic Q-H envelopes; four-pump relief/transient check required',None,None,None,96.52,'No combining34m withR10 static reference; NPSHr/weak MAWP unknown','2/3/4pumps,speed,eta','analytic_requirements.json')
    device('负荷泵组','separate primary loop',330,'330m3/h at155.92kPa loop',
        'Electrical18--24kW pergroup at eta0.8--0.6, actual table controls',None,None,None,155.92,'Do not add source and load differential heads across tank interfaces','eta/.6/.7/.8, valve interruption','analytic_requirements.json;forward_trials.json')
    device('回充泵','326.194m3/h historical independent',330,
        f'120kPa at330 requires H0>={req["required_H0_kPa_at_existing_K"]:.6f}kPa with fixed K',
        f'or keep18m curve and reduce loopDP<={req["at_old_H0_maximum_allowed_loop_dp_kPa"]:.6f}kPa',None,None,None,120,
        'H0 upgrade may violate18m; cannot silently adopt; matched shared/independent samePID source this run','H0factor1/1.03,DP120/115.82','analytic_requirements.json;recharge forward cases')
    device('CDU板换','1100kW required, UA not OEM confirmed',110,
        'ideal UA137.481 normal/183.295 hot kW/K;1100kW guarantee209.284 ideal',
        'Account actual pump heat and rack-vs-HX outlet offset; fresh forward UA scans do not inherit OEM',
        'primary37/secondary40;primary41/secondary44;147.25kW liquid/rack',None,None,'primary quoted74.714;secondary26.626','Three online + three standby; PG25 actual product/fouling missing','UA137481--260000W/K and normal49.19/hot68.37','unit_results.json;analytic_requirements.json')
    device('关键阀门与测点','5s assumed;fourTT;100ms source release',330,
        'Actual zero-speed/closed-valve interlocks; released paired TT/flow/pressure evidence',
        'Separate tower-outlet/far-end/tank-cold/rack-inlet TT; flow>=330 and measured ready hold;stroke2/5/10s hypothetical',
        'rack<=45, cold source pipe<=41.4448',None,None,None,'No illegalAB parallel;pipe arrival != valve open;no fabricated PLC issue','bias+/-0.2K,delay0.1/0.4/1.2s,stuck','forward_trials.json;negative witness')
    csvout(directory/'minimum_equipment_parameters.csv',devices)
    save(directory/'device_feasible_ranges.json',dict(devices=devices,tank=tank_bounds,critical=critical,precool=pre,
        numerical_convergence=convergence,robustness=robust,Pareto_tested_ids=[r['id'] for r in pareto],global_optimum='NOT_VERIFIED',OEM_GUARANTEED_VALUE=None))
    save(directory/'forward_trials.json',dynamic);save(directory/'buffer_trials.json',buffers);save(directory/'unit_results.json',units)
    save(directory/'precool_results.json',pre);save(directory/'critical_ranges.json',critical);save(directory/'analytic_requirements.json',analytic)
    csvout(directory/'buffer_convergence.csv',[dict(tank=r['tank'],parameters=json.dumps(r['parameters']),**{k:v for k,v in r.items() if k not in ('tank','parameters')}) for r in convergence])
    sensitivity=[dict(id=r['id'],status=r['status'],max_inlet_C=r['max_inlet_C'],max90_inlet_C=r['max90_inlet_C'],cold_return_delay_s=r['cold_return_delay_s'],
        actual_load_min_m3_h=r['actual_load_min_m3_h'],actual_source_final_m3_h=r['actual_source_final_m3_h'],pump_kW=r['actual_pump_heat_kW'],
        restored_reject_kW=r['restored_state_required_reject_kW'],steady_necessary=r['steady_energy_necessary_condition'],parameters=json.dumps(r['parameters'],sort_keys=True)) for r in dynamic]
    csvout(directory/'sensitivity_results.csv',sensitivity)
    paretorows=[dict(id=r['id'],tank_m3=costs(r)[0],capacity_scale=costs(r)[1],precool_MJ=costs(r)[2],startup_improvement_s=costs(r)[3],peak_C=r['max_inlet_C'],cold_delay_s=r['cold_return_delay_s']) for r in pareto]
    save(directory/'pareto_feasible_region.json',dict(status='CONDITIONALLY_FEASIBLE' if pareto else 'NO_FEASIBLE_DESIGN_IN_TESTED_GRID',points=paretorows,global_optimum='NOT_VERIFIED',cost_quotes=None))
    for mode in ('dry','wet'):csvout(directory/(mode+'_performance_surface.csv'),analytic['surfaces'][mode])
    for filename in ('precool_energy_bounds.csv',):shutil.copyfile(found['ANALYTIC'][1]/filename,directory/filename)
    rfi=[dict(id=f'RFI-{i:02}',supplier_data=x,required_condition=y,blocking=True,OEM_GUARANTEED_VALUE=None,procurement='FROZEN') for i,(x,y) in enumerate([
        ('CDU effectiveUA/fouling/PG25/4temperatures/Q-DP','37/40,41/44;110/49.19/68.37;1100kW guarantee separate'),
        ('Tank diffuser/thermocline/short-circuit/wall and initial cold inventory','A and B separately330m3/h90s<=0.5K;TT placement and worst inlet sequence'),
        ('Standby preconditioning topology/pipe volume/insulation and measured ready','Temperature/flow/transport history;thermal kW vs COP/fan electric;outage holding time'),
        ('Dry actualDB/flow/PG25/outlet map and Nminus1','DB29 supply37;DB46 cannot alone make41;finite airflow/UA/power'),
        ('Wet actualWB/DB/PG25 map, module loss, startup and fan/spray','46DB/30WB at specified inlet/outlet330;water2h includingdrift/blowdown/sump'),
        ('Pump full Q-H-eta-NPSHr/shutoff/speed/parallel map','V9 34m andR10<=18m adjudicated separately;source/load/recharge separate'),
        ('Static elevations/expansion/relief/weakest MAWP/transient','Suction/gauge references;water hammer;forbiddenAB cross-connection'),
        ('Valve Kv/stroke/zero-speed and source-ready measurement','Actual PLC receipts,release/sample latency,calibration uncertainty and independent fast protection'),
        ('Design cost/reliability/uncertainty distributions','No monetary Pareto weights,probability orROBUST approval without field envelope')],1)]
    csvout(directory/'supplier_RFI.csv',rfi)
    # One Chinese report; all table values link to stored forward outputs, no aggregate engineering PASS.
    lines=['# 孟菲斯18柜设备最低性能要求','', 'MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_CALIBRATION_REQUIRED。所有最低值是守恒必要下界或有限模型点，不是厂家保证。',
        '',f"执行commit `{os.environ['GITHUB_SHA']}`；manifest `{sha(HERE/'source_manifest.json')}`；实际正向组模型{len(dynamic)}次、独立罐试验{len(buffers)}次、预冷{len(pre)}次、设备边界{len(units)}次。",'',
        '## 孟菲斯18柜设备最低性能表','', '|设备|MODEL_REQUIRED_MINIMUM|CONDITIONAL_DESIGN_TARGET|OEM保证|采购|','|---|---|---|---|---|']
    for d in devices:lines.append('|'+d['device']+'|'+d['MODEL_REQUIRED_MINIMUM']+'|'+d['CONDITIONAL_DESIGN_TARGET']+'|空缺|冻结|')
    lines +=['','## 15个明确回答','',
        f"1. A罐：理想必要有效冷液8.25m³；相对48.29°C回水的可用显热{tank['usable_energy_MJ_at_registered_return']:.6f}MJ，预算2716.15kW×90s为{tank['duty90_energy_MJ']:.6f}MJ，两者是不同工况口径，不可相加。模型边界：{json.dumps(tank_bounds['A'],ensure_ascii=False)}。",
        f"2. B罐：相同理想必要量，独立B阶段实际重算；{json.dumps(tank_bounds['B'],ensure_ascii=False)}。对称结果来自相同登记几何和输入，不证明两台真实罐等效。",
        '3. 15m³是否足够：只在具体冷液比例、初温、混合/短路和出口曲线下有条件满足；70%不是OEM事实。最低通过总容积/冷比例为上表有限样本，不是连续全局最小。见buffer_convergence.csv全部网格，不挑选通过层数。',
        f"4. 备用管最高允许温度：80/160层临界扫描{json.dumps(temp,ensure_ascii=False)}。两网格都得到可行点时共同最大采样值{tested_temp}°C，仅是测试点范围，不保证中间未测区或其他天气。暖水48.29°C管体积的独立扫描为{json.dumps(volume_limits,ensure_ascii=False)}；阀门时间独立扫描为{json.dumps(valve_limits,ensure_ascii=False)}。不能只从热库存等式推断动态允许体积/时延。",
        '5. 预冷能力：48.29→40.9448°C、2.75m³的必要降热81.524375MJ；120秒理想>=679.37kW且理想至少82.5m³/h置换，900秒理想>=90.58kW且至少11m³/h；真实混合、热增益和泵热增加需求。实际闭式预冷扫描5--90m³/h、25--750kW与UA0/0.5kW/K见precool_results.json。电功率缺COP/风机图谱，不能把热kW当电kW。',
        f"6. 单干冷：至少排出{DUTY if False else 2716.15}kW（须按实际泵热更新）；330m³/h、37°C出液时进液{analytic['dry']['DB29_Tout37_Tin']:.6f}°C，在DB29工况保证。3模块各>=905.383kW；Nminus1剩余2模块各>=1358.075kW。有效流体-环境导热面不等于空气侧真实UA。",
        f"7. 单湿冷：330m³/h下2716.15kW、41°C出液要求进液{analytic['wet']['WB30_Tout41_Tin']:.6f}°C；若要求35°C出液，则进液{analytic['wet']['WB30_Tout35_Tin']:.6f}°C。5模块各>=543.23kW；Nminus1四模块各>=679.0375kW。WB30与PG25实际性能、喷淋和风机未OEM确认。",
        '8. DB46/WB30：无制冷单干冷不能直接产41°C水；湿冷热力学上可行不等于设备已保证。实际HOT/HYBRID/模块失效试验结果见敏感性表，额外管阻与泵热已计入，未自动批准混合拓扑。',
        '9. 一次源泵：3×110m³/h，源侧运行96.52kPa/选型115.82kPa；负荷泵330m³/h、155.92kPa独立回路。V9候选34m与R10关死<=18m是不同约束；不跨版本拼静压。实际并联交点/效率区间见analytic_requirements.json，NPSHr/静压/瞬态/弱件MAWP仍NOT_VERIFIED。',
        f"10. 回充：在原合成K不变时H0至少{req['required_H0_kPa_at_existing_K']:.6f}kPa才能330m³/h@120kPa；若保留18m曲线，系统330工况压降须<={req['at_old_H0_maximum_allowed_loop_dp_kPa']:.6f}kPa。增加H0可能违反18m，不能悄悄采用。四个实际回充试验分别保存。",
        '11. 90秒需要联合满足：全IT2650.5kW入液+实际泵热、机柜入口<=45、负载侧连续330、备用源冷返时序和最终5秒稳定、罐单体出口<=0.5K、有效冷库存、禁止A/B非法并通及真实测量权限。源侧停流不能冒充负载侧停流或放宽330。',
        '12. 最大瓶颈：暖备用管热库存/输送与冷罐储备、源启动和二次停流耦合；若源容量低于实际液体+泵热，短时缓冲通过也不能成为持续满载可行设计。',
        '13. 最有效参数须看本次sensitivity_results.csv与临界曲线：预冷、启动时间、库存、冷源能力并非处处单调；记录每个状态机边界，不用单一点推全球结论。',
        '14. 最小修改候选：优先实证备用管预冷及远端冷水ready测点，保留15m³前须证明有效比例/混合和初温。这个结论不是授权新增旁通、并罐或修改00/01；若扫描无可行点明确保留NO_FEASIBLE_DESIGN_IN_TESTED_GRID。',
        '15. OEM必须提供：CDU/泵/塔共同工况图谱、分层罐与布水器出口试验、管路UA/容积、源预备与冷水到达时间、阀行程/Kv、实际仪表时延/误差、NPSHr/MAWP/水锤，以及2h补水含蒸发/排污/漂水/死水体积。实际OEM保证值全部为空。',
        '', '## 联合可行域、Pareto与鲁棒性','',
        f"有限联合点可行{len(joint)}个；非支配点{len(pareto)}个。变量代价只是容积/合成容量倍率/预冷MJ/启动改进秒，不是经济最优或全球最优。",'',json.dumps(robust,ensure_ascii=False,indent=2),
        '', '未给联合连续区间或概率分布；若任一已登记不确定性/故障不满足，不能声明ROBUST PASS。NUMERICALLY_CONVERGED只用于匹配参数网格/步长差<=0.05K的数值点，不是实际混合或全系统保证。',
        '', '## OPTION A / B / C','',
        '- OPTION A：保持数量和15m³；必须同时达到表中冷比例/冷库存/混合条件、源实际工况排热和泵Q-H，以及临界预冷/建冷组合。缺数据或跨网格失败不算现方案已通过。',
        '- OPTION B：候选15m³、85%初始冷液、备用管40.5°C、建冷20秒；只是受控假设点，17个单因素/联合角点含二次故障实测，失败保留。预冷设施和20秒能力需供应商证明。',
        '- OPTION C：候选20m³、85%冷液、同预冷/启动目标；更大容积并非天然更可靠，独立回充需匹配泵曲线，Nminus2需独立供冷/电源域而非放宽指标；不能宣称硬件配置已经选定。',
        '', '## 独立核算与不足','',
        '独立复核各机柜控制体、HX、质量、实际泵热一次归属、储能总账、源侧许可和M1 PRE/Safety/PLC/POST；每试验保存原始物理、传感器、事务/压缩日志、参数、哈希。解析预算不额外注热。',
        '保持冻结M1、原C3-C和历史证据，不继承其集成资格。原SEM02/PF06缺口、任意POST/崩溃/断电原子性未证明、T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED原状保留。无正式C3-C、生产、硬件控制、Phase6或采购授权。',
        '', '## 供应商正式RFI','', '|编号|待提供保证数据|共同工况|','|---|---|---|']
    lines += [f"|{r['id']}|{r['supplier_data']}|{r['required_condition']}|" for r in rfi]
    report='\n'.join(lines)+'\n';(directory/'MEMPHIS_MINIMUM_EQUIPMENT_REQUIREMENTS_ZH.md').write_text(report,encoding='utf-8')
    payload=dict(source_commit=os.environ['GITHUB_SHA'],manifest_sha256=sha(HERE/'source_manifest.json'),registration_sha256=sha(HERE/'registration.json'),
        model_status='DEVELOPMENT_CALCULATION_COMPLETED',engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',dynamic_trials=len(dynamic),buffer_trials=len(buffers),precool_trials=len(pre),unit_trials=len(units),
        tank_bounds=tank_bounds,critical=critical,robustness=robust,Pareto_points=paretorows,official_raw_groups=groups,
        OEM_GUARANTEED_VALUE=None,formal=False,production=False,procurement=False,hardware=False,phase6=False)
    save(directory/'inverse_sizing_results.json',payload)
    plots=[]
    for mode,target in (('dry',37.),('wet',41.)):
        p=[r for r in analytic['surfaces'][mode] if r['flow_m3_h']==330 and r['outlet_C']==target]
        plots.append(plot(p,'ambient_C','effective_fluid_to_ambient_conductance_kW_K',mode+'有效导热要求（不是空气侧真实UA）'))
    for t in ('A','B'):plots.append(plot([dict(r,volume=r['parameters']['volume']) for r in buffers if r['tank']==t and r['parameters']['mixing']==0 and r['parameters']['fraction']==.7 and r['parameters']['cold_C']==40.9448],'volume','outlet_rise_K',t+'罐体积—90秒出口升温 / 全部网格',.5))
    plots.append(plot([dict(r,T=r['parameters'].get('standby_initial_c')) for r in dynamic if r['id'].startswith('TEMP')],'T','max_inlet_C','备用管初温—机柜峰温',45))
    plots.append(plot([dict(r,T=r['parameters'].get('startup_s')) for r in dynamic if r['id'].startswith('STARTUP')],'T','max_inlet_C','建冷时间—机柜峰温',45))
    plots.append(plot([dict(r,volume=r['tank_m3'],energy=r['precool_MJ']) for r in paretorows],'volume','energy','有限Pareto可行区域：体积与预冷MJ'))
    plots.append(plot(pre,'flow_m3_h','ready_seconds','闭式预冷：流量、能力和热增益的实际Ready时间'))
    precool_bounds=[]
    for T in (40.9448,41.,41.5,42.,43.,44.,46.,48.29):precool_bounds.append(dict(T=T,energy=CV*2.75*(T-40.9448)/1e6))
    plots.append(plot(precool_bounds,'T','energy','备用管温度—暖水热库存MJ'))
    modeldata={r['id']:read(locations[r['id']]/'plot_data.json') for r in dynamic}
    document='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>孟菲斯18柜逆向设备选型</title><style>body{font:16px/1.65 system-ui;max-width:1180px;margin:auto;padding:24px;color:#193743;background:#f7fafb}h1,h2{line-height:1.3}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #d4e0e5;text-align:left}svg{width:100%;max-height:320px;background:white}svg text{font:13px system-ui;fill:#193743}details{padding:16px 0;border-bottom:1px solid #ccdce3}select{font:inherit;max-width:100%;padding:8px}.sc{overflow:auto}</style><h1>孟菲斯18柜 · 设备最低性能反求</h1><p>实际正向复验 / 有限参数网格 / 所有OEM保证空缺 / MEMPHIS_ENGINEERING_NOT_APPROVED</p><p>必要下界 ≠ 模型条件可行 ≠ 厂家保证。保留所有失败；任何二次故障失败不能被一个总PASS覆盖。</p>'+''.join(plots)
    document+='<h2>实际故障响应与恢复时间轴</h2><label>选择已执行场景 <select id="case">'+''.join('<option>'+html.escape(r['id'])+'</option>' for r in dynamic)+'</select></label><div id="charts"></div><pre id="events"></pre><details><summary>完整中文工程报告与设备最低性能表 / 15项回答 / RFI</summary><pre>'+html.escape(report)+'</pre></details>'
    jsdata=json.dumps(dict(series=modeldata,results={r['id']:r for r in dynamic}),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    document+='<script>const data='+jsdata+''';const select=document.getElementById('case');function draw(){const id=select.value,rows=data.series[id],r=data.results[id];document.getElementById('events').textContent=JSON.stringify({status:r.status,ready:r.ready,actualEvents:r.diagnosis.actual_selector_events,controlEvents:r.diagnosis.source_events,parameters:r.parameters},null,2);let out='';for(const [keys,label,limit] of [[['rack_inlet_c','primary_inlet_c','pipe_return_c'],'机柜入口/一次供液/源管回水 °C',45],[['source_flow_m3_h','load_flow_m3_h'],'源侧/负载实际流量 m³/h',330],[['cold_A_m3','cold_B_m3'],'A/B阈值冷库存 m³',null]]){let vals=rows.flatMap(p=>keys.map(k=>p[k]));if(limit!==null)vals.push(limit);let lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max(.2,(hi-lo)*.08);lo-=pad;hi+=pad;const xmax=rows[rows.length-1].time_s;let s='<h3>'+label+'</h3><svg viewBox="0 0 800 250" role="img" aria-label="'+label+'">';for(let i=0;i<5;i++){const y=30+i*40,v=hi-(hi-lo)*i/4;s+='<path d="M65 '+y+'H770" stroke="#d6e1e7"/><text x="58" y="'+(y+4)+'" text-anchor="end">'+v.toFixed(2)+'</text><text x="'+(65+705*i/4)+'" y="220" text-anchor="middle">'+(xmax*i/4).toFixed(0)+'s</text>';}keys.forEach((k,i)=>{s+='<polyline fill="none" stroke="'+['#167885','#bd6524','#667d8a'][i]+'" stroke-width="2" points="'+rows.map(p=>(65+705*p.time_s/xmax).toFixed(2)+','+(190-160*(p[k]-lo)/(hi-lo)).toFixed(2)).join(' ')+'"/>';});if(limit!==null){let y=190-160*(limit-lo)/(hi-lo);s+='<path d="M65 '+y+'H770" stroke="#b33" stroke-dasharray="4 3"/>';}out+=s+'</svg><p>'+keys.join(' / ')+'</p>';}document.getElementById('charts').innerHTML=out;}select.addEventListener('change',draw);draw();</script></html>'''
    (directory/'engineering_report.html').write_text(document,encoding='utf-8')
    return dict(status=payload['model_status'],engineering=payload['engineering'],counts={k:payload[k] for k in ('dynamic_trials','buffer_trials','precool_trials','unit_trials')},tank=tank_bounds,critical=critical,robustness=robust,Pareto_points=len(pareto),raw_groups=groups,result_sha256=sha(directory/'inverse_sizing_results.json'))
