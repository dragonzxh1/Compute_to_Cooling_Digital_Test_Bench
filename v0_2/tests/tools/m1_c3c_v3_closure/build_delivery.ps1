# Pure-file delivery assembly. No runtime/candidate changes or approval creation.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$dest=Join-Path $repo 'C3_C_V3_FINAL_FREEZE_PACKAGE'
$target=Join-Path $dest 'EXECUTABLE_FREEZE_MANIFEST.json'
if(Test-Path -LiteralPath $target){throw 'DELIVERY_ALREADY_ASSEMBLED_DO_NOT_OVERWRITE'}
$active=Join-Path $repo 'artifacts/m1-c3c-v3-freeze/executable_proposal.json'
if((Get-FileHash -LiteralPath $active).Hash.ToLowerInvariant() -cne '2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7'){throw 'REVIEWED_PROPOSAL_DRIFT'}
$p=Get-Content -LiteralPath $active -Raw|ConvertFrom-Json -AsHashtable
if(@($p.source_raw_sha256.Keys).Count -ne 755){throw 'REGISTERED_SOURCE_COUNT_DRIFT'}
Copy-Item -LiteralPath $active -Destination $target
New-Item -ItemType Directory -Path (Join-Path $dest 'registrations')|Out-Null
$paths=[ordered]@{}
foreach($key in @('limited_scope','SEM01','SEM02','PF06_supplement')){
    $name='registrations/'+(Split-Path $p.registration_paths[$key] -Leaf)
    Copy-Item -LiteralPath (Join-Path $repo $p.registration_paths[$key]) -Destination (Join-Path $dest $name)
    if((Get-FileHash -LiteralPath (Join-Path $dest $name)).Hash.ToLowerInvariant() -cne $p.registration_raw_sha256[$key]){throw 'DELIVERY_REGISTRATION_DRIFT'}
    $paths[$key]=$name
}
Copy-Item -LiteralPath (Join-Path $repo $p.execution.environment_lock) -Destination (Join-Path $dest 'ENVIRONMENT_DEPENDENCY_LOCK.json')
Copy-Item -LiteralPath (Join-Path $repo $p.environment_policy_registration) -Destination (Join-Path $dest 'ENVIRONMENT_POLICY_REGISTRATION.json')
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_v3/batch.ps1')
$null=Write-C3Json (Join-Path $dest 'SCOPE_SEMANTIC_REGISTRATION_INDEX.json') @{
    schema='m1-c3c-v3-delivery-semantic-index-v1';package_version='C3-C-v3-final-proposal'
    scope=$p.scope;candidate_sha256=$p.candidate_sha256
    registration_raw_sha256=$p.registration_raw_sha256
    package_registration_paths=$paths;active_registration_paths=$p.registration_paths
    environment_policy_path='ENVIRONMENT_POLICY_REGISTRATION.json'
    status='PROPOSED_NOT_USER_APPROVED';limitations=$p.limitations
    formal_qualification_executed=$false;approval_generated=$false
}
$payload=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $dest -File -Recurse -Force){$name=$file.FullName.Substring($dest.Length+1).Replace('\','/');$payload[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
$names=[string[]](@($payload.Keys)+@('EXACT_HASH_INVENTORY.json'));[Array]::Sort($names,[StringComparer]::Ordinal)
$inventory=Join-Path $dest 'EXACT_HASH_INVENTORY.json'
$null=Write-C3Json $inventory @{
    schema='m1-c3c-v3-delivery-exact-inventory-v1';source_raw_sha256=$p.source_raw_sha256
    payload_files=$names;payload_raw_sha256=$payload
    self_inventory_hash_bound_by='Separate read-only control and detached post-commit attestation; no circular self hash'
    source_count=755;proposal_raw_sha256='2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7'
}
$hashes=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File){if($file.Name -ceq 'control.json'){continue};$name='v0_2/tests/tools/m1_c3c_v3_closure/'+$file.Name;$hashes[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
foreach($file in Get-ChildItem -LiteralPath $dest -File -Recurse -Force){$name='C3_C_V3_FINAL_FREEZE_PACKAGE/'+$file.FullName.Substring($dest.Length+1).Replace('\','/');$hashes[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
$hashes['.github/workflows/m1-remote-long-probe-v2-1.yml']=(Get-FileHash -LiteralPath (Join-Path $repo '.github/workflows/m1-remote-long-probe-v2-1.yml')).Hash.ToLowerInvariant()
$control=Join-Path $PSScriptRoot 'control.json'
$controlHash=Write-C3Json $control @{
    schema='m1-c3c-v3-complete-delivery-readback-control-v1';scope='DEVELOPMENT_PRE_SIGN_READ_ONLY'
    source_hashes=$hashes;formal_behavior_authorized=$false
    protected_parent_manifest_path='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
    proposal_raw_sha256='2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7'
    proposal_canonical_sha256='d83a7ba989a23d88b3f2ac19eba4b9b74c71f20dab9c81129277577446f8b0f6'
    runtime_must_bind_exact_delivered_commit=$true
}
[pscustomobject]@{control_raw_sha256=$controlHash;readonly_launcher=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'run_readback.ps1')).Hash.ToLowerInvariant();payload_file_count=$names.Count;inventory_raw_sha256=(Get-FileHash -LiteralPath $inventory).Hash.ToLowerInvariant()}|ConvertTo-Json
