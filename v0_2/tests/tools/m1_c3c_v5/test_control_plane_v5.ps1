# Finite synthetic metadata/static checks only. No model, Python or native launch.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'REMOTE_SYNTHETIC_CHECKS_ONLY'}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $PSScriptRoot 'batch.ps1')
$checks=[Collections.Generic.List[object]]::new()
function Check([string]$Id,[bool]$Passed){if(-not $Passed){throw ('CONTROL_PLANE_FAIL '+$Id)};$checks.Add(@{id=$Id;passed=$true})}
function Record {
    return @{stage_id='SYNTHETIC_ONLY';source_verified=$true;environment_verified=$true;evidence_verified=$true;
        primitive_consistent=$true;cleanup_complete=$true;launcher_exitcode=0;child_exitcode=0;active_after_cleanup=0;
        native_outcome='EXITED';capture_status='COMPLETE';result_status='PASS';passed=$true}
}
$v=Record;Check 'CP-01' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'PASS')
$v=Record;$v.source_verified='true';Check 'CP-02' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'INVALID')
$v=Record;$v.active_after_cleanup=1;Check 'CP-03' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'INVALID')
$v=Record;Check 'CP-04' ((Get-C3StageDecision $v 'OTHER').status -ceq 'INVALID')
$v=Record;$v.result_status='FAIL';$v.passed=$false;Check 'CP-05' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'FAIL')
$v=Record;$v.result_status='INCOMPLETE';$v.passed=$false;Check 'CP-06' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'INCOMPLETE')
$v=Record;$v.capture_status='NOT_CREATED';Check 'CP-07' ((Get-C3StageDecision $v 'SYNTHETIC_ONLY').status -ceq 'INVALID')
$saved=[Environment]::GetEnvironmentVariable('C2C_C3C_PACKAGE_SHA256')
try {
    [Environment]::SetEnvironmentVariable('C2C_C3C_PACKAGE_SHA256',$null)
    $denied=$false;try{$null=Get-C3DispatchIdentity}catch{$denied=$true}
    Check 'CP-08' $denied
}finally{[Environment]::SetEnvironmentVariable('C2C_C3C_PACKAGE_SHA256',$saved)}
$parsed=0
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -Filter *.ps1){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    Check ('CP-09-'+$file.Name) ($errors.Count -eq 0);$parsed++
}
$workflow=Get-Content -LiteralPath (Join-Path $repo '.github/workflows/m1-c3c-full-v5.yml') -Raw
$phaseBodies=@{}
foreach($match in [regex]::Matches($workflow,'(?ms)^  (?<name>[a-z_]+):\r?\n(?<body>.*?)(?=^  [a-z_]+:|\z)')){$phaseBodies[$match.Groups['name'].Value]=$match.Groups['body'].Value}
$required=@('prepare','references','reference_gate','select','split_u','split','plan','prefixes','startup','schema','final')
Check 'CP-10' (@($required|Where-Object {-not $phaseBodies.ContainsKey($_)}).Count -eq 0)
$edges=@{references='prepare';reference_gate='references';select='reference_gate';split_u='select';split='split_u';plan='split';prefixes='plan';startup='plan';schema='prefixes';final='schema'}
foreach($edge in $edges.GetEnumerator()){
    Check ('CP-11-'+$edge.Key) ($phaseBodies[$edge.Key] -match ('needs:\s*\[[^\]]*\b'+$edge.Value+'\b'))
}
Check 'CP-11-final-startup' ($phaseBodies['final'] -match 'needs:\s*\[[^\]]*\bstartup\b')
function MatrixIndices([string]$Phase){
    $m=[regex]::Match($phaseBodies[$Phase],'(?m)^      matrix:\s*(\{[^\r\n]+\})')
    if(-not $m.Success){throw ('MATRIX_JSON_MISSING '+$Phase)}
    $data=$m.Groups[1].Value|ConvertFrom-Json
    if($data.PSObject.Properties.Name -contains 'include'){
        return @($data.include|ForEach-Object {
            if($_.PSObject.Properties.Name -contains 'indices'){$_.indices.Split(',')|ForEach-Object {[int]$_}}
            elseif($_.PSObject.Properties.Name -contains 'index'){[int]$_.index}
            else{throw 'UNKNOWN_INCLUDE_MATRIX_ENTRY'}
        })
    }
    return @($data.index|ForEach-Object {[int]$_})
}
foreach($phase in @('references','split')){
    $indices=@(0)+@(MatrixIndices $phase)
    Check ('CP-12-'+$phase) (($indices.Count -eq 101) -and (($indices|Sort-Object -Unique) -join ',') -ceq ((0..100) -join ','))
}
foreach($phase in @('select','prefixes','schema')){
    $indices=@(MatrixIndices $phase)
    Check ('CP-12-'+$phase) (($indices.Count -eq 101) -and (($indices|Sort-Object -Unique) -join ',') -ceq ((0..100) -join ','))
}
$indices=@(MatrixIndices 'startup');Check 'CP-12-startup' (($indices.Count -eq 50) -and (($indices|Sort-Object -Unique) -join ',') -ceq ((0..49) -join ','))
$blocks=[regex]::Matches($workflow,'(?ms)^        run: \|\r?\n(?<body>(?:^          [^\r\n]*(?:\r?\n|$))+)')
foreach($block in $blocks){
    $code=($block.Groups['body'].Value -split '\r?\n'|ForEach-Object {$_ -replace '^          ',''}) -join "`n"
    # Workflow substitutions are frozen transport strings, not executable syntax.
    $code=[regex]::Replace($code,'\$\{\{[^}]+\}\}','SYNTHETIC_WORKFLOW_VALUE')
    $t=$null;$e=$null;$null=[Management.Automation.Language.Parser]::ParseInput($code,[ref]$t,[ref]$e)
    Check ('CP-13-inline-'+$checks.Count) ($e.Count -eq 0)
}
$lock=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'environment_lock.json') -Raw|ConvertFrom-Json
Check 'CP-14' (($lock.python -ceq '3.11.9') -and ($lock.version -ceq '10.0.20348') -and (($lock.image_version -join ',') -ceq '20261004.326.1,20261012.333.1'))
$spec=Get-Content -LiteralPath (Join-Path $repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
Check 'CP-15' ($spec.input_inventory.Count -eq 101)
$run=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'run.ps1') -Raw
Check 'CP-16' ($run.IndexOf('$taskDispatchIdentity=Get-C3DispatchIdentity') -lt $run.IndexOf('$taskBuildRoot='))
$bad=[pscustomobject]@{status='INVALID';stage_id='ENVIRONMENT';error='QUALIFICATION_ENVIRONMENT_DRIFT'}
$native=[pscustomobject]@{cleanup_complete=$true;active_after_cleanup=0;child_exitcode=0;outcome='EXITED'}
$envelope=Get-C3InvalidStageRecord -StageId ENVIRONMENT -Result $bad -Native $native -LauncherExitcode 0
Check 'CP-17' ($envelope.result_status -ceq 'INVALID' -and -not $envelope.passed -and -not $envelope.environment_verified)
Check 'CP-18' ((Get-C3StageDecision $envelope ENVIRONMENT).status -ceq 'INVALID')
$denied=$false;try{$null=Get-C3InvalidStageRecord -StageId OTHER -Result $bad -Native $native -LauncherExitcode 0}catch{$denied=$true}
Check 'CP-19' $denied
Check 'CP-20' ($run.IndexOf("if(`$taskResult.status -ceq 'INVALID')") -lt $run.IndexOf('$taskActual=$taskResult.runtime_identity_before'))
@{schema='m1-c3c-control-plane-synthetic-result-v1';status='PASS';scope='DEVELOPMENT_CONTROL_PLANE_ONLY';
    checks=$checks.ToArray();check_count=$checks.Count;parsed_ps_files=$parsed;candidate_behavioral_execution=$false;
    formal_qualification=$false;approval_generated=$false}|ConvertTo-Json -Depth 8
