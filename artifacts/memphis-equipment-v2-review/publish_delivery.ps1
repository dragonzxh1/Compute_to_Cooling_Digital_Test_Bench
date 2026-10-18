param([Parameter(Mandatory)][string]$Root,[string]$Parent='6031e0ef7d32bec0109f328f85ebd5dfef8fe048')
# Documentation/evidence publication only. Never changes workflow or executable inputs.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-equipment-validation-v2'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$delivery=Join-Path ([IO.Path]::GetFullPath($Root)) 'delivery'
$manifest=Get-Content (Join-Path $delivery 'delivery_manifest.json') -Raw|ConvertFrom-Json
if($manifest.source_commit -cne $Parent -or $manifest.run_id -ne 39088951176){throw 'DELIVERY_EXECUTION_IDENTITY'}
foreach($r in $manifest.records){
 if([IO.Path]::GetFileName($r.file) -cne $r.file){throw 'DELIVERY_PATH_ESCAPE'}
 $f=Join-Path $delivery $r.file
 if((Get-Item -LiteralPath $f).Length -ne $r.bytes -or (Get-FileHash -LiteralPath $f).Hash.ToLowerInvariant() -cne $r.sha256){throw ('DELIVERY_HASH_DRIFT '+$r.file)}
}
function Send([string]$endpoint,$body,[string]$method='POST'){
 $answer=($body|ConvertTo-Json -Depth 70 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('API_FAILURE '+$endpoint)};return $answer|ConvertFrom-Json
}
$current=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $current.object.sha -cne $Parent){throw 'PUBLICATION_PARENT_CHANGED'}
$parentObj=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'PARENT_UNAVAILABLE'}
$uploads=@()
foreach($f in Get-ChildItem -LiteralPath $delivery -File){$uploads+=@{local=$f.FullName;path=('artifacts/memphis-equipment-v2-delivery/'+$f.Name)}}
$reviewNames=@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object Name -notin @('publish.ps1','final_publication_receipt.json')|ForEach-Object Name)
foreach($name in $reviewNames){$uploads+=@{local=(Join-Path $PSScriptRoot $name);path=('artifacts/memphis-equipment-v2-review/'+$name)}}
$uploads+=@{local=(Join-Path $repo 'docs/MEMPHIS_EQUIPMENT_V2_DELIVERY.md');path='docs/MEMPHIS_EQUIPMENT_V2_DELIVERY.md'}
$entries=@()
foreach($f in $uploads|Sort-Object path){
 if($f.path -notmatch '^(artifacts/memphis-equipment-v2-(delivery|review)/|docs/MEMPHIS_EQUIPMENT_V2_DELIVERY\.md$)'){throw 'PUBLICATION_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes($f.local)
 $blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0))
 $expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($blob.sha -cne $expected){throw ('BLOB_DRIFT '+$f.path)}
 $entries+=@{path=$f.path;mode='100644';type='blob';sha=$blob.sha}
 Write-Host ('EXACT_DELIVERY_BLOB '+$f.path)
}
$tree=Send 'git/trees' @{base_tree=$parentObj.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Deliver independently verified Memphis V2 results and engineering limitations [skip ci]';tree=$tree.sha;parents=@($Parent)}
$compare=gh api ($api+'/compare/'+$Parent+'...'+$commit.sha)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $compare.files.Count -ne $entries.Count){throw 'DELIVERY_DIFF_COUNT'}
foreach($f in $compare.files){if($f.filename -notin $entries.path){throw ('UNEXPECTED_SOURCE_CHANGE '+$f.filename)}}
$current=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $current.object.sha -cne $Parent){throw 'PUBLICATION_PARENT_CHANGED'}
$sourceRef='codex/memphis-equipment-v2-source-6031e0e'
$known=@(gh api ($api+'/git/matching-refs/heads/'+$sourceRef)|ConvertFrom-Json)
if($LASTEXITCODE -ne 0){throw 'SOURCE_REF_QUERY_FAILED'}
if($known.Count -eq 0){$null=Send 'git/refs' @{ref=('refs/heads/'+$sourceRef);sha=$Parent}}
elseif($known.Count -ne 1 -or $known[0].ref -cne 'refs/heads/'+$sourceRef -or $known[0].object.sha -cne $Parent){throw 'SOURCE_REFERENCE_CONFLICT'}
$ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($ref.object.sha -cne $commit.sha){throw 'REF_MISMATCH'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw ('READBACK_DRIFT '+$e.path)}}
$receipt=[ordered]@{delivery_commit=$commit.sha;execution_commit=$Parent;source_ref=$sourceRef;run_id=$manifest.run_id;branch=$branch;delivery_manifest_raw_sha256=(Get-FileHash (Join-Path $delivery 'delivery_manifest.json')).Hash.ToLowerInvariant();files=$entries;method='GH_CLI_EXACT_BLOBS_REPORTS_AND_FILE_REVIEW_TOOLS_ONLY';model_executable_changed=$false;formal=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'final_publication_receipt.json'),($receipt|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
$receipt|Select-Object delivery_commit,execution_commit,delivery_manifest_raw_sha256|ConvertTo-Json
