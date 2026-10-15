param([Parameter(Mandatory)][string]$Python,
      [Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedManifestSha256,
      [Parameter(Mandatory)][ValidateSet('CHECKS','REFERENCE','SELECT','SPLIT','PREFIX','STARTUP','SCHEMA','REFERENCE_GATE','FINAL')][string]$Mode,
      [string]$JobKey='stage',
      [string]$IndicesCsv,
      [string]$RuntimePlanPath,
      [string]$ExpectedPlanSha256,
      [ValidateSet('STRICT','CAMPAIGN')][string]$MemoryProfile='STRICT')
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
$taskManifestPath=Join-Path $taskRepo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json'
if((Get-FileHash -LiteralPath $taskManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifestSha256) {
    throw 'REMOTE_EXECUTION_MANIFEST_DRIFT'
}
$taskManifest=Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
$env:C2C_M1_EXECUTION_MANIFEST_SHA256=$ExpectedManifestSha256
$env:C2C_C3C_PACKAGE_SHA256=$ExpectedManifestSha256
foreach($key in @('C2C_C3C_APPROVAL_B64','C2C_C3C_AUTHORIZATION_B64','C2C_C3C_APPROVAL_SHA256','C2C_C3C_AUTHORIZATION_SHA256')){if(-not [Environment]::GetEnvironmentVariable($key)){throw 'EXACT_USER_APPROVAL_AND_EXECUTION_AUTHORIZATION_REQUIRED'}}
foreach($taskBinding in $taskManifest.source_raw_sha256.PSObject.Properties) {
    if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {throw 'REMOTE_ADAPTER_SOURCE_DRIFT'}
}
$taskBundle=Join-Path $taskRepo $taskManifest.bundle_path
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
    foreach($taskBinding in $taskManifest.source_raw_sha256.PSObject.Properties) {
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value) {throw 'REMOTE_ADAPTER_SOURCE_DRIFT'}
    }
}
Verify-RecoverySources
. (Join-Path $taskRepo 'v0_2/tests/tools/m1_c3c_v5/batch.ps1')
$taskDispatchIdentity=Get-C3DispatchIdentity
$taskBuildRoot=Join-Path $taskRepo 'artifacts/m1-remote-executor-v1/build'
if(-not(Test-Path -LiteralPath (Join-Path $taskBuildRoot 'build_identity.json'))){& (Join-Path $taskRepo 'v0_2/tests/tools/m1_remote_executor_v1/build.ps1')}
$taskBuildIdentity=Get-Content -LiteralPath (Join-Path $taskBuildRoot 'build_identity.json') -Raw|ConvertFrom-Json
$taskBinaryHashes=[ordered]@{}
foreach($taskName in @('ControlledJob','VerifyTarget')){
    $taskExe=Join-Path $taskBuildRoot ($taskName+'.exe')
    $taskSha=(Get-FileHash -LiteralPath $taskExe -Algorithm SHA256).Hash.ToLowerInvariant()
    if($taskSha -cne $taskBuildIdentity.source_and_binary_hashes.PSObject.Properties[$taskName].Value.binary_raw_sha256){throw 'REMOTE_EXECUTOR_BINARY_DRIFT'}
    $taskBinaryHashes['artifacts/m1-remote-executor-v1/build/'+$taskName+'.exe']=$taskSha
}
$taskProcessMb=if($MemoryProfile -ceq 'STRICT'){256}else{1024}
$taskJobMb=if($MemoryProfile -ceq 'STRICT'){512}else{2048}
$taskRunKey='stream-'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT
$taskBaseRoot=Join-Path $taskRepo ('artifacts/m1-autonomous-development/'+$taskRunKey+'/cases')
$env:C2C_M1_REFERENCE_ROOT=$taskBaseRoot
$taskRuntimeInputs=[ordered]@{}
$taskStageIds=@('ENVIRONMENT','INPUT_INTEGRITY')
if($JobKey -notmatch '^[A-Za-z0-9_-]+$'){throw 'JOB_IDENTITY_DENIED'}
if($Mode -eq 'CHECKS') {
    $taskStageIds=@($taskManifest.check_stage_ids)
} else {
    . (Join-Path $taskRepo 'v0_2/tests/tools/m1_c3c_v5/campaign_plan.ps1')
    $taskDynamic=Get-C3Stages -Repo $taskRepo -Mode $Mode -IndicesCsv $IndicesCsv -RuntimePlanPath $RuntimePlanPath -ExpectedPlanSha $ExpectedPlanSha256 -JobKey $JobKey -RunKey $taskRunKey -Commit $ExpectedCommit -ManifestSha $ExpectedManifestSha256
    $taskStageIds+=@($taskDynamic.stages)
    foreach($taskBinding in $taskDynamic.input_hashes.GetEnumerator()){$taskRuntimeInputs[$taskBinding.Key]=$taskBinding.Value}
}
$taskRoot=Join-Path $taskRepo ('artifacts/liquid-recovery-v1/'+$taskRunKey+'/'+$JobKey)
$env:C2C_M1_CASE_ROOT=Join-Path $taskRepo ('artifacts/m1-autonomous-development/'+$taskRunKey+'/jobs/'+$JobKey)
New-Item -ItemType Directory -Path $env:C2C_M1_CASE_ROOT | Out-Null
$taskEnvironmentBox=[Collections.Generic.Dictionary[string,object]]::new()
$taskEnvironmentBox['identity']=$null
$taskEnvironmentBox['execution_identity']=$taskDispatchIdentity
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
$taskInvokeStage={
    param($Id,$BatchRoot)
    Write-Host ('STAGE_BEGIN '+$Id+' UTC='+[DateTime]::UtcNow.ToString('o'))
    Verify-RecoverySources
    foreach($taskBinding in $taskBinaryHashes.GetEnumerator()){
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Key) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value){throw 'REMOTE_EXECUTOR_BINARY_DRIFT'}
    }
    foreach($taskBinding in $taskRuntimeInputs.GetEnumerator()) {
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $taskBinding.Key) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskBinding.Value){throw 'FRESH_BASE_EVIDENCE_DRIFT'}
    }
    $taskStageRoot=Join-Path $BatchRoot $Id
    New-Item -ItemType Directory -Path $taskStageRoot | Out-Null
    $taskStatus=Join-Path $taskStageRoot 'job_status.json'
    $taskStart=Join-Path $taskStageRoot 'job_start.json'
    $taskCancel=Join-Path $taskStageRoot 'cancel.request'
    $taskStdout=Join-Path $taskStageRoot 'stdout.raw'; $taskStderr=Join-Path $taskStageRoot 'stderr.raw'
    $taskWallMs=[string]($taskManifest.resource_policy.child_wall_seconds*1000)
    $taskArgs=@($taskStatus,$taskStart,$taskCancel,$taskStdout,$taskStderr,$taskWallMs,'2500',[string]$taskProcessMb,[string]$taskJobMb,
        $Python,'-B','-m','v0_2.tests.tools.m1_c3c_v5.worker',$Id,$taskStageRoot)
    $taskArgLine=($taskArgs | ForEach-Object {Quote-RecoveryArgument ([string]$_)}) -join ' '
    $taskProcess=Start-Process -FilePath (Join-Path $taskBuildRoot 'ControlledJob.exe') `
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
        $taskVerifyArgs=@($taskJob.job_name,[string]$taskReady.pid,[string]$taskProcessMb,[string]$taskJobMb,$taskProofPath,'2500')
        $taskVerifier=Start-Process -FilePath (Join-Path $taskBuildRoot 'VerifyTarget.exe') `
            -ArgumentList (($taskVerifyArgs|ForEach-Object {Quote-RecoveryArgument ([string]$_)}) -join ' ') `
            -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskStageRoot 'verify_stdout.raw') `
            -RedirectStandardError (Join-Path $taskStageRoot 'verify_stderr.raw') -PassThru
        if(-not $taskVerifier.WaitForExit(5000) -or $taskVerifier.ExitCode -ne 0) {throw 'ACTUAL_JOB_IDENTITY_VERIFICATION_FAILED'}
        $taskProof=Get-Content -LiteralPath $taskProofPath -Raw|ConvertFrom-Json
        if($taskProof.in_target_job -ne $true -or $taskProof.actual_python_pid -ne $taskReady.pid -or
           $taskProof.cpu_rate -ne 2500 -or $taskProof.process_mb -ne $taskProcessMb -or $taskProof.job_mb -ne $taskJobMb){throw 'ACTUAL_JOB_IDENTITY_PROOF_MISMATCH'}
        $null=Write-C3Json (Join-Path $taskStageRoot 'release.json') @{
            actual_python_pid=$taskReady.pid; external_proof_raw_sha256=(Get-FileHash -LiteralPath $taskProofPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        $taskSamples=@()
        while(-not $taskProcess.WaitForExit(5000)) {
            if($taskTimer.ElapsedMilliseconds -gt [long]$taskWallMs+15000){throw 'NATIVE_HELPER_TIMEOUT'}
            try {
                $taskActualProcess=Get-Process -Id $taskReady.pid -ErrorAction Stop
                $taskSamples+=@{pid=$taskReady.pid;utc=[DateTime]::UtcNow.ToString('o');private_bytes=$taskActualProcess.PrivateMemorySize64;working_set_bytes=$taskActualProcess.WorkingSet64}
            } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
        $null=Write-C3Json (Join-Path $taskStageRoot 'external_memory_samples.json') @{
            samples=$taskSamples;actual_python_pid=$taskReady.pid;measurement='EXTERNAL_PROCESS_METRICS_NOT_MODEL_SIGNALS'
        }
    } catch {
        if(-not(Test-Path -LiteralPath $taskCancel)) {$null=Write-C3Json $taskCancel @{requested=$true}}
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
        $null=Write-C3Json (Join-Path $taskStageRoot 'raw_evidence_receipts.json') $taskRawReceipts
    }
    $taskNative=Get-Content -LiteralPath $taskStatus -Raw|ConvertFrom-Json
    if($taskNative.assigned_before_resume -ne $true -or $taskNative.resumed -ne $true -or
       $taskNative.cleanup_complete -ne $true -or $taskNative.active_after_cleanup -ne 0 -or
       $taskNative.child_exitcode -ne 0 -or $taskNative.outcome -cne 'EXITED' -or $taskProcess.ExitCode -ne 0) {
        $null=Write-C3Json (Join-Path $taskStageRoot 'native_failure_audit.json') @{
            stage_id=$Id;native=$taskNative;launcher_exitcode=$taskProcess.ExitCode
            behavioral_adjudication='NOT_MADE';reason='NATIVE_EXECUTION_NOT_COMPLETE'
            control_manifest_raw_sha256=$ExpectedManifestSha256
        }
        throw 'NATIVE_OR_CLEANUP_INTEGRITY_FAILURE'
    }
    $taskResult=Get-Content -LiteralPath (Join-Path $taskStageRoot 'result.json') -Raw|ConvertFrom-Json
    if($taskResult.stage_id -cne $Id){throw 'WORKER_RESULT_IDENTITY_MISMATCH'}
    if($taskResult.status -cne 'INVALID' -and ($taskResult.scope -cne 'M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN' -or -not $taskResult.formal_execution_authorized -or $taskResult.execution_identity.package_raw_sha256 -cne $ExpectedManifestSha256)){throw 'C3C_STAGE_AUTHORITY_MISMATCH'}
    Verify-RecoverySources
    if($taskResult.status -ceq 'INVALID') {
        $null=Write-C3Json (Join-Path $taskStageRoot 'invalid_failure_audit.json') @{
            stage_id=$Id;status='INVALID';behavioral_adjudication='NOT_MADE'
            original_result_raw_sha256=(Get-FileHash -LiteralPath (Join-Path $taskStageRoot 'result.json')).Hash.ToLowerInvariant()
            exact_runtime_authority_not_earned=$true
        }
        return (Get-C3InvalidStageRecord -StageId $Id -Result $taskResult -Native $taskNative -LauncherExitcode $taskProcess.ExitCode)
    }
    if($Id -eq 'ENVIRONMENT') {
        $taskActual=$taskResult.runtime_identity_before
        $taskLock=Get-Content -LiteralPath (Join-Path $taskRepo 'v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json') -Raw|ConvertFrom-Json
        if($taskActual.python -cne '3.11.9' -or $taskActual.system -cne 'Windows' -or $taskActual.machine -cne 'AMD64') {throw 'REMOTE_RUNTIME_MISMATCH'}
        foreach($taskDependency in $taskLock.dependencies.PSObject.Properties) {
            if($taskActual.dependencies.PSObject.Properties[$taskDependency.Name].Value -cne $taskDependency.Value) {throw 'REMOTE_DEPENDENCY_DRIFT'}
        }
        $taskEnvironmentBox['identity']=ConvertTo-Json -InputObject $taskActual -Depth 15 -Compress
        $taskEnvironmentBox['execution_identity']=@{}
        foreach($binding in $taskResult.execution_identity.PSObject.Properties){$taskEnvironmentBox['execution_identity'][$binding.Name]=$binding.Value}
        $taskRegistration=Join-Path $BatchRoot 'formal_runtime_bindings.json'
        $env:C2C_C3C_RUNTIME_BINDINGS_SHA256=Write-C3Json $taskRegistration @{
            scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN'
            execution_identity=$taskEnvironmentBox['execution_identity']
            runtime_identity=$taskActual
            runtime_input_raw_hashes=$taskRuntimeInputs
            runtime_binary_raw_hashes=$taskBinaryHashes
        }
        $env:C2C_C3C_RUNTIME_BINDINGS_PATH=$taskRegistration
    }
    if((ConvertTo-Json -InputObject $taskResult.runtime_identity_after -Depth 15 -Compress) -cne $taskEnvironmentBox['identity']) {throw 'REMOTE_ENVIRONMENT_AFTER_DRIFT'}
    Write-Host ('STAGE_END '+$Id+' RESULT='+$taskResult.status+' UTC='+[DateTime]::UtcNow.ToString('o'))
    return @{stage_id=$Id; source_verified=$true; environment_verified=$true; evidence_verified=$true
        primitive_consistent=$true; cleanup_complete=$taskNative.cleanup_complete
        active_after_cleanup=$taskNative.active_after_cleanup; launcher_exitcode=$taskProcess.ExitCode
        child_exitcode=$taskNative.child_exitcode; native_outcome=$taskNative.outcome
        capture_status='COMPLETE'; result_status=$taskResult.status; passed=($taskResult.status -ceq 'PASS')}
}
$null=Invoke-C3Batch -StageIds $taskStageIds -OutputRoot $taskRoot -Scope M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN -ExecutionIdentity $taskEnvironmentBox['execution_identity'] -InvokeStage $taskInvokeStage
if($Mode -eq 'PREFIX'){
    $taskIndex=[int]$IndicesCsv
    $taskCaseDir=Join-Path $taskBaseRoot ('{0:d3}' -f $taskIndex)
    $taskInventory=Get-Content -LiteralPath (Join-Path $taskCaseDir 'prefix_inventory.json') -Raw|ConvertFrom-Json
    $taskSerial=0
    while($true){
        $taskRemaining=@($taskInventory.selected_prefix_lengths|Where-Object{-not(Test-Path -LiteralPath (Join-Path $taskCaseDir ('prefix-{0:d6}-result.json' -f $_)))})
        if(-not $taskRemaining.Count){break}
        $taskSerial++
        $taskRequested=@($taskRemaining|Select-Object -First 6)
        $env:C2C_M1_PREFIX_BATCH_LENGTHS=ConvertTo-Json -InputObject $taskRequested -Compress
        $taskId='CASE-{0:d3}-PREFIX_BATCH-{1:d3}' -f $taskIndex,$taskSerial
        $taskBatchRoot=Join-Path $taskRepo ('artifacts/liquid-recovery-v1/'+$taskRunKey+'/'+$JobKey+('-batch-{0:d3}' -f $taskSerial))
        $null=Invoke-C3Batch -StageIds @($taskId) -OutputRoot $taskBatchRoot -Scope M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN -ExecutionIdentity $taskEnvironmentBox['execution_identity'] -InvokeStage $taskInvokeStage
        $taskPayload=(Get-Content -LiteralPath (Join-Path $taskBatchRoot ($taskId+'/result.json')) -Raw|ConvertFrom-Json).payload
        if(-not @($taskPayload.completed_lengths).Count -or @($taskPayload.completed_lengths|Where-Object{$_ -notin $taskRequested}).Count){throw 'PREFIX_BATCH_COVERAGE_IDENTITY_INVALID'}
    }
    foreach($taskLength in $taskInventory.selected_prefix_lengths){
        $taskResult=Get-Content -LiteralPath (Join-Path $taskCaseDir ('prefix-{0:d6}-result.json' -f $taskLength)) -Raw|ConvertFrom-Json
        if($taskResult.status -cne 'PASS' -or $taskResult.starts_from_t0 -ne $true -or $taskResult.compared_complete_frames -ne $taskLength -or @($taskResult.replayed_prefix_lengths).Count -ne 1 -or $taskResult.replayed_prefix_lengths[0] -ne $taskLength){throw 'PREFIX_CASE_INCOMPLETE_OR_FAIL'}
    }
    $taskInvReceipt=Get-Content -LiteralPath (Join-Path $taskCaseDir 'prefix_inventory_receipt.json') -Raw|ConvertFrom-Json
    $null=Write-C3Json (Join-Path $taskCaseDir 'prefix_result.json') @{
        status='PASS';inventory_receipt=$taskInvReceipt;selected_count=@($taskInventory.selected_prefix_lengths).Count;failures=@()
    }
}
Verify-RecoverySources
Write-Output ('C3C_CONTROLLED_STAGE_COMPLETE: '+$taskRoot)
