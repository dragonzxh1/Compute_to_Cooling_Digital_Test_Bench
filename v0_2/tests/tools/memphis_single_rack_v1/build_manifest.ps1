# Pure file snapshot only; no Python/model/native execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$paths=@(Get-ChildItem $PSScriptRoot -File | Where-Object Name -cne 'source_manifest.json' | ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})
$paths+=@('.github/workflows/memphis-rack-v1.yml','.github/workflows/memphis-rack-v1-runner.yml')
$new=[ordered]@{};foreach($path in $paths|Sort-Object){$new[$path]=(Get-FileHash (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$priorPath=Join-Path $repo 'v0_2/tests/tools/memphis_project_v2/source_manifest.json'
if((Get-FileHash $priorPath).Hash.ToLowerInvariant() -cne '0fae67b3b430f7072030f5338e8ff54512c9e9c0c0eb1f135efabdd088ec21a3'){throw 'PRESERVED_V2_MANIFEST_DRIFT'}
$prior=Get-Content $priorPath -Raw|ConvertFrom-Json;$old=[ordered]@{}
foreach($map in @($prior.source_raw_sha256,$prior.v1_source_raw_sha256)){
 foreach($b in $map.PSObject.Properties){if((Get-FileHash (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PRESERVED_SOURCE_DRIFT '+$b.Name)};$old[$b.Name]=$b.Value}
}
$old['v0_2/tests/tools/memphis_project_v2/source_manifest.json']='0fae67b3b430f7072030f5338e8ff54512c9e9c0c0eb1f135efabdd088ec21a3'
$manifest=[ordered]@{schema='MEMPHIS-SINGLE-RACK-FIRST-SOURCE-v1';snapshot_parent_commit=(git -C $repo rev-parse HEAD).Trim();
 candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';
 source_raw_sha256=$new;v1_source_raw_sha256=$old;formal_C3C=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'source_manifest.json'),($manifest|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))
Get-FileHash (Join-Path $PSScriptRoot 'source_manifest.json')
