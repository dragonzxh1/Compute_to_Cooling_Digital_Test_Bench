param([Parameter(Mandatory)][string]$ExpectedCommit,[ValidateSet('baseline','suite')][string]$Stage='baseline')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'REMOTE_ONLY'}
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Set-Location -LiteralPath $taskRepo
if((git rev-parse HEAD) -cne $ExpectedCommit -or $env:GITHUB_SHA -cne $ExpectedCommit){throw 'SOURCE_COMMIT_DRIFT'}
$taskManifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'source_manifest.json') -Raw|ConvertFrom-Json
function Verify-Source {
 foreach($r in $taskManifest.source_files){
  if((Get-FileHash -LiteralPath $r.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $r.sha256){throw ('SOURCE_DRIFT '+$r.path)}
 }
}
Verify-Source
$taskRoot=Join-Path $taskRepo ('artifacts/memphis-r12-solver-pressure-safety-v1/'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT)
if($Stage -eq 'suite'){
 $previous=Get-Content -LiteralPath (Join-Path $taskRoot 'baseline/result.json') -Raw|ConvertFrom-Json
 $oldJob=Get-Content -LiteralPath (Join-Path $taskRoot 'baseline/job_status.json') -Raw|ConvertFrom-Json
 if(-not $previous.suite_admitted -or $previous.status -cne 'PASS' -or $previous.environment.source_commit -cne $ExpectedCommit -or -not $oldJob.cleanup_complete -or $oldJob.active_after_cleanup -ne 0){throw 'SUITE_NOT_ADMITTED_BY_BASELINE'}
}
if($Stage -eq 'baseline'){
 & ./v0_2/tests/tools/m1_remote_executor_v1/build.ps1
 if($LASTEXITCODE -ne 0){throw 'SUPERVISOR_BUILD_FAILED'}
}else{
 $identity=Get-Content -LiteralPath 'artifacts/m1-remote-executor-v1/build/build_identity.json' -Raw|ConvertFrom-Json
 foreach($name in @('ControlledJob','VerifyTarget')){
  $expected=$identity.source_and_binary_hashes.$name.binary_raw_sha256
  if((Get-FileHash -LiteralPath ('artifacts/m1-remote-executor-v1/build/'+$name+'.exe')).Hash.ToLowerInvariant() -cne $expected){throw 'NATIVE_BINARY_DRIFT'}
 }
}
. ./v0_2/tests/tools/liquid_recovery_v1/batch.ps1
$taskOut=Join-Path $taskRoot $Stage
New-Item -ItemType Directory -Path $taskOut -Force|Out-Null
if(Test-Path -LiteralPath (Join-Path $taskOut 'ready.json')){throw 'STAGE_ALREADY_EXECUTED'}
$taskBuild=Join-Path $taskRepo 'artifacts/m1-remote-executor-v1/build'
$taskPython=(Get-Command python).Source
function Q([string]$s){
 $b=[Text.StringBuilder]::new('"');$n=0
 foreach($c in $s.ToCharArray()){
  if($c -eq '\'){$n++;continue}
  if($c -eq '"'){$null=$b.Append('\',2*$n+1)}else{$null=$b.Append('\',$n)}
  $null=$b.Append($c);$n=0
 }
 $null=$b.Append('\',2*$n);$null=$b.Append('"');$b.ToString()
}
$taskArgs=@((Join-Path $taskOut 'job_status.json'),(Join-Path $taskOut 'job_start.json'),(Join-Path $taskOut 'cancel.request'),
 (Join-Path $taskOut 'stdout.raw'),(Join-Path $taskOut 'stderr.raw'),'480000','2500','256','512',
 $taskPython,'-B','-m','v0_2.tests.tools.memphis_r12_solver_pressure_safety_v1.worker',$taskOut,$Stage)
$taskProcess=Start-Process -FilePath (Join-Path $taskBuild 'ControlledJob.exe') -WindowStyle Hidden `
 -ArgumentList (($taskArgs|ForEach-Object{Q ([string]$_)}) -join ' ') -WorkingDirectory $taskRepo -PassThru `
 -RedirectStandardOutput (Join-Path $taskOut 'supervisor_stdout.raw') -RedirectStandardError (Join-Path $taskOut 'supervisor_stderr.raw')
$timer=[Diagnostics.Stopwatch]::StartNew()
try{
 while(-not(Test-Path -LiteralPath (Join-Path $taskOut 'ready.json'))){
  if($taskProcess.HasExited -or $timer.ElapsedMilliseconds -gt 30000){throw 'READY_FAILED'}
  Start-Sleep -Milliseconds 50
 }
 $ready=Get-Content (Join-Path $taskOut 'ready.json') -Raw|ConvertFrom-Json
 $start=Get-Content (Join-Path $taskOut 'job_start.json') -Raw|ConvertFrom-Json
 $proof=Join-Path $taskOut 'external_job_identity.json'
 $va=@($start.job_name,[string]$ready.pid,'256','512',$proof,'2500')
 $vp=Start-Process -FilePath (Join-Path $taskBuild 'VerifyTarget.exe') -WindowStyle Hidden -PassThru `
  -ArgumentList (($va|ForEach-Object{Q ([string]$_)}) -join ' ') `
  -RedirectStandardOutput (Join-Path $taskOut 'verify_stdout.raw') -RedirectStandardError (Join-Path $taskOut 'verify_stderr.raw')
 if(-not $vp.WaitForExit(5000) -or $vp.ExitCode -ne 0){throw 'ACTUAL_PYTHON_JOB_FAILED'}
 $p=Get-Content $proof -Raw|ConvertFrom-Json
 if(-not $p.in_target_job -or $p.actual_python_pid -ne $ready.pid -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 256 -or $p.job_mb -ne 512){throw 'LIMIT_PROOF_FAILED'}
 $null=Write-RecoveryJson (Join-Path $taskOut 'release.json') @{actual_python_pid=$ready.pid;external_proof_raw_sha256=(Get-FileHash $proof).Hash.ToLowerInvariant()}
 if(-not $taskProcess.WaitForExit(495000)){throw 'NATIVE_TIMEOUT'}
 $native=Get-Content (Join-Path $taskOut 'job_status.json') -Raw|ConvertFrom-Json
 if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED' -or $taskProcess.ExitCode -ne 0){throw 'NATIVE_OR_MODEL_FAILURE'}
 $result=Get-Content (Join-Path $taskOut 'result.json') -Raw|ConvertFrom-Json
 if($result.status -cne 'PASS'){throw 'MODEL_EXECUTION_FAILURE'}
 if($Stage -eq 'baseline'){
  ('suite_ready='+([string]$result.suite_admitted).ToLowerInvariant())|Out-File -LiteralPath $env:GITHUB_OUTPUT -Append -Encoding utf8
 }
 Verify-Source
}finally{
 if(-not $taskProcess.HasExited){
  $null=Write-RecoveryJson (Join-Path $taskOut 'cancel.request') @{requested=$true}
  if(-not $taskProcess.WaitForExit(3000)){$taskProcess.Kill();$null=$taskProcess.WaitForExit(2000)}
 }
 $rows=@(Get-ChildItem -LiteralPath $taskOut -File -Recurse|ForEach-Object{@{path=[IO.Path]::GetRelativePath($taskOut,$_.FullName).Replace('\','/');bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()}})
 $null=Write-RecoveryJson (Join-Path $taskOut 'artifact_hashes.json') @{source_commit=$ExpectedCommit;manifest_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'source_manifest.json')).Hash.ToLowerInvariant();records=$rows}
}
