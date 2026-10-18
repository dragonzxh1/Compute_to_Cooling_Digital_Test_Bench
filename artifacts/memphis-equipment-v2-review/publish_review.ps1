$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$parent='6031e0ef7d32bec0109f328f85ebd5dfef8fe048';$branch='codex/memphis-equipment-v2-evidence-review'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
function Send([string]$endpoint,$body){$r=($body|ConvertTo-Json -Depth 35 -Compress)|gh api ($api+'/'+$endpoint) --method POST --input -;if($LASTEXITCODE -ne 0){throw ('PUBLICATION '+$endpoint)};return $r|ConvertFrom-Json}
$base=gh api ($api+'/git/commits/'+$parent)|ConvertFrom-Json;if($LASTEXITCODE -ne 0){throw 'EXACT_PARENT'}
$paths=@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object Name -ne 'final_publication_receipt.json'|ForEach-Object {[IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/')})+@('.github/workflows/memphis-equipment-v2-evidence-review.yml')
$entries=@()
foreach($path in $paths|Sort-Object){$bytes=[IO.File]::ReadAllBytes((Join-Path $repo $path));$blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)};$header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant();if($blob.sha -cne $expected){throw 'BLOB_DRIFT'};$entries+=@{path=$path;mode='100644';type='blob';sha=$blob.sha}}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Independently review completed Memphis V2 evidence remotely without model execution';tree=$tree.sha;parents=@($parent)}
$ref=Send 'git/refs' @{ref=('refs/heads/'+$branch);sha=$commit.sha}
if($ref.object.sha -cne $commit.sha){throw 'REF_MISMATCH'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'review_publication_receipt.json'),(@{review_commit=$commit.sha;model_commit=$parent;branch=$branch;files=$entries;model_source_changed=$false}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$commit.sha
