# Publish this task's already-created commit without local pack/gc. No Git repair.
param([string]$ExpectedCommit='c88677ab5a175e8519052e0b6817fae5b1571e3f',[switch]$UpdateExisting)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $repo
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$expected=$ExpectedCommit
if((git rev-parse HEAD) -cne $expected){throw 'LOCAL_HEAD_CHANGED'}
function Send-Api([string]$endpoint,$body,[string]$method='POST'){
    $json=$body|ConvertTo-Json -Depth 30 -Compress
    $answer=$json | gh api ($api+'/'+$endpoint) --method $method --input -
    if($LASTEXITCODE -ne 0){throw ('GITHUB_API_FAILED '+$endpoint)}
    return ($answer|ConvertFrom-Json)
}
$parent=(git rev-parse HEAD^).Trim()
$p=gh api ($api+'/git/commits/'+$parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'PARENT_UNAVAILABLE'}
$paths=@(git diff-tree --no-commit-id --name-only -r HEAD)
$entries=@();$i=0
foreach($path in $paths){
    $deliveryFiles=@('.gitattributes','run_build1.json','run_build2.json','run_build3.json','download_official.ps1','verify_official.ps1','publish_snapshot.ps1','build_delivery_manifest.ps1','independent_verification.json','delivery_manifest.json','publication_receipt_4093b7d.json','publication_receipt_9a5df03.json','publication_receipt_fe94f1b.json','delivered/consolidated_report.json','delivered/engineering_report.md')|ForEach-Object {'artifacts/memphis-single-rack-v1-review/'+$_}
    if(-not($path.StartsWith('v0_2/tests/tools/memphis_single_rack_v1/') -or $path -in ($deliveryFiles+@('.github/workflows/memphis-rack-v1.yml','.github/workflows/memphis-rack-v1-runner.yml','docs/MEMPHIS_SINGLE_RACK_BASELINE_V1.md','docs/MEMPHIS_SINGLE_RACK_RESULTS_20261017.md','artifacts/memphis-single-rack-v1-review/BUILD1_FAILURE.md','artifacts/memphis-single-rack-v1-review/BUILD2_FAILURE.md')))){throw ('OUT_OF_SCOPE '+$path)}
    $bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path))
    $blob=Send-Api 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
    $expectedBlob=(git hash-object --no-filters -- $path).Trim()
    if($blob.sha -cne $expectedBlob){throw ('REMOTE_BLOB_IDENTITY '+$path)}
    $entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha}
    $i++;if($i%10 -eq 0){Write-Host ('Published exact blobs '+$i+'/'+$paths.Count)}
}
$tree=Send-Api 'git/trees' @{base_tree=$p.tree.sha;tree=$entries}
if($tree.sha -cne (git rev-parse 'HEAD^{tree}').Trim()){throw 'REMOTE_TREE_NOT_LOCAL_TREE'}
$meta=@(git show -s --format='%an%n%ae%n%aI%n%cn%n%ce%n%cI' HEAD)
$message=(git show -s --format='%B' HEAD | Out-String).TrimEnd()
$body=@{message=$message;tree=$tree.sha;parents=@($parent);author=@{name=$meta[0];email=$meta[1];date=$meta[2]};committer=@{name=$meta[3];email=$meta[4];date=$meta[5]}}
$commit=Send-Api 'git/commits' $body
if($commit.sha -cne $expected){
    # Git commit messages conventionally carry a final LF. Require exact SHA,
    # not merely equivalent content, before making an executable branch ref.
    $body.message=$message+"`n"
    $commit=Send-Api 'git/commits' $body
}
if($commit.sha -cne $expected){throw ('REMOTE_COMMIT_NOT_EXACT '+$commit.sha)}
$record=@{local_and_remote_commit=$commit.sha;tree=$tree.sha;parent=$parent;files=$entries;method='GITHUB_CLI_GIT_DATA_API_NO_LOCAL_PACK_OR_REPAIR';local_corrupt_object_retained='67b7fe4c2709aeeb8cd7a68519b853a3a5363d9f'}
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('publication_receipt_'+$expected.Substring(0,7)+'.json')),($record|ConvertTo-Json -Depth 12),$utf8)
if($UpdateExisting){
    $current=gh api ($api+'/git/ref/heads/codex/memphis-single-rack-v1')|ConvertFrom-Json
    if($LASTEXITCODE -ne 0 -or $current.object.sha -cne $parent){throw 'REMOTE_BRANCH_NOT_EXPECTED_PARENT'}
    $ref=Send-Api 'git/refs/heads/codex/memphis-single-rack-v1' @{sha=$commit.sha;force=$false} 'PATCH'
}else{$ref=Send-Api 'git/refs' @{ref='refs/heads/codex/memphis-single-rack-v1';sha=$commit.sha}}
if($ref.object.sha -cne $expected){throw 'REF_IDENTITY'}
Write-Output ('EXACT_REMOTE_BRANCH_CREATED '+$commit.sha)
