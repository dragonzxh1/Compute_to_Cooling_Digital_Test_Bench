# New DEVELOPMENT read-only hypothesis proof. NO candidate/Python/native child.
param([Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedControlSha256)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or
   $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'DELIVERY_READONLY_REMOTE_REQUIRED'}
if($ExpectedCommit -cnotmatch '^[a-f0-9]{40}$' -or $env:GITHUB_SHA -cne $ExpectedCommit -or
   (git -C $repo rev-parse HEAD) -cne $ExpectedCommit){throw 'DELIVERY_READONLY_SOURCE_COMMIT'}
$controlPath=Join-Path $PSScriptRoot 'readonly_control.json'
if((Get-FileHash -LiteralPath $controlPath).Hash.ToLowerInvariant() -cne $ExpectedControlSha256){throw 'DELIVERY_READONLY_CONTROL_DRIFT'}
$control=Get-Content -Raw -LiteralPath $controlPath|ConvertFrom-Json -AsHashtable
foreach($pair in $control.source_hashes.GetEnumerator()) {
    if((Get-FileHash -LiteralPath (Join-Path $repo $pair.Key)).Hash.ToLowerInvariant() -cne $pair.Value){throw ('DELIVERY_REVIEW_SOURCE_DRIFT: '+$pair.Key)}
}
if($control.scope -cne 'DEVELOPMENT_READONLY_EVIDENCE_TRANSPORT' -or $control.candidate_execution_authorized -or
   $control.formal_execution_authorized){throw 'DELIVERY_READONLY_SCOPE_DENIED'}
$proposalPath=Join-Path $repo $control.baseline_proposal.path
if((Get-FileHash -LiteralPath $proposalPath).Hash.ToLowerInvariant() -cne $control.baseline_proposal.raw_sha256){throw 'DELIVERY_BASELINE_PACKAGE_DRIFT'}
$proposal=Get-Content -Raw -LiteralPath $proposalPath|ConvertFrom-Json -AsHashtable
$bundle=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $proposal.bundle_path))
$hashAlgorithm=[Security.Cryptography.SHA256]::Create()
try{foreach($pair in $proposal.source_raw_sha256.GetEnumerator()) {
    $path=Join-Path $repo $pair.Key
    if(Test-Path -LiteralPath $path){$got=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    else {
        $entry=$bundle.GetEntry($pair.Key);if($null -eq $entry){throw 'DELIVERY_FROZEN_SOURCE_MISSING'}
        $stream=$entry.Open();try{$got=[Convert]::ToHexString($hashAlgorithm.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
    }
    if($got -cne $pair.Value){throw ('DELIVERY_PROTECTED_SOURCE_DRIFT: '+$pair.Key)}
}}finally{$bundle.Dispose();$hashAlgorithm.Dispose()}
. (Join-Path $PSScriptRoot 'native_closure.ps1')
$root=Join-Path $repo ('artifacts/m1-c3c-delivery-v4/'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT)
if(Test-Path -LiteralPath $root){throw 'DELIVERY_FRESH_REVIEW_ROOT_REQUIRED'}
New-Item -ItemType Directory -Path $root|Out-Null
$cache=Join-Path $env:RUNNER_TEMP ('c3c-delivery-zips-'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT)
if(Test-Path -LiteralPath $cache){throw 'DELIVERY_FRESH_CACHE_REQUIRED'}
New-Item -ItemType Directory -Path $cache|Out-Null
function Save-Json([string]$Name,$Value) {
    $path=Join-Path $root $Name
    $bytes=[Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 50))
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Mark([string]$Event,[string]$Name) {
    $bytes=[Text.Encoding]::UTF8.GetBytes((@{utc=[DateTime]::UtcNow.ToString('o');event=$Event;name=$Name}|ConvertTo-Json -Compress)+"`n")
    $stream=[IO.File]::Open((Join-Path $root 'progress.jsonl'),[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    Write-Host ($Event+' '+$Name)
}
$downloads=[Collections.Generic.List[object]]::new()
try {
    & (Join-Path $PSScriptRoot 'test_native_closure.ps1') -OutputPath (Join-Path $root 'synthetic_tests.json') | Out-Null
    $sourceRun=$control.baseline_run_id
    $api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/'+$sourceRun
    $runRaw=gh api $api
    if($LASTEXITCODE -ne 0){throw 'DELIVERY_SOURCE_RUN_API_FAILED'}
    $sourceRunRecord=($runRaw -join "`n")|ConvertFrom-Json -AsHashtable
    if($sourceRunRecord.head_sha -cne $control.baseline_source_commit -or $sourceRunRecord.status -cne 'completed' -or
       $sourceRunRecord.run_attempt -ne 1 -or $sourceRunRecord.conclusion -cne 'failure'){throw 'DELIVERY_FAILED_HISTORY_IDENTITY_REQUIRED'}
    Save-Json 'original_run.json' $sourceRunRecord
    $pagesRaw=gh api --paginate --slurp ($api+'/artifacts?per_page=100')
    if($LASTEXITCODE -ne 0){throw 'DELIVERY_SOURCE_ARTIFACT_API_FAILED'}
    $pages=($pagesRaw -join "`n")|ConvertFrom-Json -AsHashtable
    $artifacts=@($pages|ForEach-Object {$_.artifacts})
    Save-Json 'official_artifact_inventory.json' $artifacts
    $names=@('final','reference-gate')+@(0..9|ForEach-Object {'ref-'+$_})+@(0..10|ForEach-Object {'select-'+$_})+@('split-u')+@(0..9|ForEach-Object {'split-'+$_})+@(0..100|ForEach-Object {'prefix-'+$_})
    if($names.Count -ne 135 -or ($names|Select-Object -Unique).Count -ne 135){throw 'DELIVERY_PLANNED_ARTIFACT_COUNT'}
    $inventories=[Collections.Generic.List[object]]::new()
    foreach($name in $names) {
        $artifactMatches=@($artifacts|Where-Object {$_.name -ceq $name})
        if($artifactMatches.Count -ne 1 -or $artifactMatches[0].expired -or $artifactMatches[0].digest -cnotmatch '^sha256:[a-f0-9]{64}$'){throw ('DELIVERY_OFFICIAL_ARTIFACT_NOT_UNIQUE: '+$name)}
        $artifact=$artifactMatches[0];$sha=$artifact.digest.Substring(7)
        if($name -ceq 'final' -and $sha -cne $control.baseline_final_artifact.sha256){throw 'DELIVERY_ORIGINAL_FINAL_DIGEST_DRIFT'}
        $partial=Join-Path $cache ($name+'.partial.zip');$complete=Join-Path $cache ($name+'.zip')
        Mark 'DOWNLOAD_BEGIN' $name
        # Token is inherited by curl as a header, never echoed. No tracing.
        $token=$env:GH_TOKEN
        curl.exe --fail --silent --show-error --location --max-time 600 --header "Authorization: Bearer $token" --header 'Accept: application/vnd.github+json' --output $partial ('https://api.github.com/repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/artifacts/'+$artifact.id+'/zip')
        $token=$null
        if($LASTEXITCODE -ne 0){throw ('DELIVERY_OFFICIAL_DOWNLOAD_FAILED: '+$name)}
        if((Get-Item -LiteralPath $partial).Length -ne $artifact.size_in_bytes -or
           (Get-FileHash -LiteralPath $partial).Hash.ToLowerInvariant() -cne $sha){throw 'DELIVERY_DOWNLOADED_ARTIFACT_DRIFT'}
        Move-Item -LiteralPath $partial -Destination $complete
        $downloads.Add(@{name=$name;artifact_id=$artifact.id;sha256=$sha;bytes=$artifact.size_in_bytes})
        $options=@{Path=$complete;ExpectedSha256=$sha;RunId=$sourceRun;CaptureStageProofs=$true}
        if($name -ceq 'final'){$options.QuarantineJobs=@('final')}
        $inventory=Read-C3NativeZip @options
        $inventories.Add($inventory)
        Mark 'DOWNLOAD_HASHED_NATIVE_INVENTORIED' $name
    }
    Save-Json 'download_receipts.json' @($downloads.ToArray())
    $registryPath=Join-Path $repo $proposal.registration_paths.limited_scope
    if((Get-FileHash -LiteralPath $registryPath).Hash.ToLowerInvariant() -cne $proposal.registration_raw_sha256.limited_scope){throw 'DELIVERY_STATIC_REGISTRATION_DRIFT'}
    $registry=Get-Content -Raw -LiteralPath $registryPath|ConvertFrom-Json -AsHashtable
    $lockPath=Join-Path $repo $proposal.execution.environment_lock
    $lock=Get-Content -Raw -LiteralPath $lockPath|ConvertFrom-Json -AsHashtable
    $identity=$control.baseline_execution_identity
    $coverageArguments=@{RequiredStageIds=$registry.required_static_stage_ids;SourceCommit=$control.baseline_source_commit;PackageSha256=$control.baseline_proposal.raw_sha256;RunId=$sourceRun}
    $baseline=Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($inventories[0])) @coverageArguments
    Save-Json 'original_missing_coverage.json' $baseline
    if($baseline.missing_count -ne 802 -or $baseline.unique_stage_ids -ne 167){throw 'DELIVERY_ORIGINAL_FAILURE_NOT_REPRODUCED'}
    Mark 'BASELINE_REPRODUCED' '802 missing static stages'
    $merged=Merge-C3NativeEvidence @($inventories.ToArray())
    Mark 'VERIFY_ALL_NATIVE_PROOFS_BEGIN' ([string]$merged.batches.Count)
    $corrected=Test-C3NativeCoverage -Merged $merged @coverageArguments -VerifyStageProofs -ExpectedExecutionIdentity $identity -EnvironmentLock $lock
    Save-Json 'corrected_native_coverage.json' $corrected
    if($corrected.missing_count -ne 0){throw 'DELIVERY_CORRECTED_STATIC_COVERAGE_INCOMPLETE'}
    Mark 'VERIFY_ALL_NATIVE_PROOFS_PASS' ([string]$corrected.stage_proofs_verified)
    Export-C3NativeEvidence -Merged $merged -Destination (Join-Path $root 'future_delivery_transport_sample')
    $fileManifest=@(foreach($pair in $merged.files.GetEnumerator()){@{path=$pair.Key;sha256=$pair.Value.sha256;bytes=$pair.Value.bytes}})|Sort-Object path
    Save-Json 'native_file_hash_inventory.json' $fileManifest
    $inventoryHash=(Get-FileHash -LiteralPath (Join-Path $root 'native_file_hash_inventory.json')).Hash.ToLowerInvariant()
    Save-Json 'result.json' @{
        schema='m1-c3c-delivery-v4-readonly-proof-v1';status='DEVELOPMENT_READONLY_NATIVE_CLOSURE_VALIDATED'
        source_commit=$ExpectedCommit;control_raw_sha256=$ExpectedControlSha256
        baseline_run_id=$sourceRun;baseline_run_reclassified=$false;baseline_formal_gate='INVALID_C3_C_EXECUTION'
        original_missing_count=802;corrected_missing_count=0;original_aggregate_formal_pass=$false
        synthetic_test_count=(Get-Content -Raw -LiteralPath (Join-Path $root 'synthetic_tests.json')|ConvertFrom-Json).count
        official_archives_verified=$downloads.Count;native_stage_proofs_verified=$corrected.stage_proofs_verified
        raw_captures_verified=$corrected.raw_captures_verified;native_file_hash_inventory_sha256=$inventoryHash
        protected_source_bindings_verified=$proposal.source_raw_sha256.Count
        candidate_imported=$false;candidate_executed=$false;python_or_native_child_executed=$false
        formal_execution_authorized=$false;production_hardware_phase6_authorized=$false
        quarantined_original_final_failure=$true;full_frames_schema_repeats_re_adjudicated=$false
        limits='Read-only original evidence transport proof, not formal requalification or candidate score. No frozen outcome is rewritten.'
    }
    Mark 'COMPLETE' 'read-only transport proof, not formal PASS'
} catch {
    $errorText=$_.Exception.Message
    Mark 'STOP' $errorText
    if(!(Test-Path -LiteralPath (Join-Path $root 'download_receipts.json'))){Save-Json 'download_receipts.json' @($downloads.ToArray())}
    Save-Json 'failed_review.json' @{status='INVALID_READONLY_DELIVERY_PROOF';error=$errorText;candidate_executed=$false;formal_execution_executed=$false;no_original_execution_retry=$true}
    throw
}
