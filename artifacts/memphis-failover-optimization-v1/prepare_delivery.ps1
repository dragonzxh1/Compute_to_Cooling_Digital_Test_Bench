# Pure-file source/input/environment binding and derived delivery packaging only.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$evidence='D:/Github/c2c-evidence-review/memphis-failover-optimization-v1/run39129984525'
$delivery=Join-Path $repo 'artifacts/memphis-failover-optimization-v1-delivery'
$utf8=[Text.UTF8Encoding]::new($false)
$module=Join-Path $repo 'v0_2/tests/tools/memphis_failover_optimization_v1'
$source=Get-Content -LiteralPath (Join-Path $module 'source_manifest.json') -Raw|ConvertFrom-Json
foreach($map in @($source.source_raw_sha256,$source.v1_source_raw_sha256)) {foreach($b in $map.PSObject.Properties){
 $path=if($b.Name -ceq '.github/workflows/ci.yml'){Join-Path $module 'infra/ci-branch-only.yml'}else{Join-Path $repo $b.Name}
 if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $b.Value){throw ('SOURCE_DRIFT '+$b.Name)}
}}
$freezePath=Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json'
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
foreach($b in $freeze.source_raw_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PROTECTED_SOURCE_DRIFT '+$b.Name)}}
$proof=Get-Content -LiteralPath (Join-Path $evidence 'independent_file_verification.json') -Raw|ConvertFrom-Json
$inputs=[ordered]@{}
$originalDir='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
$expected=@{'00'='f366d8001fdb785c5b41cf149886eefac1ad9e79d1b498f0244cc2cdffd915b7';'01'='5c52fec8ad34b675cc6294d699754fb896f2e31abc120c4a6bc8dfac29b9e73c'}
foreach($key in @('00','01')){
 $files=@(Get-ChildItem -LiteralPath $originalDir -File|Where-Object Name -like ($key+'_*'))
 if($files.Count -ne 1){throw 'EXACT_CUSTOMER_ORIGINAL'}
 $hash=(Get-FileHash -LiteralPath $files[0].FullName).Hash.ToLowerInvariant()
 if($hash -cne $expected[$key]){throw 'CUSTOMER_ORIGINAL_DRIFT'}
 $inputs[$key]=@{filename=$files[0].Name;raw_sha256=$hash;identity='CUSTOMER_FINAL00_01';original_document_uploaded=$false}
}
$binding=[ordered]@{schema='MEMPHIS-FAILOVER-OPTIMIZATION-SOURCE-INPUT-ENVIRONMENT-v1';execution_commit='a07e5fba7d78f34ab907ce209399068f9c92c760';run=39129984525;manifest_raw_sha256='715d8d9cd7a5d99ddccff2373754ee6f32e3084e48e3deffecf8b91702421bef';registration_raw_sha256=(Get-FileHash (Join-Path $module 'registration.json')).Hash.ToLowerInvariant();candidate_sha256=$source.candidate_sha256;source=$source;protected_source_raw_sha256=$freeze.source_raw_sha256;protected_manifest_raw_sha256=(Get-FileHash $freezePath).Hash.ToLowerInvariant();customer_inputs=$inputs;environment=@{images=@($proof.stages.image|Sort-Object -Unique);python='3.11.9';dependencies=@{numpy='2.4.6';pytest='9.1.1';jsonschema='4.26.0'};cpu_rate=2500;process_mb=1024;job_mb=2048;wall_ms=480000;actual_stages=$proof.stages};formal=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'source_input_environment_manifest.json'),($binding|ConvertTo-Json -Depth 35),$utf8)
Copy-Item -LiteralPath (Join-Path $evidence 'official_artifacts.json') -Destination (Join-Path $delivery 'official_artifacts.json')
$official=Get-ChildItem -LiteralPath (Join-Path $evidence 'official-final') -Recurse -Filter comparisons.json|Select-Object -First 1
if((Get-FileHash $official.FullName).Hash -cne (Get-FileHash (Join-Path $delivery 'comparisons.json')).Hash){throw 'DERIVED_NUMERICAL_JSON_DRIFT'}
$records=foreach($f in Get-ChildItem -LiteralPath $delivery -File|Where-Object Name -notin @('package_manifest.json','delivery_publication_receipt.json')){
 @{path=$f.Name;bytes=$f.Length;raw_sha256=(Get-FileHash -LiteralPath $f.FullName).Hash.ToLowerInvariant()}
}
$package=[ordered]@{schema='MEMPHIS-FAILOVER-OPTIMIZATION-DELIVERY-v1.1';execution_commit=$binding.execution_commit;run=39129984525;scope='26 dynamic comparisons;17 refusal/positive witnesses;FINAL;28 controlled stages';software='BOUNDED_SOFTWARE_COMPARISON_COMPLETED';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';manifest_raw_sha256=$binding.manifest_raw_sha256;source_input_environment_manifest_sha256=(Get-FileHash (Join-Path $delivery 'source_input_environment_manifest.json')).Hash.ToLowerInvariant();official_numeric_json_sha256=(Get-FileHash $official.FullName).Hash.ToLowerInvariant();official_html_sha256=(Get-FileHash (Join-Path $official.DirectoryName 'engineering_report.html')).Hash.ToLowerInvariant();official_report_sha256=(Get-FileHash (Join-Path $official.DirectoryName 'DESIGN_DECISION_REPORT_ZH.md')).Hash.ToLowerInvariant();derivation='v1.1 Chinese quantitative interpretation, explicit mesh/preconditioning/recharge confound limits, human-readable event tables; model and numerical JSON unchanged';files=@($records);raw_zip_count=$proof.archives.Count;raw_files=$proof.raw_files;raw_logs_sha256=$proof.raw_logs_sha256;formal=$false;procurement=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'package_manifest.json'),($package|ConvertTo-Json -Depth 15),$utf8)
foreach($f in Get-ChildItem -LiteralPath $delivery -File){Copy-Item -LiteralPath $f.FullName -Destination (Join-Path (Join-Path $evidence 'delivery') $f.Name)}
[PSCustomObject]@{package_sha256=(Get-FileHash (Join-Path $delivery 'package_manifest.json')).Hash.ToLowerInvariant();new_source=@($source.source_raw_sha256.PSObject.Properties).Count;preserved_source=@($source.v1_source_raw_sha256.PSObject.Properties).Count;protected_source=@($freeze.source_raw_sha256.PSObject.Properties).Count;files=@($records).Count}|ConvertTo-Json
