param([Parameter(Mandatory)][string]$EvidenceRoot)
# Hash persisted evidence and delivery files only; never execute a model.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$verification=Get-Content (Join-Path $PSScriptRoot 'independent_verification.json') -Raw|ConvertFrom-Json
if($verification.status -cne 'OFFICIAL_PERSISTED_EVIDENCE_VERIFIED_NOT_EQUIPMENT_QUALIFICATION'){throw 'INDEPENDENT_REVIEW_REQUIRED'}
function Binding([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{bytes=$f.Length;raw_sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()}}
$paths=@('docs/MEMPHIS_SINGLE_RACK_BASELINE_V1.md','docs/MEMPHIS_SINGLE_RACK_RESULTS_20261017.md',
 'artifacts/memphis-single-rack-v1-review/.gitattributes',
 'artifacts/memphis-single-rack-v1-review/run_build1.json','artifacts/memphis-single-rack-v1-review/run_build2.json','artifacts/memphis-single-rack-v1-review/run_build3.json',
 'artifacts/memphis-single-rack-v1-review/publication_receipt_4093b7d.json','artifacts/memphis-single-rack-v1-review/publication_receipt_9a5df03.json','artifacts/memphis-single-rack-v1-review/publication_receipt_fe94f1b.json',
 'artifacts/memphis-single-rack-v1-review/BUILD1_FAILURE.md','artifacts/memphis-single-rack-v1-review/BUILD2_FAILURE.md',
 'artifacts/memphis-single-rack-v1-review/download_official.ps1','artifacts/memphis-single-rack-v1-review/verify_official.ps1',
 'artifacts/memphis-single-rack-v1-review/build_delivery_manifest.ps1','artifacts/memphis-single-rack-v1-review/publish_snapshot.ps1',
 'artifacts/memphis-single-rack-v1-review/independent_verification.json',
 'artifacts/memphis-single-rack-v1-review/delivered/consolidated_report.json','artifacts/memphis-single-rack-v1-review/delivered/engineering_report.md')
$files=[ordered]@{};foreach($p in $paths){$files[$p]=Binding (Join-Path $repo $p)}
$official=[ordered]@{};foreach($name in @('official_artifact_index.json','run_metadata.json','raw_logs.zip')){$official[$name]=Binding (Join-Path $EvidenceRoot $name)}
$failed=[ordered]@{}
foreach($id in @(39009958272,39010286517)){
 $dir=Join-Path (Split-Path $EvidenceRoot) ('failed-run'+$id);$entry=[ordered]@{}
 foreach($name in @('official_artifact_index.json','run_metadata.json','raw_logs.zip')){$entry[$name]=Binding (Join-Path $dir $name)}
 $meta=Get-Content (Join-Path $dir 'run_metadata.json') -Raw|ConvertFrom-Json
 $record=Get-Content (Join-Path $PSScriptRoot ('run_build'+$(if($id -eq 39009958272){'1'}else{'2'})+'.json')) -Raw|ConvertFrom-Json
 if($meta.id -ne $id -or $meta.status -cne 'completed' -or $meta.conclusion -cne 'failure' -or $meta.head_sha -cne $record.execution_commit){throw 'PRESERVED_FAILED_RUN_IDENTITY'}
 $index=Get-Content (Join-Path $dir 'official_artifact_index.json') -Raw|ConvertFrom-Json
 foreach($a in $index.artifacts){$b=Binding (Join-Path $dir ($a.name+'.zip'));if($b.bytes -ne $a.size_in_bytes -or 'sha256:'+$b.raw_sha256 -cne $a.digest){throw 'PRESERVED_FAILED_ZIP_HASH'}}
 $entry['official_zips']=@($index.artifacts|Select-Object id,name,size_in_bytes,digest)
 $failed[[string]$id]=$entry
}
$doc=Get-Content (Join-Path $repo 'v0_2/tests/tools/memphis_single_rack_v1/baseline_registration.json') -Raw|ConvertFrom-Json
$result=[ordered]@{schema='MEMPHIS-RACK-FIRST-DELIVERY-HASHES-v1';run=$verification.run;execution_commit=$verification.execution_commit;
 execution_manifest_raw_sha256=$verification.manifest_raw_sha256;scope='CONDITIONAL_OFFLINE_DEVELOPMENT_SINGLE_THEN_SIX_NOT_EQUIPMENT_QUALIFICATION';
 input_document_bindings=$doc.final_design_sources;official_artifact_zips=$verification.official_artifacts;official_metadata_and_logs=$official;
 preserved_failed_runs=$failed;delivery_files=$files;local_evidence_root=$EvidenceRoot;
 self_hash_note='This manifest excludes itself and later publication receipt to avoid circular identity; SHA256 is supplied separately.';
 formal_C3C=$false;production_hardware_Phase6=$false;local_model_execution=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'delivery_manifest.json'),($result|ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false)))
Get-FileHash (Join-Path $PSScriptRoot 'delivery_manifest.json') -Algorithm SHA256
