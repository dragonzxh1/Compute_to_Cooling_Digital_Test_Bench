# Pure file closure/hash preparation only. Never executes the model locally.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$utf8=[Text.UTF8Encoding]::new($false)
$baseline='D:/Github/c2c-evidence-review/memphis-equipment-v2/run39088951176/full/memphis-equipment-raw-group-a-39088951176/artifacts/m1-autonomous-development/memphis-equipment-v2-39088951176-1/group-a/G_WET_LOSS/case'
$hashes=[ordered]@{}
foreach($name in @('physics.json','series.json','source_phases.json','phases.json')){$hashes[$name]=(Get-FileHash -LiteralPath (Join-Path $baseline $name)).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'baseline_hashes.json'),($hashes|ConvertTo-Json),$utf8)
# Mechanical namespacing of copied runner wrappers; original V2 unchanged.
foreach($path in @((Join-Path $PSScriptRoot 'run_remote.ps1'),(Join-Path $repo '.github/workflows/memphis-failover-optimization-v1-runner.yml'))){
 $s=[IO.File]::ReadAllText($path).Replace('memphis_equipment_validation_v2','memphis_failover_optimization_v1').Replace('memphis-equipment-v2','memphis-failover-optimization-v1').Replace('memphis-equipment-','memphis-failover-')
 $s=$s.Replace("'baseline','units-a','units-b','units-c','group-a','group-b','recharge'","'baseline','control','timing','mesh','failure','recharge','final'")
 [IO.File]::WriteAllText($path,$s,$utf8)
}
$oldPath=Join-Path $repo 'v0_2/tests/tools/memphis_equipment_validation_v2/source_manifest.json'
if((Get-FileHash -LiteralPath $oldPath).Hash.ToLowerInvariant() -cne '5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16'){throw 'V2_MANIFEST_DRIFT'}
$prior=Get-Content -LiteralPath $oldPath -Raw|ConvertFrom-Json
$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){foreach($b in $map.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$b.Name)};$old[$b.Name]=$b.Value
}}
$old['v0_2/tests/tools/memphis_equipment_validation_v2/source_manifest.json']='5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16'
$new=[ordered]@{}
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File -Recurse|Where-Object Name -cne 'source_manifest.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-failover-optimization-v1.yml','.github/workflows/memphis-failover-optimization-v1-runner.yml')
foreach($path in $paths|Sort-Object){$new[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$manifest=[ordered]@{schema='MEMPHIS-FAILOVER-OPTIMIZATION-v1';parent_execution='6031e0ef7d32bec0109f328f85ebd5dfef8fe048';source_raw_sha256=$new;v1_source_raw_sha256=$old;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 8),$utf8)
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'source_manifest.json')
