$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$parent='a07e5fba7d78f34ab907ce209399068f9c92c760';$branch='codex/memphis-failover-optimization-v1';$sourceRef='codex/memphis-failover-opt-source-a07e5fb'
function Send([string]$endpoint,$body,[string]$method='POST'){
 $r=($body|ConvertTo-Json -Depth 40 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GITHUB_PUBLICATION '+$endpoint)};return $r|ConvertFrom-Json
}
$head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $head.object.sha -cne $parent){throw 'EXACT_PARENT_CHANGED'}
$fixed=Send 'git/refs' @{ref=('refs/heads/'+$sourceRef);sha=$parent}
if($fixed.object.sha -cne $parent){throw 'FIXED_SOURCE_REF_DRIFT'}
$base=gh api ($api+'/git/commits/'+$parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'PARENT_UNAVAILABLE'}
$delivery=Join-Path $repo 'artifacts/memphis-failover-optimization-v1-delivery'
$package=Get-Content -LiteralPath (Join-Path $delivery 'package_manifest.json') -Raw|ConvertFrom-Json
foreach($item in $package.files){if((Get-FileHash -LiteralPath (Join-Path $delivery $item.path)).Hash.ToLowerInvariant() -cne $item.raw_sha256){throw 'DELIVERY_PACKAGE_DRIFT'}}
$paths=@(Get-ChildItem -LiteralPath $delivery -File|Where-Object Name -cne 'delivery_publication_receipt.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('docs/MEMPHIS_FAILOVER_OPTIMIZATION_V1_DELIVERY.md')+@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object Name -in @('verify_official.ps1','delivery_findings.html','annotate_delivery.ps1','prepare_delivery.ps1','publish_delivery.ps1')|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})
$entries=@()
foreach($path in $paths|Sort-Object){
 if($path -notmatch '^(artifacts/memphis-failover-optimization-v1(-delivery)?/|docs/MEMPHIS_FAILOVER_OPTIMIZATION_V1_DELIVERY.md$)'){throw 'DOCS_ONLY_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path));$blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$sha=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($sha -cne $blob.sha){throw ('BLOB_IDENTITY '+$path)}
 $entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Deliver Memphis failover causal comparison, verified evidence and engineering limits [skip ci]';tree=$tree.sha;parents=@($parent)}
$diff=gh api ($api+'/compare/'+$parent+'...'+$commit.sha)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'DIFF_UNAVAILABLE'}
foreach($file in $diff.files){if($file.filename -notin $paths -or $file.status -notin @('added','modified')){throw ('OUT_OF_SCOPE_DIFF '+$file.filename)}}
$ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($ref.object.sha -cne $commit.sha){throw 'DELIVERY_REF_DRIFT'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw ('REMOTE_READBACK '+$e.path)}}
$record=[ordered]@{delivery_commit=$commit.sha;execution_commit=$parent;branch=$branch;fixed_source_ref=$sourceRef;run=39129984525;package_raw_sha256=(Get-FileHash (Join-Path $delivery 'package_manifest.json')).Hash.ToLowerInvariant();files=$entries;candidate_or_model_source_changed=$false;formal=$false;procurement=$false;production=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'delivery_publication_receipt.json'),($record|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Join-Path $delivery 'delivery_publication_receipt.json') -Destination 'D:/Github/c2c-evidence-review/memphis-failover-optimization-v1/run39129984525/delivery/delivery_publication_receipt.json'
[PSCustomObject]$record|Select-Object delivery_commit,execution_commit,branch,fixed_source_ref,package_raw_sha256|ConvertTo-Json
