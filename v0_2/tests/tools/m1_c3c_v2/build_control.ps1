# Pure-file mechanical registration for remote synthetic checks only.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$dest=Join-Path $PSScriptRoot 'assembly_v3_control.json'
if(Test-Path -LiteralPath $dest){throw 'NEW_CONTROL_REQUIRED'}
$old=Join-Path $repo 'artifacts/m1-c3c-v1-freeze/executable_proposal.json'
if((Get-FileHash -LiteralPath $old).Hash.ToLowerInvariant() -cne 'f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45'){throw 'APPROVED_OLD_PACKAGE_DRIFT'}
$hashes=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File){$path='v0_2/tests/tools/m1_c3c_v2/'+$file.Name;$hashes[$path]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
foreach($path in @('.github/workflows/m1-c3c-v2-assembly.yml','.github/workflows/m1-c3c-full-v2.yml','.github/actions/m1-c3c-runtime-v2/action.yml','.github/workflows/liquid-cooling-recovery.yml','artifacts/m1-c3c-v1-freeze/executable_proposal.json')){$hashes[$path]=(Get-FileHash -LiteralPath (Join-Path $repo $path)).Hash.ToLowerInvariant()}
$parent='v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
. (Join-Path $PSScriptRoot 'batch.ps1')
$null=Write-C3Json $dest @{
    schema='m1-c3c-v2-environment-synthetic-control-v1';scope='DEVELOPMENT_INFRASTRUCTURE_ONLY'
    formal_behavior_authorized=$false;synthetic_test_count=51
    protected_parent_manifest_path=$parent
    protected_parent_manifest_raw_sha256=(Get-FileHash -LiteralPath (Join-Path $repo $parent)).Hash.ToLowerInvariant()
    source_hashes=$hashes
    environment_update_authorization='Direct human message: 我同意这个更新版本的测试.'
    authorized_image_version='20261012.333.1'
    prior_formal_run_id=38566504587;prior_result='INVALID_C3_C_EXECUTION'
    candidate_algorithm_or_frozen_expectation_change_authorized=$false
}
Get-FileHash -LiteralPath $dest,(Join-Path $PSScriptRoot 'run_assembly_v3.ps1')
