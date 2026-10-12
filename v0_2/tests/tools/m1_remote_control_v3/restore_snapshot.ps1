# Pure file hydration: no Python, native executor or model is started here.
function Restore-M1Snapshot {
    param([Parameter(Mandatory)][string]$Repo,
          [Parameter(Mandatory)][string]$ExpectedManifestSha256,
          [string]$Destination)
    $ErrorActionPreference='Stop'
    $sourceRoot=(Resolve-Path -LiteralPath $Repo).Path
    if(-not $Destination){$Destination=$sourceRoot}
    $destinationRoot=(Resolve-Path -LiteralPath $Destination).Path
    $manifestPath=Join-Path $sourceRoot 'v0_2/tests/tools/m1_remote_control_v3/execution_manifest.json'
    if($ExpectedManifestSha256 -notmatch '^[a-f0-9]{64}$' -or
       (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifestSha256){throw 'REMOTE_EXECUTION_MANIFEST_DRIFT'}
    $manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
    foreach($binding in $manifest.remote_source_raw_hashes.PSObject.Properties){
        if((Get-FileHash -LiteralPath (Join-Path $sourceRoot $binding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $binding.Value){throw 'REMOTE_ADAPTER_SOURCE_DRIFT'}
    }
    $bundle=Join-Path $sourceRoot $manifest.bundle_path
    if((Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash.ToLowerInvariant() -cne $manifest.bundle_raw_sha256){throw 'SOURCE_BUNDLE_DRIFT'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[IO.Compression.ZipFile]::OpenRead($bundle)
    try {
        $names=@($archive.Entries|ForEach-Object FullName)
        $expectedNames=@($manifest.bundle_entry_raw_hashes.PSObject.Properties.Name)
        if(@(Compare-Object ($names|Sort-Object) ($expectedNames|Sort-Object)).Count -or
           @($names|Select-Object -Unique).Count -ne $names.Count){throw 'BUNDLE_ENTRY_INVENTORY_MISMATCH'}
        $targets=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
        # Check ALL paths and entry bytes before restoring any file.
        foreach($entry in $archive.Entries){
            if($entry.FullName -match '(^[/\\]|:|(^|[/\\])\.\.([/\\]|$))'){throw 'BUNDLE_PATH_ESCAPE'}
            $target=[IO.Path]::GetFullPath((Join-Path $destinationRoot $entry.FullName))
            if(-not $target.StartsWith($destinationRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or $targets.ContainsKey($target)){throw 'BUNDLE_PATH_ESCAPE_OR_ALIAS'}
            $cursor=$target
            while($cursor.Length -ge $destinationRoot.Length){
                if(Test-Path -LiteralPath $cursor){
                    if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'BUNDLE_REPARSE_TARGET_DENIED'}
                }
                $cursor=Split-Path -Parent $cursor
            }
            $stream=$entry.Open(); $sha=[Security.Cryptography.SHA256]::Create()
            try {$hash=[BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
            finally {$stream.Dispose();$sha.Dispose()}
            if($hash -cne $manifest.bundle_entry_raw_hashes.PSObject.Properties[$entry.FullName].Value){throw 'BUNDLE_ENTRY_SOURCE_DRIFT'}
            $targets.Add($target,$entry.FullName)
        }
        foreach($entry in $archive.Entries){
            $target=[IO.Path]::GetFullPath((Join-Path $destinationRoot $entry.FullName))
            New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$true)
        }
    } finally {$archive.Dispose()}
    foreach($binding in $manifest.bundle_entry_raw_hashes.PSObject.Properties){
        if((Get-FileHash -LiteralPath (Join-Path $destinationRoot $binding.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $binding.Value){throw 'RESTORED_SOURCE_DRIFT'}
    }
    Write-Host ('SOURCE_SNAPSHOT_RESTORED_AND_VERIFIED entries='+$names.Count+' manifest='+$ExpectedManifestSha256)
    return $names.Count
}
