# File identity/extraction only. No model execution or network request.
$ErrorActionPreference='Stop'
$evidenceRoot='D:/Github/c2c-evidence-review/memphis-r12-dynamic-hydraulic-v1/run39492934891'
$reviewed='D:/Github/Compute_to_Cooling_Digital_Test_Bench/artifacts/memphis-r12-dynamic-hydraulic-v1/reviewed-delivery'
$art=(Get-Content -LiteralPath "$evidenceRoot/github_artifacts.json" -Raw|ConvertFrom-Json).artifacts[0]
if($art.workflow_run.id -ne 39492934891 -or $art.workflow_run.head_sha -ne 'cfc7eb2663f8ed28ea8bfcc3b88182c54983d941'){throw 'R12_ARTIFACT_IDENTITY'}
$zipPath=Join-Path $evidenceRoot ($art.name+'.zip')
$zipHash=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if('sha256:'+$zipHash -ne $art.digest){throw 'R12_OFFICIAL_ZIP_HASH'}
$bindings=[ordered]@{run='39492934891';source_commit=$art.workflow_run.head_sha;official_zip_sha256=$zipHash;files=[ordered]@{}}
$zip=[IO.Compression.ZipFile]::OpenRead($zipPath)
try{foreach($caseId in 'T2_COLD_STANDBY','T2_WARM_STANDBY','NEG_DUTY_PUMP_LOSS'){
 foreach($name in 'trace.ndjson','case_result.json'){
  $entries=@($zip.Entries|Where-Object {$_.FullName.EndsWith("/delivery/$caseId/$name")})
  if($entries.Count -ne 1){throw "AMBIGUOUS_ENTRY $caseId/$name"}
  $stream=$entries[0].Open();$buffer=[IO.MemoryStream]::new();$stream.CopyTo($buffer);$stream.Dispose()
  $rawHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($buffer.ToArray())).ToLowerInvariant();$buffer.Dispose()
  if((Get-FileHash -LiteralPath "$reviewed/$caseId/$name").Hash.ToLowerInvariant() -ne $rawHash){throw "REVIEWED_BYTES_NOT_OFFICIAL $caseId/$name"}
  $bindings.files["$caseId/$name"]=@{entry=$entries[0].FullName;sha256=$rawHash}
 }
}}finally{$zip.Dispose()}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'data/cdu_zip_bindings.json'),($bindings|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
node (Join-Path $PSScriptRoot 'prepare_switching_data.mjs')
if($LASTEXITCODE -ne 0){throw 'SWITCHING_DATA_PROJECTION_FAILED'}
