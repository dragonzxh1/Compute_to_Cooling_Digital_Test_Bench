# Tiny synthetic ZIP/JSON regression checks only; no Python/native/model child.
param([string]$OutputPath)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'native_closure.ps1')
$taskTestRoot=Join-Path ([IO.Path]::GetTempPath()) ('c3c-delivery-test-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTestRoot|Out-Null
$taskTestResults=[Collections.Generic.List[object]]::new()
$taskIdentity=@{scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN';execution_source_commit=('a'*40);package_raw_sha256=('b'*64);candidate_sha256=('c'*64);approval_receipt_raw_sha256=('d'*64);authorization_raw_sha256=('e'*64)}
$taskLock=@{python='3.11.9';image_version=@('20261004.326.1','20261012.333.1')}

function New-TestArchive([string]$Name,[Collections.IDictionary]$Entries) {
    $path=Join-Path $taskTestRoot ($Name+'.zip')
    $zip=[IO.Compression.ZipFile]::Open($path,[IO.Compression.ZipArchiveMode]::Create)
    try{foreach($pair in $Entries.GetEnumerator()) {
        $entry=$zip.CreateEntry($pair.Key);$stream=$entry.Open()
        try{$bytes=[Text.Encoding]::UTF8.GetBytes([string]$pair.Value);$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    }}finally{$zip.Dispose()}
    return @{path=$path;sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
}

function New-TestBatch([string]$Job,[string]$Stage) {
    $base='liquid-recovery-v1/stream-123-1/'+$Job+'/'
    $folder=$base+$Stage+'/'
    $proof=@{actual_python_pid=7;in_target_job=$true;target_job_name='test-job';cpu_rate=2500;cpu_flags=5;basic_flags=8968;max_active_processes=4;process_mb=1024;job_mb=2048}
    $proofRaw=ConvertTo-C3DeliveryCanonical $proof
    $environment=@{python='3.11.9';image_version='20261004.326.1'}
    $result=@{stage_id=$Stage;status='PASS';github_run_id='123';github_run_attempt='1';execution_identity=$taskIdentity;runtime_identity_before=$environment;runtime_identity_after=$environment}
    $start=@{pid=7;job_name='test-job';wall_ms=480000;kill_on_close=$true}
    $native=@{outcome='EXITED';child_exitcode=0;cleanup_complete=$true;active_after_cleanup=0;assigned_before_resume=$true;resumed=$true;pid=7}
    $raw=@{};$files=@{}
    foreach($name in @('stdout.raw','stderr.raw','verify_stdout.raw','verify_stderr.raw')) {
        $files[$folder+$name]='';$raw[$name]=@{status='PERSISTED';raw_sha256=(Get-C3DeliverySha ([byte[]]@()))}
    }
    foreach($pair in @{ 'job_start.json'=$start;'job_status.json'=$native;'external_job_identity.json'=$proof;'ready.json'=@{pid=7};'release.json'=@{actual_python_pid=7;external_proof_raw_sha256=(Get-C3DeliverySha ([Text.Encoding]::UTF8.GetBytes($proofRaw)))};'result.json'=$result;'raw_evidence_receipts.json'=$raw }.GetEnumerator()) {
        $files[$folder+$pair.Key]=ConvertTo-C3DeliveryCanonical $pair.Value
    }
    $outer='{"passed":true}'
    $files[$base+'stage-000-result.json']=$outer
    $files[$base+'batch_complete.json']=ConvertTo-C3DeliveryCanonical @{
        status='COMPLETE';scope=$taskIdentity.scope;formal_execution_authorized=$true;execution_identity=$taskIdentity
        stages=@(@{stage_id=$Stage;status='PASS'});receipts=@(@{stage_id=$Stage;result_raw_sha256=(Get-C3DeliverySha ([Text.Encoding]::UTF8.GetBytes($outer)))})
    }
    return $files
}

function Check([string]$Name,[scriptblock]$Action,[string]$ExpectedError='') {
    try {
        $null=& $Action
        if($ExpectedError){throw 'TEST_EXPECTED_REJECTION_NOT_RAISED'}
        $taskTestResults.Add(@{id=$Name;status='PASS'})
    } catch {
        if($ExpectedError -and $_.Exception.Message -like ($ExpectedError+'*')){$taskTestResults.Add(@{id=$Name;status='PASS'});return}
        throw ('TEST_FAIL '+$Name+': '+$_.Exception.Message)
    }
}

$taskRefEntries=New-TestBatch 'ref-0' 'CASE-001-REFERENCE'
$taskSchemaEntries=New-TestBatch 'schema-1' 'CASE-001-SCHEMA'
$taskRef=New-TestArchive 'reference' $taskRefEntries
$taskSchema=New-TestArchive 'schema' $taskSchemaEntries
$taskRefInv=Read-C3NativeZip -Path $taskRef.path -ExpectedSha256 $taskRef.sha256 -RunId '123'
$taskSchemaInv=Read-C3NativeZip -Path $taskSchema.path -ExpectedSha256 $taskSchema.sha256 -RunId '123'
$taskRequired=@('CASE-001-REFERENCE','CASE-001-SCHEMA')

Check 'OLD_OWNED_EXPORT_REPRODUCES_MISSING_STAGE' {
    $merged=Merge-C3NativeEvidence -Inventories @($taskSchemaInv)
    $got=Test-C3NativeCoverage -Merged $merged -RequiredStageIds $taskRequired -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123'
    if($got.missing_count -ne 1 -or $got.missing_ids[0] -cne 'CASE-001-REFERENCE'){throw 'Wrong old-export counterexample'}
}
Check 'EXPLICIT_UPSTREAM_MERGE_COMPLETE_WITH_ORIGINAL_PROOFS' {
    $merged=Merge-C3NativeEvidence -Inventories @($taskSchemaInv,$taskRefInv)
    $got=Test-C3NativeCoverage -Merged $merged -RequiredStageIds $taskRequired -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123' -VerifyStageProofs -ExpectedExecutionIdentity $taskIdentity -EnvironmentLock $taskLock
    if($got.missing_count -ne 0 -or $got.stage_proofs_verified -ne 2 -or $got.raw_captures_verified -ne 8){throw 'Incorrect merged proof result'}
}
Check 'BYTE_IDENTICAL_DUPLICATES_ARE_DETERMINISTIC' {
    $merged=Merge-C3NativeEvidence -Inventories @($taskRefInv,$taskRefInv)
    if($merged.batches.Count -ne 1 -or $merged.files.Count -ne $taskRefInv.files.Count){throw 'Duplicate incorrectly counted'}
}
Check 'WRONG_ZIP_HASH_REJECTED' {Read-C3NativeZip -Path $taskRef.path -ExpectedSha256 ('f'*64) -RunId '123'} 'DELIVERY_ZIP_DIGEST_MISMATCH'
Check 'FOREIGN_RUN_REJECTED' {Read-C3NativeZip -Path $taskRef.path -ExpectedSha256 $taskRef.sha256 -RunId '124'} 'DELIVERY_FOREIGN_RUN_NATIVE_EVIDENCE'
Check 'CONFLICTING_UPSTREAM_BYTES_REJECTED' {
    $bad=$taskRefEntries.Clone();$bad['liquid-recovery-v1/stream-123-1/ref-0/CASE-001-REFERENCE/stdout.raw']='corrupted'
    $zip=New-TestArchive 'conflicting' $bad
    $inv=Read-C3NativeZip -Path $zip.path -ExpectedSha256 $zip.sha256 -RunId '123'
    Merge-C3NativeEvidence -Inventories @($taskRefInv,$inv)
} 'DELIVERY_CONFLICTING_BYTES'
Check 'CHANGED_RAW_CAPTURE_REJECTED' {
    $bad=$taskRefEntries.Clone();$bad['liquid-recovery-v1/stream-123-1/ref-0/CASE-001-REFERENCE/stdout.raw']='changed'
    $zip=New-TestArchive 'raw-change' $bad;$inv=Read-C3NativeZip -Path $zip.path -ExpectedSha256 $zip.sha256 -RunId '123'
    Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($inv)) -RequiredStageIds @('CASE-001-REFERENCE') -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123' -VerifyStageProofs -ExpectedExecutionIdentity $taskIdentity -EnvironmentLock $taskLock
} 'DELIVERY_RAW_CAPTURE_HASH'
Check 'PATH_ESCAPE_REJECTED' {
    $zip=New-TestArchive 'escape' @{'../outside.txt'='bad'}
    Read-C3NativeZip -Path $zip.path -ExpectedSha256 $zip.sha256 -RunId '123'
} 'DELIVERY_ARCHIVE_PATH_ESCAPE'
Check 'SOURCE_COMMIT_DRIFT_REJECTED' {
    Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($taskRefInv)) -RequiredStageIds @('CASE-001-REFERENCE') -SourceCommit ('f'*40) -PackageSha256 ('b'*64) -RunId '123'
} 'DELIVERY_BATCH_AUTHORITY_MISMATCH'
Check 'MISSING_PROOF_LOCK_REJECTED' {
    Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($taskRefInv)) -RequiredStageIds @('CASE-001-REFERENCE') -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123' -VerifyStageProofs
} 'DELIVERY_PROOF_AUTHORITY_LOCK_REQUIRED'
Check 'NEW_EXPORT_PRESERVES_EVERY_NATIVE_BYTE' {
    $merged=Merge-C3NativeEvidence @($taskSchemaInv,$taskRefInv)
    $destination=Join-Path $taskTestRoot 'future-execution-only'
    Export-C3NativeEvidence -Merged $merged -Destination $destination
    foreach($pair in $merged.files.GetEnumerator()) {
        if((Get-FileHash -LiteralPath (Join-Path $destination $pair.Key)).Hash.ToLowerInvariant() -cne $pair.Value.sha256){throw 'Export bytes changed'}
    }
}
Check 'EXISTING_EXPORT_DESTINATION_REJECTED' {
    Export-C3NativeEvidence -Merged (Merge-C3NativeEvidence @($taskRefInv)) -Destination (Join-Path $taskTestRoot 'future-execution-only')
} 'DELIVERY_FRESH_DESTINATION_REQUIRED'

function Check-BadProof([string]$Name,[string]$File,[scriptblock]$Change,[string]$ErrorId) {
    Check $Name {
        $bad=$taskRefEntries.Clone();$key='liquid-recovery-v1/stream-123-1/ref-0/CASE-001-REFERENCE/'+$File
        $value=$bad[$key]|ConvertFrom-Json -AsHashtable
        & $Change $value
        $bad[$key]=ConvertTo-C3DeliveryCanonical $value
        $zip=New-TestArchive $Name $bad
        $inv=Read-C3NativeZip -Path $zip.path -ExpectedSha256 $zip.sha256 -RunId '123' -CaptureStageProofs
        Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($inv)) -RequiredStageIds @('CASE-001-REFERENCE') -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123' -VerifyStageProofs -ExpectedExecutionIdentity $taskIdentity -EnvironmentLock $taskLock
    } $ErrorId
}
Check-BadProof 'WRONG_ACTUAL_PYTHON_PID_REJECTED' 'ready.json' {param($v) $v.pid=8} 'DELIVERY_ACTUAL_JOB_OR_CLEANUP'
Check-BadProof 'INCOMPLETE_CLEANUP_REJECTED' 'job_status.json' {param($v) $v.active_after_cleanup=1} 'DELIVERY_ACTUAL_JOB_OR_CLEANUP'
Check-BadProof 'UNAPPROVED_IMAGE_REJECTED' 'result.json' {
    param($v) $v.runtime_identity_before.image_version='unknown';$v.runtime_identity_after.image_version='unknown'
} 'DELIVERY_UNKNOWN_ENVIRONMENT_IMAGE'
Check-BadProof 'ENVIRONMENT_BEFORE_AFTER_DRIFT_REJECTED' 'result.json' {param($v) $v.runtime_identity_after.python='3.12.0'} 'DELIVERY_STAGE_IDENTITY_DRIFT'
Check-BadProof 'WRONG_JOB_RESOURCE_LIMIT_REJECTED' 'job_start.json' {param($v) $v.wall_ms=999999} 'DELIVERY_RESOURCE_POLICY_DRIFT'
Check 'MISSING_OUTER_RECEIPT_REJECTED' {
    $bad=$taskRefEntries.Clone();$bad.Remove('liquid-recovery-v1/stream-123-1/ref-0/stage-000-result.json')
    $zip=New-TestArchive 'missing-outer' $bad;$inv=Read-C3NativeZip -Path $zip.path -ExpectedSha256 $zip.sha256 -RunId '123'
    Test-C3NativeCoverage -Merged (Merge-C3NativeEvidence @($inv)) -RequiredStageIds @('CASE-001-REFERENCE') -SourceCommit ('a'*40) -PackageSha256 ('b'*64) -RunId '123'
} 'DELIVERY_OUTER_RECEIPT_DRIFT'

$taskReport=@{schema='c3c-native-closure-synthetic-tests-v1';status='PASS';tests=@($taskTestResults.ToArray());count=$taskTestResults.Count;candidate_executed=$false;python_or_native_child_executed=$false;temporary_fixture_directory=$taskTestRoot}
if($OutputPath){if(Test-Path -LiteralPath $OutputPath){throw 'TEST_REPORT_FRESH_PATH_REQUIRED'};[IO.File]::WriteAllText($OutputPath,($taskReport|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))}
$taskReport|ConvertTo-Json -Depth 12
