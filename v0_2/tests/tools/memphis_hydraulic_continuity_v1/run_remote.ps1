param([Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedManifestSha256,
      [Parameter(Mandatory)][ValidateSet('baseline','hydraulic','recovery','final')][string]$StudyGroup)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or
   $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'ISOLATED_REMOTE_ONLY'}
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Set-Location -LiteralPath $taskRepo
if($ExpectedCommit -notmatch '^[a-f0-9]{40}$' -or (git rev-parse HEAD) -cne $ExpectedCommit -or $env:GITHUB_SHA -cne $ExpectedCommit){throw 'COMMIT_DRIFT'}
$taskManifestPath=Join-Path $PSScriptRoot 'source_manifest.json'
if((Get-FileHash -LiteralPath $taskManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifestSha256){throw 'MANIFEST_DRIFT'}
$taskManifest=Get-Content -LiteralPath $taskManifestPath -Raw|ConvertFrom-Json
function Verify-IntegrationSources {
    foreach($b in $taskManifest.source_raw_sha256.PSObject.Properties){
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $b.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw ('INTEGRATION_SOURCE_DRIFT '+$b.Name)}
    }
    foreach($b in $taskManifest.v1_source_raw_sha256.PSObject.Properties){
        if((Get-FileHash -LiteralPath (Join-Path $taskRepo $b.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw ('V1_BASELINE_SOURCE_DRIFT '+$b.Name)}
    }
    $f=Get-Content -LiteralPath 'artifacts/m1-c3c-v5-freeze/executable_proposal.json' -Raw|ConvertFrom-Json
    foreach($b in $f.source_raw_sha256.PSObject.Properties){
        if((Get-FileHash -LiteralPath $b.Name -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw ('FROZEN_SOURCE_DRIFT '+$b.Name)}
    }
    if((Get-FileHash 'v0_2/tests/tools/m1_engine_v4/engine.py' -Algorithm SHA256).Hash.ToLowerInvariant() -cne '70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce'){throw 'CANDIDATE_DRIFT'}
}
Verify-IntegrationSources
& ./v0_2/tests/tools/m1_remote_executor_v1/build.ps1
if($LASTEXITCODE -ne 0){throw 'REMOTE_EXECUTOR_BUILD_FAILURE'}
. ./v0_2/tests/tools/liquid_recovery_v1/batch.ps1
$taskBuild=Join-Path $taskRepo 'artifacts/m1-remote-executor-v1/build'
$taskPython=(Get-Command python).Source
$taskRoot=Join-Path $taskRepo ('artifacts/m1-autonomous-development/memphis-hydraulic-continuity-v1-'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT+'/'+$StudyGroup)
New-Item -ItemType Directory -Path $taskRoot | Out-Null
$taskEnvEvidence=[ordered]@{commit=$ExpectedCommit;manifest_raw_sha256=$ExpectedManifestSha256;
  image=$env:ImageVersion;runner=$env:RUNNER_NAME;python_executable=$taskPython;formal=$false;cpu_rate=2500;process_mb=1024;job_mb=2048;wall_seconds=480}
$null=Write-RecoveryJson (Join-Path $taskRoot 'environment_registration.json') $taskEnvEvidence
function Quote-Arg([string]$Value){
    $b=[Text.StringBuilder]::new('"');$slashes=0
    foreach($c in $Value.ToCharArray()){
        if($c -eq '\'){$slashes++;continue}
        if($c -eq '"'){$null=$b.Append('\',2*$slashes+1)}else{$null=$b.Append('\',$slashes)}
        $null=$b.Append($c);$slashes=0
    }
    $null=$b.Append('\',2*$slashes);$null=$b.Append('"');return $b.ToString()
}
$taskReceipts=@()
$taskRegistration=Get-Content (Join-Path $PSScriptRoot 'registration.json') -Raw|ConvertFrom-Json
$taskStages=@($taskRegistration.cases|Where-Object group -ceq $StudyGroup|ForEach-Object id)

foreach($taskStage in $taskStages){
    Verify-IntegrationSources
    $taskDir=Join-Path $taskRoot $taskStage
    New-Item -ItemType Directory -Path $taskDir|Out-Null
    $status=Join-Path $taskDir 'job_status.json';$start=Join-Path $taskDir 'job_start.json';$cancel=Join-Path $taskDir 'cancel.request'
    $stdout=Join-Path $taskDir 'stdout.raw';$stderr=Join-Path $taskDir 'stderr.raw'
    $argsList=@($status,$start,$cancel,$stdout,$stderr,'480000','2500','1024','2048',
        $taskPython,'-B','-m','v0_2.tests.tools.memphis_hydraulic_continuity_v1.worker',$taskStage,$taskDir)
    $taskProcess=Start-Process -FilePath (Join-Path $taskBuild 'ControlledJob.exe') -WindowStyle Hidden `
        -ArgumentList (($argsList|ForEach-Object{Quote-Arg ([string]$_)}) -join ' ') -WorkingDirectory $taskRepo `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    $timer=[Diagnostics.Stopwatch]::StartNew()
    try{
        while(-not(Test-Path -LiteralPath (Join-Path $taskDir 'ready.json'))){
            if($taskProcess.HasExited -or $timer.ElapsedMilliseconds -gt 30000){throw 'CHILD_READY_TIMEOUT_OR_EXIT'}
            Start-Sleep -Milliseconds 50
        }
        $ready=Get-Content (Join-Path $taskDir 'ready.json') -Raw|ConvertFrom-Json
        $job=Get-Content -LiteralPath $start -Raw|ConvertFrom-Json
        $proof=Join-Path $taskDir 'external_job_identity.json'
        $verifyArgs=@($job.job_name,[string]$ready.pid,'1024','2048',$proof,'2500')
        $verifier=Start-Process -FilePath (Join-Path $taskBuild 'VerifyTarget.exe') -WindowStyle Hidden `
            -ArgumentList (($verifyArgs|ForEach-Object{Quote-Arg ([string]$_)}) -join ' ') `
            -RedirectStandardOutput (Join-Path $taskDir 'verify_stdout.raw') -RedirectStandardError (Join-Path $taskDir 'verify_stderr.raw') -PassThru
        if(-not $verifier.WaitForExit(5000) -or $verifier.ExitCode -ne 0){throw 'ACTUAL_JOB_IDENTITY_FAILED'}
        $p=Get-Content -LiteralPath $proof -Raw|ConvertFrom-Json
        if(-not $p.in_target_job -or $p.actual_python_pid -ne $ready.pid -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048){throw 'ACTUAL_LIMIT_PROOF_MISMATCH'}
        $null=Write-RecoveryJson (Join-Path $taskDir 'release.json') @{actual_python_pid=$ready.pid;external_proof_raw_sha256=(Get-FileHash $proof -Algorithm SHA256).Hash.ToLowerInvariant()}
        while(-not $taskProcess.WaitForExit(5000)){
            if($timer.ElapsedMilliseconds -gt 495000){throw 'NATIVE_TIMEOUT'}
            $lines=Get-Content -LiteralPath $stdout -Tail 1 -ErrorAction SilentlyContinue
            if($lines){Write-Host ($taskStage+' '+$lines)}
        }
    }catch{
        if(-not(Test-Path -LiteralPath $cancel)){$null=Write-RecoveryJson $cancel @{requested=$true}}
        if(-not $taskProcess.WaitForExit(3000)){$taskProcess.Kill();$null=$taskProcess.WaitForExit(2000)}
        throw
    }
    $native=Get-Content -LiteralPath $status -Raw|ConvertFrom-Json
    if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or
       $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED' -or $taskProcess.ExitCode -ne 0){throw ('NATIVE_OR_TEST_FAILURE '+$taskStage)}
    $result=Get-Content (Join-Path $taskDir 'result.json') -Raw|ConvertFrom-Json
    if($result.stage -cne $taskStage -or $result.status -cne 'PASS'){throw ('INTEGRATION_STAGE_NOT_PASS '+$taskStage)}
    Verify-IntegrationSources
    $taskReceipts+=@{stage=$taskStage;status=$result.status;actual_python_pid=$ready.pid;cleanup_complete=$true;active_after_cleanup=0}
    Write-Host ('INTEGRATION_STAGE_END '+$taskStage+' PASS')
}
$null=Write-RecoveryJson (Join-Path $taskRoot 'execution_receipts.json') @{stages=$taskReceipts;source_commit=$ExpectedCommit;manifest_sha256=$ExpectedManifestSha256}
# Full raw journal stays in the raw artifact. Small analysis copy is separate,
# never mislabeled as the complete raw archive. Hash every original file first.
$taskRecords=foreach($f in Get-ChildItem -LiteralPath $taskRoot -File -Recurse){
 @{path=[IO.Path]::GetRelativePath($taskRoot,$f.FullName).Replace('\','/');bytes=$f.Length;raw_sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$null=Write-RecoveryJson (Join-Path $taskRoot 'artifact_hashes.json') @{source_commit=$ExpectedCommit;group=$StudyGroup;records=@($taskRecords)}
$compact=Join-Path $taskRepo ('artifacts/memphis-hydraulic-continuity-v1-compact/'+$StudyGroup)
New-Item -ItemType Directory -Path $compact -Force|Out-Null
foreach($f in Get-ChildItem -LiteralPath $taskRoot -File -Recurse){
 if($f.Extension -notin @('.json','.csv','.md','.html') -or $f.Name -in @('physics.json','series.json','phases.json','source_phases.json','measurements.json','source_observations.json','input.json','component_prelude.json') -or $f.Name -like 'm1_U*_index.json'){continue}
 $dest=Join-Path $compact ([IO.Path]::GetRelativePath($taskRoot,$f.FullName))
 New-Item -ItemType Directory -Path (Split-Path $dest) -Force|Out-Null
 Copy-Item -LiteralPath $f.FullName -Destination $dest
}
Write-Host ('MEMPHIS_GROUP_COMPLETE '+$StudyGroup)
