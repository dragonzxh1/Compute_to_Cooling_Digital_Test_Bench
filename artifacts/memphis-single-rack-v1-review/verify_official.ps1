param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit,[Parameter(Mandatory)][string]$ExpectedManifest,[Parameter(Mandatory)][string]$DesignRoot)
# PURE FILE REVIEW. No Python/native/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression.FileSystem
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$reg=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_single_rack_v1/registration.json') -Raw|ConvertFrom-Json
$manifestPath=Join-Path $repo 'v0_2/tests/tools/memphis_single_rack_v1/source_manifest.json'
if((Get-FileHash $manifestPath).Hash.ToLowerInvariant() -cne $ExpectedManifest){throw 'REVIEW_MANIFEST_IDENTITY'}
$manifest=Get-Content $manifestPath -Raw|ConvertFrom-Json;$sources=0
$design=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_single_rack_v1/baseline_registration.json') -Raw|ConvertFrom-Json
foreach($d in $design.final_design_sources){if((Get-FileHash -LiteralPath (Join-Path $DesignRoot $d.filename)).Hash.ToLowerInvariant() -cne $d.raw_sha256){throw ('FINAL_DESIGN_DOCUMENT_DRIFT '+$d.id)}}
foreach($map in @($manifest.source_raw_sha256,$manifest.v1_source_raw_sha256,(Get-Content (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json') -Raw|ConvertFrom-Json).source_raw_sha256)){
 foreach($b in $map.PSObject.Properties){if((Get-FileHash (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('REVIEW_SOURCE_DRIFT '+$b.Name)};$sources++}
}
$index=Get-Content (Join-Path $Root 'official_artifact_index.json') -Raw|ConvertFrom-Json
$run=Get-Content (Join-Path $Root 'run_metadata.json') -Raw|ConvertFrom-Json
if($run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.head_sha -cne $ExpectedCommit -or $run.run_attempt -ne 1){throw 'RUN_IDENTITY_OR_CONCLUSION'}
$reportArtifact=@($index.artifacts|Where-Object name -like 'memphis-rack-report-*')
if($reportArtifact.Count -ne 1){throw 'EXACT_OFFICIAL_REPORT'}
$reportZip=[IO.Compression.ZipFile]::OpenRead((Join-Path $Root ($reportArtifact[0].name+'.zip')));$reportBindings=[ordered]@{}
try{foreach($name in @('consolidated_report.json','engineering_report.md')){
 $entry=@($reportZip.Entries|Where-Object FullName -ceq $name);if($entry.Count -ne 1){throw 'EXACT_OFFICIAL_REPORT_FILE'}
 $dest=Join-Path $Root ('report-complete/'+$name);New-Item -ItemType Directory -Path (Split-Path $dest) -Force|Out-Null
 if(-not(Test-Path $dest)){[IO.Compression.ZipFileExtensions]::ExtractToFile($entry[0],$dest)}
 $stream=$entry[0].Open();try{$h=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
 if((Get-FileHash $dest).Hash.ToLowerInvariant() -cne $h){throw 'OFFICIAL_REPORT_EXTRACTION_HASH'};$reportBindings[$name]=$h
}}finally{$reportZip.Dispose()}
$report=Get-Content (Join-Path $Root 'report-complete/consolidated_report.json') -Raw|ConvertFrom-Json
if($report.execution_commit -cne $ExpectedCommit -or $report.stage_count -ne 25 -or $report.dynamic_cases -ne 22 -or
 $report.status -cne 'CONDITIONAL_DEVELOPMENT_COMPLETED_NOT_EQUIPMENT_QUALIFIED' -or -not $report.no_aggregate_equipment_PASS){throw 'EXACT_REPORT_SCOPE'}
$stage=@{};$groups=@{};$files=0;$zips=0;$frames=0;$phaseCount=0;$models=0;$images=@();$sourceManifestCopies=0
foreach($a in $index.artifacts){
 $path=Join-Path $Root ($a.name+'.zip')
 if((Get-Item $path).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $path).Hash.ToLowerInvariant() -cne $a.digest){throw ('OFFICIAL_ZIP_IDENTITY '+$a.name)};$zips++
 if($a.name -notlike 'memphis-rack-raw-*'){continue}
 $dest=Join-Path $Root ('full/'+$a.name);if(-not(Test-Path $dest)){[IO.Compression.ZipFile]::ExtractToDirectory([IO.Path]::GetFullPath($path),[IO.Path]::GetFullPath($dest))}
 $invFiles=@(Get-ChildItem $dest -Recurse -File -Filter artifact_hashes.json)
 if($invFiles.Count -ne 1){throw 'EXACT_RAW_INVENTORY'}
 $base=$invFiles[0].Directory.FullName;$inv=Get-Content $invFiles[0].FullName -Raw|ConvertFrom-Json
 if($inv.source_commit -cne $ExpectedCommit){throw 'RAW_SOURCE_IDENTITY'};$groups[$inv.group]=$base
 $er=Get-Content (Join-Path $base 'environment_registration.json') -Raw|ConvertFrom-Json
 if($er.commit -cne $ExpectedCommit -or $er.manifest_raw_sha256 -cne $ExpectedManifest -or $er.cpu_rate -ne 2500 -or $er.process_mb -ne 1024 -or $er.job_mb -ne 2048 -or $er.wall_seconds -ne 480 -or $er.formal){throw 'REGISTERED_ENVIRONMENT'}
 foreach($b in $inv.records){$p=[IO.Path]::GetFullPath((Join-Path $base $b.path));if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'RAW_PATH_ESCAPE'}
  if((Get-Item $p).Length -ne $b.bytes -or (Get-FileHash $p).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('RAW_FILE_HASH '+$b.path)};$files++}
 $copies=@(Get-ChildItem $dest -Recurse -File -Filter source_manifest.json)
 if($copies.Count -ne 1 -or (Get-FileHash $copies[0].FullName).Hash.ToLowerInvariant() -cne $ExpectedManifest){throw 'OFFICIAL_SOURCE_MANIFEST_COPY'};$sourceManifestCopies++
 foreach($d in Get-ChildItem $base -Directory){
  $r=Get-Content (Join-Path $d.FullName 'result.json') -Raw|ConvertFrom-Json
  $ready=Get-Content (Join-Path $d.FullName 'ready.json') -Raw|ConvertFrom-Json
  $proofPath=Join-Path $d.FullName 'external_job_identity.json';$p=Get-Content $proofPath -Raw|ConvertFrom-Json
  $n=Get-Content (Join-Path $d.FullName 'job_status.json') -Raw|ConvertFrom-Json
  $release=Get-Content (Join-Path $d.FullName 'release.json') -Raw|ConvertFrom-Json
  if($stage.ContainsKey($r.stage) -or @($reg.cases|Where-Object {$_.id -ceq $r.stage -and $_.group -ceq $inv.group}).Count -ne 1 -or
   $release.actual_python_pid -ne $r.pid -or $release.external_proof_raw_sha256 -cne (Get-FileHash $proofPath).Hash.ToLowerInvariant()){throw 'EXACT_STAGE_GROUP_RELEASE'}
  if($r.status -cne 'PASS' -or $r.pid -ne $ready.pid -or $r.pid -ne $p.actual_python_pid -or -not $p.in_target_job -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048 -or
   -not $n.assigned_before_resume -or -not $n.resumed -or -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or $n.child_exitcode -ne 0 -or $n.outcome -cne 'EXITED'){throw ('ACTUAL_JOB_CLEANUP '+$r.stage)}
  if(($r.environment|ConvertTo-Json -Compress) -cne ($r.environment_after|ConvertTo-Json -Compress) -or $r.environment.source_commit -cne $ExpectedCommit -or $r.environment.python -cne '3.11.9' -or
   $r.environment.dependencies.numpy -cne '2.4.6' -or $r.environment.dependencies.pytest -cne '9.1.1' -or $r.environment.dependencies.jsonschema -cne '4.26.0' -or
   $r.environment.image -notin @('20261004.326.1','20261012.333.1') -or $r.environment.executable -cne $ready.executable -or $r.environment.executable -cne $er.python_executable -or
   $r.environment.job_proof_sha256 -cne (Get-FileHash $proofPath).Hash.ToLowerInvariant()){throw 'EXACT_EXECUTION_ENVIRONMENT'}
  $stage[$r.stage]=$d.FullName;$images+=$r.environment.image
 }
 foreach($file in Get-ChildItem $base -Recurse -File -Filter phases.json){
  $phases=Get-Content $file.FullName -Raw|ConvertFrom-Json;$phaseCount+=@($phases).Count;$models++
  $previous=$null
  foreach($f in $phases){$m=$f.PRE.measurement
   if($m.sample_ns -gt $m.release_ns -or $m.release_ns -gt $f.time_ns -or $f.SAFETY.pre_digest -cne $f.immutable_pre_digest -or $f.PLC.safety_digest -cne $f.immutable_safety_digest -or
    $f.POST.pre_id -cne $f.PRE.record_id -or $f.POST.plc_id -cne $f.PLC.record_id -or $f.actuator_command.producer_module -cne 'PLC'){throw 'PERSISTED_CAUSAL_PHASE_BINDING'}
   if($null -ne $previous -and ($f.PRE.old_command.value -ne $previous.command -or $f.PRE.old_command.issue_ns -ne $previous.issue_ns)){throw 'PERSISTED_PRE_FUTURE_COMMAND'};$previous=$f.PLC
  }
 }
 foreach($ix in Get-ChildItem $base -Recurse -File -Filter m1_completed_index.json){
  $rows=Get-Content $ix.FullName -Raw|ConvertFrom-Json;$stream=[IO.File]::OpenRead((Join-Path $ix.Directory.FullName 'm1_completed.zlib'));$cursor=0L
  try{foreach($row in $rows){
   if($row.offset -ne $cursor -or $row.compression -cne 'zlib' -or $row.bytes -gt 268435456){throw 'JOURNAL_FRAME_LAYOUT'}
   $buffer=[byte[]]::new([int]$row.stored_bytes);$pos=0
   while($pos -lt $buffer.Length){$got=$stream.Read($buffer,$pos,$buffer.Length-$pos);if($got -eq 0){throw 'TRUNCATED_FRAME'};$pos+=$got}
   $ms=[IO.MemoryStream]::new($buffer,$false);$zs=[IO.Compression.ZLibStream]::new($ms,[IO.Compression.CompressionMode]::Decompress);$out=[IO.MemoryStream]::new()
   try{$zs.CopyTo($out);$raw=$out.ToArray()}finally{$zs.Dispose();$ms.Dispose();$out.Dispose()}
   if($raw.Length -ne $row.bytes -or $raw[-1] -ne 10 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $row.raw_sha256){throw 'DECOMPRESSED_FRAME_RAW_IDENTITY'}
   $cursor+=$row.stored_bytes;$frames++
  };if($stream.Length -ne $cursor){throw 'UNREGISTERED_JOURNAL_TAIL'}}finally{$stream.Dispose()}
 }
}
if($zips -ne 9 -or $groups.Count -ne 4 -or $sourceManifestCopies -ne 4 -or $stage.Count -ne $reg.cases.Count -or @($reg.cases|Where-Object {-not $stage.ContainsKey($_.id)}).Count -or $frames -ne $phaseCount -or $models -ne 24){throw 'EXACT_COMPLETE_COVERAGE'}
foreach($pair in @(@('SR_HOT','SR_REPEAT'),@('SIX_HOT','SIX_REPEAT'))){foreach($name in @('series.json','physics.json')){
 if((Get-FileHash (Join-Path $stage[$pair[0]] ('case/'+$name))).Hash -cne (Get-FileHash (Join-Path $stage[$pair[1]] ('case/'+$name))).Hash){throw 'INDEPENDENT_REPEAT_DRIFT'}
}}
$prior=Get-Content (Join-Path $repo 'v0_2/tests/tools/gb300_m1_closed_loop_v2/v1_regression_hashes.json') -Raw|ConvertFrom-Json
foreach($case in @('LOAD_STEP','PUMP_STUCK')){foreach($b in $prior.$case.PSObject.Properties){if((Get-FileHash (Join-Path $stage['BASELINE'] ($case+'/'+$b.Name))).Hash.ToLowerInvariant() -cne $b.Value){throw 'FRESH_OLD_REGRESSION_RAW_DRIFT'}}}
$actual=[ordered]@{}
$inputs=[ordered]@{}
# Per-case outcome is re-derived from physical series, not just the PASS field.
foreach($spec in $reg.cases){if($spec.PSObject.Properties.Name -notcontains 'rack_count'){continue}
 $base=Join-Path $stage[$spec.id] 'case';$c=Get-Content (Join-Path $base 'input.json') -Raw|ConvertFrom-Json
 $inputs[$spec.id]=@{raw_sha256=(Get-FileHash (Join-Path $base 'input.json')).Hash.ToLowerInvariant();bytes=(Get-Item (Join-Path $base 'input.json')).Length}
 $rows=Get-Content (Join-Path $base 'series.json') -Raw|ConvertFrom-Json;$analysis=Get-Content (Join-Path $stage[$spec.id] 'independent_analysis.json') -Raw|ConvertFrom-Json
 if(($analysis|ConvertTo-Json -Depth 40 -Compress) -cne ($report.cases.($spec.id)|ConvertTo-Json -Depth 40 -Compress)){throw 'REPORT_VS_OFFICIAL_RAW_ANALYSIS'}
 if($c.rack_count -ne $spec.rack_count -or $c.liquid_fraction -ne .95 -or $c.supply_hard_k -ne 318.15 -or $rows.Count -ne $c.duration_ns/$c.dt_ns+1){throw 'CASE_DESIGN_OR_TIME_COVERAGE'}
 if($c.duration_ns -ne 120000000000 -or $c.density_kg_m3 -ne 1009 -or $c.cp_j_kg_k -ne 4000 -or
  $c.authority -cne 'CONDITIONAL_OFFLINE_DEVELOPMENT_NO_QUALIFICATION' -or $c.control_period_ns -ne 200000000 -or
  $c.sensor_period_ns -ne 200000000 -or $c.sensor_delay_ns -ne 100000000 -or $c.sensor_max_age_ns -ne 1000000000){throw 'EXACT_REGISTERED_CASE_BOUNDARIES'}
 $max=($rows|ForEach-Object supply_k|Measure-Object -Maximum).Maximum-273.15
 if([math]::Abs($max-$analysis.maximum_inlet_C) -gt 1e-10){throw 'PHYSICAL_THERMAL_SUMMARY'}
 if($spec.expect -eq 'NOMINAL' -and $max -gt 45){throw 'NOMINAL_HARD_LIMIT_EXCEEDED'}
 if($spec.expect -eq 'THERMAL_NEGATIVE' -and $max -le 45){throw 'THERMAL_NEGATIVE_NOT_PRESERVED'}
 foreach($row in $rows){if(@($row.branch_flows_m3_s).Count -ne $spec.rack_count -or @($row.rack_it_w|Where-Object {$_ -lt 0 -or $_ -gt 155000}).Count){throw 'RACK_IDENTITY_OR_LOAD_DERATE'}}
 # Account persisted transfers independently; this is a file-ledger check,
 # not a local rerun of the numerical/thermal model.
 $physics=Get-Content (Join-Path $base 'physics.json') -Raw|ConvertFrom-Json
 $cv=[double]$c.density_kg_m3*[double]$c.cp_j_kg_k
 $initialT=@($rows[0].supply_k)+@($rows[0].rack_return_k)+@($rows[0].return_k)
 $finalT=@($rows[-1].supply_k)+@($rows[-1].rack_return_k)+@($rows[-1].return_k)
 $initialE=0.;$finalE=0.;for($i=0;$i -lt $initialT.Count;$i++){$initialE+=[double]$initialT[$i]*$cv*[double]$c.volumes_m3[$i];$finalE+=[double]$finalT[$i]*$cv*[double]$c.volumes_m3[$i]}
 $liquid=0.;$pump=0.;$export=0.;$loadIndex=0
 foreach($p in $physics){
  $dt=([double]$p.end_ns-[double]$p.start_ns)/1e9
  while($loadIndex+1 -lt $c.load_profile.Count -and $c.load_profile[$loadIndex+1].time_ns -le $p.start_ns){$loadIndex++}
  if(($p.rack_it_w|ConvertTo-Json -Compress) -cne ($c.load_profile[$loadIndex].rack_it_w|ConvertTo-Json -Compress)){throw 'PERSISTED_NO_LOAD_DERATE'}
  $it=0.;foreach($w in $p.rack_it_w){$it+=[double]$w}
  $liquid+=$it*.95*$dt;$pump+=[double]$p.pump_electrical_w*$dt;$export+=[double]$p.hx_w*$dt
  $powerResidual=[double]$p.pump_electrical_w-[double]$p.pump_liquid_loss_w-[double]$p.hydraulic_w
  if([math]::Abs($powerResidual) -gt 4096*[math]::Pow(2,-53)*[math]::Max(1,2*[math]::Abs([double]$p.pump_electrical_w))){throw 'PERSISTED_PUMP_HEAT_DUPLICATION'}
 }
 $residual=$finalE-$initialE-$liquid-$pump+$export;$x=8192*($physics.Count+1)*[math]::Pow(2,-53)
 $bound=$x/(1-$x)*([math]::Abs($initialE)+[math]::Abs($finalE)+$liquid/.95+$liquid+$pump+[math]::Abs($export))
 if([math]::Abs($residual) -gt $bound){throw 'INDEPENDENT_PERSISTED_ENERGY_LEDGER'}
 $phases=Get-Content (Join-Path $base 'phases.json') -Raw|ConvertFrom-Json
 $cross=@($rows|Where-Object supply_k -gt 318.15|Select-Object -First 1)
 $protected=@($phases|Where-Object {$_.SAFETY.reason_codes -contains 'LIQUID_SUPPLY_LIMIT_MEASURED'}|Select-Object -First 1)
 $actual[$spec.id]=@{maximum_inlet_C=$max;final_inlet_C=$analysis.final_inlet_C;maximum_return_C=$analysis.maximum_return_C;
  final_return_C=$analysis.final_return_C;initial_flow_m3_h=$rows[0].flow_m3_s*3600;final_flow_m3_h=$analysis.final_flow_m3_h;
  final_branch_flow_m3_h=$analysis.final_branch_flow_m3_h;final_rack_return_C=$analysis.final_rack_return_C;
  first_physical_inlet_over45_s=$(if($cross.Count){$cross[0].time_ns/1e9}else{$null});first_measured_temperature_protection_s=$(if($protected.Count){$protected[0].time_ns/1e9}else{$null});
  final_hx_W=$physics[-1].hx_w;final_pump_electrical_W=$physics[-1].pump_electrical_w;supply45=$analysis.supply45;
  first_tracking_suspected_s=$analysis.first_tracking_suspected_s;first_tracking_confirmed_s=$analysis.first_tracking_confirmed_s;
  first_safety_fault_s=$analysis.first_safety_fault_s;independent_file_energy_residual_J=$residual;independent_file_energy_bound_J=$bound}
}
$logZip=[IO.Compression.ZipFile]::OpenRead((Join-Path $Root 'raw_logs.zip'));$logs=''
try{foreach($e in $logZip.Entries){if($e.FullName.EndsWith('.txt')){$reader=[IO.StreamReader]::new($e.Open());try{$logs+=$reader.ReadToEnd()}finally{$reader.Dispose()}}}}finally{$logZip.Dispose()}
foreach($spec in $reg.cases){if($logs -notmatch ('INTEGRATION_STAGE_END '+[regex]::Escape($spec.id)+' PASS')){throw 'MISSING_RAW_STAGE_END'}}
if($logs -notmatch 'RACK_REPORT_COMPLETED stages=25 dynamic=22'){throw 'MISSING_REPORT_END'}
[ordered]@{status='OFFICIAL_PERSISTED_EVIDENCE_VERIFIED_NOT_EQUIPMENT_QUALIFICATION';run=$run.id;execution_commit=$ExpectedCommit;manifest_raw_sha256=$ExpectedManifest;
 official_zips=$zips;raw_files=$files;source_bindings=$sources;stages=$stage.Count;actual_python_jobs=$stage.Count;models_including_fresh_old_baselines=$models;
 causal_phases=$phaseCount;decompressed_raw_journal_frames=$frames;images=@($images|Sort-Object -Unique);cleanup_complete_all=$true;active_after_cleanup_all=0;
 fresh_original_regression='8_FILES_EACH_BYTE_IDENTICAL';repeat='SINGLE_AND_SIX_PHYSICS_SERIES_BYTE_IDENTICAL';cases=$actual;
 input_bindings=$inputs;
 final_design_document_bindings=$design.final_design_sources;
 report_files_raw_sha256=$reportBindings;report_cases_match_official_raw=22;
 raw_logs_sha256=(Get-FileHash (Join-Path $Root 'raw_logs.zip')).Hash.ToLowerInvariant();official_artifacts=@($index.artifacts|Select-Object id,name,size_in_bytes,digest);
 formal_C3C=$false;production_hardware_Phase6=$false;local_model_execution=$false}|ConvertTo-Json -Depth 12
