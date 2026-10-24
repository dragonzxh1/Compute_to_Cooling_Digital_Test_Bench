param([Parameter(Mandatory)][string]$OutputPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'REMOTE_BUILD_ONLY'}
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$taskExpectedRoot=[IO.Path]::GetFullPath((Join-Path $taskRepo 'artifacts/engineering-design-mvp-v1'))+[IO.Path]::DirectorySeparatorChar
if(-not [IO.Path]::GetFullPath($OutputPath).StartsWith($taskExpectedRoot)){throw 'BUILD_OUTPUT_SCOPE'}
New-Item -ItemType Directory -Path $OutputPath|Out-Null
$taskCompiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$taskHashes=[ordered]@{}
foreach($taskName in @('ControlledJob','VerifyTarget')){
 $taskSource=Join-Path $PSScriptRoot ($taskName+'.cs');$taskExe=Join-Path $OutputPath ($taskName+'.exe')
 & $taskCompiler /nologo /platform:x64 /target:exe ('/out:'+$taskExe) $taskSource
 if($LASTEXITCODE -ne 0){throw 'REMOTE_NATIVE_COMPILE_FAILED'}
 $taskHashes[$taskName]=@{source_raw_sha256=(Get-FileHash $taskSource).Hash.ToLowerInvariant();binary_raw_sha256=(Get-FileHash $taskExe).Hash.ToLowerInvariant()}
}
& (Join-Path $OutputPath 'ControlledJob.exe') --layout-selftest
if($LASTEXITCODE -ne 0){throw 'REMOTE_ABI_SELFTEST_FAILED'}
# Refusal probe: old throttle/memory policy must not launch any child.
$taskPython=(Get-Command python).Source
& (Join-Path $OutputPath 'ControlledJob.exe') unused unused unused unused unused 480000 2500 256 512 $taskPython
if($LASTEXITCODE -ne 125){throw 'OBSOLETE_POLICY_WAS_NOT_REJECTED'}
$global:LASTEXITCODE=0
$taskPolicy=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../resource_environment.json') -Raw|ConvertFrom-Json
. (Join-Path $taskRepo 'v0_2/tests/tools/liquid_recovery_v1/batch.ps1')
$null=Write-RecoveryJson (Join-Path $OutputPath 'build_identity.json') @{
 source_and_binary_hashes=$taskHashes;compiler=$taskCompiler;compiler_version=(Get-Item $taskCompiler).VersionInfo.FileVersion
 resource_policy=$taskPolicy;actual_python_job_proof='REQUIRED_BEFORE_RELEASE';abi_selftest='PASS';obsolete_policy_refusal='PASS'
 formal_qualification=$false;local_build_or_execution=$false;legacy_m1_executor_modified=$false
}
