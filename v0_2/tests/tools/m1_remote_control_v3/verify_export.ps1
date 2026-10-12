# Local-safe file-copy regression only: no Python, native, model or GitHub writes.
$ErrorActionPreference='Stop'
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$taskSavedId=$env:GITHUB_RUN_ID;$taskSavedAttempt=$env:GITHUB_RUN_ATTEMPT
$taskTestId='synthetic-'+[Guid]::NewGuid().ToString('N')
$env:GITHUB_RUN_ID=$taskTestId;$env:GITHUB_RUN_ATTEMPT='1'
try {
    . (Join-Path $taskRepo 'v0_2/tests/tools/liquid_recovery_v1/batch.ps1')
    $r='stream-'+$taskTestId+'-1'
    foreach($p in @(('artifacts/liquid-recovery-v1/'+$r+'/test-export'),('artifacts/m1-autonomous-development/'+$r+'/jobs/test-export'))){
        $d=Join-Path $taskRepo $p;New-Item -ItemType Directory -Path $d -Force|Out-Null
        $null=Write-RecoveryJson (Join-Path $d 'synthetic.json') @{synthetic=$true;no_candidate_execution=$true}
    }
    & (Join-Path $PSScriptRoot 'export.ps1') -JobKey test-export
    foreach($p in @(('liquid-recovery-v1/'+$r+'/test-export/synthetic.json'),('m1-autonomous-development/'+$r+'/jobs/test-export/synthetic.json'))){
        if(-not(Test-Path -LiteralPath (Join-Path $taskRepo ('artifacts/export/test-export/'+$p)))){throw 'EXPORT_TWO_DIRECTORY_REGRESSION'}
    }
    'EXPORT_BOTH_DIRECTORIES_PASS_NO_WORKLOAD_EXECUTED'
} finally {$env:GITHUB_RUN_ID=$taskSavedId;$env:GITHUB_RUN_ATTEMPT=$taskSavedAttempt}
