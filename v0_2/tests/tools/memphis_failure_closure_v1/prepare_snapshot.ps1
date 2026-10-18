# Pure mechanical namespacing and SHA closure only. No local Python/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path;$utf8=[Text.UTF8Encoding]::new($false)
$priorPath=Join-Path $repo 'v0_2/tests/tools/memphis_inverse_sizing_v1/source_manifest.json'
if((Get-FileHash $priorPath).Hash.ToLowerInvariant() -cne '33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'){throw 'PARENT_MANIFEST_DRIFT'}
$prior=Get-Content -LiteralPath $priorPath -Raw|ConvertFrom-Json;$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){foreach($b in $map.PSObject.Properties){
 $key=if($b.Name -ceq '.github/workflows/ci.yml'){'v0_2/tests/tools/memphis_failure_closure_v1/infra/prior-ci.yml'}else{$b.Name}
 if((Get-FileHash -LiteralPath (Join-Path $repo $key)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$key)};$old[$key]=$b.Value
}}
$old['v0_2/tests/tools/memphis_inverse_sizing_v1/source_manifest.json']='33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'
$new=[ordered]@{}
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File -Recurse|Where-Object Name -cne 'source_manifest.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-failure-closure-v1.yml','.github/workflows/memphis-failure-closure-v1-runner.yml')
foreach($path in $paths|Sort-Object){$new[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$new['.github/workflows/ci.yml']=(Get-FileHash (Join-Path $PSScriptRoot 'infra/ci-branch-only.yml')).Hash.ToLowerInvariant()
$manifest=[ordered]@{schema='MEMPHIS-FAILURE-CLOSURE-SOURCE-v1';parent_execution='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb';source_raw_sha256=$new;v1_source_raw_sha256=$old;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';preservation_note='All historical physics/M1/fixtures/contracts unchanged; only new branch genericCI exclusion changes, prior branch CI exact bytes retained ininfra/prior-ci.yml';formal=$false;hardware=$false;production=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 12),$utf8)
Get-FileHash (Join-Path $PSScriptRoot 'source_manifest.json')
