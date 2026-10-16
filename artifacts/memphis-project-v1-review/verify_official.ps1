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
$reg=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_project_v1/registration.json') -Raw|ConvertFrom-Json
$expected=@('NEGATIVE','NODE_PORT','SOURCE_COMPARISON')+@($reg.cases|ForEach-Object id)
if($zipCount -ne 11 -or $groups.Count -ne 5 -or $stages.Count -ne $expected.Count -or @($expected|Where-Object {-not $stages.Contains($_)}).Count){throw 'OFFICIAL_FULL_COVERAGE'}
if($frames -ne $phaseCount -or $modelCount -ne 22){throw 'JOURNAL_OR_MODEL_CASE_COUNT'}
foreach($name in @('series.json','physics.json')){
 $a=Join-Path $stages['SIX_UA220'].directory ('case/'+$name);$b=Join-Path $stages['SIX_UA220_REPEAT'].directory ('case/'+$name)
 if((Get-FileHash $a -Algorithm SHA256).Hash -cne (Get-FileHash $b -Algorithm SHA256).Hash){throw 'EXACT_REPEAT_DRIFT'}
}
$expectations=Get-Content (Join-Path $repo 'v0_2/tests/tools/gb300_m1_closed_loop_v2/v1_regression_hashes.json') -Raw|ConvertFrom-Json
foreach($name in @('LOAD_STEP','PUMP_STUCK')){
 $id=if($name -ceq 'LOAD_STEP'){'V2_REGRESSION_LOAD'}else{'V2_REGRESSION_STUCK'}
 foreach($b in $expectations.$name.PSObject.Properties){if((Get-FileHash (Join-Path $stages[$id].directory ('case/'+$b.Name)) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw 'V1_V2_FRESH_REGRESSION_DRIFT'}}
}
$summary=[ordered]@{status='OFFICIAL_PERSISTED_EVIDENCE_VERIFIED_NOT_EQUIPMENT_QUALIFICATION';execution_commit=$ExpectedCommit;official_zip_count=$zipCount;
 raw_files_verified=$fileCount;stages=$stages.Count;model_cases=$modelCount;phase_transactions=$phaseCount;source_transactions=$sourcePhaseCount;
 all_completed_journal_frames_decompressed_hash_verified=$frames;actual_python_jobs_verified=$stages.Count;actual_node_job=$localNode;
 cleanup_complete_all=$true;active_after_cleanup_all=0;repeat='PHYSICS_AND_SERIES_BYTE_IDENTICAL';V1_V2='FRESH8_FILES_EACH_IDENTICAL';
 CPU_percent=25;process_MiB=1024;job_MiB=2048;stage_wall_budget_s=480;local_model_execution=$false;
 no_equipment_or_OEM_or_C3C_or_production_or_hardware_or_Phase6_approval=$true}
$summary|ConvertTo-Json -Depth 12
