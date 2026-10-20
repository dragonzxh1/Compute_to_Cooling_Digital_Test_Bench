"""One report from actual saved execution outputs; no prewritten PASS results."""
import json,os,shutil,hashlib
from pathlib import Path
from html import escape
from .checks import save,require
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def finalize(directory):
    root=ROOT/'artifacts/memphis-loop-validation-v1-analysis';reg=json.loads((HERE/'registration.json').read_bytes())
    cases={};points={}
    for p in root.rglob('loop_summary.json'):
        value=json.loads(p.read_bytes());key=value['id'];require(key not in cases,'DUPLICATE_LOOP_CASE')
        require(value['source_commit']==os.environ['GITHUB_SHA'],'SAME_EXECUTION_CASE_SOURCE')
        cases[key]=value;points[key]=json.loads((p.parent/'plot_data.json').read_bytes())
    expected={x['id'] for x in reg['cases'] if x['kind']=='forward'}
    conditional=list(root.rglob('C_DECISION.json'));require(len(conditional)==1,'EXACT_C_DECISION_REQUIRED')
    c_decision=json.loads(conditional[0].read_bytes())
    if c_decision['status']=='RUN_DECLARED_SOURCE_VFD_MARGIN':expected.add('C_CONDITIONAL_HYDRAULIC')
    require(set(cases)==expected,'ALL_NEW_REGISTERED_CASES_REQUIRED')
    baseline=list(root.rglob('audit_summary.json'));require(len(baseline)==1,'ONE_EXACT_BASELINE_REQUIRED')
    old=json.loads(baseline[0].read_bytes());require(old['baseline_exact_six_hashes'],'BASELINE_EXACT_REQUIRED')
    d=directory/'delivery';d.mkdir()
    save(d/'ACTUAL_RESULTS.json',cases);save(d/'ACTUAL_PLOTS.json',points)
    save(d/'C_DECISION.json',c_decision)
    candidates=[]
    for key in ('RC_PERF500_SECOND','RC_PERF750_SECOND','RC_SECOND_REPAIRED','RC_PERF1250_SECOND'):
        c=cases[key]
        ok=all(c['grades'][x]=='PASS' for x in ('90S_CONTINUITY','THERMAL_COMPLIANCE','LOAD_FLOW_COMPLIANCE','SECOND_FAULT_90S')) and c['second_fault']['pre_event_component_qualified']
        candidates.append(dict(id=key,external_sink_kW=c['parameters']['rc_capacity_kW'],four_requested_gates=ok,
            source_recovery=c['grades']['SOURCE_RECOVERY'],complete90s_cold_return=c['source_cold_delay_s'] is not None and c['source_cold_delay_s']<=90,
            profile_tested_at_s=1800,customer_deadline=None))
    passing=[c['external_sink_kW'] for c in candidates if c['four_requested_gates']]
    sizing=dict(tested=candidates,lowest_passing_tested_sink_kW=min(passing) if passing else None,
        label='FINITE_TEST_GRID_CONDITIONAL_NOT_GLOBAL_MINIMUM_NOT_OEM_SELECTION',customer_recovery_deadline='NOT_REGISTERED',
        heat_source='Hypothetical independent external RC cooling service, not online W2 counted twice')
    save(d/'RC_PERFORMANCE_BOUNDS.json',sizing)
    save(d/'REGISTERED_INPUTS.json',reg);shutil.copyfile(HERE/'customer_originals.json',d/'CUSTOMER_ORIGINAL_EXTRACTS.json')
    md='# 原00/01主回路与双罐可选RC开发验证\n\nMEMPHIS_ENGINEERING_NOT_APPROVED。以下数值均来自本轮保存的实际物理轨迹，不是预测界面。工程FAIL不等于软件执行错误；GitHub绿灯不代表客户方案达标。\n\n'
    md+='执行提交：'+os.environ['GITHUB_SHA']+'；运行：'+os.environ['GITHUB_RUN_ID']+'。原T2基线六份原始文件逐字节复现；原模型不改。\n\n'
    md+='## 实际结果\n\n|案例|最高机柜入口°C|最低负荷m³/h|首次90秒|末态双罐研究放冷|第二事件|\n|---|---:|---:|---|---|---|\n'
    for k,c in cases.items():
        second=c.get('second_fault');sv=second['qualification'] if second else 'NOT_RUN'
        md+=f"|{k}|{c['maximum_inlet_C']:.6f}|{c['minimum_load_m3_h']:.6f}|{c['grades']['90S_CONTINUITY']}|{c['grades']['RESERVE_RECOVERY']}|{sv}|\n"
    md+='\n## 不能据此宣称必须加回路\n\n原拓扑是否达标与本次控制器/假设是否达标必须分开。1800秒是观察窗，不是客户恢复截止期限。任何候选失败只证明当前绑定组合在该有限工况失败，不能证明所有原拓扑方案不可行。RC即使通过也只证明附加冷源假设下的条件性效果，不证明采购必要性。\n\n'
    md+='方案C门禁：'+c_decision['status']+'。只有A/B均未通过且有登记的实际水力缺口，才执行预登记3%源VFD余量诊断，不新增中性循环。\n\n'
    md+='RC有限网格最低四项通过点：'+str(sizing['lowest_passing_tested_sink_kW'])+'kW。网格500/750/1000/1250kW，在固定40.5°C冷源、900s维修返回/1800s第二事件的假设下；不是连续最小值或真实选型。实际合格冷液90秒返回另列，若超过90秒必须保留失败，不可被四项结果隐藏。\n\n'
    for k,c in cases.items():
        md+='### '+k+'\n\n'
        md+=f"A末态合格冷体积{c['cold_A_final_m3']:.6f}m³，B {c['cold_B_final_m3']:.6f}m³；断流{c['zero_flow_duration_s']:.6f}s，流量亏缺{c['deficit_m3']:.6f}m³。\n\n"
        recovery=c['recovery_scan'];md+='最早已测试双罐研究放冷通过时刻：'+str(recovery['first_tested_joint_pass_s'])+'s；不代表此前未采样时刻，也不代表之后持续就绪。\n\n'
        for name,net in c['observed']['tank_energy'].items():md+=f"{name}罐累计净积热{net['delta_U_J']/1e6:.6f}MJ，负载输入{net['load_J']/1e6:.6f}MJ、源及RC合计{net['source_J']/1e6:.6f}MJ、环境{net['ambient_J']/1e6:.6f}MJ。\n\n"
        md+='末态再次90秒试验：\n\n'
        for trial in c['final_full_discharge']:md+=f"- {trial['tank']}罐{trial['layers']}层：最高出口{trial['maximum_outlet_C']:.6f}°C，升温{trial['rise_K']:.6f}K，{trial['status']}。\n"
        if c['second_fault']:
            s=c['second_fault'];md+=f"\n第二事件1800s：事前组件资格{s['pre_event_component_qualified']}；随后90秒峰值{s['maximum_inlet_C']:.6f}°C、最低流量{s['minimum_load_m3_h']:.6f}m³/h；{s['qualification']}。W1在900s返回是假设维修场景，重启仍需54s及真实热管置换，不是实际维修能力证明。\n"
        md+='\n'
    md+='## 保留限制\n\n本轮只验证源侧/储罐/回充及三个运行CDU耦合，未完整建模3用3备CDU接管，不能标成完整00/01系统资格。源泵QH、塔UA、54秒建冷、5秒配对阀、RC1MW/40.5°C冷源、管容积、PG25常物性及1D混合均属工程假设，不是OEM标定。无新增第三中性循环或免费预冷服务。\n\n17TT观测筛选不是完整90秒放冷资格。保留原研究85%体积门槛，与客户70%有效量/10.5m³、90秒8.25m³区分；41.4448°C为原研究罐出口门槛，机柜入口硬限45°C不可混用。80/160及时间步对照不等于真实布水器/CFD收敛。绝对压力、NPSH、水锤、施工接口、电源和共同故障未验证。RC违反原“不新增回充泵”设计边界，需单独变更批准。正式C3-C、采购、生产、硬件、Phase6均未授权。\n'
    (d/'ENGINEERING_REPORT_ZH.md').write_text(md,encoding='utf-8')
    # Presentation reads persisted physical comparisons only, never computes a plant.
    payload=json.dumps(dict(cases=cases,points=points),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>孟菲斯主回路验证</title><style>
body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#f3f6f9;color:#162e40}main{max-width:1240px;margin:auto;padding:28px}h1{font-size:27px}select{font:inherit;padding:10px;max-width:100%}.note{color:#596d7d}section{background:white;border-radius:12px;padding:20px;margin:20px 0}svg{width:100%;display:block}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;text-align:left;border-bottom:1px solid #dae3ea}.table{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#086778}</style><main><h1>原回路优先 · 双罐RC对照</h1><p>实际轨迹回放 / 开发验证 / MEMPHIS_ENGINEERING_NOT_APPROVED</p><label>案例 <select id="case"></select></label><p id="summary"></p><p class="note">没有第三中性循环。新增RC及维修返回为明确研究假设。B回充完成不等于双罐资格；观察窗不是客户恢复期限。</p><section><h2>机柜入口 · °C</h2><div id="thermal"></div></section><section><h2>A/B合格冷库存 · m³</h2><div id="reserve"></div></section><section><h2>实际流量 · m³/h</h2><div id="flow"></div></section><section><h2>真实转换事件</h2><div class="table"><table><thead><tr><th>秒</th><th>原状态</th><th>新状态</th><th>原因</th></tr></thead><tbody id="events"></tbody></table></div></section><section><h2>分项判定</h2><pre id="grades"></pre><a href="ENGINEERING_REPORT_ZH.md">中文工程报告与限制</a></section></main><script>const data=PAYLOAD;
const picker=document.getElementById('case');for(const key of Object.keys(data.cases)){const o=document.createElement('option');o.value=o.textContent=key;picker.append(o)}
function plot(id,rows,series,threshold){const el=document.getElementById(id),w=Math.max(310,el.clientWidth),h=240,pad=48;const ts=rows.map(r=>r.time_s),vals=rows.flatMap(r=>series.map(s=>r[s[0]]).filter(Number.isFinite));if(Number.isFinite(threshold))vals.push(threshold);let lo=Math.min(...vals),hi=Math.max(...vals);const delta=Math.max(.2,(hi-lo)*.1);lo-=delta;hi+=delta;const maxT=Math.max(...ts),x=t=>pad+t/maxT*(w-pad-16),y=v=>h-pad-(v-lo)/(hi-lo)*(h-pad-16);let s=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="实际保存轨迹"><path d="M${pad} 16V${h-pad}H${w-16}" fill="none" stroke="#8093a2"/>`;for(let i=0;i<4;i++){const v=lo+(hi-lo)*i/3;s+=`<text x="2" y="${y(v)+4}" font-size="12">${v.toFixed(1)}</text>`}for(let i=0;i<4;i++){const t=maxT*i/3;s+=`<text x="${x(t)}" y="${h-20}" text-anchor="middle" font-size="12">${t.toFixed(0)}s</text>`}if(Number.isFinite(threshold))s+=`<path d="M${pad} ${y(threshold)}H${w-16}" stroke="#ba443b" stroke-dasharray="5 4"/><text x="${pad+8}" y="${y(threshold)-6}" font-size="12">参考 ${threshold}</text>`;series.forEach(([key,label,color],i)=>{const p=rows.filter(r=>Number.isFinite(r[key])).map((r,j)=>(j?'L':'M')+x(r.time_s).toFixed(2)+' '+y(r[key]).toFixed(2)).join(' ');s+=`<path d="${p}" fill="none" stroke="${color}" stroke-width="2"/><text x="${pad+i*180}" y="${h-2}" fill="${color}" font-size="13">${label}</text>`});el.innerHTML=s+'</svg>'}
function render(){const k=picker.value,c=data.cases[k],r=data.points[k];document.getElementById('summary').textContent=`最高入口 ${c.maximum_inlet_C.toFixed(3)}°C · 最低流量 ${c.minimum_load_m3_h.toFixed(3)}m³/h · 首次90秒 ${c.grades['90S_CONTINUITY']} · 末态储备 ${c.grades.RESERVE_RECOVERY}`;plot('thermal',r,[['rack_C','机柜最高入口','#087c93']],45);plot('reserve',r,[['cold_A_m3','A罐','#087c93'],['cold_B_m3','B罐','#ac621d']],12.75);plot('flow',r,[['load_m3_h','负荷','#087c93'],['source_m3_h','源侧','#ac621d']],330);document.getElementById('grades').textContent=JSON.stringify({grades:c.grades,second_fault:c.second_fault,proposal_checks:c.proposal_checks},null,2);const t=document.getElementById('events');t.replaceChildren();for(const e of c.events){const tr=document.createElement('tr');for(const v of [(e.time_ns/1e9).toFixed(1),e.from_state,e.to_state,e.reason]){const td=document.createElement('td');td.textContent=v;tr.append(td)}t.append(tr)}}picker.addEventListener('change',render);window.addEventListener('resize',render);render();</script></html>'''
    (d/'engineering_report.html').write_text(html.replace('PAYLOAD',payload),encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
    save(d/'DELIVERY_HASHES.json',dict(source_commit=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],files=hashes,engineering='NOT_APPROVED',formal=False))
    return dict(cases=len(cases),baseline_exact=True,delivery_files=hashes,scope='DEVELOPMENT_COMPARISON_ONLY')
