# Generate a non-circular hash inventory from already reviewed files only.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$files=@('docs/MEMPHIS_PROJECT_V2_REPAIR.md','docs/MEMPHIS_PROJECT_V2_RESULTS_20261017.md')
$files+=@('.gitattributes','BUILD1_FAILURE.md','build2_run_registration.json','download_official.ps1','verify_official.ps1','review_logs.ps1','publish_snapshot.ps1','build_delivery_manifest.ps1','independent_verification.json','log_report_verification.json','publication_receipt_2f5f534.json','delivered/consolidated_report.json','delivered/engineering_report.html')|ForEach-Object {'artifacts/memphis-project-v2-review/'+$_}
$records=@();foreach($name in $files){$p=Join-Path $repo $name;$records+=@{path=$name;bytes=(Get-Item $p).Length;raw_sha256=(Get-FileHash $p).Hash.ToLowerInvariant()}}
$review=Get-Content (Join-Path $PSScriptRoot 'log_report_verification.json') -Raw|ConvertFrom-Json
$failed=Get-Content (Join-Path $PSScriptRoot 'failed-run38991246285/official_artifact_index.json') -Raw|ConvertFrom-Json
$body=[ordered]@{schema='MEMPHIS-V2-REPAIR-DELIVERY-v1';scope='BOUNDED_REMOTE_DEVELOPMENT_SOFTWARE_FIX_NOT_THERMAL_QUALIFICATION';
 execution_commit='2f5f5347539df9af8023ae35b5292505bbe1243b';run_id=38991705994;run_attempt=1;
 source_manifest_raw_sha256='0fae67b3b430f7072030f5338e8ff54512c9e9c0c0eb1f135efabdd088ec21a3';
 registration_raw_sha256=(Get-FileHash (Join-Path $repo 'v0_2/tests/tools/memphis_project_v2/registration.json')).Hash.ToLowerInvariant();
 environment=@{image='20261012.333.1';python='3.11.9';numpy='2.4.6';pytest='9.1.1';jsonschema='4.26.0';node='22.23.3';cpu_percent=25;process_MiB=1024;job_MiB=2048;stage_wall_budget_s=480};
 result=@{software_fix='DEVELOPMENT_VERIFIED';thermal='CONDITIONAL_45C_EXCEEDED';continuity='CONDITIONAL_NOT_MET';equipment='NOT_VERIFIED';OEM='CALIBRATION_REQUIRED';global_CI='FAIL_COLLECTION_CONFIGURATION';formal_C3C='NOT_RUN';production=$false;hardware=$false;phase6=$false};
 official_artifact_digests=$review.official_artifact_digests;official_raw_logs_sha256=$review.raw_logs_sha256;
 preserved_failed_run=@{id=38991246285;status='FAIL_NOT_RELABELED';official_artifact_digests=@($failed.artifacts|Select-Object id,name,size_in_bytes,digest);raw_logs_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'failed-run38991246285/raw_logs.zip')).Hash.ToLowerInvariant()};
 global_CI_log_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'general_ci_failed.log')).Hash.ToLowerInvariant();
 files=$records;self_hash_rule='This manifest excludes itself and its later Git publication receipt; hash these raw bytes separately.'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'delivery_manifest.json'),($body|ConvertTo-Json -Depth 15),(New-Object Text.UTF8Encoding($false)))
Get-FileHash (Join-Path $PSScriptRoot 'delivery_manifest.json') -Algorithm SHA256
