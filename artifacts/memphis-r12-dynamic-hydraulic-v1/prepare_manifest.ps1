$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$prefix='v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1'
$files=@(Get-ChildItem -LiteralPath (Join-Path $taskRepo $prefix) -File -Recurse|Where-Object {$_.Name -cne 'source_manifest.json'}|ForEach-Object{[IO.Path]::GetRelativePath($taskRepo,$_.FullName).Replace('\','/')})
$files+=@('.github/workflows/memphis-r12-dynamic-hydraulic-v1.yml','v0_2/tests/tools/m1_remote_executor_v1/build.ps1','v0_2/tests/tools/m1_remote_executor_v1/ControlledJob.cs','v0_2/tests/tools/m1_remote_executor_v1/VerifyTarget.cs','v0_2/tests/tools/liquid_recovery_v1/batch.ps1')
foreach($init in @('v0_2/__init__.py','v0_2/tests/__init__.py','v0_2/tests/tools/__init__.py')){if(Test-Path -LiteralPath (Join-Path $taskRepo $init)){$files+=$init}}
$rows=@($files|Sort-Object -Unique|ForEach-Object{@{path=$_;sha256=(Get-FileHash -LiteralPath (Join-Path $taskRepo $_) -Algorithm SHA256).Hash.ToLowerInvariant()}})
$registration=Get-Content -LiteralPath (Join-Path $taskRepo ($prefix+'/registration.json')) -Raw|ConvertFrom-Json
$value=[ordered]@{revision=$registration.revision;scope='ONE_SIX_RACK_SHORT_DYNAMIC_RESEARCH';frozen_m1_modified=$false;cpu_rate=2500;process_mb=256;job_mb=512;wall_seconds=480;source_files=$rows}
[IO.File]::WriteAllText((Join-Path $taskRepo ($prefix+'/source_manifest.json')),($value|ConvertTo-Json -Depth 15)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
Get-FileHash -LiteralPath (Join-Path $taskRepo ($prefix+'/source_manifest.json')) -Algorithm SHA256
