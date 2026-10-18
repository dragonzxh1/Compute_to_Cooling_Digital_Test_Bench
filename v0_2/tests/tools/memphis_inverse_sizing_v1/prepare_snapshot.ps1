# Pure mechanical namespacing and SHA closure only. No local Python/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path;$utf8=[Text.UTF8Encoding]::new($false)
foreach($path in @((Join-Path $PSScriptRoot 'run_remote.ps1'),(Join-Path $repo '.github/workflows/memphis-inverse-sizing-v1-runner.yml'))){
 $s=[IO.File]::ReadAllText($path).Replace('memphis_failover_optimization_v1','memphis_inverse_sizing_v1').Replace('memphis-failover-optimization-v1','memphis-inverse-sizing-v1').Replace('memphis-failover-','memphis-inverse-')
 $s=$s.Replace("'baseline','control','timing','mesh','failure','recharge','final'","'baseline','tanks-a','tanks-b','precool','inverse','joint','robust','scenarios','recharge','final'")
 [IO.File]::WriteAllText($path,$s,$utf8)
}
$priorPath=Join-Path $repo 'v0_2/tests/tools/memphis_failover_optimization_v1/source_manifest.json'
if((Get-FileHash $priorPath).Hash.ToLowerInvariant() -cne '715d8d9cd7a5d99ddccff2373754ee6f32e3084e48e3deffecf8b91702421bef'){throw 'PARENT_MANIFEST_DRIFT'}
$prior=Get-Content -LiteralPath $priorPath -Raw|ConvertFrom-Json;$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){foreach($b in $map.PSObject.Properties){
 $key=if($b.Name -ceq '.github/workflows/ci.yml'){'v0_2/tests/tools/memphis_inverse_sizing_v1/infra/prior-ci.yml'}else{$b.Name}
 if((Get-FileHash -LiteralPath (Join-Path $repo $key)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$key)};$old[$key]=$b.Value
}}
$old['v0_2/tests/tools/memphis_failover_optimization_v1/source_manifest.json']='715d8d9cd7a5d99ddccff2373754ee6f32e3084e48e3deffecf8b91702421bef'
Copy-Item -LiteralPath (Join-Path $repo 'v0_2/tests/tools/memphis_failover_optimization_v1/baseline_hashes.json') -Destination (Join-Path $PSScriptRoot 'baseline_hashes.json')
$new=[ordered]@{}
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File -Recurse|Where-Object Name -cne 'source_manifest.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-inverse-sizing-v1.yml','.github/workflows/memphis-inverse-sizing-v1-runner.yml')
foreach($path in $paths|Sort-Object){$new[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$new['.github/workflows/ci.yml']=(Get-FileHash (Join-Path $PSScriptRoot 'infra/ci-branch-only.yml')).Hash.ToLowerInvariant()
$manifest=[ordered]@{schema='MEMPHIS-INVERSE-SIZING-SOURCE-v1';parent_execution='a07e5fba7d78f34ab907ce209399068f9c92c760';source_raw_sha256=$new;v1_source_raw_sha256=$old;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';preservation_note='All historical physics/M1/fixtures/contracts unchanged; only new branch genericCI exclusion changes, prior branch CI exact bytes retained ininfra/prior-ci.yml';formal=$false;hardware=$false;production=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 12),$utf8)
Get-FileHash (Join-Path $PSScriptRoot 'source_manifest.json')
