# Pure-file derivation of a NEW unsigned delivery reviewer. No native/Python execution.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$prior=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v4_closure'
$control=Get-Content -Raw -LiteralPath (Join-Path $prior 'control.json')|ConvertFrom-Json -AsHashtable
foreach($name in @('__init__.py','readback_worker.py','run_readback.ps1','complete_delivery.ps1','build_final_package.ps1')) {
    $relative='v0_2/tests/tools/m1_c3c_v4_closure/'+$name
    if((Get-FileHash -LiteralPath (Join-Path $prior $name)).Hash.ToLowerInvariant() -cne $control.source_hashes[$relative]){throw 'V5_PRIOR_CLOSURE_SOURCE_DRIFT'}
    $dest=Join-Path $PSScriptRoot $name
    if(Test-Path -LiteralPath $dest){throw 'V5_CLOSURE_DERIVATION_NO_OVERWRITE'}
    $text=[IO.File]::ReadAllText((Join-Path $prior $name))
    $text=$text.Replace('m1_c3c_v4','m1_c3c_v5').Replace('m1-c3c-v4','m1-c3c-v5').Replace('C3_C_V4','C3_C_V5').Replace('C3C_V4','C3C_V5').Replace('C3-C v4','C3-C v5').Replace('C3-C-v4','C3-C-v5').Replace('V4_','V5_')
    [IO.File]::WriteAllText($dest,$text,[Text.UTF8Encoding]::new($false))
}
$workflow='.github/workflows/m1-remote-long-probe.yml'
$text=[IO.File]::ReadAllText((Join-Path $repo $workflow))
if((Get-FileHash -LiteralPath (Join-Path $repo $workflow)).Hash.ToLowerInvariant() -cne $control.source_hashes[$workflow]){throw 'V5_PRIOR_REVIEW_WORKFLOW_DRIFT'}
$text=$text.Replace('m1_c3c_v4_closure','m1_c3c_v5_closure').Replace('m1-c3c-v4','m1-c3c-v5').Replace('C3-C v4','C3-C v5').Replace('C3-C-V4','C3-C-V5').Replace('V4_READ','V5_READ').Replace('V4_DELIVERY','V5_DELIVERY')
[IO.File]::WriteAllText((Join-Path $repo $workflow),$text,[Text.UTF8Encoding]::new($false))
Write-Output 'V5_READONLY_CLOSURE_DERIVED_NOT_EXECUTED'
