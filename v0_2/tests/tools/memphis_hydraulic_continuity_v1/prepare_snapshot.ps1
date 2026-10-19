# Source closure, no local Python/native/model/boolean execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$priorPath=Join-Path $repo 'v0_2/tests/tools/memphis_failure_closure_v1/source_manifest.json'
$priorHash=(Get-FileHash -LiteralPath $priorPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($priorHash -cne 'ba263422c76d02710e410c2071cc87b84d6faee82fd0d65e94cc4148adee7ce2'){throw 'PARENT_SOURCE_MANIFEST_DRIFT'}
$prior=Get-Content -LiteralPath $priorPath -Raw|ConvertFrom-Json
$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){
 foreach($b in $map.PSObject.Properties){
  $key=if($b.Name -ceq '.github/workflows/ci.yml'){'v0_2/tests/tools/memphis_failure_closure_v1/infra/ci-branch-only.yml'}else{$b.Name}
  if((Get-FileHash -LiteralPath (Join-Path $repo $key) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$key)}
  $old[$key]=$b.Value
 }
}
$old['v0_2/tests/tools/memphis_failure_closure_v1/source_manifest.json']=$priorHash
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File -Recurse | Where-Object Name -cne 'source_manifest.json' | ForEach-Object{[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-hydraulic-continuity-v1.yml','.github/workflows/memphis-hydraulic-continuity-v1-runner.yml')
$new=[ordered]@{}
foreach($p in $paths|Sort-Object){$new[$p]=(Get-FileHash -LiteralPath (Join-Path $repo $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
$new['.github/workflows/ci.yml']=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'infra/ci-branch-only.yml') -Algorithm SHA256).Hash.ToLowerInvariant()
$freeze=Get-Content -LiteralPath (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json') -Raw|ConvertFrom-Json
foreach($b in $freeze.source_raw_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw ('FROZEN_SOURCE_DRIFT '+$b.Name)}}
$reg=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
if(@($reg.cases.id|Sort-Object -Unique).Count -ne $reg.cases.Count){throw 'DUPLICATE_STAGE'}
$manifest=[ordered]@{schema='MEMPHIS-HYDRAULIC-CONTINUITY-SOURCE-v1';build=$reg.build;parent_execution='be3e9ea395ebd461683190d6cf3a0d5125973e13';parent_delivery='e8fd76847f5daa57ae266b772375dca404af3b12';source_raw_sha256=$new;v1_source_raw_sha256=$old;protected_source_count=@($freeze.source_raw_sha256.PSObject.Properties).Count;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';scope='Bounded new DEVELOPMENT; no old evidence/core/math/expectation modifications';formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{source_manifest_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'source_manifest.json')).Hash.ToLowerInvariant();protected=$manifest.protected_source_count;stages=$reg.cases.Count}|ConvertTo-Json
