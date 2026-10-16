param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$taskCases=[ordered]@{};$taskNative=@();$taskSkippedRaw=@();$taskVerified=0
foreach($group in @('baseline','sensitivity-a','sensitivity-b','fault')){
 $base=Join-Path $taskRoot $group
 $inventory=Get-Content -LiteralPath (Join-Path $base 'artifact_hashes.json') -Raw|ConvertFrom-Json
 if($inventory.source_commit -cne $ExpectedCommit -or $inventory.group -cne $group){throw 'GROUP_SOURCE_DRIFT'}
 foreach($b in $inventory.records){
  $target=[IO.Path]::GetFullPath((Join-Path $base $b.path))
  if(-not $target.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'EVIDENCE_PATH_ESCAPE'}
  if($b.path.EndsWith('.zlib')){$taskSkippedRaw+=@{group=$group;path=$b.path;sha256=$b.raw_sha256;bytes=$b.bytes;location='SEPARATE_COMPLETE_RAW_ARTIFACT'};continue}
  if((Get-Item -LiteralPath $target).Length -ne $b.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('COMPACT_EVIDENCE_DRIFT '+$b.path)}
  $taskVerified++
 }
 foreach($d in Get-ChildItem -LiteralPath $base -Directory){
  $result=Get-Content -LiteralPath (Join-Path $d.FullName 'result.json') -Raw|ConvertFrom-Json
  $native=Get-Content -LiteralPath (Join-Path $d.FullName 'job_status.json') -Raw|ConvertFrom-Json
  $proof=Get-Content -LiteralPath (Join-Path $d.FullName 'external_job_identity.json') -Raw|ConvertFrom-Json
  if($result.status -cne 'PASS' -or $result.environment.source_commit -cne $ExpectedCommit -or $result.pid -ne $proof.actual_python_pid -or
     -not $proof.in_target_job -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or
     -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0){throw ('STAGE_OR_NATIVE_INVALID '+$d.Name)}
  $taskNative+=@{stage=$result.stage;pid=$result.pid;cleanup=$true;active_after=0;image=$result.environment.image}
  if($d.Name -ceq 'NEGATIVE'){continue}
  if($result.independent_analysis.status -cne 'INDEPENDENT_DECLARED_EQUATIONS_PASS'){throw 'INDEPENDENT_EQUATIONS_FAILED'}
  $spec=Get-Content -LiteralPath (Join-Path $d.FullName 'case_spec.json') -Raw|ConvertFrom-Json
  $taskCases[$d.Name]=@{spec=$spec;analysis=$result.independent_analysis;behavior=$result.payload;regression=$result.regression;directory=[IO.Path]::GetRelativePath($taskRoot,$d.FullName).Replace('\','/')}
 }
}
if($taskCases.Count -ne 21 -or $taskNative.Count -ne 22){throw 'EXACT_CASE_COVERAGE_FAILED'}
foreach($case in @('BASE__LOAD_STEP','BASE__PUMP_STUCK')){
 if(@($taskCases[$case].regression.PSObject.Properties).Count -ne 8 -or @($taskCases[$case].regression.PSObject.Properties|Where-Object Value -ne $true).Count){throw 'V1_BASELINE_REGRESSION_FAILED'}
}
$taskConvergence=[ordered]@{}
foreach($field in @('final_supply_c','final_return_c','final_flow_m3_h','final_dp_kpa')){
 $a=$taskCases['BASE__PUMP_STUCK'].analysis.$field;$b=$taskCases['REFINE_STUCK_50'].analysis.$field;$c=$taskCases['REFINE_STUCK_25'].analysis.$field
 $coarse=[Math]::Abs($a-$b);$fine=[Math]::Abs($b-$c)
 $ok=($coarse -eq 0 -and $fine -eq 0) -or $fine -lt $coarse
 $taskConvergence[$field]=@{coarse_medium_delta=$coarse;medium_fine_delta=$fine;shrinks_or_invariant=$ok}
 if(-not $ok){throw ('FAULT_NUMERICAL_CONVERGENCE_NOT_ESTABLISHED '+$field)}
}
$taskRanges=[ordered]@{}
foreach($kind in @('LOAD_STEP','PUMP_STUCK')){
 $selected=@($taskCases.GetEnumerator()|Where-Object {$_.Value.spec.case -ceq $kind -and $null -eq $_.Value.spec.fault -and -not $_.Key.StartsWith('REFINE')})
 if($selected.Count -ne 7){throw 'EXACT_OAT_COVERAGE'}
 $ranges=[ordered]@{}
 foreach($field in @('max_supply_c','max_rack_return_c','final_return_c','final_flow_m3_h','final_dp_kpa','stored_change_mj')){
  $values=@($selected|ForEach-Object {$_.Value.analysis.$field})
  $ranges[$field]=@{minimum=($values|Measure-Object -Minimum).Minimum;maximum=($values|Measure-Object -Maximum).Maximum}
 }
 $taskRanges[$kind]=$ranges
}
$normal=@($taskCases.GetEnumerator()|Where-Object {$_.Key.EndsWith('__LOAD_STEP')})
$stuck=@($taskCases.GetEnumerator()|Where-Object {$_.Key.EndsWith('__PUMP_STUCK')})
$normalNoFalse=@($normal|Where-Object {$null -ne $_.Value.analysis.first_tracking_confirmed_s}).Count -eq 0
$stuckDetected=@($stuck|Where-Object {$null -eq $_.Value.analysis.first_tracking_confirmed_s}).Count -eq 0
$taskReport=[ordered]@{schema='SIX-RACK-V2-ENGINEERING-STUDY-RESULT';status='V2_DECLARED_MODEL_STUDY_COMPLETED';source_commit=$ExpectedCommit;
 v1_regression='FRESH_BYTE_IDENTICAL_8_FILES_EACH';case_count=21;stage_count=22;compact_raw_files_verified=$taskVerified;
 independent_review='ALL8_LOCAL_LIQUID_CONTROL_VOLUMES_PLUS_TOTAL_ENERGY_HX_PUMP_AND_MASS';
 pump_stuck_convergence=$taskConvergence;cases=$taskCases;OAT_ranges=$taskRanges;
 robustness=@{normal_no_false_confirmation_across_7_OAT=$normalNoFalse;stuck_detected_across_7_OAT=$stuckDetected;scope='ONLY_REGISTERED_OAT_POINTS_NOT_JOINT_ENVELOPE_OR_PROBABILITY'};
 return45=@{status='NOT_REGISTERED_NOT_SCORED';customer45_location='RACK_SECONDARY_INLET';source='bound_project.parameters.secondary_hard_limit;02.docx B012';v1_control45_location='MAX_OF_SIX_MODELED_SECONDARY_RACK_RETURN_OBSERVATIONS';v1_control45_authority='ENGINEERING_ASSUMPTION_NOT_CUSTOMER_REQUIREMENT';customer_reference_return_c=@(56.11,55.52,55.67)};
 native_stages=$taskNative;complete_raw_journals=$taskSkippedRaw;C3_C_V5_RESULT='PRESERVE';NEW_INTEGRATED_SYSTEM_QUALIFICATION='NO';PRODUCTION='NO';HARDWARE='CALIBRATION_REQUIRED';PHASE6='NO'}
function Save-New([string]$Path,[string]$Text){
 $raw=[Text.Encoding]::UTF8.GetBytes($Text)
 $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
$json=ConvertTo-Json -InputObject $taskReport -Depth 50
Save-New (Join-Path $taskRoot 'consolidated_report.json') $json
$tables=@()
foreach($case in $taskCases.GetEnumerator()){
 $a=$case.Value.analysis
 $tables+='<tr><td>'+[Net.WebUtility]::HtmlEncode($case.Key)+'</td><td>'+('{0:F3}' -f $a.final_supply_c)+'</td><td>'+('{0:F3}' -f $a.final_return_c)+'</td><td>'+('{0:F3}' -f $a.max_rack_return_c)+'</td><td>'+('{0:F3}' -f $a.final_flow_m3_h)+'</td><td>'+('{0:F3}' -f $a.final_dp_kpa)+'</td><td>'+[string]$a.first_tracking_confirmed_s+'</td></tr>'
}
$plots=@()
foreach($case in @('BASE__LOAD_STEP','BASE__PUMP_STUCK','SENSOR_LOSS','STALE_MEASUREMENT','ACTUATOR_SLOW','LOW_FLOW','ACTUATOR_RECOVERY')){
 $data=Get-Content -LiteralPath (Join-Path $taskRoot ($taskCases[$case].directory+'/case/series.json')) -Raw|ConvertFrom-Json
 $plots+='<h3>'+$case+'</h3>'
 foreach($chart in @(@{title='温度℃：供液蓝/混合回液橙/最热柜回液红';min=30;max=100;fields=@('supply_k','return_k','maxrack')},@{title='命令蓝/实际转速橙 fraction';min=0;max=1;fields=@('commanded_speed','actual_speed')},@{title='实际流量 m³/h';min=0;max=80;fields=@('flow_m3_s')})){
  $svg='<svg viewBox="0 0 1000 260"><rect width="1000" height="260" fill="white"/><path d="M50 25V225H950" stroke="#999" fill="none"/><text x="50" y="20">'+$chart.title+'</text>'
  $colors=@('#1676b7','#d25b16','#ce3434');$i=0
  foreach($field in $chart.fields){
   $points=foreach($r in $data){
    $value=if($field -ceq 'maxrack'){($r.rack_return_k|Measure-Object -Maximum).Maximum}else{$r.$field}
    if($field -in @('supply_k','return_k','maxrack')){$value-=273.15};if($field -ceq 'flow_m3_s'){$value*=3600}
    $x=50+900*$r.time_ns/120000000000;$y=225-180*($value-$chart.min)/($chart.max-$chart.min)
    '{0},{1}' -f $x.ToString('F2',[cultureinfo]::InvariantCulture),$y.ToString('F2',[cultureinfo]::InvariantCulture)
   }
   $svg+='<polyline fill="none" stroke="'+$colors[$i]+'" stroke-width="2" points="'+($points -join ' ')+'"/>';$i++
  }
  $svg+='<text x="50" y="250">0s</text><text x="900" y="250">120s</text><text x="0" y="45">'+$chart.max+'</text><text x="0" y="225">'+$chart.min+'</text></svg>';$plots+=$svg
 }
}
$html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>六柜V2工程可信度研究</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:20px;background:#f5f7fa;color:#142435}table{border-collapse:collapse;width:100%}th,td{padding:8px;border:1px solid #bbc}svg{width:100%;margin:8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>六柜V2：声明模型的工程可信度研究</h1><p>数值一致性和限定工况研究，不是OEM标定、GPU结温安全或设备资格。</p><p>客户45℃是机柜二次侧入口保护；V1的45℃回液仅为开发控制设定。客户回液45℃要求未登记，不作合格评分。0–120秒有限时间；OAT只代表列出的单因素点，不代表联合不确定性包络。</p><table><tr><th>场景</th><th>末供液℃</th><th>末混合回液℃</th><th>最大柜回液℃</th><th>末流量m³/h</th><th>末差压kPa</th><th>M1确认秒/空=未确认</th></tr>'+($tables -join '')+'</table>'+($plots -join '')+'<h2>完整数据、故障与未证明项</h2><pre>'+[Net.WebUtility]::HtmlEncode($json)+'</pre></html>'
Save-New (Join-Path $taskRoot 'consolidated_report.html') $html
$records=foreach($f in Get-ChildItem -LiteralPath $taskRoot -File -Recurse){@{path=[IO.Path]::GetRelativePath($taskRoot,$f.FullName).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}}
Save-New (Join-Path $taskRoot 'consolidated_hashes.json') (ConvertTo-Json -InputObject @{source_commit=$ExpectedCommit;records=@($records)} -Depth 8)
Write-Host 'V2_DECLARED_MODEL_STUDY_COMPLETED; return45 NOT_REGISTERED; physical calibration NOT_CLAIMED'
