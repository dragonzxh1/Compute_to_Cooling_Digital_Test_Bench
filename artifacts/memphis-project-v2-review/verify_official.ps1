param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
# PURE PERSISTED-FILE REVIEW. No Python, native/model execution or stress test.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path $Root).Path
$meta=Get-Content (Join-Path $taskRoot 'official_artifact_index.json') -Raw|ConvertFrom-Json
$zipCount=0;$fileCount=0;$frames=0;$phaseCount=0;$sourcePhaseCount=0;$stages=[ordered]@{};$groups=[ordered]@{};$modelCount=0;$localNode=$null
foreach($a in $meta.artifacts){
 $path=Join-Path $taskRoot ($a.name+'.zip')
 if((Get-Item $path).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $a.digest){throw ('OFFICIAL_ZIP_DRIFT '+$a.name)}
 $zipCount++
 if($a.name -notlike 'memphis-raw-*'){continue}
 $dest=Join-Path $taskRoot ('full/'+$a.name)
 if(-not(Test-Path $dest)){[IO.Compression.ZipFile]::ExtractToDirectory($path,$dest)}
 $inventories=@(Get-ChildItem $dest -Recurse -File -Filter artifact_hashes.json)
 if($inventories.Count -ne 1){throw 'RAW_INVENTORY_REQUIRED'}
 $base=$inventories[0].Directory.FullName;$inv=Get-Content $inventories[0].FullName -Raw|ConvertFrom-Json
 if($inv.source_commit -cne $ExpectedCommit){throw 'RAW_SOURCE_COMMIT'}
 $er=Get-Content (Join-Path $base 'environment_registration.json') -Raw|ConvertFrom-Json
 if($er.commit -cne $ExpectedCommit -or $er.manifest_raw_sha256 -cne '0fae67b3b430f7072030f5338e8ff54512c9e9c0c0eb1f135efabdd088ec21a3' -or
 $er.formal -or $er.cpu_rate -ne 2500 -or $er.process_mb -ne 1024 -or $er.job_mb -ne 2048 -or $er.wall_seconds -ne 480){throw 'ENVIRONMENT_REGISTRATION'}
 $groups[$inv.group]=$base
 foreach($b in $inv.records){
  $target=[IO.Path]::GetFullPath((Join-Path $base $b.path))
  if(-not $target.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'RAW_PATH_ESCAPE'}
  if((Get-Item $target).Length -ne $b.bytes -or (Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('RAW_BYTES_DRIFT '+$b.path)}
  $fileCount++
 }
 foreach($stage in Get-ChildItem $base -Directory){
  $r=Get-Content (Join-Path $stage.FullName 'result.json') -Raw|ConvertFrom-Json
  $p=Get-Content (Join-Path $stage.FullName 'external_job_identity.json') -Raw|ConvertFrom-Json
  $ready=Get-Content (Join-Path $stage.FullName 'ready.json') -Raw|ConvertFrom-Json
  $n=Get-Content (Join-Path $stage.FullName 'job_status.json') -Raw|ConvertFrom-Json
  if($r.status -cne 'PASS' -or $r.environment.source_commit -cne $ExpectedCommit -or $r.pid -ne $p.actual_python_pid -or $r.pid -ne $ready.pid -or
   -not $p.in_target_job -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048 -or
   -not $n.assigned_before_resume -or -not $n.resumed -or -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or $n.child_exitcode -ne 0 -or $n.outcome -cne 'EXITED'){throw ('ACTUAL_JOB_OR_CLEANUP_INVALID '+$r.stage)}
  if(($r.environment|ConvertTo-Json -Compress) -cne ($r.environment_after|ConvertTo-Json -Compress)){throw 'ENVIRONMENT_DRIFT'}
  if($r.environment.python -cne '3.11.9' -or $r.environment.dependencies.numpy -cne '2.4.6' -or $r.environment.dependencies.pytest -cne '9.1.1' -or $r.environment.dependencies.jsonschema -cne '4.26.0'){throw 'EXACT_DEPENDENCY_IDENTITY'}
  if($r.environment.image -notin @('20261004.326.1','20261012.333.1') -or $r.environment.image -cne $er.image -or $r.environment.executable -cne $er.python_executable -or $ready.executable -cne $er.python_executable){throw 'EXACT_IMAGE_OR_EXECUTABLE_IDENTITY'}
  if((Get-FileHash (Join-Path $stage.FullName 'external_job_identity.json') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $r.environment.job_proof_sha256){throw 'JOB_PROOF_RAW_HASH'}
  $stages[$r.stage]=@{directory=$stage.FullName;pid=$r.pid;image=$r.environment.image;status=$r.status}
  if($r.stage -ceq 'NODE_PORT'){
   $nr=Get-Content (Join-Path $stage.FullName 'node_ready.json') -Raw|ConvertFrom-Json
   $np=Get-Content (Join-Path $stage.FullName 'node_external_job_identity.json') -Raw|ConvertFrom-Json
   if($np.actual_python_pid -ne $nr.pid -or $nr.pid -ne $r.node.pid -or -not $np.in_target_job -or $np.cpu_rate -ne 2500 -or $np.process_mb -ne 1024 -or $np.job_mb -ne 2048){throw 'ACTUAL_NODE_JOB_INVALID'}
   $localNode=$r.node
  }
  $caseDir=Join-Path $stage.FullName 'case'
  if(-not(Test-Path $caseDir)){continue}
  $phase=Get-Content (Join-Path $caseDir 'phases.json') -Raw|ConvertFrom-Json
  $phaseCount+=@($phase).Count
  if(Test-Path (Join-Path $caseDir 'source_phases.json')){
   $sourcePhaseCount+=@(Get-Content (Join-Path $caseDir 'source_phases.json') -Raw|ConvertFrom-Json).Count;$modelCount++
  }
  foreach($f in $phase){
   $m=$f.PRE.measurement
   if($m.sample_ns -gt $m.release_ns -or $m.release_ns -gt $f.time_ns -or $f.SAFETY.pre_digest -cne $f.immutable_pre_digest -or
      $f.PLC.safety_digest -cne $f.immutable_safety_digest -or $f.POST.plc_id -cne $f.PLC.record_id -or $f.POST.pre_id -cne $f.PRE.record_id -or
      $f.actuator_command.producer_module -cne 'PLC'){throw 'PERSISTED_PHASE_BINDING_INVALID'}
  }
  foreach($ix in Get-ChildItem $caseDir -Filter 'm1*_index.json' -File){
   $journal=if($ix.Name -ceq 'm1_completed_index.json'){Join-Path $caseDir 'm1_completed.zlib'}else{Join-Path $caseDir ($ix.Name.Replace('_index.json','.zlib'))}
   $rows=Get-Content $ix.FullName -Raw|ConvertFrom-Json
   $stream=[IO.File]::OpenRead($journal);$cursor=0L
   try{
    foreach($row in $rows){
     if($row.offset -ne $cursor -or $row.compression -cne 'zlib' -or $row.bytes -gt 268435456){throw 'COMPRESSED_FRAME_LAYOUT'}
     $compressed=[byte[]]::new([int]$row.stored_bytes);$pos=0
     while($pos -lt $compressed.Length){$got=$stream.Read($compressed,$pos,$compressed.Length-$pos);if($got -eq 0){throw 'TRUNCATED_ZLIB'};$pos+=$got}
     $ms=[IO.MemoryStream]::new($compressed,$false);$zs=[IO.Compression.ZLibStream]::new($ms,[IO.Compression.CompressionMode]::Decompress);$out=[IO.MemoryStream]::new()
     try{$zs.CopyTo($out);$raw=$out.ToArray()}finally{$zs.Dispose();$ms.Dispose();$out.Dispose()}
     if($raw.Length -ne $row.bytes -or $raw[-1] -ne 10 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $row.raw_sha256){throw 'INDEPENDENT_RAW_FRAME_DRIFT'}
     $frames++;$cursor+=$row.stored_bytes
    }
    if($cursor -ne $stream.Length){throw 'UNREGISTERED_JOURNAL_TAIL'}
   }finally{$stream.Dispose()}
  }
 }
}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$manifestPath=Join-Path $repo 'v0_2/tests/tools/memphis_project_v2/source_manifest.json'
if((Get-FileHash $manifestPath).Hash.ToLowerInvariant() -cne '0fae67b3b430f7072030f5338e8ff54512c9e9c0c0eb1f135efabdd088ec21a3'){throw 'LOCAL_REVIEW_SOURCE_MANIFEST_DRIFT'}
$manifest=Get-Content $manifestPath -Raw|ConvertFrom-Json
$sourceCount=0
foreach($map in @($manifest.source_raw_sha256,$manifest.v1_source_raw_sha256,(Get-Content (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json') -Raw|ConvertFrom-Json).source_raw_sha256)){
 foreach($binding in $map.PSObject.Properties){if((Get-FileHash (Join-Path $repo $binding.Name)).Hash.ToLowerInvariant() -cne $binding.Value){throw ('REVIEW_SOURCE_DRIFT '+$binding.Name)};$sourceCount++}
}
$reg=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_project_v2/registration.json') -Raw|ConvertFrom-Json
$expected=@('NEGATIVE','NODE_PORT','SOURCE_COMPARISON')+@($reg.cases|ForEach-Object id)
if($zipCount -ne 11 -or $groups.Count -ne 5 -or $stages.Count -ne $expected.Count -or @($expected|Where-Object {-not $stages.Contains($_)}).Count){throw 'OFFICIAL_FULL_COVERAGE'}
if($frames -ne $phaseCount -or $modelCount -ne 25){throw 'JOURNAL_OR_MODEL_CASE_COUNT'}
foreach($name in @('series.json','physics.json')){
 $a=Join-Path $stages['SIX_UA220'].directory ('case/'+$name);$b=Join-Path $stages['SIX_UA220_REPEAT'].directory ('case/'+$name)
 if((Get-FileHash $a -Algorithm SHA256).Hash -cne (Get-FileHash $b -Algorithm SHA256).Hash){throw 'EXACT_REPEAT_DRIFT'}
}
$legacySpec=@($reg.cases|Where-Object id -ceq 'V1_REPRO_WET_LOSS')[0]
foreach($b in $legacySpec.expected_raw_sha256.PSObject.Properties){
 $p=Join-Path $stages['V1_REPRO_WET_LOSS'].directory ('case/'+$b.Name)
 if((Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw 'FRESH_ORIGINAL_PROJECT_RAW_DRIFT'}
}
foreach($name in @('series.json','physics.json')){
 $a=Join-Path $stages['WET_LOSS_STRATIFIED'].directory ('case/'+$name)
 $b=Join-Path $stages['WET_LOSS_FIXED_REPEAT'].directory ('case/'+$name)
 if((Get-FileHash $a -Algorithm SHA256).Hash -cne (Get-FileHash $b -Algorithm SHA256).Hash){throw 'COMPOUND_REPEAT_DRIFT'}
}
$fixedRoot=Join-Path $stages['WET_LOSS_STRATIFIED'].directory 'case'
$fixed=Get-Content (Join-Path $fixedRoot 'result.json') -Raw|ConvertFrom-Json
$events=@($fixed.source_timeline|Where-Object reason -ceq 'SECONDARY_INLET44_5_AND_MEASURED_B_RESERVE')
if($events.Count -ne 1){throw 'COMPOUND_ACTION_NOT_ONCE'}
$sources=Get-Content (Join-Path $fixedRoot 'source_phases.json') -Raw|ConvertFrom-Json
$at=@($sources|Where-Object time_ns -eq $events[0].time_ns)
if($at.Count -ne 1 -or -not $at[0].request.source_fault_handled -or -not $at[0].request.thermal_takeover_used -or
 $at[0].request.load_tank -cne 'B' -or $at[0].safety.data.codes -notcontains 'SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER'){throw 'COMPOUND_CAUSE_OR_ISSUER_MISSING'}
$proof=Get-Content (Join-Path $stages['WET_LOSS_STRATIFIED'].directory 'independent_analysis.json') -Raw|ConvertFrom-Json
if(@($proof.compound_fix.actual_load_selector_changes|Where-Object to -ceq 'B').Count -ne 1 -or
 -not $proof.compound_fix.all_original_equation_checks_preserved){throw 'COMPOUND_PHYSICAL_COMPLETION_MISSING'}
$warm=Get-Content (Join-Path $stages['WET_LOSS_B_WARM'].directory 'independent_analysis.json') -Raw|ConvertFrom-Json
if(@($warm.compound_fix.thermal_takeover_events).Count -ne 0 -or @($warm.compound_fix.actual_load_selector_changes).Count -ne 0){throw 'WARM_BACKUP_FALSE_PASS'}
$mixed=Get-Content (Join-Path $stages['WET_LOSS_MIXED'].directory 'independent_analysis.json') -Raw|ConvertFrom-Json
if(@($mixed.compound_fix.thermal_takeover_events).Count -ne 0 -or @($mixed.compound_fix.actual_load_selector_changes).Count -ne 0){throw 'MIXED_BACKUP_FALSE_PASS'}
$expectations=Get-Content (Join-Path $repo 'v0_2/tests/tools/gb300_m1_closed_loop_v2/v1_regression_hashes.json') -Raw|ConvertFrom-Json
foreach($name in @('LOAD_STEP','PUMP_STUCK')){
 $id=if($name -ceq 'LOAD_STEP'){'V2_REGRESSION_LOAD'}else{'V2_REGRESSION_STUCK'}
 foreach($b in $expectations.$name.PSObject.Properties){if((Get-FileHash (Join-Path $stages[$id].directory ('case/'+$b.Name)) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw 'V1_V2_FRESH_REGRESSION_DRIFT'}}
}
$summary=[ordered]@{status='OFFICIAL_PERSISTED_EVIDENCE_VERIFIED_NOT_EQUIPMENT_QUALIFICATION';execution_commit=$ExpectedCommit;official_zip_count=$zipCount;
 raw_files_verified=$fileCount;source_bindings_verified=$sourceCount;stages=$stages.Count;model_cases=$modelCount;phase_transactions=$phaseCount;source_transactions=$sourcePhaseCount;
 all_completed_journal_frames_decompressed_hash_verified=$frames;actual_python_jobs_verified=$stages.Count;actual_node_job=$localNode;
 cleanup_complete_all=$true;active_after_cleanup_all=0;repeat='PHYSICS_AND_SERIES_BYTE_IDENTICAL';V1_V2='FRESH8_FILES_EACH_IDENTICAL';
 CPU_percent=25;process_MiB=1024;job_MiB=2048;stage_wall_budget_s=480;local_model_execution=$false;
 compound_fix='MEASURED_SOURCE_THEN_THERMAL_SINGLE_ACTION_AND_ACTUAL_B_SELECTOR';warm_B='REFUSED';mixed_B='REFUSED';fresh_original_project='FOUR_RAW_FILES_BYTE_IDENTICAL';
 no_equipment_or_OEM_or_C3C_or_production_or_hardware_or_Phase6_approval=$true}
$summary|ConvertTo-Json -Depth 12
