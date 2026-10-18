# Hash-only local packaging; no Python/native/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$evidence='D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run39136524640'
$delivery=Join-Path $repo 'artifacts/memphis-inverse-sizing-v1-delivery'
$utf8=[Text.UTF8Encoding]::new($false)
New-Item -ItemType Directory -Path $delivery -Force|Out-Null
$module=Join-Path $repo 'v0_2/tests/tools/memphis_inverse_sizing_v1'
$source=Get-Content (Join-Path $module 'source_manifest.json') -Raw|ConvertFrom-Json
if((Get-FileHash (Join-Path $module 'source_manifest.json')).Hash.ToLowerInvariant() -cne '33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'){throw 'MODEL_MANIFEST_DRIFT'}
foreach($map in @($source.source_raw_sha256,$source.v1_source_raw_sha256)){foreach($b in $map.PSObject.Properties){
 $path=if($b.Name -ceq '.github/workflows/ci.yml'){Join-Path $module 'infra/ci-branch-only.yml'}else{Join-Path $repo $b.Name}
 if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $b.Value){throw ('SOURCE_DRIFT '+$b.Name)}
}}
$freezePath=Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json';$freeze=Get-Content $freezePath -Raw|ConvertFrom-Json
foreach($b in $freeze.source_raw_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PROTECTED_SOURCE_DRIFT '+$b.Name)}}
$proof=Get-Content (Join-Path $evidence 'independent_file_verification.json') -Raw|ConvertFrom-Json
if($proof.status -cne 'OFFICIAL_ZIP_RAW_AND_RUNTIME_INDEPENDENT_FILE_VERIFICATION_PASS' -or $proof.stages.Count -ne 49){throw 'OFFICIAL_VERIFICATION_REQUIRED'}
$inputs=[ordered]@{};$originalDir='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
$expected=@{'00'='f366d8001fdb785c5b41cf149886eefac1ad9e79d1b498f0244cc2cdffd915b7';'01'='5c52fec8ad34b675cc6294d699754fb896f2e31abc120c4a6bc8dfac29b9e73c'}
foreach($key in @('00','01')){
 $files=@(Get-ChildItem -LiteralPath $originalDir -File|Where-Object Name -like ($key+'_*'));if($files.Count -ne 1){throw 'EXACT_ORIGINAL'}
 $hash=(Get-FileHash $files[0].FullName).Hash.ToLowerInvariant();if($hash -cne $expected[$key]){throw 'CUSTOMER_ORIGINAL_DRIFT'}
 $inputs[$key]=@{filename=$files[0].Name;raw_sha256=$hash;authority='CUSTOMER_FINAL00_01_V9';original_uploaded=$false}
}
$official=Get-ChildItem (Join-Path $evidence 'official-final') -Recurse -Filter inverse_sizing_results.json|Select-Object -First 1
if(-not $official){throw 'OFFICIAL_FINAL_REQUIRED'}
foreach($f in Get-ChildItem $official.DirectoryName -File|Where-Object {$_.Extension -in @('.csv','.md','.html') -or $_.Name -in @('inverse_sizing_results.json','device_feasible_ranges.json','forward_trials.json','buffer_trials.json','unit_results.json','precool_results.json','critical_ranges.json','analytic_requirements.json','pareto_feasible_region.json')}){
 Copy-Item $f.FullName (Join-Path $delivery $f.Name)
}
Copy-Item (Join-Path $evidence 'independent_file_verification.json') (Join-Path $delivery 'independent_file_verification.json')
Copy-Item (Join-Path $evidence 'official_artifacts.json') (Join-Path $delivery 'official_artifacts.json')
$primary=Join-Path $evidence 'primary-review/primary_hydraulic_verification.json'
$primaryProof=Get-Content $primary -Raw|ConvertFrom-Json
if($primaryProof.status -cne 'INDEPENDENT_PRIMARY_HYDRAULIC_MASS_PUMP_HEAT_FILE_REVIEW_PASS' -or $primaryProof.cases.Count -ne 133 -or $primaryProof.stages.Count -ne 25){throw 'PRIMARY_INDEPENDENT_REVIEW_REQUIRED'}
Copy-Item $primary (Join-Path $delivery 'primary_hydraulic_verification.json')
Copy-Item (Join-Path $evidence 'interactive-report.png') (Join-Path $delivery 'interactive-report.png')
$prior=@();foreach($id in @('39134808524','39134995538','39135290316')){$prior+=Get-Content ('D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run'+$id+'/preserved_evidence.json') -Raw|ConvertFrom-Json}
[IO.File]::WriteAllText((Join-Path $delivery 'preserved_preflights.json'),($prior|ConvertTo-Json -Depth 20),$utf8)
$binding=[ordered]@{schema='MEMPHIS-INVERSE-SIZING-SOURCE-INPUT-ENVIRONMENT-v1';execution_commit='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb';run=39136524640;manifest_raw_sha256=$proof.manifest_sha256;registration_raw_sha256=(Get-FileHash (Join-Path $module 'registration.json')).Hash.ToLowerInvariant();candidate_sha256=$source.candidate_sha256;source=$source;protected_source_raw_sha256=$freeze.source_raw_sha256;protected_manifest_raw_sha256=(Get-FileHash $freezePath).Hash.ToLowerInvariant();customer_inputs=$inputs;environment=@{images=@($proof.stages.image|Sort-Object -Unique);python='3.11.9';dependencies=@{numpy='2.4.6';pytest='9.1.1';jsonschema='4.26.0'};cpu_rate=2500;process_mb=1024;job_mb=2048;wall_ms=480000;actual_stages=$proof.stages};formal=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'source_input_environment_manifest.json'),($binding|ConvertTo-Json -Depth 35),$utf8)
foreach($name in @('inverse_sizing_results.json','forward_trials.json','engineering_report.html','MEMPHIS_MINIMUM_EQUIPMENT_REQUIREMENTS_ZH.md')){if((Get-FileHash (Join-Path $official.DirectoryName $name)).Hash -cne (Get-FileHash (Join-Path $delivery $name)).Hash){throw 'OFFICIAL_RESULT_DRIFT'}}
$records=foreach($f in Get-ChildItem $delivery -File|Where-Object Name -notin @('package_manifest.json','delivery_publication_receipt.json')){@{path=$f.Name;bytes=$f.Length;raw_sha256=(Get-FileHash $f.FullName).Hash.ToLowerInvariant()}}
$package=[ordered]@{schema='MEMPHIS-INVERSE-SIZING-DELIVERY-v1';execution_commit=$binding.execution_commit;run=$binding.run;scope='Bounded software inverse/forward sizing; finite scans/Pareto/uncertainty, not OEM guarantees';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';manifest_raw_sha256=$binding.manifest_raw_sha256;source_input_environment_manifest_sha256=(Get-FileHash (Join-Path $delivery 'source_input_environment_manifest.json')).Hash.ToLowerInvariant();independent_primary_review_run=39141542985;independent_primary_review_commit=$primaryProof.review_commit;official_html_sha256=(Get-FileHash (Join-Path $official.DirectoryName 'engineering_report.html')).Hash.ToLowerInvariant();official_report_sha256=(Get-FileHash (Join-Path $official.DirectoryName 'MEMPHIS_MINIMUM_EQUIPMENT_REQUIREMENTS_ZH.md')).Hash.ToLowerInvariant();derivation='Official HTML/JSON/Markdown unchanged. ENGINEERING_DECISION_ZH adds actual quantitative selection interpretation, separates forward/tank/recharge/normal-temperature targets, records unexcited stuck-valve and post-fault recharge gaps; no new PASS';files=@($records);raw_zip_count=$proof.archives.Count;raw_files=$proof.raw_files;raw_logs_sha256=$proof.raw_logs_sha256;formal=$false;procurement=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'package_manifest.json'),($package|ConvertTo-Json -Depth 20),$utf8)
$localDelivery=Join-Path $evidence 'delivery';New-Item -ItemType Directory -Path $localDelivery -Force|Out-Null
foreach($f in Get-ChildItem $delivery -File){Copy-Item $f.FullName (Join-Path $localDelivery $f.Name)}
@{package_sha256=(Get-FileHash (Join-Path $delivery 'package_manifest.json')).Hash.ToLowerInvariant();files=@($records).Count;protected_sources=@($freeze.source_raw_sha256.PSObject.Properties).Count}|ConvertTo-Json
