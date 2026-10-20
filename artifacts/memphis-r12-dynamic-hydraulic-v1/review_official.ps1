param([Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$Commit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
if($RunId -notmatch '^\d+$' -or $Commit -notmatch '^[a-f0-9]{40}$'){throw 'IDENTITY_FORMAT'}
$base='D:/Github/c2c-evidence-review/memphis-r12-dynamic-hydraulic-v1/run'+$RunId
New-Item -ItemType Directory -Path $base -Force|Out-Null
function J($path,$value){[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 90),[Text.UTF8Encoding]::new($false))}
function ReadJ($path){Get-Content -LiteralPath $path -Raw|ConvertFrom-Json -Depth 90}
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.head_sha -cne $Commit -or $run.status -cne 'completed' -or $run.run_attempt -ne 1){throw 'NOT_TERMINAL_SINGLE_FRESH_RUN'}
$arts=gh api ($api+'/actions/runs/'+$RunId+'/artifacts?per_page=100')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $arts.total_count -ne 1){throw 'ARTIFACT_INVENTORY'}
$a=$arts.artifacts[0]
if($a.name -cne ('memphis-r12-short-dynamic-'+$RunId) -or $a.expired){throw 'ARTIFACT_IDENTITY'}
J (Join-Path $base 'github_run.json') $run;J (Join-Path $base 'github_artifacts.json') $arts
$zip=Join-Path $base ($a.name+'.zip')
if(-not(Test-Path -LiteralPath $zip)){
 $temp=$zip+'.partial-'+[guid]::NewGuid().ToString('N')
 gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $temp
 if($LASTEXITCODE -ne 0){throw ('DOWNLOAD_FAILED_BYTES_PRESERVED '+$temp)}
 if(('sha256:'+(Get-FileHash -LiteralPath $temp).Hash.ToLowerInvariant()) -cne $a.digest){throw 'OFFICIAL_ZIP_DIGEST'}
 Move-Item -LiteralPath $temp -Destination $zip
}
if(('sha256:'+(Get-FileHash -LiteralPath $zip).Hash.ToLowerInvariant()) -cne $a.digest){throw 'CACHED_ZIP_DIGEST'}
$extract=Join-Path $base 'official'
if(-not(Test-Path -LiteralPath $extract)){
 $z=[IO.Compression.ZipFile]::OpenRead($zip)
 try{foreach($entry in $z.Entries){$dest=[IO.Path]::GetFullPath((Join-Path $extract $entry.FullName));if(-not $dest.StartsWith(([IO.Path]::GetFullPath($extract)+[IO.Path]::DirectorySeparatorChar))){throw 'ZIP_PATH_ESCAPE'}}}finally{$z.Dispose()}
 [IO.Compression.ZipFile]::ExtractToDirectory($zip,$extract)
}
$logs=Join-Path $base 'official_logs.zip'
if(-not(Test-Path -LiteralPath $logs)){gh api ($api+'/actions/runs/'+$RunId+'/logs') > $logs;if($LASTEXITCODE -ne 0){throw 'LOG_DOWNLOAD'}}
$evidence=Join-Path $extract ('artifacts/memphis-r12-dynamic-hydraulic-v1/'+$RunId+'-1')
$manifest=Join-Path $extract 'v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1/source_manifest.json'
$manifestHash=(Get-FileHash -LiteralPath $manifest).Hash.ToLowerInvariant()
$publication=ReadJ (Join-Path $PSScriptRoot ('publication_'+$Commit.Substring(0,7)+'.json'))
if($publication.manifest_sha256 -cne $manifestHash){throw 'SOURCE_MANIFEST_BINDING'}
$source=Join-Path $PSScriptRoot ('source-'+$Commit.Substring(0,7))
if((Get-FileHash -LiteralPath ($source+'.zip')).Hash.ToLowerInvariant() -cne $publication.source_zip_sha256){throw 'SOURCE_SNAPSHOT_DRIFT'}
$stages=@()
foreach($stage in @('baseline','suite')){
 $d=Join-Path $evidence $stage;if(-not(Test-Path -LiteralPath $d)){continue}
 $index=ReadJ (Join-Path $d 'artifact_hashes.json')
 if($index.source_commit -cne $Commit -or $index.manifest_sha256 -cne $manifestHash){throw 'INDEX_SOURCE'}
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
 foreach($row in $index.records){
  if(-not $seen.Add($row.path)){throw 'DUPLICATE_HASH_RECORD'}
  $p=[IO.Path]::GetFullPath((Join-Path $d $row.path))
  if(-not $p.StartsWith(([IO.Path]::GetFullPath($d)+[IO.Path]::DirectorySeparatorChar))){throw 'INDEX_ESCAPE'}
  if((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant() -cne $row.sha256){throw ('RAW_HASH '+$row.path)}
 }
 if(@(Get-ChildItem -LiteralPath $d -Recurse -File).Count -ne $seen.Count+1){throw 'UNINDEXED_RAW'}
 $ready=ReadJ (Join-Path $d 'ready.json');$proof=ReadJ (Join-Path $d 'external_job_identity.json');$native=ReadJ (Join-Path $d 'job_status.json')
 if($proof.actual_python_pid -ne $ready.pid -or -not $proof.in_target_job -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 256 -or $proof.job_mb -ne 512){throw 'ACTUAL_JOB_IDENTITY'}
 if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0){throw 'CLEANUP_OR_ASSIGNMENT'}
 $result=if(Test-Path -LiteralPath (Join-Path $d 'result.json')){ReadJ (Join-Path $d 'result.json')}else{$null}
 $env=if(Test-Path -LiteralPath (Join-Path $d 'environment_before.json')){ReadJ (Join-Path $d 'environment_before.json')}else{$null}
 if($null -ne $env){
  if($env.source_commit -cne $Commit -or $env.pid -ne $ready.pid -or $env.python -cne '3.11.9' -or $env.numpy -cne '2.4.6' -or $env.long_run){throw 'ENV_IDENTITY'}
  if(Test-Path -LiteralPath (Join-Path $d 'environment_after.json')){if(($env|ConvertTo-Json -Compress) -cne ((ReadJ (Join-Path $d 'environment_after.json'))|ConvertTo-Json -Compress)){throw 'ENV_DRIFT'}}
 }
 $stages+=@{stage=$stage;actual_python_pid=$ready.pid;job=$native;environment=$env;result=$result;raw_files_verified=$seen.Count}
}
$review=[ordered]@{schema='R12-SHORT-DYNAMIC-OFFICIAL-BYTE-REVIEW-1';run=$RunId;source_commit=$Commit;
 official_zip_sha256=(Get-FileHash -LiteralPath $zip).Hash.ToLowerInvariant();official_digest_verified=$true;
 raw_logs_sha256=(Get-FileHash -LiteralPath $logs).Hash.ToLowerInvariant();source_manifest_sha256=$manifestHash;
 source_zip_sha256=$publication.source_zip_sha256;github_conclusion=$run.conclusion;stages=$stages;
 scope='IDENTITY_HASH_RESOURCE_CLEANUP_REVIEW_NOT_ENGINEERING_APPROVAL';engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED'}
J (Join-Path $base 'independent_byte_review.json') $review
$review|ConvertTo-Json -Depth 10
