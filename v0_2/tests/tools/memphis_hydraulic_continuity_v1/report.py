"""One consolidated numerical decision report, without aggregate design approval."""
import json,os,html,csv
from pathlib import Path
from .checks import save,require,digest
from .scenarios import cases
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

TOPOLOGY='''## 功能拓扑及隔离边界

### T0 旧单负荷选择器模型

`A罐 / B罐 → 单选择器先关后开 → 负荷泵 → 3个运行CDU → 对应罐`

它未完整表达00/01每环网独立负荷泵及每6柜备用CDU，只是旧抽象的对照，不直接认定原设计必然断流。

### T1 00/01已有源侧/负荷侧解耦

`运行A罐冷侧 → A负荷泵 → 3个运行CDU → A罐热侧`保持运行；共用源泵在停泵、闭旧供回阀确认后，选择合法源及同一目标罐。源设备故障、A环网需隔离与CDU故障是不同场景。

原设计还允许仅一对CDU/负荷泵短时重叠。完整双二次环网接管图、Kv和动态尚未绑定，本轮不伪造这一候选的全模型PASS：`DUAL_CDU_PAIR_MODEL=NOT_RUN_PENDING_DETAILED_BINDINGS`。

### T2 明确新增的隔离缓冲候选

`A罐 ↔ A转移泵/隔离阀 ↔ HX-A一次侧 ↔ A罐`

`B罐 ↔ B转移泵/隔离阀 ↔ HX-B一次侧 ↔ B罐`

`独立负荷缓冲罐 → 新连续负荷泵 → 3个CDU → HX-A负荷侧 → HX-B负荷侧（两台固定串联，不随一次侧切换关闭）→ 缓冲罐`

A/B一次液体不与新负荷液体混合，只作换热；切换期间仅一个转移支路实际供热交换，独立缓冲支撑负荷流量。新增1/3/5m³罐、两台独立换热器、连续泵一用一备及传感器/阀/供电接口。UA4MW/K为未标定假设；两台固定串联换热器负荷侧各50kPa、连接阀及口合计15kPa，计入新回路总270.92kPa@330m³/h。新泵Q-H曲线按该点注册，实际流量仍由交点求得，额外20%阻力负控不重选泵、不强制330。该点电功率约35.48kW@效率0.7，45kW仅电机预算，不能当OEM型号。转移回路删去旧3CDU135.92kPa，改为单台新HX50kPa+原管20kPa+新增阀口15kPa=85kPa@330，复用旧泵曲线求实际流量，不虚构免费换热器、不误将旧CDU串在新转移回路。须用真实换热器两侧损失复核整个分配，不能视为已有设备有余量。两台换热器负荷侧始终通流，仅选中一次侧交换热；未选中一次侧无免费冷量。换热器金属及负荷侧管道热容量以缓冲容积集总，未解析支管输送迟滞。各泵热只计一次。旧A/B负荷泵在此候选中改作转移用途，须设计方核查改接，不是自动批准。

以上是P&ID级功能边界，不是可施工PID；须补口径、设备位号、死角/排气/补水/膨胀、阀Kv、止回、维护隔离、静压/NPSH及瞬态校核。

## 回充边界

共享源方案逐段给B补冷、限时回A、必要时4泵恢复A，不能A/B同时直通，不能把4×110当实际440。独立RC500/1000kW方案是另加热服务、泵、管线和电源，不重复借在线W2冷量。1800秒只为研究观察窗，二次故障允许间隔需业主另定。

每个已保存真实温层直接用于80/160层保守细化再放冷90秒，不重置理想初态。全程出罐绝对温度≤41.4448°C、初始冷库存≥85%及温升≤0.5K须同时满足。回液边界取48.29°C与该次正向仿真实际最高回液较大者，属于保守常值部件试验，不是假称控制器预知未来。

恢复时间按故障后的60秒已保存温层试放冷，首个通过区间再按10秒细分；只报最早已测试通过时刻，不能声称未采样时段必然不通过或恢复单调。SECOND_SHARED_900与SECOND_RC1000_900另在900秒固定注入W2故障，沿用连续热状态、阀和PLC，不重置温层；分别直接计算后续完整90秒热/流，不以部件资格代替系统试验。900秒为登记比较间隔，不是业主允许故障间隔。非零混合的物理网格收敛、未知最坏回液和OEM保证仍不完备。

## 实施接口及需核实的增减项

|候选|设备变化|必须联锁/取证|未解决约束|
|---|---|---|---|
|T1 原运行负荷环保持|不因单一源故障切断负荷；源端预冷环、17点TT、快保护为新增假设|源泵零速+旧供回两阀闭反馈才可改选；新路径实际流量及近远TT/TTL/保持时间|备用CDU完整二次水力接管尚未建模；一对短时重叠需设计院提供详细图|
|T2 第三液路隔离缓冲|新罐1/3/5m³、新负荷泵1+1、HX-A/B各一、止回/维护隔离/独立供电|一次A/B无质量直通；仅选中转移支路交换热；主回路低流独立保护|共用负荷泵组/电源失效仍是共同故障；静压、NPSH、水锤未验证|
|共享分段回充|原源回路按段给B补冷，回A优先；不可假定四泵就是440|A测得储备足够才离开A；B补冷限时；测得回A恢复后才继续|真实塔性能/泵交点限幅；1800秒不通过须保留FAIL|
|独立RC回充|额外500/1000kW冷却服务、泵、管、电源|RC冷量独立计账，不重复计在线W2；失去RC不得误报恢复|厂商净冷量、进出温度、实际Q-H、可用性待证|

厂家需提交两侧Q-Δp及UA随工况面、泵全Q-H/效率/NPSHr及启动曲线、阀Kv和行程/失效/止回、罐接口及温跃层试验；设计方需补全部支路容积/高程/波速/膨胀排气和单对CDU接管图。元件FAT只保证单件，系统FAT/SAT必须实际激发断源、卡阀、公共负荷失效及第二次故障并高频记录流量/压差/温度。不得拿本报告代替这些验收。
'''

def finalize(directory):
    input_root=ROOT/'artifacts/memphis-hydraulic-continuity-v1-analysis'
    results={};series={}
    for p in input_root.rglob('forward_result.json'):
        r=json.loads(p.read_bytes());require(r['id'] not in results,'DUPLICATE_FINAL_CASE');results[r['id']]=r
        series[r['id']]=json.loads((p.parent/'plot_data.json').read_bytes())
    expected={x['id'] for x in cases()}|{'valves__A_demand_no_stuck','valves__A_demand_stuck'}
    require(set(results)==expected,'FINAL_EXACT_CASE_COVERAGE')
    groups={p.parent.name for p in input_root.glob('*/execution_receipts.json')}
    reg=json.loads((HERE/'registration.json').read_bytes())
    require(groups=={x['group'] for x in reg['cases'] if x['kind']!='final'},'FINAL_GROUP_RECEIPTS')
    all_rows=[]
    for id,r in results.items():
        grades=r['grades']
        row=dict(id=id,peak_C=r.get('maximum_inlet_C'),min_load_m3_h=r['minimum_load_m3_h'],
            shortfall_s=r.get('shortfall_duration_s'),zero_flow_s=r.get('zero_flow_duration_s'),deficit_m3=r.get('deficit_m3'),
            source_cold_s=r.get('source_cold_delay_s',r.get('cold_return_delay_s')),thermal=grades.get('THERMAL_COMPLIANCE'),
            load=grades.get('LOAD_FLOW_COMPLIANCE',grades.get('HYDRAULIC_COMPLIANCE')),continuity90=grades.get('90S_CONTINUITY'),
            source=grades.get('SOURCE_RECOVERY'),reserve=grades.get('RESERVE_RECOVERY'),
            first_tested_reserve_s=(r.get('recovery_scan') or {}).get('first_tested_joint_pass_s'),second90=grades.get('SECOND_FAULT_90S','NOT_RUN'))
        all_rows.append(row)
    save(directory/'actual_results.json',results)
    with (directory/'comparison.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    text='# 孟菲斯水力连续性与储备恢复 V1\n\n工程状态：MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_NOT_VERIFIED；采购未放行。本轮为有界离线开发仿真，不是正式C3-C、实物FAT或现场运行。\n\n'
    text+='执行源码：`'+os.environ['GITHUB_SHA']+'`；run '+os.environ['GITHUB_RUN_ID']+'。源和每项输入绑定到本次清单；未借旧PASS。\n\n'
    text+='|场景|峰温°C|最小负荷m³/h|低流秒|零流秒|亏缺m³|热/流/90s/源/储备|\n|---|---|---|---|---|---|---|---|\n'
    def fmt(v):return '未提供/未达到' if v is None else f'{v:.6f}' if isinstance(v,(int,float)) else str(v)
    for r in all_rows:text+='|'+ '|'.join([r['id'],fmt(r['peak_C']),fmt(r['min_load_m3_h']),fmt(r['shortfall_s']),fmt(r['zero_flow_s']),fmt(r['deficit_m3']),'/'.join(str(r[k]) for k in ('thermal','load','continuity90','source','reserve'))])+'|\n'
    text+='\n## 储备恢复与第二次故障：独立判定\n\n|场景|B初始冷量m³/状态|最早已测试双罐90秒资格时刻s|故障后延时s|末态双罐|实际第二故障90秒|第二窗口峰温°C/最小流量m³/h|\n|---|---|---|---|---|---|\n'
    for id,r in results.items():
        scan=r.get('recovery_scan');second=r.get('second_fault')
        if scan:
            text+='|'+ '|'.join([id,fmt(scan['initial_B_cold_m3'])+'/'+scan['initial_B_state'],fmt(scan['first_tested_joint_pass_s']),fmt(scan['delay_from_first_fault_s']),r['grades']['RESERVE_RECOVERY'],r['grades']['SECOND_FAULT_90S'],('未运行' if not second else fmt(second['maximum_inlet_C'])+'/'+fmt(second['minimum_load_m3_h']))])+'|\n'
    text+='\n零流/低流的持续时间按每个原始积分区间计算，浮点比较仅使用1e−8m³/h数值舍入界，不放宽客户流量限值。新压力曲线仅准稳态差压；水锤、NPSH和绝对承压NOT_VERIFIED。\n\n'+TOPOLOGY
    text+='\n## 失败与开口项\n\n各场景的FAIL全部保留；保护正确不抵消失去连续供冷。新增中性回路的热、水力通过只能称假设下候选，不能称客户设备合格。并未用更细dt替代压力瞬态模型，也未将18柜结果直接扩展为90柜整体结论。\n'
    save(directory/'source_inputs.json',dict(source=os.environ['GITHUB_SHA'],registration=json.loads((HERE/'registration.json').read_bytes()),expanded=cases()))
    (directory/'ENGINEERING_REPORT_ZH.md').write_text(text,encoding='utf-8')
    payload=json.dumps(dict(rows=all_rows,series=series,results=results),allow_nan=False,separators=(',',':')).replace('</','<\\/')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>孟菲斯连续供冷对照</title>
<style>body{margin:0;background:#f2f5f8;color:#182b3a;font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:24px}h1{font-size:28px}select{font:inherit;max-width:100%;padding:9px}section{background:white;padding:20px;margin:16px 0;border-radius:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #dbe2e9}.scroll{overflow:auto}.warn{color:#8c3916}a{color:#14528b}@media(max-width:600px){main{padding:12px}section{padding:12px}}</style>
<main><h1>水力连续性与储备恢复</h1><p class="warn">离线未标定模型；工程未批准。差压为准稳态，不代表水锤或承压合格。</p><p><a href="ENGINEERING_REPORT_ZH.md">中文完整报告</a> · <a href="comparison.csv">实际数据表</a></p><label>实际场景 <select id="case"></select></label><section><h2>分项判据</h2><pre id="metrics"></pre></section><section><h2>所有机柜最高入口温度</h2><div id="temperature"></div></section><section><h2>负荷与转移回路流量</h2><div id="flow"></div></section><section><h2>A/B模型真值冷库存</h2><div id="reserve"></div></section><section><h2>实际事件</h2><pre id="events"></pre></section><section><h2>真实末态再次90秒</h2><pre id="challenge"></pre></section></main><script>const data=PAYLOAD;
const select=document.getElementById('case');for(const row of data.rows){const o=document.createElement('option');o.value=row.id;o.textContent=row.id;select.add(o)}
function plot(id,points,keys,labels,limit,unit){const clean=points.filter(p=>keys.some(k=>Number.isFinite(p[k])));if(!clean.length){document.getElementById(id).textContent='无此项绘图数据；不能补造';return}const vals=clean.flatMap(p=>keys.map(k=>p[k]).filter(Number.isFinite));let lo=Math.min(...vals,limit??Infinity),hi=Math.max(...vals,limit??-Infinity);const pad=Math.max(.2,(hi-lo)*.08);lo-=pad;hi+=pad;if(unit==='m³/h'||unit==='m³')lo=Math.max(0,lo);const end=Math.max(...clean.map(p=>p.time_s)),x=t=>65+t/end*860,y=v=>260-(v-lo)/(hi-lo)*205;let s='<svg viewBox="0 0 980 320" role="img" aria-label="'+labels.join('、')+'，单位'+unit+'">';for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;s+='<path d="M65 '+y(v)+'H925" stroke="#dbe2e9"/><text x="3" y="'+(y(v)+5)+'" font-size="14">'+v.toFixed(1)+'</text>'}const colors=['#155c8b','#b35b1c'];keys.forEach((k,i)=>{const a=clean.filter(p=>Number.isFinite(p[k]));s+='<polyline fill="none" stroke="'+colors[i]+'" stroke-width="2" points="'+a.map(p=>x(p.time_s)+','+y(p[k])).join(' ')+'"/><text x="'+(70+i*370)+'" y="24" fill="'+colors[i]+'">'+labels[i]+' · '+unit+'</text>'});if(limit!==null)s+='<path d="M65 '+y(limit)+'H925" stroke="#a64035" stroke-dasharray="5 4"/>';for(let i=0;i<5;i++)s+='<text x="'+x(end*i/4)+'" y="292" font-size="14">'+(end*i/4).toFixed(0)+'s</text>';document.getElementById(id).innerHTML=s+'</svg>'}
function show(){const id=select.value,r=data.results[id],p=data.series[id];document.getElementById('metrics').textContent=JSON.stringify(data.rows.find(x=>x.id===id),null,2);plot('temperature',p,['rack_C'],['机柜入口最高'],45,'°C');plot('flow',p,['load_m3_h','transfer_m3_h'],['实际负荷供流','新增隔离转移支路'],330,'m³/h');plot('reserve',p,['cold_A_m3','cold_B_m3'],['A罐','B罐'],null,'m³');document.getElementById('events').textContent=JSON.stringify(r.events??[],null,2);document.getElementById('challenge').textContent=JSON.stringify(r.reserve_challenge??'NOT_RUN',null,2)}select.addEventListener('change',show);show();</script></html>'''.replace('PAYLOAD',payload)
    page=page.replace('<section><h2>实际事件</h2>', '<section><h2>准稳态泵差压（非水锤）</h2><div id="pressure"></div></section><section><h2>一次侧泵总电功率</h2><div id="power"></div></section><section><h2>实际事件</h2>')
    page=page.replace("document.getElementById('events').textContent=", "plot('pressure',p,['load_dp_quasi_pa','transfer_dp_quasi_pa'],['新连续负荷泵','隔离转移泵'],null,'Pa');plot('power',p,['primary_pump_kW'],['一次侧总电功率'],null,'kW');document.getElementById('events').textContent=")
    page=page.replace("JSON.stringify(r.reserve_challenge??'NOT_RUN',null,2)", "JSON.stringify({final:r.reserve_challenge??'NOT_RUN',recovery:r.recovery_scan??'NOT_RUN',second:r.second_fault??'NOT_RUN'},null,2)")
    (directory/'engineering_report.html').write_text(page,encoding='utf-8')
    coverage=dict(case_count=len(results),new_dynamic_count=len(cases()),fresh_old_baselines=2,
        engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',no_aggregate_design_pass=True,dual_CDU_pair='NOT_RUN_PENDING_DETAILED_BINDINGS',
        pressure_transient='NOT_VERIFIED',OEM='NOT_VERIFIED')
    save(directory/'coverage.json',coverage)
    return dict(kind='consolidated_actual_engineering_results',coverage=coverage,
        outputs={p.name:digest(p) for p in directory.iterdir() if p.is_file()})
