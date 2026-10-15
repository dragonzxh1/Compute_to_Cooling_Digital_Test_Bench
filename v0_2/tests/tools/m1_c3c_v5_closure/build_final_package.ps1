# Pure-file promotion/assembly. Never signs or grants formal authority.
param([Parameter(Mandatory)][string]$ExpectedDraftSha256)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$draft=Join-Path $repo 'artifacts/m1-c3c-v5-draft/executable_proposal.json'
if((Get-FileHash -LiteralPath $draft).Hash.ToLowerInvariant() -cne $ExpectedDraftSha256){throw 'V5_DRAFT_IDENTITY_DRIFT'}
$p=Get-Content -Raw -LiteralPath $draft|ConvertFrom-Json -AsHashtable
if($p.status -cne 'PREPARATION_NOT_FINALIZED' -or $p.approval_generated -or $p.formal_execution_started){throw 'V5_DRAFT_NOT_PROMOTABLE'}
$archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $p.bundle_path));$sha=[Security.Cryptography.SHA256]::Create()
try{foreach($pair in $p.source_raw_sha256.GetEnumerator()) {
    $path=Join-Path $repo $pair.Key
    if(Test-Path -LiteralPath $path){$got=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    else{$entry=$archive.GetEntry($pair.Key);if($null -eq $entry){throw 'V5_REVIEW_SOURCE_MISSING'};$stream=$entry.Open();try{$got=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}}
    if($got -cne $pair.Value){throw ('V5_REVIEW_SOURCE_DRIFT: '+$pair.Key)}
}}finally{$archive.Dispose();$sha.Dispose()}
$activeDir=Join-Path $repo 'artifacts/m1-c3c-v5-freeze'
if(Test-Path -LiteralPath $activeDir){throw 'V5_NEW_FINAL_PACKAGE_REQUIRED'}
New-Item -ItemType Directory -Path $activeDir|Out-Null
[IO.File]::WriteAllText((Join-Path $activeDir '.gitattributes'),"*.json -text -eol`n",[Text.UTF8Encoding]::new($false))
foreach($key in @('limited_scope','SEM01','SEM02','PF06_supplement')) {
    $source=Join-Path $repo $p.registration_paths[$key];$name=Split-Path $source -Leaf
    Copy-Item -LiteralPath $source -Destination (Join-Path $activeDir $name)
    $newPath='artifacts/m1-c3c-v5-freeze/'+$name
    $newHash=(Get-FileHash -LiteralPath (Join-Path $repo $newPath)).Hash.ToLowerInvariant()
    if($newHash -cne $p.registration_raw_sha256[$key]){throw 'V5_NORMATIVE_BYTES_CHANGED'}
    $p.registration_paths[$key]=$newPath;$p.source_raw_sha256[$newPath]=$newHash
}
$p.status='FINALIZED_AWAITING_USER_APPROVAL'
$p.approval_generated=$false;$p.formal_execution_started=$false
$p.snapshot_parent_commit=(git -C $repo rev-parse HEAD)
$p.evidence_delivery_registration=@{
    version='C3C-V5-EXPLICIT-UPSTREAM-NATIVE-DELIVERY-v1'
    required_final_artifact_inputs=@('schema-*','startup-*','prepare','ref-*','reference-gate','select-*','split-*','prefix-*','plan')
    original_v3_execution='38586777499';original_v3_classification='INVALID_C3_C_EXECUTION'
    original_v3_reclassification_authorized=$false
    readonly_transport_proof_run='38671417001';readonly_proof_is_not_behavioral_or_formal_result=$true
    runtime_stage_obligations_unchanged=$true;raw_job_cleanup_source_environment_evidence_required=$true
}
$p.final_audit_revision=@{
    version='C3C-V5-INVOCATION-LOCAL-IMMUTABLE-PACKAGE-CHECK-v1'
    original_v4_execution='38675166533';original_v4_classification='INVALID_C3_C_EXECUTION'
    original_v4_reclassification_authorized=$false
    implementation_change='Load immutable package/environment lock once per audit invocation, outside per-stage loops; retain per-record checks and before/after source guards'
    progress='11 durable BEGIN/END phase pairs and batch/case counters'
    assembly_proof_run='38759498586';assembly_unit_checks=57;assembly_control_checks=62
    native_archive_readback_run='38754888400';remaining_archive_aggregation_run='38756839568'
    archived_readback_is_not_fresh_qualification=$true
    cpu_memory_wall_budget_and_model_timers_unchanged=$true
}
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
function Save-Canonical([string]$Path,$Value) {
    if(Test-Path -LiteralPath $Path){throw 'V5_PACKAGE_NO_OVERWRITE'}
    [IO.File]::WriteAllText($Path,(ConvertTo-C3DeliveryCanonical $Value)+"`n",[Text.UTF8Encoding]::new($false))
    return (Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant()
}
$proposal=Join-Path $activeDir 'executable_proposal.json'
$proposalHash=Save-Canonical $proposal $p
$canonicalHash=Get-C3DeliverySha ([Text.Encoding]::UTF8.GetBytes((ConvertTo-C3DeliveryCanonical $p)))
$dest=Join-Path $repo 'C3_C_V5_FINAL_FREEZE_PACKAGE'
if(Test-Path -LiteralPath $dest){throw 'V5_DELIVERY_ALREADY_ASSEMBLED'}
New-Item -ItemType Directory -Path $dest|Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'OPERATOR_INSTRUCTIONS.md') -Destination (Join-Path $dest 'OPERATOR_INSTRUCTIONS.md')
[IO.File]::WriteAllText((Join-Path $dest '.gitattributes'),"* -text -eol`n",[Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath $proposal -Destination (Join-Path $dest 'EXECUTABLE_FREEZE_MANIFEST.json')
New-Item -ItemType Directory -Path (Join-Path $dest 'registrations')|Out-Null
$paths=[ordered]@{}
foreach($key in @('limited_scope','SEM01','SEM02','PF06_supplement')) {
    $name='registrations/'+(Split-Path $p.registration_paths[$key] -Leaf)
    Copy-Item -LiteralPath (Join-Path $repo $p.registration_paths[$key]) -Destination (Join-Path $dest $name)
    $paths[$key]=$name
}
Copy-Item -LiteralPath (Join-Path $repo $p.execution.environment_lock) -Destination (Join-Path $dest 'ENVIRONMENT_DEPENDENCY_LOCK.json')
Copy-Item -LiteralPath (Join-Path $repo $p.environment_policy_registration) -Destination (Join-Path $dest 'ENVIRONMENT_POLICY_REGISTRATION.json')
$null=Save-Canonical (Join-Path $dest 'SCOPE_SEMANTIC_REGISTRATION_INDEX.json') @{
    schema='m1-c3c-v5-delivery-semantic-index-v1';package_version='C3-C-v5-final-proposal'
    scope=$p.scope;candidate_sha256=$p.candidate_sha256;registration_raw_sha256=$p.registration_raw_sha256
    package_registration_paths=$paths;active_registration_paths=$p.registration_paths
    environment_policy_path='ENVIRONMENT_POLICY_REGISTRATION.json';status='PROPOSED_NOT_USER_APPROVED'
    limitations=$p.limitations;formal_qualification_executed=$false;approval_generated=$false
    evidence_delivery_registration=$p.evidence_delivery_registration
}
$payload=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $dest -Recurse -File -Force){$name=$file.FullName.Substring($dest.Length+1).Replace('\','/');$payload[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
$names=[string[]](@($payload.Keys)+@('EXACT_HASH_INVENTORY.json'));[Array]::Sort($names,[StringComparer]::Ordinal)
$inventory=Join-Path $dest 'EXACT_HASH_INVENTORY.json'
$inventoryHash=Save-Canonical $inventory @{
    schema='m1-c3c-v5-delivery-exact-inventory-v1';source_raw_sha256=$p.source_raw_sha256
    payload_files=$names;payload_raw_sha256=$payload;source_count=$p.source_raw_sha256.Count
    proposal_raw_sha256=$proposalHash;self_inventory_hash_bound_by='Independent read-only control and detached post-commit attestation; no circular hash'
}
$hashes=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File){if($file.Name -ceq 'control.json'){continue};$name='v0_2/tests/tools/m1_c3c_v5_closure/'+$file.Name;$hashes[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
foreach($file in Get-ChildItem -LiteralPath $dest -Recurse -File -Force){$name='C3_C_V5_FINAL_FREEZE_PACKAGE/'+$file.FullName.Substring($dest.Length+1).Replace('\','/');$hashes[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
$workflow='.github/workflows/m1-remote-long-probe.yml'
$hashes[$workflow]=(Get-FileHash -LiteralPath (Join-Path $repo $workflow)).Hash.ToLowerInvariant()
$controlHash=Save-Canonical (Join-Path $PSScriptRoot 'control.json') @{
    schema='m1-c3c-v5-complete-delivery-readback-control-v1';scope='DEVELOPMENT_PRE_SIGN_READ_ONLY'
    source_hashes=$hashes;formal_behavior_authorized=$false
    protected_parent_manifest_path='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
    proposal_raw_sha256=$proposalHash;proposal_canonical_sha256=$canonicalHash
    expected_source_binding_count=$p.source_raw_sha256.Count;expected_refusal_check_count=9
    runtime_must_bind_exact_delivered_commit=$true
}
[pscustomobject]@{status='FINALIZED_AWAITING_USER_APPROVAL';proposal_raw=$proposalHash;proposal_canonical=$canonicalHash;source_bindings=$p.source_raw_sha256.Count;control_raw=$controlHash;readonly_launcher=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'run_readback.ps1')).Hash.ToLowerInvariant();payload_static_files=$names.Count;inventory_raw=$inventoryHash;formal_execution_authorized=$false}|ConvertTo-Json
