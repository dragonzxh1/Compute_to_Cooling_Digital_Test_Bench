# File-only regression. Never starts Python, native helpers or model behavior.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../../..')).Path
. (Join-Path $PSScriptRoot 'restore_snapshot.ps1')
$manifestPath=Join-Path $PSScriptRoot 'execution_manifest.json'
$manifestSha=(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$root=Join-Path $repo ('artifacts/snapshot-file-tests/'+[Guid]::NewGuid().ToString('N'))
$destination=Join-Path $root 'restored'
New-Item -ItemType Directory -Path $destination -Force|Out-Null
$count=Restore-M1Snapshot -Repo $repo -ExpectedManifestSha256 $manifestSha -Destination $destination
if($count -ne 601 -or -not(Test-Path -LiteralPath (Join-Path $destination 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json'))){throw 'MISSING_PLAN_INPUT_REGRESSION'}
$again=Restore-M1Snapshot -Repo $repo -ExpectedManifestSha256 $manifestSha -Destination $destination
if($again -ne $count){throw 'HYDRATION_REPEAT_MISMATCH'}
$empty=Join-Path $root 'denied'
New-Item -ItemType Directory -Path $empty|Out-Null
$caught=$false
try {$null=Restore-M1Snapshot -Repo $repo -ExpectedManifestSha256 ('0'*64) -Destination $empty}
catch {if($_.Exception.Message -cne 'REMOTE_EXECUTION_MANIFEST_DRIFT'){throw};$caught=$true}
if(-not $caught -or @(Get-ChildItem -LiteralPath $empty -Recurse -File).Count){throw 'MANIFEST_GUARD_NOT_FAIL_CLOSED'}
function Assert-DeniedArchive([string]$Case,[string]$Entry,[bool]$BadHash,[bool]$BadInventory,[string]$ExpectedError){
    $source=Join-Path $root $Case
    $dir=Join-Path $source 'v0_2/tests/tools/m1_remote_control_v3'
    New-Item -ItemType Directory -Path $dir -Force|Out-Null
    $zip=Join-Path $source 'fixture.zip'
    $archive=[IO.Compression.ZipFile]::Open($zip,[IO.Compression.ZipArchiveMode]::Create)
    try {
        $item=$archive.CreateEntry($Entry);$stream=$item.Open()
        try {$bytes=[Text.Encoding]::UTF8.GetBytes('inert fixture');$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    } finally {$archive.Dispose()}
    $sha=[Security.Cryptography.SHA256]::Create()
    try {$entryHash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
    $entries=[ordered]@{}
    $entries[$Entry]=if($BadHash){'0'*64}else{$entryHash}
    if($BadInventory){$entries['missing.txt']=$entryHash}
    $synthetic=@{bundle_path='fixture.zip';bundle_raw_sha256=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant();bundle_entry_raw_hashes=$entries;remote_source_raw_hashes=@{}}
    $syntheticPath=Join-Path $dir 'execution_manifest.json'
    [IO.File]::WriteAllText($syntheticPath,($synthetic|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
    $hash=(Get-FileHash -LiteralPath $syntheticPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $caught=$false
    try {$null=Restore-M1Snapshot -Repo $source -ExpectedManifestSha256 $hash -Destination $empty}
    catch {if($_.Exception.Message -cne $ExpectedError){throw};$caught=$true}
    if(-not $caught -or @(Get-ChildItem -LiteralPath $empty -Recurse -File).Count){throw 'ARCHIVE_GUARD_NOT_FAIL_CLOSED'}
}
Assert-DeniedArchive 'bad-entry' 'input.txt' $true $false 'BUNDLE_ENTRY_SOURCE_DRIFT'
Assert-DeniedArchive 'bad-inventory' 'input.txt' $false $true 'BUNDLE_ENTRY_INVENTORY_MISMATCH'
Assert-DeniedArchive 'escape' '../outside.txt' $false $false 'BUNDLE_PATH_ESCAPE'
Write-Host ('SNAPSHOT_FILE_REGRESSION_PASS checks=6 entries='+$count+' evidence='+$root)
