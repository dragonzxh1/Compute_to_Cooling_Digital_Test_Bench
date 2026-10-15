# Independent pure-file review of an already downloaded official artifact.
# Does not execute Python/native/model or grant any authority.
param([string]$EvidenceDirectory='artifacts/m1-c3c-v5-final-review/run-38761086285')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$base=(Resolve-Path (Join-Path $repo $EvidenceDirectory)).Path
function Assert([bool]$Condition,[string]$Reason){if(-not $Condition){throw $Reason}}
function Hash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Json([string]$Path){return ,(Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json -AsHashtable)}
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
$raw=Join-Path $base 'raw'
$package=Join-Path $raw 'm1-c3c-v5-final-delivery/C3_C_V5_FINAL_FREEZE_PACKAGE'
$run=Join-Path $raw 'm1-c3c-v5-closure/38761086285-1-CHECKS'
$commit='9ad4b9d1fdab261db9be09b91f261a927d529970'
$zip=Join-Path $base 'official.zip'
Assert ((Hash $zip) -ceq 'c7b310afc1ce62d1febb808997812b53c3dafd556f80e6ba1df5d8597b608607' -and (Get-Item -LiteralPath $zip).Length -eq 134490) 'OFFICIAL_ZIP_IDENTITY'
$archive=[IO.Compression.ZipFile]::OpenRead($zip);$hasher=[Security.Cryptography.SHA256]::Create();$entries=[ordered]@{}
try{foreach($e in $archive.Entries){
    Assert (-not $entries.Contains($e.FullName) -and $e.FullName -notmatch '(^/|\\|(^|/)\.\.(/|$)|:)') 'UNSAFE_OR_DUPLICATE_ZIP_ENTRY'
    $stream=$e.Open();try{$h=[Convert]::ToHexString($hasher.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
    $path=Join-Path $raw $e.FullName
    Assert ((Hash $path) -ceq $h -and (Get-Item -LiteralPath $path).Length -eq $e.Length) 'EXTRACTED_BYTE_DRIFT'
    $entries[$e.FullName]=@{bytes=$e.Length;raw_sha256=$h}
}}finally{$archive.Dispose();$hasher.Dispose()}
Assert (@(Get-ChildItem -LiteralPath $raw -Recurse -Force -File).Count -eq $entries.Count) 'EXTRA_EXTRACTED_FILE'
$definition=Json (Join-Path $package 'EXECUTABLE_FREEZE_MANIFEST.json')
$control=Json (Join-Path $repo 'v0_2/tests/tools/m1_c3c_v5_closure/control.json')
$result=Json (Join-Path $run 'result.json')
$attestation=Json (Join-Path $package 'EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json')
Assert ((Hash (Join-Path $package 'EXECUTABLE_FREEZE_MANIFEST.json')) -ceq $control.proposal_raw_sha256) 'PACKAGE_RAW_DRIFT'
$canon=Get-C3DeliverySha ([Text.Encoding]::UTF8.GetBytes((ConvertTo-C3DeliveryCanonical $definition)))
Assert ($canon -ceq $control.proposal_canonical_sha256 -and $canon -ceq $attestation.proposal_canonical_sha256) 'PACKAGE_CANONICAL_DRIFT'
Assert ($definition.status -ceq 'FINALIZED_AWAITING_USER_APPROVAL' -and -not $definition.approval_generated -and -not $definition.formal_execution_started) 'FALSE_FREEZE_OR_EXECUTION'
$bundle=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $definition.bundle_path));$hasher=[Security.Cryptography.SHA256]::Create();$local=0;$fromBundle=0
try{foreach($b in $definition.source_raw_sha256.GetEnumerator()){
    $path=Join-Path $repo $b.Key
    if(Test-Path -LiteralPath $path){$h=Hash $path;$local++}else{
        $entry=$bundle.GetEntry($b.Key);Assert ($null -ne $entry) 'SOURCE_MISSING'
        $stream=$entry.Open();try{$h=[Convert]::ToHexString($hasher.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()};$fromBundle++
    }
    Assert ($h -ceq $b.Value) ('SOURCE_DRIFT '+$b.Key)
}}finally{$bundle.Dispose();$hasher.Dispose()}
foreach($b in $control.source_hashes.GetEnumerator()){Assert ((Hash (Join-Path $repo $b.Key)) -ceq $b.Value) 'CLOSURE_REVIEWER_SOURCE_DRIFT'}
$inventory=Json (Join-Path $package 'EXACT_HASH_INVENTORY.json')
Assert ((ConvertTo-C3DeliveryCanonical $inventory.source_raw_sha256) -ceq (ConvertTo-C3DeliveryCanonical $definition.source_raw_sha256)) 'SOURCE_INVENTORY_DRIFT'
foreach($b in $inventory.payload_raw_sha256.GetEnumerator()){Assert ((Hash (Join-Path $package $b.Key)) -ceq $b.Value) 'PAYLOAD_DRIFT'}
$names=@(Get-ChildItem -LiteralPath $package -Recurse -Force -File|ForEach-Object {$_.FullName.Substring($package.Length+1).Replace('\','/')})
$expected=@($inventory.payload_files)+@('INDEPENDENT_READBACK_RESULT.json','EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json','USER_APPROVAL_DECISION_SHEET.md')
Assert (@(Compare-Object $names $expected).Count -eq 0) 'DELIVERY_FILE_SET'
foreach($b in $attestation.independently_verified_content_raw_sha256.GetEnumerator()){Assert ((Hash (Join-Path $package $b.Key)) -ceq $b.Value) 'ATTESTATION_CONTENT_DRIFT'}
Assert ((Hash (Join-Path $run 'result.json')) -ceq $attestation.readback_result_raw_sha256 -and (Hash (Join-Path $package 'INDEPENDENT_READBACK_RESULT.json')) -ceq $attestation.readback_result_raw_sha256) 'READBACK_RESULT_DRIFT'
Assert ($result.status -ceq 'C3C_V5_FINAL_PACKAGE_READBACK_PASS' -and $result.source_bindings_verified -eq 836 -and $result.inputs -eq 101 -and $result.input_rows -eq 3216 -and $result.expected_full_snapshots -eq 499 -and $result.required_static_stages_before_final -eq 969) 'READBACK_SCOPE_OR_STATUS'
Assert ($result.source_commit -ceq $commit -and $attestation.execution_source_commit -ceq $commit -and $attestation.delivery_commit -ceq $commit -and $attestation.status -ceq 'READY_FOR_USER_SIGNATURE') 'EXECUTION_DELIVERY_COMMIT_DRIFT'
Assert (-not $result.candidate_imported -and -not $result.candidate_behavioral_execution -and -not $result.formal_qualification -and -not $result.approval_generated -and -not $attestation.executable_freeze_user_approved -and -not $attestation.formal_execution_authorized) 'READONLY_AUTHORITY_VIOLATION'
$ids=@('MISSING_APPROVAL','WRONG_EXECUTION_COMMIT','WRONG_PACKAGE_RAW_HASH','WRONG_SCOPE','MISSING_SOURCE_ARTIFACT','MISSING_DELIVERY_ARTIFACT','EXTRA_UNAUTHORIZED_DELIVERY_FILE','MISSING_UPSTREAM_REFERENCE_DELIVERY','MISSING_UPSTREAM_PREFIX_NATIVE_DELIVERY')
Assert ($result.refusal_checks.Count -eq 9 -and @(Compare-Object $ids @($result.refusal_checks|ForEach-Object id)).Count -eq 0 -and @($result.refusal_checks|Where-Object status -cne 'PASS').Count -eq 0) 'REFUSAL_CHECK_INVENTORY'
$scope=Json (Join-Path $repo $definition.registration_paths.limited_scope)
$spec=Json (Join-Path $repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')
$static=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach($id in $definition.check_stage_ids){$null=$static.Add($id)}
$rows=0;$snapshots=0
for($i=0;$i -lt 101;$i++){
    $input=$definition.inputs[$i];$descriptor=$spec.input_inventory[$i]
    Assert ($input.index -eq $i -and $input.row_count -eq $descriptor.row_count -and $input.input_canonical_sha256 -ceq $descriptor.input_canonical_sha256) 'INPUT_BINDING_DRIFT'
    $rows+=$input.row_count
    foreach($kind in @('REFERENCE','SELECT','SPLIT','SEAL','SCHEMA')){$null=$static.Add(('CASE-{0:000}-{1}' -f $i,$kind))}
    $count=if($descriptor.stage_id -cin @('C-history','S-history','P15-history')){11}else{2};$snapshots+=$count
    for($j=1;$j -lt $count;$j++){$null=$static.Add(('CASE-{0:000}-REPEAT-{1}' -f $i,$j))}
}
for($i=0;$i -lt 50;$i++){$null=$static.Add('STARTUP-'+$i)};$null=$static.Add('REFERENCE_GROUPS')
Assert ($rows -eq 3216 -and $snapshots -eq 499 -and $static.Count -eq 969 -and @(Compare-Object @($static) @($scope.required_static_stage_ids)).Count -eq 0 -and $scope.final_current_batch_post_cleanup_readback_required) 'STATIC_STAGE_OR_CLEANUP_POLICY_DRIFT'
foreach($key in @('limited_scope','SEM01','SEM02','PF06_supplement')){Assert ((Hash (Join-Path $repo $definition.registration_paths[$key])) -ceq $definition.registration_raw_sha256[$key]) 'REGISTRATION_HASH_DRIFT'}
$proof=Json (Join-Path $run 'external_job_identity.json');$ready=Json (Join-Path $run 'ready.json');$release=Json (Join-Path $run 'release.json');$start=Json (Join-Path $run 'job_start.json');$native=Json (Join-Path $run 'job_status.json');$accept=Json (Join-Path $run 'execution_acceptance.json')
Assert ($proof.actual_python_pid -eq 5812 -and $proof.actual_python_pid -eq $ready.pid -and $ready.pid -eq $release.actual_python_pid -and $ready.pid -eq $native.pid -and $native.pid -eq $start.pid -and $proof.target_job_name -ceq $start.job_name -and $proof.in_target_job) 'ACTUAL_JOB_PID_CHAIN'
Assert ($proof.cpu_rate -eq 2500 -and $proof.cpu_flags -eq 5 -and $proof.basic_flags -eq 8968 -and $proof.max_active_processes -eq 4 -and $proof.process_mb -eq 256 -and $proof.job_mb -eq 512 -and $start.wall_ms -eq 480000 -and $start.kill_on_close) 'RESOURCE_POLICY_DRIFT'
Assert ($native.outcome -ceq 'EXITED' -and $native.child_exitcode -eq 0 -and $native.assigned_before_resume -and $native.resumed -and $native.cleanup_complete -and $native.active_after_cleanup -eq 0 -and $accept.actual_job_verified -and $accept.cleanup_verified) 'CLEANUP_OR_ACCEPTANCE_FAILURE'
Assert ($release.external_proof_raw_sha256 -ceq (Hash (Join-Path $run 'external_job_identity.json'))) 'RELEASE_PROOF_DRIFT'
$receipts=Json (Join-Path $run 'raw_receipts.json')
Assert ($receipts.Count -eq 4) 'RAW_SET_DRIFT'
foreach($b in $receipts.GetEnumerator()){Assert ($b.Value.status -ceq 'PERSISTED' -and $b.Value.raw_sha256 -ceq (Hash (Join-Path $run $b.Key)) -and $b.Value.bytes -eq (Get-Item -LiteralPath (Join-Path $run $b.Key)).Length) 'RAW_RECEIPT_DRIFT'}
Assert ((ConvertTo-C3DeliveryCanonical $result.environment_before) -ceq (ConvertTo-C3DeliveryCanonical $result.environment_after)) 'ENVIRONMENT_DRIFT'
$lock=Json (Join-Path $package 'ENVIRONMENT_DEPENDENCY_LOCK.json')
foreach($b in $lock.GetEnumerator()){if($b.Key -ceq 'image_version'){Assert ($result.environment_before[$b.Key] -cin $b.Value) 'UNAPPROVED_IMAGE'}else{Assert ((ConvertTo-C3DeliveryCanonical $result.environment_before[$b.Key]) -ceq (ConvertTo-C3DeliveryCanonical $b.Value)) 'ENVIRONMENT_LOCK_DRIFT'}}
$sheet=Get-Content -LiteralPath (Join-Path $package 'USER_APPROVAL_DECISION_SHEET.md') -Raw
foreach($text in @($commit,$control.proposal_raw_sha256,$control.proposal_canonical_sha256,$definition.candidate_sha256,(Hash (Join-Path $package 'EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json')),'EXECUTABLE_FREEZE_USER_APPROVED=NO','C3_C_FORMAL_EXECUTION_AUTHORIZED=NO','历史49/50','strict P1 B/C仍INCOMPLETE')){Assert ($sheet.Contains($text)) 'SIGNATURE_SHEET_BINDING_DRIFT'}
$evidence=@{schema='m1-c3c-v5-independent-final-closure-readback-v1';status='READY_FOR_USER_SIGNATURE';run='38761086285';artifact_id=11986085927;artifact_sha256=(Hash $zip);artifact_bytes=134490;source_commit=$commit;proposal_raw_sha256=$control.proposal_raw_sha256;proposal_canonical_sha256=$canon;source_bindings=836;local_source_bindings=$local;bundle_source_bindings=$fromBundle;inputs=101;rows=$rows;planned_snapshots=$snapshots;required_static_stages=969;refusal_checks=9;raw_captures_verified=4;actual_python_pid=$proof.actual_python_pid;cpu_rate=2500;process_mb=256;job_mb=512;wall_ms=480000;cleanup_complete=$true;active_after_cleanup=0;environment_before=$result.environment_before;environment_after=$result.environment_after;candidate_imported=$false;formal_execution=$false;approval_generated=$false;signature_sheet_raw_sha256=(Hash (Join-Path $package 'USER_APPROVAL_DECISION_SHEET.md'));attestation_raw_sha256=(Hash (Join-Path $package 'EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json'));official_entries=$entries}
$output=Join-Path $base 'independent_readback.json'
Assert (-not (Test-Path -LiteralPath $output)) 'NO_READBACK_OVERWRITE'
$bytes=[Text.Encoding]::UTF8.GetBytes((ConvertTo-C3DeliveryCanonical $evidence)+"`n")
$file=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
Assert ((Hash $output) -ceq (Get-C3DeliverySha $bytes)) 'INDEPENDENT_EVIDENCE_PERSISTENCE'
[pscustomobject]@{status=$evidence.status;entries=$entries.Count;source_bindings=836;raw_captures=4;actual_python_pid=$proof.actual_python_pid;image=$result.environment_before.image_version;signature_sheet_raw=$evidence.signature_sheet_raw_sha256;attestation_raw=$evidence.attestation_raw_sha256;evidence_raw=(Hash $output);formal_execution=$false}|ConvertTo-Json
