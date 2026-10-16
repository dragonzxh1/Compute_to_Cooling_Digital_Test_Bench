# Read-only delivery audit of one completed run. No Python/native/model execution.
param([Parameter(Mandatory)][string]$ZipPath,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
function Assert([bool]$ok,[string]$reason){if(-not $ok){throw $reason}}
function Save([string]$name,$value){
    $path=Join-Path $OutputDirectory $name
    $bytes=[Text.Encoding]::UTF8.GetBytes(($value|ConvertTo-Json -Depth 80)+"`n")
    $s=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try{$s.Write($bytes,0,$bytes.Length);$s.Flush($true)}finally{$s.Dispose()}
}
Assert (-not(Test-Path -LiteralPath $OutputDirectory)) 'NEW_AUDIT_OUTPUT_REQUIRED'
New-Item -ItemType Directory -Path $OutputDirectory|Out-Null
$run='38833878662';$commit='9ad4b9d1fdab261db9be09b91f261a927d529970'
$packageSha='18d54940b672e4ec06b0c0c0a6691cf15219ee96e01b7864b31fe00a1adf23c8'
$zipSha='bc8a49397e10415d157260c21e4d2869f3ace4065600a22aeb6da96a2140c293'
Assert ((Get-Item -LiteralPath $ZipPath).Length -eq 2011688990) 'OFFICIAL_ZIP_LENGTH'
Assert ((Get-FileHash -LiteralPath $ZipPath).Hash.ToLowerInvariant() -ceq $zipSha) 'OFFICIAL_ZIP_SHA'
$definition=Get-Content -Raw -LiteralPath (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json')|ConvertFrom-Json -AsHashtable
Assert ((Get-FileHash -LiteralPath (Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json')).Hash.ToLowerInvariant() -ceq $packageSha) 'PROPOSAL_DRIFT'
$identity=@{scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN';package_raw_sha256=$packageSha;approval_receipt_raw_sha256='1d5ac4f01fcc6f7a11b35d29c00e0241a31a2feeac038cac92f8abbfb3555def';authorization_raw_sha256='76ad4f5817d625e05a5b9a9a96afde9c4ffb4375a699dc65a84fc14153b69493';candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce';execution_source_commit=$commit}
$lock=Get-Content -Raw -LiteralPath (Join-Path $repo $definition.execution.environment_lock)|ConvertFrom-Json -AsHashtable
$scope=Get-Content -Raw -LiteralPath (Join-Path $repo $definition.registration_paths.limited_scope)|ConvertFrom-Json -AsHashtable
$zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
$hash=[Security.Cryptography.SHA256]::Create()
$all=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$native=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$names=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$batches=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$nativePrefix='liquid-recovery-v1/stream-'+$run+'-1/'
$dataPrefix='m1-autonomous-development/stream-'+$run+'-1/'
function J([string]$name){
    $e=$zip.GetEntry($name);Assert ($null -ne $e) ('MISSING_JSON '+$name)
    # Preserve even singleton JSON arrays; pipeline enumeration loses their identity.
    $r=[IO.StreamReader]::new($e.Open());try{return ,(ConvertFrom-Json -InputObject $r.ReadToEnd() -AsHashtable -NoEnumerate)}finally{$r.Dispose()}
}
try{
    $count=0
    foreach($e in $zip.Entries){
        $name=$e.FullName
        Assert ($name -notmatch '(^[/\\]|:|\\|(^|/)\.\.(/|$))' -and $names.Add($name)) 'UNSAFE_DUPLICATE_PATH'
        if($name.EndsWith('/')){continue}
        Assert ($name.StartsWith($nativePrefix,[StringComparison]::Ordinal) -or $name.StartsWith($dataPrefix,[StringComparison]::Ordinal)) ('FOREIGN_RUN_OR_PATH '+$name)
        $s=$e.Open();try{$sha=[Convert]::ToHexString($hash.ComputeHash($s)).ToLowerInvariant()}finally{$s.Dispose()}
        $item=@{sha256=$sha;bytes=$e.Length;archive=$ZipPath;entry=$name};$all.Add($name,$item)
        if($name.StartsWith($nativePrefix,[StringComparison]::Ordinal)){
            # FINAL is explicitly audited here after exit, not pre-counted by its child.
            $job=$name.Substring($nativePrefix.Length).Split('/')[0]
            Assert ($job -cmatch '^(final|prepare|reference-gate|ref-\d+|select-\d+|split-u|split-\d+|prefix-\d+|schema-\d+|startup-\d+)(-batch-\d+)?$') 'UNREGISTERED_NATIVE_JOB'
            Assert (-not $name.EndsWith('/batch_stop.json')) 'NATIVE_STOP_RECORD'
            $native.Add($name,$item)
            if([IO.Path]::GetFileName($name) -cin @('job_start.json','job_status.json','external_job_identity.json','ready.json','release.json','result.json','raw_evidence_receipts.json')){$item.json_value=J $name}
            if($name.EndsWith('/batch_complete.json')){$batches.Add($name,@{path=$name;sha256=$sha;record=(J $name)})}
        }
        $count++;if($count%10000 -eq 0){Write-Output ('ZIP_HASHED '+$count)}
    }
    Save 'entry_hashes.json' @($all.GetEnumerator()|ForEach-Object {@{path=$_.Key;sha256=$_.Value.sha256;bytes=$_.Value.bytes}}|Sort-Object path)
    Write-Output ('ZIP_HASH_COMPLETE '+$all.Count)
    $coverage=Test-C3NativeCoverage -Merged @{files=$native;batches=$batches} -RequiredStageIds (@($scope.required_static_stage_ids)+@('FINAL_ACCEPTANCE')) -SourceCommit $commit -PackageSha256 $packageSha -RunId $run -VerifyStageProofs -ExpectedExecutionIdentity $identity -EnvironmentLock $lock
    Assert ($coverage.missing_count -eq 0) 'STATIC_NATIVE_COVERAGE'
    Save 'native_coverage.json' $coverage
    Write-Output ('NATIVE_PROOFS_COMPLETE '+$coverage.stage_proofs_verified)
    $plan=J ($dataPrefix+'prefix_plan.json')
    Assert ($plan.source_commit -ceq $commit -and $plan.manifest_sha256 -ceq $packageSha -and $plan.run_key -ceq ('stream-'+$run+'-1') -and $plan.cases.Count -eq 101 -and -not $plan.prefix_policy_changed) 'PREFIX_PLAN_IDENTITY'
    foreach($b in $plan.case_source_raw_hashes.GetEnumerator()){
        $name=$b.Key.Substring(10);Assert ($all.ContainsKey($name) -and $all[$name].sha256 -ceq $b.Value) ('PLAN_SOURCE_HASH '+$name)
    }
    $result=J ($dataPrefix+'c3c_qualification_result.json')
    Save 'reported_qualification_result.json' $result
    Assert ($result.gate -ceq 'C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS' -and (ConvertTo-C3DeliveryCanonical $result.execution_identity) -ceq (ConvertTo-C3DeliveryCanonical $identity) -and $result.github_run_id -ceq $run -and $result.github_run_attempt -ceq '1' -and -not $result.prior_pass_credit) 'FORMAL_RESULT_IDENTITY_OR_GATE'
    $caseResults=[Collections.Generic.List[object]]::new();$prefixCount=0;$rowPairs=0;$snapshots=0
    function CheckReceipt($receipt){
        $name=$receipt.path.Substring(10)
        Assert ($all.ContainsKey($name) -and $all[$name].sha256 -ceq $receipt.raw_sha256 -and $all[$name].bytes -eq $receipt.bytes) ('RECEIPT_DRIFT '+$name)
        return $name
    }
    $traceRows=0
    function CheckTrace($receipt){
        $doc=CheckReceipt $receipt
        $index=J ($doc.Substring(0,$doc.Length-5)+'.trace_index.json')
        Assert ($index.schema -ceq 'm1-complete-stream-trace-v1' -and $index.frame_count -eq $index.rows.Count) 'TRACE_INDEX_SCHEMA'
        Assert ((ConvertTo-C3DeliveryCanonical $index.document_receipt) -ceq (ConvertTo-C3DeliveryCanonical $receipt)) 'TRACE_DOCUMENT_RECEIPT'
        $frames=CheckReceipt $index.frames_receipt
        $source=$zip.GetEntry($frames).Open();$offset=0;$digests=[Collections.Generic.List[string]]::new()
        try{foreach($row in $index.rows){
            Assert ($row.offset -eq $offset -and $row.compression -ceq 'zlib') 'TRACE_GAP_OR_COMPRESSION'
            $buf=[byte[]]::new([int]$row.stored_bytes);$read=0
            while($read -lt $buf.Length){$n=$source.Read($buf,$read,$buf.Length-$read);Assert ($n -gt 0) 'TRACE_TRUNCATED';$read+=$n}
            $memory=[IO.MemoryStream]::new($buf,$false);$z=[IO.Compression.ZLibStream]::new($memory,[IO.Compression.CompressionMode]::Decompress);$output=[IO.MemoryStream]::new()
            try{$z.CopyTo($output);$bytes=$output.ToArray()}finally{$z.Dispose();$memory.Dispose();$output.Dispose()}
            Assert ($bytes.Length -eq $row.bytes -and $bytes[-1] -eq 10 -and (Get-C3DeliverySha $bytes) -ceq $row.raw_sha256) 'TRACE_FRAME_BYTES'
            $digests.Add([Convert]::ToHexString($hash.ComputeHash($bytes,0,$bytes.Length-1)).ToLowerInvariant())
            $offset+=$row.stored_bytes
        };Assert ($source.ReadByte() -eq -1 -and $offset -eq $index.frames_receipt.bytes) 'TRACE_TRAILING_BYTES'}finally{$source.Dispose()}
        return @{index=$index;digests=@($digests.ToArray())}
    }
    for($i=0;$i -lt 101;$i++){
        $base=$dataPrefix+('cases/{0:000}/' -f $i)
        $stage=J ($base+'stage_result.json');$inventory=J ($base+'prefix_inventory.json');$prefix=J ($base+'prefix_result.json');$schema=J ($base+'schema_readback.json')
        Assert ($stage.status -ceq 'PASS' -and $stage.repeat_pass -and $stage.comparison.status -ceq 'PASS' -and $stage.comparison.findings.Count -eq 0 -and $schema.status -ceq 'PASS' -and $schema.index -eq $i -and $schema.all_original_frame_fields_checked) ('CASE_FAIL '+$i)
        Assert ($stage.descriptor.input_canonical_sha256 -ceq $definition.inputs[$i].input_canonical_sha256 -and $stage.descriptor.row_count -eq $definition.inputs[$i].row_count -and $inventory.input_sha256 -ceq $stage.descriptor.input_canonical_sha256) ('INPUT_BINDING '+$i)
        $null=CheckReceipt $stage.reference_receipt;$null=CheckReceipt $stage.split_receipt
        $referenceTrace=CheckTrace $stage.reference_receipt;$splitTrace=CheckTrace $stage.split_receipt
        $traceRows+=$referenceTrace.index.frame_count+$splitTrace.index.frame_count
        foreach($r in $stage.repeat_receipts){
            $repeated=CheckTrace $r;$traceRows+=$repeated.index.frame_count
            Assert ($r.raw_sha256 -ceq $stage.split_receipt.raw_sha256 -and $r.canonical_sha256 -ceq $stage.split_receipt.canonical_sha256) ('ACTUAL_REPEAT_BYTE_DRIFT '+$i)
        }
        Assert ($stage.repeat_receipts.Count -eq $stage.required_snapshot_count-1 -and $stage.repeat_hashes.Count -eq $stage.required_snapshot_count -and @($stage.repeat_hashes|Select-Object -Unique).Count -eq 1) ('REPEAT_COUNT_OR_HASH '+$i)
        $snapshots+=$stage.required_snapshot_count
        $selected=@($inventory.selected_prefix_lengths);$union=@(($inventory.mandatory_prefix_lengths+$inventory.output_triggered_progress_lengths+$inventory.output_triggered_confirmed_lengths)|Sort-Object -Unique)
        $records=$referenceTrace.index.metadata.snapshot.records
        $progress=@(for($j=0;$j -lt $records.Count;$j++){if($records[$j].state -ceq 'TRACKING_PROGRESS'){$j+1}})
        $confirmed=@(for($j=0;$j -lt $records.Count;$j++){if($records[$j].state -ceq 'TRACKING_FAULT_CONFIRMED'){$j+1}})
        Assert (($progress -join ',') -ceq ($inventory.output_triggered_progress_lengths -join ',') -and ($confirmed -join ',') -ceq ($inventory.output_triggered_confirmed_lengths -join ',')) ('ACTUAL_OUTPUT_TRIGGER_SET '+$i)
        Assert (($selected -join ',') -ceq ($union -join ',') -and ($selected -join ',') -ceq ($plan.cases[$i].selected_prefix_lengths -join ',') -and $plan.cases[$i].index -eq $i -and $prefix.status -ceq 'PASS' -and $prefix.selected_count -eq $selected.Count -and $schema.all_selected_prefixes -eq $selected.Count) ('SELECTED_SET '+$i)
        $null=CheckReceipt $prefix.inventory_receipt;$null=CheckReceipt $inventory.reference_receipt
        if($inventory.selection_policy -ceq 'SUPPORT_FROZEN_ALL_PREFIXES'){Assert (($selected -join ',') -ceq ((1..$stage.descriptor.row_count) -join ',')) ('SUPPORT_PREFIX '+$i)}
        foreach($n in $selected){
            Assert ($n -ge 1 -and $n -le $stage.descriptor.row_count) ('PREFIX_BOUND '+$i)
            $p=J ($base+('prefix-{0:000000}-result.json' -f $n))
            Assert ($p.status -ceq 'PASS' -and $p.starts_from_t0 -and $p.compared_complete_frames -eq $n -and $p.replayed_prefix_lengths.Count -eq 1 -and $p.replayed_prefix_lengths[0] -eq $n) ('PREFIX_PROOF '+$i+':'+$n)
            $rows=J (CheckReceipt $p.row_receipts)
            Assert ($rows.Count -eq $n) 'PREFIX_ROWS_COUNT'
            for($j=0;$j -lt $rows.Count;$j++){Assert ($rows[$j].row -eq $j -and $rows[$j].reference_sha256 -ceq $rows[$j].full_reference_sha256 -and $rows[$j].split_sha256 -ceq $rows[$j].full_split_sha256 -and $rows[$j].full_reference_sha256 -ceq $referenceTrace.digests[$j] -and $rows[$j].full_split_sha256 -ceq $splitTrace.digests[$j]) ('PREFIX_FRAME_PROOF '+$i+':'+$n+':'+$j)}
            $prefixCount++;$rowPairs+=$n
        }
        $caseResults.Add(@{index=$i;descriptor=$stage.descriptor;status='PASS';selected_count=$selected.Count;snapshots=$stage.required_snapshot_count;checks=$stage.checks})
        if($i%10 -eq 0){Write-Output ('CASES_READ '+($i+1))}
    }
    Assert ($snapshots -eq 499 -and $prefixCount -eq $result.selected_prefixes -and $result.fresh_descriptor_count -eq 101 -and $result.original_startup_historical -ceq '49/50' -and $result.versioned_startup_compatibility -ceq 'PASS' -and $result.schema_readback.passed) 'FINAL_COUNTS_OR_STARTUP'
    Save 'case_readback.json' @($caseResults.ToArray())
    Save 'readback_summary.json' @{status='INDEPENDENT_NATIVE_CASE_RECEIPT_PREFIX_READBACK_PASS';qualification_verdict='PENDING_SEMANTIC_SOURCE_CROSSCHECK';run_id=$run;execution_source_commit=$commit;official_artifact_id=12025669904;official_zip_sha256=$zipSha;official_zip_bytes=2011688990;zip_entries_hashed=$all.Count;native_files_hashed=$native.Count;native_coverage=$coverage;cases=101;full_snapshots=$snapshots;trace_frames_decompressed_and_hashed=$traceRows;selected_prefixes=$prefixCount;prefix_frame_pairs=$rowPairs;plan_bindings_verified=$plan.case_source_raw_hashes.Count;candidate_executed_locally=$false;python_native_or_model_executed_locally=$false}
    Write-Output 'READBACK_PASS_PENDING_FINAL_CROSSCHECK'
}catch{Save 'readback_failure.json' @{status='READBACK_STOP';error=$_.Exception.Message;location=$_.ScriptStackTrace;candidate_executed_locally=$false};throw}finally{$hash.Dispose();$zip.Dispose()}
