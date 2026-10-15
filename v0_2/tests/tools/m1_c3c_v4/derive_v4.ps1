# Pure mechanical new-version derivation. Does not execute candidate/native.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$prior=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v3'
$files=@('__init__.py','authority.py','bindings.py','source_lock.py','runtime_admission.py','stream_worker.py','stage_worker.py','worker.py','final_gate.py','preflight_worker.py','test_authority.py','test_assembly.py','test_environment_revision.py','artifact_schema.json','stop_rules.json','environment_lock.json','environment_policy_registration.json','batch.ps1','campaign_plan.ps1','run.ps1','assembly_v3_worker.py','run_assembly_v3.ps1','test_control_plane_v3.ps1','verify_proposal.py')
function Convert-V4Version([string]$Text) {
    return $Text.Replace('m1_c3c_v3','m1_c3c_v4').Replace('m1-c3c-v3','m1-c3c-v4').Replace('m1-c3c-full-v3','m1-c3c-full-v4').Replace('m1-c3c-runtime-v3','m1-c3c-runtime-v4').Replace('assembly_v3','assembly_v4').Replace('control_plane_v3','control_plane_v4').Replace('C3C_ASSEMBLY_V3','C3C_ASSEMBLY_V4')
}
function Copy-V4Version([string]$Source,[string]$Destination) {
    if(Test-Path -LiteralPath $Destination){throw ('V4_NO_SOURCE_OVERWRITE: '+$Destination)}
    $text=Convert-V4Version ([IO.File]::ReadAllText($Source))
    $directory=Split-Path $Destination
    if(!(Test-Path -LiteralPath $directory)){New-Item -ItemType Directory -Path $directory|Out-Null}
    [IO.File]::WriteAllText($Destination,$text,[Text.UTF8Encoding]::new($false))
}
foreach($name in $files){Copy-V4Version (Join-Path $prior $name) (Join-Path $PSScriptRoot (Convert-V4Version $name))}
Copy-V4Version (Join-Path $repo '.github/actions/m1-c3c-runtime-v3/action.yml') (Join-Path $repo '.github/actions/m1-c3c-runtime-v4/action.yml')
Copy-V4Version (Join-Path $repo '.github/workflows/m1-c3c-full-v3.yml') (Join-Path $repo '.github/workflows/m1-c3c-full-v4.yml')
Copy-V4Version (Join-Path $repo '.github/workflows/m1-c3c-v3-assembly.yml') (Join-Path $repo '.github/workflows/m1-c3c-v4-assembly.yml')
Write-Host 'V4_SOURCE_DERIVED_NOT_FROZEN_NOT_AUTHORIZED'
