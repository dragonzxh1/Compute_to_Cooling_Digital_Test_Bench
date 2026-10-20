"""Consolidated evidence-based short-case report, no live or invented measurements."""
import html
import json
from .campaign import dump


def package(out,reg,results,series,env):
    def esc(x):return html.escape(str(x))
    def plot(rows,keys,colors,title,unit,limit=None):
        width,height=960,240;left,right,top,bottom=65,930,35,205
        vals=[r[k] for r in rows for k in keys]+([] if limit is None else [limit])
        lo,hi=min(vals),max(vals);gap=max((hi-lo)*.12,1.);lo-=gap;hi+=gap
        xy=lambda t,v:(left+(right-left)*t/rows[-1]['t'],bottom-(bottom-top)*(v-lo)/(hi-lo))
        s=f'<svg viewBox="0 0 {width} {height}" role="img"><text x="20" y="22">{esc(title)} · {esc(unit)}</text>'
        for i in range(5):
            val=lo+(hi-lo)*i/4;x,y=xy(0,val)
            s+=f'<path d="M{left},{y}H{right}" stroke="#d5dfeb"/><text x="8" y="{y+5}" font-size="12">{val:.2f}</text>'
        if limit is not None:
            _,y=xy(0,limit);s+=f'<path d="M{left},{y}H{right}" stroke="#dc2626" stroke-dasharray="6 4"/>'
        for key,color in zip(keys,colors):
            pts=' '.join(f'{xy(r["t"],r[key])[0]:.1f},{xy(r["t"],r[key])[1]:.1f}' for r in rows)
            s+=f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>'
        s+=f'<text x="{left}" y="230">0s</text><text x="{right-35}" y="230">{rows[-1]["t"]:.1f}s</text></svg>'
        return s+'<p>'+', '.join(f'<span style="color:{c}">{esc(k)}</span>' for k,c in zip(keys,colors))+'</p>'
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R12 短程动态接管</title><style>body{font:16px/1.65 "Microsoft YaHei",sans-serif;color:#172b45;background:#eef3f9;margin:0}main{max-width:1100px;margin:auto;padding:24px}section{background:white;border:1px solid #dce5ef;border-radius:12px;margin:18px 0;padding:24px}svg{width:100%;font:14px sans-serif;fill:#304965}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border:1px solid #dce5ef;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}.warn{background:#fff4df;border-left:5px solid #e58b19;padding:16px}a{color:#0866aa}</style><main><h1>Memphis R12 · 单六柜 T-2 短程动态接管</h1>']
    parts.append('<p class="warn">MEMPHIS_ENGINEERING_NOT_APPROVED。未标定研究模型；非 OEM 保证、非现场测量、非全18柜/源泵/冷塔验证、非正式 C3-C。</p>')
    parts.append(f'<p>源码 {esc(env["source_commit"])} · 输入 JSON {reg["topology_sha256"]} · CPU25% / 256/512MiB / 480s单次上限。</p>')
    parts.append('<table><tr><th>场景</th><th>最小单柜m³/h</th><th>最高入口°C</th><th>水力</th><th>温度</th><th>接管</th><th>HX入口压力</th></tr>')
    for r in results:
        parts.append(f'<tr><td><a href="#{esc(r["case"]["id"])}">{esc(r["case"]["id"])}</a></td><td>{r["min_rack_flow_m3_h"]:.4f}</td><td>{r["max_rack_inlet_C"]:.4f}</td><td>{r["hydraulic_verdict"]}</td><td>{r["thermal_verdict"]}</td><td>{r["takeover_verdict"]}</td><td>{r["hx_pressure_verdict"]}</td></tr>')
    parts.append('</table>')
    for r,rows in zip(results,series):
        cid=r['case']['id'];parts.append(f'<section id="{esc(cid)}"><h2>{esc(cid)}</h2>')
        parts.append(f'<p>末态 {r["controller_terminal"]}；接管完成 {r["complete_at"]}s；近零流量累计 {r["near_zero_flow_duration_s"]:.2f}s；流量亏缺 {r["flow_deficit_volume_m3"]:.6f}m³。</p>')
        parts.append(plot(rows,['min_rack_flow_m3_h'],['#087e8b'],'六柜中最小单柜流量','m³/h',reg['requirements']['each_rack_flow_hot_m3_h']))
        parts.append(plot(rows,['max_rack_inlet_C','A_outlet_C','B_outlet_C'],['#d94b35','#5570aa','#009c80'],'温度','°C',45))
        parts.append(plot(rows,['A_secondary_m3_h','B_secondary_m3_h'],['#5570aa','#009c80'],'两 CDU 实际二次流量','m³/h'))
        parts.append('<h3>实际事件时间轴</h3><pre>'+esc(json.dumps(r['events'],ensure_ascii=False,indent=2))+'</pre>')
        parts.append(f'<p><a href="{cid}/summary.csv">汇总CSV</a> · <a href="{cid}/racks.csv">每柜CSV</a> · <a href="{cid}/cdus.csv">CDU CSV</a> · <a href="{cid}/energy.csv">能量账本</a> · <a href="{cid}/trace.ndjson">PRE/命令/POST原始记录</a> · <a href="{cid}/case_result.json">完整结论</a></p></section>')
    parts.append('<section><h2>参数与能力边界</h2><pre>'+esc(json.dumps(dict(assumptions=reg['assumptions'],capability_missing=reg['capability_missing']),ensure_ascii=False,indent=2))+'</pre></section></main></html>')
    with (out/'engineering_report.html').open('x',encoding='utf8') as f:f.write(''.join(parts))
    dump(out/'campaign_results.json',dict(status='MODEL_RUNS_COMPLETED_NOT_ENGINEERING_APPROVAL',results=results,environment=env))
    dump(out/'R12_DYNAMIC_MODEL_ADAPTER.json',dict(topology_sha256=reg['topology_sha256'],scope=reg['scope'],
        no_frozen_m1_import=True,primary_boundary=reg['assumptions']['primary_boundary_basis'],capability_missing=reg['capability_missing']))
    dump(out/'R12_PRESSURE_MASTER_TRANSFER.json',dict(research_control='SINGLE_MASTER_WITH_SPARE_FLOW_FOLLOWER',
        cases=[dict(id=r['case']['id'],events=r['events'],complete_at=r['complete_at'],max_actual_overlap_s=r['max_actual_overlap_s']) for r in results]))
    dump(out/'R12_OPEN_DESIGN_BLOCKERS.json',dict(engineering_status=reg['engineering_status'],
        missing=reg['capability_missing'],required_vendor_data=['Q-H and efficiency/NPSHr curves','clean and fouled filter dp','valve Kv/Cv and travel bounds','HX fouled UA and pressure-drop surface','sensor accuracy/lag and independent wiring']))
    dump(out/'R12_MEASUREMENT_INTERFACE_MATRIX.json',dict(source='MODELED_SENSOR_RELEASE_NOT_FIELD_IO',
        sample_s=reg['assumptions']['instrument_sample_s'],lag_s=reg['assumptions']['instrument_lag_s'],
        release_delay_s=reg['assumptions']['instrument_release_delay_s'],max_age_s=reg['assumptions']['measurement_max_age_s'],
        feedback=['per-CDU P1/P2 flow, Tin/Tout, dp, HX heat, pump speed, actual valve opening','per-rack A/B supply/return flow, inlet/outlet temperature and dp'],
        field_sensor_independence='NOT_VERIFIED',P1_FT='PROPOSED_REQUIRED_INSTRUMENT_NOT_ORIGINAL_FIELD_INSTALLATION'))
