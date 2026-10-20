param([string]$RunId='39408912940',[string]$Commit='3ee9f97f31f5f395e51c1a561b2a8aed8ba2c97d')
# Independent file review of a FAILED finite campaign. This is not the full verifier,
# does not execute candidate code, and can NEVER emit a campaign PASS.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($RunId -cne '39408912940' -or $Commit -cne '3ee9f97f31f5f395e51c1a561b2a8aed8ba2c97d'){throw 'EXACT_PARTIAL_EXECUTION_REQUIRED'}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$base='D:/Github/c2c-evidence-review/memphis-control-path-v1/run'+$RunId
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$utf=[Text.UTF8Encoding]::new($false)
$manifest='14964e55fe39f721ffd2fd03e8cd3f2f1e58a0ae168d630c07e2be62c04fbf97'
function ReadEntry($z,$name){$e=$z.GetEntry($name);if(-not $e){throw ('ENTRY_MISSING '+$name)};$r=[IO.StreamReader]::new($e.Open());try{return $r.ReadToEnd()|ConvertFrom-Json}finally{$r.Dispose()}}
function HashEntry($e){$s=$e.Open();try{return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}}
function GitBlob($bytes){$h=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));return [Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($h+$bytes))).ToLowerInvariant()}
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.head_sha -cne $Commit -or $run.status -cne 'completed' -or $run.conclusion -cne 'failure' -or $run.run_attempt -ne 1){throw 'COMPLETED_FAILED_EXACT_RUN_REQUIRED'}
$listing=gh api ($api+'/actions/runs/'+$RunId+'/artifacts?per_page=100')|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'LISTING'}
$tree=gh api ($api+'/git/trees/'+$Commit+'?recursive=1')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $tree.truncated){throw 'FULL_EXECUTION_TREE_REQUIRED'}
$treeMap=@{};foreach($p in $tree.tree){$treeMap[$p.path]=$p}
$m=Get-Content -Raw (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/source_manifest.json')|ConvertFrom-Json
if((Get-FileHash (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/source_manifest.json')).Hash.ToLowerInvariant() -cne $manifest){throw 'LOCAL_SEALED_MANIFEST_DRIFT'}
$freeze=Get-Content -Raw (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json')|ConvertFrom-Json
$hydratePath='v0_2/tests/tools/m1_remote_control_v3/execution_manifest.json'
$hydrate=Get-Content -Raw (Join-Path $repo $hydratePath)|ConvertFrom-Json
if((Get-FileHash (Join-Path $repo $hydratePath)).Hash.ToLowerInvariant() -cne '6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93'){throw 'SEALED_HYDRATION_MANIFEST'}
$bundlePath=Join-Path $repo $hydrate.bundle_path;$bundleBytes=[IO.File]::ReadAllBytes($bundlePath)
if((Get-FileHash $bundlePath).Hash.ToLowerInvariant() -cne $hydrate.bundle_raw_sha256 -or $treeMap[$hydrate.bundle_path].sha -cne (GitBlob $bundleBytes)){throw 'REMOTE_SEALED_BUNDLE'}
$bz=[IO.Compression.ZipFile]::OpenRead($bundlePath);try{foreach($p in $hydrate.bundle_entry_raw_hashes.PSObject.Properties){$e=$bz.GetEntry($p.Name);if(-not $e -or (HashEntry $e) -cne $p.Value){throw 'BUNDLE_ENTRY_DRIFT'}}}finally{$bz.Dispose()}
$counts=@();foreach($map in @($m.source_raw_sha256,$m.v1_source_raw_sha256,$freeze.source_raw_sha256)){
 $count=0;foreach($p in $map.PSObject.Properties){
  # Publication intentionally uses branch-only CI bytes in the immutable snapshot,
  # not the user's checkout CI. Never overwrite checkout files to make a check pass.
  $local=if($p.Name -ceq '.github/workflows/ci.yml'){Join-Path $PSScriptRoot ('source-3ee9f97/'+$p.Name)}else{Join-Path $repo $p.Name}
  $b=[IO.File]::ReadAllBytes($local);$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($b)).ToLowerInvariant()
  $hb=$hydrate.bundle_entry_raw_hashes.PSObject.Properties[$p.Name]
  $bound=if($null -ne $hb -and $hb.Value -ceq $p.Value){$true}else{$treeMap.ContainsKey($p.Name) -and $treeMap[$p.Name].sha -ceq (GitBlob $b)}
  if($hash -cne $p.Value -or -not $bound){throw ('SOURCE_TREE_OR_RAW_DRIFT '+$p.Name)};$count++
 };$counts+=,$count
}
$reg=Get-Content -Raw (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/registration.json')|ConvertFrom-Json
$regMap=@{};foreach($s in $reg.cases){$regMap[$s.id]=$s}
$archives=@();$stages=@();$rawFiles=0;$caseData=@();$unindexed=@()
foreach($a in $listing.artifacts|Sort-Object name){
 if($a.name -notmatch ('^memphis-loop-(raw|compact)-(baseline|mesh|diagnostic|second)-'+$RunId+'$')){throw 'UNREGISTERED_ARTIFACT'}
 $path=Join-Path $base ($a.name+'.zip');if(-not(Test-Path $path)){throw 'PREFETCH_OFFICIAL_FIRST'}
 if(('sha256:'+(Get-FileHash $path).Hash.ToLowerInvariant()) -cne $a.digest){throw 'OFFICIAL_ZIP_DIGEST'}
 $z=[IO.Compression.ZipFile]::OpenRead($path)
 try{
  if(@($z.Entries.FullName|Sort-Object -Unique).Count -ne $z.Entries.Count){throw 'DUPLICATE_ZIP_PATH'}
  $ie=@($z.Entries|Where-Object FullName -match '(^|/)artifact_hashes.json$');$map=@{}
  if($ie.Count -eq 1){
   $prefix=$ie[0].FullName.Substring(0,$ie[0].FullName.Length-'artifact_hashes.json'.Length);$idx=ReadEntry $z $ie[0].FullName
   if($idx.source_commit -cne $Commit){throw 'INDEX_EXECUTION'}
   foreach($rec in $idx.records){if($map.ContainsKey($rec.path)){throw 'DUPLICATE_BOUND_PATH'};$map[$rec.path]=$rec}
  }elseif($ie.Count -eq 0 -and $a.name -ceq ('memphis-loop-raw-second-'+$RunId)){
   # The batch throws before writing its completion index/receipts. Official ZIP
   # digest binds these bytes, but local post-download hashes are NOT remote receipts.
   $roots=@($z.Entries|Where-Object FullName -match '/second/[A-Z_]+/result.json$')
   if(-not $roots.Count){throw 'FAILED_GROUP_STAGE_RESULTS_MISSING'}
   $prefix=$roots[0].FullName -replace '[A-Z_]+/result.json$',''
   foreach($e in $z.Entries|Where-Object Length -gt 0){$unindexed+=@{artifact=$a.name;path=$e.FullName;bytes=$e.Length;local_sha256=(HashEntry $e)}}
  }else{throw 'UNEXPLAINED_INDEX_ABSENCE'}
  if($a.name -like 'memphis-loop-raw-*'){
   $me=$z.GetEntry('v0_2/tests/tools/memphis_control_path_v1/source_manifest.json');if(-not $me -or (HashEntry $me) -cne $manifest){throw 'OFFICIAL_MANIFEST_RAW'}
   if($ie.Count){foreach($rec in $idx.records){$e=$z.GetEntry($prefix+$rec.path);if(-not $e -or $e.Length -ne $rec.bytes -or (HashEntry $e) -cne $rec.raw_sha256){throw ('RAW_HASH '+$rec.path)};$rawFiles++}}
   if($ie.Count){
    $receipts=ReadEntry $z ($prefix+'execution_receipts.json')
    if($receipts.source_commit -cne $Commit -or $receipts.manifest_sha256 -cne $manifest){throw 'RECEIPT_IDENTITY'}
    $stageRecords=$receipts.stages
   }else{$stageRecords=@($roots|ForEach-Object {@{stage=($_.FullName -split '/')[-2]}})}
   foreach($r in $stageRecords){
    $p=$prefix+$r.stage+'/';$s=ReadEntry $z ($p+'result.json');$ready=ReadEntry $z ($p+'ready.json');$native=ReadEntry $z ($p+'job_status.json');$proof=ReadEntry $z ($p+'external_job_identity.json');$start=ReadEntry $z ($p+'job_start.json');$release=ReadEntry $z ($p+'release.json')
    if(-not $regMap.ContainsKey($r.stage) -or $s.stage -cne $r.stage -or $s.status -notin @('PASS','FAIL')){throw 'STAGE_REGISTRATION'}
    if($s.pid -ne $ready.pid -or $start.pid -ne $ready.pid -or $proof.actual_python_pid -ne $ready.pid -or $release.actual_python_pid -ne $ready.pid -or $start.job_name -cne $proof.target_job_name -or -not $proof.in_target_job){throw 'ACTUAL_PYTHON_JOB'}
    if($release.external_proof_raw_sha256 -cne (HashEntry ($z.GetEntry($p+'external_job_identity.json'))) -or $s.environment.job_proof_sha256 -cne $release.external_proof_raw_sha256){throw 'EXTERNAL_RELEASE_HASH'}
    if($proof.cpu_rate -ne 2500 -or $proof.cpu_flags -ne 5 -or $proof.basic_flags -ne 8968 -or $proof.max_active_processes -ne 4 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or $start.wall_ms -ne 480000 -or -not $start.kill_on_close){throw 'RESOURCE_GUARD'}
    if(@($proof.modules_before_workload|Where-Object {$_ -match '(?i)(numpy|openblas|mkl)'}).Count){throw 'NUMERICAL_IMPORT_BEFORE_RELEASE'}
    $exit=if($s.status -ceq 'PASS'){0}else{1}
    if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne $exit -or $native.outcome -cne 'EXITED'){throw 'POST_EXIT_CLEANUP'}
    if(($s.environment|ConvertTo-Json -Depth 8 -Compress) -cne ($s.environment_after|ConvertTo-Json -Depth 8 -Compress) -or $s.environment.source_commit -cne $Commit -or $s.environment.image -notin @('20261004.326.1','20261012.333.1') -or $s.environment.python -cne '3.11.9' -or $s.environment.dependencies.numpy -cne '2.4.6' -or $s.environment.dependencies.pytest -cne '9.1.1' -or $s.environment.dependencies.jsonschema -cne '4.26.0'){throw 'SOURCE_ENVIRONMENT_DRIFT'}
    $errorText=if($s.PSObject.Properties['error']){$s.error}else{$null}
    if($s.status -ceq 'FAIL' -and $errorText -cne 'NEGATIVE_B_NOT_EXCITED'){throw ('UNREVIEWED_FAILURE_STOP '+$errorText)}
    $stages+=@{stage=$r.stage;status=$s.status;error=$errorText;pid=$ready.pid;image=$s.environment.image;cpu_rate=2500;process_mb=1024;job_mb=2048;cleanup_complete=$true;active_after_cleanup=0}
    $fe=$z.GetEntry($p+'loop_summary.json');if($fe){$c=ReadEntry $z $fe.FullName;if($c.source_commit -cne $Commit -or $c.id -cne $r.stage){throw 'CASE_IDENTITY'};$caseData+=$c.id}
   }
  }else{
   foreach($e in $z.Entries|Where-Object {$_.Length -gt 0 -and $_.FullName -cne $ie[0].FullName}){$rel=$e.FullName.Substring($prefix.Length);if(-not $map.ContainsKey($rel) -or $e.Length -ne $map[$rel].bytes -or (HashEntry $e) -cne $map[$rel].raw_sha256){throw ('COMPACT_RAW_BINDING '+$rel)}}
  }
 }finally{$z.Dispose()}
 $archives+=@{name=$a.name;id=$a.id;local_sha256=(Get-FileHash $path).Hash.ToLowerInvariant();official_digest=$a.digest};Write-Host ('PARTIAL_BYTES_VERIFIED '+$a.name)
}
if(@($stages.stage|Sort-Object -Unique).Count -ne $stages.Count){throw 'DUPLICATE_STAGE'}
$missing=@($reg.cases.id|Where-Object {$_ -notin $stages.stage});$failed=@($stages|Where-Object status -eq FAIL)
if(-not $failed.Count -or 'FINAL' -notin $missing){throw 'PARTIAL_FAILURE_EXPECTATION'}
$log=Join-Path $base 'official_raw_logs.zip';if(-not(Test-Path $log)){throw 'PRESERVE_OFFICIAL_LOGS_FIRST'}
$z=[IO.Compression.ZipFile]::OpenRead($log);$logs=[Text.StringBuilder]::new();try{foreach($e in $z.Entries|Where-Object Length -gt 0){$r=[IO.StreamReader]::new($e.Open());try{$null=$logs.AppendLine($r.ReadToEnd())}finally{$r.Dispose()}}}finally{$z.Dispose()}
foreach($s in $stages){
 $marker=if($s.status -ceq 'PASS'){'INTEGRATION_STAGE_END '+$s.stage+' PASS'}else{'NATIVE_OR_TEST_FAILURE '+$s.stage}
 if(-not $logs.ToString().Contains($marker)){throw ('RAW_LOG_STAGE '+$s.stage)}
 if($s.status -ceq 'FAIL'){$stdout=Get-Content -Raw (Join-Path $base ($s.stage+'/stdout.raw'));if(-not $stdout.Contains('EQUIPMENT_STAGE_END '+$s.stage+' FAIL') -or -not $stdout.Contains($s.error)){throw 'FAILED_WORKER_RAW_LOG'}}
}
[IO.File]::WriteAllText((Join-Path $base 'FAILED_GROUP_LOCAL_HASHES.json'),($unindexed|ConvertTo-Json -Depth 8),$utf)
$proof=[ordered]@{schema='MEMPHIS-PARTIAL-OFFICIAL-REVIEW-v1';evidence_integrity='AVAILABLE_OFFICIAL_BYTES_AND_ACTUAL_JOBS_VERIFIED_WITH_EXPLICIT_INDEX_GAP';campaign='INCOMPLETE_FAILED_NEGATIVE_NOT_EXCITED';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';run=$RunId;execution_commit=$Commit;manifest_sha256=$manifest;source_counts=@{new=$counts[0];preserved=$counts[1];protected=$counts[2]};source_method='SHA256 sources plus exact remote Git blob identity; protected hydration entries separately verified in sealed hash-bound source bundle; original checkout CI preserved';hydration_manifest_sha256='6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93';raw_files=$rawFiles;stages=$stages;failed=$failed;missing=$missing;completed_forward_cases=$caseData;archives=$archives;raw_logs_sha256=(Get-FileHash $log).Hash.ToLowerInvariant();failed_group_index='NOT_WRITTEN_AFTER_BATCH_THROW; official ZIP digest checked; local post-download hashes separately saved, NOT remote completion receipts';failed_group_local_hashes_sha256=(Get-FileHash (Join-Path $base 'FAILED_GROUP_LOCAL_HASHES.json')).Hash.ToLowerInvariant();final_batch_cleanup='NOT_EXECUTED_FINAL_SKIPPED';full_campaign_pass=$false;formal=$false;hardware=$false;procurement=$false;phase6=$false;method='Pure PowerShell/ZIP/hash review; no local model'}
[IO.File]::WriteAllText((Join-Path $base 'independent_partial_verification.json'),($proof|ConvertTo-Json -Depth 35),$utf)
[pscustomobject]$proof|Select-Object campaign,raw_files,source_counts,@{n='stages';e={$_.stages.Count}},missing,raw_logs_sha256|ConvertTo-Json -Depth 4
