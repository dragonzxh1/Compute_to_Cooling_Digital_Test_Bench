# File-only retrieval/readback of official artifacts. No models or native tests.
param([Parameter(Mandatory)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path -LiteralPath $EvidenceRoot).Path
$inventory=Get-Content (Join-Path $root 'github-artifact-inventory.json') -Raw|ConvertFrom-Json
if($inventory.run_id -ne 38423165745 -or $inventory.source_commit -cne '717a98dd89ece8d3b6944a80727b32f20a311b8b'){throw 'COLLECTION_EXECUTION_IDENTITY'}
$archives=Join-Path $root 'native-archives'
$union=Join-Path $root 'native-union'
New-Item -ItemType Directory -Path $archives,$union -Force|Out-Null
$taskToken=gh auth token
foreach($item in $inventory.artifacts){
    if($item.name -notmatch '^(ref-\d+|reference-gate|select-\d+|split-(u|\d+)|prefix-\d+)$'){continue}
    $zip=Join-Path $archives ($item.name+'.zip')
    if(-not(Test-Path -LiteralPath $zip)){
        curl.exe --fail --location --silent --show-error --connect-timeout 30 --max-time 900 -H "Authorization: Bearer $taskToken" -H 'Accept: application/vnd.github+json' -o $zip ('https://api.github.com/repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/artifacts/'+$item.id+'/zip')
        if($LASTEXITCODE -ne 0){throw ('OFFICIAL_NATIVE_DOWNLOAD_FAILED '+$item.name)}
    }
    $digest=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    if($digest -cne $item.digest.Substring(7) -or (Get-Item $zip).Length -ne $item.size_in_bytes){throw ('OFFICIAL_NATIVE_ZIP_DRIFT '+$item.name)}
    $archive=[IO.Compression.ZipFile]::OpenRead($zip)
    $count=0
    try{foreach($entry in $archive.Entries){
        if(-not $entry.FullName.StartsWith('liquid-recovery-v1/') -or $entry.FullName.EndsWith('/')){continue}
        $target=[IO.Path]::GetFullPath((Join-Path $union $entry.FullName))
        if(-not $target.StartsWith($union+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'NATIVE_ARCHIVE_PATH_ESCAPE'}
        New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null
        if(Test-Path -LiteralPath $target){
            $stream=$entry.Open();$sha=[Security.Cryptography.SHA256]::Create()
            try{$memberHash=[Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()}finally{$stream.Dispose();$sha.Dispose()}
            if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -cne $memberHash){throw 'NATIVE_UNION_COLLISION'}
        }else{[IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)}
        $count++
    }}finally{$archive.Dispose()}
    if($count -eq 0){throw ('NATIVE_METADATA_NOT_FOUND '+$item.name)}
    Write-Output ('OFFICIAL_NATIVE_COLLECTION_PASS '+$item.name+' files='+$count+' sha256='+$digest)
}
'NATIVE_FILE_COLLECTION_FINISHED_NO_MODEL_EXECUTION'
