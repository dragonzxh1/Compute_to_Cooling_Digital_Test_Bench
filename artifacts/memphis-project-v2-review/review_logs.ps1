param([string]$Root='D:/Github/c2c-evidence-review/memphis-project-v2/run38991705994')
# Persisted ZIP/log/JSON review only; no simulation or executable under review.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $Root 'raw_logs.zip'))
$parts=@();$names=@()
try{foreach($e in $zip.Entries){if($e.FullName.EndsWith('.txt')){$r=[IO.StreamReader]::new($e.Open());try{$parts+=$r.ReadToEnd();$names+=$e.FullName}finally{$r.Dispose()}}}}finally{$zip.Dispose()}
$logs=$parts -join "`n"
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$reg=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_project_v2/registration.json') -Raw|ConvertFrom-Json
$expected=@('NEGATIVE','NODE_PORT','SOURCE_COMPARISON')+@($reg.cases|ForEach-Object id)
foreach($stage in $expected){if($logs -notmatch ('INTEGRATION_STAGE_END '+[regex]::Escape($stage)+' PASS')){throw ('MISSING_RAW_LOG_STAGE_END '+$stage)}}
if($logs -notmatch 'MEMPHIS_REPORT_COMPLETED stages=31 model_cases=24'){throw 'MISSING_REPORT_LOG_COMPLETION'}
# pytest is invoked in-process with quiet flags: its persisted stdout carries
# one dot per passing item, not the CLI's optional "71 passed" summary.
$negative=@(Get-ChildItem (Join-Path $Root 'full') -Recurse -File -Filter stdout.raw|Where-Object {$_.Directory.Name -ceq 'NEGATIVE'})
if($negative.Count -ne 1 -or (Get-Content $negative[0].FullName -Raw) -notmatch '(?m)^\.{71}\s+\[100%\]\r?$'){throw 'PERSISTED_71_TEST_ITEMS_NOT_PROVEN'}
$run=Get-Content (Join-Path $Root 'run_metadata.json') -Raw|ConvertFrom-Json
if($run.id -ne 38991705994 -or $run.run_attempt -ne 1 -or $run.head_sha -cne '2f5f5347539df9af8023ae35b5292505bbe1243b' -or $run.conclusion -cne 'success'){throw 'RUN_METADATA_IDENTITY'}
$index=Get-Content (Join-Path $Root 'official_artifact_index.json') -Raw|ConvertFrom-Json
$reportZip=Join-Path $Root 'memphis-consolidated-report-38991705994.zip'
$out=Join-Path $Root 'report-complete'
New-Item -ItemType Directory -Path $out -Force|Out-Null
$zip=[IO.Compression.ZipFile]::OpenRead($reportZip)
try{foreach($name in @('consolidated_report.json','engineering_report.html')){
 $entry=$zip.GetEntry($name);if($null -eq $entry){throw ('REPORT_ENTRY_MISSING '+$name)}
 $path=Join-Path $out $name
 if(-not(Test-Path $path)){[IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$path,$false)}
 $s=$entry.Open();try{$expectedHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}
 if((Get-FileHash $path).Hash.ToLowerInvariant() -cne $expectedHash){throw 'EXTRACTED_REPORT_DRIFT'}
}}finally{$zip.Dispose()}
$report=Get-Content (Join-Path $out 'consolidated_report.json') -Raw|ConvertFrom-Json
foreach($case in $report.cases.PSObject.Properties){
 $match=@(Get-ChildItem (Join-Path $Root 'full') -Recurse -File -Filter independent_analysis.json|Where-Object {$_.Directory.Name -ceq $case.Name})
 if($match.Count -ne 1){throw ('EXACT_INDEPENDENT_ANALYSIS_REQUIRED '+$case.Name)}
 $analysis=Get-Content $match[0].FullName -Raw|ConvertFrom-Json
 if(($analysis|ConvertTo-Json -Depth 60 -Compress) -cne ($case.Value.analysis|ConvertTo-Json -Depth 60 -Compress)){throw ('CONSOLIDATED_ANALYSIS_DRIFT '+$case.Name)}
}
[ordered]@{status='RAW_LOG_AND_REPORT_BINDINGS_VERIFIED';run_id=$run.id;run_attempt=$run.run_attempt;
 raw_log_entries=$names;registered_stage_ends_verified=$expected.Count;bounded_pytest_checks_passed=71;
 report_model_analyses_bound_to_raw=$report.model_case_count;
 raw_logs_sha256=(Get-FileHash (Join-Path $Root 'raw_logs.zip')).Hash.ToLowerInvariant();
 report_json_sha256=(Get-FileHash (Join-Path $out 'consolidated_report.json')).Hash.ToLowerInvariant();
 report_html_sha256=(Get-FileHash (Join-Path $out 'engineering_report.html')).Hash.ToLowerInvariant();
 evidence_location=$Root;interrupted_C_drive_download_preserved='memphis-raw-baseline-38991705994.zip.partial-preserved';
 official_artifact_digests=@($index.artifacts|Select-Object id,name,size_in_bytes,digest)}|ConvertTo-Json -Depth 8
