param([Parameter(Mandatory)][string]$Parent,[Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$ExecutionCommit)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-failure-closure-v1'
function Send($endpoint,$body,$method='POST'){
 $s=($body|ConvertTo-Json -Depth 60 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GITHUB_API '+$endpoint)};return $s|ConvertFrom-Json
}
$head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $head.object.sha -cne $Parent){throw 'EXACT_PARENT_CHANGED'}
$base=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
$delivery=Join-Path $repo 'artifacts/memphis-failure-closure-v1-delivery'
$package=Get-Content (Join-Path $delivery 'package_manifest.json') -Raw|ConvertFrom-Json
if($package.execution_commit -cne $ExecutionCommit -or $package.run -ne [long]$RunId){throw 'DELIVERY_EXECUTION_IDENTITY'}
foreach($f in $package.files){if((Get-FileHash (Join-Path $delivery $f.path)).Hash.ToLowerInvariant() -cne $f.raw_sha256){throw 'PACKAGE_DRIFT'}}
$paths=@(Get-ChildItem $delivery -File|Where-Object Name -cne 'delivery_publication_receipt.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('docs/MEMPHIS_FAILURE_CLOSURE_V1_DELIVERY.md')+@(Get-ChildItem $PSScriptRoot -File|Where-Object Name -match '\.ps1$|^BUILD.*\.md$'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})
$entries=@();$count=0
foreach($path in $paths|Sort-Object -Unique){
 if($path -notmatch '^(artifacts/memphis-failure-closure-v1(-delivery)?/|docs/MEMPHIS_FAILURE_CLOSURE_V1_DELIVERY.md$)'){throw 'PUBLICATION_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path));$blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$sha=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($blob.sha -cne $sha){throw 'REMOTE_BLOB_IDENTITY'};$entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha};$count++;if($count%10 -eq 0){Write-Host ('Exact delivery blobs '+$count+'/'+$paths.Count)}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Deliver Memphis failure closure, actual engineering comparisons and supplier FAT proposals [skip ci]';tree=$tree.sha;parents=@($Parent)}
$diff=gh api ($api+'/compare/'+$Parent+'...'+$commit.sha)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'DIFF_UNAVAILABLE'}
foreach($f in $diff.files){if($f.filename -notin $paths -or $f.status -notin @('added','modified')){throw ('UNAUTHORIZED_DIFF '+$f.filename)}}
$ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($ref.object.sha -cne $commit.sha){throw 'REF_READBACK'}
$remote=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($remote.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw 'TREE_READBACK'}}
$receipt=@{commit=$commit.sha;parent=$Parent;branch=$branch;execution_commit=$ExecutionCommit;run=[long]$RunId;model_source_changed=$false;files=$entries;package_sha256=(Get-FileHash (Join-Path $delivery 'package_manifest.json')).Hash.ToLowerInvariant();formal=$false;procurement=$false;hardware=$false;phase6=$false}
$utf8=[Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $delivery 'delivery_publication_receipt.json'),($receipt|ConvertTo-Json -Depth 15),$utf8)
Copy-Item (Join-Path $delivery 'delivery_publication_receipt.json') ('D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$RunId+'/delivery/delivery_publication_receipt.json')
$receipt|Select-Object commit,parent,branch,run,execution_commit,package_sha256|ConvertTo-Json
