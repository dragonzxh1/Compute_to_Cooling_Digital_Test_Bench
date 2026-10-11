# Bounded synthetic records ONLY. Never starts Python/native helpers/workloads.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'batch.ps1')
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$taskRoot = Join-Path $taskRepo ('artifacts/liquid-recovery-v1/synthetic-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskRoot | Out-Null
$taskChecks = [Collections.Generic.List[object]]::new()
function Make-PassRecord([string]$Id) {
    return @{stage_id=$Id; source_verified=$true; environment_verified=$true
        evidence_verified=$true; primitive_consistent=$true; cleanup_complete=$true
        launcher_exitcode=0; child_exitcode=0; active_after_cleanup=0
        native_outcome='EXITED'; capture_status='COMPLETE'; result_status='PASS'; passed=$true}
}
$taskCases = @(
    @{id='pass'; field=$null; value=$null; expected=2},
    @{id='passed-false-cleanup-ok'; field='passed'; value=$false; expected=1},
    @{id='native-access-violation'; field='child_exitcode'; value=3221225477L; expected=1},
    @{id='nonzero-exit'; field='child_exitcode'; value=1; expected=1},
    @{id='launcher-exit'; field='launcher_exitcode'; value=1; expected=1},
    @{id='primitive-inconsistent'; field='primitive_consistent'; value=$false; expected=1},
    @{id='timeout'; field='native_outcome'; value='TIMEOUT'; expected=1},
    @{id='behavior-fail'; field='result_status'; value='FAIL'; expected=1},
    @{id='invalid'; field='result_status'; value='INVALID'; expected=1},
    @{id='incomplete'; field='result_status'; value='INCOMPLETE'; expected=1},
    @{id='capture-incomplete'; field='capture_status'; value='INCOMPLETE'; expected=1},
    @{id='source-drift'; field='source_verified'; value=$false; expected=1},
    @{id='environment-drift'; field='environment_verified'; value=$false; expected=1},
    @{id='evidence-invalid'; field='evidence_verified'; value=$false; expected=1},
    @{id='cleanup-invalid'; field='cleanup_complete'; value=$false; expected=1},
    @{id='live-child'; field='active_after_cleanup'; value=1; expected=1},
    @{id='string-pass'; field='passed'; value='true'; expected=1},
    @{id='string-zero'; field='child_exitcode'; value='0'; expected=1},
    @{id='array-native'; field='native_outcome'; value=@('EXITED'); expected=1},
    @{id='array-capture'; field='capture_status'; value=@('COMPLETE'); expected=1},
    @{id='array-result'; field='result_status'; value=@('PASS'); expected=1},
    @{id='truthy-cleanup'; field='cleanup_complete'; value='true'; expected=1},
    @{id='wrong-id'; field='stage_id'; value='OLD'; expected=1},
    @{id='missing-field'; field='DELETE'; value='child_exitcode'; expected=1},
    @{id='adapter-throws'; field='THROW'; value=$null; expected=1},
    @{id='adapter-malformed'; field='MALFORMED'; value=$null; expected=1},
    @{id='result-persistence-fails'; field='COLLISION'; value=$null; expected=1},
    @{id='next-begin-persistence-fails'; field='NEXT_COLLISION'; value=$null; expected=1}
)
foreach ($taskCase in $taskCases) {
    $taskCalls = [Collections.Generic.List[string]]::new()
    $taskOutput = Join-Path $taskRoot $taskCase.id
    $taskStopped = $false
    try {
        $null = Invoke-RecoveryBatch -StageIds @('FIRST','SECOND') -OutputRoot $taskOutput `
            -Scope SYNTHETIC_CONTROL_PLANE -InvokeStage {
                param($Id, $Folder)
                $taskCalls.Add($Id)
                $taskRecord = Make-PassRecord $Id
                if ($Id -eq 'FIRST') {
                    switch ($taskCase.field) {
                        'THROW' { throw 'SYNTHETIC_ADAPTER_EXCEPTION' }
                        'MALFORMED' { return 'not-a-record' }
                        'DELETE' { $taskRecord.Remove($taskCase.value) }
                        'COLLISION' { $null = Write-RecoveryJson (Join-Path $Folder 'stage-000-result.json') @{synthetic_collision=$true} }
                        'NEXT_COLLISION' { $null = Write-RecoveryJson (Join-Path $Folder 'stage-001-begin.json') @{synthetic_collision=$true} }
                        default { if ($null -ne $taskCase.field) { $taskRecord[$taskCase.field]=$taskCase.value } }
                    }
                }
                return $taskRecord
            }
    } catch { $taskStopped = $true }
    $taskShouldStop = $taskCase.id -ne 'pass'
    if ($taskCalls.Count -ne $taskCase.expected -or $taskStopped -ne $taskShouldStop) {
        throw ('SYNTHETIC_ASSERTION_FAILED: '+$taskCase.id)
    }
    if ($taskShouldStop) {
        $taskStop = Get-Content -LiteralPath (Join-Path $taskOutput 'batch_stop.json') -Raw | ConvertFrom-Json
        if ($taskStop.status -cne 'STOPPED_NOT_FULL_PASS' -or
            (Test-Path -LiteralPath (Join-Path $taskOutput 'batch_complete.json'))) {
            throw 'STOP_EVIDENCE_ASSERTION_FAILED'
        }
        if ($taskCase.id -ne 'next-begin-persistence-fails' -and
            ($taskStop.stages[1].status -cne 'NOT_RUN' -or
             (Test-Path -LiteralPath (Join-Path $taskOutput 'stage-001-begin.json')))) {
            throw 'NEXT_STAGE_WAS_NOT_BLOCKED'
        }
    }
    $taskChecks.Add(@{case_id=$taskCase.id; pass=$true; callback_calls=$taskCalls.Count
        expected_calls=$taskCase.expected; stopped=$taskStopped})
}
# No new execution is admitted on HIPPO in development scope, even a fake one.
if ([Environment]::MachineName -ieq 'HIPPO') {
    $taskCalled = [Collections.Generic.List[string]]::new()
    $taskRejected = $false
    try {
        $null = Invoke-RecoveryBatch -StageIds @('FIRST') -OutputRoot (Join-Path $taskRoot 'host-hold') `
            -Scope INDEPENDENT_DEVELOPMENT -InvokeStage { $taskCalled.Add('UNSAFE'); Make-PassRecord 'FIRST' }
    } catch { $taskRejected=$_.Exception.Message -eq 'HARD_HANG_HOST_WORKLOAD_HOLD' }
    if (-not $taskRejected -or $taskCalled.Count) { throw 'HOST_HOLD_FAILED' }
    $taskChecks.Add(@{case_id='current-host-denied'; pass=$true; callback_calls=0})
}
$taskIdentity=@{}
foreach($taskName in @('batch.ps1','verify_batch.ps1')) {
    $taskIdentity[$taskName]=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $taskName) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$null = Write-RecoveryJson (Join-Path $taskRoot 'synthetic_evidence.json') @{
    status='SYNTHETIC_CONTROL_PLANE_PASS'; count=$taskChecks.Count; checks=$taskChecks
    source_raw_hashes=$taskIdentity; python_started=$false; native_helper_started=$false
    behavioral_tests_executed=0; host_stability_proven=$false
}
Write-Output $taskRoot
