param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
# Pure persisted-file verification; no Python/native/model process is launched.
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$tool=Join-Path $repo 'v0_2/tests/tools/gb300_m1_closed_loop_v2'
$manifestHash=(Get-FileHash (Join-Path $tool 'source_manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$study=Get-Content (Join-Path $tool 'study.json') -Raw|ConvertFrom-Json
$baseline=Get-Content (Join-Path $repo 'v0_2/tests/tools/gb300_m1_closed_loop_v1/scenario.json') -Raw|ConvertFrom-Json
$expected=@(@($study.settings|ForEach-Object {$_.id+'__LOAD_STEP';$_.id+'__PUMP_STUCK'});@($study.faults.id);@('REFINE_STUCK_50','REFINE_STUCK_25'))|ForEach-Object {$_}
$seenStages=@{}
$files=0;$phasesCount=0;$intervalsCount=0;$cases=0;$duplicates=0;$nativeCount=0
foreach($group in @('baseline','sensitivity-a','sensitivity-b','fault')){
 $base=Join-Path $taskRoot $group
 $inv=Get-Content (Join-Path $base 'artifact_hashes.json') -Raw|ConvertFrom-Json
 if($inv.source_commit -cne $ExpectedCommit -or $inv.group -cne $group){throw 'GROUP_IDENTITY'}
 foreach($b in $inv.records){
  $p=[IO.Path]::GetFullPath((Join-Path $base $b.path))
  if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'PATH_ESCAPE'}
  if((Get-Item -LiteralPath $p).Length -ne $b.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('RAW_HASH_DRIFT '+$b.path)}
  $files++
 }
 foreach($d in Get-ChildItem -LiteralPath $base -Directory){
  $r=Get-Content (Join-Path $d.FullName 'result.json') -Raw|ConvertFrom-Json
  $n=Get-Content (Join-Path $d.FullName 'job_status.json') -Raw|ConvertFrom-Json
  $j=Get-Content (Join-Path $d.FullName 'external_job_identity.json') -Raw|ConvertFrom-Json
  $release=Get-Content (Join-Path $d.FullName 'release.json') -Raw|ConvertFrom-Json
  $proofHash=(Get-FileHash (Join-Path $d.FullName 'external_job_identity.json') -Algorithm SHA256).Hash.ToLowerInvariant()
  if($release.actual_python_pid -ne $r.pid -or $release.external_proof_raw_sha256 -cne $proofHash -or $r.environment.job_proof_sha256 -cne $proofHash){throw 'EXTERNAL_RELEASE_BINDING'}
  $envr=Get-Content (Join-Path $base 'environment_registration.json') -Raw|ConvertFrom-Json
  if($r.status -cne 'PASS' -or $r.stage -cne $d.Name -or $r.pid -ne $j.actual_python_pid -or
   -not $j.in_target_job -or $j.cpu_rate -ne 2500 -or $j.process_mb -ne 1024 -or $j.job_mb -ne 2048 -or
   -not $n.assigned_before_resume -or -not $n.resumed -or -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or
   $n.child_exitcode -ne 0 -or $n.outcome -cne 'EXITED' -or $envr.wall_seconds -ne 480 -or
   $envr.manifest_raw_sha256 -cne $manifestHash -or $envr.commit -cne $ExpectedCommit){throw ('NATIVE_IDENTITY_OR_CLEANUP '+$d.Name)}
  if($r.environment.source_commit -cne $ExpectedCommit -or $r.environment.python -cne '3.11.9' -or
   $r.environment.system -cne 'Windows' -or $r.environment.image -cne $r.environment_after.image -or
   (ConvertTo-Json $r.environment -Compress) -cne (ConvertTo-Json $r.environment_after -Compress)){throw 'ENVIRONMENT_IDENTITY'}
  if($r.environment.dependencies.numpy -cne '2.4.6' -or $r.environment.dependencies.pytest -cne '9.1.1' -or $r.environment.dependencies.jsonschema -cne '4.26.0'){throw 'DEPENDENCY_IDENTITY'}
  $nativeCount++
  if($d.Name -ceq 'NEGATIVE'){
   $out=Get-Content (Join-Path $d.FullName 'stdout.raw') -Raw
   # Repository addopts plus -q use pytest double-quiet: no summary line.
   # All 28 progress marks must be passes, with no skip/xfail/failure marks.
   if(($out -notmatch '28 passed' -and $out -notmatch '(?m)^\.{28}\s+\[100%\]') -or $r.pytest_exitcode -ne 0){throw 'NEGATIVE_TEST_COVERAGE'}
   continue
  }
  $cases++;$casePath=Join-Path $d.FullName 'case'
  if($d.Name -notin $expected -or $seenStages.ContainsKey($d.Name)){throw 'EXACT_CASE_IDENTITY'};$seenStages[$d.Name]=$true
  $c=(Get-Content (Join-Path $casePath 'input.json') -Raw|ConvertFrom-Json).config
  $spec=Get-Content (Join-Path $d.FullName 'case_spec.json') -Raw|ConvertFrom-Json
  if($spec.id -cne $d.Name -or $spec.group -cne $group -or $c.duration_ns -ne 120000000000 -or
   $c.hx_ua_w_k -ne $baseline.hx_ua_w_k*$spec.setting.ua_scale -or
   $c.secondary_supply_volume_m3 -ne $baseline.secondary_supply_volume_m3*$spec.setting.inventory_scale -or
   $c.secondary_return_volume_m3 -ne $baseline.secondary_return_volume_m3*$spec.setting.inventory_scale -or
   $c.rack_fluid_volume_each_m3 -ne $baseline.rack_fluid_volume_each_m3*$spec.setting.inventory_scale -or
   $c.load_profile.Count -ne $baseline.load_profile.Count){throw 'INPUT_BINDING'}
  for($e=0;$e -lt $baseline.load_profile.Count;$e++){
   if($c.load_profile[$e].time_ns -ne $baseline.load_profile[$e].time_ns -or $c.load_profile[$e].rack_it_w.Count -ne 6){throw 'LOAD_TIME_OR_COUNT'}
   for($rack=0;$rack -lt 6;$rack++){if($c.load_profile[$e].rack_it_w[$rack] -ne $baseline.load_profile[$e].rack_it_w[$rack]){throw 'LOAD_VALUE_DRIFT'}}
  }
  $s=Get-Content (Join-Path $casePath 'series.json') -Raw|ConvertFrom-Json
  $ms=Get-Content (Join-Path $casePath 'measurements.json') -Raw|ConvertFrom-Json
  $fs=Get-Content (Join-Path $casePath 'phases.json') -Raw|ConvertFrom-Json
  $ps=Get-Content (Join-Path $casePath 'physics_intervals.json') -Raw|ConvertFrom-Json
  $idx=Get-Content (Join-Path $casePath 'm1_completed_index.json') -Raw|ConvertFrom-Json
  if($s.Count -ne 1+$c.duration_ns/$c.physics_dt_ns -or $ps.Count -ne $s.Count-1 -or $fs.Count -ne 600 -or $idx.Count -ne $fs.Count){throw 'TRACE_COVERAGE'}
  $stored=0L
  foreach($entry in $idx){if($entry.offset -ne $stored -or $entry.compression -cne 'zlib' -or $entry.raw_sha256 -notmatch '^[0-9a-f]{64}$'){throw 'JOURNAL_INDEX'};$stored+=$entry.stored_bytes}
  if((Get-Item (Join-Path $casePath 'm1_completed.zlib')).Length -ne $stored){throw 'JOURNAL_TRUNCATED'}
  # Whole compressed journal bytes are hash-verified above. Every frame was
  # decompressed/hash-read on the source-bound remote worker; no local replay.
  $source=@{};$times=@{};$seen=@{};$prior=$null;$latched=$false
  foreach($x in $s){$times[[string]$x.time_ns]=$x}
  foreach($m in $ms){
   if($m.available_ns -ne $m.sample_ns+$c.sensor_delay_ns){throw 'SAMPLE_DELAY'}
   if($m.quality -ceq 'VALID'){
    $truth=$times[[string]$m.sample_ns]
    if($m.pump_speed -ne $truth.actual_speed -or $m.flow_m3_s -ne $truth.flow_m3_s -or $m.dp_pa -ne $truth.dp_pa){throw 'MEASUREMENT_ORIGIN'}
   }elseif($null -ne $m.pump_speed -or $null -ne $m.flow_m3_s){throw 'MISSING_MEASUREMENT_TRUTH_LEAK'}
   $source[$m.measurement_record_id]=$m
  }
  foreach($f in $fs){
   $m=$f.PRE.measurement;$o=$source[$m.measurement_record_id]
   if($null -eq $o -or $m.sample_ns -ne $o.sample_ns -or $m.release_ns -ne $o.available_ns -or $m.release_ns -gt $f.time_ns){throw 'PRE_SOURCE_TIME'}
   $valid=$o.quality -ceq 'VALID' -and $f.time_ns-$o.sample_ns -le $c.sensor_max_age_ns
   if(($m.quality -ceq 'VALID') -ne $valid){throw 'STALE_RELABEL'}
   if($valid){
    $request=[Math]::Min(.9,[Math]::Max(.3,$c.initial_speed+$c.feedback_gain_fraction_per_k*(($o.rack_return_k|Measure-Object -Maximum).Maximum-$c.return_target_k)))
    if($m.measured_speed -ne $o.pump_speed -or [Math]::Abs($request-$f.controller_request) -gt 32*2.220446049250313e-16){throw 'CONTROLLER_SOURCE'}
   }elseif($null -ne $f.controller_request -or $null -ne $m.measured_speed){throw 'INVALID_TRUTH_FALLBACK'}
   if($seen.ContainsKey($m.measurement_record_id)){$duplicates++};$seen[$m.measurement_record_id]=$true
   if($null -ne $prior -and ($f.PRE.old_command.value -ne $prior.command -or $f.PRE.old_command.issue_ns -ne $prior.issue_ns)){throw 'PRE_FUTURE_COMMAND'}
   if($f.SAFETY.pre_digest -cne $f.immutable_pre_digest -or $f.PLC.safety_digest -cne $f.immutable_safety_digest -or
    $f.POST.pre_id -cne $f.PRE.record_id -or $f.POST.plc_id -cne $f.PLC.record_id -or
    $f.actuator_command.producer_module -cne 'PLC' -or $f.PLC.command -lt $f.envelope.minimum_speed -or $f.PLC.command -gt $f.envelope.maximum_speed){throw 'PHASE_OWNERSHIP'}
   if($f.SAFETY.severity -ceq 'FAULT'){$latched=$true};if($latched -and $f.SAFETY.severity -cne 'FAULT'){throw 'FAULT_RESET'}
   $prior=$f.PLC
  }
  if($r.independent_analysis.status -cne 'INDEPENDENT_DECLARED_EQUATIONS_PASS'){throw 'EQUATION_AUDIT'}
  if($d.Name.StartsWith('BASE__') -and (@($r.regression.PSObject.Properties).Count -ne 8 -or @($r.regression.PSObject.Properties|Where-Object Value -ne $true).Count)){throw 'V1_FRESH_REGRESSION'}
  $phasesCount+=$fs.Count;$intervalsCount+=$ps.Count
 }
}
if($cases -ne 21 -or $nativeCount -ne 22){throw 'EXACT_STUDY_COVERAGE'}
@{status='INDEPENDENT_PURE_FILE_REVIEW_PASS';source_commit=$ExpectedCommit;raw_files_verified=$files;cases=$cases;native_stages=$nativeCount;
 phases_checked=$phasesCount;physics_intervals=$intervalsCount;repeated_observations=$duplicates;
 full_journal_bytes='HASH_VERIFIED_NO_LOCAL_MODEL_REPLAY';meaning='DECLARED_MODEL_STUDY_NOT_OEM_OR_PRODUCTION_QUALIFICATION'}|ConvertTo-Json -Depth 8
