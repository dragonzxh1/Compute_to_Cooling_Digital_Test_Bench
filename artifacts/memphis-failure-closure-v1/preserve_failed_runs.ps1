$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$utf8=[Text.UTF8Encoding]::new($false)
foreach($id in @('39146509431','39146681509','39180072218')){
 $dir='D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$id;New-Item -ItemType Directory -Path $dir -Force|Out-Null
 $run=gh api ($api+'/actions/runs/'+$id)|ConvertFrom-Json
 if($LASTEXITCODE -ne 0 -or $run.status -cne 'completed' -or $run.conclusion -notin @('failure','cancelled')){throw 'EXACT_FAILED_OR_CANCELLED_RUN_REQUIRED'}
 $art=gh api ($api+'/actions/runs/'+$id+'/artifacts?per_page=100')|ConvertFrom-Json;if($LASTEXITCODE -ne 0){throw 'LIST_FAILED_ARTIFACTS'}
 $log=Join-Path $dir 'official_failed_logs.zip';$logHash=$null;$logState='PRESERVED'
 if($id -ceq '39180072218'){
  $jobs=gh api ($api+'/actions/runs/'+$id+'/jobs')|ConvertFrom-Json
  if($LASTEXITCODE -ne 0 -or $jobs.total_count -ne 0 -or $art.total_count -ne 0){throw 'QUEUED_CANCEL_IDENTITY_CHANGED'}
  $logState='NOT_CREATED_NO_JOBS_NO_NUMERICAL_EXECUTION'
 }else{
  if(-not(Test-Path $log)){gh api ($api+'/actions/runs/'+$id+'/logs') > $log;if($LASTEXITCODE -ne 0){throw 'FAILED_LOGS_DOWNLOAD'}}
  $logHash=(Get-FileHash $log).Hash.ToLowerInvariant()
 }
 $local=@()
 foreach($a in $art.artifacts|Where-Object name -like '*raw-robust-*'){
  $path=Join-Path $dir 'failed-robust.zip';if(-not(Test-Path $path)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $path;if($LASTEXITCODE -ne 0){throw 'FAILED_RAW_DOWNLOAD'}}
  $h=(Get-FileHash $path).Hash.ToLowerInvariant();if(('sha256:'+$h) -cne $a.digest){throw 'FAILED_RAW_DIGEST'}
  $local+=@{name=$a.name;id=$a.id;bytes=$a.size_in_bytes;raw_sha256=$h;state='FAILED_NOT_PASS'}
 }
 $record=[ordered]@{run=$run.id;source_commit=$run.head_sha;conclusion=$run.conclusion;official_artifacts=$art;preserved_raw=$local;log_sha256=$logHash;log_state=$logState;all_official_artifacts_remain_on_GitHub=$true;no_pass_reuse=$true;engineering='MEMPHIS_ENGINEERING_NOT_APPROVED'}
 [IO.File]::WriteAllText((Join-Path $dir 'preserved_failed_run.json'),($record|ConvertTo-Json -Depth 30),$utf8)
 [PSCustomObject]$record|Select-Object run,source_commit,conclusion,log_sha256|ConvertTo-Json
}
