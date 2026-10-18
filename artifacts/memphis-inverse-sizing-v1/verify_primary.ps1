# Verify supplementary remote pure-file results, never run model locally.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$id='39141542985';$root='D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run39136524640/primary-review'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$utf8=[Text.UTF8Encoding]::new($false)
$run=gh api ($api+'/actions/runs/'+$id)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.head_sha -cne '43269d7a01bb8244cad05bfffe38e984e1bd1a2b' -or $run.run_attempt -ne 1){throw 'EXACT_REVIEW_RUN'}
New-Item -ItemType Directory -Path $root -Force|Out-Null
$index=gh api ($api+'/actions/runs/'+$id+'/artifacts?per_page=100')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $index.total_count -ne 6){throw 'REVIEW_ARCHIVES'}
$archives=@();Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach($a in $index.artifacts){
 $zip=Join-Path $root ($a.name+'.zip');if(-not(Test-Path $zip)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $zip;if($LASTEXITCODE -ne 0){throw 'REVIEW_DOWNLOAD'}}
 $h=(Get-FileHash $zip).Hash.ToLowerInvariant();if('sha256:'+$h -cne $a.digest){throw 'OFFICIAL_REVIEW_ZIP_HASH'}
 $dest=Join-Path $root $a.name;if(-not(Test-Path $dest)){[IO.Compression.ZipFile]::ExtractToDirectory($zip,$dest)}
 $archives+=@{name=$a.name;digest=$a.digest;sha256=$h;bytes=$a.size_in_bytes}
}
$official=Get-ChildItem (Join-Path (Split-Path $root) 'official-final') -Recurse -Filter forward_trials.json|Select-Object -First 1
$forward=[System.Text.Json.JsonDocument]::Parse([IO.File]::ReadAllText($official.FullName));$wanted=@{}
try{foreach($r in $forward.RootElement.EnumerateArray()){$wanted[$r.GetProperty('id').GetString()]=$r.GetProperty('raw_hashes').GetProperty('physics.json').GetString()}}finally{$forward.Dispose()}
$seen=@{};$stages=@();$rawResults=@();$reviewHash=(Get-FileHash (Join-Path $repo 'artifacts/memphis-inverse-sizing-v1-review/file_review.py')).Hash.ToLowerInvariant()
foreach($file in Get-ChildItem $root -Recurse -Filter review.json){
 $r=Get-Content $file.FullName -Raw|ConvertFrom-Json;$dir=$file.DirectoryName
 $proof=Get-Content (Join-Path $dir 'external_job_identity.json') -Raw|ConvertFrom-Json;$start=Get-Content (Join-Path $dir 'job_start.json') -Raw|ConvertFrom-Json;$native=Get-Content (Join-Path $dir 'job_status.json') -Raw|ConvertFrom-Json
 if($r.status -cne 'PASS' -or $r.review_commit -cne $run.head_sha -or $r.source_commit -cne '840e813dbc6ef0840c7e26850bc4ba6276dd4ffb' -or $r.reviewer_sha256 -cne $reviewHash){throw 'REVIEW_SOURCE_OR_RESULT'}
 if($r.pid -ne $proof.actual_python_pid -or $r.pid -ne $start.pid -or $proof.target_job_name -cne $start.job_name -or -not $proof.in_target_job -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 1024 -or $proof.job_mb -ne 2048 -or $start.wall_ms -ne 480000){throw 'REVIEW_ACTUAL_PID_OR_LIMIT'}
 if(-not $native.assigned_before_resume -or -not $native.resumed -or -not $native.cleanup_complete -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0 -or $native.outcome -cne 'EXITED'){throw 'REVIEW_POST_EXIT_CLEANUP'}
 foreach($case in $r.results){if($seen.ContainsKey($case.id) -or -not $wanted.ContainsKey($case.id) -or $case.physics_sha256 -cne $wanted[$case.id]){throw 'PRIMARY_CASE_DUPLICATE_OR_HASH'};$seen[$case.id]=$case.physics_sha256;$rawResults+=$case}
 $stages+=@{stage=$r.stage;pid=$r.pid;review_sha256=(Get-FileHash $file.FullName).Hash.ToLowerInvariant();job_status_sha256=(Get-FileHash (Join-Path $dir 'job_status.json')).Hash.ToLowerInvariant();active_after_cleanup=0;steps=($r.results.steps|Measure-Object -Sum).Sum}
}
$reg=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_inverse_sizing_v1/registration.json') -Raw|ConvertFrom-Json
$expected=@($reg.cases|Where-Object kind -in @('group','critical','joint','robust')|ForEach-Object id)
if($stages.Count -ne $expected.Count -or $seen.Count -ne $wanted.Count -or (Compare-Object ($stages.stage|Sort-Object) ($expected|Sort-Object))){throw 'PRIMARY_REVIEW_COMPLETE_COVERAGE'}
$log=Join-Path $root 'official_review_logs.zip';gh api ($api+'/actions/runs/'+$id+'/logs') > $log;if($LASTEXITCODE -ne 0){throw 'REVIEW_LOG_DOWNLOAD'}
$result=[ordered]@{status='INDEPENDENT_PRIMARY_HYDRAULIC_MASS_PUMP_HEAT_FILE_REVIEW_PASS';model_run=39136524640;review_run=[long]$id;review_commit=$run.head_sha;reviewer_sha256=$reviewHash;stages=$stages;cases=$rawResults;archives=$archives;model_not_rerun=$true;scope='Saved primary source/load/recharge Q-H, tank flow ownership, wire-to-liquid pump heat; not real equipment calibration';raw_logs_sha256=(Get-FileHash $log).Hash.ToLowerInvariant();engineering_approval=$false}
[IO.File]::WriteAllText((Join-Path $root 'primary_hydraulic_verification.json'),($result|ConvertTo-Json -Depth 20),$utf8)
@{stages=$stages.Count;cases=$seen.Count;steps=($stages.steps|Measure-Object -Sum).Sum;status=$result.status}|ConvertTo-Json
