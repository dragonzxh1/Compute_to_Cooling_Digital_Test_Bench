# Mechanical file transformations and hashes only; no model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$utf8=[Text.UTF8Encoding]::new($false)
foreach($path in @((Join-Path $PSScriptRoot 'run_remote.ps1'),(Join-Path $repo '.github/workflows/memphis-equipment-v2-runner.yml'))){
 $s=[IO.File]::ReadAllText($path).Replace('memphis_single_rack_v1','memphis_equipment_validation_v2').Replace('memphis-rack-v1','memphis-equipment-v2').Replace('memphis-rack-','memphis-equipment-')
 $s=$s.Replace("'baseline','component','single','six'","'baseline','units-a','units-b','units-c','group-a','group-b','recharge'")
 [IO.File]::WriteAllText($path,$s,$utf8)
}
$rawroot='D:/Github/c2c-evidence-review'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$history=[ordered]@{}
foreach($binding in @(@('SR_STUCK','memphis-single-rack-v1/run39010789593/memphis-rack-raw-single-39010789593.zip','/SR_STUCK/case/'),@('WET_LOSS_STRATIFIED','memphis-project-v2/run38991705994/memphis-raw-plant-a-38991705994.zip','/WET_LOSS_STRATIFIED/case/'))){
 $z=[IO.Compression.ZipFile]::OpenRead((Join-Path $rawroot $binding[1]));$hash=[ordered]@{}
 try{foreach($e in $z.Entries|Where-Object {$_.FullName.Contains($binding[2]) -and $_.Name -in @('input.json','series.json','physics.json','phases.json')}){
  $stream=$e.Open();try{$hash[$e.Name]=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
 }}finally{$z.Dispose()}
 if($hash.Count -ne 4){throw 'HISTORICAL_RAW_INCOMPLETE'};$history[$binding[0]]=$hash
}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'historical_hashes.json'),($history|ConvertTo-Json -Depth 6),$utf8)
$prior=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_single_rack_v1/source_manifest.json') -Raw|ConvertFrom-Json
$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)) {foreach($b in $map.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$b.Name)};$old[$b.Name]=$b.Value
}}
$new=[ordered]@{}
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File -Recurse|Where-Object Name -cne 'source_manifest.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-equipment-v2.yml','.github/workflows/memphis-equipment-v2-runner.yml')
foreach($path in $paths|Sort-Object){$new[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$manifest=[ordered]@{schema='MEMPHIS-EQUIPMENT-V2-SOURCE';parent='77db1f4ef568722357639a0dfd9367bcafe5a1cd';source_raw_sha256=$new;v1_source_raw_sha256=$old;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 8),$utf8)
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'source_manifest.json')
