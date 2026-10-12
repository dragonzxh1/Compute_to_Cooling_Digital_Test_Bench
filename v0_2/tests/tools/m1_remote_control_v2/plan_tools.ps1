# Pure evidence/selector coordinator: no Python, candidate or native process launch.
Set-StrictMode -Version Latest

function Get-LongRawHash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-LongReceipt([string]$Repo,$Receipt) {
    $taskPath=[IO.Path]::GetFullPath((Join-Path $Repo $Receipt.path))
    if(-not $taskPath.StartsWith($Repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
       (Get-Item -LiteralPath $taskPath).Length -ne $Receipt.bytes -or
       (Get-LongRawHash $taskPath) -cne $Receipt.raw_sha256){throw 'LONG_BASE_RECEIPT_DRIFT'}
}

function Assert-LongList($Actual,$Expected,[string]$Name) {
    $taskActual=@($Actual); $taskExpected=@($Expected)
    if($taskActual.Count -ne $taskExpected.Count){throw ('LONG_SELECTION_COUNT_DRIFT: '+$Name)}
    for($taskI=0;$taskI -lt $taskExpected.Count;$taskI++) {
        if(($taskActual[$taskI] -isnot [int] -and $taskActual[$taskI] -isnot [long]) -or
           $taskActual[$taskI] -ne $taskExpected[$taskI]){throw ('LONG_SELECTION_ORDER_DRIFT: '+$Name)}
    }
}

function New-LongPrefixPlan {
    param([string]$Repo,[string]$RunKey,[string]$Commit,[string]$ManifestSha)
    if($RunKey -notmatch '^long-[0-9]+-[0-9]+$'){throw 'LONG_RUN_KEY_DENIED'}
    $taskManifest=Get-Content -LiteralPath (Join-Path $Repo 'v0_2/tests/tools/m1_remote_control_v2/execution_manifest.json') -Raw|ConvertFrom-Json
    $taskModelRoot='artifacts/m1-autonomous-development/'+$RunKey+'/base'
    $taskBatchRoot='artifacts/liquid-recovery-v1/'+$RunKey+'/base'
    $taskBatch=Get-Content -LiteralPath (Join-Path $Repo ($taskBatchRoot+'/batch_complete.json')) -Raw|ConvertFrom-Json
    if(@($taskBatch.stages).Count -ne @($taskManifest.base_stage_ids).Count){throw 'LONG_BASE_STAGE_COUNT_DRIFT'}
    for($taskI=0;$taskI -lt @($taskManifest.base_stage_ids).Count;$taskI++) {
        if($taskBatch.stages[$taskI].stage_id -cne $taskManifest.base_stage_ids[$taskI] -or $taskBatch.stages[$taskI].status -cne 'PASS'){throw 'LONG_BASE_INCOMPLETE_OR_NOT_PASS'}
    }
    if($taskBatch.status -cne 'COMPLETE'){throw 'LONG_BASE_BATCH_INCOMPLETE'}
    $taskSpec=Get-Content -LiteralPath (Join-Path $Repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
    $taskCases=@(); $taskShards=@(); $taskSerial=0
    foreach($taskIndex in @(65,66,92)) {
        $taskDescriptor=$taskSpec.input_inventory[$taskIndex]
        $taskFolder=$taskModelRoot+('/{0:d3}' -f $taskIndex)
        $taskInv=Get-Content -LiteralPath (Join-Path $Repo ($taskFolder+'/prefix_inventory.json')) -Raw|ConvertFrom-Json
        $taskInvReceipt=Get-Content -LiteralPath (Join-Path $Repo ($taskFolder+'/prefix_inventory_receipt.json')) -Raw|ConvertFrom-Json
        Assert-LongReceipt $Repo $taskInvReceipt
        Assert-LongReceipt $Repo $taskInv.reference_receipt
        $taskReference=Get-Content -LiteralPath (Join-Path $Repo $taskInv.reference_receipt.path) -Raw|ConvertFrom-Json
        $taskInput=Get-Content -LiteralPath (Join-Path $Repo ($taskModelRoot+('/inputs/input-{0:d3}.json' -f $taskIndex))) -Raw|ConvertFrom-Json
        $taskRows=@($taskInput.observations); $taskRecords=@($taskReference.snapshot.records)
        if($taskRows.Count -ne $taskDescriptor.row_count -or $taskRecords.Count -ne $taskRows.Count -or
           $taskInv.input_sha256 -cne $taskDescriptor.input_canonical_sha256){throw 'LONG_INPUT_REFERENCE_BINDING_DRIFT'}
        $taskMandatory=@($taskRows.Count); $taskProgress=@(); $taskConfirmed=@()
        $taskPrevious=$null; $taskPreviousValid=$true
        for($taskI=0;$taskI -lt $taskRows.Count;$taskI++) {
            $taskRow=$taskRows[$taskI]; $taskRecord=$taskRecords[$taskI]; $taskValid=$taskRow.quality -ceq 'VALID'
            if($taskRecord.time_ns -ne $taskRow.time_ns){throw 'LONG_REFERENCE_ORDER_DRIFT'}
            if($null -eq $taskPrevious -or $taskPrevious -ne $taskRow.plc_command -or $taskValid -ne $taskPreviousValid){$taskMandatory+=($taskI+1)}
            if($taskRecord.state -ceq 'TRACKING_PROGRESS'){$taskProgress+=($taskI+1)}
            if($taskRecord.state -ceq 'TRACKING_FAULT_CONFIRMED'){$taskConfirmed+=($taskI+1)}
            $taskPrevious=$taskRow.plc_command; $taskPreviousValid=$taskValid
        }
        $taskConditional=$taskDescriptor.stage_id.StartsWith('ITQ-',[StringComparison]::Ordinal)
        if($taskConditional){
            if($taskInv.selection_policy -cne 'ITQ_FROZEN_CONDITIONAL'){throw 'LONG_PREFIX_POLICY_DRIFT'}
            $taskMandatory=@($taskMandatory|Sort-Object -Unique)
        } else {
            if($taskInv.selection_policy -cne 'SUPPORT_FROZEN_ALL_PREFIXES'){throw 'LONG_PREFIX_POLICY_DRIFT'}
            $taskMandatory=@(1..$taskRows.Count)
        }
        $taskSelected=@(($taskMandatory+$taskProgress+$taskConfirmed)|Sort-Object -Unique)
        Assert-LongList $taskInv.mandatory_prefix_lengths $taskMandatory 'mandatory'
        Assert-LongList $taskInv.output_triggered_progress_lengths $taskProgress 'progress'
        Assert-LongList $taskInv.output_triggered_confirmed_lengths $taskConfirmed 'confirmed'
        Assert-LongList $taskInv.selected_prefix_lengths $taskSelected 'selected'
        $taskStage=Get-Content -LiteralPath (Join-Path $Repo ($taskFolder+'/stage_result.json')) -Raw|ConvertFrom-Json
        if($taskStage.status -cne 'PASS' -or $taskStage.comparison.status -cne 'PASS' -or $taskStage.repeat_pass -ne $true -or
           @($taskStage.checks.PSObject.Properties|Where-Object {$_.Value -ne $true}).Count){throw 'LONG_SPLIT_NOT_PASS'}
        foreach($taskReceipt in @($taskStage.reference_receipt,$taskStage.split_receipt)+@($taskStage.repeat_receipts)){Assert-LongReceipt $Repo $taskReceipt}
        $taskCases+=[ordered]@{index=$taskIndex;stage_id=$taskDescriptor.stage_id;case_key=$taskDescriptor.case_key;
            row_count=$taskRows.Count;selected_prefix_lengths=$taskSelected;inventory_receipt=$taskInvReceipt;
            terminal_probe_length=$taskRows.Count;all_selected_prefixes_executed=$false}
        for($taskOffset=0;$taskOffset -lt $taskSelected.Count;$taskOffset+=6) {
            $taskLengths=@($taskSelected[$taskOffset..([Math]::Min($taskOffset+5,$taskSelected.Count-1))])
            $taskSerial++
            $taskShards+=[ordered]@{id=('shard-{0:d3}' -f $taskSerial);case_index=$taskIndex;prefix_lengths=$taskLengths;
                stage_ids=@($taskLengths|ForEach-Object {'CASE-{0:d3}-PREFIX_ONE-{1}' -f $taskIndex,$_})}
        }
    }
    $taskBindings=[ordered]@{}
    foreach($taskRelativeRoot in @($taskModelRoot,$taskBatchRoot)) {
        foreach($taskFile in (Get-ChildItem -LiteralPath (Join-Path $Repo $taskRelativeRoot) -File -Recurse|Sort-Object FullName)) {
            $taskRelative=$taskFile.FullName.Substring($Repo.Length+1).Replace('\','/')
            $taskBindings[$taskRelative]=Get-LongRawHash $taskFile.FullName
        }
    }
    $taskEnvironment=Get-Content -LiteralPath (Join-Path $Repo ($taskBatchRoot+'/independent_environment_registration.json')) -Raw|ConvertFrom-Json
    return [ordered]@{version='M1_LONG_PREFIX_SELECTION_V2';scope='M1_REMOTE_DEVELOPMENT_ONLY';
        status='FRESH_SELECTION_AND_TERMINAL_PROBES_NOT_COMPLETE_PREFIX_CAMPAIGN';
        run_key=$RunKey;source_commit=$Commit;execution_manifest_raw_sha256=$ManifestSha;
        base_runtime_identity=$taskEnvironment.runtime_identity;cases=$taskCases;shards=$taskShards;
        base_artifact_raw_hashes=$taskBindings;shard_size=6;each_prefix_replay='INDEPENDENT_CHILD_FROM_T0';
        prefix_shards_execution_status='PLANNED_NOT_EXECUTED';formal_qualification=$false;production=$false;phase6=$false}
}

function Read-VerifiedLongPlan {
    param([string]$Repo,[string]$Path,[string]$ExpectedSha,[string]$ExpectedCommit,[string]$ExpectedManifestSha,[string]$RunKey)
    if((Get-LongRawHash $Path) -cne $ExpectedSha){throw 'LONG_RUNTIME_PLAN_HASH_DRIFT'}
    $taskPlan=Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json
    if($taskPlan.source_commit -cne $ExpectedCommit -or $taskPlan.execution_manifest_raw_sha256 -cne $ExpectedManifestSha -or
       $taskPlan.run_key -cne $RunKey -or $taskPlan.scope -cne 'M1_REMOTE_DEVELOPMENT_ONLY'){throw 'LONG_RUNTIME_PLAN_BINDING_DRIFT'}
    foreach($taskBinding in $taskPlan.base_artifact_raw_hashes.PSObject.Properties){
        if((Get-LongRawHash (Join-Path $Repo $taskBinding.Name)) -cne $taskBinding.Value){throw 'LONG_BASE_ARTIFACT_DRIFT'}
    }
    $taskRebuilt=New-LongPrefixPlan -Repo $Repo -RunKey $RunKey -Commit $ExpectedCommit -ManifestSha $ExpectedManifestSha
    if((ConvertTo-Json -InputObject $taskPlan -Depth 30 -Compress) -cne (ConvertTo-Json -InputObject $taskRebuilt -Depth 30 -Compress)){throw 'LONG_PLAN_NOT_EXACT_FROZEN_SELECTOR_UNION'}
    return $taskPlan
}
