# New recovery control plane. No Python, native helper or workload is launched here.
Set-StrictMode -Version Latest

function Write-RecoveryJson {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $taskBytes = [Text.UTF8Encoding]::new($false).GetBytes(
        (ConvertTo-Json -InputObject $Value -Depth 30) + "`n")
    $taskFile = [IO.File]::Open($Path, [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try {
        $taskFile.Write($taskBytes, 0, $taskBytes.Length)
        $taskFile.Flush($true)
    } finally { $taskFile.Dispose() }
    $taskRead = [IO.File]::ReadAllBytes($Path)
    $taskSha = [Security.Cryptography.SHA256]::Create()
    try {
        $taskExpected = [Convert]::ToBase64String($taskSha.ComputeHash($taskBytes))
        if ([Convert]::ToBase64String($taskSha.ComputeHash($taskRead)) -cne $taskExpected) {
            throw 'EVIDENCE_READBACK_MISMATCH'
        }
    } finally { $taskSha.Dispose() }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-RecoveryStageDecision {
    param($Record, [Parameter(Mandatory)][string]$StageId)
    # Missing fields, truthy strings and an old case's passed=true are NOT admission.
    if ($null -eq $Record -or $Record -isnot [System.Collections.IDictionary]) {
        return @{status='INVALID'; reason='MALFORMED_STAGE_RECORD'}
    }
    if ($Record['stage_id'] -isnot [string] -or $Record['stage_id'] -cne $StageId) {
        return @{status='INVALID'; reason='STAGE_IDENTITY_MISMATCH'}
    }
    foreach ($taskField in @('source_verified','environment_verified','evidence_verified',
                            'primitive_consistent','cleanup_complete')) {
        if ($Record[$taskField] -isnot [bool] -or $Record[$taskField] -ne $true) {
            return @{status='INVALID'; reason=('REJECTED_' + $taskField.ToUpperInvariant())}
        }
    }
    foreach ($taskField in @('launcher_exitcode','child_exitcode','active_after_cleanup')) {
        if (($Record[$taskField] -isnot [int] -and $Record[$taskField] -isnot [long]) -or
            $Record[$taskField] -ne 0) {
            return @{status='INVALID'; reason=('REJECTED_' + $taskField.ToUpperInvariant())}
        }
    }
    foreach ($taskField in @('native_outcome','capture_status','result_status')) {
        if ($Record[$taskField] -isnot [string]) {
            return @{status='INVALID'; reason=('MALFORMED_' + $taskField.ToUpperInvariant())}
        }
    }
    if ($Record['native_outcome'] -cne 'EXITED') {
        return @{status='INVALID'; reason='NATIVE_NOT_EXITED'}
    }
    if ($Record['capture_status'] -cne 'COMPLETE') {
        return @{status='INVALID'; reason='CAPTURE_NOT_COMPLETE'}
    }
    if ($Record['result_status'] -cne 'PASS' -or $Record['passed'] -isnot [bool] -or
        $Record['passed'] -ne $true) {
        return @{status='STOP'; reason='RESULT_NOT_PASS'}
    }
    return @{status='PASS'; reason='ALL_REQUIRED_FIELDS_ACCEPTED'}
}

function Invoke-RecoveryBatch {
    param(
        [Parameter(Mandatory)][string[]]$StageIds,
        [Parameter(Mandatory)][string]$OutputRoot,
        [Parameter(Mandatory)][scriptblock]$InvokeStage,
        [Parameter(Mandatory)][ValidateSet('SYNTHETIC_CONTROL_PLANE','INDEPENDENT_DEVELOPMENT')]
        [string]$Scope
    )
    # InvokeStage is a TRUSTED adapter, responsible for identity/resource checks,
    # bounded execution, owned-process cleanup, and fsynced raw evidence FIRST.
    # This module does not implement or qualify a remote executor.
    if (-not $StageIds.Count -or @($StageIds | Select-Object -Unique).Count -ne $StageIds.Count -or
        @($StageIds | Where-Object { $_ -notmatch '^[A-Za-z0-9_-]+$' }).Count) {
        throw 'INVALID_STAGE_INVENTORY'
    }
    if ($Scope -eq 'INDEPENDENT_DEVELOPMENT' -and
        [Environment]::MachineName -ieq 'HIPPO') {
        throw 'HARD_HANG_HOST_WORKLOAD_HOLD'
    }
    $taskRoot = [IO.Path]::GetFullPath($OutputRoot)
    $taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
    $taskAllowed = [IO.Path]::GetFullPath((Join-Path $taskRepo 'artifacts/liquid-recovery-v1')) +
        [IO.Path]::DirectorySeparatorChar
    if (-not $taskRoot.StartsWith($taskAllowed, [StringComparison]::OrdinalIgnoreCase) -or
        (Test-Path -LiteralPath $taskRoot)) { throw 'FRESH_ARTIFACT_ROOT_REQUIRED' }
    New-Item -ItemType Directory -Path $taskRoot -ErrorAction Stop | Out-Null
    $taskStates = @($StageIds | ForEach-Object { @{stage_id=$_; status='NOT_RUN'} })
    $taskReceipts = @()
    $null = Write-RecoveryJson (Join-Path $taskRoot 'batch_start.json') @{
        scope=$Scope; stage_ids=$StageIds; fresh_execution=$true; no_retry=$true
        start_utc=[DateTime]::UtcNow.ToString('o'); pid=$PID; formal_qualification=$false
    }
    for ($taskIndex=0; $taskIndex -lt $StageIds.Count; $taskIndex++) {
        $taskId = $StageIds[$taskIndex]
        $taskPrefix = 'stage-{0:d3}' -f $taskIndex
        try {
            $null = Write-RecoveryJson (Join-Path $taskRoot ($taskPrefix+'-begin.json')) @{
                stage_id=$taskId; event='BEGIN'; utc=[DateTime]::UtcNow.ToString('o')
            }
            # Anything after BEGIN but before a durable result remains unfinished.
            $taskStates[$taskIndex]['status'] = 'RUNNING'
            $taskRecord = & $InvokeStage $taskId $taskRoot
            $taskResultPath = Join-Path $taskRoot ($taskPrefix+'-result.json')
            $taskHash = Write-RecoveryJson $taskResultPath $taskRecord
            $taskReceipts += @{stage_id=$taskId; result_raw_sha256=$taskHash}
            $taskDecision = Get-RecoveryStageDecision $taskRecord $taskId
            $taskStates[$taskIndex]['status'] = $taskDecision.status
            $taskStates[$taskIndex]['reason'] = $taskDecision.reason
            if ($taskDecision.status -cne 'PASS') { throw ('FIRST_FAILURE_STOP: '+$taskDecision.reason) }
            $null = Write-RecoveryJson (Join-Path $taskRoot ($taskPrefix+'-end.json')) @{
                stage_id=$taskId; event='END'; result_raw_sha256=$taskHash
                utc=[DateTime]::UtcNow.ToString('o')
            }
        } catch {
            if ($taskStates[$taskIndex]['status'] -in @('NOT_RUN','RUNNING','PASS')) {
                $taskStates[$taskIndex]['status'] = 'INVALID'
            }
            # Persist STOP before returning. If STOP persistence itself fails, throw:
            # the caller must never convert missing evidence into success.
            $null = Write-RecoveryJson (Join-Path $taskRoot 'batch_stop.json') @{
                status='STOPPED_NOT_FULL_PASS'; failed_stage=$taskId; stages=$taskStates
                receipts=$taskReceipts; scope=$Scope; no_same_run_repair_or_retry=$true
                error_type=$_.Exception.GetType().Name; utc=[DateTime]::UtcNow.ToString('o')
            }
            throw ('RECOVERY_BATCH_STOP: '+$taskId)
        }
    }
    $null = Write-RecoveryJson (Join-Path $taskRoot 'batch_complete.json') @{
        status='COMPLETE'; scope=$Scope; stages=$taskStates; receipts=$taskReceipts
        formal_qualification=$false; utc=[DateTime]::UtcNow.ToString('o')
    }
    return @{status='COMPLETE'; scope=$Scope; output_root=$taskRoot}
}
