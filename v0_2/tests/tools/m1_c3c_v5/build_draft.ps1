# Pure-file draft/controls. Creates neither approval nor executable freeze.
param([string]$ExpectedPriorDraftSha256,[string]$ExpectedPriorControlSha256)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$priorPath=Join-Path $repo 'artifacts/m1-c3c-v4-freeze/executable_proposal.json'
if((Get-FileHash -LiteralPath $priorPath).Hash.ToLowerInvariant() -cne '759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357'){throw 'V5_APPROVED_PRIOR_DRIFT'}
$p=Get-Content -Raw -LiteralPath $priorPath|ConvertFrom-Json -AsHashtable
$archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $p.bundle_path));$sha=[Security.Cryptography.SHA256]::Create()
try{foreach($pair in $p.source_raw_sha256.GetEnumerator()) {
    # The prior pinned ref stays immutable. Only the already-versioned router
    # is replaced in this NEW draft and rebound below; all other prior bytes match.
    if($pair.Key -ceq '.github/workflows/m1-remote-long-probe-v2-1.yml'){continue}
    $path=Join-Path $repo $pair.Key
    if(Test-Path -LiteralPath $path){$got=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    else{$entry=$archive.GetEntry($pair.Key);if($null -eq $entry){throw 'V5_FROZEN_SOURCE_MISSING'};$stream=$entry.Open();try{$got=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}}
    if($got -cne $pair.Value){throw ('V5_ORIGINAL_PROTECTED_SOURCE_DRIFT: '+$pair.Key)}
}}finally{$archive.Dispose();$sha.Dispose()}
$dest=Join-Path $repo 'artifacts/m1-c3c-v5-draft'
if(Test-Path -LiteralPath $dest) {
    $priorDraft=Join-Path $dest 'executable_proposal.json'
    $priorControl=Join-Path $PSScriptRoot 'assembly_v5_control.json'
    if($ExpectedPriorDraftSha256 -cnotmatch '^[a-f0-9]{64}$' -or $ExpectedPriorControlSha256 -cnotmatch '^[a-f0-9]{64}$' -or
       (Get-FileHash -LiteralPath $priorDraft).Hash.ToLowerInvariant() -cne $ExpectedPriorDraftSha256 -or
       (Get-FileHash -LiteralPath $priorControl).Hash.ToLowerInvariant() -cne $ExpectedPriorControlSha256){throw 'V5_UNSEALED_REFRESH_IDENTITY_REQUIRED'}
    $previous=Get-Content -Raw -LiteralPath $priorDraft|ConvertFrom-Json -AsHashtable
    if($previous.status -cne 'PREPARATION_NOT_FINALIZED' -or $previous.approval_generated -or $previous.formal_execution_started){throw 'V5_SEALED_DRAFT_REFRESH_DENIED'}
} else {New-Item -ItemType Directory -Path $dest|Out-Null}
[IO.File]::WriteAllText((Join-Path $dest '.gitattributes'),"*.json -text -eol`n",[Text.UTF8Encoding]::new($false))
foreach($name in @('limited_scope','SEM01','SEM02','PF06_supplement')) {
    $source=Join-Path $repo $p.registration_paths[$name]
    $leaf=Split-Path $source -Leaf
    Copy-Item -LiteralPath $source -Destination (Join-Path $dest $leaf)
    $path='artifacts/m1-c3c-v5-draft/'+$leaf
    $hash=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()
    if($hash -cne $p.registration_raw_sha256[$name]){throw 'V5_NORMATIVE_REGISTRATION_CHANGED'}
    $p.registration_paths[$name]=$path;$p.source_raw_sha256[$path]=$hash
}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File) {
    if($file.Name -eq 'assembly_v5_control.json'){continue}
    $path='v0_2/tests/tools/m1_c3c_v5/'+$file.Name
    $p.source_raw_sha256[$path]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()
}
foreach($path in @('.github/workflows/m1-c3c-full-v5.yml','.github/workflows/m1-c3c-v5-assembly.yml','.github/workflows/m1-remote-long-probe-v2-1.yml','.github/actions/m1-c3c-runtime-v5/action.yml','v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1','v0_2/tests/tools/m1_c3c_delivery_v4/test_native_closure.ps1')) {
    $p.source_raw_sha256[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()
}
foreach($key in @('runner','worker','environment_lock','artifact_schema','stop_rules')){$p.execution[$key]=$p.execution[$key].Replace('m1_c3c_v4','m1_c3c_v5')}
$p.execution.workflow='.github/workflows/m1-c3c-full-v5.yml'
$p.status='PREPARATION_NOT_FINALIZED'
$p.approval_generated=$false;$p.formal_execution_started=$false
$p.snapshot_parent_commit=(git -C $repo rev-parse HEAD)
$p.prior_approved_package_raw_sha256='759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357'
$p.revision_scope='Versioned execution namespace; invocation-local FINAL package/environment-lock load and durable progress only. Candidate/math/profile/contracts/fixtures/expectations/timers/authority/acceptance/transport coverage unchanged.'
$p.versioned_router_revision=@{path='.github/workflows/m1-remote-long-probe-v2-1.yml';prior_approved_raw_sha256='8a08ca7d4f5980f52e657ae29b1b929cccbf433052fcb9e0ed82480c03a0df17';new_raw_sha256=(Get-FileHash -LiteralPath (Join-Path $repo '.github/workflows/m1-remote-long-probe-v2-1.yml')).Hash.ToLowerInvariant();new_version_not_original_execution_patch=$true}
$p.environment_policy_registration='v0_2/tests/tools/m1_c3c_v5/environment_policy_registration.json'
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
$raw=ConvertTo-C3DeliveryCanonical $p
[IO.File]::WriteAllText((Join-Path $dest 'executable_proposal.json'),$raw+"`n",[Text.UTF8Encoding]::new($false))
$control=@{schema='m1-c3c-v5-assembly-control';scope='DEVELOPMENT_INFRASTRUCTURE_ONLY';synthetic_test_count=57;formal_behavior_authorized=$false;protected_parent_manifest_path='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json';source_hashes=$p.source_raw_sha256}
$controlPath=Join-Path $PSScriptRoot 'assembly_v5_control.json'
if((Test-Path -LiteralPath $controlPath) -and !$ExpectedPriorControlSha256){throw 'V5_NO_ASSEMBLY_CONTROL_OVERWRITE'}
[IO.File]::WriteAllText($controlPath,(ConvertTo-C3DeliveryCanonical $control)+"`n",[Text.UTF8Encoding]::new($false))
[pscustomobject]@{status='PREPARATION_NOT_FINALIZED';draft_raw=(Get-FileHash -LiteralPath (Join-Path $dest 'executable_proposal.json')).Hash.ToLowerInvariant();source_binding_count=$p.source_raw_sha256.Count;assembly_control=(Get-FileHash -LiteralPath $controlPath).Hash.ToLowerInvariant();formal_execution_authorized=$false}|ConvertTo-Json
