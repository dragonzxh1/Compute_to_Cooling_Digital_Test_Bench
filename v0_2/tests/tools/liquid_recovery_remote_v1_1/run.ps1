param([Parameter(Mandatory)][string]$Python,
      [Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedManifestSha256)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Set-Location -LiteralPath $taskRepo
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or
   $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO') {
    throw 'INDEPENDENT_GITHUB_WINDOWS_REQUIRED'
}
if($ExpectedCommit -notmatch '^[a-f0-9]{40}$' -or (git rev-parse HEAD) -cne $ExpectedCommit -or
   $env:GITHUB_SHA -cne $ExpectedCommit) {throw 'EXECUTION_COMMIT_DRIFT'}
$taskManifestPath=Join-Path $PSScriptRoot 'execution_manifest.json'
if((Get-FileHash -LiteralPath $taskManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifestSha256) {
    throw 'REMOTE_EXECUTION_MANIFEST_DRIFT'
}
$taskManifest=Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
foreach($taskBinding in $taskManifest.remote_source_raw_hashes.PSObject.Properties) {
    if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {throw 'REMOTE_ADAPTER_SOURCE_DRIFT'}
}
$taskBundle=Join-Path $PSScriptRoot 'source_bundle.zip'
if((Get-FileHash -LiteralPath $taskBundle -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskManifest.bundle_raw_sha256) {throw 'SOURCE_BUNDLE_DRIFT'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskArchive=[IO.Compression.ZipFile]::OpenRead($taskBundle)
try {
    $taskNames=@($taskArchive.Entries | ForEach-Object FullName)
    $taskExpectedNames=@($taskManifest.bundle_entry_raw_hashes.PSObject.Properties.Name)
    if(@(Compare-Object ($taskNames|Sort-Object) ($taskExpectedNames|Sort-Object)).Count -or
       @($taskNames|Select-Object -Unique).Count -ne $taskNames.Count) {throw 'BUNDLE_ENTRY_INVENTORY_MISMATCH'}
    foreach($taskEntry in $taskArchive.Entries) {
        $taskDest=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskEntry.FullName))
        if(-not $taskDest.StartsWith($taskRepo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'BUNDLE_PATH_ESCAPE'}
        New-Item -ItemType Directory -Path (Split-Path $taskDest) -Force | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntry,$taskDest,$true)
    }
} finally {$taskArchive.Dispose()}
function Verify-RecoverySources {
    foreach($taskBinding in $taskManifest.bundle_entry_raw_hashes.PSObject.Properties) {
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {throw 'RECOVERY_SOURCE_DRIFT'}
    }
    foreach($taskBinding in $taskManifest.remote_source_raw_hashes.PSObject.Properties) {
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {throw 'REMOTE_ADAPTER_SOURCE_DRIFT'}
    }
}
Verify-RecoverySources
. (Join-Path $taskRepo 'v0_2/tests/tools/liquid_recovery_v1/batch.ps1')
$taskRoot=Join-Path $taskRepo ('artifacts/liquid-recovery-v1/remote-'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT)
$taskEnvironmentBox=[Collections.Generic.Dictionary[string,object]]::new()
$taskEnvironmentBox['identity']=$null
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
function Quote-RecoveryArgument([string]$Value) {
    $taskBuilder=[Text.StringBuilder]::new('"'); $taskSlashes=0
    foreach($taskChar in $Value.ToCharArray()) {
        if($taskChar -eq '\'){$taskSlashes++;continue}
        if($taskChar -eq '"'){$null=$taskBuilder.Append('\',2*$taskSlashes+1)}
        else {$null=$taskBuilder.Append('\',$taskSlashes)}
        $null=$taskBuilder.Append($taskChar); $taskSlashes=0
    }
    $null=$taskBuilder.Append('\',2*$taskSlashes); $null=$taskBuilder.Append('"')
    return $taskBuilder.ToString()
}
$taskStageIds=@('ENVIRONMENT','LOG_SCALAR_ADAPTER','THERMAL','HYDRAULICS_TRANSPORT_CDU','PHYSICAL_PROBE','SHORT_FEEDBACK')
$null=Invoke-RecoveryBatch -StageIds $taskStageIds -OutputRoot $taskRoot -Scope INDEPENDENT_DEVELOPMENT -InvokeStage {
    param($Id,$BatchRoot)
    Verify-RecoverySources
    $taskStageRoot=Join-Path $BatchRoot $Id
    New-Item -ItemType Directory -Path $taskStageRoot | Out-Null
    $env:C2C_RECOVERY_PROGRESS_PATH=Join-Path $taskStageRoot 'progress.jsonl'
    $taskStatus=Join-Path $taskStageRoot 'job_status.json'
    $taskStart=Join-Path $taskStageRoot 'job_start.json'
    $taskCancel=Join-Path $taskStageRoot 'cancel.request'
    $taskStdout=Join-Path $taskStageRoot 'stdout.raw'; $taskStderr=Join-Path $taskStageRoot 'stderr.raw'
    $taskArgs=@($taskStatus,$taskStart,$taskCancel,$taskStdout,$taskStderr,'120000','100','256','512',
        $Python,'-B','-m','v0_2.tests.tools.liquid_recovery_remote_v1_1.worker',$Id,$taskStageRoot)
    $taskArgLine=($taskArgs | ForEach-Object {Quote-RecoveryArgument ([string]$_)}) -join ' '
    $taskProcess=Start-Process -FilePath (Join-Path $taskRepo 'artifacts/executor-safety-v2_1/build/ControlledJob.exe') `
        -ArgumentList $taskArgLine -WindowStyle Hidden -WorkingDirectory $taskRepo `
        -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr -PassThru
    $taskVerifier=$null
    try {
        $taskTimer=[Diagnostics.Stopwatch]::StartNew()
        while(-not(Test-Path -LiteralPath (Join-Path $taskStageRoot 'ready.json'))) {
            if($taskProcess.HasExited -or $taskTimer.ElapsedMilliseconds -gt 30000) {throw 'CHILD_READY_TIMEOUT_OR_EXIT'}
            Start-Sleep -Milliseconds 50
        }
        $taskReady=Get-Content -LiteralPath (Join-Path $taskStageRoot 'ready.json') -Raw|ConvertFrom-Json
        $taskJob=Get-Content -LiteralPath $taskStart -Raw|ConvertFrom-Json
        $taskProofPath=Join-Path $taskStageRoot 'external_job_identity.json'
        $taskVerifyArgs=@($taskJob.job_name,[string]$taskReady.pid,'256','512',$taskProofPath)
        $taskVerifier=Start-Process -FilePath (Join-Path $taskRepo 'artifacts/runtime-isolation-v1/build/VerifyTarget.exe') `
            -ArgumentList (($taskVerifyArgs|ForEach-Object {Quote-RecoveryArgument ([string]$_)}) -join ' ') `
            -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskStageRoot 'verify_stdout.raw') `
            -RedirectStandardError (Join-Path $taskStageRoot 'verify_stderr.raw') -PassThru
        if(-not $taskVerifier.WaitForExit(5000) -or $taskVerifier.ExitCode -ne 0) {throw 'ACTUAL_JOB_IDENTITY_VERIFICATION_FAILED'}
        $taskProof=Get-Content -LiteralPath $taskProofPath -Raw|ConvertFrom-Json
        if($taskProof.in_target_job -ne $true -or $taskProof.actual_python_pid -ne $taskReady.pid) {throw 'ACTUAL_JOB_IDENTITY_PROOF_MISMATCH'}
        $null=Write-RecoveryJson (Join-Path $taskStageRoot 'release.json') @{
            actual_python_pid=$taskReady.pid; external_proof_raw_sha256=(Get-FileHash -LiteralPath $taskProofPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        if(-not $taskProcess.WaitForExit(130000)) {throw 'NATIVE_HELPER_TIMEOUT'}
    } catch {
        if(-not(Test-Path -LiteralPath $taskCancel)) {$null=Write-RecoveryJson $taskCancel @{requested=$true}}
        if(-not $taskProcess.WaitForExit(3000)) {$taskProcess.Kill();$null=$taskProcess.WaitForExit(2000)}
        if($null -ne $taskVerifier -and -not $taskVerifier.HasExited) {$taskVerifier.Kill();$null=$taskVerifier.WaitForExit(2000)}
        throw
    } finally {
        # Also persist failed/timeout captures before the batch STOP gate.
        $taskRawReceipts=@{}
        foreach($taskName in @('stdout.raw','stderr.raw','verify_stdout.raw','verify_stderr.raw')) {
            $taskRaw=Join-Path $taskStageRoot $taskName
            if(-not(Test-Path -LiteralPath $taskRaw)) {
                $taskRawReceipts[$taskName]=@{status='NOT_CREATED'; raw_sha256=$null}
                continue
            }
            $taskFile=[IO.File]::Open($taskRaw,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
            try {$taskFile.Flush($true)}finally{$taskFile.Dispose()}
            $taskFirstHash=(Get-FileHash -LiteralPath $taskRaw -Algorithm SHA256).Hash.ToLowerInvariant()
            if((Get-FileHash -LiteralPath $taskRaw -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskFirstHash) {throw 'RAW_HASH_READBACK_FAILED'}
            $taskRawReceipts[$taskName]=@{status='PERSISTED'; raw_sha256=$taskFirstHash}
        }
        $null=Write-RecoveryJson (Join-Path $taskStageRoot 'raw_evidence_receipts.json') $taskRawReceipts
    }
    $taskNative=Get-Content -LiteralPath $taskStatus -Raw|ConvertFrom-Json
    $taskResult=Get-Content -LiteralPath (Join-Path $taskStageRoot 'result.json') -Raw|ConvertFrom-Json
    if($taskResult.stage_id -cne $Id){throw 'WORKER_RESULT_IDENTITY_MISMATCH'}
    if($taskNative.assigned_before_resume -ne $true -or $taskNative.resumed -ne $true -or
       $taskNative.cleanup_complete -ne $true -or $taskNative.active_after_cleanup -ne 0 -or
       $taskNative.child_exitcode -ne 0 -or $taskNative.outcome -cne 'EXITED' -or $taskProcess.ExitCode -ne 0) {
        throw 'NATIVE_OR_CLEANUP_INTEGRITY_FAILURE'
    }
    Verify-RecoverySources
    if($Id -eq 'ENVIRONMENT') {
        $taskActual=$taskResult.runtime_identity
        $taskLock=Get-Content -LiteralPath (Join-Path $taskRepo 'v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json') -Raw|ConvertFrom-Json
        if($taskActual.python -cne '3.11.9' -or $taskActual.system -cne 'Windows' -or $taskActual.machine -cne 'AMD64') {throw 'REMOTE_RUNTIME_MISMATCH'}
        foreach($taskDependency in $taskLock.dependencies.PSObject.Properties) {
            if($taskActual.dependencies.PSObject.Properties[$taskDependency.Name].Value -cne $taskDependency.Value) {throw 'REMOTE_DEPENDENCY_DRIFT'}
        }
        $taskEnvironmentBox['identity']=ConvertTo-Json -InputObject $taskActual -Depth 15 -Compress
        $taskRegistration=Join-Path $BatchRoot 'independent_environment_registration.json'
        $env:C2C_RECOVERY_REGISTRATION_SHA256=Write-RecoveryJson $taskRegistration @{
            scope='GENERIC_LIQUID_COOLING_DEVELOPMENT_SMOKE'; status='REVIEWED_FOR_SMOKE_EXECUTION'
            independent_execution_location='GITHUB_HOSTED_WINDOWS'; runtime_identity=$taskActual
            source_inventory_raw_sha256=$taskManifest.original_source_inventory_raw_sha256
            admission_basis='MECHANICAL_ENVIRONMENT_AND_EXTERNAL_JOB_CHECK_UNDER_USER_REMOTE_SMOKE_AUTHORIZATION'
            old_m1_environment_replaced=$false; formal_qualification=$false
            remote_execution_manifest_raw_sha256=$ExpectedManifestSha256; remote_adapter_version='v1.1'
        }
        $env:C2C_RECOVERY_REGISTRATION_PATH=$taskRegistration
    }
    if((ConvertTo-Json -InputObject $taskResult.runtime_identity_after -Depth 15 -Compress) -cne $taskEnvironmentBox['identity']) {throw 'REMOTE_ENVIRONMENT_AFTER_DRIFT'}
    return @{stage_id=$Id; source_verified=$true; environment_verified=$true; evidence_verified=$true
        primitive_consistent=$true; cleanup_complete=$taskNative.cleanup_complete
        active_after_cleanup=$taskNative.active_after_cleanup; launcher_exitcode=$taskProcess.ExitCode
        child_exitcode=$taskNative.child_exitcode; native_outcome=$taskNative.outcome
        capture_status='COMPLETE'; result_status=$taskResult.status; passed=($taskResult.status -ceq 'PASS')}
}
Verify-RecoverySources
Write-Output ('REMOTE_SMOKE_COMPLETE: '+$taskRoot)
