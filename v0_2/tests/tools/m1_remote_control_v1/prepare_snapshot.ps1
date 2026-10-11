# Offline byte inventory/copy only. NEVER launches Python, candidate or helpers.
param([string]$SourceRoot='D:/Github/Compute_to_Cooling_Digital_Test_Bench')
$ErrorActionPreference='Stop'
$taskSource=[IO.Path]::GetFullPath($SourceRoot)
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
if($taskSource -eq $taskRepo){throw 'SEPARATE_SOURCE_AND_PREPARATION_WORKTREE_REQUIRED'}
$taskIntegrity=Get-Content -LiteralPath (Join-Path $taskSource 'phase5_r5_2_1r4_7_c3_a_integrity_evidence.json') -Raw|ConvertFrom-Json
$taskSpec=Get-Content -LiteralPath (Join-Path $taskSource 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
foreach($taskBinding in @($taskIntegrity.source_hash_bindings.PSObject.Properties)+@($taskIntegrity.artifact_hashes.PSObject.Properties)){
    $taskPath=if([IO.Path]::IsPathRooted($taskBinding.Name)){$taskBinding.Name}else{Join-Path $taskSource $taskBinding.Name}
    if((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value.raw_sha256){throw ('NORMATIVE_SOURCE_DRIFT: '+$taskBinding.Name)}
}
foreach($taskDescriptor in $taskSpec.input_inventory){
    if((Get-FileHash -LiteralPath (Join-Path $taskSource $taskDescriptor.result_path) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskDescriptor.result_raw_sha256){throw 'FROZEN_INPUT_SOURCE_DRIFT'}
}
$taskNames=@($taskIntegrity.source_hash_bindings.PSObject.Properties.Name)+@($taskIntegrity.artifact_hashes.PSObject.Properties.Name)+@($taskSpec.input_inventory.result_path)+@(
    'phase5_r5_2_1r4_7_c3_a_integrity_evidence.json','phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json',
    'phase5_r5_2_2_fixture_tracking_profile.json','phase5_r5_2_silent_tracking_fault_registration.json')
foreach($taskFolder in @('v0_2/examples','v0_2/tests/control','v0_2/tests/data/tracking_qualification',
    'v0_2/tests/tools/c3b_v5','v0_2/tests/tools/c3b_v6','v0_2/tests/tools/c3b_v7','v0_2/tests/tools/c3b_v8',
    'v0_2/tests/tools/c3b_v9','v0_2/tests/tools/c3b_v10','v0_2/tests/tools/c3b_v11','v0_2/tests/tools/c3b_v14_1')){
    Push-Location -LiteralPath $taskSource
    try{$taskNames+=@(rg --files $taskFolder -g '*.py' -g '*.json' -g '*.md' -g '*.lock')}finally{Pop-Location}
}
$taskBindings=[ordered]@{};$taskAliases=[ordered]@{};$taskBytes=0L
foreach($taskName in ($taskNames|ForEach-Object{$_.Replace('\','/')}|Sort-Object -Unique)){
    if($taskName -match '(?i)(DSX|/twin/)'){throw 'DSX_NOT_IN_THIS_PUBLICATION_SCOPE'}
    $taskPath=if([IO.Path]::IsPathRooted($taskName)){$taskName}else{Join-Path $taskSource $taskName}
    $taskItem=Get-Item -LiteralPath $taskPath
    $taskHash=(Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskBytes+=$taskItem.Length
    $taskRelative=$taskName
    if([IO.Path]::IsPathRooted($taskName)){
        $taskRelative='v0_2/tests/data/m1_external_frozen/'+$taskHash+'.txt'
        $taskAliases[$taskName]=@{portable_path=$taskRelative;raw_sha256=$taskHash}
        $taskText=Get-Content -LiteralPath $taskPath -Raw
        if($taskText -match 'github_pat_|ghp_[A-Za-z0-9]{20}|BEGIN [A-Z ]*PRIVATE KEY|(?i)(password|api_key)\s*=\s*["''][^"'']+'){throw 'EXTERNAL_SOURCE_PRIVACY_REVIEW_REQUIRED'}
    }
    $taskDest=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskRelative))
    if(-not $taskDest.StartsWith($taskRepo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'COPY_OUTSIDE_WORKTREE_DENIED'}
    New-Item -ItemType Directory -Path (Split-Path $taskDest) -Force|Out-Null
    if(Test-Path -LiteralPath $taskDest){
        if((Get-FileHash -LiteralPath $taskDest -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskHash){throw ('EXISTING_WORKTREE_FILE_DIFFERS: '+$taskRelative)}
    }else{Copy-Item -LiteralPath $taskPath -Destination $taskDest}
    $taskBindings[$taskRelative]=$taskHash
}
$taskValue=[ordered]@{status='INPUT_COMPLETE_PREPARATION_NOT_EXECUTED';baseline='C3B_V14_1_MATH_WITH_V11_THIN_ADAPTER_BASE';
    normative_source_count=222;normative_artifact_count=5;descriptors=101;observer_attributes=56;
    unique_input_sources=@($taskSpec.input_inventory|Sort-Object result_path -Unique).Count;
    source_raw_hashes=$taskBindings;frozen_external_path_aliases=$taskAliases;original_byte_count=$taskBytes;
    historical_result_use='INPUT_POINTER_AND_SOURCE_HASH_ONLY_NEVER_BORROW_SCORES_OR_SNAPSHOTS';
    full_P_history_available=$false;hardware='CALIBRATION_REQUIRED';formal_qualification_authorized=$false;production_authorized=$false}
$taskJsonPath=Join-Path $PSScriptRoot 'source_inventory.json'
$taskRaw=[Text.UTF8Encoding]::new($false).GetBytes(($taskValue|ConvertTo-Json -Depth 8)+"`n")
$taskFile=[IO.File]::Open($taskJsonPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$taskFile.Write($taskRaw,0,$taskRaw.Length);$taskFile.Flush($true)}finally{$taskFile.Dispose()}
[pscustomobject]@{count=$taskBindings.Count;bytes=$taskBytes;descriptors=101;external_aliases=$taskAliases.Count;inventory_raw=(Get-FileHash -LiteralPath $taskJsonPath -Algorithm SHA256).Hash.ToLowerInvariant()}
