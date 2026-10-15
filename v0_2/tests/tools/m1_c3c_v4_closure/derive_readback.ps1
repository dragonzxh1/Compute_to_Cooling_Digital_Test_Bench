# Mechanical new-version copy of independently verified read-only infrastructure.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$prior=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v3_closure'
$priorControl=Get-Content -Raw -LiteralPath (Join-Path $prior 'control.json')|ConvertFrom-Json -AsHashtable
foreach($name in @('__init__.py','readback_worker.py','run_readback.ps1','complete_delivery.ps1')) {
    $path='v0_2/tests/tools/m1_c3c_v3_closure/'+$name
    if((Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant() -cne $priorControl.source_hashes[$path]){throw 'V4_PRIOR_READONLY_SOURCE_DRIFT'}
    $dest=Join-Path $PSScriptRoot $name
    if(Test-Path -LiteralPath $dest){throw 'V4_READONLY_SOURCE_NO_OVERWRITE'}
    $text=[IO.File]::ReadAllText((Join-Path $prior $name))
    $text=$text.Replace('m1_c3c_v3','m1_c3c_v4').Replace('m1-c3c-v3','m1-c3c-v4').Replace('C3_C_V3','C3_C_V4').Replace('C3C_V3','C3C_V4').Replace('C3-C v3','C3-C v4').Replace('C3-C-v3','C3-C-v4')
    $text=$text.Replace('bound == 755','bound == control["expected_source_binding_count"]').Replace('$result.source_bindings_verified -ne 755','$result.source_bindings_verified -ne $control.expected_source_binding_count').Replace('完整755source bindings','完整$($control.expected_source_binding_count)项source bindings')
    [IO.File]::WriteAllText($dest,$text,[Text.UTF8Encoding]::new($false))
}
Write-Host 'V4_READONLY_SOURCE_DERIVED_NO_CANDIDATE_EXECUTION'
