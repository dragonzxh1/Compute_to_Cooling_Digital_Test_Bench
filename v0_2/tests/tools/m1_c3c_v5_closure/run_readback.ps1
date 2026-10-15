param([Parameter(Mandatory)][string]$Python,
      [Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedManifestSha256)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Target='CHECKS'
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Set-Location -LiteralPath $taskRepo
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'INDEPENDENT_HOST_ONLY'}
if($ExpectedCommit -notmatch '^[a-f0-9]{40}$' -or (git rev-parse HEAD) -cne $ExpectedCommit -or $env:GITHUB_SHA -cne $ExpectedCommit){throw 'SOURCE_COMMIT_MISMATCH'}
$taskManifestPath=Join-Path $PSScriptRoot 'control.json'
if((Get-FileHash $taskManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifestSha256){throw 'MANIFEST_DRIFT'}
$taskManifest=Get-Content $taskManifestPath -Raw|ConvertFrom-Json
function Verify-AtomicitySources {
    foreach($binding in $taskManifest.source_hashes.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $taskRepo $binding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $binding.Value){throw ('SOURCE_DRIFT '+$binding.Name)}}
    $parent=Get-Content -LiteralPath (Join-Path $taskRepo $taskManifest.protected_parent_manifest_path) -Raw|ConvertFrom-Json
    foreach($map in @($parent.bundle_entry_raw_hashes,$parent.remote_source_raw_hashes)){
        foreach($binding in $map.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $taskRepo $binding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $binding.Value){throw ('SEALED_PARENT_SOURCE_DRIFT '+$binding.Name)}}
    }
}
Verify-AtomicitySources
. ./v0_2/tests/tools/m1_remote_control_v3/restore_snapshot.ps1
$null=Restore-M1Snapshot -Repo $taskRepo -ExpectedManifestSha256 '6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93'
Verify-AtomicitySources
. ./v0_2/tests/tools/liquid_recovery_v1/batch.ps1
$taskBuild=Join-Path $taskRepo 'artifacts/m1-remote-executor-v1/build'
if(-not(Test-Path (Join-Path $taskBuild 'build_identity.json'))){& ./v0_2/tests/tools/m1_remote_executor_v1/build.ps1}
$taskRoot=Join-Path $taskRepo ('artifacts/m1-c3c-v5-closure/'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT+'-'+$Target)
New-Item -ItemType Directory -Path $taskRoot|Out-Null
$taskStart=Join-Path $taskRoot 'job_start.json';$taskStatus=Join-Path $taskRoot 'job_status.json';$taskCancel=Join-Path $taskRoot 'cancel.request'
$taskStdout=Join-Path $taskRoot 'stdout.raw';$taskStderr=Join-Path $taskRoot 'stderr.raw'
function Quote-Argument([string]$Value){
    $b=[Text.StringBuilder]::new('"');$slashes=0
    foreach($c in $Value.ToCharArray()){if($c -eq '\'){$slashes++;continue};if($c -eq '"'){$null=$b.Append('\',2*$slashes+1)}else{$null=$b.Append('\',$slashes)};$null=$b.Append($c);$slashes=0}
    $null=$b.Append('\',2*$slashes);$null=$b.Append('"');return $b.ToString()
}
$taskArgs=@($taskStatus,$taskStart,$taskCancel,$taskStdout,$taskStderr,'480000','2500','256','512',$Python,'-B','-m','v0_2.tests.tools.m1_c3c_v5_closure.readback_worker',$Target,$taskRoot,$ExpectedManifestSha256)
$taskProcess=Start-Process -FilePath (Join-Path $taskBuild 'ControlledJob.exe') -ArgumentList (($taskArgs|ForEach-Object{Quote-Argument ([string]$_)}) -join ' ') -WindowStyle Hidden -WorkingDirectory $taskRepo -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr -PassThru
$taskVerifier=$null
try {
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while(-not(Test-Path (Join-Path $taskRoot 'ready.json'))){if($taskProcess.HasExited -or $timer.ElapsedMilliseconds -gt 30000){throw 'READY_TIMEOUT'};Start-Sleep -Milliseconds 50}
    $ready=Get-Content (Join-Path $taskRoot 'ready.json') -Raw|ConvertFrom-Json
    $job=Get-Content $taskStart -Raw|ConvertFrom-Json
    $proofPath=Join-Path $taskRoot 'external_job_identity.json'
    $verifyArgs=@($job.job_name,[string]$ready.pid,'256','512',$proofPath,'2500')
    $taskVerifier=Start-Process -FilePath (Join-Path $taskBuild 'VerifyTarget.exe') -ArgumentList (($verifyArgs|ForEach-Object{Quote-Argument ([string]$_)}) -join ' ') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot 'verify_stdout.raw') -RedirectStandardError (Join-Path $taskRoot 'verify_stderr.raw') -PassThru
    if(-not $taskVerifier.WaitForExit(5000) -or $taskVerifier.ExitCode -ne 0){throw 'PID_JOB_VERIFICATION_FAILED'}
    $proof=Get-Content $proofPath -Raw|ConvertFrom-Json
    if(-not $proof.in_target_job -or $proof.actual_python_pid -ne $ready.pid -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 256 -or $proof.job_mb -ne 512){throw 'PID_JOB_LIMIT_MISMATCH'}
    $null=Write-RecoveryJson (Join-Path $taskRoot 'release.json') @{actual_python_pid=$ready.pid;external_proof_raw_sha256=(Get-FileHash $proofPath -Algorithm SHA256).Hash.ToLowerInvariant()}
    if(-not $taskProcess.WaitForExit(495000)){throw 'EXECUTION_TIMEOUT'}
} catch {
    if(-not(Test-Path $taskCancel)){$null=Write-RecoveryJson $taskCancel @{requested=$true}}
    if(-not $taskProcess.WaitForExit(3000)){$taskProcess.Kill();$null=$taskProcess.WaitForExit(2000)}
    if($null -ne $taskVerifier -and -not $taskVerifier.HasExited){$taskVerifier.Kill();$null=$taskVerifier.WaitForExit(2000)}
    throw
} finally {
    $captures=[ordered]@{}
    foreach($name in @('stdout.raw','stderr.raw','verify_stdout.raw','verify_stderr.raw')){$p=Join-Path $taskRoot $name;if(Test-Path $p){$s=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read);try{$s.Flush($true)}finally{$s.Dispose()};$h=(Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant();if((Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $h){throw 'CAPTURE_READBACK_FAILED'};$captures[$name]=@{bytes=(Get-Item $p).Length;raw_sha256=$h;status='PERSISTED'}}else{$captures[$name]=@{status='NOT_CREATED'}}}
    $null=Write-RecoveryJson (Join-Path $taskRoot 'raw_receipts.json') $captures
}
$native=Get-Content $taskStatus -Raw|ConvertFrom-Json
if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED' -or $taskProcess.ExitCode -ne 0){throw 'NATIVE_EXECUTION_INVALID'}
Verify-AtomicitySources
$result=Get-Content (Join-Path $taskRoot 'result.json') -Raw|ConvertFrom-Json
$expected='C3C_V5_FINAL_PACKAGE_READBACK_PASS'
if($result.status -cne $expected -or $result.source_commit -cne $ExpectedCommit -or $result.control_manifest_sha256 -cne $ExpectedManifestSha256){throw 'DEVELOPMENT_ASSERTION_STOP'}
$null=Write-RecoveryJson (Join-Path $taskRoot 'execution_acceptance.json') @{status=$result.status;source_commit=$ExpectedCommit;control_manifest_sha256=$ExpectedManifestSha256;actual_job_verified=$true;cleanup_verified=$true;candidate_behavioral_execution=$false;formal_qualification=$false}
Write-Output ($result|ConvertTo-Json -Depth 12)
