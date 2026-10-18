# Mechanical annotation of the derived delivery only. Official raw artifacts unchanged.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$evidence='D:/Github/c2c-evidence-review/memphis-failover-optimization-v1/run39129984525'
$delivery=Join-Path $evidence 'delivery'
$original=Get-ChildItem -LiteralPath (Join-Path $evidence 'official-final') -Recurse -Filter engineering_report.html|Select-Object -First 1
$text=[IO.File]::ReadAllText($original.FullName)
$findings=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'delivery_findings.html'))
$text=$text.Replace('<div class="scroll">',$findings+'<div class="scroll">')
$text=$text.Replace('<th>连续330</th>','<th>负载侧连续330</th>')
$text=$text.Replace('<td>118.80000000000001</td>','<td>118.8</td>').Replace('<td>None</td>','<td>未达成</td>')
$text=$text.Replace('rack_inlet_c / primary_inlet_c / pipe_return_c','机柜入口 / 一次侧供液 / 源管回水 · °C')
$text=$text.Replace('source_flow_m3_h / load_flow_m3_h','源侧实际流量 / 负载侧实际流量 · m³/h')
$text=$text.Replace('cold_A_m3 / cold_B_m3','A罐阈值冷库存 / B罐阈值冷库存 · m³')
$data=Get-Content -LiteralPath (Join-Path $delivery 'comparisons.json') -Raw|ConvertFrom-Json
foreach($case in $data.comparisons){
 $anchor='<summary>'+$case.case_id+'</summary>'
 $begin=$text.IndexOf($anchor);$cut=$text.IndexOf('<h3>实际事件、区段积分与输入</h3><pre>',$begin)
 if($begin -lt 0 -or $cut -lt 0){throw 'CASE_EVENT_ANCHOR'}
 $eventTable='<h3>实际控制事件</h3><div class="scroll"><table><tr><th>时刻s</th><th>原状态</th><th>新状态</th><th>测量/动作依据</th></tr>'
 foreach($event in $case.diagnosis.source_events){$eventTable+='<tr><td>'+($event.time_ns/1e9).ToString('F1',[Globalization.CultureInfo]::InvariantCulture)+'</td><td>'+[Net.WebUtility]::HtmlEncode($event.from_state)+'</td><td>'+[Net.WebUtility]::HtmlEncode($event.to_state)+'</td><td>'+[Net.WebUtility]::HtmlEncode($event.reason)+'</td></tr>'}
 $eventTable+='</table></div><details class="raw"><summary>展开完整区段积分与原始结构化诊断</summary><pre>'
 $needle='<h3>实际事件、区段积分与输入</h3><pre>'
 $text=$text.Substring(0,$cut)+$eventTable+$text.Substring($cut+$needle.Length)
}
$text=$text.Replace('</pre></details>','</pre></details></details>')
$cut=$text.LastIndexOf('<h2>设计决定报告</h2><pre>')
if($cut -lt 0){throw 'REPORT_ANCHOR_MISSING'}
$report=[IO.File]::ReadAllText((Join-Path $delivery 'DESIGN_DECISION_REPORT_ZH.md'))
$text=$text.Substring(0,$cut)+'<h2>设计决定报告 · 交付释义v1.1</h2><pre>'+[Net.WebUtility]::HtmlEncode($report)+'</pre></html>'
[IO.File]::WriteAllText((Join-Path $delivery 'engineering_report.html'),$text,[Text.UTF8Encoding]::new($false))
