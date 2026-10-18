# Archive-only evidence retrieval. No local Python/native/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$utf8=[Text.UTF8Encoding]::new($false)
foreach($id in @('39134808524','39134995538','39135290316')){
 $dest='D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run'+$id
 New-Item -ItemType Directory -Path $dest -Force|Out-Null
 $run=gh api ($api+'/actions/runs/'+$id)|ConvertFrom-Json
 if($LASTEXITCODE -ne 0 -or $run.status -cne 'completed' -or $run.conclusion -notin @('cancelled','failure')){throw 'EXACT_TERMINAL_PREFLIGHT_REQUIRED'}
 $listing=gh api ($api+'/actions/runs/'+$id+'/artifacts?per_page=100')|ConvertFrom-Json
 if($LASTEXITCODE -ne 0){throw 'LISTING_FAILED'}
 $records=@()
 foreach($a in $listing.artifacts){
  $path=Join-Path $dest ($a.name+'.zip')
  if(-not(Test-Path -LiteralPath $path)){
   gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $path
   if($LASTEXITCODE -ne 0){throw 'DOWNLOAD_FAILED'}
  }
  $sha=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
  if(('sha256:'+$sha) -cne $a.digest){throw ('ZIP_DIGEST_MISMATCH '+$a.name)}
  $records+=@{artifact=$a.name;id=$a.id;sha256=$sha;bytes=$a.size_in_bytes}
 }
 $log=Join-Path $dest 'official_raw_logs.zip'
 if(-not(Test-Path -LiteralPath $log)){gh api ($api+'/actions/runs/'+$id+'/logs') > $log;if($LASTEXITCODE -ne 0){throw 'LOG_DOWNLOAD_FAILED'}}
 $record=[ordered]@{run=$id;source_commit=$run.head_sha;conclusion=$run.conclusion;scope='PRESERVED_CANCELLED_OR_FAILED_NOT_COMPLETE_VALIDATION';archives=$records;raw_logs_sha256=(Get-FileHash $log).Hash.ToLowerInvariant();no_prior_pass_borrowed=$true}
 [IO.File]::WriteAllText((Join-Path $dest 'preserved_evidence.json'),($record|ConvertTo-Json -Depth 12),$utf8)
 Write-Host ('PRESERVED '+$id+' '+$records.Count+' official ZIPs')
}
