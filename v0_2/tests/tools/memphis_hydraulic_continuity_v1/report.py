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

`独立负荷缓冲罐 → 新连续负荷泵 → 3个CDU → HX-A或HX-B独立另一侧 → 缓冲罐`

A/B一次液体不与新负荷液体混合，只作换热；切换期间仅一个转移支路实际供热交换，独立缓冲支撑负荷流量。新增1/3/5m³罐、两台独立换热器、连续泵一用一备及传感器/阀/供电接口。UA4MW/K及新回路155.92kPa均是工程假设，额外泵热已计入，未当成现场已有或OEM选型。旧A/B负荷泵在此候选中改作转移用途，须设计方核查改接，不是自动批准。

以上是P&ID级功能边界，不是可施工PID；须补口径、设备位号、死角/排气/补水/膨胀、阀Kv、止回、维护隔离、静压/NPSH及瞬态校核。

## 回充边界

共享源方案逐段给B补冷、限时回A、必要时4泵恢复A，不能A/B同时直通，不能把4×110当实际440。独立RC500/1000kW方案是另加热服务、泵、管线和电源，不重复借在线W2冷量。1800秒只为研究观察窗，二次故障允许间隔需业主另定。

最终每个罐的真实温层直接用于80/160层保守细化再放冷90秒，不重置理想初态。初始绝对温度、冷库存≥85%及0.5K温升须同时满足；非零混合的物理网格收敛、未知最坏回液和OEM保证仍不完备。
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
    require(groups=={'baseline','hydraulic','recovery'},'FINAL_GROUP_RECEIPTS')
    all_rows=[]
    for id,r in results.items():
        grades=r['grades']
        row=dict(id=id,peak_C=r.get('maximum_inlet_C'),min_load_m3_h=r['minimum_load_m3_h'],
            shortfall_s=r.get('shortfall_duration_s'),zero_flow_s=r.get('zero_flow_duration_s'),deficit_m3=r.get('deficit_m3'),
            source_cold_s=r.get('source_cold_delay_s',r.get('cold_return_delay_s')),thermal=grades.get('THERMAL_COMPLIANCE'),
            load=grades.get('LOAD_FLOW_COMPLIANCE',grades.get('HYDRAULIC_COMPLIANCE')),continuity90=grades.get('90S_CONTINUITY'),
            source=grades.get('SOURCE_RECOVERY'),reserve=grades.get('RESERVE_RECOVERY'))
        all_rows.append(row)
    save(directory/'actual_results.json',results)
    with (directory/'comparison.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    text='# 孟菲斯水力连续性与储备恢复 V1\n\n工程状态：MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_NOT_VERIFIED；采购未放行。本轮为有界离线开发仿真，不是正式C3-C、实物FAT或现场运行。\n\n'
    text+='执行源码：`'+os.environ['GITHUB_SHA']+'`；run '+os.environ['GITHUB_RUN_ID']+'。源和每项输入绑定到本次清单；未借旧PASS。\n\n'
    text+='|场景|峰温°C|最小负荷m³/h|低流秒|零流秒|亏缺m³|热/流/90s/源/储备|\n|---|---|---|---|---|---|---|\n'
    def fmt(v):return '未提供/未达到' if v is None else f'{v:.6f}' if isinstance(v,(int,float)) else str(v)
    for r in all_rows:text+='|'+ '|'.join([r['id'],fmt(r['peak_C']),fmt(r['min_load_m3_h']),fmt(r['shortfall_s']),fmt(r['zero_flow_s']),fmt(r['deficit_m3']),'/'.join(str(r[k]) for k in ('thermal','load','continuity90','source','reserve'))])+'|\n'
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
    (directory/'engineering_report.html').write_text(page,encoding='utf-8')
    coverage=dict(case_count=len(results),new_dynamic_count=len(cases()),fresh_old_baselines=2,
        engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',no_aggregate_design_pass=True,dual_CDU_pair='NOT_RUN_PENDING_DETAILED_BINDINGS',
        pressure_transient='NOT_VERIFIED',OEM='NOT_VERIFIED')
    save(directory/'coverage.json',coverage)
    return dict(kind='consolidated_actual_engineering_results',coverage=coverage,
        outputs={p.name:digest(p) for p in directory.iterdir() if p.is_file()})
