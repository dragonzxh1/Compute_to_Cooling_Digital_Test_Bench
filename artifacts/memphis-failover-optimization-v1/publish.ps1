param([string]$Parent='4381a3ff2b484a183f3faf635b6c6145cda50336',[switch]$Update)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-failover-optimization-v1'
function Send([string]$endpoint,$body,[string]$method='POST'){
 $answer=($body|ConvertTo-Json -Depth 80 -Compress)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('API_FAILURE '+$endpoint)};return $answer|ConvertFrom-Json
}
$parentObj=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'PARENT_UNAVAILABLE'}
$paths=@(Get-ChildItem -LiteralPath (Join-Path $repo 'v0_2/tests/tools/memphis_failover_optimization_v1') -File -Recurse|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-failover-optimization-v1.yml','.github/workflows/memphis-failover-optimization-v1-runner.yml','artifacts/memphis-failover-optimization-v1/publish.ps1','artifacts/memphis-failover-optimization-v1/BUILD001_STOP.md','.github/workflows/ci.yml')
$entries=@();$count=0
foreach($path in $paths|Sort-Object){
 if($path -notmatch '^(v0_2/tests/tools/memphis_failover_optimization_v1/|\.github/workflows/memphis-failover-optimization-v1|artifacts/memphis-failover-optimization-v1/)' -and $path -cne '.github/workflows/ci.yml'){throw 'PUBLICATION_SCOPE'}
 $local=if($path -ceq '.github/workflows/ci.yml'){'v0_2/tests/tools/memphis_failover_optimization_v1/infra/ci-branch-only.yml'}else{$path}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $local));$blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($blob.sha -cne $expected){throw ('REMOTE_BLOB_DRIFT '+$path)}
 $entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha};$count++;if($count%15 -eq 0){Write-Host ('Exact blobs '+$count+'/'+$paths.Count)}
}
$tree=Send 'git/trees' @{base_tree=$parentObj.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Compare measured Memphis failover strategies and bounded physical sensitivities';tree=$tree.sha;parents=@($Parent)}
if($Update){
 $current=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
 if($LASTEXITCODE -ne 0 -or $current.object.sha -cne $Parent){throw 'REMOTE_BRANCH_PARENT_CHANGED'}
 $ref=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
}else{$ref=Send 'git/refs' @{ref=('refs/heads/'+$branch);sha=$commit.sha}}
if($ref.object.sha -cne $commit.sha){throw 'REMOTE_REF_MISMATCH'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
foreach($e in $entries){if(-not($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw ('TREE_READBACK_FAILED '+$e.path)}}
$record=[ordered]@{commit=$commit.sha;parent=$Parent;branch=$branch;tree=$tree.sha;files=$entries;manifest_raw_sha256=(Get-FileHash (Join-Path $repo 'v0_2/tests/tools/memphis_failover_optimization_v1/source_manifest.json')).Hash.ToLowerInvariant();method='GH_CLI_EXACT_BLOBS_NO_LOCAL_GIT_REPAIR';formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('publication_'+$commit.sha.Substring(0,7)+'.json')),($record|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
[PSCustomObject]$record|Select-Object commit,branch,manifest_raw_sha256|ConvertTo-Json
