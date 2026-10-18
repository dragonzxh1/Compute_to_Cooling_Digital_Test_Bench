param([Parameter(Mandatory)][string]$Root)
# Report formatting from verified persisted evidence; never executes a model.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$verified=Get-Content (Join-Path $Root 'independent_verification.json') -Raw|ConvertFrom-Json
$reportPath=Join-Path $Root 'report-complete/consolidated_report.json'
$report=Get-Content $reportPath -Raw|ConvertFrom-Json
if($verified.source_commit -cne $report.source_commit -or $verified.stage_count -ne $report.stage_count){throw 'VERIFIED_DELIVERY_IDENTITY'}
$report.software='MEMPHIS_V2_SOFTWARE_VALIDATED'
$report|Add-Member -NotePropertyName independent_verification_raw_sha256 -NotePropertyValue (Get-FileHash (Join-Path $Root 'independent_verification.json')).Hash.ToLowerInvariant()
$dest=Join-Path $Root 'delivery';New-Item -ItemType Directory -Path $dest -Force|Out-Null
$utf8=[Text.UTF8Encoding]::new($false)
$e=($report.stages|Where-Object stage -ceq 'EQUIPMENT').analysis.engineering
$e.RFI|Select-Object id,topic,blocking|Export-Csv (Join-Path $dest 'supplier_RFI.csv') -NoTypeInformation -Encoding utf8BOM
$matrix=foreach($candidate in $e.candidates){foreach($p in $candidate.parameters.PSObject.Properties){
 [PSCustomObject]@{candidate=$candidate.name;parameter=$p.Name;value=$p.Value.value;provenance=$p.Value.provenance;selection=$candidate.selection;source=$candidate.source;note=$candidate.note}
}}
$matrix|Export-Csv (Join-Path $dest 'equipment_selection.csv') -NoTypeInformation -Encoding utf8BOM
$curveRows=foreach($r in ($report.stages|Where-Object stage -ceq 'SOURCE_CURVES').analysis.engineering.rows){
 $copy=$r|Select-Object * -ExcludeProperty NPSHa_conditional_range_m
 $copy|Add-Member -NotePropertyName NPSHa_conditional_range_m -NotePropertyValue ($r.NPSHa_conditional_range_m -join ';') -PassThru
}
$curveRows|Export-Csv (Join-Path $dest 'pump_conflict_curves.csv') -NoTypeInformation -Encoding utf8BOM
$e.points|Export-Csv (Join-Path $dest 'UA_requirements.csv') -NoTypeInformation -Encoding utf8BOM
$outcomes=foreach($s in $report.stages){if($s.analysis.PSObject.Properties.Name -contains 'grades'){foreach($g in $s.analysis.grades.PSObject.Properties){[PSCustomObject]@{case=$s.stage;criterion=$g.Name;status=$g.Value}}}}
$outcomes|Export-Csv (Join-Path $dest 'engineering_outcomes.csv') -NoTypeInformation -Encoding utf8BOM
$timeline=if(Test-Path (Join-Path $Root 'remote_causal_timeline.json')){Get-Content (Join-Path $Root 'remote_causal_timeline.json') -Raw|ConvertFrom-Json}else{foreach($s in $report.stages|Where-Object {$_.analysis.PSObject.Properties.Name -contains 'kind' -and $_.analysis.kind -ceq 'unit'}){
 $dir=@(Get-ChildItem -LiteralPath (Join-Path $Root 'full') -Directory -Recurse|Where-Object Name -ceq $s.stage)
 if($dir.Count -ne 1){throw 'EXACT_UNIT_EVIDENCE_DIRECTORY'}
 $phases=Get-Content (Join-Path $dir[0].FullName 'case/phases.json') -Raw|ConvertFrom-Json
 $fast=$phases|Where-Object {$_.fast_permission.data.codes -contains 'FAST_LOW_FLOW'}|Select-Object -First 1
 $fault=$phases|Where-Object {$_.SAFETY.severity -ceq 'FAULT'}|Select-Object -First 1
 $request=$s.analysis.events|Where-Object event -ceq 'BACKUP_REQUESTED'|Select-Object -First 1
 $started=$s.analysis.events|Where-Object event -ceq 'BACKUP_STARTED'|Select-Object -First 1
 [PSCustomObject]@{case=$s.stage;first_safety_fault_s=if($fault){$fault.time_ns/1e9}else{$null};first_fast_low_flow_s=if($fast){$fast.time_ns/1e9}else{$null};M1_confirmed_s=$s.analysis.causal.tracking_confirmed_s;backup_requested_s=if($request){$request.time_ns/1e9}else{$null};backup_started_s=if($started){$started.time_ns/1e9}else{$null};flow_recovered_s=$s.analysis.flow_recovered_s;pressure_recovered_s=$s.analysis.pressure_recovered_s;temperature_recovered_s=$s.analysis.temperature_recovered_s;terminal_recovery_maintained=$s.analysis.terminal_recovery_maintained;full_load_continuity=$s.analysis.grades.FULL_LOAD_CONTINUITY}
}}
$timeline|Export-Csv (Join-Path $dest 'failover_timeline.csv') -NoTypeInformation -Encoding utf8BOM
$report|Add-Member -NotePropertyName delivery_causal_timeline -NotePropertyValue @($timeline)
function Value($o,[string]$key){if($o.PSObject.Properties.Name -contains $key){return $o.$key};return '—'}
function Num($v){if($v -is [ValueType]){return ([double]$v).ToString('F3',[Globalization.CultureInfo]::InvariantCulture)};return [string]$v}
$lines=[Collections.Generic.List[string]]::new()
$lines.Add('# 孟菲斯设备验证与故障接管V2：实际交付')
$lines.Add('')
$lines.Add('软件执行及独立证据核验完成。工程审批状态：MEMPHIS_ENGINEERING_NOT_APPROVED。设计决策：DESIGN_INFORMATION_INSUFFICIENT；已有失败处另列MODIFICATION_RECOMMENDED。')
$lines.Add('')
$lines.Add(('运行：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/'+$report.run_id))
$lines.Add(('执行源码：`'+$report.source_commit+'`；source manifest RAW SHA256：`'+$verified.manifest_raw_sha256+'`。'))
$lines.Add(('本次'+$verified.stage_count+'个实际受控阶段；'+$verified.unique_source_files+'个独立源码文件、'+$verified.source_bindings+'项跨清单哈希核验；'+$verified.raw_files+'个raw文件；'+$verified.phases+'条阶段事务；'+$verified.journal_frames+'个完成日志帧；镜像'+($verified.images -join ',')+'。PID/Job、CPU25%、1024/2048MiB、480s、退出cleanup均已检查。'))
$lines.Add('')
$lines.Add('## 单柜与六柜实际结果')
$lines.Add('')
$lines.Add('| 场景 | 最高入口°C | 末入口°C | 末机柜出口°C | 末总流量m³/h | 流量恢复时刻s | 温控/接管/连续性 |')
$lines.Add('|---|---:|---:|---:|---:|---:|---|')
foreach($s in $report.stages|Where-Object {$_.analysis.PSObject.Properties.Name -contains 'kind' -and $_.analysis.kind -ceq 'unit'}){
 $a=$s.analysis;$lines.Add(('|'+$s.stage+'|'+(Num $a.maximum_inlet_c)+'|'+(Num $a.final_inlet_c)+'|'+(Num $a.final_return_c)+'|'+(Num $a.final_flow_m3_h)+'|'+(Num $a.flow_recovered_s)+'|'+$a.grades.RACK_THERMAL_COMPLIANCE+'/'+$a.grades.FAILOVER_RECOVERY+'/'+$a.grades.FULL_LOAD_CONTINUITY+'|'))
}
$lines.Add('')
$lines.Add('恢复时刻为绝对仿真时刻，故障在10s；流量/压差恢复需连续5s满足登记的99%设计参考。原运行泵M1与备用执行器分别保留身份。备用泵先启动并收到发布的转速反馈，再断开旧路、打开备用路径；独立快速低流量保护与M1分别记录。')
$lines.Add('单柜缩比一次边界、合成泵曲线、阀门5s/慢阀15s和备用0.2/s均为工程假设。备用CDU按相同HX与共享机柜液体库存建等效隔离路径，断开CDU内部液体/金属热容及零流量电机损耗未知；因此这些恢复时间不能作为厂家保证。')
$lines.Add('45°C仅约束机柜二次入口；正常40°C/高温44°C目标跟踪精度、OEM最高回温/最低流量、露点及GPU die安全仍未验证。FULL_LOAD_CONTINUITY的PASS仅是已登记模型窗口条件，不覆盖这些设备资格缺口。')
$lines.Add('')
$lines.Add('## 18柜冷源、90秒及回充')
$lines.Add('')
$lines.Add('| 场景 | 最高入口°C | 故障后90s最高°C | 冷水首返330m³/h延迟s | 原264指标延迟s | A/B实际切换 | 储备恢复时刻s |')
$lines.Add('|---|---:|---:|---:|---:|---|---:|')
foreach($s in $report.stages|Where-Object {$_.analysis.PSObject.Properties.Name -contains 'kind' -and $_.analysis.kind -ceq 'group'}){
 $a=$s.analysis;$lines.Add(('|'+$s.stage+'|'+(Num $a.maximum_inlet_c)+'|'+(Num $a.first90_maximum_inlet_c)+'|'+(Num $a.first_cold_return_330_delay_s)+'|'+(Num $a.historical_264_threshold_delay_s)+'|'+(($a.actual_AB_switches|ConvertTo-Json -Compress) -replace '\|','/')+'|'+(Num $a.reserve_ready_absolute_s)+'|'))
}
$lines.Add('')
$lines.Add('每组2790kW IT，2650.50kW入液，泵热由实际模型工作点加入一次；模型排热不强钳为2716.15kW设计预算。330判据和旧264判据独立列示，空值表示窗口内未满足，不能给PASS。罐15m³保持完整热容量，70%只用于初始冷层。冷源/管路/分层由守恒方程推进，不固定一次41°C。')
$lines.Add('表中90秒窗口统一为30—120s；对有故障场景是故障后90s，对G_CURRENT/回充场景只是对照窗口，不代表这些场景发生了故障。无故障场景首返空值为不适用，不能解释为一次接管失败。')
$lines.Add('首返仅统计故障后的实际物理区间；故障前冷水不能算作0秒恢复，无故障场景不虚构接管通过。首次冷水达到不代表此后持续可用，末5秒恢复保持单独检查；旧Build4的错误首返统计保留为缺陷证据，不作为本次合格结论。')
$lines.Add('0—90s逐秒储热、排热、泵热、流量和冷量数据保存在每场景first90_energy_rows。检测1s、阀序、54s备用建冷、2.75m³源管热置换、热跃层扩散、44.5°C后触发及备用冷量构成解释链；这些假设不是厂家动作时间。没有修改触发点来追求通过。')
$lines.Add('各敏感性场景差值不是可直接相加的独立因果贡献。分层网格的数值扩散与真实混合必须区分；完整网格/步长差异见consolidated_report.json的resolution_study，不能挑选一个通过网格替代设备实测。')
$lines.Add('')
$lines.Add('| 回充场景 | 最大实际回充m³/h | 330m³/h判据 | 双罐冷储备恢复时刻s |')
$lines.Add('|---|---:|---|---:|')
foreach($s in $report.stages|Where-Object stage -in @('RECHARGE_SHARED','RECHARGE_INDEPENDENT')){
 $a=$s.analysis;$lines.Add(('|'+$s.stage+'|'+(Num $a.recharge_flow_comparison.maximum_actual_m3_h)+'|'+$a.recharge_flow_comparison.status+'|'+(Num $a.reserve_ready_absolute_s)+'|'))
}
$lines.Add('储备恢复时刻是登记冷量阈值的首次满足，不能替代完整330m³/h回充能力、下一故障连续性或长期稳定性。共用方案的源侧流量与独立方案的专用回充支路分别按其实际拓扑读取。')
$lines.Add('')
foreach($s in $report.stages|Where-Object {$_.analysis.PSObject.Properties.Name -contains 'kind' -and $_.analysis.kind -ceq 'buffer'}){$a=$s.analysis;$lines.Add(('- '+$s.stage+'：330m³/h持续90s，出液最大升温'+(Num $a.maximum_outlet_rise_K)+'K，判定'+$a.grades.'90_SECOND_BUFFER_COMPLIANCE'+'。'))}
$lines.Add('')
$lines.Add('## 设备选型与采购阻塞')
$lines.Add('')
foreach($p in $e.points){$lines.Add(('- '+(Num $p.q_kw)+'kW，'+$p.primary_in_c+'→'+$p.secondary_out_c+'°C供温条件，需有效UA约'+(Num $p.required_UA_kW_K)+'kW/K；理想逆流、暂定PG25常物性，无污垢及制造裕量。'))}
$lines.Add('厂家可用UA尚无完整项目保证点；110/183.30/209.28/220均为研究输入，不能提升为OEM_CONFIRMED。三花S200AL-246H的型号和引用压降已存在，缺的是完整原始热选型；Alfa Laval与三花参数不可混用。')
$lines.Add('137/183/209kW/K是所列板换四端温条件的理想反算值。板换二次出口与机柜入口之间的水力耗散/储热位置仍需区分；若仿真UA183.30时机柜入口略高于44°C，应保留该偏差，不能把理论需求数字当作端到端温控保证。六柜共用充分混合供液节点，支路入口同温是显式降阶假设；各柜回温与流量独立，未作供液支路空间温差或CFD验证。')
$lines.Add('CDU整机接口差压应与外部管路/机柜需求比较，不能将内部板换和过滤器损失再次计入外部需求。按原预算高温外部约295.21kPa，常态约152.81kPa；371.81kPa是整个二次泵路径预算。厂家目录额定流量与项目不同，须提供完整曲线再判适配。')
foreach($c in $e.candidates){$lines.Add(('- '+$c.name+'：'+$c.selection+'。'+$c.note+' 来源：'+$c.source))}
$lines.Add('')
$lines.Add('源泵34m是115m³/h候选工作点，≤18m是R10完整曲线约束，二者不是同一种数字。已分别计算2/3/4泵、五档转速和0.6/0.7/0.8效率假设。静压、NPSHr、真实最弱MAWP与瞬态缺失使采购阻塞；同标高条件绝压不能当现场验证。源侧96.52kPa和负荷侧155.92kPa经分层罐解耦，不相加选一台泵。')
$lines.Add('')
$lines.Add('| 合成版本 | 运行泵数 | 转速比例 | 每泵m³/h | 总m³/h | 运行压差kPa | 关死压差kPa | 泵电耗kW（效率0.7） |')
$lines.Add('|---|---:|---:|---:|---:|---:|---:|---:|')
foreach($r in ($report.stages|Where-Object stage -ceq 'SOURCE_CURVES').analysis.engineering.rows|Where-Object {$_.efficiency -eq .7 -and $_.pumps -in @(3,4) -and $_.speed -in @(.8,1.)}){
 $lines.Add(('|'+$r.variant+'|'+$r.pumps+'|'+(Num $r.speed)+'|'+(Num $r.per_pump_m3_h)+'|'+(Num $r.total_m3_h)+'|'+(Num $r.head_kpa)+'|'+(Num $r.shutoff_kpa)+'|'+(Num $r.electrical_kw)+'|'))
}
$lines.Add('这些是按显式二次曲线假设求交点的工程扫描，不是厂家的完整恒速Q–H图。不能将其中某个有利工作点作为订货参数。板换一次/二次入口表压差≤10kPa、泵吸入口≥50kPag的全工况压力链尚未闭合；单侧板换压降、循环扬程或同标高条件绝压均不能替代这两个要求。')
$lines.Add('')
$lines.Add('## 工程决策及下一步')
$lines.Add('')
foreach($o in $e.options){$lines.Add(('- '+$o.option+'：'+$o.decision+'；'+$o.scope))}
$lines.Add('共享备用CDU仅完成架构及失效域/水力/维护风险比较，未完成交叉管网动态验证；混合冷源无实际共同工况图谱。不得将这两项备选解释为已经验证的客户配置。风机功率、实际水耗及全年CAPEX/OPEX缺曲线/报价，不输出虚假数值排名；有限窗口泵耗可从账本读取。')
$lines.Add('2小时断水带载、10分钟UPS切换、现场压力瞬态、真实泄漏流量及设备全工作包络未由本次120/240/900秒窗口覆盖，保持NOT_VERIFIED；原有测量触发的漏液隔离逻辑不能替代泄漏质量损失试验。尚不能出采购合格证或完整客户验收结论。')
$lines.Add('最高优先级RFI：订货机柜允许回温/最小流量；准确CDU/BOM及1100kW项目保证点；完整PG25泵图与压力链；15m³罐90s温升和实际阀泵时序。其余见supplier_RFI.csv。')
$lines.Add('')
$lines.Add('保持原Startup49/50与兼容性分开；SEM02五项strict P1 B/C不完整、PF06原域INCOMPLETE、任意POST/崩溃/断电原子性NOT_PROVEN、T09 HOLD、fullP历史不可用、硬件CALIBRATION_REQUIRED。该项目开发不继承正式C3-C资格，未授权生产、硬件、Phase6或采购实施。')
[IO.File]::WriteAllText((Join-Path $dest 'ENGINEERING_REPORT_ZH.md'),($lines -join "`n"),$utf8)
$renderer=Join-Path (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path 'v0_2/tests/tools/memphis_equipment_validation_v2/report.template.html'
$payload=($report|ConvertTo-Json -Depth 70 -Compress).Replace('</','<\/')
$view=Join-Path $PSScriptRoot 'delivery_view.js'
$html=[IO.File]::ReadAllText($renderer).Replace('__EVIDENCE_JSON__',$payload).Replace('</html>',('<script>'+[IO.File]::ReadAllText($view)+'</script></html>'))
[IO.File]::WriteAllText((Join-Path $dest 'engineering_report.html'),$html,$utf8)
[IO.File]::WriteAllText((Join-Path $dest 'consolidated_report.json'),($report|ConvertTo-Json -Depth 70),$utf8)
Copy-Item -LiteralPath (Join-Path $Root 'independent_verification.json') -Destination (Join-Path $dest 'independent_verification.json')
Copy-Item -LiteralPath (Join-Path $Root 'source_input_environment_manifest.json') -Destination (Join-Path $dest 'source_input_environment_manifest.json')
Copy-Item -LiteralPath (Join-Path (Split-Path $renderer) 'registration.json') -Destination (Join-Path $dest 'registration.json')
Copy-Item -LiteralPath (Join-Path (Split-Path $renderer) 'source_manifest.json') -Destination (Join-Path $dest 'source_manifest.json')
$hashes=Get-ChildItem -LiteralPath $dest -File|Where-Object Name -cne 'delivery_manifest.json'|ForEach-Object {@{file=$_.Name;bytes=$_.Length;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant()}}
[IO.File]::WriteAllText((Join-Path $dest 'delivery_manifest.json'),(@{source_commit=$report.source_commit;run_id=$report.run_id;official_report_raw_sha256=(Get-FileHash $reportPath).Hash.ToLowerInvariant();renderer_raw_sha256=(Get-FileHash $renderer).Hash.ToLowerInvariant();presentation_overlay_sha256=(Get-FileHash $view).Hash.ToLowerInvariant();records=@($hashes)}|ConvertTo-Json -Depth 12),$utf8)
Get-FileHash (Join-Path $dest 'delivery_manifest.json')
