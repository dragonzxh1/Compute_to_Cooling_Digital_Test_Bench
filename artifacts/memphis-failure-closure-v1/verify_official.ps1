param([Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$Commit,[Parameter(Mandatory)][string]$Manifest)
# Pure file/ZIP/cryptographic/runtime checks; no local model or Python execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($RunId -notmatch '^\d+$' -or $Commit -notmatch '^[a-f0-9]{40}$' -or $Manifest -notmatch '^[a-f0-9]{64}$'){throw 'EXACT_IDENTITY_REQUIRED'}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$resolved='D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$RunId
New-Item -ItemType Directory -Path $resolved -Force|Out-Null
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$utf8=[Text.UTF8Encoding]::new($false)
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.head_sha -cne $Commit -or $run.conclusion -cne 'success' -or $run.status -cne 'completed' -or $run.run_attempt -ne 1){throw 'COMPLETED_EXACT_RUN_REQUIRED'}
$listing=gh api ($api+'/actions/runs/'+$RunId+'/artifacts?per_page=100')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $listing.total_count -ne 20){throw 'ALL20_ARTIFACTS_REQUIRED'}
[IO.File]::WriteAllText((Join-Path $resolved 'official_artifacts.json'),($listing|ConvertTo-Json -Depth 25),$utf8)
[IO.File]::WriteAllText((Join-Path $resolved 'official_run.json'),($run|ConvertTo-Json -Depth 30),$utf8)
function Read-SmallEntry($z,[string]$name){
 $e=$z.GetEntry($name);if(-not $e -or $e.Length -gt 4000000){throw ('SMALL_ENTRY_MISSING_OR_LARGE '+$name)}
 $reader=[IO.StreamReader]::new($e.Open());try{return $reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
}
function Hash-Entry($e){$s=$e.Open();try{return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}}
$archives=@();$stages=@();$files=0
foreach($a in $listing.artifacts|Sort-Object name){
 $path=Join-Path $resolved ($a.name+'.zip')
 if(-not(Test-Path -LiteralPath $path)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $path;if($LASTEXITCODE -ne 0){throw 'OFFICIAL_DOWNLOAD'}}
 $actual=(Get-FileHash $path).Hash.ToLowerInvariant();if(('sha256:'+$actual) -cne $a.digest){throw 'OFFICIAL_DIGEST'}
 $z=[IO.Compression.ZipFile]::OpenRead($path)
 try{
  $indexes=@($z.Entries|Where-Object FullName -match '(^|/)artifact_hashes.json$');if($indexes.Count -ne 1){throw 'ZIP_INDEX_COVERAGE'}
  $entry=$indexes[0];$prefix=$entry.FullName.Substring(0,$entry.FullName.Length-'artifact_hashes.json'.Length)
  $idx=Read-SmallEntry $z $entry.FullName;if($idx.source_commit -cne $Commit){throw 'INDEX_SOURCE'}
  $bound=@{};foreach($rec in $idx.records){if($bound.ContainsKey($rec.path)){throw 'DUPLICATE_RAW_PATH'};$bound[$rec.path]=$rec}
  if($a.name -like 'memphis-closure-raw-*'){
   $me=$z.GetEntry('v0_2/tests/tools/memphis_failure_closure_v1/source_manifest.json')
   if(-not $me -or (Hash-Entry $me) -cne $Manifest){throw 'OFFICIAL_MANIFEST_BYTES'}
   $ms=Read-SmallEntry $z $me.FullName
   if($ms.candidate_sha256 -cne '70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce'){throw 'OFFICIAL_CANDIDATE_BINDING'}
   foreach($rec in $idx.records){$e=$z.GetEntry($prefix+$rec.path);if(-not $e -or $e.Length -ne $rec.bytes -or (Hash-Entry $e) -cne $rec.raw_sha256){throw ('RAW_ENTRY_DRIFT '+$rec.path)};$files++}
   $receipts=Read-SmallEntry $z ($prefix+'execution_receipts.json')
   if($receipts.source_commit -cne $Commit -or $receipts.manifest_sha256 -cne $Manifest){throw 'RECEIPT_IDENTITY'}
   foreach($r in $receipts.stages){
    $p=$prefix+$r.stage+'/'
    $s=Read-SmallEntry $z ($p+'result.json');$ready=Read-SmallEntry $z ($p+'ready.json');$native=Read-SmallEntry $z ($p+'job_status.json');$proof=Read-SmallEntry $z ($p+'external_job_identity.json');$start=Read-SmallEntry $z ($p+'job_start.json');$release=Read-SmallEntry $z ($p+'release.json')
    if($s.status -cne 'PASS' -or $s.stage -cne $r.stage -or $s.pid -ne $ready.pid -or $start.pid -ne $ready.pid -or $proof.actual_python_pid -ne $ready.pid -or $release.actual_python_pid -ne $ready.pid -or $start.job_name -cne $proof.target_job_name -or -not $proof.in_target_job){throw 'ACTUAL_PYTHON_JOB'}
    if($release.external_proof_raw_sha256 -cne (Hash-Entry ($z.GetEntry($p+'external_job_identity.json'))) -or $s.environment.job_proof_sha256 -cne $release.external_proof_raw_sha256){throw 'EXTERNAL_RELEASE_BINDING'}
    if($proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or $start.wall_ms -ne 480000 -or -not $start.kill_on_close){throw 'RESOURCE_LIMITS'}
    if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED'){throw 'FINAL_POST_EXIT_CLEANUP'}
    if(($s.environment|ConvertTo-Json -Depth 8 -Compress) -cne ($s.environment_after|ConvertTo-Json -Depth 8 -Compress) -or $s.environment.source_commit -cne $Commit -or $s.environment.image -notin @('20261004.326.1','20261012.333.1') -or $s.environment.python -cne '3.11.9' -or $s.environment.dependencies.numpy -cne '2.4.6' -or $s.environment.dependencies.pytest -cne '9.1.1' -or $s.environment.dependencies.jsonschema -cne '4.26.0'){throw 'SOURCE_ENVIRONMENT_DRIFT'}
    $stages+=@{stage=$r.stage;pid=$ready.pid;image=$s.environment.image;cpu_rate=2500;process_mb=1024;job_mb=2048;cleanup_complete=$true;active_after_cleanup=0}
   }
  }else{
   foreach($e in $z.Entries|Where-Object {$_.Length -gt 0 -and $_.FullName -cne $entry.FullName}){
    $rel=$e.FullName.Substring($prefix.Length);if(-not $bound.ContainsKey($rel) -or $e.Length -ne $bound[$rel].bytes -or (Hash-Entry $e) -cne $bound[$rel].raw_sha256){throw ('COMPACT_NOT_RAW_BOUND '+$rel)}
   }
  }
 }finally{$z.Dispose()}
 $archives+=@{name=$a.name;id=$a.id;bytes=$a.size_in_bytes;official_digest=$a.digest;local_sha256=$actual};Write-Host ('ZIP_AND_RAW_VERIFIED '+$a.name)
}
$registrationPath='v0_2/tests/tools/memphis_failure_closure_v1/registration.json'
$remoteReg=gh api ($api+'/contents/'+$registrationPath+'?ref='+$Commit)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'EXACT_COMMIT_REGISTRATION_UNAVAILABLE'}
$regBytes=[Convert]::FromBase64String($remoteReg.content)
$regHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($regBytes)).ToLowerInvariant()
if($regHash -cne $ms.source_raw_sha256.PSObject.Properties[$registrationPath].Value){throw 'REGISTERED_INVENTORY_SOURCE_DRIFT'}
$reg=[Text.Encoding]::UTF8.GetString($regBytes)|ConvertFrom-Json
if($stages.Count -ne $reg.cases.Count -or @($stages.stage|Sort-Object -Unique).Count -ne $stages.Count -or (Compare-Object ($stages.stage|Sort-Object) ($reg.cases.id|Sort-Object))){throw 'ALL_REGISTERED_STAGES'}
$log=Join-Path $resolved 'official_raw_logs.zip';gh api ($api+'/actions/runs/'+$RunId+'/logs') > $log;if($LASTEXITCODE -ne 0){throw 'RAW_LOG_DOWNLOAD'}
$z=[IO.Compression.ZipFile]::OpenRead($log);$all=[Text.StringBuilder]::new()
try{foreach($e in $z.Entries|Where-Object Length -gt 0){$rd=[IO.StreamReader]::new($e.Open());try{$null=$all.AppendLine($rd.ReadToEnd())}finally{$rd.Dispose()}}}finally{$z.Dispose()}
foreach($stage in $reg.cases.id){if(-not $all.ToString().Contains('INTEGRATION_STAGE_END '+$stage+' PASS')){throw ('RAW_LOG_STAGE_MISSING '+$stage)}}
if(-not $all.ToString().Contains('MEMPHIS_GROUP_COMPLETE final')){throw 'FINAL_BATCH_COMPLETION_MISSING'}
$proof=[ordered]@{status='OFFICIAL_ZIP_RAW_AND_RUNTIME_INDEPENDENT_FILE_VERIFICATION_PASS';run=[long]$RunId;source_commit=$Commit;manifest_sha256=$Manifest;raw_files=$files;stages=$stages;archives=$archives;raw_logs_sha256=(Get-FileHash $log).Hash.ToLowerInvariant();method='PowerShell streaming SHA256; no local Python/model';engineering_approval=$false;formal=$false;procurement=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $resolved 'independent_file_verification.json'),($proof|ConvertTo-Json -Depth 20),$utf8)
[PSCustomObject]$proof|Select-Object status,run,raw_files,@{Name='stage_count';Expression={$_.stages.Count}},raw_logs_sha256|ConvertTo-Json
