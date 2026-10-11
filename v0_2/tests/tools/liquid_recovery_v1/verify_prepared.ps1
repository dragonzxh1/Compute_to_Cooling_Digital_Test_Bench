# Static/synthetic evidence only: does not import/launch Python or any native helper.
param([Parameter(Mandatory)][string]$SyntheticEvidence)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'batch.ps1')
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$taskChecks=[Collections.Generic.List[object]]::new()
function Require-Preparation([bool]$Condition,[string]$Name) {
    if(-not $Condition){throw ('PREPARATION_CHECK_FAILED: '+$Name)}
    $taskChecks.Add(@{check=$Name; pass=$true})
}
$taskPlan=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'plan.json') -Raw | ConvertFrom-Json
Require-Preparation ($taskPlan.status -ceq 'PREPARED_NOT_BEHAVIORALLY_EXECUTED') 'prepared-not-executed'
Require-Preparation ($taskPlan.boolean_pressure_prerequisite -eq $false) 'no-bool-prerequisite'
Require-Preparation ($taskPlan.external_publication_dispatch_authorized -eq $false) 'no-publication-dispatch'
Require-Preparation ($taskPlan.independent_environment_status -ceq 'NOT_REGISTERED') 'environment-not-fabricated'
$taskSelection=@($taskPlan.smoke_stages | ForEach-Object { $_.pytest_node_ids })
Require-Preparation ($taskSelection.Count -eq 12 -and @($taskSelection | Select-Object -Unique).Count -eq 12) 'unique-12-test-functions'
$taskCount=0
foreach($taskNode in $taskSelection) {
    $taskParts=$taskNode -split '::'
    $taskSource=Get-Content -LiteralPath (Join-Path $taskRepo $taskParts[0]) -Raw
    Require-Preparation ([regex]::IsMatch($taskSource,'(?m)^def '+[regex]::Escape($taskParts[1])+'\(')) ('existing-test:'+ $taskParts[1])
    $taskItems=$taskPlan.expected_collection_counts.PSObject.Properties[$taskNode].Value
    Require-Preparation (($taskItems -is [int] -or $taskItems -is [long]) -and $taskItems -gt 0) ('explicit-count:'+ $taskParts[1])
    $taskCount+=$taskItems
}
Require-Preparation ($taskCount -eq 20) 'planned-20-parametrized-smoke-items-not-results'
foreach($taskFile in @('batch.ps1','verify_batch.ps1','verify_prepared.ps1')) {
    $taskTokens=$null; $taskErrors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $taskFile),[ref]$taskTokens,[ref]$taskErrors)
    Require-Preparation ($taskErrors.Count -eq 0) ('powershell-parse:'+ $taskFile)
}
$taskInventoryPath=Join-Path $PSScriptRoot 'source_inventory.json'
$taskInventory=Get-Content -LiteralPath $taskInventoryPath -Raw | ConvertFrom-Json
$taskBindings=@($taskInventory.source_raw_hashes.PSObject.Properties)
Require-Preparation ($taskBindings.Count -gt 0) 'nonempty-smoke-source-inventory'
foreach($taskBinding in $taskBindings) {
    $taskPath=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskBinding.Name))
    Require-Preparation ($taskPath.StartsWith($taskRepo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) ('source-in-repo:'+ $taskBinding.Name)
    Require-Preparation ((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $taskBinding.Value) ('smoke-source-hash:'+ $taskBinding.Name)
}
$taskProtectedPath=Join-Path $taskRepo 'artifacts/runtime-isolation-v6/registration.json'
$taskProtected=Get-Content -LiteralPath $taskProtectedPath -Raw | ConvertFrom-Json
$taskProtectedMismatches=@()
foreach($taskBinding in $taskProtected.source_raw_hashes.PSObject.Properties) {
    $taskPath=if([IO.Path]::IsPathRooted($taskBinding.Name)){$taskBinding.Name}else{Join-Path $taskRepo $taskBinding.Name}
    if(-not(Test-Path -LiteralPath $taskPath) -or
       (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {
        $taskProtectedMismatches+=$taskBinding.Name
    }
}
Require-Preparation ($taskProtectedMismatches.Count -eq 0) 'original-655-protected-source-audit'
$taskSynthetic=Get-Content -LiteralPath $SyntheticEvidence -Raw | ConvertFrom-Json
Require-Preparation ($taskSynthetic.status -ceq 'SYNTHETIC_CONTROL_PLANE_PASS' -and
    $taskSynthetic.count -eq 29 -and @($taskSynthetic.checks | Where-Object pass -ne $true).Count -eq 0 -and
    $taskSynthetic.python_started -eq $false -and $taskSynthetic.native_helper_started -eq $false) '29-synthetic-not-behavioral-checks'
foreach($taskBinding in $taskSynthetic.source_raw_hashes.PSObject.Properties) {
    Require-Preparation ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $taskBinding.Value) ('synthetic-source-match:'+ $taskBinding.Name)
}
$taskThin=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'progress.py') -Raw
Require-Preparation (-not [regex]::IsMatch($taskThin,'sys\.settrace|ctypes|faulthandler|@logged|contextmanager|Thread\(')) 'thin-log-no-in-process-ffi-tracer-watchdog'
Require-Preparation ([regex]::IsMatch($taskThin,'os\.fsync') -and [regex]::IsMatch($taskThin,'2 \* 1024 \* 1024')) 'thin-log-durable-bounded'
$taskAdmission=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'admission.py') -Raw
Require-Preparation ([regex]::IsMatch($taskAdmission,'HARD_HANG_HOST_WORKLOAD_HOLD') -and
    [regex]::IsMatch($taskAdmission,'INDEPENDENT_ENVIRONMENT_NOT_REGISTERED')) 'workload-default-deny'
$taskRoot=Join-Path $taskRepo ('artifacts/liquid-recovery-v1/preparation-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskRoot | Out-Null
$null=Write-RecoveryJson (Join-Path $taskRoot 'preparation_evidence.json') @{
    status='PREPARATION_STATIC_SYNTHETIC_PASS_NOT_WORKLOAD_PASS'
    checks=$taskChecks; count=$taskChecks.Count; smoke_source_count=$taskBindings.Count
    planned_pytest_item_count=$taskCount; behavioral_tests_executed=0
    protected_source_count=@($taskProtected.source_raw_hashes.PSObject.Properties).Count
    protected_source_drift=$taskProtectedMismatches; python_started=$false; native_helper_started=$false
    python_syntax_runtime_validation='NOT_RUN'; thin_log_runtime_validation='NOT_RUN'
    independent_environment_status='NOT_REGISTERED'; prefix_status='NOT_RUN'; campaign_status='NOT_RUN'
    git_commit_push=$false; host_stability_proven=$false
    source_inventory_raw_sha256=(Get-FileHash -LiteralPath $taskInventoryPath -Algorithm SHA256).Hash.ToLowerInvariant()
    synthetic_evidence_path=$SyntheticEvidence
    synthetic_evidence_raw_sha256=(Get-FileHash -LiteralPath $SyntheticEvidence -Algorithm SHA256).Hash.ToLowerInvariant()
}
Write-Output $taskRoot
