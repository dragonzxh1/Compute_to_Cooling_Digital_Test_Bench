# Pure source/hash operations; no local numerical workload.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$priorPath=Join-Path $repo 'v0_2/tests/tools/memphis_topology_audit_v1/source_manifest.json'
if((Get-FileHash $priorPath).Hash.ToLowerInvariant() -cne '25126c48431eb62697a70b19529b8f0a5eedb7099815321189ea33eae8cc64d5'){throw 'SEALED_PARENT_MANIFEST_DRIFT'}
$prior=Get-Content -LiteralPath $priorPath -Raw|ConvertFrom-Json;$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){
 foreach($p in $map.PSObject.Properties){
  $key=if($p.Name -ceq '.github/workflows/ci.yml'){'v0_2/tests/tools/memphis_topology_audit_v1/infra/ci-branch-only.yml'}else{$p.Name}
  if((Get-FileHash -LiteralPath (Join-Path $repo $key)).Hash.ToLowerInvariant() -cne $p.Value){throw ('PARENT_SOURCE_DRIFT '+$key)}
  $old[$key]=$p.Value
 }
}
$old['v0_2/tests/tools/memphis_topology_audit_v1/source_manifest.json']=(Get-FileHash $priorPath).Hash.ToLowerInvariant()
$new=[ordered]@{}
$paths=@(Get-ChildItem $PSScriptRoot -File -Recurse|Where-Object Name -ne 'source_manifest.json'|ForEach-Object{[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-loop-validation-v1.yml','.github/workflows/memphis-loop-validation-v1-runner.yml')
foreach($p in $paths|Sort-Object){$new[$p]=(Get-FileHash -LiteralPath (Join-Path $repo $p)).Hash.ToLowerInvariant()}
$new['.github/workflows/ci.yml']=(Get-FileHash (Join-Path $PSScriptRoot 'infra/ci-branch-only.yml')).Hash.ToLowerInvariant()
$freeze=Get-Content (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json') -Raw|ConvertFrom-Json
foreach($p in $freeze.source_raw_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $p.Name)).Hash.ToLowerInvariant() -cne $p.Value){throw ('PROTECTED_SOURCE_DRIFT '+$p.Name)}}
$reg=Get-Content (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
$m=[ordered]@{schema='MEMPHIS-LOOP-VALIDATION-SOURCE-v1';build=$reg.build;source_raw_sha256=$new;v1_source_raw_sha256=$old;protected_source_count=@($freeze.source_raw_sha256.PSObject.Properties).Count;candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';parent_execution=$reg.parent_execution;parent_delivery=$reg.parent_delivery;scope='New primary loop and selectable RC comparison; historical/frozen sources unchanged';formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($m|ConvertTo-Json -Depth 18),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{hash=(Get-FileHash (Join-Path $PSScriptRoot 'source_manifest.json')).Hash.ToLowerInvariant();new=$new.Count;preserved=$old.Count;protected=$m.protected_source_count}|ConvertTo-Json
