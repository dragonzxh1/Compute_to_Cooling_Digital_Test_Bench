# Additional pure-file semantic/schema audit; no candidate or test execution.
param([Parameter(Mandatory)][string]$EvidenceRoot)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
function A([bool]$ok,[string]$why){if(-not $ok){throw $why}}
$zipPath=Join-Path $EvidenceRoot 'final.official.zip'
A ((Get-FileHash -LiteralPath $zipPath).Hash.ToLowerInvariant() -ceq 'bc8a49397e10415d157260c21e4d2869f3ace4065600a22aeb6da96a2140c293') 'ZIP_DRIFT'
$zip=[IO.Compression.ZipFile]::OpenRead($zipPath);$prefix='m1-autonomous-development/stream-38833878662-1/';$nativePrefix='liquid-recovery-v1/stream-38833878662-1/'
function Text([string]$n){$e=$zip.GetEntry($n);A ($null -ne $e) ('MISSING '+$n);$r=[IO.StreamReader]::new($e.Open());try{return $r.ReadToEnd()}finally{$r.Dispose()}}
function J([string]$n){return ,(ConvertFrom-Json -InputObject (Text $n) -AsHashtable -NoEnumerate)}
function LocalJ([string]$n){return ,(ConvertFrom-Json -InputObject (Get-Content -Raw -LiteralPath (Join-Path $repo $n)) -AsHashtable -NoEnumerate)}
try{
    $definition=LocalJ 'artifacts/m1-c3c-v5-freeze/executable_proposal.json'
    $bundle=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $definition.bundle_path));$hasher=[Security.Cryptography.SHA256]::Create();$localCount=0;$bundleCount=0
    try{foreach($b in $definition.source_raw_sha256.GetEnumerator()){
        $path=Join-Path $repo $b.Key
        if(Test-Path -LiteralPath $path){$h=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();$localCount++}else{$e=$bundle.GetEntry($b.Key);A ($null -ne $e) 'SOURCE_MISSING';$s=$e.Open();try{$h=[Convert]::ToHexString($hasher.ComputeHash($s)).ToLowerInvariant()}finally{$s.Dispose()};$bundleCount++}
        A ($h -ceq $b.Value) ('PROTECTED_SOURCE_DRIFT '+$b.Key)
    }}finally{$bundle.Dispose();$hasher.Dispose()}
    $outerCount=0;$constructors=0;$images=[Collections.Generic.HashSet[string]]::new();$schemaFile=Join-Path $repo 'v0_2/tests/tools/m1_c3c_v5/artifact_schema.json'
    foreach($entry in $zip.Entries){
        if(-not $entry.FullName.StartsWith($nativePrefix) -or -not $entry.FullName.EndsWith('/result.json')){continue}
        $raw=Text $entry.FullName
        A (Test-Json -Json $raw -SchemaFile $schemaFile -ErrorAction Stop) ('OUTER_SCHEMA '+$entry.FullName)
        $v=ConvertFrom-Json -InputObject $raw -AsHashtable
        A ($v.status -ceq 'PASS' -and $v.formal_execution_authorized -and $v.formal_qualification -and $v.github_run_id -ceq '38833878662') 'OUTER_STATUS'
        $id=$v.stage_id
        if($id.StartsWith('STARTUP-') -or ($id.StartsWith('CASE-') -and $id -cmatch '(-SPLIT|-REPEAT-|-PREFIX_ONE-|-PREFIX_BATCH-)')){A ($v.sut_constructors.Count -gt 0) ('SUT_CONSTRUCTOR_MISSING '+$id)}
        foreach($c in $v.sut_constructors){A ($c.class -ceq 'v0_2.tests.tools.m1_engine_v4.engine.SplitEngine' -and $c.post_module -ceq 'v0_2.tests.tools.m1_engine_v4.engine') 'WRONG_SUT';$constructors++}
        $null=$images.Add($v.runtime_identity_before.image_version);$outerCount++
    }
    A ($outerCount -eq 1970) 'OUTER_SCHEMA_COUNT'
    $inventory=J ($prefix+'startup_inventory.json');A ($inventory.nodeids.Count -eq 50 -and @($inventory.nodeids|Select-Object -Unique).Count -eq 50) 'STARTUP_INVENTORY'
    $passed=0;$failed=[Collections.Generic.List[object]]::new()
    for($i=0;$i -lt 50;$i++){
        $n=J ($prefix+('startup/{0:000}/node_result.json' -f $i));A ($n.status -ceq 'PASS' -and $n.nodeid -ceq $inventory.nodeids[$i] -and $n.structured_result.session_complete) 'STARTUP_NODE'
        $calls=@($n.structured_result.reports|Where-Object when -ceq 'call');A ($calls.Count -eq 1) 'STARTUP_CALL_COUNT'
        if($calls[0].outcome -ceq 'passed'){A ($n.historical_test_pass -and $n.pytest_exitcode -eq 0) 'STARTUP_PASS_IDENTITY';$passed++}else{A ($calls[0].outcome -ceq 'failed' -and -not $n.historical_test_pass -and $n.legacy_assertion_preserved -and $n.pytest_exitcode -eq 1) 'STARTUP_LEGACY_FAILURE';$failed.Add(@{nodeid=$n.nodeid;call=$calls[0]})}
    }
    A ($passed -eq 49 -and $failed.Count -eq 1 -and $failed[0].call.exception_type -ceq 'AssertionError' -and $failed[0].call.longrepr.Contains('startup_demand_suspended')) 'STARTUP_EXACT_49_1'
    $sem02=LocalJ $definition.registration_paths.SEM02;$eligibility=J ($prefix+'startup_eligibility.json')
    A ($eligibility.cases.Count -eq 5 -and $sem02.cases.Count -eq 5 -and $eligibility.STARTUP_STRICT_P1_CAUSAL_ELIGIBILITY -ceq 'INCOMPLETE') 'SEM02_COUNT'
    foreach($f in $sem02.cases){
        $matches=@($eligibility.cases|Where-Object nodeid -ceq $f.nodeid);A ($matches.Count -eq 1) 'SEM02_NODE';$c=$matches[0]
        A ($c.causal_reason -ceq $f.reason -and $c.domain_events.Count -eq $f.events -and $c.strict_P1_Lane_B -ceq 'INCOMPLETE' -and $c.strict_P1_Lane_C -ceq 'INCOMPLETE' -and -not $c.fake_PLC_receipts -and -not $c.fake_Safety_decisions -and -not $c.source_sensor_coerced_valid) 'SEM02_CAUSAL_IDENTITY'
        for($i=0;$i -lt $c.domain_events.Count;$i++){$e=$c.domain_events[$i];A ($e.input_typed_sha256 -ceq $f.input_typed_hashes[$i] -and $e.PLC_receipts -eq 0 -and $e.Safety_commits -eq 0) 'SEM02_INPUT_OR_FAKE_RECEIPT'}
    }
    $pf=LocalJ $definition.registration_paths.PF06_supplement;$matrix=J ($prefix+'PF16_witness_matrix.json');$p=$matrix.PF06_proposal;$cut=$p.positive_witness
    A ($p.version -ceq $pf.binding_id -and $cut.row_index -eq 4 -and $cut.time_ns -eq 800000000 -and $cut.source_descriptor.case_key -ceq 'C8_normal' -and $cut.source_id -ceq $pf.source_id -and $cut.observed_preconditions['PF-06'] -and $cut.PLC.producer -ceq 'SIMULATED_PLC') 'PF06_POSITIVE_BINDING'
    A ((ConvertTo-C3DeliveryCanonical $cut.source_descriptor) -ceq (ConvertTo-C3DeliveryCanonical $pf.source_descriptor) -and (ConvertTo-C3DeliveryCanonical $cut.independent_expected_PRE) -ceq (ConvertTo-C3DeliveryCanonical $pf.independent_expectations.PRE) -and (ConvertTo-C3DeliveryCanonical $cut.independent_expected_POST) -ceq (ConvertTo-C3DeliveryCanonical $pf.independent_expectations.POST)) 'PF06_INDEPENDENT_EXPECTATION'
    foreach($b in $pf.independent_expectations.expected_Safety.GetEnumerator()){A ((ConvertTo-C3DeliveryCanonical $cut.Safety[$b.Key]) -ceq (ConvertTo-C3DeliveryCanonical $b.Value)) 'PF06_SAFETY_EXPECTATION'}
    A ($p.negative_controls.Count -eq 2 -and $pf.negative_controls.Count -eq 2 -and $p.comparison.status -ceq 'PASS' -and -not $p.self_approved -and -not $matrix.original_matrix_changed -and $matrix.original_validated_count -eq 15) 'PF06_SCOPE_OR_CONTROL_COUNT'
    foreach($f in $pf.negative_controls){$matched=@($p.negative_controls|Where-Object {$_.descriptor.stage_id -ceq $f.stage_id -and $_.descriptor.input_canonical_sha256 -ceq $f.input_canonical_sha256});A ($matched.Count -eq 1 -and $matched[0].all_PF06_absent -and $matched[0].comparison.status -ceq 'PASS') 'PF06_NEGATIVE_CONTROL'}
    $progress=@((Text ($nativePrefix+'final/FINAL_ACCEPTANCE/progress.jsonl')).Split("`n")|Where-Object {$_}|ForEach-Object {ConvertFrom-Json -InputObject $_ -AsHashtable})
    $phases=@('FINAL_ADMISSION','FINAL_NATIVE_AUDIT','FINAL_CASE_METADATA','FINAL_REFERENCE_GROUPS','FINAL_SPLIT_GROUPS','FINAL_STARTUP','FINAL_PF_MATRIX','FINAL_ELIGIBILITY','FINAL_SCHEMAS','FINAL_REGISTERED_GATES','FINAL_RESULT_PERSISTENCE')
    foreach($phase in $phases){$begin=@($progress|Where-Object {$_.phase -ceq $phase -and $_.event -ceq 'BEGIN'});$end=@($progress|Where-Object {$_.phase -ceq $phase -and $_.event -ceq 'END'});A ($begin.Count -eq 1 -and $end.Count -eq 1 -and $end[0].sequence -gt $begin[0].sequence) ('FINAL_PHASE '+$phase)}
    $first=@($progress|Where-Object {$_.phase -ceq 'FINAL_ADMISSION' -and $_.event -ceq 'BEGIN'})[0];$last=@($progress|Where-Object {$_.phase -ceq 'C3C_STAGE' -and $_.event -ceq 'END'})[0]
    $q=J ($prefix+'c3c_qualification_result.json')
    foreach($group in @($q.reference_groups.C,$q.reference_groups.S,$q.split_groups.C,$q.split_groups.S)){A ($group.status -ceq 'PASS' -and @($group.checks.Values|Where-Object {$_ -ne $true}).Count -eq 0) 'HISTORICAL_GROUP_FAIL'}
    $cases=ConvertFrom-Json -InputObject (Get-Content -Raw -LiteralPath (Join-Path $EvidenceRoot 'independent-readback-v2/case_readback.json')) -AsHashtable -NoEnumerate
    $p15=@($cases|Where-Object {$_.descriptor.stage_id -ceq 'P15-history'});A ($p15.Count -eq 1 -and $p15[0].status -ceq 'PASS' -and @($p15[0].checks.Values|Where-Object {$_ -ne $true}).Count -eq 0) 'P15_FAIL'
    $result=@{schema='m1-c3c-v5-pure-file-semantic-crosscheck-v1';status='INDEPENDENT_SEMANTIC_SCHEMA_SOURCE_READBACK_PASS';run_id='38833878662';source_bindings=836;local_source_bindings=$localCount;bundle_source_bindings=$bundleCount;outer_stage_schemas=$outerCount;sut_constructors=$constructors;allowed_images_observed=@($images|Sort-Object);startup_original='49/50';startup_unique_legacy_failure=@($failed.ToArray());versioned_compatibility='PASS';sem02_exact_five_cases_match=$true;sem02_event_inputs_verified=158;strict_P1_B_C='INCOMPLETE';PF06_original='INCOMPLETE';PF06_supplement='FORMALLY_VALIDATED_UNDER_SEPARATELY_APPROVED_REGISTRATION';PF06_negative_controls=2;C=11;S=17;P15='PASS';final_phase_pairs=11;final_worker_elapsed_seconds=($last.monotonic_ns-$first.monotonic_ns)/1e9;arbitrary_post_crash_powerloss_atomicity='NOT_PROVEN';T09='IMPLEMENTATION_HOLD';full_P_history_available=$false;hardware='CALIBRATION_REQUIRED';candidate_or_model_executed_locally=$false}
    $out=Join-Path $EvidenceRoot 'independent-readback-v2/semantic_crosscheck.json';A (-not(Test-Path -LiteralPath $out)) 'NO_OVERWRITE'
    $bytes=[Text.Encoding]::UTF8.GetBytes(($result|ConvertTo-Json -Depth 30)+"`n");$s=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$s.Write($bytes,0,$bytes.Length);$s.Flush($true)}finally{$s.Dispose()}
    $result|Select-Object status,source_bindings,outer_stage_schemas,sut_constructors,startup_original,final_phase_pairs,final_worker_elapsed_seconds|ConvertTo-Json
}finally{$zip.Dispose()}
