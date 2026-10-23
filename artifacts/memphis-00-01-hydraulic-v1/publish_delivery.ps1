param([Parameter(Mandatory)][string]$Delivery)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-00-01-hydraulic-v1'
$parent='274871a94ef13680c508a736ea9635095570cecb';$prefix='artifacts/memphis-00-01-hydraulic-v1'
function Send($endpoint,$value,$method='POST'){
 $r=($value|ConvertTo-Json -Compress -Depth 50)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GH_API '+$endpoint)};$r|ConvertFrom-Json
}
$manifest=Get-Content -LiteralPath (Join-Path $Delivery '16_SOURCE_AND_EVIDENCE_MANIFEST.json') -Raw|ConvertFrom-Json
if($manifest.source_commit -cne $parent){throw 'DELIVERY_EXECUTION_BINDING'}
foreach($r in $manifest.records){
 $p=[IO.Path]::GetFullPath((Join-Path $Delivery $r.path))
 if(-not $p.StartsWith(([IO.Path]::GetFullPath($Delivery)+[IO.Path]::DirectorySeparatorChar))){throw 'PATH_ESCAPE'}
 if((Get-FileHash $p).Hash.ToLowerInvariant() -cne $r.sha256 -or (Get-Item $p).Length -ne $r.bytes){throw ('DELIVERY_HASH '+$r.path)}
}
$head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($head.object.sha -cne $parent){throw 'BRANCH_MOVED_DO_NOT_OVERWRITE'}
$base=gh api ($api+'/git/commits/'+$parent)|ConvertFrom-Json
$files=@{}
foreach($f in Get-ChildItem -LiteralPath $Delivery -File -Recurse){$p=[IO.Path]::GetRelativePath($Delivery,$f.FullName).Replace('\','/');$files[$prefix+'/delivery/'+$p]=$f.FullName}
$files['docs/MEMPHIS_00_01_HYDRAULIC_V1_DELIVERY.md']=Join-Path $Delivery '14_ENGINEERING_REPORT_ZH.md'
foreach($n in @('publish_delivery.ps1','publish.ps1','prepare_build002.ps1')){$files[$prefix+'/'+$n]=Join-Path $PSScriptRoot $n}
$entries=@()
foreach($p in $files.Keys|Sort-Object){
 if(-not $p.StartsWith($prefix+'/') -and $p -cne 'docs/MEMPHIS_00_01_HYDRAULIC_V1_DELIVERY.md'){throw 'DELIVERY_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes($files[$p]);$b=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($b.sha -cne $expected){throw 'BLOB_IDENTITY'}
 $entries+=@{path=$p;sha=$b.sha;type='blob';mode='100644'}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{parents=@($parent);tree=$tree.sha;message='Deliver verified hosted resources and 00/01 reduced hydraulic evidence with retained failures [skip ci]'}
$diff=gh api ($api+'/compare/'+$parent+'...'+$commit.sha)|ConvertFrom-Json
foreach($f in $diff.files){if(-not $files.ContainsKey($f.filename)){throw 'SOURCE_CHANGED_IN_DELIVERY'}}
$r=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($r.object.sha -cne $commit.sha){throw 'REF_IDENTITY'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
if($readback.truncated){throw 'TREE_TRUNCATED'}
foreach($e in $entries){if(-not ($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw 'TREE_READBACK_IDENTITY'}}
$result=@{delivery_commit=$commit.sha;execution_commit=$parent;branch=$branch;files=$entries;model_executed=$false;
 delivery_manifest_sha256=(Get-FileHash (Join-Path $Delivery '16_SOURCE_AND_EVIDENCE_MANIFEST.json')).Hash.ToLowerInvariant();engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'delivery_publication.json'),($result|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
$result|Select-Object delivery_commit,execution_commit,branch,delivery_manifest_sha256|ConvertTo-Json
