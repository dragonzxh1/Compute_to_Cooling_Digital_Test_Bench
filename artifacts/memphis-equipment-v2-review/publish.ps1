param([string]$Parent='77db1f4ef568722357639a0dfd9367bcafe5a1cd',[switch]$Update)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-equipment-validation-v2'
function Send([string]$endpoint,$body,[string]$method='POST'){
 $answer=($body|ConvertTo-Json -Depth 80 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('API_FAILURE '+$endpoint)};return $answer|ConvertFrom-Json
}
$parentObj=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'PARENT_UNAVAILABLE'}
$paths=@(Get-ChildItem -LiteralPath (Join-Path $repo 'v0_2/tests/tools/memphis_equipment_validation_v2') -File -Recurse|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-equipment-v2.yml','.github/workflows/memphis-equipment-v2-runner.yml','artifacts/memphis-equipment-v2-review/publish.ps1')
$entries=@();$count=0
foreach($path in $paths|Sort-Object){
 $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path))
 $blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$sha=[Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes));$expected=[Convert]::ToHexString($sha).ToLowerInvariant()
 if($blob.sha -cne $expected){throw ('REMOTE_BLOB_DRIFT '+$path)}
 $entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha};$count++;if($count%15 -eq 0){Write-Host ('Exact blobs '+$count+'/'+$paths.Count)}
}
$tree=Send 'git/trees' @{base_tree=$parentObj.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Add Memphis equipment validation and physical failover V2 development';tree=$tree.sha;parents=@($Parent)}
if($Update){
 $current=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
 if($LASTEXITCODE -ne 0 -or $current.object.sha -cne $Parent){throw 'REMOTE_BRANCH_PARENT_CHANGED'}
 $ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
}else{$ref=Send 'git/refs' @{ref=('refs/heads/'+$branch);sha=$commit.sha}}
if($ref.object.sha -cne $commit.sha){throw 'REMOTE_REF_MISMATCH'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw ('TREE_READBACK_FAILED '+$e.path)}}
$record=[ordered]@{commit=$commit.sha;parent=$Parent;branch=$branch;tree=$tree.sha;files=$entries;manifest_raw_sha256=(Get-FileHash (Join-Path $repo 'v0_2/tests/tools/memphis_equipment_validation_v2/source_manifest.json')).Hash.ToLowerInvariant();method='GH_CLI_GIT_DATA_API_EXACT_BLOBS_NO_LOCAL_GIT_REPAIR'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('publication_'+$commit.sha.Substring(0,7)+'.json')),($record|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
[PSCustomObject]$record|Select-Object commit,branch,manifest_raw_sha256|ConvertTo-Json
