# Pure source/graph regression. No Python/model/native launch.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$old=[IO.File]::ReadAllText((Join-Path $repo '.github/workflows/m1-c3c-full-v3.yml'))
$new=[IO.File]::ReadAllText((Join-Path $repo '.github/workflows/m1-c3c-full-v4.yml'))
function Normalize-V4([string]$Text) {
    return $Text.Replace('m1_c3c_v4','m1_c3c_v3').Replace('m1-c3c-v4','m1-c3c-v3').Replace('m1-c3c-full-v4','m1-c3c-full-v3').Replace('m1-c3c-runtime-v4','m1-c3c-runtime-v3')
}
$oldFinal=$old.Substring($old.IndexOf("  final:`n"))
$newFinal=$new.Substring($new.IndexOf("  final:`n"))
$oldTargets=@([regex]::Matches($oldFinal,'(?m)^          (?:name|pattern): (.+)$')|ForEach-Object {$_.Groups[1].Value})
$newTargets=@([regex]::Matches($newFinal,'(?m)^          (?:name|pattern): (.+)$')|ForEach-Object {$_.Groups[1].Value})
$expected=@('schema-*','startup-*','prepare','ref-*','reference-gate','select-*','split-*','prefix-*','plan','final')
if(@(Compare-Object $expected $newTargets).Count -or $newTargets.Count -ne 10){throw 'V4_FINAL_DOWNLOAD_OR_OUTPUT_FAMILY_CLOSURE'}
# Old final had only three inputs and its output named final. This is a
# counterexample, never an assertion that the original runner was correct.
if($oldTargets.Count -ne 4 -or $oldTargets -contains 'ref-*'){throw 'V4_OLD_WORKFLOW_COUNTEREXAMPLE_DRIFT'}
$addedStart=$new.IndexOf('      # Case payload export intentionally')
$addedEnd=$new.IndexOf('      - name: Controlled FINAL',$addedStart)
if($addedStart -lt 0 -or $addedEnd -lt 0){throw 'V4_TRANSPORT_PATCH_BOUNDARY'}
$withoutTransport=$new.Remove($addedStart,$addedEnd-$addedStart)
if((Normalize-V4 $withoutTransport) -cne $old){throw 'V4_UNAUTHORIZED_WORKFLOW_SEMANTIC_DIFF'}
foreach($name in @('authority.py','bindings.py','source_lock.py','runtime_admission.py','stream_worker.py','stage_worker.py','worker.py','final_gate.py','artifact_schema.json','stop_rules.json','environment_lock.json','environment_policy_registration.json','batch.ps1','campaign_plan.ps1','run.ps1')) {
    $prior=[IO.File]::ReadAllText((Join-Path $repo ('v0_2/tests/tools/m1_c3c_v3/'+$name)))
    $current=[IO.File]::ReadAllText((Join-Path $PSScriptRoot $name))
    if((Normalize-V4 $current) -cne $prior){throw ('V4_UNAUTHORIZED_CORE_SEMANTIC_DIFF: '+$name)}
}
[pscustomobject]@{status='V4_WORKFLOW_TRANSPORT_ONLY_REGRESSION_PASS';unchanged_core_file_count=15;old_final_inputs=3;new_final_inputs=9;candidate_executed=$false;formal_qualification_executed=$false}|ConvertTo-Json
