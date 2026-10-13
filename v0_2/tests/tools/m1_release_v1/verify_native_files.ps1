# Inspect completed records only. No local model or native executor is launched.
param([Parameter(Mandatory)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path -LiteralPath $EvidenceRoot).Path

$base=Join-Path $root 'native-union/liquid-recovery-v1/stream-38423165745-1'
if(@(Get-ChildItem -LiteralPath $base -Filter batch_stop.json -Recurse).Count){throw 'NATIVE_STOP_EVIDENCE_PRESENT'}
$expected=@('prepare','reference-gate','split-u','final')
$expected+=@(0..9|ForEach-Object{'ref-'+$_})
$expected+=@(0..10|ForEach-Object{'select-'+$_})
$expected+=@(0..9|ForEach-Object{'split-'+$_})
$expected+=@(0..49|ForEach-Object{'startup-'+$_})
$expected+=@(0..100|ForEach-Object{'prefix-'+$_})
$expected+=@(0..100|ForEach-Object{'schema-'+$_})
foreach($name in $expected){if(-not(Test-Path -LiteralPath (Join-Path $base ($name+'/batch_complete.json')))){throw ('MISSING_PRIMARY_JOB_EVIDENCE '+$name)}}
$batches=Get-ChildItem -LiteralPath $base -Filter batch_complete.json -Recurse
$constructors=0;$sutStages=0
$stages=0;$captures=0;$identities=@();$maxPrivate=0L;$maxWorking=0L;$memorySamples=0
$batchRecords=@()
function Software-Json($Identity){
    $data=[ordered]@{}
    foreach($p in ($Identity.PSObject.Properties|Sort-Object Name)){if($p.Name -cne 'host'){$data[$p.Name]=$p.Value}}
    return ($data|ConvertTo-Json -Depth 10 -Compress)
}
$finalResult=Get-Content -LiteralPath (Join-Path $root 'final/m1-autonomous-development/stream-38423165745-1/development_result.json') -Raw|ConvertFrom-Json
$softwareExpected=Software-Json $finalResult.execution_audit.software_identity
foreach($batch in $batches){
    $b=Get-Content -LiteralPath $batch.FullName -Raw|ConvertFrom-Json
    $name=$batch.Directory.Name
    if($name -notin $expected -and $name -notmatch '^prefix-(\d+)-batch-\d+$'){throw 'UNREGISTERED_NATIVE_JOB_DIRECTORY'}
    if($b.status -cne 'COMPLETE'){throw 'NATIVE_BATCH_INCOMPLETE'}
    for($i=0;$i -lt $b.stages.Count;$i++){
        $s=$b.stages[$i]
        if($s.status -cne 'PASS'){throw 'NATIVE_STAGE_FAIL'}
        $result=Join-Path $batch.DirectoryName ('stage-{0:d3}-result.json' -f $i)
        if((Get-FileHash -LiteralPath $result -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.receipts[$i].result_raw_sha256){throw 'NATIVE_STAGE_RECEIPT_DRIFT'}
        $accepted=Get-Content -LiteralPath $result -Raw|ConvertFrom-Json
        if(-not $accepted.source_verified -or -not $accepted.environment_verified -or -not $accepted.evidence_verified -or
           -not $accepted.primitive_consistent -or -not $accepted.passed){throw 'SOURCE_ENVIRONMENT_OR_ACCEPTANCE_NOT_VERIFIED'}
        $dir=Join-Path $batch.DirectoryName $s.stage_id
        $proof=Get-Content -LiteralPath (Join-Path $dir 'external_job_identity.json') -Raw|ConvertFrom-Json
        $native=Get-Content -LiteralPath (Join-Path $dir 'job_status.json') -Raw|ConvertFrom-Json
        $ready=Get-Content -LiteralPath (Join-Path $dir 'ready.json') -Raw|ConvertFrom-Json
        $release=Get-Content -LiteralPath (Join-Path $dir 'release.json') -Raw|ConvertFrom-Json
        $start=Get-Content -LiteralPath (Join-Path $dir 'job_start.json') -Raw|ConvertFrom-Json
        if($ready.pid -ne $native.pid -or $release.actual_python_pid -ne $ready.pid -or
           $proof.target_job_name -cne $start.job_name -or -not $native.assigned_before_resume -or -not $native.resumed -or
           $start.wall_ms -ne 480000 -or -not $start.kill_on_close -or $proof.cpu_flags -ne 5 -or
           $proof.max_active_processes -ne 4 -or $proof.modules_before_workload -notcontains 'python.exe' -or
           (Get-FileHash -LiteralPath (Join-Path $dir 'external_job_identity.json') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $release.external_proof_raw_sha256){throw 'ACTUAL_PID_RELEASE_AND_JOB_LINK_INVALID'}
        if(-not $proof.in_target_job -or $proof.actual_python_pid -ne $native.pid -or $proof.cpu_rate -ne 2500 -or
           $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or $native.outcome -cne 'EXITED' -or
           $native.child_exitcode -ne 0 -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0){throw 'NATIVE_JOB_IDENTITY_LIMIT_OR_CLEANUP_INVALID'}
        $raw=Get-Content -LiteralPath (Join-Path $dir 'raw_evidence_receipts.json') -Raw|ConvertFrom-Json
        foreach($r in $raw.PSObject.Properties){
            if($r.Value.status -cne 'PERSISTED' -or (Get-FileHash -LiteralPath (Join-Path $dir $r.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $r.Value.raw_sha256){throw 'NATIVE_RAW_CAPTURE_DRIFT'}
            $captures++
        }
        $worker=Get-Content -LiteralPath (Join-Path $dir 'result.json') -Raw|ConvertFrom-Json
        if($worker.status -cne 'PASS'){throw 'NATIVE_WORKER_RESULT_INVALID'}
        if($worker.sut -cne 'v0_2.tests.tools.m1_engine_v4.engine.SplitEngine'){throw 'V4_WORKER_TARGET_IDENTITY'}
        if($s.stage_id -match '^STARTUP-' -or $s.stage_id -match '^CASE-.*-(SPLIT|REPEAT-|PREFIX_ONE-|PREFIX_BATCH-)'){
            if(@($worker.sut_constructors).Count -eq 0){throw 'ACTUAL_V4_CONSTRUCTOR_MISSING'}
            $sutStages++
        }
        foreach($constructor in $worker.sut_constructors){
            if($constructor.class -cne 'v0_2.tests.tools.m1_engine_v4.engine.SplitEngine' -or $constructor.post_module -cne 'v0_2.tests.tools.m1_engine_v4.engine'){throw 'WRONG_ACTUAL_V4_ENGINE'}
            $constructors++
        }
        if((Software-Json $worker.runtime_identity_before) -cne (Software-Json $worker.runtime_identity_after)){throw 'V4_BEFORE_AFTER_DRIFT'}
        if($ready.executable -cne $worker.runtime_identity_before.executable){throw 'ACTUAL_PYTHON_EXECUTABLE_IDENTITY'}
        if((Software-Json $worker.runtime_identity_after) -cne $softwareExpected){throw 'AFTER_SOFTWARE_ENVIRONMENT_DRIFT'}
        if($s.stage_id -ceq 'ENVIRONMENT'){
            $software=[ordered]@{}
            foreach($p in ($worker.runtime_identity.PSObject.Properties|Sort-Object Name)){
                if($p.Name -cne 'host'){$software[$p.Name]=$p.Value}
            }
            $identities+=($software|ConvertTo-Json -Depth 10 -Compress)
        }
        $memory=Get-Content -LiteralPath (Join-Path $dir 'external_memory_samples.json') -Raw|ConvertFrom-Json
        foreach($sample in $memory.samples){
            $memorySamples++
            $maxPrivate=[Math]::Max($maxPrivate,[long]$sample.private_bytes)
            $maxWorking=[Math]::Max($maxWorking,[long]$sample.working_set_bytes)
        }
        $stages++
    }
    $batchRecords+=@{job=$name;stages=@($b.stages).Count;raw_sha256=(Get-FileHash -LiteralPath $batch.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
if($expected.Count -ne 287 -or $identities.Count -ne 287 -or @($identities|Select-Object -Unique).Count -ne 1){throw 'NATIVE_JOB_OR_SOFTWARE_ENVIRONMENT_COVERAGE_DRIFT'}
$summary=@{scope='M1_REMOTE_DEVELOPMENT_ONLY';run_id=38423165745;source_commit='717a98dd89ece8d3b6944a80727b32f20a311b8b';readback='PASS';
    primary_execution_jobs_verified=287;pure_plan_jobs=1;native_batches_verified=@($batches).Count;native_stages_verified=$stages;
    raw_captures_verified=$captures;software_host_registrations=287;software_environment_identical=$true;
    software_environment=($identities[0]|ConvertFrom-Json);actual_python_pid_job_limits_cleanup='PASS';
    externally_sampled_private_bytes_max=$maxPrivate;externally_sampled_working_set_bytes_max=$maxWorking;
    memory_samples=$memorySamples;sampled_max_is_not_exact_peak=$true;batch_receipts=$batchRecords;
    original_final_embedded_audit_batches=$finalResult.execution_audit.batches;original_final_embedded_audit_stages=$finalResult.execution_audit.stages;actual_v4_constructors_verified=$constructors;sut_execution_stages=$sutStages;original_final_result_not_rewritten=$true;
    supplementary_union_from_owned_artifacts=$true;local_python_native_model_executed=$false;formal_qualification=$false}
$bytes=[Text.Encoding]::UTF8.GetBytes(($summary|ConvertTo-Json -Depth 12))
$file=[IO.File]::Open((Join-Path $root 'full-native-union-readback.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
Write-Host ('FULL_NATIVE_UNION_READBACK_PASS jobs=287 batches='+@($batches).Count+' stages='+$stages+' raw='+$captures)
