"""One netlist-generated engineering report; no precomputed physical answers."""
import json,csv,shutil,hashlib,os
from pathlib import Path
from math import fsum
from html import escape
from .topology import build,runtime,svg,check_graph
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.checks import save,require
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def rows(path,values):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)

def finalize(directory):
    analysis=ROOT/'artifacts/memphis-topology-audit-v1-analysis'
    found={}
    for p in analysis.rglob('audit_summary.json'):
        a=json.loads(p.read_bytes());require(a['id'] not in found,'DUPLICATE_CASE_EVIDENCE');found[a['id']]=(p,a)
    reg=json.loads((HERE/'registration.json').read_bytes());expected={x['id'] for x in reg['cases'] if x['kind']=='forward'}
    require(set(found)==expected,'ALL_CASES_REQUIRED_FOR_FINAL')
    cases={k:v[1] for k,v in found.items()};baseline=cases['BASELINE_EXACT'];require(baseline['baseline_exact_six_hashes'],'NO_EXACT_BASELINE')
    d=directory/'delivery';d.mkdir()
    graph=build();check_graph(graph)
    final=baseline['keyframes'][-1];bound=runtime(graph,final)
    bound['runtime_keyframes']=[runtime(graph,f) for f in baseline['keyframes']]
    save(d/'04_TOPOLOGY_NETLIST.json',bound)
    modelsvg=svg(runtime(graph,final),'当前源码功能级 P&ID · 1800s 实际末态')
    (d/'01_MODEL_ACTUAL_PID.svg').write_text(modelsvg,encoding='utf-8')
    # SVG is the editable vector original; graph/layout generator are additional editable sources.
    (d/'02_MODEL_ACTUAL_PID_EDITABLE.svg').write_text(modelsvg,encoding='utf-8')
    shutil.copyfile(HERE/'topology.py',d/'02_MODEL_ACTUAL_PID_EDITABLE.py')
    import re
    drawn=set(re.findall(r'data-edge-id="([^"]+)"',modelsvg))
    require(drawn=={e['id'] for e in graph['edges']},'DRAWING_NETLIST_EDGE_MISMATCH')
    views={'A_TANK':['TRANSFER_A','SOURCE_A'],'B_TANK':['TRANSFER_B','SOURCE_B','RC_B'],
           'SOURCE_SWITCH':['SOURCE_A','SOURCE_B'],'LOAD_BUFFER':['NEUTRAL','TRANSFER_A','TRANSFER_B','CDU_PRIMARY_1','CDU_PRIMARY_2','CDU_PRIMARY_3'],
           'RC':['RC_B'],'INSTRUMENTS':['SOURCE_A','TRANSFER_A','SOURCE_B','RC_B']}
    for name,paths in views.items():(d/(name+'.svg')).write_text(svg(runtime(graph,final),name+' · 派生功能图；测点见仪表注册表',paths),encoding='utf-8')
    for name,t in [('RUN',30.),('FAULT',42.9),('RECHARGE',635.9)]:
        f=min(baseline['keyframes'],key=lambda x:abs(x['time_s']-t))
        (d/('STATE_'+name+'.svg')).write_text(svg(runtime(graph,f),name+' '+str(f['time_s'])+'s'),encoding='utf-8')
    docs=json.loads((HERE/'customer_originals.json').read_bytes());save(d/'CUSTOMER_ORIGINAL_EXTRACTS.json',docs)
    diff=[
      dict(item='罐顶部热回液/源泵取液，底部冷源回液/负荷取液',customer='00-P455/P724;01-P49',model='四端口角色一致；负载端现在经新增HX',classification='MATCH',impact='角色匹配不等于新增回路属于客户设计',decision='核实实际接管高程/布水器'),
      dict(item='CDU一次直接由A/B负荷泵供液',customer='00-P724;01-P49',model='新增第三介质缓冲回路及HX-A/B固定串联',classification='SIMULATION_SIMPLIFICATION',impact='重大候选拓扑变化，不能评价原00/01方案',decision='独立候选设计审批；原图不改'),
      dict(item='备用罐补冷',customer='00-P716明确不新增回充泵;01-P175',model='独立1MW RC只接B，额外预冷管回路',classification='DESIGN_CONFLICT',impact='不是客户已确认共享分段补冷；B恢复不能代表A恢复',decision='只允许作为研究候选'),
      dict(item='运行流量',customer='00-P716/719负荷330，源>330恢复A',model='中性负荷330，但A转移约414；源侧仅约373',classification='MODEL_CONNECTION_MISMATCH',impact='源>客户负荷330仍小于新增实际罐转移；恢复假设不再成立',decision='重新绑定新转移环泵QH及恢复条件'),
      dict(item='3用3备CDU及双独立二次环网',customer='00-P724/P757;01-P3/P54',model='3台运行CDU/3条二次回路，备用CDU接管未显式计算',classification='SIMULATION_SIMPLIFICATION',impact='不证明完整客户CDU接管连续性',decision='缺几何/Kv/备用切换数据'),
      dict(item='A/B不并通/供回成对',customer='00-P718/P757;01-P54/P55',model='源选择器零速闭阀后变更；一次A/B无质量跨接',classification='MATCH',impact='代码互锁一致，实阀Kvs/动作仍未验证',decision='厂家FAT及系统SAT分开'),
      dict(item='绝对压力/NPSH/水锤',customer='00-P469;01-P165',model='准稳态压差；绝对压力null',classification='NOT_VERIFIED',impact='不能选承压等级/NPSH或证明水锤安全',decision='静高差/定压/管径长度/泵阀瞬态'),
      dict(item='完整最终P&ID',customer='00-P37/P765表示新版待归档',model='本轮源码功能图不是客户正式施工图',classification='NOT_VERIFIED',impact='不得声称图纸已获设计院批准',decision='需设计方最终接管图及现场Tag')]
    rows(d/'10_TOPOLOGY_DIFFERENCE_MATRIX.csv',diff)
    md='# 客户00/01与当前实际模型对照\n\n原件重新打开并校验SHA256。P为word/document.xml中body后代w:p零基段落，不是页码。客户图仅按文字重建，不是缺失正式图纸的替代品。\n\n'
    for x in diff:md+='## '+x['item']+'\n\n'+x['classification']+'；依据 '+x['customer']+'。模型：'+x['model']+'。影响：'+x['impact']+'。设计方事项：'+x['decision']+'。\n\n'
    for doc in docs['documents']:md+='原件 '+doc['document']+'，SHA256 '+doc.get('raw_sha256','SOURCE_MISSING')+'。\n\n'
    (d/'03_CUSTOMER_00_01_PID_COMPARISON.md').write_text(md,encoding='utf-8')
    # A deliberately separate customer functional drawing: never reuse T2 candidate netlist.
    customer=build();customer['edges']=[];customer['nodes']=[]
    for n in ('A','B'):
        seq=[('TANK_'+n,'BOTTOM_OUT'),('LOAD_PUMP_'+n,'IN'),('3_ACTIVE_CDU_PRIMARY','IN'),('TANK_'+n,'TOP_IN')]
        seq2=[('TANK_'+n,'TOP_OUT'),('SHARED_SOURCE_PUMPS_4','IN'),('SELECTED_D_OR_W','IN'),('TANK_'+n,'BOTTOM_IN')]
        for path,s in [('CUSTOMER_LOAD_'+n,seq),('CUSTOMER_SOURCE_'+n,seq2)]:
            for i,(a,b) in enumerate(zip(s,s[1:])):customer['edges'].append(dict(id=path+str(i),path=path,source_component=a[0],source_port=a[1],destination_component=b[0],destination_port=b[1],fluid_domain=n+'_PG25',flow_m3_h=None,temperature_C=None))
    (d/'CUSTOMER_00_01_FUNCTIONAL_PID.svg').write_text(svg(customer,'00/01文字功能重建 · 非正式施工图 · 无独立RC或第三介质环'),encoding='utf-8')
    for name in ('05_A_TANK_ENERGY_LEDGER.csv','06_B_TANK_ENERGY_LEDGER.csv','07_ALL_CONTROL_VOLUME_LEDGER.csv','09_RECHARGE_CONTROL_TIMELINE.json'):
        shutil.copyfile(found['BASELINE_EXACT'][0].parent/name,d/name)
    save(d/'08_TANK_TEMPERATURE_PROFILES.json',dict(keyframes=baseline['keyframes'],all_physics_steps='08_TANK_TEMPERATURE_PROFILES.jsonl in official BASELINE_EXACT raw artifact; no decimation',initial=baseline['initial_profiles'],mesh_profiles={k:v['keyframes'][-1]['profile'] for k,v in cases.items()}))
    # Persisted ledger is independently read back, not just trusting in-memory CV claims.
    totals={};maxerr=0.;count=0
    with (d/'07_ALL_CONTROL_VOLUME_LEDGER.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            count+=1;tag=r['cv'];maxerr=max(maxerr,abs(float(r['residual_J'])))
            require(abs(float(r['mass_in_kg_s'])-float(r['mass_out_kg_s']))<=1e-9,'PERSISTED_MASS')
            totals[tag]=float(r['cumulative_delta_U_J'])
    for tag,v in totals.items():require(abs(v-baseline['integrals'][tag]['delta_U_J'])<1e-6,'PERSISTED_CUMULATIVE_CV')
    save(d/'INDEPENDENT_LEDGER_READBACK.json',dict(rows=count,max_step_residual_J=maxerr,cumulative_delta_U_J=totals,status='SAVED_CSV_MATCHES_INDEPENDENT_RUNTIME_CV_EQUATIONS',drawing_edge_ids_match=True))
    last=baseline['curves'][-1];diag=cases['TRANSFER330_DIAGNOSTIC'];lastd=diag['curves'][-1]
    def challenge_ready(a):return bool(a['final_challenge']) and all(x['status']=='PASS' for x in a['final_challenge'])
    hypotheses=[
      dict(id='H1',claim='A源侧排热不足是唯一原因',verdict='NOT_SUFFICIENT_AS_SOLE_EXPLANATION',evidence=baseline['integrals']['TANK_A'],counterevidence='Use cumulative A balance and temperature-profile transport; whole-site rejection includes RC_B and cannot certify A cold-volume rebuild',controlled_test='TRANSFER330_DIAGNOSTIC; unchanged tower/RC/storage/limits'),
      dict(id='H2',claim='冷源回液足够冷但未建立大体积冷层',verdict='SUPPORTED_IN_CURRENT_DISCRETE_MODEL',evidence=dict(final=last,profile=final['profile']['A']),counterevidence='Bottom temperature alone cannot establish90s reserve; compare all grids and actual discharge',controlled_test='MESH20/40/80/160,DT005,TRANSFER330_DIAGNOSTIC'),
      dict(id='H3',claim='A顶部/底部接反',verdict='NO_REVERSED_PORT_EVIDENCE; T2_TOPOLOGY_DIFFERS_FROM_CUSTOMER',evidence='00-P455/P724 and source-bound tank port equations',counterevidence='Actual nozzle elevation/diffuser geometry absent; cannot assert real flow-field correctness',controlled_test='source-only/load-only/equal/unequal port FV vectors'),
      dict(id='H4',claim='两闭合回路错误叠加成泄漏',verdict='NO_MASS_LEAK_OR_DISCRETE_FACE_SIGN_ERROR_FOUND',evidence=dict(cv_rows=count,baseline_net_down_m3_h=last['transfer_m3_h']-last['source_m3_h']),counterevidence='Correct conservative1D equations are not proof of real diffuser/mixing',controlled_test='independent face flux vectors and every-layer every-step reconstruction'),
      dict(id='H5',claim='0.1875m3是假失败',verdict='QUANTIZED_VOLUME_NOT_REAL_PRECISION; SEE_GRID_STUDY',evidence={k:dict(final_A=v['curves'][-1]['A_cold_m3'],challenge=v['final_challenge']) for k,v in cases.items() if k in ('BASELINE_EXACT','MESH20','MESH40','MESH160','DT005')},counterevidence='Actual outlet90s challenge is independent of cold-cell count',controlled_test='4fullforward grids + smallerdt, no favorablemesh selection'),
      dict(id='H6',claim='B回充完成被当双罐恢复',verdict='CONTROL_LOGIC_GAP_IN_READY_SEMANTICS',evidence=baseline['events'],counterevidence='Existing controller does request4sourcepumps based on A17TT, but stopping RC only follows B17TT; no full-discharge/dual-ready flag',controlled_test='read actual released17TT timeline versus independent physical profiles'),
      dict(id='H7',claim='客户实际方案必然无法恢复',verdict='NOT_PROVEN; CONDITIONAL_T2_DESIGN_LIMITATION_ONLY',evidence=dict(baseline_dual_ready=challenge_ready(baseline),diagnostic_dual_ready=challenge_ready(diag),diagnostic_end=lastd),counterevidence='00/01 load tank circuit330, not this414T2loop; OEM curves/mixing/deadline unknown',controlled_test='single-variableT2transferresistance QH and continuous true-state secondfault')]
    save(d/'11_CAUSAL_HYPOTHESIS_TESTS.json',hypotheses)
    requirements=[dict(condition='源侧流量必须超过实际A转移流量，且回液合格',current=last['source_m3_h'],reference=last['transfer_m3_h'],unit='m3/h',status='NECESSARY_FOR_BULK_UPWARD_REBUILD_IN_CURRENT1D_PORT_MODEL_NOT_SUFFICIENT',missing='PG25QH/冷塔排热/真实布水器'),
      dict(condition='恢复时间',current=None,reference=None,unit='s',status='CUSTOMER_DEADLINE_NOT_REGISTERED',missing='允许第二故障间隔；不虚构600或1800秒合同'),
      dict(condition='恢复A库存所需净合格流量下界',current=last['source_m3_h']-last['transfer_m3_h'],reference='(V_required-V_available)/recovery_hours',unit='m3/h',status='NEGATIVE_BASELINE; energy andmixing must also hold',missing='设计恢复时限/流量能力'),
      dict(condition='两罐90秒组件资格与整系统二次故障分别通过',current=str(challenge_ready(diag)),reference='All component gates + full coupled secondfault',unit='separate_verdicts',status='SEE_ACTUAL_COMPARISONS',missing='厂家标定/定压/NPSH/真实双CDU接管')]
    rows(d/'12_RESERVE_RESTORATION_REQUIREMENTS.csv',requirements)
    numerical=[]
    for k in ('MESH20','MESH40','BASELINE_EXACT','MESH160','DT005'):
        a=cases[k];prof=a['keyframes'][-1]['profile']['A'];cap=1009*4000*15/len(prof)
        numerical.append(dict(case=k,layers=len(prof),dt_s=a['parameters']['dt_s'],A_cold_m3=a['curves'][-1]['A_cold_m3'],A_bottom_C=prof[0]-273.15,
            A_enthalpy_MJ=cap*fsum(x-273.15 for x in prof)/1e6,extractable_to_threshold_MJ=cap*fsum(max(0.,314.5948-x) for x in prof)/1e6,
            challenge=a['final_challenge'],status='NUMERICAL_INCOMPLETE_REAL_MIXING_UNCALIBRATED'))
    save(d/'NUMERICAL_STUDY.json',numerical)
    save(d/'ACTUAL_AUDIT_RESULTS.json',cases)
    # One concise report with actual computed values, no claims from GitHub green.
    lines=['# 孟菲斯实际仿真拓扑与逐控制体能量审计','',
      'MEMPHIS_ENGINEERING_NOT_APPROVED。当前图是源码功能连接，不是现场竣工/施工P&ID。新T2候选不是客户00/01；不能据其失败宣布客户最终方案失败。',
      '', '## 原样复现与账本', '',
      'BASELINE_EXACT重新运行，physics/series/phases/source_phases/measurements/source_observations六份原始文件SHA256与run39231568548完全一致。只增加观察器，没有修改原模型输出。',
      f'已核对{count}条逐控制体CSV记录；最大单步残差{maxerr:.9g}J。PG25按原模型rho1009/cp4000常值，非OEM标定物性。热交换界面两侧质量独立，热量相反；嵌套控制体不能简单加总。',
      '', '## A罐机制', '',
      f'1800s A转移{last["transfer_m3_h"]:.9f}m³/h，源侧{last["source_m3_h"]:.9f}m³/h；净层间流动向下{last["transfer_m3_h"]-last["source_m3_h"]:.9f}m³/h。这不是漏水，每条回路进出质量相等。',
      f'A末态底层{final["profile"]["A"][0]-273.15:.6f}°C，第二层{final["profile"]["A"][1]-273.15:.6f}°C。80层阈值只计一层，{last["A_cold_m3"]:.6f}m³是网格量化结果，不是实罐可用冷水精度。',
      '当源流量低于转移流量，上层热水向下补充底部抽液；源侧冷回液能维持底部局部冷温，但不能使整体热跃层向上扩展。需结合逐层独立离散核验与网格结果，不把一维模型当真实布水器性能。',
      '', '## 受控诊断与实际结果', '',
      '只将新增转移环端口阻力从15kPa改为85.92kPa@330，使原泵QH交点变化；其他塔能力、RC1MW、储罐容积和客户硬限不变。这是诊断性反事实，不是建议加阀节流或OEM选型。',
      '|案例|A冷库存m³|B冷库存m³|最高入口°C|最低负荷m³/h|双罐组件储备|',
      '|---|---:|---:|---:|---:|---|']
    for k,a in cases.items():
        z=a['curves'][-1];lines.append(f'|{k}|{z["A_cold_m3"]:.6f}|{z["B_cold_m3"]:.6f}|{a["maximum_inlet_C"]:.6f}|{a["minimum_load_m3_h"]:.6f}|{"PASS" if challenge_ready(a) else "FAIL"}|')
    lines+=['','## 回充控制与第二故障','','独立RC硬接B罐。B17TT估计达到85%触发停止，泵归零后recharge_done=True；不等于A储备或双罐再次90秒资格。原控制器已有A17TT触发4源泵，但没有以实际转移流量414重定义恢复前提，也没有双罐完整放冷就绪信号。所有估计只来自已发布测量，独立真值不反灌控制器。']
    for k in ('BASELINE_SECOND1800','TRANSFER330_SECOND1800'):
        a=cases[k];pre=a['second_fault_preconditions'];ready=bool(pre) and all(x['status']=='PASS' for x in pre)
        lines += [f'{k}：1800s前置双罐组件资格{"PASS" if ready else "FAIL"}；实际第二90秒结果{a["grades"]["SECOND_FAULT_90S"]}。'+('仅当前条件下二次事件验证，不是硬件资格。' if ready else '仅UNQUALIFIED_DIAGNOSTIC，禁止当恢复冗余后正式二次故障PASS。')]
    lines+=['','## 限制及设计方决策','','20/40/80/160整程及更小时间步结果见NUMERICAL_STUDY.json；尚未证明真实混合/布水器收敛，保持NUMERICAL_INCOMPLETE。原研究85%冷库存门槛与客户70%有效容积、8.25m³实际90秒需求分开，不放宽原门槛取PASS。',
      '需要真实PG25泵曲线、冷塔性能面、阀Kv/行程、管容积、罐接口高程/布水器、定压/NPSH/瞬态、备用CDU拓扑及客户恢复时限。没有这些只能CONDITIONAL_FEASIBILITY。未扫描额外RC容量。',
      '软件账本验证、模型拓扑来源、储备资格、客户一致性、OEM标定和采购授权必须分别判定。冻结M1/C3-C不变；未合并、未发版、未批准采购、未控制硬件、未进入Phase6。']
    report='\n'.join(lines)+'\n';(d/'13_ENGINEERING_REPORT_ZH.md').write_text(report,encoding='utf-8')
    make_html(d,graph,cases,diff,report)
    manifest=dict(schema='TOPOLOGY-AUDIT-DELIVERY-v1',source_commit=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
        source_manifest_sha256=hashlib.sha256((HERE/'source_manifest.json').read_bytes()).hexdigest(),parent=reg['parent_execution'],
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()},customer_originals=docs,
        engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',OEM='CALIBRATION_REQUIRED',procurement=False,formal=False,hardware=False,phase6=False,
        independent_official_zip_and_native_cleanup='PENDING_POST_EXIT_FILE_VERIFICATION_NOT_IMPLIED_BY_THIS_REPORT')
    save(d/'15_SOURCE_AND_EVIDENCE_MANIFEST.json',manifest)
    return dict(status='SOFTWARE_AUDIT_FILES_GENERATED_PENDING_EXTERNAL_VERIFICATION',cases=8,delivery_files=len(list(d.iterdir())),engineering='MEMPHIS_ENGINEERING_NOT_APPROVED')

def make_html(d,graph,cases,diff,report):
    data={k:dict(curves=a['curves'],keyframes=a['keyframes'],grades=a['grades'],challenge=a['final_challenge'],pre_second=a['second_fault_preconditions']) for k,a in cases.items()}
    diagrams=[svg(runtime(graph,f),'实际流路 '+str(f['time_s'])+'s') for f in cases['BASELINE_EXACT']['keyframes']]
    options=''.join('<option>'+escape(k)+'</option>' for k in data)
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>孟菲斯源码拓扑与能量审计</title>
<style>body{font:16px/1.6 system-ui,Microsoft YaHei,sans-serif;color:#172b3a;background:#f5f7fa;margin:0}main{max-width:1440px;margin:auto;padding:24px}h1{font-size:28px}h2{margin-top:32px}select,input,button{font:inherit;padding:8px;max-width:100%}section{background:white;margin:18px 0;padding:20px;border:1px solid #dbe2e8}svg{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #dbe2e8;text-align:left;overflow-wrap:anywhere}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.plots{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:760px){.plots{grid-template-columns:1fr}main{padding:10px}}.warning{color:#9f391e}</style>
<main><h1>源码真实流路与储冷去向</h1><p class="warning">MEMPHIS_ENGINEERING_NOT_APPROVED · 仿真实际功能图，非施工图。T2新增缓冲/RC候选不是客户00/01。</p>
<section><h2>当前模型与客户设计</h2><div class="controls"><button id="model">当前模型</button><button id="customer">00/01文字重建</button><label>实际关键时刻 <select id="frame"></select></label></div><div id="pid"></div><p id="pidnote"></p></section>
<section><h2>实际计算轨迹</h2><div class="controls"><label>案例 <select id="case">OPTIONS</select></label><label>时间 <input id="time" type="range" min="0" value="0"></label><output id="clock"></output></div><div class="plots"><div id="inventory"></div><div id="thermal"></div><div id="energy"></div><div id="flow"></div></div><div id="point"></div></section>
<section><h2>A/B实际四端口与账本边界</h2><p>温度取步开始端口状态；流量为当前步实际QH；绝对压力未建模。泵/CDU热已在接口焓流中，不在罐账本重复加入。</p><div class="scroll" id="ports"></div></section>
<section><h2>各项资格分别判定</h2><pre id="grades"></pre><pre id="challenge"></pre></section>
<section><h2>客户设计差异</h2><div class="scroll" id="diff"></div></section>
<section><h2>合并工程报告</h2><pre>REPORT</pre></section></main>
<script>const D=__DATA__,DIAGS=__DIAGRAMS__,CUSTOMER=__CUSTOMER__,DIFF=__DIFFDATA__;
const $=id=>document.getElementById(id);const E=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
let kind='model';const base=D.BASELINE_EXACT;for(let i=0;i<base.keyframes.length;i++)$('frame').add(new Option(base.keyframes[i].time_s+' s',i));
function pid(){const i=+$('frame').value;$('pid').innerHTML=kind==='model'?DIAGS[i]:CUSTOMER;$('pidnote').textContent=kind==='model'?'箭头表示登记正向，零流量以Q=0标识。A/B图重复罐端口是同一控制体，不是额外储罐。':'客户文字仅能重建功能连接；完整正式阀件、几何及施工图未提供。';}
$('model').onclick=()=>{kind='model';pid()};$('customer').onclick=()=>{kind='customer';pid()};$('frame').onchange=pid;
function table(rows){if(!rows.length)return '';const keys=Object.keys(rows[0]);return '<table><thead><tr>'+keys.map(k=>'<th>'+E(k)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+keys.map(k=>'<td>'+E(r[k]??'NOT_VERIFIED')+'</td>').join('')+'</tr>').join('')+'</tbody></table>';}
function plot(id,rows,keys,title,unit){const w=600,h=235,left=70,right=20,top=35,bottom=45;const vals=rows.flatMap(r=>keys.map(k=>r[k]));let lo=Math.min(...vals),hi=Math.max(...vals);let pad=Math.max(.01,(hi-lo)*.08);lo-=pad;hi+=pad;const xmax=rows.at(-1).time_s;const x=t=>left+t/xmax*(w-left-right),y=v=>h-bottom-(v-lo)/(hi-lo)*(h-top-bottom);let s='<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-label="'+E(title)+'"><text x="10" y="20" font-size="15">'+E(title)+' / '+unit+'</text>';
for(let i=0;i<4;i++){let v=lo+(hi-lo)*i/3;s+='<path d="M'+left+' '+y(v)+'H'+(w-right)+'" stroke="#d9e0e7"/><text x="4" y="'+(y(v)+4)+'" font-size="12">'+v.toFixed(2)+'</text>';let t=xmax*i/3;s+='<text x="'+x(t)+'" y="'+(h-20)+'" font-size="12">'+t.toFixed(0)+'s</text>';}
const colors=['#156d9b','#ba5c20','#3e7b54'];keys.forEach((k,i)=>{s+='<path d="'+rows.map((r,j)=>(j?'L':'M')+x(r.time_s)+','+y(r[k])).join(' ')+'" fill="none" stroke="'+colors[i]+'" stroke-width="2"/><text x="'+(80+i*160)+'" y="'+(h-3)+'" font-size="12" fill="'+colors[i]+'">'+E(k)+'</text>';});s+='</svg>';$ (id).innerHTML=s;}
function show(){const a=D[$('case').value];$('time').max=a.curves.length-1;const r=a.curves[Math.min(+$('time').value,a.curves.length-1)];$('clock').textContent=r.time_s+' s';$('point').textContent='实际选点 '+JSON.stringify(r);plot('inventory',a.curves,['A_cold_m3','B_cold_m3'],'阈值冷库存，非保证可用体积','m³');plot('thermal',a.curves,['rack_C','source_return_C'],'机柜入口与冷源返回','°C');plot('energy',a.curves,['A_delta_U_MJ','B_delta_U_MJ'],'罐累计储能变化','MJ');plot('flow',a.curves,['source_m3_h','transfer_m3_h'],'不同闭合回路的实际流量','m³/h');$('grades').textContent=JSON.stringify(a.grades,null,2);$('challenge').textContent=JSON.stringify({final_component:a.challenge,second_fault_preconditions:a.pre_second},null,2);
const f=a.keyframes.reduce((best,v)=>Math.abs(v.time_s-r.time_s)<Math.abs(best.time_s-r.time_s)?v:best);let rows=[];for(const n of ['A','B']){const t=f.tanks[n];rows.push({罐:n,时刻:f.time_s,顶部热入_m3h:t.load_m3_s*3600,顶部热入_C:t.return_k-273.15,底部冷出_m3h:t.load_m3_s*3600,底部冷出_C:t.old_k[0]-273.15,顶部热出_m3h:t.source_m3_s*3600,顶部热出_C:t.old_k.at(-1)-273.15,底部冷入_m3h:t.source_m3_s*3600,底部冷入_C:t.source_in_k-273.15});}$('ports').innerHTML=table(rows);}
$('case').onchange=()=>{$('time').value=0;show()};$('time').oninput=show;$('diff').innerHTML=table(DIFF);pid();show();</script></html>'''
    for key,value in [('OPTIONS',options),('REPORT',escape(report)),('__DIFFDATA__',json.dumps(diff,ensure_ascii=False)),('__DIAGRAMS__',json.dumps(diagrams,ensure_ascii=False)),('__CUSTOMER__',json.dumps((d/'CUSTOMER_00_01_FUNCTIONAL_PID.svg').read_text(encoding='utf-8'),ensure_ascii=False)),('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))]:
        html=html.replace(key,value)
    (d/'14_INTERACTIVE_ENGINEERING_REPORT.html').write_text(html,encoding='utf-8')
