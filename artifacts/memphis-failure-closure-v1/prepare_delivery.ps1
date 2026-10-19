param([Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$Commit,[Parameter(Mandatory)][string]$Manifest)
# Packaging actual verified outputs only; no local model/Python execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$utf8=[Text.UTF8Encoding]::new($false)
$evidence='D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$RunId
$module=Join-Path $repo 'v0_2/tests/tools/memphis_failure_closure_v1'
$delivery=Join-Path $repo 'artifacts/memphis-failure-closure-v1-delivery';New-Item -ItemType Directory -Path $delivery -Force|Out-Null
$proof=Get-Content (Join-Path $evidence 'independent_file_verification.json') -Raw|ConvertFrom-Json
if($proof.status -cne 'OFFICIAL_ZIP_RAW_AND_RUNTIME_INDEPENDENT_FILE_VERIFICATION_PASS' -or $proof.source_commit -cne $Commit -or $proof.manifest_sha256 -cne $Manifest -or $proof.stages.Count -ne 40){throw 'ACTUAL_COMPLETE_VERIFICATION_REQUIRED'}
if((Get-FileHash (Join-Path $module 'source_manifest.json')).Hash.ToLowerInvariant() -cne $Manifest){throw 'MANIFEST_DRIFT'}
$source=Get-Content (Join-Path $module 'source_manifest.json') -Raw|ConvertFrom-Json
foreach($map in @($source.source_raw_sha256,$source.v1_source_raw_sha256)){foreach($b in $map.PSObject.Properties){
 $p=if($b.Name -ceq '.github/workflows/ci.yml'){Join-Path $module 'infra/ci-branch-only.yml'}else{Join-Path $repo $b.Name}
 if((Get-FileHash $p).Hash.ToLowerInvariant() -cne $b.Value){throw ('SOURCE_DRIFT '+$b.Name)}
}}
$freezePath=Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json';$freeze=Get-Content $freezePath -Raw|ConvertFrom-Json
foreach($b in $freeze.source_raw_sha256.PSObject.Properties){if((Get-FileHash (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw ('PROTECTED_SOURCE_DRIFT '+$b.Name)}}
$inputs=[ordered]@{};$originalDir='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
$expected=@{'00'='f366d8001fdb785c5b41cf149886eefac1ad9e79d1b498f0244cc2cdffd915b7';'01'='5c52fec8ad34b675cc6294d699754fb896f2e31abc120c4a6bc8dfac29b9e73c'}
foreach($key in @('00','01')){
 $f=@(Get-ChildItem -LiteralPath $originalDir -File|Where-Object Name -like ($key+'_*'));if($f.Count -ne 1){throw 'EXACT_CUSTOMER_ORIGINAL'}
 $h=(Get-FileHash $f[0].FullName).Hash.ToLowerInvariant();if($h -cne $expected[$key]){throw 'CUSTOMER_ORIGINAL_DRIFT'}
 $inputs[$key]=@{filename=$f[0].Name;raw_sha256=$h;authority='CUSTOMER_FINAL00_01_V9';original_uploaded=$false}
}
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $evidence ('memphis-closure-compact-final-'+$RunId+'.zip')))
try{foreach($e in $z.Entries|Where-Object {$_.FullName -match '(^|/)FINAL/[^/]+\.(json|csv|md|html)$'}){
 $dest=Join-Path $delivery $e.Name
 if(Test-Path $dest){$s=$e.Open();try{$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()};if((Get-FileHash $dest).Hash.ToLowerInvariant() -cne $hash){throw ('DELIVERED_FILE_ALREADY_DIFFERS '+$e.Name)}}
 else{$s=$e.Open();$out=[IO.File]::Open($dest,[IO.FileMode]::CreateNew);try{$s.CopyTo($out)}finally{$s.Dispose();$out.Dispose()}}
}}finally{$z.Dispose()}
$summary=Get-Content (Join-Path $delivery 'closure_summary.json') -Raw|ConvertFrom-Json
if($summary.source_commit -cne $Commit -or $summary.manifest_sha256 -cne $Manifest -or $summary.dynamic_trials -ne 127 -or $summary.tank_trials -ne 340){throw 'ACTUAL_RESULT_COVERAGE'}
foreach($name in @('independent_file_verification.json','official_artifacts.json','official_run.json')){Copy-Item -LiteralPath (Join-Path $evidence $name) -Destination (Join-Path $delivery $name)}
Copy-Item -LiteralPath (Join-Path $evidence 'independent_event_boundary_file_proof.json') -Destination (Join-Path $delivery 'independent_event_boundary_file_proof.json')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'original_valve_excitation_file_proof.json') -Destination (Join-Path $delivery 'original_valve_excitation_file_proof.json')
$preserved=@();foreach($id in @('39146509431','39146681509','39180072218')){$preserved+=Get-Content ('D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$id+'/preserved_failed_run.json') -Raw|ConvertFrom-Json}
[IO.File]::WriteAllText((Join-Path $delivery 'preserved_failed_runs.json'),($preserved|ConvertTo-Json -Depth 35),$utf8)
$binding=[ordered]@{schema='MEMPHIS-FAILURE-CLOSURE-SOURCE-INPUT-ENVIRONMENT-v1';run=[long]$RunId;execution_commit=$Commit;manifest_raw_sha256=$Manifest;source=$source;registration_sha256=(Get-FileHash (Join-Path $module 'registration.json')).Hash.ToLowerInvariant();protected_source_raw_sha256=$freeze.source_raw_sha256;protected_manifest_raw_sha256=(Get-FileHash $freezePath).Hash.ToLowerInvariant();customer_inputs=$inputs;environment=@{images=@($proof.stages.image|Sort-Object -Unique);python='3.11.9';dependencies=@{numpy='2.4.6';pytest='9.1.1';jsonschema='4.26.0'};stages=$proof.stages};prior_official_run=39136524640;prior_raw_robust_zip_sha256='6103ea42e1b0746991c021a95a664fe212805d0e0e654a23da6785fa529f1e55';prior_delivery='f9d2b2fbae5feb3b3421f980dee837a2868247d8';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';formal=$false;procurement=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'source_input_environment_manifest.json'),($binding|ConvertTo-Json -Depth 40),$utf8)
$records=foreach($f in Get-ChildItem $delivery -File|Where-Object Name -notin @('package_manifest.json','delivery_publication_receipt.json')){@{path=$f.Name;bytes=$f.Length;raw_sha256=(Get-FileHash $f.FullName).Hash.ToLowerInvariant()}}
$derived=if(Test-Path (Join-Path $delivery 'critical_plot_provenance.json')){Get-Content (Join-Path $delivery 'critical_plot_provenance.json') -Raw|ConvertFrom-Json}else{$null}
$package=[ordered]@{schema='MEMPHIS-FAILURE-CLOSURE-DELIVERY-v1';execution_commit=$Commit;run=[long]$RunId;scope='Finite engineering software failure diagnosis, component sensitivity and supplier protocol proposal, NOT OEM qualification';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';manifest_raw_sha256=$Manifest;source_input_environment_manifest_sha256=(Get-FileHash (Join-Path $delivery 'source_input_environment_manifest.json')).Hash.ToLowerInvariant();derivation_note='Official raw HTML/Markdown/JSON untouched; ENGINEERING_DECISION_ZH interprets actual outputs, clarifies incomplete source/reserve/numerical scope. Event-complete HTML/CSV decodes saved physical steps only; no local model execution. Original artifact_hashes indexes official FINAL, package_manifest indexes the full delivery.';derived_plot_provenance=$derived;model_source_changed_by_delivery=$false;files=@($records);raw_zip_count=$proof.archives.Count;raw_files=$proof.raw_files;raw_logs_sha256=$proof.raw_logs_sha256;formal=$false;procurement=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'package_manifest.json'),($package|ConvertTo-Json -Depth 20),$utf8)
$local=Join-Path $evidence 'delivery';New-Item -ItemType Directory -Path $local -Force|Out-Null
foreach($f in Get-ChildItem $delivery -File){Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $local $f.Name)}
@{files=@($records).Count;protected_sources=@($freeze.source_raw_sha256.PSObject.Properties).Count;package_sha256=(Get-FileHash (Join-Path $delivery 'package_manifest.json')).Hash.ToLowerInvariant()}|ConvertTo-Json
