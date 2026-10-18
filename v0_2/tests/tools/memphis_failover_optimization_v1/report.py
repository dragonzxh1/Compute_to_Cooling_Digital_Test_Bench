"""Final persisted-file comparison; no candidate/model imports."""
import json,hashlib,os,html
from pathlib import Path
from .audit import need
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def chart(data,keys,title,reference=None):
    # Scientific SVG: all data derived from persisted numerical rows.
    values=[r[k] for r in data for k in keys]+([] if reference is None else [reference])
    low=min(values);high=max(values);pad=max(.2,(high-low)*.08);low-=pad;high+=pad
    xmax=max(r['time_s'] for r in data);colors=['#167785','#bd6524','#637887']
    parts=[f'<svg viewBox="0 0 800 240" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title>']
    for j in range(5):
        y=25+j*42;v=high-j*(high-low)/4
        parts.append(f'<path d="M65 {y}H780" stroke="#dce4e8"/><text x="58" y="{y+4}" text-anchor="end">{v:.2f}</text>')
    for k,col in zip(keys,colors):
        points=' '.join(f"{65+715*r['time_s']/xmax:.3f},{193-168*(r[k]-low)/(high-low):.3f}" for r in data)
        parts.append(f'<polyline fill="none" stroke="{col}" stroke-width="2" points="{points}"/>')
    if reference is not None:
        y=193-168*(reference-low)/(high-low);parts.append(f'<path d="M65 {y}H780" stroke="#c33" stroke-dasharray="5 4"/><text x="70" y="{y-5}">limit {reference}</text>')
    for t in (0,xmax/4,xmax/2,3*xmax/4,xmax):parts.append(f'<text x="{65+715*t/xmax}" y="218" text-anchor="middle">{t:g}s</text>')
    parts.append('</svg><p>'+html.escape(' / '.join(keys))+'</p>');return ''.join(parts)

def finalize(directory):
    reg=read(HERE/'registration.json');manifest=read(HERE/'source_manifest.json')
    root=ROOT/'artifacts/memphis-failover-optimization-v1-analysis'
    expected=[s for s in reg['cases'] if s['group']!='final'];found={};raw_bindings=[]
    # Compact originals are checked against each raw group index, not treated as
    # a substitute for the full official raw archive or original V2 evidence.
    for index in root.rglob('artifact_hashes.json'):
        doc=read(index);need(doc['source_commit']==os.environ['GITHUB_SHA'],'FINAL_COMMIT_DRIFT')
        base=index.parent;by={x['path']:x for x in doc['records']}
        for f in base.rglob('*'):
            if f.is_file() and f.name!='artifact_hashes.json':
                relative=f.relative_to(base).as_posix();need(relative in by and sha(f)==by[relative]['raw_sha256'],'FINAL_COMPACT_RAW_HASH')
        receipts=read(base/'execution_receipts.json')
        for receipt in receipts['stages']:
            stage=receipt['stage'];need(stage not in found,'FINAL_DUPLICATE_STAGE')
            d=base/stage;result=read(d/'result.json');proof=read(d/'external_job_identity.json');native=read(d/'job_status.json');ready=read(d/'ready.json')
            need(result['stage']==stage and result['status']=='PASS','FINAL_STAGE_FAILURE')
            need(native['assigned_before_resume'] and native['resumed'] and native['cleanup_complete'] and native['active_after_cleanup']==0 and native['child_exitcode']==0 and native['outcome']=='EXITED','FINAL_NATIVE_CLEANUP')
            need(result['pid']==ready['pid']==proof['actual_python_pid'] and proof['in_target_job'] and proof['cpu_rate']==2500 and proof['process_mb']==1024 and proof['job_mb']==2048,'FINAL_ACTUAL_JOB')
            need(result['environment']==result['environment_after'] and result['environment']['source_commit']==os.environ['GITHUB_SHA'],'FINAL_ENVIRONMENT')
            need(result['environment']['job_proof_sha256']==sha(d/'external_job_identity.json'),'FINAL_JOB_PROOF_HASH')
            need(result['analysis']==read(d/'independent_analysis.json'),'FINAL_ANALYSIS_PERSISTENCE')
            found[stage]=(result['analysis'],d)
        raw_bindings.append(dict(group=doc['group'],raw_index_sha256=sha(index),raw_files=len(by)))
    need(set(found)=={s['id'] for s in expected},'FINAL_COVERAGE')
    # Fresh repeat comparison on original raw hash indexes, not rounded plots.
    def raw_case(name,filename):
        d=found[name][1];b=read(d.parent/'artifact_hashes.json')
        return next(x['raw_sha256'] for x in b['records'] if x['path']==name+'/case/'+filename)
    repeat={f:raw_case('COORDINATED_B',f)==raw_case('COORD_REPEAT',f) for f in ('physics.json','series.json')}
    need(all(repeat.values()),'FINAL_REPEAT_DRIFT')
    comparison=[]
    for spec in expected:
        a,d=found[spec['id']]
        if spec['kind']=='negative':continue
        diag=a['diagnosis'];w=a['first90_maximum_inlet_c'];delay=a['first_cold_return_330_delay_s']
        cont=('PASS' if w<=45 and delay is not None and delay<=90 and a['terminal_source_recovery_maintained'] else 'FAIL') if spec.get('recharge') is None else 'INCOMPLETE_NO_FAULT'
        comparison.append(dict(case_id=spec['id'],spec=spec,max_inlet_c=a['maximum_inlet_c'],first90_max_c=w,
            cold_return_delay_s=delay,thermal_verdict=a['grades']['RACK_THERMAL_COMPLIANCE'],
            cooling90_verdict=cont,strict330_verdict=diag['strict_uninterrupted_primary330'],
            full_continuity_verdict='PASS' if cont=='PASS' and diag['strict_uninterrupted_primary330']=='PASS' and a['maximum_inlet_c']<=45 else 'FAIL',
            secondary_branch_verdict=a['independent']['grades']['HYDRAULIC_ADEQUACY'],
            exceedance_K_s=a['thermal_exceedance_K_s'],exceedance_duration_s=a['thermal_exceedance_duration_s'],
            actual_AB=a['actual_AB_switches'],reserve_ready_s=a['reserve_ready_absolute_s'],
            recharge=a['recharge_flow_comparison'],diagnosis=diag))
    base=next(x for x in comparison if x['case_id']=='G_WET_LOSS')
    for a in comparison:
        a['delta_peak_C_vs_baseline']=a['max_inlet_c']-base['max_inlet_c']
        a['cold_return_earlier_s']=None if a['cold_return_delay_s'] is None else base['cold_return_delay_s']-a['cold_return_delay_s']
    payload=dict(status='BOUNDED_SOFTWARE_COMPARISON_COMPLETED',engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',
        execution_commit=os.environ['GITHUB_SHA'],manifest_sha256=sha(HERE/'source_manifest.json'),
        registration_sha256=sha(HERE/'registration.json'),candidate_sha256=manifest['candidate_sha256'],
        comparisons=comparison,repeat=repeat,negative=found['NEGATIVE'][0],raw_groups=raw_bindings,
        source_hashes=manifest,formal=False,production=False,hardware=False,phase6=False)
    out=directory/'comparisons.json';out.write_text(json.dumps(payload,sort_keys=True,indent=2),encoding='utf-8')
    lines=['# 孟菲斯故障切换因果诊断与受控优化 v1','',
        '状态：离线软件比较完成；MEMPHIS_ENGINEERING_NOT_APPROVED。全部工程判定基于登记的未标定模型条件，不构成厂家性能、采购或硬件批准。',
        '',f"执行源码 `{payload['execution_commit']}`；manifest `{payload['manifest_sha256']}`。",'',
        '## 因果结论','',
        '第二次转换是原控制器明确登记的后续热接管，不是又等待54秒的重复启动，也不是此前“故障处理后永不接管”的旧缺陷。第一轮W1→W2仍向A罐供冷，第二轮才因44.5°C和四点温度冷库存证明切B。原程序的RUN仅表示允许源泵启动，不能解释为测得冷水就绪。',
        '',
        '策略弱点：备用源恢复与备用罐接管串行、后者再停源泵换路；故障后对较晚温升作反应。模型限制：54秒是泵停止期间的假设建冷等待，塔无独立启动热状态/实际ready反馈。不能把此计时假设称为厂家建冷性能，也不能把源泵停等计时简单缩短就宣称代码修好。',
        '',
        '所有A/B负载侧转换保留先关后开，因此实际负载流量会暂降至330以下。即使温度或首返改善，严格连续330仍不得标PASS。水锤、静压、NPSHr及弱件MAWP尚无模型/厂家证据。',
        '', '## 实际比较','',
        '|方案|全程最高°C|90秒最高°C|冷返延迟s|温度|90秒冷返回窗口|连续330|完整连续供冷|',
        '|---|---:|---:|---:|---|---|---|---|']
    for a in comparison:
        delay='未达成' if a['cold_return_delay_s'] is None else f"{a['cold_return_delay_s']:.3f}"
        lines.append(f"|{a['case_id']}|{a['max_inlet_c']:.6f}|{a['first90_max_c']:.6f}|{delay}|{a['thermal_verdict']}|{a['cooling90_verdict']}|{a['strict330_verdict']}|{a['full_continuity_verdict']}|")
    lines+=['','## 原始基线事件和体积/能量分解','',
        '各段量为实际离散积分；先后区段不等于可相加的独立根因贡献，冷库存阈值受网格扩散影响。', '',
        '|开始s|结束s|状态|源水量m³|负载水量m³|排热MJ|A冷m³|B冷m³|最高入口°C|',
        '|---:|---:|---|---:|---:|---:|---:|---:|---:|']
    for s in base['diagnosis']['segments']:
        lines.append(f"|{s['start_s']:.1f}|{s['end_s']:.1f}|{s['state']}|{s['source_pumped_m3']:.4f}|{s['load_transported_m3']:.4f}|{s['heat_rejected_MJ']:.4f}|{s['cold_A_end_m3']:.3f}|{s['cold_B_end_m3']:.3f}|{s['max_rack_inlet_c']:.4f}|")
    lines+=['','## 设计决定与供应商RFI','',
        '1. 优先比较不改设备的测量驱动协调接管；不以软件PASS释放采购。保持原V2及本轮全部FAIL作为对照。',
        '2. 要求供应商给出54/20/0秒对应的启动条件、流量/温度曲线、ready测点、预备状态及耗电；预冷初始水量能量信用不是连续预备能力证明。',
        '3. 要求罐几何/布水器/混合/短路和330m³/h×90秒≤0.5K实测；20/40/80/160层及细时间步全部列出，不采用有利网格作选型。',
        '4. 要求源管实际容积、全程流量/阀位和首返测点；1m³只为热容灵敏度，未同步减少真实管阻；2秒阀动作须Kv及水锤/泵零速互锁证明。',
        '5. 独立回充需厂家Q-H/效率/NPSHr证明330，且须解决W2备用与回充共用角色冲突；原00/01仍为共享分段回充。',
        '', '## 判定边界','',
        '不继承正式C3-C资格。五项SEM02严格P1缺口、原PF06不完整、任意POST/OS崩溃/断电原子性未证明、T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED均保持原状。独立快速保护和M1冻结核心未修改。',
        '', '90秒罐单体验收仍为INCOMPLETE；本轮没有重跑原V2全套或单罐试验。恢复时间只用故障后实际可用源330和≤41.4448°C，最终5秒继续满足；不能借首次恢复掩盖后续失败。']
    report='\n'.join(lines)+'\n';(directory/'DESIGN_DECISION_REPORT_ZH.md').write_text(report,encoding='utf-8')
    pieces=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>孟菲斯故障切换比较</title><style>body{font:16px/1.6 system-ui;max-width:1160px;margin:auto;padding:24px;color:#173341;background:#f7fafb}h1,h2{line-height:1.3}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #d5e0e5;text-align:left}svg{width:100%;max-height:300px;background:#fff}svg text{font:13px system-ui;fill:#173341}details{padding:18px 0;border-bottom:1px solid #bbcdd6}summary{font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere}.scroll{overflow:auto}</style><h1>孟菲斯 · 故障切换因果与受控优化</h1><p>实际保存数据 · 离线未标定模型 · MEMPHIS_ENGINEERING_NOT_APPROVED</p><p>温度45°C / 90秒 / 实际330m³/h分别判定。RUN不等于测得冷水到达。</p><div class="scroll"><table><tr><th>方案</th><th>全程°C</th><th>90秒°C</th><th>冷返延迟s</th><th>温度</th><th>90秒冷返</th><th>连续330</th></tr>']
    for a in comparison:pieces.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in (a['case_id'],round(a['max_inlet_c'],4),round(a['first90_max_c'],4),a['cold_return_delay_s'],a['thermal_verdict'],a['cooling90_verdict'],a['strict330_verdict']))+'</tr>')
    pieces.append('</table></div>')
    for a in comparison:
        data=read(found[a['case_id']][1]/'case/plot_data.json')
        pieces.append('<details '+('open' if a['case_id']=='G_WET_LOSS' else '')+'><summary>'+html.escape(a['case_id'])+'</summary>')
        for keys,title,ref in [(['rack_inlet_c','primary_inlet_c','pipe_return_c'],'温度 °C',45),(['source_flow_m3_h','load_flow_m3_h'],'源侧与负载侧实际流量 m³/h',330),(['cold_A_m3','cold_B_m3'],'A/B 阈值冷库存 m³',None)]:pieces+=['<h3>'+title+'</h3>',chart(data,keys,title,ref)]
        pieces+=['<h3>实际事件、区段积分与输入</h3><pre>'+html.escape(json.dumps(a,ensure_ascii=False,indent=2))+'</pre></details>']
    pieces+=['<h2>设计决定报告</h2><pre>'+html.escape(report)+'</pre></html>']
    (directory/'engineering_report.html').write_text(''.join(pieces),encoding='utf-8')
    return dict(status=payload['status'],cases=len(comparison),negative=payload['negative'],raw_groups=raw_bindings,repeat=repeat,
        comparisons_sha256=sha(out),engineering='MEMPHIS_ENGINEERING_NOT_APPROVED')
