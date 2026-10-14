# Independent C3-C durable batch control. Exact authority is mandatory.
Set-StrictMode -Version Latest

function Get-C3DispatchIdentity {
    # Byte-authenticated transport only. Python validates canonical/package
    # semantics before any model import. This is not a user approval generator.
    $scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN'
    foreach($name in @('C2C_C3C_PACKAGE_SHA256','C2C_C3C_APPROVAL_SHA256','C2C_C3C_AUTHORIZATION_SHA256')){
        if([Environment]::GetEnvironmentVariable($name) -cnotmatch '^[a-f0-9]{64}$'){throw 'C3C_DISPATCH_HASH_REQUIRED'}
    }
    $approvalRaw=[Convert]::FromBase64String($env:C2C_C3C_APPROVAL_B64)
    $authorizationRaw=[Convert]::FromBase64String($env:C2C_C3C_AUTHORIZATION_B64)
    $sha=[Security.Cryptography.SHA256]::Create()
    try {
        $a=[BitConverter]::ToString($sha.ComputeHash($approvalRaw)).Replace('-','').ToLowerInvariant()
        $x=[BitConverter]::ToString($sha.ComputeHash($authorizationRaw)).Replace('-','').ToLowerInvariant()
    }finally{$sha.Dispose()}
    if($a -cne $env:C2C_C3C_APPROVAL_SHA256 -or $x -cne $env:C2C_C3C_AUTHORIZATION_SHA256){throw 'C3C_APPROVAL_TRANSPORT_DRIFT'}
    $approval=[Text.Encoding]::UTF8.GetString($approvalRaw)|ConvertFrom-Json
    $authorization=[Text.Encoding]::UTF8.GetString($authorizationRaw)|ConvertFrom-Json
    if($approval.schema -cne 'm1-c3c-user-approval-receipt-v1' -or $approval.status -cne 'FROZEN_USER_APPROVED' -or $approval.scope -cne $scope -or $approval.package_raw_sha256 -cne $env:C2C_C3C_PACKAGE_SHA256){throw 'C3C_FREEZE_APPROVAL_NOT_EXACT'}
    foreach($name in @('limited_scope','SEM01','SEM02','PF06_supplement')){if($approval.decisions.$name -cne 'APPROVED'){throw 'C3C_UNRESOLVED_SCOPE_DECISION'}}
    if($authorization.schema -cne 'm1-c3c-execution-authorization-v1' -or $authorization.status -cne 'EXECUTION_AUTHORIZED' -or $authorization.scope -cne $scope -or $authorization.package_raw_sha256 -cne $env:C2C_C3C_PACKAGE_SHA256 -or $authorization.approval_receipt_raw_sha256 -cne $a){throw 'C3C_EXECUTION_AUTHORIZATION_NOT_EXACT'}
    if($env:GITHUB_SHA -cnotmatch '^[a-f0-9]{40}$' -or $approval.execution_source_commit -cne $env:GITHUB_SHA -or $authorization.execution_source_commit -cne $env:GITHUB_SHA){throw 'C3C_AUTHORIZATION_COMMIT_DRIFT'}
    if($approval.candidate_sha256 -cne '70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce'){throw 'C3C_APPROVED_CANDIDATE_DRIFT'}
    return @{scope=$scope;package_raw_sha256=$env:C2C_C3C_PACKAGE_SHA256;approval_receipt_raw_sha256=$a;
        authorization_raw_sha256=$x;candidate_sha256=$approval.candidate_sha256;execution_source_commit=$env:GITHUB_SHA}
}

function Write-C3Json {
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

function Get-C3StageDecision {
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
        return @{status=if($Record['result_status'] -ceq 'FAIL'){'FAIL'}elseif($Record['result_status'] -ceq 'INCOMPLETE'){'INCOMPLETE'}else{'INVALID'}; reason='RESULT_NOT_PASS'}
    }
    return @{status='PASS'; reason='ALL_REQUIRED_FIELDS_ACCEPTED'}
}

function Get-C3InvalidStageRecord {
    param([Parameter(Mandatory)][string]$StageId,
          [Parameter(Mandatory)]$Result,
          [Parameter(Mandatory)]$Native,
          [Parameter(Mandatory)][int]$LauncherExitcode)
    if($Result.status -cne 'INVALID' -or $Result.stage_id -cne $StageId){throw 'INVALID_ENVELOPE_IDENTITY_REQUIRED'}
    # Absence of runtime authority is not a property access error or a PASS.
    # The original durable result retains the specific rejection diagnostics.
    return @{stage_id=$StageId; source_verified=$true; environment_verified=$false; evidence_verified=$true;
        primitive_consistent=$true; cleanup_complete=$Native.cleanup_complete;
        active_after_cleanup=$Native.active_after_cleanup; launcher_exitcode=$LauncherExitcode;
        child_exitcode=$Native.child_exitcode; native_outcome=$Native.outcome;
        capture_status='COMPLETE'; result_status='INVALID'; passed=$false}
}

function Invoke-C3Batch {
    param(
        [Parameter(Mandatory)][string[]]$StageIds,
        [Parameter(Mandatory)][string]$OutputRoot,
        [Parameter(Mandatory)][scriptblock]$InvokeStage,
        [Parameter(Mandatory)][ValidateSet('M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN')]
        [string]$Scope,
        [Parameter(Mandatory)][System.Collections.IDictionary]$ExecutionIdentity
    )
    if($ExecutionIdentity['scope'] -cne $Scope -or $ExecutionIdentity['package_raw_sha256'] -cne $env:C2C_C3C_PACKAGE_SHA256 -or $ExecutionIdentity['approval_receipt_raw_sha256'] -cne $env:C2C_C3C_APPROVAL_SHA256 -or $ExecutionIdentity['authorization_raw_sha256'] -cne $env:C2C_C3C_AUTHORIZATION_SHA256){throw 'EXACT_C3C_AUTHORITY_REQUIRED'}
    # InvokeStage is a TRUSTED adapter, responsible for identity/resource checks,
    # bounded execution, owned-process cleanup, and fsynced raw evidence FIRST.
    # This module does not implement or qualify a remote executor.
    if (-not $StageIds.Count -or @($StageIds | Select-Object -Unique).Count -ne $StageIds.Count -or
        @($StageIds | Where-Object { $_ -notmatch '^[A-Za-z0-9_-]+$' }).Count) {
        throw 'INVALID_STAGE_INVENTORY'
    }
    if ($Scope -eq 'M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN' -and
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
    $null = Write-C3Json (Join-Path $taskRoot 'batch_start.json') @{
        scope=$Scope; stage_ids=$StageIds; fresh_execution=$true; no_retry=$true
        start_utc=[DateTime]::UtcNow.ToString('o'); pid=$PID; formal_qualification=$true;formal_execution_authorized=$true;execution_identity=$ExecutionIdentity
    }
    for ($taskIndex=0; $taskIndex -lt $StageIds.Count; $taskIndex++) {
        $taskId = $StageIds[$taskIndex]
        $taskPrefix = 'stage-{0:d3}' -f $taskIndex
        try {
            $null = Write-C3Json (Join-Path $taskRoot ($taskPrefix+'-begin.json')) @{
                stage_id=$taskId; event='BEGIN'; utc=[DateTime]::UtcNow.ToString('o')
            }
            # Anything after BEGIN but before a durable result remains unfinished.
            $taskStates[$taskIndex]['status'] = 'RUNNING'
            $taskRecord = & $InvokeStage $taskId $taskRoot
            $taskResultPath = Join-Path $taskRoot ($taskPrefix+'-result.json')
            $taskHash = Write-C3Json $taskResultPath $taskRecord
            $taskReceipts += @{stage_id=$taskId; result_raw_sha256=$taskHash}
            $taskDecision = Get-C3StageDecision $taskRecord $taskId
            $taskStates[$taskIndex]['status'] = $taskDecision.status
            $taskStates[$taskIndex]['reason'] = $taskDecision.reason
            if ($taskDecision.status -cne 'PASS') { throw ('FIRST_FAILURE_STOP: '+$taskDecision.reason) }
            $null = Write-C3Json (Join-Path $taskRoot ($taskPrefix+'-end.json')) @{
                stage_id=$taskId; event='END'; result_raw_sha256=$taskHash
                utc=[DateTime]::UtcNow.ToString('o')
            }
        } catch {
            if ($taskStates[$taskIndex]['status'] -in @('NOT_RUN','RUNNING','PASS')) {
                $taskStates[$taskIndex]['status'] = 'INVALID'
            }
            # Persist STOP before returning. If STOP persistence itself fails, throw:
            # the caller must never convert missing evidence into success.
            $null = Write-C3Json (Join-Path $taskRoot 'batch_stop.json') @{
                status='STOPPED_NOT_FULL_PASS'; failed_stage=$taskId; stages=$taskStates
                receipts=$taskReceipts; scope=$Scope; execution_identity=$ExecutionIdentity; no_same_run_repair_or_retry=$true
                error_type=$_.Exception.GetType().Name; utc=[DateTime]::UtcNow.ToString('o')
            }
            throw ('C3C_BATCH_STOP: '+$taskId)
        }
    }
    $null = Write-C3Json (Join-Path $taskRoot 'batch_complete.json') @{
        status='COMPLETE'; scope=$Scope; stages=$taskStates; receipts=$taskReceipts
        formal_qualification=$true;formal_execution_authorized=$true;execution_identity=$ExecutionIdentity; utc=[DateTime]::UtcNow.ToString('o')
    }
    return @{status='COMPLETE'; scope=$Scope; output_root=$taskRoot}
}
