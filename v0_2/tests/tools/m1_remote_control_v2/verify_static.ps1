# Safe local static / synthetic selector checks. NEVER starts Python or native.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $PSScriptRoot 'plan_tools.ps1')
$taskChecks=@()
function Add-LongStaticCheck([string]$Id,[bool]$Passed) {
    if(-not $Passed){throw ('LONG_STATIC_CHECK_FAIL: '+$Id)}
    $script:taskChecks+=@{id=$Id;passed=$true}
}
foreach($taskName in @('run.ps1','plan_tools.ps1','verify_static.ps1')) {
    $taskTokens=$null;$taskErrors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $taskName),[ref]$taskTokens,[ref]$taskErrors)
    Add-LongStaticCheck ('PS_PARSE_'+$taskName) ($taskErrors.Count -eq 0)
}
foreach($taskName in @('engine.py','codec.py','comparator.py','scheduler.py','state_copy.py','pre_oracle.py','projection.py','pf16.py','schemas.py')) {
    Add-LongStaticCheck ('FROZEN_CORE_'+$taskName) ((Get-LongRawHash (Join-Path $taskRepo ('v0_2/tests/tools/m1_engine_v2/'+$taskName))) -ceq
        (Get-LongRawHash (Join-Path $taskRepo ('v0_2/tests/tools/c3b_v14_1/'+$taskName))))
}
$taskRunner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'run.ps1') -Raw
foreach($taskLiteral in @("'120000','100','256','512'",'in_target_job','actual_python_pid','RAW_HASH_READBACK_FAILED',
    'REMOTE_ENVIRONMENT_AFTER_DRIFT','REMOTE_ADAPTER_SOURCE_DRIFT','PREFIX_BASE_SOFTWARE_ENVIRONMENT_DRIFT','New-LongPrefixPlan')) {
    Add-LongStaticCheck ('RETAINED_GUARD_'+$taskLiteral) ($taskRunner.Contains($taskLiteral))
}
Assert-LongList @(1,2,3) @(1,2,3) 'positive'
Add-LongStaticCheck 'LIST_POSITIVE' $true
foreach($taskBad in @(@(1,2),@(1,3,2),@(1,2,2),@('1',2,3))) {
    $taskRejected=$false
    try {Assert-LongList $taskBad @(1,2,3) 'negative'}catch{$taskRejected=$true}
    Add-LongStaticCheck ('LIST_NEGATIVE_'+$taskChecks.Count) $taskRejected
}
$taskWorker=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'stage_worker.py') -Raw
Add-LongStaticCheck 'ONLY_THREE_LONG_CASES' ($taskWorker.Contains('index not in (65, 66, 92)'))
$taskWorkflow=Get-Content -LiteralPath (Join-Path $taskRepo '.github/workflows/m1-remote-long-probe.yml') -Raw
Add-LongStaticCheck 'WORKFLOW_BASE_ONLY' ($taskWorkflow.Contains('-Mode BASE') -and -not $taskWorkflow.Contains('-Mode PREFIX'))
$taskOld=Get-Content -LiteralPath (Join-Path $taskRepo 'v0_2/tests/tools/m1_remote_control_v1/execution_manifest.json') -Raw|ConvertFrom-Json
foreach($taskBinding in $taskOld.remote_source_raw_hashes.PSObject.Properties){
    Add-LongStaticCheck ('V1_UNCHANGED_'+$taskBinding.Name) ((Get-LongRawHash (Join-Path $taskRepo $taskBinding.Name)) -ceq $taskBinding.Value)
}
[pscustomobject]@{status='STATIC_AND_SYNTHETIC_ONLY_PASS';checks=$taskChecks.Count;python_started=$false;native_started=$false;candidate_executed=$false}
