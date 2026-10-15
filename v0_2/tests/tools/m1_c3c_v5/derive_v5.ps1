# Pure mechanical new-version derivation. Does not execute candidate/native.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$prior=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v4'
$files=@('__init__.py','authority.py','bindings.py','source_lock.py','runtime_admission.py','stream_worker.py','stage_worker.py','worker.py','final_gate.py','preflight_worker.py','test_authority.py','test_assembly.py','test_environment_revision.py','artifact_schema.json','stop_rules.json','environment_lock.json','environment_policy_registration.json','batch.ps1','campaign_plan.ps1','run.ps1','assembly_v4_worker.py','run_assembly_v4.ps1','test_control_plane_v4.ps1','verify_proposal.py')
function Convert-V5Version([string]$Text) {
    return $Text.Replace('m1_c3c_v4','m1_c3c_v5').Replace('m1-c3c-v4','m1-c3c-v5').Replace('m1-c3c-full-v4','m1-c3c-full-v5').Replace('m1-c3c-runtime-v4','m1-c3c-runtime-v5').Replace('assembly_v4','assembly_v5').Replace('control_plane_v4','control_plane_v5').Replace('C3C_ASSEMBLY_V4','C3C_ASSEMBLY_V5')
}
function Copy-V5Version([string]$Source,[string]$Destination) {
    if(Test-Path -LiteralPath $Destination){throw ('V5_NO_SOURCE_OVERWRITE: '+$Destination)}
    $text=Convert-V5Version ([IO.File]::ReadAllText($Source))
    $directory=Split-Path $Destination
    if(!(Test-Path -LiteralPath $directory)){New-Item -ItemType Directory -Path $directory|Out-Null}
    [IO.File]::WriteAllText($Destination,$text,[Text.UTF8Encoding]::new($false))
}
foreach($name in $files){Copy-V5Version (Join-Path $prior $name) (Join-Path $PSScriptRoot (Convert-V5Version $name))}
Copy-V5Version (Join-Path $repo '.github/actions/m1-c3c-runtime-v4/action.yml') (Join-Path $repo '.github/actions/m1-c3c-runtime-v5/action.yml')
Copy-V5Version (Join-Path $repo '.github/workflows/m1-c3c-full-v4.yml') (Join-Path $repo '.github/workflows/m1-c3c-full-v5.yml')
Copy-V5Version (Join-Path $repo '.github/workflows/m1-c3c-v4-assembly.yml') (Join-Path $repo '.github/workflows/m1-c3c-v5-assembly.yml')
Write-Host 'V5_SOURCE_DERIVED_NOT_FROZEN_NOT_AUTHORIZED'
