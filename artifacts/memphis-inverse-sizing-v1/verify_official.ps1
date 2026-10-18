param([string]$EvidenceRoot='D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run39136524640')
# Pure-file ZIP/SHA/runtime verification only. No Python/native/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$runId='39136524640';$commit='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb'
$resolved=[IO.Path]::GetFullPath($EvidenceRoot)
if(-not $resolved.StartsWith('D:\Github\c2c-evidence-review\memphis-inverse-sizing-v1\run39136524640',[StringComparison]::OrdinalIgnoreCase)){throw 'EXACT_EVIDENCE_ROOT_REQUIRED'}
New-Item -ItemType Directory -Path $resolved -Force|Out-Null
$run=gh api ($api+'/actions/runs/'+$runId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.head_sha -cne $commit -or $run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.run_attempt -ne 1){throw 'COMPLETED_EXACT_RUN_REQUIRED'}
$listing=gh api ($api+'/actions/runs/'+$runId+'/artifacts?per_page=100')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $listing.total_count -ne 20){throw 'ARTIFACT_COVERAGE'}
$utf8=[Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $resolved 'official_artifacts.json'),($listing|ConvertTo-Json -Depth 20),$utf8)
[IO.File]::WriteAllText((Join-Path $resolved 'official_run.json'),($run|ConvertTo-Json -Depth 30),$utf8)
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Read-SmallEntry($zip,[string]$name){
 $e=$zip.GetEntry($name);if(-not $e -or $e.Length -gt 2000000){throw ('SMALL_ENTRY_MISSING_OR_LARGE '+$name)}
 $stream=$e.Open();$reader=[IO.StreamReader]::new($stream)
 try{return $reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
}
$archives=@();$stages=@();$files=0
foreach($artifact in $listing.artifacts|Sort-Object name){
 $path=Join-Path $resolved ($artifact.name+'.zip')
 if(-not(Test-Path -LiteralPath $path)){gh api ($api+'/actions/artifacts/'+$artifact.id+'/zip') > $path;if($LASTEXITCODE -ne 0){throw 'OFFICIAL_DOWNLOAD'}}
 $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if(('sha256:'+$actual) -cne $artifact.digest){throw ('OFFICIAL_ZIP_DIGEST '+$artifact.name)}
 $z=[IO.Compression.ZipFile]::OpenRead($path)
 try{
  $indexes=@($z.Entries|Where-Object FullName -match '(^|/)artifact_hashes.json$')
  if($indexes.Count -ne 1){throw 'ZIP_INDEX_COVERAGE'}
  $entry=$indexes[0];$prefix=$entry.FullName.Substring(0,$entry.FullName.Length-'artifact_hashes.json'.Length)
  $index=Read-SmallEntry $z $entry.FullName
  if($index.source_commit -cne $commit){throw 'INDEX_SOURCE_DRIFT'}
  if($artifact.name -like 'memphis-inverse-raw-*'){
   foreach($item in $index.records){
    $e=$z.GetEntry($prefix+$item.path)
    if(-not $e -or $e.Length -ne $item.bytes){throw ('RAW_ENTRY_MISSING '+$item.path)}
    $stream=$e.Open();try{$h=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
    if($h -cne $item.raw_sha256){throw ('RAW_ENTRY_SHA256 '+$item.path)};$files++
   }
   $receipts=Read-SmallEntry $z ($prefix+'execution_receipts.json')
   if($receipts.source_commit -cne $commit -or $receipts.manifest_sha256 -cne '33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'){throw 'RECEIPT_SOURCE'}
   foreach($receipt in $receipts.stages){
    $p=$prefix+$receipt.stage+'/'
    $result=Read-SmallEntry $z ($p+'result.json');$ready=Read-SmallEntry $z ($p+'ready.json');$native=Read-SmallEntry $z ($p+'job_status.json');$proof=Read-SmallEntry $z ($p+'external_job_identity.json')
    $start=Read-SmallEntry $z ($p+'job_start.json')
    if($start.pid -ne $ready.pid -or $proof.target_job_name -cne $start.job_name -or $start.wall_ms -ne 480000 -or -not $start.kill_on_close){throw 'START_JOB_IDENTITY_OR_BUDGET'}
    if($result.status -cne 'PASS' -or $result.stage -cne $receipt.stage -or $result.pid -ne $ready.pid -or $proof.actual_python_pid -ne $ready.pid -or -not $proof.in_target_job -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048){throw 'ACTUAL_PYTHON_JOB_OR_STAGE'}
    if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED'){throw 'NATIVE_POST_EXIT_CLEANUP'}
    if(($result.environment|ConvertTo-Json -Depth 8 -Compress) -cne ($result.environment_after|ConvertTo-Json -Depth 8 -Compress) -or $result.environment.source_commit -cne $commit -or $result.environment.image -notin @('20261004.326.1','20261012.333.1') -or $result.environment.python -cne '3.11.9'){throw 'ENVIRONMENT_DRIFT'}
    if($result.environment.dependencies.numpy -cne '2.4.6' -or $result.environment.dependencies.pytest -cne '9.1.1' -or $result.environment.dependencies.jsonschema -cne '4.26.0'){throw 'DEPENDENCY_DRIFT'}
    $stages+=@{stage=$receipt.stage;pid=$ready.pid;cpu_rate=$proof.cpu_rate;process_mb=$proof.process_mb;job_mb=$proof.job_mb;image=$result.environment.image;cleanup_complete=$true;active_after_cleanup=0}
   }
  }else{
   # Compact is not raw: independently bind every contained selected file to raw index.
   foreach($e in $z.Entries|Where-Object {$_.Length -gt 0 -and $_.FullName -cne $entry.FullName}){
    $relative=$e.FullName.Substring($prefix.Length);$item=@($index.records|Where-Object path -ceq $relative)
    if($item.Count -ne 1){throw ('COMPACT_UNBOUND '+$relative)}
    $stream=$e.Open();try{$h=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
    if($h -cne $item[0].raw_sha256 -or $e.Length -ne $item[0].bytes){throw 'COMPACT_RAW_HASH_DRIFT'}
   }
  }
 }finally{$z.Dispose()}
 $archives+=@{name=$artifact.name;id=$artifact.id;bytes=$artifact.size_in_bytes;official_digest=$artifact.digest;local_sha256=$actual}
 Write-Host ('ZIP_AND_RAW_VERIFIED '+$artifact.name)
}
$expected=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../../v0_2/tests/tools/memphis_inverse_sizing_v1/registration.json') -Raw|ConvertFrom-Json
if($stages.Count -ne $expected.cases.Count -or (@($stages.stage|Sort-Object -Unique).Count) -ne $stages.Count -or (Compare-Object ($stages.stage|Sort-Object) ($expected.cases.id|Sort-Object))){throw 'FINAL_STAGE_COVERAGE'}
$taskLog=Join-Path $resolved 'official_raw_logs.zip'
gh api ($api+'/actions/runs/'+$runId+'/logs') > $taskLog
if($LASTEXITCODE -ne 0){throw 'RAW_LOG_DOWNLOAD'}
$logZip=[IO.Compression.ZipFile]::OpenRead($taskLog);$logText=[Text.StringBuilder]::new()
try{foreach($entry in $logZip.Entries|Where-Object Length -gt 0){$reader=[IO.StreamReader]::new($entry.Open());try{$null=$logText.AppendLine($reader.ReadToEnd())}finally{$reader.Dispose()}}}finally{$logZip.Dispose()}
foreach($stage in $expected.cases.id){if(-not $logText.ToString().Contains('INTEGRATION_STAGE_END '+$stage+' PASS')){throw ('RAW_STAGE_END_MISSING '+$stage)}}
$proof=[ordered]@{status='OFFICIAL_ZIP_RAW_AND_RUNTIME_INDEPENDENT_FILE_VERIFICATION_PASS';run=[long]$runId;source_commit=$commit;manifest_sha256='33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f';raw_files=$files;stages=$stages;archives=$archives;raw_logs_sha256=(Get-FileHash -LiteralPath $taskLog).Hash.ToLowerInvariant();verification='PowerShell pure-file streaming SHA256; no local Python or model';engineering_approval=$false;formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $resolved 'independent_file_verification.json'),($proof|ConvertTo-Json -Depth 15),$utf8)
[PSCustomObject]$proof|Select-Object status,run,raw_files,@{Name='stage_count';Expression={$_.stages.Count}},raw_logs_sha256|ConvertTo-Json
