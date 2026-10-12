# Only input/provenance planning. No model, Python or native process launch here.
Set-StrictMode -Version Latest
function Get-CampaignStages {
    param([string]$Repo,[string]$Mode,[string]$IndicesCsv,[string]$RuntimePlanPath,[string]$ExpectedPlanSha,
          [string]$JobKey,[string]$RunKey,[string]$Commit,[string]$ManifestSha)
    $taskSpec=Get-Content -LiteralPath (Join-Path $Repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
    $taskStages=@();$taskHashes=[ordered]@{}
    if($Mode -in @('REFERENCE','SELECT','SPLIT','SCHEMA')) {
        if($IndicesCsv -notmatch '^[0-9]+(,[0-9]+)*$'){throw 'CASE_INDEX_INVENTORY_REQUIRED'}
        $taskIndices=@($IndicesCsv.Split(',')|ForEach-Object{[int]$_})
        if(@($taskIndices|Select-Object -Unique).Count -ne $taskIndices.Count -or @($taskIndices|Where-Object{$_ -lt 0 -or $_ -ge 101}).Count){throw 'CASE_INDEX_OUT_OF_SCOPE'}
        foreach($taskIndex in $taskIndices) {
            $taskId='CASE-{0:d3}' -f $taskIndex
            if($Mode -ne 'SPLIT'){$taskStages+=($taskId+'-'+$Mode)}else{
                $taskStages+=($taskId+'-SPLIT')
                $taskCount=if($taskSpec.input_inventory[$taskIndex].stage_id -in @('C-history','S-history','P15-history')){11}else{2}
                for($taskRepeat=1;$taskRepeat -lt $taskCount;$taskRepeat++){$taskStages+=($taskId+'-REPEAT-'+$taskRepeat)}
                $taskStages+=($taskId+'-SEAL')
            }
        }
        # Every downloaded prerequisite byte is bound before new model execution.
        $taskCases=Join-Path $Repo ('artifacts/m1-autonomous-development/'+$RunKey+'/cases')
        if(Test-Path -LiteralPath $taskCases){foreach($taskFile in (Get-ChildItem -LiteralPath $taskCases -File -Recurse|Sort-Object FullName)){
            $taskRelative=$taskFile.FullName.Substring($Repo.Length+1).Replace('\','/')
            $taskHashes[$taskRelative]=(Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }}
    } elseif($Mode -eq 'PREFIX') {
        if($IndicesCsv -notmatch '^[0-9]+$'){throw 'PREFIX_CASE_REQUIRED'}
        $taskIndex=[int]$IndicesCsv
        if($taskIndex -lt 0 -or $taskIndex -ge 101){throw 'PREFIX_CASE_OUT_OF_SCOPE'}
        if($ExpectedPlanSha -notmatch '^[a-f0-9]{64}$' -or -not $RuntimePlanPath){throw 'PREFIX_PLAN_BINDING_REQUIRED'}
        $taskPlanPath=[IO.Path]::GetFullPath((Join-Path $Repo $RuntimePlanPath))
        if(-not $taskPlanPath.StartsWith($Repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
            (Get-FileHash -LiteralPath $taskPlanPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedPlanSha){throw 'PREFIX_PLAN_HASH_DRIFT'}
        $taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw|ConvertFrom-Json
        if($taskPlan.run_key -cne $RunKey -or $taskPlan.source_commit -cne $Commit -or $taskPlan.manifest_sha256 -cne $ManifestSha){throw 'PREFIX_PLAN_SOURCE_DRIFT'}
        foreach($taskBinding in $taskPlan.case_source_raw_hashes.PSObject.Properties){
            $taskPath=Join-Path $Repo $taskBinding.Name
            # A case-scoped worker downloads only its own immutable prerequisite files.
            if($taskBinding.Name -match ('/cases/{0:d3}/' -f $taskIndex)){
                if((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value){throw 'PREFIX_CASE_SOURCE_DRIFT'}
                $taskHashes[$taskBinding.Name]=$taskBinding.Value
            }
        }
        $taskHashes[$RuntimePlanPath]=$ExpectedPlanSha
    } elseif($Mode -eq 'STARTUP') {
        if($IndicesCsv -notmatch '^[0-9]+$'){throw 'STARTUP_CASE_INDEX_REQUIRED'}
        $taskStages+=('STARTUP-'+$IndicesCsv)
    } elseif($Mode -eq 'FINAL') {
        $taskStages+=@('FINAL_ACCEPTANCE')
    } elseif($Mode -eq 'REFERENCE_GATE') {
        $taskStages+=@('REFERENCE_GROUPS')
    } else {throw 'CAMPAIGN_MODE_NOT_ADMITTED'}
    if($Mode -in @('FINAL','REFERENCE_GATE')){
        $taskDataRoot=Join-Path $Repo ('artifacts/m1-autonomous-development/'+$RunKey)
        foreach($taskFile in (Get-ChildItem -LiteralPath $taskDataRoot -Recurse -File|Sort-Object FullName)){
            $taskHashes[$taskFile.FullName.Substring($Repo.Length+1).Replace('\','/')]=(Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    if($Mode -eq 'STARTUP'){
        $taskInventoryRelative='artifacts/m1-autonomous-development/'+$RunKey+'/startup_inventory.json'
        $taskHashes[$taskInventoryRelative]=(Get-FileHash -LiteralPath (Join-Path $Repo $taskInventoryRelative) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return @{stages=$taskStages;input_hashes=$taskHashes}
}

function Write-CampaignPrefixPlan {
    param([string]$Repo,[string]$RunKey,[string]$Commit,[string]$ManifestSha)
    $taskSpec=Get-Content -LiteralPath (Join-Path $Repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
    $taskCases=@();$taskHashes=[ordered]@{}
    for($taskIndex=0;$taskIndex -lt 101;$taskIndex++){
        $taskRelative='artifacts/m1-autonomous-development/'+$RunKey+('/cases/{0:d3}' -f $taskIndex)
        $taskDir=Join-Path $Repo $taskRelative
        $taskStage=Get-Content -LiteralPath (Join-Path $taskDir 'stage_result.json') -Raw|ConvertFrom-Json
        $taskInventory=Get-Content -LiteralPath (Join-Path $taskDir 'prefix_inventory.json') -Raw|ConvertFrom-Json
        if($taskStage.status -cne 'PASS' -or $taskStage.repeat_pass -ne $true -or $taskStage.comparison.status -cne 'PASS'){throw 'COMPLETE_SPLIT_REQUIRED_BEFORE_PREFIX_PLAN'}
        $taskLengths=@($taskInventory.selected_prefix_lengths)
        $taskUnion=@(($taskInventory.mandatory_prefix_lengths+$taskInventory.output_triggered_progress_lengths+$taskInventory.output_triggered_confirmed_lengths)|Sort-Object -Unique)
        if(($taskLengths -join ',') -cne ($taskUnion -join ',') -or @($taskLengths|Where-Object{$_ -lt 1 -or $_ -gt $taskSpec.input_inventory[$taskIndex].row_count}).Count){throw 'PREFIX_SELECTED_UNION_DRIFT'}
        if($taskInventory.selection_policy -ceq 'SUPPORT_FROZEN_ALL_PREFIXES' -and ($taskLengths -join ',') -cne ((1..$taskSpec.input_inventory[$taskIndex].row_count) -join ',')){throw 'SUPPORT_PREFIX_MISSING'}
        $taskCases+=[ordered]@{index=$taskIndex;selected_prefix_lengths=$taskLengths;selected_count=$taskLengths.Count}
        foreach($taskFile in (Get-ChildItem -LiteralPath $taskDir -File -Recurse|Sort-Object FullName)){
            $taskHashes[$taskFile.FullName.Substring($Repo.Length+1).Replace('\','/')]=(Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    return [ordered]@{scope='M1_DEVELOPMENT_CAMPAIGN_NOT_FORMAL';run_key=$RunKey;source_commit=$Commit;
        manifest_sha256=$ManifestSha;cases=$taskCases;case_source_raw_hashes=$taskHashes;
        descriptor_count=101;prefix_policy_changed=$false;budget_yield_is_not_behavioral_acceptance=$true}
}
