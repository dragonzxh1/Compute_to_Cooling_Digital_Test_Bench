# Deterministic, pure-file delivery assembly. Never launches Python/native/model.
param([Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_delivery_v4/native_closure.ps1')
function A([bool]$ok,[string]$why){if(-not $ok){throw $why}}
function Get-DeliveryFileSha([string]$path){return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function J([string]$path){return ,(ConvertFrom-Json -InputObject (Get-Content -LiteralPath $path -Raw) -AsHashtable -NoEnumerate)}
$definitionPath=Join-Path $repo 'artifacts/m1-c3c-v5-freeze/executable_proposal.json'
A ((Get-DeliveryFileSha $definitionPath) -ceq '18d54940b672e4ec06b0c0c0a6691cf15219ee96e01b7864b31fe00a1adf23c8') 'FROZEN_PROPOSAL_DRIFT'
$definition=J $definitionPath
function VerifySources {
    $bundle=[IO.Compression.ZipFile]::OpenRead((Join-Path $repo $definition.bundle_path));$hasher=[Security.Cryptography.SHA256]::Create();$count=0
    try{foreach($b in $definition.source_raw_sha256.GetEnumerator()){
        $path=Join-Path $repo $b.Key
        if(Test-Path -LiteralPath $path){$sha=Get-DeliveryFileSha $path}else{$entry=$bundle.GetEntry($b.Key);A ($null -ne $entry) ('SOURCE_MISSING '+$b.Key);$s=$entry.Open();try{$sha=[Convert]::ToHexString($hasher.ComputeHash($s)).ToLowerInvariant()}finally{$s.Dispose()}}
        A ($sha -ceq $b.Value) ('PROTECTED_SOURCE_DRIFT '+$b.Key);$count++
    }}finally{$bundle.Dispose();$hasher.Dispose()}
    A ($count -eq 836) 'SOURCE_BINDING_COUNT'
}
VerifySources
$resultRoot=Join-Path $repo 'artifacts/m1-c3c-v5-formal-result-38833878662'
A ((Get-DeliveryFileSha (Join-Path $resultRoot 'independent_verdict.json')) -ceq '80c6685a8f4e3f9c82c795e0d28632883e12c5f72e4e822a928d14708cbf1525') 'FORMAL_VERDICT_DRIFT'
A ((Get-DeliveryFileSha (Join-Path $resultRoot 'file_manifest.json')) -ceq '20b91edf6b123b255de1e314040104d9f9f4c9bbde49321321f7e4da1ec41cb4') 'FORMAL_READBACK_MANIFEST_DRIFT'
$resultManifest=J (Join-Path $resultRoot 'file_manifest.json')
foreach($f in $resultManifest.files){$path=Join-Path $resultRoot $f.path;A ((Get-DeliveryFileSha $path) -ceq $f.sha256 -and (Get-Item -LiteralPath $path).Length -eq $f.bytes) ('FORMAL_EVIDENCE_DRIFT '+$f.path)}
$sdkPath=Join-Path $repo 'artifacts/m1-sdk-streaming-v3/source-sdk.zip'
$sdkSha='820baee49b3170dc07bc7bb6bfa3ffdc9732c9c79492ccc7df43699202e6bf78'
A ((Get-DeliveryFileSha $sdkPath) -ceq $sdkSha) 'SEALED_SDK_DRIFT'
$sdk=[IO.Compression.ZipFile]::OpenRead($sdkPath);$hasher=[Security.Cryptography.SHA256]::Create();$sdkHashes=@{};$sdkSizes=@{}
try{
    foreach($e in $sdk.Entries){A ($e.FullName -notmatch '(^/|:|\\|(^|/)\.\.(/|$))' -and -not $sdkHashes.ContainsKey($e.FullName)) 'UNSAFE_SDK_ENTRY';$s=$e.Open();try{$sdkHashes[$e.FullName]=[Convert]::ToHexString($hasher.ComputeHash($s)).ToLowerInvariant();$sdkSizes[$e.FullName]=$e.Length}finally{$s.Dispose()}}
    $r=[IO.StreamReader]::new($sdk.GetEntry('DELIVERY_MANIFEST.json').Open());try{$sdkManifest=ConvertFrom-Json -InputObject $r.ReadToEnd() -AsHashtable}finally{$r.Dispose()}
    A ($sdkManifest.files.Count -eq 675 -and $sdkHashes.Count -eq 676) 'SDK_PAYLOAD_COUNT'
    foreach($f in $sdkManifest.files){A ($sdkHashes[$f.path] -ceq $f.sha256 -and $sdkSizes[$f.path] -eq $f.bytes) ('SDK_INTERNAL_DRIFT '+$f.path)}
}finally{$sdk.Dispose();$hasher.Dispose()}
$shared=0;$same=0;$diff=[Collections.Generic.List[object]]::new();$sdkOnly=[Collections.Generic.List[string]]::new()
foreach($f in $sdkManifest.files){if($definition.source_raw_sha256.ContainsKey($f.path)){
    $shared++;if($f.sha256 -ceq $definition.source_raw_sha256[$f.path]){$same++}else{$diff.Add(@{path=$f.path;sdk_sha256=$f.sha256;formal_sha256=$definition.source_raw_sha256[$f.path]})}
}else{$sdkOnly.Add($f.path)}}
A ($diff.Count -eq 1 -and $diff[0].path -ceq 'docs/M1_SOFTWARE_USER_GUIDE.md' -and $sdkHashes['v0_2/tests/tools/m1_engine_v4/engine.py'] -ceq $definition.candidate_sha256) 'SDK_FORMAL_RUNTIME_CONFLICT'
A (-not(Test-Path -LiteralPath $OutputDirectory)) 'NEW_DELIVERY_OUTPUT_REQUIRED'
New-Item -ItemType Directory -Path $OutputDirectory|Out-Null
$payload=Join-Path $OutputDirectory 'M1_OFFLINE_DELIVERY_RC1';New-Item -ItemType Directory -Path $payload|Out-Null
$sources=[ordered]@{'README_FIRST.zh-CN.md'=(Join-Path $PSScriptRoot 'README_FIRST.zh-CN.md');'source-sdk.zip'=$sdkPath;'formal/EXECUTABLE_FREEZE_MANIFEST.json'=$definitionPath}
foreach($name in @('M1_SOFTWARE_USER_GUIDE.md','V02_PHYSICS_PARAMETER_REFERENCE.md','LEGACY_SCENARIO_PARAMETER_REFERENCE.md','parameter_reference_coverage.json','M1_C3_C_V5_FORMAL_RESULT.md')){$sources['docs/'+$name]=Join-Path $repo ('docs/'+$name)}
foreach($b in $definition.registration_paths.GetEnumerator()){$sources['formal/'+[IO.Path]::GetFileName($b.Value)]=Join-Path $repo $b.Value}
foreach($name in @('user_freeze_approval.json','formal_execution_authorization.json','formal_run_registration.json')){$sources['formal/'+$name]=Join-Path $repo ('artifacts/m1-c3c-v5-authorization/'+$name)}
foreach($f in (Get-ChildItem -LiteralPath $resultRoot -Recurse -File)){$name=$f.FullName.Substring($resultRoot.Length+1).Replace('\','/');$sources['evidence/'+$name]=$f.FullName}
foreach($name in @('M1_SDK_STREAMING_VALIDATION.md','M1_SDK_STREAMING_READBACK.json')){$sources['installation/'+$name]=Join-Path $repo ('docs/'+$name)}
$files=[Collections.Generic.List[object]]::new()
foreach($b in $sources.GetEnumerator()){
    $target=Join-Path $payload $b.Key;New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force|Out-Null
    Copy-Item -LiteralPath $b.Value -Destination $target
    $sha=Get-DeliveryFileSha $target;A ($sha -ceq (Get-DeliveryFileSha $b.Value)) 'COPY_DRIFT'
    $files.Add([ordered]@{path=$b.Key;bytes=(Get-Item -LiteralPath $target).Length;sha256=$sha})
}
$manifest=[ordered]@{schema='m1-offline-delivery-rc1-v1';status='PREPARED_FOR_USER_DELIVERY_REVIEW';software_scope='OFFLINE_SOFTWARE_ONLY_NOT_ORIGINAL_FULL_M1_SCOPE';formal_scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN';formal_gate='C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS';formal_run_id=38833878662;formal_execution_source_commit='9ad4b9d1fdab261db9be09b91f261a927d529970';formal_candidate_sha256=$definition.candidate_sha256;formal_proposal_raw_sha256=(Get-DeliveryFileSha $definitionPath);sdk_zip_sha256=$sdkSha;sdk_source_commit=$sdkManifest.source_commit;sdk_install_development_run=38493762797;sdk_CLI_formally_qualified=$false;builder_raw_sha256=(Get-DeliveryFileSha $PSCommandPath);sdk_formal_byte_crossbinding=@{shared_paths=$shared;identical_paths=$same;differences=@($diff.ToArray());sdk_only_paths=@($sdkOnly.ToArray());interpretation='One preserved documentation snapshot difference; no runtime conflict. SDK-only CLI remains development-validated, not formally qualified.'};permissions=@{distribution_user_approved=$false;production=$false;hardware_control=$false;phase6=$false;new_formal_execution=$false};limitations=@{original_startup='49/50';versioned_compatibility='PASS';SEM02_five_strict_P1_B_C='INCOMPLETE';PF06_original='INCOMPLETE';PF06_supplement='FORMALLY_VALIDATED_UNDER_SEPARATELY_APPROVED_REGISTRATION';arbitrary_POST_OS_crash_powerloss_atomicity='NOT_PROVEN';T09='IMPLEMENTATION_HOLD';full_P_history_available=$false;hardware='CALIBRATION_REQUIRED'};files=@($files.ToArray()|Sort-Object path)}
$manifestPath=Join-Path $payload 'RELEASE_MANIFEST.json';[IO.File]::WriteAllText($manifestPath,(ConvertTo-C3DeliveryCanonical $manifest)+"`n",[Text.UTF8Encoding]::new($false))
$archivePath=Join-Path $OutputDirectory 'M1_OFFLINE_DELIVERY_RC1.zip';$archive=[IO.Compression.ZipFile]::Open($archivePath,[IO.Compression.ZipArchiveMode]::Create)
try{foreach($file in (Get-ChildItem -LiteralPath $payload -Recurse -File|Sort-Object FullName)){
    $name=$file.FullName.Substring($payload.Length+1).Replace('\','/');$entry=$archive.CreateEntry($name,[IO.Compression.CompressionLevel]::Optimal);$entry.LastWriteTime=[DateTimeOffset]::new(1980,1,1,0,0,0,[TimeSpan]::Zero)
    $input=[IO.File]::OpenRead($file.FullName);$output=$entry.Open();try{$input.CopyTo($output)}finally{$input.Dispose();$output.Dispose()}
}}finally{$archive.Dispose()}
# Verify actual zipped bytes, not only the source staging directory.
$archive=[IO.Compression.ZipFile]::OpenRead($archivePath);$hasher=[Security.Cryptography.SHA256]::Create()
try{A ($archive.Entries.Count -eq $files.Count+1) 'DELIVERY_ZIP_COUNT';foreach($e in $archive.Entries){$s=$e.Open();try{$sha=[Convert]::ToHexString($hasher.ComputeHash($s)).ToLowerInvariant()}finally{$s.Dispose()};A ($sha -ceq (Get-DeliveryFileSha (Join-Path $payload $e.FullName))) ('DELIVERY_ZIP_BYTES '+$e.FullName)}}finally{$archive.Dispose();$hasher.Dispose()}
VerifySources
$result=[ordered]@{status='PURE_FILE_ASSEMBLY_AND_ARCHIVE_READBACK_PASS';delivery_status=$manifest.status;archive_sha256=(Get-DeliveryFileSha $archivePath);archive_bytes=(Get-Item -LiteralPath $archivePath).Length;release_manifest_sha256=(Get-DeliveryFileSha $manifestPath);payload_files=$files.Count+1;sealed_sdk_unchanged=$true;protected_source_bindings_unchanged=836;shared_source_paths=$shared;identical_shared_paths=$same;source_differences=@($diff.ToArray());candidate_or_model_executed=$false;new_development_or_formal_tests_run=$false;user_distribution_approval_generated=$false}
[IO.File]::WriteAllText((Join-Path $OutputDirectory 'assembly_readback.json'),($result|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Depth 10
