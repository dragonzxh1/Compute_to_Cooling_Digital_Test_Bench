# Compilation/native ABI checks ONLY on an independent hosted Windows machine.
$ErrorActionPreference='Stop'
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'REMOTE_BUILD_ONLY'}
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$taskOutput=Join-Path $taskRepo 'artifacts/m1-remote-executor-v1/build'
New-Item -ItemType Directory -Path $taskOutput|Out-Null
$taskCompiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$taskHashes=[ordered]@{}
foreach($taskName in @('ControlledJob','VerifyTarget')){
    $taskSource=Join-Path $PSScriptRoot ($taskName+'.cs')
    $taskExe=Join-Path $taskOutput ($taskName+'.exe')
    & $taskCompiler /nologo /platform:x64 /target:exe ('/out:'+$taskExe) $taskSource
    if($LASTEXITCODE -ne 0){throw 'REMOTE_NATIVE_COMPILE_FAILED'}
    $taskHashes[$taskName]=@{source_raw_sha256=(Get-FileHash $taskSource -Algorithm SHA256).Hash.ToLowerInvariant();binary_raw_sha256=(Get-FileHash $taskExe -Algorithm SHA256).Hash.ToLowerInvariant()}
}
& (Join-Path $taskOutput 'ControlledJob.exe') --layout-selftest
if($LASTEXITCODE -ne 0){throw 'REMOTE_ABI_SELFTEST_FAILED'}
. (Join-Path $taskRepo 'v0_2/tests/tools/liquid_recovery_v1/batch.ps1')
$null=Write-RecoveryJson (Join-Path $taskOutput 'build_identity.json') @{
    source_and_binary_hashes=$taskHashes;compiler=$taskCompiler;compiler_version=(Get-Item $taskCompiler).VersionInfo.FileVersion
    environment='INDEPENDENT_GITHUB_HOSTED_WINDOWS_ONLY';CPU_rate=2500;strict_process_mb=256;strict_job_mb=512;campaign_process_mb=1024;campaign_job_mb=2048
    actual_python_job_proof='REQUIRED_BEFORE_EVERY_RELEASE';formal_qualification=$false;local_build_or_execution=$false
}
