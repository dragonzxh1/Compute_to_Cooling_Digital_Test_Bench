param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$reg=Get-Content (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
$stage=@{};$cases=[ordered]@{};$jobs=@();$files=0
foreach($group in @('baseline','component','single','six')){
 $base=Join-Path $Root $group;$inventory=Get-Content (Join-Path $base 'artifact_hashes.json') -Raw|ConvertFrom-Json
 if($inventory.source_commit -cne $ExpectedCommit -or $inventory.group -cne $group){throw 'REPORT_SOURCE_GROUP_IDENTITY'}
 foreach($b in $inventory.records){
  if($b.path.EndsWith('.zlib')){continue}
  $p=[IO.Path]::GetFullPath((Join-Path $base $b.path));$prefix=[IO.Path]::GetFullPath($base)+[IO.Path]::DirectorySeparatorChar
  if(-not $p.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or (Get-FileHash $p).Hash.ToLowerInvariant() -cne $b.raw_sha256 -or (Get-Item $p).Length -ne $b.bytes){throw 'REPORT_RAW_HASH'};$files++
 }
 foreach($d in Get-ChildItem $base -Directory){
  $r=Get-Content (Join-Path $d.FullName 'result.json') -Raw|ConvertFrom-Json
  $n=Get-Content (Join-Path $d.FullName 'job_status.json') -Raw|ConvertFrom-Json
  $p=Get-Content (Join-Path $d.FullName 'external_job_identity.json') -Raw|ConvertFrom-Json
  if($r.status -cne 'PASS' -or $r.environment.source_commit -cne $ExpectedCommit -or $r.pid -ne $p.actual_python_pid -or -not $p.in_target_job -or
   $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048 -or -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or $n.child_exitcode -ne 0){throw 'REPORT_JOB_OR_CLEANUP'}
  $stage[$r.stage]=$d.FullName;$jobs+=@{stage=$r.stage;pid=$r.pid;image=$r.environment.image;cleanup_complete=$true;active_after_cleanup=0}
  if(Test-Path (Join-Path $d.FullName 'independent_analysis.json')){$cases[$r.stage]=Get-Content (Join-Path $d.FullName 'independent_analysis.json') -Raw|ConvertFrom-Json}
 }
}
if($stage.Count -ne $reg.cases.Count -or @($reg.cases|Where-Object {-not $stage.ContainsKey($_.id)}).Count){throw 'EXACT_REGISTERED_STAGE_COVERAGE'}
foreach($pair in @(@('SR_HOT','SR_REPEAT'),@('SIX_HOT','SIX_REPEAT'))){foreach($name in @('physics.json','series.json')){
 if((Get-FileHash (Join-Path $stage[$pair[0]] ('case/'+$name))).Hash -cne (Get-FileHash (Join-Path $stage[$pair[1]] ('case/'+$name))).Hash){throw 'FRESH_REPEAT_DRIFT'}
}}
$refine=[ordered]@{};foreach($id in @('SR_REFINE50','SR_REFINE25','SIX_REFINE50')){
 $basis=if($id.StartsWith('SR_')){'SR_HOT'}else{'SIX_HOT'}
 $refine[$id]=@{basis=$basis;maximum_inlet_delta_K=$cases[$id].maximum_inlet_C-$cases[$basis].maximum_inlet_C;final_inlet_delta_K=$cases[$id].final_inlet_C-$cases[$basis].final_inlet_C;scope='OBSERVED_NUMERICAL_SENSITIVITY_NOT_OEM_ERROR_BAR'}
}
$result=[ordered]@{schema='MEMPHIS-SINGLE-THEN-SIX-RESULT-v1';status='CONDITIONAL_DEVELOPMENT_COMPLETED_NOT_EQUIPMENT_QUALIFIED';
 execution_commit=$ExpectedCommit;stage_count=$stage.Count;dynamic_cases=$cases.Count;raw_nonjournal_files_verified=$files;
 cases=$cases;refinement=$refine;repeat='SINGLE_AND_SIX_PHYSICS_SERIES_BYTE_IDENTICAL';jobs=$jobs;
 component=(Get-Content (Join-Path $stage['COMPONENT'] 'result.json') -Raw|ConvertFrom-Json);
 final_design='00/01 only; no18rack/source/recharge claims';equipment='INCOMPLETE_VENDOR_MAPS_AND_GEOMETRY';formal_C3C=$false;production=$false;hardware=$false;phase6=$false;
 load_identity='single155kW_IT147.25kW_liquid;six930kW_IT883.5kW_liquid_plus_pump_heat_once;1100kW_CDU_selection_not_injected_load';
 no_aggregate_equipment_PASS=$true;local_model_execution=$false}
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $Root 'consolidated_report.json'),($result|ConvertTo-Json -Depth 45),$utf8)
$lines=@('# 单柜优先与六柜CDU开发结果','','仅条件性离线开发，不是OEM/设备/正式C3-C/生产/硬件资格。','',('执行源码：'+$ExpectedCommit),'',('| 场景 | 最高入口°C | 最终入口°C | 最终回液°C | 最终流量m³/h | 45°C入口判定 | tracking确认s |'),'| --- | ---: | ---: | ---: | ---: | --- | ---: |')
foreach($kv in $cases.GetEnumerator()){$a=$kv.Value;$lines+=('| '+$kv.Key+' | '+('{0:F6}' -f $a.maximum_inlet_C)+' | '+('{0:F6}' -f $a.final_inlet_C)+' | '+('{0:F6}' -f $a.final_return_C)+' | '+('{0:F6}' -f $a.final_flow_m3_h)+' | '+$a.supply45+' | '+$a.first_tracking_confirmed_s+' |')}
$lines+=@('','暖冷源/低UA/故障场景的超温按实际结果保留，不因保护正确变成温控PASS。','单柜换热UA、库存和泵曲线是显式工程假设。固定一次侧供温意味着外部冷源，不包含塔/罐/90秒接管验证。','原M1资格边界、历史排除、T09 HOLD和硬件待校准保持不变。')
[IO.File]::WriteAllText((Join-Path $Root 'engineering_report.md'),($lines -join "`n"),$utf8)
Write-Host ('RACK_REPORT_COMPLETED stages='+$stage.Count+' dynamic='+$cases.Count)
