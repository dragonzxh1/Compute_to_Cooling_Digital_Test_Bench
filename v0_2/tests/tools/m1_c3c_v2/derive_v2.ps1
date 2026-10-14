# Mechanical versioned copy only; never executes Python/native/model code.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$prior=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v1'
$files=@('__init__.py','authority.py','bindings.py','source_lock.py','runtime_admission.py','stream_worker.py','stage_worker.py','worker.py','final_gate.py','preflight_worker.py','test_authority.py','test_assembly.py','artifact_schema.json','stop_rules.json','environment_lock.json','batch.ps1','campaign_plan.ps1','run.ps1','assembly_v3_worker.py','run_assembly_v3.ps1','test_control_plane_v3.ps1','verify_proposal.py','pre_sign_v2_worker.py','run_pre_sign_v2.ps1')
function Copy-Version([string]$Source,[string]$Destination){
    if(Test-Path -LiteralPath $Destination){throw 'DO_NOT_OVERWRITE_VERSIONED_SOURCE'}
    $text=[IO.File]::ReadAllText($Source)
    $text=$text.Replace('v0_2/tests/tools/m1_c3c_v1','v0_2/tests/tools/m1_c3c_v2').Replace('v0_2.tests.tools.m1_c3c_v1','v0_2.tests.tools.m1_c3c_v2').Replace('artifacts/m1-c3c-v1-freeze','artifacts/m1-c3c-v2-freeze').Replace('.github/workflows/m1-c3c-full.yml','.github/workflows/m1-c3c-full-v2.yml').Replace('./.github/actions/m1-c3c-runtime','./.github/actions/m1-c3c-runtime-v2').Replace('artifacts/m1-c3c-assembly-v3','artifacts/m1-c3c-v2-assembly')
    $directory=Split-Path $Destination
    if(-not(Test-Path -LiteralPath $directory)){New-Item -ItemType Directory -Path $directory|Out-Null}
    [IO.File]::WriteAllText($Destination,$text,[Text.UTF8Encoding]::new($false))
}
foreach($name in $files){Copy-Version (Join-Path $prior $name) (Join-Path $PSScriptRoot $name)}
Copy-Version (Join-Path $repo '.github/workflows/m1-c3c-full.yml') (Join-Path $repo '.github/workflows/m1-c3c-full-v2.yml')
Copy-Version (Join-Path $repo '.github/workflows/m1-c3c-assembly-v3.yml') (Join-Path $repo '.github/workflows/m1-c3c-v2-assembly.yml')
Copy-Version (Join-Path $repo '.github/actions/m1-c3c-runtime/action.yml') (Join-Path $repo '.github/actions/m1-c3c-runtime-v2/action.yml')
