param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$reg=Get-Content (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
$all=@();$plots=@{};$receipts=@()
foreach($spec in $reg.cases){
 $path=Join-Path $taskRoot ($spec.group+'/'+$spec.id+'/result.json')
 $r=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
 if($r.status -cne 'PASS' -or $r.stage -cne $spec.id -or $r.environment.source_commit -cne $ExpectedCommit){throw ('MISSING_OR_INVALID_STAGE '+$spec.id)}
 $status=Get-Content -LiteralPath (Join-Path (Split-Path $path) 'job_status.json') -Raw|ConvertFrom-Json
 $identity=Get-Content -LiteralPath (Join-Path (Split-Path $path) 'external_job_identity.json') -Raw|ConvertFrom-Json
 if(-not $status.cleanup_complete -or $status.active_after_cleanup -ne 0 -or $status.child_exitcode -ne 0 -or -not $identity.in_target_job -or $identity.actual_python_pid -ne $r.pid){throw ('IDENTITY_OR_CLEANUP '+$spec.id)}
 $all+=@{stage=$spec.id;group=$spec.group;analysis=$r.analysis;environment=$r.environment}
 $receipts+=@{stage=$spec.id;pid=$r.pid;cleanup=$true;active_after=0;result_raw_sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
 $seriesPath=Join-Path (Split-Path $path) 'case/series.json'
 if(Test-Path -LiteralPath $seriesPath){
  $rows=Get-Content -LiteralPath $seriesPath -Raw|ConvertFrom-Json
  if($spec.kind -ceq 'unit'){
   $plots[$spec.id]=@($rows|Where-Object {$_.time_ns%1000000000 -eq 0}|ForEach-Object {@{t=$_.time_ns/1e9;inlet=$_.supply_k-273.15;outlet=($_.rack_return_k|Measure-Object -Maximum).Maximum-273.15;mixed=$_.return_k-273.15;flow=$_.flow_m3_s*3600;head=$_.dp_pa/1000;main=$_.main_speed;backup=$_.backup_speed;cdu=$_.active_cdu;valve=$_.valve_opening}})
  }elseif($spec.kind -ceq 'group'){
   $plots[$spec.id]=@($rows|ForEach-Object {@{t=$_.time_ns/1e9;inlet=($_.units|ForEach-Object {$_.inlet_k}|Measure-Object -Maximum).Maximum-273.15;primary=$_.primary_inlet_c;flow=$_.source_flow_m3_h;A=$_.cold_A_m3;B=$_.cold_B_m3;load=$_.actual_load_selector;valve=$_.actual_load_valve;sourceSpeed=$_.source_actual_speed;state=$_.source_state}})
  }
 }
}
$out=[ordered]@{schema='MEMPHIS-EQUIPMENT-V2-DELIVERY';source_commit=$ExpectedCommit;run_id=$env:GITHUB_RUN_ID;software='MEMPHIS_V2_SOFTWARE_VALIDATED_PENDING_INDEPENDENT_DOWNLOAD';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';stage_count=$all.Count;stages=$all;receipts=$receipts;plots=$plots;decision='DESIGN_INFORMATION_INSUFFICIENT';formal=$false;production=$false;hardware=$false;phase6=$false}
$byId=@{};foreach($entry in $all){$byId[$entry.stage]=$entry.analysis}
$mesh=@();foreach($id in @('BUFFER20','BUFFER40','BUFFER80','BUFFER160','BUFFER160_REFINED')){$mesh+=@{case=$id;maximum_outlet_rise_K=$byId[$id].maximum_outlet_rise_K}}
$out['resolution_study']=@{tank_mesh=$mesh;unit_dt_final_difference_K=$byId.SIX_REFINED.final_inlet_c-$byId.SIX_UA220.final_inlet_c;group_dt_peak_difference_K=$byId.G_REFINED.maximum_inlet_c-$byId.G_WET_LOSS.maximum_inlet_c;group_40_peak_difference_K=$byId.G_LAYERS40.maximum_inlet_c-$byId.G_WET_LOSS.maximum_inlet_c;group_80_peak_difference_K=$byId.G_LAYERS80.maximum_inlet_c-$byId.G_WET_LOSS.maximum_inlet_c;scope='Finite-volume equation/energy validity does not establish spatial convergence or OEM physical calibration; all grids retained'}
$utf8=[Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $taskRoot 'consolidated_report.json'),($out|ConvertTo-Json -Depth 70),$utf8)
$payload=($out|ConvertTo-Json -Depth 70 -Compress).Replace('</','<\/')
$template=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'report.template.html'))
[IO.File]::WriteAllText((Join-Path $taskRoot 'engineering_report.html'),$template.Replace('__EVIDENCE_JSON__',$payload),$utf8)
$items=@(Get-ChildItem -LiteralPath $taskRoot -File|ForEach-Object {@{file=$_.Name;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant();bytes=$_.Length}})
[IO.File]::WriteAllText((Join-Path $taskRoot 'delivery_hashes.json'),($items|ConvertTo-Json -Depth 8),$utf8)
Write-Host ('EQUIPMENT_REPORT_COMPLETE '+$all.Count+' actual stages; engineering grades retained')
