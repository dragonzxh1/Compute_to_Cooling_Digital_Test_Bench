# Pure file assembly; never executes a candidate or generates user approval.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$oldDir=Join-Path $repo 'artifacts/m1-c3c-v1-freeze'
$dest=Join-Path $repo 'artifacts/m1-c3c-v3-freeze'
if(Test-Path -LiteralPath $dest){throw 'FRESH_PROPOSAL_DIRECTORY_REQUIRED'}
$prior=Join-Path $oldDir 'executable_proposal.json'
if((Get-FileHash -LiteralPath $prior).Hash.ToLowerInvariant() -cne 'f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45'){throw 'SIGNED_PRIOR_PACKAGE_DRIFT'}
$p=Get-Content -LiteralPath $prior -Raw|ConvertFrom-Json -AsHashtable
$newLock=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'environment_lock.json') -Raw|ConvertFrom-Json -AsHashtable
$oldLock=Get-Content -LiteralPath (Join-Path $repo 'v0_2/tests/tools/m1_c3c_v1/environment_lock.json') -Raw|ConvertFrom-Json -AsHashtable
if(($newLock.image_version -join ',') -cne '20261004.326.1,20261012.333.1'){throw 'UNAPPROVED_ENVIRONMENT_POLICY'}
foreach($key in @('python','system','version','machine','image_os','dependencies')){if((ConvertTo-Json -InputObject $newLock[$key] -Depth 10 -Compress) -cne (ConvertTo-Json -InputObject $oldLock[$key] -Depth 10 -Compress)){throw ('UNAUTHORIZED_IDENTITY_CHANGE:'+ $key)}}
$zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $p.bundle_path))
$sha=[Security.Cryptography.SHA256]::Create()
try{foreach($item in $p.source_raw_sha256.GetEnumerator()){
    if($item.Key -ceq '.github/workflows/liquid-cooling-recovery.yml'){continue}
    $path=Join-Path $repo $item.Key
    if(Test-Path -LiteralPath $path){$got=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    else{$entry=$zip.GetEntry($item.Key);if($null -eq $entry){throw ('FROZEN_SOURCE_MISSING:'+ $item.Key)};$stream=$entry.Open();try{$got=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}}
    if($got -cne $item.Value){throw ('FROZEN_SOURCE_CHANGED:'+ $item.Key)}
}}finally{$zip.Dispose();$sha.Dispose()}
New-Item -ItemType Directory -Path $dest|Out-Null
[IO.File]::WriteAllText((Join-Path $dest '.gitattributes'),"*.json -text -eol`n",[Text.UTF8Encoding]::new($false))
$hashes=$p.source_raw_sha256
foreach($decision in @('limited_scope','SEM01','SEM02','PF06_supplement')){
    $source=Join-Path $repo $p.registration_paths[$decision]
    $name=Split-Path $source -Leaf
    Copy-Item -LiteralPath $source -Destination (Join-Path $dest $name)
    $newPath='artifacts/m1-c3c-v3-freeze/'+$name
    $p.registration_paths[$decision]=$newPath
    $hashes[$newPath]=(Get-FileHash -LiteralPath (Join-Path $repo $newPath)).Hash.ToLowerInvariant()
    if($hashes[$newPath] -cne $p.registration_raw_sha256[$decision]){throw 'NORMATIVE_REGISTRATION_CHANGED'}
}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File){
    $path='v0_2/tests/tools/m1_c3c_v3/'+$file.Name
    $hashes[$path]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()
}
foreach($path in @('.github/workflows/liquid-cooling-recovery.yml','.github/workflows/m1-c3c-full-v3.yml','.github/workflows/m1-c3c-v3-assembly.yml','.github/workflows/m1-c3c-v3-pre-sign.yml','.github/actions/m1-c3c-runtime-v3/action.yml','artifacts/m1-c3c-v1-freeze/executable_proposal.json')){$hashes[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
foreach($key in @('runner','worker','environment_lock','artifact_schema','stop_rules')){$p.execution[$key]=$p.execution[$key].Replace('m1_c3c_v1','m1_c3c_v3')}
$p.execution.workflow='.github/workflows/m1-c3c-full-v3.yml'
$p.prior_approved_package_raw_sha256='f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45'
$p.environment_policy_registration='v0_2/tests/tools/m1_c3c_v3/environment_policy_registration.json'
$p.revision_scope='Only approved two-image environment whitelist and fail-closed INVALID diagnostic/envelope handling; no candidate/math/input/expectation/threshold/timer/contract changes'
$p.environment_scope='Actual completed stage-image pairings; no claim that every descriptor ran on both image builds'
$p.snapshot_parent_commit=(git -C $repo rev-parse HEAD)
$p.approval_generated=$false;$p.formal_execution_started=$false
. (Join-Path $PSScriptRoot 'batch.ps1')
$proposalPath=Join-Path $dest 'executable_proposal.json'
$rawHash=Write-C3Json $proposalPath $p
function Canonical-Json($value){
    if($null -eq $value){return 'null'}
    if($value -is [Collections.IDictionary]){$keys=[string[]]@($value.Keys);[Array]::Sort($keys,[StringComparer]::Ordinal);$parts=@(foreach($k in $keys){(ConvertTo-Json -InputObject $k -Compress)+':'+(Canonical-Json $value[$k])});return '{'+[string]::Join(',',$parts)+'}'}
    if($value -is [Array]){$parts=@(foreach($v in $value){Canonical-Json $v});return '['+[string]::Join(',',$parts)+']'}
    return (ConvertTo-Json -InputObject $value -Compress)
}
$sha=[Security.Cryptography.SHA256]::Create()
try{$canonicalHash=[Convert]::ToHexString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes((Canonical-Json $p)))).ToLowerInvariant()}finally{$sha.Dispose()}
$controlSources=[ordered]@{}
foreach($name in @('pre_sign_v2_worker.py','run_pre_sign_v2.ps1','verify_proposal.py')){$path='v0_2/tests/tools/m1_c3c_v3/'+$name;$controlSources[$path]=$hashes[$path]}
foreach($path in @('.github/workflows/m1-c3c-v3-pre-sign.yml','.github/workflows/liquid-cooling-recovery.yml','v0_2/tests/tools/m1_campaign_v4/execution_manifest.json')){$controlSources[$path]=$hashes[$path]}
$controlSources['artifacts/m1-c3c-v3-freeze/executable_proposal.json']=$rawHash
$controlPath=Join-Path $PSScriptRoot 'pre_sign_v2_control.json'
$controlHash=Write-C3Json $controlPath @{
    schema='m1-c3c-v3-proposal-pre-sign-control';status='PREREGISTERED_NOT_EXECUTED'
    scope='DEVELOPMENT_PRE_SIGN_READ_ONLY';source_hashes=$controlSources
    protected_parent_manifest_path='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
    proposal_raw_sha256=$rawHash;candidate_behavioral_execution=$false;formal_behavior_authorized=$false
}
[pscustomobject]@{proposal_raw=$rawHash;proposal_canonical=$canonicalHash;source_bindings=@($hashes.Keys).Count;pre_sign_control=$controlHash;pre_sign_runner=$hashes['v0_2/tests/tools/m1_c3c_v3/run_pre_sign_v2.ps1'];formal_runner=$hashes[$p.execution.runner];environment_lock=$hashes[$p.execution.environment_lock]}|ConvertTo-Json
