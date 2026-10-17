param([Parameter(Mandatory)][long]$RunId,[Parameter(Mandatory)][string]$Directory,[switch]$RawOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$dest=[IO.Path]::GetFullPath($Directory)
New-Item -ItemType Directory -Path $dest -Force|Out-Null
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.status -cne 'completed'){throw 'ONLY_DOWNLOAD_COMPLETED_RUN'}
$raw=gh api ($api+'/actions/runs/'+$RunId+'/artifacts')
if($LASTEXITCODE -ne 0){throw 'ARTIFACT_INDEX_UNAVAILABLE'}
$meta=$raw|ConvertFrom-Json
[IO.File]::WriteAllText((Join-Path $dest 'official_artifact_index.json'),($raw|Out-String),(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllText((Join-Path $dest 'run_metadata.json'),($run|ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false)))
foreach($a in $meta.artifacts){
    if($RawOnly -and $a.name -notlike 'memphis-rack-raw-*'){continue}
    $path=Join-Path $dest ($a.name+'.zip')
    if(-not(Test-Path -LiteralPath $path)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $path;if($LASTEXITCODE -ne 0){throw ('ARTIFACT_DOWNLOAD '+$a.name)}}
    if((Get-Item $path).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $path).Hash.ToLowerInvariant() -cne $a.digest){throw ('OFFICIAL_ZIP_HASH '+$a.name)}
    Write-Host ('ZIP_VERIFIED '+$a.name)
}
$logs=Join-Path $dest 'raw_logs.zip'
if(-not(Test-Path -LiteralPath $logs)){gh api ($api+'/actions/runs/'+$RunId+'/logs') > $logs;if($LASTEXITCODE -ne 0){throw 'RAW_LOG_DOWNLOAD'}}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z=[IO.Compression.ZipFile]::OpenRead($logs);try{if($z.Entries.Count -lt 1){throw 'EMPTY_RAW_LOG_ZIP'}}finally{$z.Dispose()}
Write-Output ('OFFICIAL_DOWNLOAD_COMPLETED '+$RunId)
