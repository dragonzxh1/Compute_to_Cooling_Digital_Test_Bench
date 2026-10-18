param([Parameter(Mandatory)][long]$RunId,[Parameter(Mandatory)][string]$Directory,[switch]$AllowPartial)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$dest=[IO.Path]::GetFullPath($Directory);New-Item -ItemType Directory -Path $dest -Force|Out-Null
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$utf8=[Text.UTF8Encoding]::new($false)
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or ($run.status -cne 'completed' -and -not $AllowPartial)){throw 'DOWNLOAD_COMPLETED_RUN_ONLY'}
$raw=gh api ($api+'/actions/runs/'+$RunId+'/artifacts?per_page=100')
if($LASTEXITCODE -ne 0){throw 'ARTIFACT_INDEX_UNAVAILABLE'}
$meta=$raw|ConvertFrom-Json
[IO.File]::WriteAllText((Join-Path $dest 'official_artifact_index.json'),($raw|Out-String),$utf8)
[IO.File]::WriteAllText((Join-Path $dest 'run_metadata.json'),($run|ConvertTo-Json -Depth 40),$utf8)
foreach($a in $meta.artifacts){
 $path=Join-Path $dest ($a.name+'.zip')
 if((Test-Path -LiteralPath $path) -and ((Get-Item $path).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $path).Hash.ToLowerInvariant() -cne $a.digest)){
  $preserved=$path+'.partial-preserved-'+[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  if(-not([IO.Path]::GetFullPath($preserved).StartsWith($dest+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase))){throw 'PARTIAL_TARGET_ESCAPE'}
  Move-Item -LiteralPath $path -Destination $preserved
 }
 if(-not(Test-Path -LiteralPath $path)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $path;if($LASTEXITCODE -ne 0){throw ('DOWNLOAD_RETRY_SAME_RUN '+$a.name)}}
 if((Get-Item $path).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $path).Hash.ToLowerInvariant() -cne $a.digest){throw ('ZIP_HASH '+$a.name)}
 Write-Host ('OFFICIAL_ZIP_VERIFIED '+$a.name)
}
$logs=Join-Path $dest 'raw_logs.zip'
if($run.status -cne 'completed'){Write-Host 'PARTIAL_DOWNLOAD_ONLY_NOT_FINAL_EVIDENCE';return}
if(-not(Test-Path -LiteralPath $logs)){gh api ($api+'/actions/runs/'+$RunId+'/logs') > $logs;if($LASTEXITCODE -ne 0){throw 'LOG_DOWNLOAD_RETRY_SAME_RUN'}}
Get-FileHash -LiteralPath $logs
