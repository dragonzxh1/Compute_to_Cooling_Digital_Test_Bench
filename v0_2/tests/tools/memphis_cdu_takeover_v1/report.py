"""One consolidated source-bound report; engineering gates never inferred from green."""
import json,os,hashlib,shutil
from pathlib import Path
from .stages import require,save
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def finalize(d):
    reg=json.loads((HERE/'registration.json').read_bytes());root=ROOT/'artifacts/memphis-cdu-takeover-v1-analysis';cases={};points={}
    for p in root.rglob('summary.json'):
        r=json.loads(p.read_bytes());require(r['source_commit']==os.environ['GITHUB_SHA'] and r['id'] not in cases,'FINAL_EXACT_UNIQUE_EXECUTION')
        cases[r['id']]=r;points[r['id']]=json.loads((p.parent/'case/plot_data.json').read_bytes())
    require(set(cases)=={x['id'] for x in reg['cases'] if x['kind']=='forward'},'ALL_REGISTERED_CASES_REQUIRED')
    out=d/'delivery';out.mkdir();save(out/'ACTUAL_RESULTS.json',cases);save(out/'REGISTERED_INPUTS.json',reg)
    for f in ('SOURCE_BASIS_AND_ASSUMPTIONS.md','customer_basis.json','source_manifest.json'):shutil.copyfile(HERE/f,out/f)
    shutil.copyfile(HERE/'diagram/runtime_pid.svg',out/'runtime_pid.svg')
    md='# 孟菲斯CDU接管与真实储冷耗用\n\nMEMPHIS_ENGINEERING_NOT_APPROVED。开发执行与离散账本核验不等于客户设计批准。\n\n'
    md+='执行'+os.environ['GITHUB_SHA']+' / run'+os.environ['GITHUB_RUN_ID']+'。原00/01明确三用三备，但最终新版施工PID与详细故障矩阵SOURCE_MISSING；候选细节不是批准阀序。\n\n'
    md+='## 每组结果独立判断\n\n|实际案例|六柜单元|峰温°C|最低一次m³/h|最低二次m³/h|首次90秒温/局部流量|\n|---|---|---:|---:|---:|---|\n'
    for k,r in cases.items():
        for i,u in enumerate(r['units']):md+=f"|{k}|U{i}|{u['max_C']:.6f}|{u['min_primary']:.6f}|{u['min_secondary']:.6f}|{r['first90']['thermal']}/{r['first90']['local_primary_and_secondary_flow']}|\n"
    md+='\n无故障CASE的30–120s只是登记对照窗，不是发生了故障；一次330与每组110、二次每组68.37分别列出。局部低流不因总管足够而放行。\n\n'
    for k,r in cases.items():
        w=r['B_path'];md+='## '+k+'\n\n'
        md+=f"末态CDU状态：{r['final_CDU_states']}。实际B负载体积{w['B_load_volume_m3']:.6f}m³；B初始/最低冷库存{w['B_initial_cold_m3']:.6f}/{w['B_min_cold_m3']:.6f}m³。真实罐口热回使温层变化，不按时间虚扣。\n\n"
        md+=f"补B首命令{w['B_command_s']}s、实际源侧B流{w['B_flow_s']}s、合格冷返{w['B_cold_return_s']}s、冷库存回升{w['B_inventory_increase_s']}s，B源口净热{w['B_net_source_J']/1e6:.6f}MJ。负值为抽热；命令或有流不单独算回充成功。\n\n"
        md+='分项：'+json.dumps(r['statuses'],ensure_ascii=False)+'。阶段：'+json.dumps(r['gates'],ensure_ascii=False)+'。负对照：'+r['negative_control']+'。\n\n'
        md+='M1锁存FAULT（六CDU泵顺序U0A/U0B/U1A/U1B/U2A/U2B）：'+str(r['m1_fault_latched'])+'。不自动清锁；物理接管完成不等于无故障可投运。\n\n'
        md+='首次各节点超过45°C的实际时刻：'+json.dumps(r['first_45C_crossing_s'],ensure_ascii=False)+'。45°C机柜硬限不替代一次供温测点。原始各节点曲线见timeline.csv、physics.json。\n\n'
        md+='|接管时间s|单元|原状态|新状态|测量依据|\n|---:|---|---|---|---|\n'
        for e in r['CDU_events']:md+=f"|{e['time_ns']/1e9:.3f}|U{e['unit']}|{e['from_state']}|{e['to_state']}|{e['measurement_id']} / {e['reason']}|\n"
        md+='\n每个固定采样真实剖面的330m³/h、90秒放冷结果：\n\n|采样s|罐|网格|峰值°C|升温K|研究完整判定|\n|---:|---|---:|---:|---:|---|\n'
        for sample in r['qualification']:
            for t in sample['trials']:md+=f"|{sample['time_s']:.1f}|{t['tank']}|{t['layers']}|{t['maximum_outlet_C']:.6f}|{t['rise_K']:.6f}|{t['status']}|\n"
        if r['pre_second']:
            md+='\n第二故障继承完整温层/管温/泵阀和启动历史，无理想重置；事前资格不合格则仅诊断。\n\n|单元|第二90秒峰温°C|最小一次|最小二次|\n|---|---:|---:|---:|\n'
            for i,u in enumerate(r['units']):md+=f"|U{i}|{u['second90_max_C']}|{u['second90_min_primary']}|{u['second90_min_secondary']}|\n"
        md+='\n独立能量账本：'+json.dumps(r['energy'],ensure_ascii=False)+'；逐CV及HX核对：'+json.dumps(r['independent'],ensure_ascii=False)+'。\n\n'
    md+='## 归因与十四项最终回答\n\n'
    baseline=cases['B_CDU_FAILURE'];source=cases['A_SOURCE_ONLY']
    md+='旧53.580°C是旧版未完成CDU链的保存结果，本轮不篡改、不借其PASS。新源故障单变量对照：\n\n|案例|首次90秒最高机柜°C|其余物理输入|\n|---|---:|---|\n'
    for k in ('A_SOURCE_ONLY','SOURCE_STARTUP0','SOURCE_COLD_PIPE'):md+=f"|{k}|{max(u['first90_max_C'] for u in cases[k]['units']):.6f}|见精确登记|\n"
    md+='\n不能把不同版本流体容积、拓扑和控制同时变化造成的温差全部说成接管收益。新UA/步长/混合对照仅比较共同故障90秒；网格均保留，无有利挑选。\n\n'
    md+='1. CDU真实接管是否完成：看B/C/D的actual事件及两侧流/四温，不看状态名；结果逐CASE在上文。\n2. 三组六柜是否持续供冷：逐组最差温度、一次与二次流同时判断，任何一组FAIL就不满足整组连续性。\n3. 是否真实耗用储冷：B累计实际供液及温层变化、A/B罐口焓流均有原始账本，不是虚拟倒计时。\n4. 哪罐承担负载：原运行CDU从A取液；被接管单元的备用CDU从B取液，其余单元仍A，具体流量逐步保存。\n5. 旧补B为何不触发：旧均温与库存门槛及暖B人工起点，随后新预算也未满足，原控制链没有真实B放冷事件。\n6. 本次补B是否有效：仅B命令、实际源流、净抽热、冷库存回升全部出现才算；详见B_path和阶段4。\n7. B何时恢复：固定300s和末态剖面挑战中的已测试时刻，不推断未采样连续最早时刻。\n8. A何时恢复：与B独立同样判，不将B回充结束称系统恢复。\n9. 双罐何时同时合格：要求同一真实采样两罐全部90s试验通过，原研究85%与客户70%须分开。\n10. 第二次故障是否通过：事前双罐不合格则UNQUALIFIED_DIAGNOSTIC，即使某条温度合格也不算整体通过。\n11. 53.580°C物理原因：原源启动无排热、暖管底部回入与不完整备用路径是已知研究因素；本轮节点先升温序列和单参数数值在上文，不能直接定案客户设计缺陷。\n12. 是否需要RC：本轮没有RC，也未反求其必要性；分支或资格未闭合不等于必须新增RC。\n13. 未标定依赖：UA、常物性、合成QH、管容、阀时序、温层混合、备用源54s、测量延迟、零流泵热及共有机柜接口均需确认。\n14. 客户/OEM待确认：最终P&ID与CDU故障矩阵/一次常态选网、一次/二次PG曲线及局部最低流量、UA/污垢和热惯性、双罐放冷/实际回充、压力/NPSH/水锤、恢复SLA。元件FAT不能代替系统接管/第二故障FAT与SAT。\n\n'
    md+='## 判定约束\n\nGATE1缺施工与联锁依据，不能声明FULL ENGINEERING PASS。早期失败后所有后续结果DIAGNOSTIC_ONLY。负对照未激发只记INCOMPLETE，不再阻断无关诊断；源码/环境/因果/守恒/Job完整性错误仍立即停止，不绕guard。\n\n客户70%有效量及出液升温≤0.5K不由新研究替代。原85%/41.4448°C挑战原函数未修改；额外70%比较仅条件性口径，不能隐藏绝对温度或源侧恢复失败。原Startup49/50/compatibility、SEM02五项strict P1 B/C缺口、PF06原域INCOMPLETE、任意POST/崩溃/断电原子性NOT_PROVEN、T09 HOLD/fullP不可用/hardware CALIBRATION_REQUIRED全部保持，本项目不继承正式C3-C批准。\n'
    (out/'ENGINEERING_REPORT_ZH.md').write_text(md,encoding='utf-8')
    payload=json.dumps(dict(cases=cases,points=points),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    template=(HERE/'report_template.html').read_text(encoding='utf-8').replace('PID_SVG',(HERE/'diagram/runtime_pid.svg').read_text(encoding='utf-8'))
    (out/'engineering_report.html').write_text(template.replace('PAYLOAD',payload),encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    save(out/'DELIVERY_HASHES.json',dict(source_commit=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],files=hashes,engineering='MEMPHIS_ENGINEERING_NOT_APPROVED'))
    return dict(cases=len(cases),delivery_hashes=hashes,scope='FULL_REGISTERED_DEVELOPMENT_EXECUTION; NOT_FULL_ENGINEERING_PASS')
