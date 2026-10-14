# Pure source packaging. Never invokes Python/native/model on this workstation.
param([Parameter(Mandatory)][string]$Repo,[Parameter(Mandatory)][string]$Output,
      [Parameter(Mandatory)][string]$SourceCommit,[Parameter(Mandatory)][string]$CampaignManifestSha256)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $Repo).Path
$destination=[IO.Path]::GetFullPath($Output)
if($SourceCommit -notmatch '^[a-f0-9]{40}$' -or (git -C $root rev-parse HEAD) -cne $SourceCommit){throw 'DELIVERY_SOURCE_IDENTITY'}
if(Test-Path -LiteralPath $destination){throw 'FRESH_DELIVERY_DIRECTORY_REQUIRED'}
$manifestPath=Join-Path $root 'v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
if((Get-FileHash $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $CampaignManifestSha256){throw 'DELIVERY_CONTROL_IDENTITY'}
$manifest=Get-Content $manifestPath -Raw|ConvertFrom-Json
$bindings=[ordered]@{}
foreach($p in $manifest.bundle_entry_raw_hashes.PSObject.Properties){$bindings[$p.Name]=$p.Value}
foreach($p in $manifest.remote_source_raw_hashes.PSObject.Properties){$bindings[$p.Name]=$p.Value}
foreach($relative in @('LICENSE','docs/M1_SOFTWARE_USER_GUIDE.md','docs/LEGACY_SCENARIO_PARAMETER_REFERENCE.md','docs/V02_PHYSICS_PARAMETER_REFERENCE.md','docs/parameter_reference_coverage.json')){
    $bindings[$relative]=(Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
}
New-Item -ItemType Directory -Path $destination|Out-Null
$files=@()
$bundle=Join-Path $root $manifest.bundle_path
if((Get-FileHash $bundle -Algorithm SHA256).Hash.ToLowerInvariant() -cne $manifest.bundle_raw_sha256){throw 'PACKAGE_FROZEN_BUNDLE_DRIFT'}
$archive=[IO.Compression.ZipFile]::OpenRead($bundle)
try {
foreach($p in $bindings.GetEnumerator()){
    $source=[IO.Path]::GetFullPath((Join-Path $root $p.Key));$target=[IO.Path]::GetFullPath((Join-Path $destination $p.Key))
    if(-not $source.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or -not $target.StartsWith($destination+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'PACKAGE_PATH_ESCAPE'}
    New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null
    # Frozen dependencies come from the exact original archive, not an assumed
    # hydrated worktree. Current driver/workflow/docs still use actual source.
    $member=$archive.GetEntry($p.Key)
    $runtime=@($manifest.remote_source_raw_hashes.PSObject.Properties.Name) -ccontains $p.Key
    if($null -ne $member -and -not $runtime){
        $stream=$member.Open();$hasher=[Security.Cryptography.SHA256]::Create()
        try{$hash=[Convert]::ToHexString($hasher.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose();$hasher.Dispose()}
        if($hash -cne $p.Value){throw ('PACKAGE_BUNDLE_MEMBER_DRIFT '+$p.Key)}
        [IO.Compression.ZipFileExtensions]::ExtractToFile($member,$target,$false)
    }else{
        if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -cne $p.Value){throw ('PACKAGE_SOURCE_DRIFT '+$p.Key)}
        Copy-Item -LiteralPath $source -Destination $target
    }
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -cne $p.Value){throw 'PACKAGE_COPIED_BYTE_DRIFT'}
    $files+=@{path=$p.Key;bytes=(Get-Item -LiteralPath $target).Length;sha256=$p.Value}
}
}finally{$archive.Dispose()}
$cli=Join-Path $PSScriptRoot 'sdk_cli.py';$target=Join-Path $destination 'sdk_cli.py';Copy-Item -LiteralPath $cli -Destination $target
$files+=@{path='sdk_cli.py';bytes=(Get-Item $target).Length;sha256=(Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText((Join-Path $destination 'README-SDK.md'),@'
# C2C-DTB offline V4 source SDK
Use a separate stable Python3.11 environment; install the delivered
v0_2/tests/tools/c3b_v14_1/requirements-development.lock.
Run `python sdk_cli.py --describe --verify` to inspect parameters without models.
On an approved stable execution host, use
`python sdk_cli.py --run --input-index 15 --rows 3` for a small offline example.
Complete traces and immutable completed records are retained under artifacts/m1-autonomous-development in this SDK directory. This is not formal qualification or hardware control.
The known hard-hanging HIPPO workstation is refused for model execution.
See docs/M1_SOFTWARE_USER_GUIDE.md and docs/V02_PHYSICS_PARAMETER_REFERENCE.md.
Do not modify frozen parameters/expectations merely to get PASS.
'@,[Text.UTF8Encoding]::new($false))
$readme=Join-Path $destination 'README-SDK.md'
$files+=@{path='README-SDK.md';bytes=(Get-Item $readme).Length;sha256=(Get-FileHash $readme -Algorithm SHA256).Hash.ToLowerInvariant()}
$delivery=[ordered]@{schema='m1-v4-streaming-source-sdk-v3';status='DEVELOPMENT_DELIVERY_CANDIDATE_NOT_FORMAL_FREEZE';source_commit=$SourceCommit;
    campaign_control_sha256=$CampaignManifestSha256;files=$files;manifest_authenticity_requires_trusted_external_zip_sha256=$true;
    reference_parent_unchanged=$true;production=$false;hardware='CALIBRATION_REQUIRED';phase6=$false}
$path=Join-Path $destination 'DELIVERY_MANIFEST.json'
[IO.File]::WriteAllText($path,($delivery|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$zip=$destination+'.zip';if(Test-Path -LiteralPath $zip){throw 'DELIVERY_ZIP_ALREADY_EXISTS'}
[IO.Compression.ZipFile]::CreateFromDirectory($destination,$zip,[IO.Compression.CompressionLevel]::Optimal,$false)
[pscustomobject]@{status='SOURCE_SDK_PACKAGED_NOT_INSTALLATION_VALIDATED';files=$files.Count;zip=$zip;zip_sha256=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant();manifest_raw_sha256=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()}|ConvertTo-Json
