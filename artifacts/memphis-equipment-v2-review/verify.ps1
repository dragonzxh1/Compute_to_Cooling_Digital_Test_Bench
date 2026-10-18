param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit,[Parameter(Mandatory)][string]$ExpectedManifest)
# Independent pure-file review. No Python/native/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$verifierAtStart=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
Add-Type -AssemblyName System.IO.Compression.FileSystem
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pkg=Join-Path $repo 'v0_2/tests/tools/memphis_equipment_validation_v2'
$reg=Get-Content (Join-Path $pkg 'registration.json') -Raw|ConvertFrom-Json
if((Get-FileHash (Join-Path $pkg 'source_manifest.json')).Hash.ToLowerInvariant() -cne $ExpectedManifest){throw 'LOCAL_MANIFEST_DRIFT'}
$manifest=Get-Content (Join-Path $pkg 'source_manifest.json') -Raw|ConvertFrom-Json
$bindings=0;$uniqueBindings=@{}
foreach($map in @($manifest.source_raw_sha256,$manifest.v1_source_raw_sha256,(Get-Content (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json') -Raw|ConvertFrom-Json).source_raw_sha256)){
 foreach($b in $map.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('SOURCE_DRIFT '+$b.Name)};if($uniqueBindings.ContainsKey($b.Name) -and $uniqueBindings[$b.Name] -cne $b.Value){throw 'CONFLICTING_SOURCE_REGISTRATION'};$uniqueBindings[$b.Name]=$b.Value;$bindings++}
}
$designRoot='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
foreach($prefix in @('00','01')){
 $f=@(Get-ChildItem -LiteralPath $designRoot -Filter ($prefix+'*.docx'))
 if($f.Count -ne 1 -or (Get-FileHash -LiteralPath $f[0].FullName).Hash.ToLowerInvariant() -cne $reg.input_hashes.$prefix){throw 'DESIGN_ORIGINAL_DRIFT'}
}
$run=Get-Content (Join-Path $Root 'run_metadata.json') -Raw|ConvertFrom-Json
if($run.head_sha -cne $ExpectedCommit -or $run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.run_attempt -ne 1){throw 'EXACT_RUN_IDENTITY'}
$index=Get-Content (Join-Path $Root 'official_artifact_index.json') -Raw|ConvertFrom-Json
$stages=@{};$files=0;$frames=0;$phases=0;$groups=0;$images=@();$energy=@();$inputHashes=[ordered]@{};$executionProofs=@()
function Check-UnitEnergy([string]$Directory){
 $input=Get-Content (Join-Path $Directory 'case/input.json') -Raw|ConvertFrom-Json
 $c=$input.config;$cv=$c.density_kg_m3*$c.cp_j_kg_k
 $steps=Get-Content (Join-Path $Directory 'case/physics.json') -Raw|ConvertFrom-Json
 $rows=Get-Content (Join-Path $Directory 'case/series.json') -Raw|ConvertFrom-Json
 if($steps.Count -ne $c.duration_ns/$c.dt_ns -or $rows.Count -ne $steps.Count+1){throw 'LOCAL_INTERVAL_COVERAGE'}
 $heat=0.;$pump=0.;$hx=0.;$maxLocal=0.;$maxInlet=-273.15
 foreach($s in $steps){
  $dt=($s.end_ns-$s.start_ns)/1e9;$load=0.;foreach($w in $s.rack_it_w){$load+=.95*$w}
  $q=$s.flow_m3_s;$branch=0.;foreach($f in $s.branch_flows_m3_s){$branch+=$f}
  if([Math]::Abs($branch-$q) -gt 4096*[Math]::Pow(2,-53)*[Math]::Max(1,[Math]::Abs($q)+[Math]::Abs($branch))){throw 'LOCAL_MASS_BALANCE'}
  $energyStep=0.;$oldEnergy=0.;$newEnergy=0.
  for($j=0;$j -lt $c.volumes_m3.Count;$j++){
   $cap=$cv*$c.volumes_m3[$j];$a=$s.old_k[$j]*$cap;$b=$s.new_k[$j]*$cap
   $expected=$dt*$s.rates_w[$j];$err=($b-$a)-$expected
   $tol=4096*[Math]::Pow(2,-53)*[Math]::Max(1,[Math]::Abs($a)+[Math]::Abs($b)+[Math]::Abs($expected))
   if([Math]::Abs($err) -gt $tol){throw 'LOCAL_RECOMPUTED_STORAGE'}
   $maxLocal=[Math]::Max($maxLocal,[Math]::Abs($err));$oldEnergy+=$a;$newEnergy+=$b;$energyStep+=$expected
  }
  $external=$dt*($load+$s.pump_electrical_w-$s.hx_w)
  $tol=8192*[Math]::Pow(2,-53)*([Math]::Abs($oldEnergy)+[Math]::Abs($newEnergy)+[Math]::Abs($external))
  if([Math]::Abs(($newEnergy-$oldEnergy)-$external) -gt $tol){throw 'LOCAL_RECOMPUTED_EXTERNAL_LEDGER'}
  $heat+=$dt*$load;$pump+=$dt*$s.pump_electrical_w;$hx+=$dt*$s.hx_w
  $maxInlet=[Math]::Max($maxInlet,$s.new_k[0]-273.15)
 }
 $initial=0.;$final=0.
 for($j=0;$j -lt $c.volumes_m3.Count;$j++){$initial+=$steps[0].old_k[$j]*$cv*$c.volumes_m3[$j];$final+=$steps[-1].new_k[$j]*$cv*$c.volumes_m3[$j]}
 $residual=$final-$initial-$heat-$pump+$hx
 $ops=8192*($steps.Count+1);$g=$ops*[Math]::Pow(2,-53)/(1-$ops*[Math]::Pow(2,-53));$tol=$g*([Math]::Abs($initial)+[Math]::Abs($final)+$heat+$pump+[Math]::Abs($hx))
 if([Math]::Abs($residual) -gt $tol){throw 'LOCAL_RECOMPUTED_GLOBAL_LEDGER'}
 return @{residual_j=$residual;bound_j=$tol;max_local_j=$maxLocal;maximum_inlet_c=[Math]::Max($maxInlet,$rows[0].supply_k-273.15);steps=$steps.Count;heat_j=$heat;pump_j=$pump;hx_j=$hx}
}
function Group-Stored($Row){
 $cv=1009*4000;$total=0.;$vol=@(.1)+@(.025)*6+@(.15)*6+@(.15)
 foreach($u in $Row.units){$temps=@($u.supply_header_k)+@($u.inlet_k)+@($u.rack_return_k)+@($u.return_k);for($j=0;$j -lt $vol.Count;$j++){$total+=$cv*$vol[$j]*$temps[$j]}}
 foreach($name in @('tank_A_k','tank_B_k')){foreach($t in $Row.$name){$total+=$cv*15/$Row.$name.Count*$t}}
 foreach($p in $Row.source_pipe_k.PSObject.Properties){foreach($t in $p.Value){$total+=$cv*2.75/$p.Value.Count*$t}}
 return $total
}
function Check-Buffer([string]$Directory){
 $steps=Get-Content (Join-Path $Directory 'buffer_steps.json') -Raw|ConvertFrom-Json
 $cv=1009*4000;$cap=$cv*15/$steps[0].old_k.Count;$initial=0.;$final=0.;$net=0.;$end=0.;$rise=0.
 foreach($t in $steps[0].old_k){$initial+=$cap*$t}
 foreach($s in $steps){
  $dt=$s.end_s-$end;$end=$s.end_s;$a=0.;$b=0.
  if([Math]::Abs($s.load_m3_s*3600-330) -gt 1e-8 -or $s.source_m3_s -ne 0 -or $s.return_k -ne 321.44 -or $s.pump_loss_w -ne 0){throw 'BUFFER_REGISTERED_BOUNDARY_DRIFT'}
  for($j=0;$j -lt $s.old_k.Count;$j++){$a+=$cap*$s.old_k[$j];$b+=$cap*$s.new_k[$j]}
  $expected=$cv*$s.load_m3_s*($s.return_k-$s.old_k[0])*$dt
  if([Math]::Abs($b-$a-$expected) -gt 4096*[Math]::Pow(2,-53)*([Math]::Abs($a)+[Math]::Abs($b)+[Math]::Abs($expected))){throw 'BUFFER_GEOMETRIC_ENERGY'}
  $net+=$expected;$rise=[Math]::Max($rise,$s.new_k[0]-$steps[0].old_k[0]);$final=$b
 }
 if($end -ne 90){throw 'BUFFER_90S_COVERAGE'}
 $residual=$final-$initial-$net;$ops=8192*($steps.Count+1);$g=$ops*[Math]::Pow(2,-53)/(1-$ops*[Math]::Pow(2,-53));$tol=$g*([Math]::Abs($initial)+[Math]::Abs($final)+[Math]::Abs($net))
 if([Math]::Abs($residual) -gt $tol){throw 'BUFFER_GLOBAL_ENERGY'}
 return @{maximum_outlet_rise_K=$rise;residual_j=$residual;bound_j=$tol;steps=$steps.Count}
}
function Check-GroupEnergy([string]$Directory){
 $rows=Get-Content (Join-Path $Directory 'case/series.json') -Raw|ConvertFrom-Json
 $steps=Get-Content (Join-Path $Directory 'case/physics.json') -Raw|ConvertFrom-Json
 $initial=Group-Stored $rows[0];$final=Group-Stored $rows[-1];$previous=$initial;$heat=0.;$pump=0.;$reject=0.;$maxError=0.;$maxInlet=-273.15;$lookup=@{}
 $cold330=$null;$cold264=$null;$terminal=$true;$terminalBegin=$steps[-1].end_ns-5000000000
 foreach($r in $rows){$lookup[[string]$r.time_ns]=$r;foreach($u in $r.units){foreach($t in $u.inlet_k){$maxInlet=[Math]::Max($maxInlet,$t-273.15)}}}
 foreach($s in $steps){
  $dt=($s.end_ns-$s.start_ns)/1e9;$h=2650500*$dt;$p=($s.primary_pump_electrical_w+$s.secondary_pump_electrical_w)*$dt;$x=$s.rejected_w*$dt
  $err=$s.stored_j-$previous-$h-$p+$x;$tol=4096*[Math]::Pow(2,-53)*([Math]::Abs($previous)+[Math]::Abs($s.stored_j)+[Math]::Abs($h)+[Math]::Abs($p)+[Math]::Abs($x))
  if([Math]::Abs($err) -gt $tol){throw 'GROUP_STEP_ENERGY_RECOMPUTATION'}
  if($lookup.ContainsKey([string]$s.end_ns)){
   $actual=Group-Stored $lookup[[string]$s.end_ns]
   if([Math]::Abs($actual-$s.stored_j) -gt 4096*[Math]::Pow(2,-53)*([Math]::Abs($actual)+[Math]::Abs($s.stored_j))){throw 'GROUP_GEOMETRIC_STORAGE_BINDING'}
  }
  foreach($u in $s.unit_records){foreach($t in $u.new_k[1..6]){$maxInlet=[Math]::Max($maxInlet,$t-273.15)}}
  $available=$s.source_available.($s.source_path)
  $ready330=$available -and $s.source_flow_m3_h -ge 330-1e-8 -and $s.source_return_k -le 314.5948
  $ready264=$available -and $s.source_flow_m3_h -ge 264-1e-8 -and $s.source_return_k -le 314.5948
  if($s.start_ns -ge 30000000000){
   if($null -eq $cold330 -and $ready330){$cold330=$s.end_ns/1e9-30}
   if($null -eq $cold264 -and $ready264){$cold264=$s.end_ns/1e9-30}
  }
  if($s.end_ns -gt $terminalBegin -and -not $ready330){$terminal=$false}
  $maxError=[Math]::Max($maxError,[Math]::Abs($err));$previous=$s.stored_j;$heat+=$h;$pump+=$p;$reject+=$x
 }
 $residual=$final-$initial-$heat-$pump+$reject;$ops=8192*($steps.Count+1);$g=$ops*[Math]::Pow(2,-53)/(1-$ops*[Math]::Pow(2,-53));$tol=$g*([Math]::Abs($initial)+[Math]::Abs($final)+$heat+$pump+[Math]::Abs($reject))
 if([Math]::Abs($residual) -gt $tol){throw 'GROUP_GLOBAL_ENERGY_RECOMPUTATION'}
 return @{residual_j=$residual;bound_j=$tol;maximum_step_j=$maxError;maximum_inlet_c=$maxInlet;heat_j=$heat;pump_j=$pump;rejected_j=$reject;steps=$steps.Count;post_fault_cold330_s=$cold330;post_fault_cold264_s=$cold264;terminal_source_ready=$terminal}
}
foreach($artifact in $index.artifacts){
 $zip=Join-Path $Root ($artifact.name+'.zip')
 if((Get-Item $zip).Length -ne $artifact.size_in_bytes -or 'sha256:'+(Get-FileHash $zip).Hash.ToLowerInvariant() -cne $artifact.digest){throw 'OFFICIAL_ARTIFACT_DRIFT'}
 if($artifact.name -notlike 'memphis-equipment-raw-*'){continue}
 $dest=Join-Path $Root ('full/'+$artifact.name)
 if(-not(Test-Path -LiteralPath $dest)){[IO.Compression.ZipFile]::ExtractToDirectory([IO.Path]::GetFullPath($zip),[IO.Path]::GetFullPath($dest))}
 $inv=@(Get-ChildItem -LiteralPath $dest -Recurse -File -Filter artifact_hashes.json)
 if($inv.Count -ne 1){throw 'RAW_INVENTORY_REQUIRED'};$base=$inv[0].Directory.FullName
 $hashes=Get-Content $inv[0].FullName -Raw|ConvertFrom-Json
 if($hashes.source_commit -cne $ExpectedCommit){throw 'RAW_SOURCE_IDENTITY'}
 $copies=@(Get-ChildItem -LiteralPath $dest -Recurse -File -Filter source_manifest.json)
 if($copies.Count -ne 1 -or (Get-FileHash $copies[0].FullName).Hash.ToLowerInvariant() -cne $ExpectedManifest){throw 'OFFICIAL_MANIFEST_COPY_DRIFT'}
 $envReg=Get-Content (Join-Path $base 'environment_registration.json') -Raw|ConvertFrom-Json
 if($envReg.commit -cne $ExpectedCommit -or $envReg.manifest_raw_sha256 -cne $ExpectedManifest -or $envReg.cpu_rate -ne 2500 -or $envReg.process_mb -ne 1024 -or $envReg.job_mb -ne 2048 -or $envReg.wall_seconds -ne 480){throw 'RESOURCE_REGISTRATION'}
 foreach($b in $hashes.records){
  $p=[IO.Path]::GetFullPath((Join-Path $base $b.path))
  if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'RAW_PATH_ESCAPE'}
  if((Get-Item $p).Length -ne $b.bytes -or (Get-FileHash $p).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('RAW_FILE_DRIFT '+$b.path)};$files++
 }
 foreach($spec in $reg.cases|Where-Object group -ceq $hashes.group){
  $d=Join-Path $base $spec.id;$r=Get-Content (Join-Path $d 'result.json') -Raw|ConvertFrom-Json
  $proof=Get-Content (Join-Path $d 'external_job_identity.json') -Raw|ConvertFrom-Json
  $ready=Get-Content (Join-Path $d 'ready.json') -Raw|ConvertFrom-Json
  $release=Get-Content (Join-Path $d 'release.json') -Raw|ConvertFrom-Json
  $status=Get-Content (Join-Path $d 'job_status.json') -Raw|ConvertFrom-Json
  if($stages.ContainsKey($spec.id) -or $r.status -cne 'PASS' -or $r.stage -cne $spec.id -or $r.pid -ne $ready.pid -or $r.pid -ne $proof.actual_python_pid -or $r.pid -ne $release.actual_python_pid -or -not $proof.in_target_job -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or -not $status.assigned_before_resume -or -not $status.cleanup_complete -or $status.active_after_cleanup -ne 0 -or $status.child_exitcode -ne 0 -or $status.outcome -cne 'EXITED'){throw ('ACTUAL_JOB_OR_CLEANUP '+$spec.id)}
  $ph=(Get-FileHash (Join-Path $d 'external_job_identity.json')).Hash.ToLowerInvariant()
  if($release.external_proof_raw_sha256 -cne $ph -or $r.environment.job_proof_sha256 -cne $ph -or $r.environment.source_commit -cne $ExpectedCommit -or $r.environment.python -cne '3.11.9' -or $r.environment.image -notin @('20261004.326.1','20261012.333.1') -or $r.environment.dependencies.numpy -cne '2.4.6' -or $r.environment.dependencies.pytest -cne '9.1.1' -or $r.environment.dependencies.jsonschema -cne '4.26.0' -or ($r.environment|ConvertTo-Json -Compress) -cne ($r.environment_after|ConvertTo-Json -Compress)){throw 'ENVIRONMENT_OR_RELEASE_DRIFT'}
  $images+=$r.environment.image;$stages[$spec.id]=$d
  $executionProofs+=@{stage=$spec.id;actual_python_pid=$r.pid;environment=$r.environment;result_raw_sha256=(Get-FileHash (Join-Path $d 'result.json')).Hash.ToLowerInvariant();job_proof_raw_sha256=$ph;release_raw_sha256=(Get-FileHash (Join-Path $d 'release.json')).Hash.ToLowerInvariant();cleanup_raw_sha256=(Get-FileHash (Join-Path $d 'job_status.json')).Hash.ToLowerInvariant();active_after_cleanup=0;child_exitcode=0}
  $input=Join-Path $d 'case/input.json'
  if(Test-Path $input){$inputHashes[$spec.id]=(Get-FileHash $input).Hash.ToLowerInvariant()}
  if($spec.kind -ceq 'unit'){
   $computed=Check-UnitEnergy $d
   if([Math]::Abs($computed.maximum_inlet_c-$r.analysis.maximum_inlet_c) -gt 1e-10){throw 'INDEPENDENT_THERMAL_RESULT_DRIFT'}
   $thermal=if($computed.maximum_inlet_c -le 45){'PASS'}else{'FAIL'}
   if($r.analysis.grades.RACK_THERMAL_COMPLIANCE -cne $thermal){throw 'THERMAL_FAILURE_HIDDEN'}
   $energy+=@{case=$spec.id;recomputed=$computed}
  }
  if($spec.kind -ceq 'buffer'){
   $computed=Check-Buffer $d;$grade=if($computed.maximum_outlet_rise_K -le .5){'PASS'}else{'FAIL'}
   if([Math]::Abs($computed.maximum_outlet_rise_K-$r.analysis.maximum_outlet_rise_K) -gt 1e-10 -or $grade -cne $r.analysis.grades.'90_SECOND_BUFFER_COMPLIANCE'){throw 'BUFFER_RESULT_FAILURE_HIDDEN'}
   $energy+=@{case=$spec.id;recomputed=$computed}
  }
  if($spec.kind -ceq 'group'){
   $computed=Check-GroupEnergy $d
   if([Math]::Abs($computed.maximum_inlet_c-$r.analysis.maximum_inlet_c) -gt 1e-10){throw 'GROUP_THERMAL_RESULT_DRIFT'}
   $thermal=if($computed.maximum_inlet_c -le 45){'PASS'}else{'FAIL'}
   if($r.analysis.grades.RACK_THERMAL_COMPLIANCE -cne $thermal){throw 'GROUP_THERMAL_FAILURE_HIDDEN'}
   $hasFault=$spec.PSObject.Properties.Name -contains 'fault'
   if($hasFault){
    if($computed.post_fault_cold330_s -ne $r.analysis.first_cold_return_330_delay_s -or $computed.post_fault_cold264_s -ne $r.analysis.historical_264_threshold_delay_s){throw 'POST_FAULT_RETURN_TIMING_DRIFT'}
   }elseif($null -ne $r.analysis.first_cold_return_330_delay_s -or $null -ne $r.analysis.historical_264_threshold_delay_s){throw 'NO_FAULT_FALSE_RECOVERY_CLAIM'}
   if($computed.terminal_source_ready -ne $r.analysis.terminal_source_recovery_maintained){throw 'TERMINAL_SOURCE_RECOVERY_DRIFT'}
   $recovered=$hasFault -and $null -ne $computed.post_fault_cold330_s -and $computed.post_fault_cold330_s -le 90 -and $computed.terminal_source_ready
   $recoveryGrade=if(-not $hasFault){'INCOMPLETE'}elseif($recovered){'PASS'}else{'FAIL'}
   if($recoveryGrade -cne $r.analysis.grades.FAILOVER_RECOVERY){throw 'GROUP_RECOVERY_FAILURE_HIDDEN'}
   $energy+=@{case=$spec.id;recomputed=$computed}
   $sourceFrames=Get-Content (Join-Path $d 'case/source_phases.json') -Raw|ConvertFrom-Json
   $priorRequest=$null
   foreach($f in $sourceFrames){
    $o=$f.measurement;$request=$f.request
    if($o.sample_ns -gt $o.release_ns -or $o.release_ns -gt $f.time_ns -or $request.permission -cne $f.safety.sha256 -or $f.PLC.data.safety_sha256 -cne $f.safety.sha256 -or $request.observation_id -cne $o.record_id -or $f.PLC.data.measurement_id -cne $o.record_id){throw 'SOURCE_OBSERVATION_PLC_BINDING'}
    if($priorRequest -and $priorRequest.load_tank -cne $request.load_tank -and $request.load_tank -ceq 'B' -and -not $o.leak_A){
     $reserve=0.;for($j=0;$j -lt $o.tank_B_tt_k.Count-1;$j++){if($o.tank_B_tt_k[$j] -le 314.5948 -and $o.tank_B_tt_k[$j+1] -le 314.5948){$reserve+=5}}
     if($reserve -lt 8.25 -or $f.time_ns-$o.sample_ns -gt 1000000000 -or $o.maximum_secondary_inlet_c -lt 44.5){throw 'UNPROVEN_B_RESERVE_OR_TRIGGER'}
    }
    $priorRequest=$request
   }
   if($spec.id -in @('G_B_WARM','G_VALVE_STUCK') -and @($r.analysis.actual_AB_switches).Count -ne 0){throw 'INVALID_BACKUP_ACCEPTED'}
  }
 }
 foreach($f in Get-ChildItem -LiteralPath $base -Recurse -File -Filter phases.json){
  $all=Get-Content $f.FullName -Raw|ConvertFrom-Json;$previous=@{};$latches=@{}
  foreach($row in $all){
   $unit=if($row.PSObject.Properties.Name -contains 'unit'){[string]$row.unit}else{'0'}
   $m=$row.PRE.measurement
   if($m.sample_ns -gt $m.release_ns -or $m.release_ns -gt $row.time_ns -or $row.SAFETY.pre_digest -cne $row.immutable_pre_digest -or $row.PLC.safety_digest -cne $row.immutable_safety_digest -or $row.POST.plc_id -cne $row.PLC.record_id -or $row.POST.pre_id -cne $row.PRE.record_id -or $row.actuator_command.producer_module -cne 'PLC'){throw 'PERSISTED_PHASE_BINDING'}
   if($previous.ContainsKey($unit) -and ($row.PRE.old_command.value -ne $previous[$unit].command -or $row.PRE.old_command.issue_ns -ne $previous[$unit].issue_ns)){throw 'PRE_FUTURE_COMMAND'}
   if($latches.ContainsKey($unit) -and $row.SAFETY.severity -cne 'FAULT'){throw 'FAULT_LATCH_CLEARED'}
   if($row.SAFETY.severity -ceq 'FAULT'){$latches[$unit]=$true};$previous[$unit]=$row.PLC;$phases++
  }
 }
 foreach($ix in Get-ChildItem -LiteralPath $base -Recurse -File -Filter '*_index.json'|Where-Object BaseName -like 'm1_*'){
  $journal=Join-Path $ix.Directory.FullName (($ix.BaseName -replace '_index$','')+'.zlib')
  if(-not(Test-Path $journal)){continue}
  $rows=Get-Content $ix.FullName -Raw|ConvertFrom-Json;$stream=[IO.File]::OpenRead($journal);$cursor=0L
  try{foreach($row in $rows){
   if($row.offset -ne $cursor -or $row.compression -cne 'zlib' -or $row.bytes -gt 268435456){throw 'JOURNAL_LAYOUT'}
   $buffer=[byte[]]::new([int]$row.stored_bytes);$pos=0
   while($pos -lt $buffer.Length){$n=$stream.Read($buffer,$pos,$buffer.Length-$pos);if($n -eq 0){throw 'TRUNCATED_JOURNAL'};$pos+=$n}
   $ms=[IO.MemoryStream]::new($buffer,$false);$zs=[IO.Compression.ZLibStream]::new($ms,[IO.Compression.CompressionMode]::Decompress);$out=[IO.MemoryStream]::new()
   try{$zs.CopyTo($out);$bytes=$out.ToArray()}finally{$zs.Dispose();$ms.Dispose();$out.Dispose()}
   if($bytes.Length -ne $row.bytes -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne $row.raw_sha256){throw 'JOURNAL_RAW_HASH'}
   $cursor+=$row.stored_bytes;$frames++
  };if($stream.Length -ne $cursor){throw 'JOURNAL_UNREGISTERED_TAIL'}}finally{$stream.Dispose()}
 }
 $groups++;Write-Host ('INDEPENDENT_GROUP_VERIFIED '+$hashes.group)
}
if($groups -ne 7 -or $stages.Count -ne $reg.cases.Count -or $frames -ne $phases){throw 'REGISTERED_COVERAGE_INCOMPLETE'}
$priorRoot='D:/Github/c2c-evidence-review/memphis-equipment-v2/run39087966476'
$priorIndex=Get-Content (Join-Path $priorRoot 'official_artifact_index.json') -Raw|ConvertFrom-Json
$unchangedPhysics=0
foreach($a in $priorIndex.artifacts|Where-Object name -like 'memphis-equipment-raw-*'){
 $zipPath=Join-Path $priorRoot ($a.name+'.zip')
 if('sha256:'+(Get-FileHash $zipPath).Hash.ToLowerInvariant() -cne $a.digest){throw 'PRIOR_DEFECT_EVIDENCE_DRIFT'}
 $archive=[IO.Compression.ZipFile]::OpenRead($zipPath)
 try{
  $entries=@($archive.Entries|Where-Object Name -ceq 'artifact_hashes.json')
  if($entries.Count -ne 1){throw 'PRIOR_RAW_INVENTORY'}
  $reader=[IO.StreamReader]::new($entries[0].Open());try{$priorInventory=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
  foreach($record in $priorInventory.records|Where-Object {$_.path -match '^[^/]+/(?:case/(?:series|physics)\.json|buffer_steps\.json)$'}){
   $parts=$record.path.Split('/',2);$id=$parts[0]
   if($id -notin @($reg.cases|Where-Object {$_.kind -in @('unit','group','buffer')}|ForEach-Object id)){continue}
   if((Get-FileHash (Join-Path $stages[$id] $parts[1])).Hash.ToLowerInvariant() -cne $record.raw_sha256){throw ('AUDIT_ONLY_CHANGE_ALTERED_PHYSICS '+$id)}
   $unchangedPhysics++
  }
 }finally{$archive.Dispose()}
}
if($unchangedPhysics -ne 82){throw 'AUDIT_ONLY_PHYSICS_COMPARISON_COVERAGE'}
foreach($file in @('series.json','physics.json')){
 if((Get-FileHash (Join-Path $stages.SIX_UA220 ('case/'+$file))).Hash -cne (Get-FileHash (Join-Path $stages.SIX_REPEAT ('case/'+$file))).Hash){throw 'FRESH_REPEAT_DRIFT'}
}
$reportArtifact=@($index.artifacts|Where-Object name -like 'memphis-equipment-report-*')
if($reportArtifact.Count -ne 1){throw 'EXACT_OFFICIAL_REPORT'}
$reportDest=Join-Path $Root 'report-complete'
if(-not(Test-Path $reportDest)){[IO.Compression.ZipFile]::ExtractToDirectory([IO.Path]::GetFullPath((Join-Path $Root ($reportArtifact[0].name+'.zip'))),[IO.Path]::GetFullPath($reportDest))}
$report=Get-Content (Join-Path $reportDest 'consolidated_report.json') -Raw|ConvertFrom-Json
if($report.source_commit -cne $ExpectedCommit -or $report.stage_count -ne $reg.cases.Count){throw 'CONSOLIDATED_SCOPE_DRIFT'}
foreach($s in $report.stages){
 $actual=Get-Content (Join-Path $stages[$s.stage] 'independent_analysis.json') -Raw|ConvertFrom-Json
 if(($actual|ConvertTo-Json -Depth 70 -Compress) -cne ($s.analysis|ConvertTo-Json -Depth 70 -Compress)){throw ('CONSOLIDATED_RESULT_DRIFT '+$s.stage)}
}
$plotPoints=0
foreach($spec in $reg.cases|Where-Object {$_.kind -in @('unit','group')}){
 $series=Get-Content (Join-Path $stages[$spec.id] 'case/series.json') -Raw|ConvertFrom-Json
 if($spec.kind -ceq 'unit'){$series=@($series|Where-Object {$_.time_ns%1000000000 -eq 0})}
 $plotted=$report.plots.($spec.id)
 if($plotted.Count -ne $series.Count){throw 'PLOT_INTERVAL_COVERAGE'}
 for($i=0;$i -lt $series.Count;$i++){
  $r=$series[$i]
  if($spec.kind -ceq 'unit'){
   $expected=[ordered]@{t=$r.time_ns/1e9;inlet=$r.supply_k-273.15;outlet=($r.rack_return_k|Measure-Object -Maximum).Maximum-273.15;mixed=$r.return_k-273.15;flow=$r.flow_m3_s*3600;head=$r.dp_pa/1000;main=$r.main_speed;backup=$r.backup_speed;cdu=$r.active_cdu;valve=$r.valve_opening}
  }else{
   $maximum=($r.units|ForEach-Object {$_.inlet_k}|Measure-Object -Maximum).Maximum
   $expected=[ordered]@{t=$r.time_ns/1e9;inlet=$maximum-273.15;primary=$r.primary_inlet_c;flow=$r.source_flow_m3_h;A=$r.cold_A_m3;B=$r.cold_B_m3;load=$r.actual_load_selector;valve=$r.actual_load_valve;sourceSpeed=$r.source_actual_speed;state=$r.source_state}
  }
  foreach($k in $expected.Keys){if($expected[$k] -cne $plotted[$i].$k){throw ('PLOT_PHYSICAL_VALUE_DRIFT '+$spec.id+' '+$i+' '+$k)}}
  $plotPoints++
 }
}
$logPath=Join-Path $Root 'raw_logs.zip';$logZip=[IO.Compression.ZipFile]::OpenRead($logPath);$logText=[Text.StringBuilder]::new()
try{foreach($entry in $logZip.Entries){if($entry.Length -eq 0){continue};$reader=[IO.StreamReader]::new($entry.Open());try{$null=$logText.AppendLine($reader.ReadToEnd())}finally{$reader.Dispose()}}}finally{$logZip.Dispose()}
foreach($spec in $reg.cases){if(-not $logText.ToString().Contains('INTEGRATION_STAGE_END '+$spec.id+' PASS')){throw ('RAW_LOG_STAGE_END_MISSING '+$spec.id)}}
if(-not $logText.ToString().Contains('EQUIPMENT_REPORT_COMPLETE '+$reg.cases.Count)){throw 'RAW_LOG_REPORT_COMPLETION_MISSING'}
$testCounts=@{}
foreach($pair in @(@('BASELINE',12),@('NEGATIVE',31))){
 $stdout=Get-Content (Join-Path $stages[$pair[0]] 'stdout.raw') -Raw
 $matches=[regex]::Matches($stdout,'(?m)^([.]+)\s+\[100%\]\s*$')
 if($matches.Count -ne 1 -or $matches[0].Groups[1].Value.Length -ne $pair[1]){throw 'ACTUAL_PYTEST_COVERAGE'}
 $testCounts[$pair[0]]=$pair[1]
}
if((Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant() -cne $verifierAtStart){throw 'VERIFIER_CHANGED_DURING_REVIEW'}
$out=[ordered]@{status='OFFICIAL_ARTIFACT_AND_PERSISTED_EVIDENCE_VERIFIED';source_commit=$ExpectedCommit;manifest_raw_sha256=$ExpectedManifest;verifier_raw_sha256=$verifierAtStart;source_bindings=$bindings;unique_source_files=$uniqueBindings.Count;official_zips=$index.total_count;raw_files=$files;stage_count=$stages.Count;groups=$groups;pytest_counts=$testCounts;verified_plot_points=$plotPoints;unchanged_physics_files_vs_build4=$unchangedPhysics;phases=$phases;journal_frames=$frames;images=@($images|Select-Object -Unique);input_raw_hashes=$inputHashes;independent_energy=$energy;raw_logs_sha256=(Get-FileHash $logPath).Hash.ToLowerInvariant();report_raw_sha256=(Get-FileHash (Join-Path $reportDest 'consolidated_report.json')).Hash.ToLowerInvariant();repeat='BYTE_IDENTICAL_SERIES_AND_PHYSICS';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';hardware='CALIBRATION_REQUIRED';formal=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $Root 'independent_verification.json'),($out|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$closure=[ordered]@{schema='MEMPHIS-V2-SOURCE-INPUT-ENVIRONMENT-CLOSURE';source_commit=$ExpectedCommit;run_id=$run.id;run_attempt=$run.run_attempt;source_manifest_raw_sha256=$ExpectedManifest;registration_raw_sha256=(Get-FileHash (Join-Path $pkg 'registration.json')).Hash.ToLowerInvariant();candidate_sha256=$manifest.candidate_sha256;source_file_raw_sha256=$uniqueBindings;customer_document_raw_sha256=$reg.input_hashes;scenario_input_raw_sha256=$inputHashes;stages=$executionProofs;official_artifacts=$index.artifacts|Select-Object id,name,size_in_bytes,digest;raw_logs_sha256=$out.raw_logs_sha256;scope='OFFLINE_ENGINEERING_DEVELOPMENT_NOT_OEM_OR_FORMAL_QUALIFICATION'}
[IO.File]::WriteAllText((Join-Path $Root 'source_input_environment_manifest.json'),($closure|ConvertTo-Json -Depth 25),[Text.UTF8Encoding]::new($false))
$out|ConvertTo-Json -Depth 3
