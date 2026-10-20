"""Consolidated decisions from actual saved outputs; no aggregate engineering PASS."""
import json,os,hashlib,shutil
from pathlib import Path
from .checks import save,require
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def customer_components(trials,profiles):
    if not trials or not profiles:return None
    values=[]
    for t in trials:
        p=profiles[t['tank']];cold=sum(x<=314.5948 for x in p)*15/len(p)
        values.append(dict(tank=t['tank'],layers=t['layers'],cold_m3=cold,rise_K=t['rise_K'],maximum_outlet_C=t['maximum_outlet_C'],
            conditional70_and_rise_only='PASS' if cold>=10.5 and t['rise_K']<=.5 else 'FAIL',
            research85_and_absolute=t['status'],scope='70pct uses research41.4448C cold definition; not OEM or system qualification'))
    return values

def finalize(directory):
    root=ROOT/'artifacts/memphis-control-path-v1-analysis';reg=json.loads((HERE/'registration.json').read_bytes())
    cases={};points={}
    for p in root.rglob('loop_summary.json'):
        c=json.loads(p.read_bytes());key=c['id'];require(key not in cases,'DUPLICATE_CASE')
        require(c['source_commit']==os.environ['GITHUB_SHA'],'SAME_EXECUTION_SOURCE')
        c['customer_component_comparison']=customer_components(c['final_full_discharge'],c['final_tanks_k'])
        c['customer_pre_second_comparison']=customer_components(c['observed']['pre_second_challenge'],c['observed']['pre_second_profiles'])
        cases[key]=c;points[key]=json.loads((p.parent/'plot_data.json').read_bytes())
    require(set(cases)=={x['id'] for x in reg['cases'] if x['kind']=='forward'},'ALL_DECLARED_CASES_REQUIRED')
    d=directory/'delivery';d.mkdir()
    save(d/'ACTUAL_RESULTS.json',cases);save(d/'ACTUAL_PLOTS.json',points);save(d/'REGISTERED_INPUTS.json',reg)
    for name in ('prior_root_cause.json','customer_originals.json','DESIGNER_CONFIRMATION.md'):
        shutil.copyfile(HERE/name,d/name)
    shutil.copyfile(HERE/'diagram/runtime_pid.svg',d/'runtime_pid.svg')
    base=cases['ATTR_BASE'];attribution=[]
    for name,c in cases.items():
        if not name.startswith('ATTR_'):continue
        change=next(x['change'] for x in reg['cases'] if x['id']==name)
        attribution.append(dict(id=name,registered_change=change,peak_C=c['maximum_inlet_C'],first90_C=c['maximum90_inlet_C'],
            peak_difference_K=c['maximum_inlet_C']-base['maximum_inlet_C'],minimum_m3_h=c['minimum_load_m3_h'],
            energy=c['independent']['independent_energy'],scope='ONE_PARAMETER_FIRST240S; no inherited long-term verdict'))
    save(d/'FIRST_FAULT_ATTRIBUTION.json',attribution)
    md='# 原00/01控制路径补全：实际结果\n\nMEMPHIS_ENGINEERING_NOT_APPROVED。未标定模型，不是客户设计批准。\n\n'
    md+='执行'+os.environ['GITHUB_SHA']+' / run'+os.environ['GITHUB_RUN_ID']+'。故障后90s、B恢复、A恢复、双罐组件、完整第二次故障、长期恢复分别判断；短240秒归因不冒充全过程。\n\n'
    md+='## 上轮补B为何没有执行\n\n上轮source_phases原始hash16eb52bc…0be1：120秒后8400帧最大冷量估计12.1875m³，小于14.0625门槛；16点温差最小4.905K，大于0.25K门槛。未发B命令，不能归因PLC拒绝或物理阀失效。该“近乎全罐均温”筛选不适合已观察分层。新候选仅以已发布17TT的底部连续冷量和完整离开A预算决定短时分段许可；不直接宣布90秒Ready。10s/30s预算仍需设计方确认。\n\n'
    md+='## 全部实际结果\n\n|案例|峰值°C|首次90s|最低m³/h|共享B物理覆盖|末态研究双罐|第二90s|\n|---|---:|---|---:|---|---|---|\n'
    for k,c in cases.items():md+=f"|{k}|{c['maximum_inlet_C']:.6f}|{c['grades']['90S_CONTINUITY']}|{c['minimum_load_m3_h']:.6f}|{c['control_path']['B_coverage']}|{c['grades']['RESERVE_RECOVERY']}|{c['grades']['SECOND_FAULT_90S']}|\n"
    md+='\n## 首次超温单变量归因\n\n|案例|全240秒峰值°C|相对基线K|首次90秒峰值°C|最小流量m³/h|\n|---|---:|---:|---:|---:|\n'
    for x in attribution:md+=f"|{x['id']}|{x['peak_C']:.6f}|{x['peak_difference_K']:.6f}|{x['first90_C']:.6f}|{x['minimum_m3_h']:.6f}|\n"
    md+='\n各参数仅为研究点。54秒零排热、暖管库存和1D混合不等于OEM真实性能；基线失败不是客户原拓扑必败。非零相邻层混合非网格不变扩散，20/40/80/160层不挑有利PASS，数值/物理收敛仍按差异保留限制。\n\n'
    for k,c in cases.items():
        if k.startswith('ATTR_'):continue
        x=c['control_path'];md+='### '+k+'\n\n'
        md+=f"B命令首时刻{x['first_B_command_s']}s，真实选择{x['actual_B_selector_s']}s、成对阀全开{x['actual_B_open_pair_s']}s、首次流量{x['first_B_flow_s']}s、首次合格冷返{x['first_B_cold_return_s']}s、冷库存增加{x['first_B_inventory_increase_s']}s。共享B实际流量持续{x['actual_B_flow_duration_s']:.6f}s、体积{x['B_actual_volume_m3']:.6f}m³，源口净热量{x['B_net_source_heat_J']/1e6:.6f}MJ；负值是净抽热。RC服务不冒充共享源侧覆盖。\n\n"
        md+='A供负载而源转B的每个实际持续区间、A库存消耗、峰温和最小流量见ACTUAL_RESULTS.control_path.segments；源泵Q-H交点/相对压差、真实路径、罐口温流焓原始账本见各阶段physical_path.csv及tank_port_ledger.csv。没有静压/NPSH/水锤或实体泄漏资格。\n\n'
        md+=f"首次已测试双罐研究资格：{c['recovery_scan']['first_tested_joint_pass_s']}s（固定采样，不是连续最早时刻）；末态A/B冷量{c['cold_A_final_m3']:.6f}/{c['cold_B_final_m3']:.6f}m³。\n\n"
        md+='每罐固定300秒及末态实际剖面90秒试验首通过采样：'+json.dumps(c['per_tank_qualification']['first_tested'],ensure_ascii=False)+'；不是最早连续时刻，也不保证中间持续就绪。\n\n'
        if c['second_fault']:
            s=c['second_fault'];md+=f"第二事件{s['at_s']}s：事前组件资格{s['pre_event_component_qualified']}，真实90秒峰温{s['maximum_inlet_C']:.6f}°C，最小流量{s['minimum_load_m3_h']:.6f}m³/h，{s['qualification']}。后续继续至1800秒，不重置物理状态。事前不合格时仅诊断；事前合格而系统超温仍为FAIL。\n\n"
        md+='逐罐70%+相对温升与85%+绝对温度分项：\n\n'
        for t in c['customer_component_comparison'] or []:md+=f"- {t['tank']} {t['layers']}层：出口峰值{t['maximum_outlet_C']:.6f}°C，升温{t['rise_K']:.6f}K，70%+升温{t['conditional70_and_rise_only']}，研究85%{t['research85_and_absolute']}。\n"
        md+='\n'
    md+='## 判定与工程边界\n\n如共享B未形成有效流量/焓流/冷量增加，状态为UNREACHABLE或COMMAND_ONLY而不是分支PASS；不得通过人工强制或改判据补覆盖。未达到资格不等于永久不可达，有限1800秒没有客户恢复截止期限。必要硬件缺口不能用本轮有限点直接定量选型。\n\n'
    md+='全链IT2790kW/入液2650.50kW保持，2716.15kW仅预算对照，实际泵热按一次归属；没有免费预冷/第三循环。可选负载B接管候选保留实际断流，不代表已解决无断流。完整3用3备CDU切换、压力分区静压、Kv实物、布水器浮升/CFD和OEM图谱仍缺。\n\n'
    md+='厂家须提供：源泵三/四泵Q-H-效率-NPSHr及启停；湿塔共同DB46/WB30/PG25下2716.15kW预算及真实建冷曲线；15m³罐330m³/h、90s≤0.5K真实回充后曲线和布水器；阀Kv/行程/反馈及隔离泄漏；CDU四温两流量/压降、温度精度与延迟。元件FAT不代替系统第二故障FAT/SAT。无采购、生产、硬件、正式C3C或Phase6批准。\n'
    (d/'ENGINEERING_REPORT_ZH.md').write_text(md,encoding='utf-8')
    template=(HERE/'report_template.html').read_text(encoding='utf-8')
    payload=json.dumps(dict(cases=cases,points=points),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    (d/'engineering_report.html').write_text(template.replace('PAYLOAD',payload),encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
    save(d/'DELIVERY_HASHES.json',dict(source_commit=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],files=hashes,engineering='NOT_APPROVED'))
    return dict(cases=len(cases),delivery_files=hashes,scope='SOURCE_BOUND_DEVELOPMENT_NOT_CUSTOMER_APPROVAL')
