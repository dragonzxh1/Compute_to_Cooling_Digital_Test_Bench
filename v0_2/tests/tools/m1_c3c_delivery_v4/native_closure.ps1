# Evidence transport only. Never imports or executes candidate/model code.
Set-StrictMode -Version Latest

function Get-C3DeliverySha([byte[]]$Bytes) {
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant()
}

function ConvertTo-C3DeliveryCanonical($Value) {
    if($null -eq $Value){return 'null'}
    if($Value -is [Collections.IDictionary]) {
        $keys=[string[]]@($Value.Keys);[Array]::Sort($keys,[StringComparer]::Ordinal)
        $parts=@(foreach($key in $keys){(ConvertTo-Json -InputObject $key -Compress)+':'+(ConvertTo-C3DeliveryCanonical $Value[$key])})
        return '{'+[string]::Join(',',$parts)+'}'
    }
    if($Value -is [Array] -or $Value -is [Collections.IList]) {
        return '['+[string]::Join(',',@(foreach($item in $Value){ConvertTo-C3DeliveryCanonical $item}))+']'
    }
    return (ConvertTo-Json -InputObject $Value -Compress)
}

function Read-C3NativeZip {
    param([Parameter(Mandatory)][string]$Path,
          [Parameter(Mandatory)][string]$ExpectedSha256,
          [Parameter(Mandatory)][string]$RunId,
          [string[]]$QuarantineJobs=@(),[switch]$CaptureStageProofs)
    if($ExpectedSha256 -cnotmatch '^[a-f0-9]{64}$' -or $RunId -cnotmatch '^\d+$'){throw 'DELIVERY_BAD_IDENTITY'}
    $actual=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if($actual -cne $ExpectedSha256){throw 'DELIVERY_ZIP_DIGEST_MISMATCH'}
    $archive=[IO.Compression.ZipFile]::OpenRead($Path)
    $files=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $caseNames=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $batches=[Collections.Generic.List[object]]::new()
    $quarantined=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $prefix='liquid-recovery-v1/stream-'+$RunId+'-1/'
    $hasher=[Security.Cryptography.SHA256]::Create()
    try {
        foreach($entry in $archive.Entries) {
            $name=$entry.FullName
            if($name -match '(^[/\\]|:|\\|(^|/)\.\.(/|$))'){throw 'DELIVERY_ARCHIVE_PATH_ESCAPE'}
            if($name.EndsWith('/')){continue}
            if(!$caseNames.Add($name)){throw 'DELIVERY_DUPLICATE_ARCHIVE_PATH'}
            if(!$name.StartsWith('liquid-recovery-v1/',[StringComparison]::Ordinal)){continue}
            if(!$name.StartsWith($prefix,[StringComparison]::Ordinal)){throw 'DELIVERY_FOREIGN_RUN_NATIVE_EVIDENCE'}
            $relative=$name.Substring($prefix.Length)
            $job=$relative.Split('/')[0]
            if($job -cin $QuarantineJobs){$null=$quarantined.Add($job);continue}
            if($job -cnotmatch '^(prepare|reference-gate|ref-\d+|select-\d+|split-u|split-\d+|prefix-\d+|schema-\d+|startup-\d+)(-batch-\d+)?$'){
                throw ('DELIVERY_UNREGISTERED_JOB_PATH: '+$job)
            }
            $stream=$entry.Open()
            try{$hash=[Convert]::ToHexString($hasher.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose()}
            $files.Add($name,@{sha256=$hash;bytes=$entry.Length;archive=$Path;entry=$name})
            if($CaptureStageProofs -and [IO.Path]::GetFileName($name) -cin @('job_start.json','job_status.json','external_job_identity.json','ready.json','release.json','result.json','raw_evidence_receipts.json')) {
                if($entry.Length -gt 8388608){throw 'DELIVERY_JSON_METADATA_OVERSIZED'}
                $reader=[IO.StreamReader]::new($entry.Open())
                try{$files[$name].json_value=$reader.ReadToEnd()|ConvertFrom-Json -AsHashtable}finally{$reader.Dispose()}
            }
            if($name.EndsWith('/batch_stop.json',[StringComparison]::Ordinal)){throw 'DELIVERY_UPSTREAM_STOPPED'}
            if($name.EndsWith('/batch_complete.json',[StringComparison]::Ordinal)) {
                if($entry.Length -gt 4194304){throw 'DELIVERY_BATCH_METADATA_OVERSIZED'}
                $reader=[IO.StreamReader]::new($entry.Open())
                try{$record=$reader.ReadToEnd()|ConvertFrom-Json -AsHashtable}finally{$reader.Dispose()}
                $batches.Add(@{path=$name;sha256=$hash;record=$record})
            }
        }
    } finally {$hasher.Dispose();$archive.Dispose()}
    return @{archive=$Path;archive_sha256=$actual;files=$files;batches=$batches;quarantined_jobs=@($quarantined)}
}

function Read-C3DeliveryJson($Item) {
    if($Item.ContainsKey('json_value')){return $Item.json_value}
    if($Item.bytes -gt 8388608){throw 'DELIVERY_JSON_METADATA_OVERSIZED'}
    $archive=[IO.Compression.ZipFile]::OpenRead($Item.archive)
    try {
        $entry=$archive.GetEntry($Item.entry)
        $reader=[IO.StreamReader]::new($entry.Open())
        try{return ($reader.ReadToEnd()|ConvertFrom-Json -AsHashtable)}finally{$reader.Dispose()}
    } finally {$archive.Dispose()}
}

function Merge-C3NativeEvidence {
    param([Parameter(Mandatory)][object[]]$Inventories)
    $files=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $caseNames=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $batches=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach($inventory in $Inventories) {
        foreach($pair in $inventory.files.GetEnumerator()) {
            if($caseNames.ContainsKey($pair.Key) -and $caseNames[$pair.Key] -cne $pair.Key){throw 'DELIVERY_CASE_COLLISION'}
            $caseNames[$pair.Key]=$pair.Key
            if($files.ContainsKey($pair.Key)) {
                if($files[$pair.Key].sha256 -cne $pair.Value.sha256 -or $files[$pair.Key].bytes -ne $pair.Value.bytes){
                    throw ('DELIVERY_CONFLICTING_BYTES: '+$pair.Key)
                }
            } else {$files.Add($pair.Key,$pair.Value)}
        }
        foreach($batch in $inventory.batches) {
            if($batches.ContainsKey($batch.path) -and $batches[$batch.path].sha256 -cne $batch.sha256){throw 'DELIVERY_CONFLICTING_BATCH'}
            $batches[$batch.path]=$batch
        }
    }
    return @{files=$files;batches=$batches}
}

function Test-C3NativeCoverage {
    param([Parameter(Mandatory)]$Merged,[Parameter(Mandatory)][string[]]$RequiredStageIds,
          [Parameter(Mandatory)][string]$SourceCommit,[Parameter(Mandatory)][string]$PackageSha256,
          [Parameter(Mandatory)][string]$RunId,[switch]$VerifyStageProofs,
          [Collections.IDictionary]$ExpectedExecutionIdentity,
          [Collections.IDictionary]$EnvironmentLock)
    if($VerifyStageProofs -and ($null -eq $ExpectedExecutionIdentity -or $null -eq $EnvironmentLock)){throw 'DELIVERY_PROOF_AUTHORITY_LOCK_REQUIRED'}
    $actual=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $stageCount=0;$captures=0;$proofs=0
    foreach($batch in $Merged.batches.Values) {
        $record=$batch.record
        if($record.status -cne 'COMPLETE' -or !$record.formal_execution_authorized -or
           $record.scope -cne 'M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN' -or
           $record.execution_identity.execution_source_commit -cne $SourceCommit -or
           $record.execution_identity.package_raw_sha256 -cne $PackageSha256){throw 'DELIVERY_BATCH_AUTHORITY_MISMATCH'}
        if($null -ne $ExpectedExecutionIdentity -and
           (ConvertTo-C3DeliveryCanonical $record.execution_identity) -cne
           (ConvertTo-C3DeliveryCanonical $ExpectedExecutionIdentity)){throw 'DELIVERY_BATCH_FULL_AUTHORITY_MISMATCH'}
        if($record.stages.Count -ne $record.receipts.Count){throw 'DELIVERY_BATCH_RECEIPT_COUNT'}
        $base=$batch.path.Substring(0,$batch.path.LastIndexOf('/')+1)
        for($index=0;$index -lt $record.stages.Count;$index++) {
            $stage=$record.stages[$index];$receipt=$record.receipts[$index]
            if($stage.status -cne 'PASS' -or $stage.stage_id -cne $receipt.stage_id){throw 'DELIVERY_NONPASS_OR_STAGE_ID_MISMATCH'}
            $outer=$base+('stage-{0:d3}-result.json' -f $index)
            if(!$Merged.files.ContainsKey($outer) -or $Merged.files[$outer].sha256 -cne $receipt.result_raw_sha256){throw 'DELIVERY_OUTER_RECEIPT_DRIFT'}
            $null=$actual.Add($stage.stage_id);$stageCount++
            if(!$VerifyStageProofs){continue}
            $folder=$base+$stage.stage_id+'/'
            $required=@('job_start.json','job_status.json','external_job_identity.json','ready.json','release.json','result.json','raw_evidence_receipts.json')
            foreach($file in $required){if(!$Merged.files.ContainsKey($folder+$file)){throw ('DELIVERY_STAGE_FILE_MISSING: '+$folder+$file)}}
            $start=Read-C3DeliveryJson $Merged.files[$folder+'job_start.json']
            $native=Read-C3DeliveryJson $Merged.files[$folder+'job_status.json']
            $proof=Read-C3DeliveryJson $Merged.files[$folder+'external_job_identity.json']
            $ready=Read-C3DeliveryJson $Merged.files[$folder+'ready.json']
            $release=Read-C3DeliveryJson $Merged.files[$folder+'release.json']
            $result=Read-C3DeliveryJson $Merged.files[$folder+'result.json']
            $raw=Read-C3DeliveryJson $Merged.files[$folder+'raw_evidence_receipts.json']
            if($native.outcome -cne 'EXITED' -or $native.child_exitcode -ne 0 -or !$native.cleanup_complete -or
               $native.active_after_cleanup -ne 0 -or !$native.assigned_before_resume -or !$native.resumed -or
               $native.pid -ne $start.pid -or !$proof.in_target_job -or $proof.actual_python_pid -ne $ready.pid -or
               $ready.pid -ne $release.actual_python_pid -or $proof.target_job_name -cne $start.job_name){throw 'DELIVERY_ACTUAL_JOB_OR_CLEANUP'}
            if($proof.cpu_rate -ne 2500 -or $proof.cpu_flags -ne 5 -or $proof.basic_flags -ne 8968 -or
               $proof.max_active_processes -ne 4 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or
               $start.wall_ms -ne 480000 -or !$start.kill_on_close){throw 'DELIVERY_RESOURCE_POLICY_DRIFT'}
            if($release.external_proof_raw_sha256 -cne $Merged.files[$folder+'external_job_identity.json'].sha256){throw 'DELIVERY_RELEASE_PROOF_DRIFT'}
            if($result.status -cne 'PASS' -or $result.github_run_id -cne $RunId -or $result.github_run_attempt -cne '1' -or
               $result.execution_identity.execution_source_commit -cne $SourceCommit -or
               $result.execution_identity.package_raw_sha256 -cne $PackageSha256 -or
               (ConvertTo-C3DeliveryCanonical $result.execution_identity) -cne (ConvertTo-C3DeliveryCanonical $ExpectedExecutionIdentity) -or
               (ConvertTo-C3DeliveryCanonical $result.runtime_identity_before) -cne
               (ConvertTo-C3DeliveryCanonical $result.runtime_identity_after)){throw 'DELIVERY_STAGE_IDENTITY_DRIFT'}
            foreach($key in $EnvironmentLock.Keys) {
                $actualValue=$result.runtime_identity_before[$key];$expectedValue=$EnvironmentLock[$key]
                if($key -ceq 'image_version' -and $expectedValue -is [Array]) {
                    if($actualValue -cnotin $expectedValue){throw 'DELIVERY_UNKNOWN_ENVIRONMENT_IMAGE'}
                } elseif((ConvertTo-C3DeliveryCanonical $actualValue) -cne (ConvertTo-C3DeliveryCanonical $expectedValue)) {
                    throw ('DELIVERY_ENVIRONMENT_LOCK_DRIFT: '+$key)
                }
            }
            if($raw.Count -ne 4){throw 'DELIVERY_RAW_CAPTURE_COUNT'}
            foreach($name in @('stdout.raw','stderr.raw','verify_stdout.raw','verify_stderr.raw')) {
                if(!$raw.Contains($name) -or $raw[$name].status -cne 'PERSISTED' -or !$Merged.files.ContainsKey($folder+$name) -or
                   $raw[$name].raw_sha256 -cne $Merged.files[$folder+$name].sha256){throw 'DELIVERY_RAW_CAPTURE_HASH'}
                $captures++
            }
            $proofs++
        }
    }
    $missing=@($RequiredStageIds|Where-Object {!$actual.Contains($_)})
    return @{status=if($missing.Count -eq 0){'NATIVE_COVERAGE_COMPLETE_NOT_FORMAL_VERDICT'}else{'NATIVE_COVERAGE_INCOMPLETE'}
        required_static_count=$RequiredStageIds.Count;missing_ids=$missing;missing_count=$missing.Count
        completed_batches=$Merged.batches.Count;completed_stage_records=$stageCount;unique_stage_ids=$actual.Count
        stage_proofs_verified=$proofs;raw_captures_verified=$captures;stage_ids=@($actual|Sort-Object)
        candidate_executed=$false;formal_qualification_executed=$false;original_run_reclassified=$false}
}

function Export-C3NativeEvidence {
    param([Parameter(Mandatory)]$Merged,[Parameter(Mandatory)][string]$Destination)
    # New future-execution transport only. Never targets a sealed run in place.
    if(Test-Path -LiteralPath $Destination){throw 'DELIVERY_FRESH_DESTINATION_REQUIRED'}
    $root=[IO.Path]::GetFullPath($Destination)+[IO.Path]::DirectorySeparatorChar
    New-Item -ItemType Directory -Path $Destination|Out-Null
    foreach($group in ($Merged.files.GetEnumerator()|Group-Object {$_.Value.archive})) {
        $archive=[IO.Compression.ZipFile]::OpenRead($group.Name)
        try{foreach($pair in $group.Group) {
            $target=[IO.Path]::GetFullPath((Join-Path $Destination $pair.Key))
            if(!$target.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw 'DELIVERY_EXPORT_PATH_ESCAPE'}
            New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force|Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($archive.GetEntry($pair.Value.entry),$target,$false)
            if((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -cne $pair.Value.sha256){throw 'DELIVERY_EXTRACTED_BYTE_DRIFT'}
        }}finally{$archive.Dispose()}
    }
}
