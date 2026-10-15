# Pure-file draft/controls. Creates neither approval nor executable freeze.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$priorPath=Join-Path $repo 'artifacts/m1-c3c-v3-freeze/executable_proposal.json'
if((Get-FileHash -LiteralPath $priorPath).Hash.ToLowerInvariant() -cne '2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7'){throw 'V4_APPROVED_PRIOR_DRIFT'}
$p=Get-Content -Raw -LiteralPath $priorPath|ConvertFrom-Json -AsHashtable
$archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $p.bundle_path));$sha=[Security.Cryptography.SHA256]::Create()
try{foreach($pair in $p.source_raw_sha256.GetEnumerator()) {
    $path=Join-Path $repo $pair.Key
    if(Test-Path -LiteralPath $path){$got=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    else{$entry=$archive.GetEntry($pair.Key);if($null -eq $entry){throw 'V4_FROZEN_SOURCE_MISSING'};$stream=$entry.Open();try{$got=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}}
    if($got -cne $pair.Value){throw ('V4_ORIGINAL_PROTECTED_SOURCE_DRIFT: '+$pair.Key)}
}}finally{$archive.Dispose();$sha.Dispose()}
$dest=Join-Path $repo 'artifacts/m1-c3c-v4-draft'
if(Test-Path -LiteralPath $dest){throw 'V4_FRESH_DRAFT_REQUIRED'}
New-Item -ItemType Directory -Path $dest|Out-Null
[IO.File]::WriteAllText((Join-Path $dest '.gitattributes'),"*.json -text -eol`n",[Text.UTF8Encoding]::new($false))
foreach($name in @('limited_scope','SEM01','SEM02','PF06_supplement')) {
    $source=Join-Path $repo $p.registration_paths[$name]
    $leaf=Split-Path $source -Leaf
    Copy-Item -LiteralPath $source -Destination (Join-Path $dest $leaf)
    $path='artifacts/m1-c3c-v4-draft/'+$leaf
    $hash=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()
    if($hash -cne $p.registration_raw_sha256[$name]){throw 'V4_NORMATIVE_REGISTRATION_CHANGED'}
    $p.registration_paths[$name]=$path;$p.source_raw_sha256[$path]=$hash
}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File) {
    if($file.Name -eq 'assembly_v4_control.json'){continue}
    $path='v0_2/tests/tools/m1_c3c_v4/'+$file.Name
    $p.source_raw_sha256[$path]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()
}
foreach($path in @('.github/workflows/m1-c3c-full-v4.yml','.github/workflows/m1-c3c-v4-assembly.yml','.github/actions/m1-c3c-runtime-v4/action.yml','v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1','v0_2/tests/tools/m1_c3c_delivery_v4/test_native_closure.ps1')) {
    $p.source_raw_sha256[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()
}
foreach($key in @('runner','worker','environment_lock','artifact_schema','stop_rules')){$p.execution[$key]=$p.execution[$key].Replace('m1_c3c_v3','m1_c3c_v4')}
$p.execution.workflow='.github/workflows/m1-c3c-full-v4.yml'
$p.status='PREPARATION_NOT_FINALIZED'
$p.approval_generated=$false;$p.formal_execution_started=$false
$p.snapshot_parent_commit=(git -C $repo rev-parse HEAD)
$p.prior_approved_package_raw_sha256='2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7'
$p.revision_scope='Versioned namespace only plus final downloading all original upstream native evidence families; unchanged candidate/math/profile/contracts/fixtures/expectations/timing/authority/gates.'
$p.environment_policy_registration='v0_2/tests/tools/m1_c3c_v4/environment_policy_registration.json'
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
$raw=ConvertTo-C3DeliveryCanonical $p
[IO.File]::WriteAllText((Join-Path $dest 'executable_proposal.json'),$raw+"`n",[Text.UTF8Encoding]::new($false))
$control=@{schema='m1-c3c-v4-assembly-control';scope='DEVELOPMENT_INFRASTRUCTURE_ONLY';synthetic_test_count=53;formal_behavior_authorized=$false;protected_parent_manifest_path='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json';source_hashes=$p.source_raw_sha256}
$controlPath=Join-Path $PSScriptRoot 'assembly_v4_control.json'
if(Test-Path -LiteralPath $controlPath){throw 'V4_NO_ASSEMBLY_CONTROL_OVERWRITE'}
[IO.File]::WriteAllText($controlPath,(ConvertTo-C3DeliveryCanonical $control)+"`n",[Text.UTF8Encoding]::new($false))
[pscustomobject]@{status='PREPARATION_NOT_FINALIZED';draft_raw=(Get-FileHash -LiteralPath (Join-Path $dest 'executable_proposal.json')).Hash.ToLowerInvariant();source_binding_count=$p.source_raw_sha256.Count;assembly_control=(Get-FileHash -LiteralPath $controlPath).Hash.ToLowerInvariant();formal_execution_authorized=$false}|ConvertTo-Json
