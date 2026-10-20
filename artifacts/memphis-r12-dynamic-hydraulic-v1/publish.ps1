param([string]$Parent='9af34df6fcb97d35a3dd2523277ffce09e6fea56',[switch]$Update)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-r12-dynamic-hydraulic-v1'
$prefix='v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1'
function Send($ep,$value,$method='POST'){
 $raw=($value|ConvertTo-Json -Compress -Depth 70)|gh api ($api+'/'+$ep) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GH_API '+$ep)}
 return $raw|ConvertFrom-Json
}
$base=gh api ($api+'/git/commits/'+$Parent)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'BASE_READ_FAILED'}
$files=@(Get-ChildItem -LiteralPath (Join-Path $taskRepo $prefix) -File -Recurse | ForEach-Object{[IO.Path]::GetRelativePath($taskRepo,$_.FullName).Replace('\','/')})
$pidPrefix='v0_2/tests/tools/memphis_r12_pid_revision_v1'
$files+=@(Get-ChildItem -LiteralPath (Join-Path $taskRepo $pidPrefix) -File -Recurse|Where-Object {$_.FullName -notmatch '[\\/]diagram[\\/]'}|ForEach-Object{[IO.Path]::GetRelativePath($taskRepo,$_.FullName).Replace('\','/')})
$files+=@('.github/workflows/memphis-r12-dynamic-hydraulic-v1.yml','.github/workflows/ci.yml')
$entries=@()
foreach($path in $files|Sort-Object){
 if($path -notmatch '^v0_2/tests/tools/memphis_r12_(dynamic_hydraulic_v1|pid_revision_v1)/' -and $path -notin @('.github/workflows/memphis-r12-dynamic-hydraulic-v1.yml','.github/workflows/ci.yml')){throw 'PUBLICATION_SCOPE'}
 $local=if($path -ceq '.github/workflows/ci.yml'){$prefix+'/infra/ci-branch-only.yml'}else{$path}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $taskRepo $local))
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0))
 $expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($head+$bytes))).ToLowerInvariant()
 $blob=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 if($blob.sha -cne $expected){throw 'BLOB_IDENTITY'}
 $entries+=@{path=$path;mode='100644';type='blob';sha=$expected}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{message='Add JSON-bound one-six-rack R12 short dynamic development adapter';tree=$tree.sha;parents=@($Parent)}
$diff=gh api ($api+'/compare/'+$Parent+'...'+$commit.sha)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'COMPARE_READ_FAILED'}
foreach($f in $diff.files){if($f.filename -notin $files -or $f.status -notin @('added','modified')){throw ('UNAUTHORIZED_CHANGE '+$f.filename)}}
if($Update){
 $head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
 if($head.object.sha -cne $Parent){throw 'BRANCH_MOVED'}
 $r=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
}else{$r=Send 'git/refs' @{ref='refs/heads/'+$branch;sha=$commit.sha}}
if($r.object.sha -cne $commit.sha){throw 'REF_IDENTITY'}
$readback=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json
if($readback.truncated){throw 'TREE_TRUNCATED'}
foreach($e in $entries){if(-not($readback.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw 'TREE_IDENTITY'}}
$out=Join-Path $PSScriptRoot ('source-'+$commit.sha.Substring(0,7))
if(Test-Path -LiteralPath $out){throw 'SNAPSHOT_EXISTS'}
New-Item -ItemType Directory -Path $out|Out-Null
foreach($p in $files){
 $local=if($p -ceq '.github/workflows/ci.yml'){$prefix+'/infra/ci-branch-only.yml'}else{$p}
 $dest=Join-Path $out $p;New-Item -ItemType Directory -Path (Split-Path $dest) -Force|Out-Null
 Copy-Item -LiteralPath (Join-Path $taskRepo $local) -Destination $dest
}
[IO.Compression.ZipFile]::CreateFromDirectory($out,($out+'.zip'))
$receipt=@{commit=$commit.sha;parent=$Parent;branch=$branch;files=$entries;diff_files=$diff.files;
 manifest_sha256=(Get-FileHash (Join-Path $taskRepo ($prefix+'/source_manifest.json'))).Hash.ToLowerInvariant();
 source_zip_sha256=(Get-FileHash ($out+'.zip')).Hash.ToLowerInvariant();
 scope='SHORT_SIX_RACK_DYNAMIC_RESEARCH';long_simulation=$false;formal=$false;hardware=$false;phase6=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('publication_'+$commit.sha.Substring(0,7)+'.json')),($receipt|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
$receipt|Select-Object commit,parent,branch,manifest_sha256,source_zip_sha256|ConvertTo-Json
