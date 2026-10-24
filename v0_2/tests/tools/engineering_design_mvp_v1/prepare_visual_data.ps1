# Evidence extraction only. No simulation, model import or native workload.
$ErrorActionPreference='Stop'
$evidenceRoot='D:/Github/c2c-evidence-review/memphis-single-rack-v1/run39010789593'
$artifactName='memphis-rack-raw-single-39010789593'
$indexPath=Join-Path $evidenceRoot 'official_artifact_index.json'
$index=Get-Content -LiteralPath $indexPath -Raw|ConvertFrom-Json
$artifact=@($index.artifacts|Where-Object name -eq $artifactName)
if($artifact.Count -ne 1 -or $artifact[0].workflow_run.head_sha -ne 'fe94f1bd06fbdf4b73955057d12d50cb71fac189'){throw 'Single-rack artifact identity mismatch'}
$zipPath=Join-Path $evidenceRoot "$artifactName.zip"
$zipHash=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if('sha256:'+$zipHash -ne $artifact[0].digest){throw 'Official ZIP hash mismatch'}
$data=[ordered]@{schema='C2C-SINGLE-CATALOG-1';mode='HISTORICAL_NOT_CURRENT_DESIGN';run='39010789593';source=$artifact[0].workflow_run.head_sha;zip_sha256=$zipHash;index_sha256=(Get-FileHash -LiteralPath $indexPath).Hash.ToLowerInvariant();cases=[ordered]@{}}
$caseLabels=[ordered]@{SR_NORMAL='正常运行';SR_STEP='负载阶跃';SR_STUCK='静默卡泵 + 阶跃';SR_MISSING='测量丢失 + 阶跃';SR_WARM='一次边界升温 + 阶跃'}
$zip=[IO.Compression.ZipFile]::OpenRead($zipPath)
try{foreach($caseId in $caseLabels.Keys){
 $case=[ordered]@{schema='C2C-SINGLE-REPLAY-1';mode=$data.mode;run=$data.run;source=$data.source;zip_sha256=$zipHash;case_id=$caseId;label=$caseLabels[$caseId];scope="旧单柜 $caseId 工程研究。未标定约简回路，不是当前00/01设计结果或现场测量。";bindings=[ordered]@{}}
 foreach($name in 'input','series','measurements','phases'){
 $entries=@($zip.Entries|Where-Object {$_.FullName.EndsWith("/single/$caseId/case/$name.json")})
 if($entries.Count -ne 1){throw "Ambiguous raw entry: $name"}
 $stream=$entries[0].Open();$mem=[IO.MemoryStream]::new();$stream.CopyTo($mem);$stream.Dispose();$bytes=$mem.ToArray();$mem.Dispose()
 $rawHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
 $case.bindings[$name]=@{sha256=$rawHash;entry=$entries[0].FullName}
 $case[$name]=[Text.Encoding]::UTF8.GetString($bytes)|ConvertFrom-Json
 }
 if($case.input.case_id -ne $caseId -or $case.series.Count -ne 1201 -or $case.phases.Count -ne 600){throw 'Raw inventory mismatch'}
 foreach($row in $case.measurements){if($row.sample_ns -gt $row.available_ns){throw 'Future observation'}}
 foreach($row in $case.phases){if($row.PLC.issue_ns -gt $row.time_ns -or $row.PRE.measurement.release_ns -gt $row.time_ns){throw 'Future phase input'}}
 $data.cases[$caseId]=$case
}}finally{$zip.Dispose()}
$output=Join-Path $PSScriptRoot 'data/single_history.json'
$json=ConvertTo-Json -InputObject $data -Depth 40 -Compress
[IO.File]::WriteAllText($output,$json,[Text.UTF8Encoding]::new($false))
[ordered]@{scope='FILE_ONLY_EXTRACTION_NOT_NEW_SIMULATION';output=$output;zip_sha256=$zipHash;cases=@($data.cases.Keys)}|ConvertTo-Json
