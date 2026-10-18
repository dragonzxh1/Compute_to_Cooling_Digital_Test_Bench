param([Parameter(Mandatory)][string]$Parent,[Parameter(Mandatory)][ValidateSet('Review','Delivery')][string]$Mode)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-inverse-sizing-v1'
function Send($endpoint,$body,$method='POST'){
 $s=($body|ConvertTo-Json -Depth 50 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GITHUB_API '+$endpoint)};return $s|ConvertFrom-Json
}
$head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $head.object.sha -cne $Parent){throw 'EXACT_PARENT_CHANGED'}
$base=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
if($Mode -ceq 'Review'){
 $paths=@('artifacts/memphis-inverse-sizing-v1-review/file_review.py','artifacts/memphis-inverse-sizing-v1-review/run.ps1','.github/workflows/memphis-inverse-primary-review.yml')
 $message='Independently recompute saved primary Q-H, tank mass and pump heat without model rerun'
}else{
 $delivery=Join-Path $repo 'artifacts/memphis-inverse-sizing-v1-delivery'
 $package=Get-Content (Join-Path $delivery 'package_manifest.json') -Raw|ConvertFrom-Json
 foreach($f in $package.files){if((Get-FileHash (Join-Path $delivery $f.path)).Hash.ToLowerInvariant() -cne $f.raw_sha256){throw 'PACKAGE_DRIFT'}}
 $paths=@(Get-ChildItem -LiteralPath $delivery -File|Where-Object Name -cne 'delivery_publication_receipt.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('docs/MEMPHIS_INVERSE_SIZING_V1_DELIVERY.md')+@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object Name -match '\.ps1$|^BUILD.*\.md$'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})
 $message='Deliver Memphis inverse equipment limits, actual comparisons and independently verified evidence [skip ci]'
}
$entries=@()
foreach($path in $paths|Sort-Object -Unique){
 if($path -notmatch '^(artifacts/memphis-inverse-sizing-v1(-delivery|-review)?/|docs/MEMPHIS_INVERSE_SIZING_V1_DELIVERY.md$|\.github/workflows/memphis-inverse-primary-review.yml$)'){throw 'PUBLICATION_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path));$blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$sha=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($blob.sha -cne $sha){throw 'REMOTE_BLOB_IDENTITY'};$entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message=$message;tree=$tree.sha;parents=@($Parent)}
$diff=gh api ($api+'/compare/'+$Parent+'...'+$commit.sha)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'DIFF_UNAVAILABLE'}
foreach($f in $diff.files){if($f.filename -notin $paths -or $f.status -notin @('added','modified')){throw ('UNAUTHORIZED_DIFF '+$f.filename)}}
$ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($ref.object.sha -cne $commit.sha){throw 'REF_READBACK'}
$remote=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($remote.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw 'TREE_READBACK'}}
$receipt=@{mode=$Mode;commit=$commit.sha;parent=$Parent;branch=$branch;model_execution='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb';model_source_changed=$false;files=$entries;formal=$false;procurement=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('publication_'+$Mode+'.json')),($receipt|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
if($Mode -ceq 'Delivery'){
 [IO.File]::WriteAllText((Join-Path $delivery 'delivery_publication_receipt.json'),($receipt|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
 Copy-Item (Join-Path $delivery 'delivery_publication_receipt.json') 'D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run39136524640/delivery/delivery_publication_receipt.json'
}
$receipt|Select-Object mode,commit,parent,branch,model_execution|ConvertTo-Json
