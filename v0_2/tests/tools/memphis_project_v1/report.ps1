param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path $Root).Path
$reg=Get-Content (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
$stages=[ordered]@{};$cases=[ordered]@{};$native=@();$verified=0;$journals=@()
foreach($group in @('baseline','six','plant-a','plant-b','recharge')){
 $base=Join-Path $taskRoot $group
 $inv=Get-Content (Join-Path $base 'artifact_hashes.json') -Raw|ConvertFrom-Json
 if($inv.source_commit -cne $ExpectedCommit -or $inv.group -cne $group){throw 'SOURCE_OR_GROUP_DRIFT'}
 foreach($b in $inv.records){
  $p=[IO.Path]::GetFullPath((Join-Path $base $b.path))
  if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'PATH_ESCAPE'}
  if($b.path.EndsWith('.zlib')){$journals+=@{group=$group;path=$b.path;sha256=$b.raw_sha256;bytes=$b.bytes};continue}
  if((Get-Item $p).Length -ne $b.bytes -or (Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('RAW_DRIFT '+$b.path)}
  $verified++
 }
 foreach($d in Get-ChildItem $base -Directory){
  $r=Get-Content (Join-Path $d.FullName 'result.json') -Raw|ConvertFrom-Json
  $n=Get-Content (Join-Path $d.FullName 'job_status.json') -Raw|ConvertFrom-Json
  $p=Get-Content (Join-Path $d.FullName 'external_job_identity.json') -Raw|ConvertFrom-Json
  if($r.status -cne 'PASS' -or $r.environment.source_commit -cne $ExpectedCommit -or $r.pid -ne $p.actual_python_pid -or
    -not $p.in_target_job -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048 -or
    -not $n.assigned_before_resume -or -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or $n.child_exitcode -ne 0){throw ('EXECUTION_INVALID '+$d.Name)}
  if(($r.environment|ConvertTo-Json -Compress) -cne ($r.environment_after|ConvertTo-Json -Compress)){throw 'ENVIRONMENT_DRIFT'}
  $stages[$r.stage]=$r;$native+=@{stage=$r.stage;pid=$r.pid;cleanup_complete=$true;active_after_cleanup=0;image=$r.environment.image}
  $sp=@($reg.cases|Where-Object id -ceq $r.stage)
  if($sp.Count -ne 1 -or $sp[0].scope -notin @('SIX','GROUP18') -or $null -eq $sp[0].ua_w_k){continue}
  $a=$r.independent_analysis
  if(@($a.grades.PSObject.Properties).Count -ne 7 -or -not $a.no_aggregate_engineering_pass){throw 'GRADE_SCOPE_MISSING'}
  $cases[$r.stage]=@{spec=$sp[0];analysis=$a;directory=$d.FullName}
 }
}
$expected=@('NEGATIVE','NODE_PORT','SOURCE_COMPARISON')+@($reg.cases|ForEach-Object id)
if($stages.Count -ne $expected.Count -or @($expected|Where-Object {-not $stages.Contains($_)}).Count){throw 'EXACT_STAGE_COVERAGE'}
foreach($f in @('series.json','physics.json')){
 $a=Join-Path $cases['SIX_UA220'].directory ('case/'+$f);$b=Join-Path $cases['SIX_UA220_REPEAT'].directory ('case/'+$f)
 if((Get-FileHash $a -Algorithm SHA256).Hash -cne (Get-FileHash $b -Algorithm SHA256).Hash){throw ('NONDETERMINISTIC_REPEAT '+$f)}
}
$deltas=[ordered]@{}
foreach($id in @('SIX_UA220_REFINE','SIX_UA220_REFINE25','WET_LOSS_MESH40','WET_LOSS_REFINE')){
 $basis=if($id.StartsWith('SIX')){'SIX_UA220'}else{'WET_LOSS_STRATIFIED'}
 $deltas[$id]=@{basis=$basis;maximum_inlet_delta_K=$cases[$id].analysis.maximum_inlet_c-$cases[$basis].analysis.maximum_inlet_c;
  final_primary_delta_K=$cases[$id].analysis.final_primary_inlet_c-$cases[$basis].analysis.final_primary_inlet_c;
  final_rack_inlet_delta_K=$cases[$id].analysis.final_inlet_c-$cases[$basis].analysis.final_inlet_c;
  final_rack_return_delta_K=$cases[$id].analysis.final_return_c-$cases[$basis].analysis.final_return_c;
  status='OBSERVED_DISCRETIZATION_DIFFERENCE_NOT_OEM_CONFIDENCE_INTERVAL'}
}
function Save-New([string]$Path,[string]$Text){
 $bytes=[Text.Encoding]::UTF8.GetBytes($Text);$s=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$s.Write($bytes,0,$bytes.Length);$s.Flush($true)}finally{$s.Dispose()}
}
$rows=@();$plots=@();$timelines=@();$rackTables=@()
foreach($kv in $cases.GetEnumerator()){
 $a=$kv.Value.analysis;$id=$kv.Key;$g=$a.grades
 $rr=@();$ui=0
 foreach($unit in $a.final_units){
  for($ri=0;$ri -lt 6;$ri++){
   $pressure=[double]$unit.edge_drops_pa.('inlet'+$ri)+[double]$unit.edge_drops_pa.('rack'+$ri)
   $rr+='<tr><td>U'+$ui+'/R'+($ri+1)+'</td><td>'+('{0:F4}' -f ([double]$unit.inlet_k[$ri]-273.15))+'</td><td>'+('{0:F4}' -f ([double]$unit.rack_return_k[$ri]-273.15))+'</td><td>'+('{0:F4}' -f ([double]$unit.branch_flows_m3_s[$ri]*3600))+'</td><td>'+('{0:F3}' -f ($pressure/1000))+'</td></tr>'
  };$ui++
 }
 $rackTables+='<h3>'+$id+' 最后时刻逐柜结果</h3><table><tr><th>柜</th><th>入口°C</th><th>回液°C</th><th>流量m³/h</th><th>整支路Δp kPa</th></tr>'+($rr -join '')+'</table>'
 $rows+='<tr><td>'+[Net.WebUtility]::HtmlEncode($id)+'</td><td>'+('{0:F3}' -f $a.maximum_inlet_c)+'</td><td>'+('{0:F3}' -f $a.maximum_return_c)+'</td><td>'+('{0:F3}' -f $a.minimum_branch_flow_m3_h)+'</td><td>'+[Net.WebUtility]::HtmlEncode(($g|ConvertTo-Json -Compress))+'</td></tr>'
 $s=Get-Content (Join-Path $kv.Value.directory 'case/series.json') -Raw|ConvertFrom-Json
 $last=[double]$s[-1].time_ns/1e9;$points=@();$primary=@();$ymax=[Math]::Max(55,[double]$a.maximum_inlet_c+2)
 foreach($x in $s){
  $t=[double]$x.time_ns/1e9;$mx=($x.units|ForEach-Object {$_.inlet_k}|Measure-Object -Maximum).Maximum-273.15
  $points+=('{0:F2},{1:F2}' -f (40+680*$t/$last),(210-180*($mx-30)/($ymax-30)))
  $primary+=('{0:F2},{1:F2}' -f (40+680*$t/$last),(210-180*([double]$x.primary_inlet_c-30)/($ymax-30)))
 }
 $limit=210-180*15/($ymax-30)
 $plots+='<section><h3>'+[Net.WebUtility]::HtmlEncode($id)+'</h3><svg viewBox="0 0 760 240" role="img" aria-label="Measured physical rack inlet and primary temperature"><rect width="760" height="240" fill="#fafafa"/><path d="M40 20V210H730" fill="none" stroke="#888"/><line x1="40" x2="730" y1="'+$limit+'" y2="'+$limit+'" stroke="#b33" stroke-dasharray="5 4"/><polyline fill="none" stroke="#086" points="'+($points -join ' ')+'"/><polyline fill="none" stroke="#36a" points="'+($primary -join ' ')+'"/><text x="45" y="235">0–'+$last+' s; green=max rack inlet; blue=primary; dashed=45°C</text></svg></section>'
 $timelines+='<h3>'+$id+'</h3><p>状态机启动就绪时延='+[string]$a.coordinator_ready_latency_s+'s；实际冷水返回首达时延='+[string]$a.takeover_latency_s+'s；故障90s内最高柜入口='+[string]$a.changeover_window_maximum_inlet_c+'°C。未达到或无故障的时延保持空值，首达不等于持续恢复。</p><pre>'+[Net.WebUtility]::HtmlEncode(($a.source_timeline|ConvertTo-Json -Depth 10))+'</pre>'
}
$caseExport=[ordered]@{};foreach($kv in $cases.GetEnumerator()){$caseExport[$kv.Key]=@{spec=$kv.Value.spec;analysis=$kv.Value.analysis}}
$report=[ordered]@{schema='MEMPHIS-PROJECT-V1-ENGINEERING-RESULT';status='REGISTERED_MODEL_EXPERIMENTS_COMPLETED_NOT_EQUIPMENT_QUALIFICATION';
 source_commit=$ExpectedCommit;stage_count=$stages.Count;model_case_count=$cases.Count;compact_raw_files_verified=$verified;
 seven_separate_grades=$reg.grading;cases=$caseExport;repeat='SIX_UA220_PHYSICS_AND_SERIES_BYTE_IDENTICAL';discretization=$deltas;
 original_V1_V2_regressions='FRESH_8_RAW_FILES_EACH_UNCHANGED';source_comparison=$stages['SOURCE_COMPARISON'].comparison;
 supplier_gaps=$reg.supplier_gaps;native=$native;raw_journals_separate=$journals;
 cdu_requirements=(Get-Content (Join-Path $taskRoot 'baseline/NODE_PORT/upstream_actual_output.json') -Raw|ConvertFrom-Json).requirements;
 retained=@{Startup='ORIGINAL49/50_COMPATIBILITY_SEPARATE';SEM02='FIVE_STRICT_P1_BC_INCOMPLETE';PF06='ORIGINAL_INCOMPLETE_SUPPLEMENT_SEPARATE';arbitrary_POST_crash_power_atomicity='NOT_PROVEN';T09='IMPLEMENTATION_HOLD';full_P='HISTORICALLY_UNAVAILABLE';hardware='CALIBRATION_REQUIRED'};
 formal_C3_C='NOT_RUN';production=$false;hardware_control=$false;phase6=$false;source_pump_selection=$null;recharge_selection=$null}
Save-New (Join-Path $taskRoot 'consolidated_report.json') ($report|ConvertTo-Json -Depth 60)
$comparison=[Net.WebUtility]::HtmlEncode(($stages['SOURCE_COMPARISON'].comparison|ConvertTo-Json -Depth 12))
$html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>孟菲斯项目 V1 条件性工程报告</title><style>body{font:16px/1.6 system-ui;max-width:1280px;margin:32px auto;padding:20px;color:#172334}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ccd;padding:8px;vertical-align:top}pre{white-space:pre-wrap;background:#f1f5fa;padding:15px}svg{width:100%;max-width:900px}section{break-inside:avoid}</style><h1>孟菲斯六柜满额与18柜冷源集成</h1><p>离线开发仿真；不是设备选型合格、OEM校准、生产控制或正式 C3-C。七项分开评分，没有系统总PASS。</p><p>六柜930 kW IT /883.5 kW入液；18柜2790 kW IT /2650.5 kW入液。全部泵电耗按登记假设入液一次。UA110/220 kW/K为敏感性假设，不是三花保证。45°C严格指机柜二次侧入口；44°C目标单独保留。</p><p>执行源码 '+$ExpectedCommit+'；'+$stages.Count+'阶段；'+$cases.Count+'动态场景。90秒结论同时检查实际温度与接管时延，不由15m³容积推定。A漏液仅为信号隔离逻辑，不是实际泄漏/失液模型。</p><h2>数值和七项独立评分</h2><table><tr><th>场景</th><th>最高柜入口°C</th><th>最高柜回液°C</th><th>最低逐柜流量m³/h</th><th>七项评分</th></tr>'+($rows -join '')+'</table><h2>源泵候选冲突 / 关死与NPSH</h2><p>V9与PID不自动合并或选优。PID静压335.89kPa(g)只用于条件性同高程计算，不能移用为V9已批准边界。厂家完整曲线、最弱MAWP和NPSHr缺失。</p><pre>'+$comparison+'</pre><h2>实际动态曲线</h2>'+($plots -join '')+'<h2>故障与接管事件</h2>'+($timelines -join '')+'<h2>供应商RFI</h2><pre>'+[Net.WebUtility]::HtmlEncode(($reg.supplier_gaps|ConvertTo-Json))+'</pre><h2>限制</h2><p>有限时域不是稳态保证；水力阻力、罐扩散/短路、泵热分配、阀门和仪表时序均需实测校准。共用源泵与独立回充均未获设计选定。原M1历史排除与资格边界不变；禁止把本报告继承为新增系统C3-C或GPU die安全结论。</p></html>'
$html=$html.Replace('<h2>实际动态曲线</h2>','<h2>逐柜实际流量、温度与支路压降</h2>'+($rackTables -join '')+'<h2>CDU需求矩阵（不是OEM保证）</h2><pre>'+[Net.WebUtility]::HtmlEncode(($report.cdu_requirements|ConvertTo-Json -Depth 14))+'</pre><h2>实际动态曲线</h2>')
Save-New (Join-Path $taskRoot 'engineering_report.html') $html
Write-Host ('MEMPHIS_REPORT_COMPLETED stages='+$stages.Count+' model_cases='+$cases.Count+'; engineering grades remain separate')
