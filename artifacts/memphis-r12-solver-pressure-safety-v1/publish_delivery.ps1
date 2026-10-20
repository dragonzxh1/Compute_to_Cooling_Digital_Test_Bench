param([Parameter(Mandatory)][string]$Delivery)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-r12-solver-pressure-safety-v1'
$parent='418ccfbe494774f9ebe416f575c3ba0d44939f1c';$prefix='artifacts/memphis-r12-solver-pressure-safety-v1'
function Send($endpoint,$value,$method='POST'){
 $r=($value|ConvertTo-Json -Compress -Depth 50)|gh api ($api+'/'+$endpoint) --method $method --input -
 if($LASTEXITCODE -ne 0){throw ('GH_API '+$endpoint)};$r|ConvertFrom-Json
}
$head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json
if($head.object.sha -cne $parent){throw 'BRANCH_MOVED_DO_NOT_OVERWRITE'}
$base=gh api ($api+'/git/commits/'+$parent)|ConvertFrom-Json
$files=@{}
foreach($f in Get-ChildItem -LiteralPath $Delivery -File){$files[$prefix+'/delivery/'+$f.Name]=$f.FullName}
$files['docs/MEMPHIS_00_01_SOLVER_PRESSURE_SAFETY_V1_DELIVERY.md']=Join-Path $Delivery '14_ENGINEERING_REPORT_ZH.md'
foreach($name in @('review_official.ps1','review_traces.mjs','assemble_review.mjs','publish_delivery.ps1','prepare_manifest.ps1','publish.ps1','extract_final_basis.ps1','report_qa.json')){$files[$prefix+'/'+$name]=Join-Path $PSScriptRoot $name}
foreach($id in @('39495584820','39497147240')){
 $r='D:/Github/c2c-evidence-review/memphis-r12-solver-pressure-safety-v1/run'+$id
 foreach($name in @('independent_byte_review.json','github_artifacts.json')){$files[$prefix+'/evidence/run'+$id+'/'+$name]=Join-Path $r $name}
 if(Test-Path -LiteralPath (Join-Path $r 'independent_trace_review.json')){$files[$prefix+'/evidence/run'+$id+'/independent_trace_review.json']=Join-Path $r 'independent_trace_review.json'}
}
$entries=@()
foreach($p in $files.Keys|Sort-Object){
 if($p -notlike ($prefix+'/*') -and $p -cne 'docs/MEMPHIS_00_01_SOLVER_PRESSURE_SAFETY_V1_DELIVERY.md'){throw 'DELIVERY_SCOPE'}
 $bytes=[IO.File]::ReadAllBytes($files[$p]);$b=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($bytes)}
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0));$expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$bytes))).ToLowerInvariant()
 if($b.sha -cne $expected){throw 'BLOB_IDENTITY'}
 $entries+=@{path=$p;sha=$b.sha;type='blob';mode='100644'}
}
$tree=Send 'git/trees' @{base_tree=$base.tree.sha;tree=$entries}
$commit=Send 'git/commits' @{parents=@($parent);tree=$tree.sha;message='Bind final 00/01 basis and document bounded solver fix with retained pressure and continuity failures [skip ci]'}
$diff=gh api ($api+'/compare/'+$parent+'...'+$commit.sha)|ConvertFrom-Json
foreach($f in $diff.files){if(-not $files.ContainsKey($f.filename)){throw 'SOURCE_CHANGED_IN_DELIVERY'}}
$r=Send ('git/refs/heads/'+$branch) @{sha=$commit.sha;force=$false} 'PATCH'
if($r.object.sha -cne $commit.sha){throw 'REF_IDENTITY'}
$result=@{delivery_commit=$commit.sha;execution_commit=$parent;branch=$branch;files=$entries;model_executed=$false;
 delivery_manifest_sha256=(Get-FileHash -LiteralPath (Join-Path $Delivery '16_SOURCE_AND_EVIDENCE_MANIFEST.json')).Hash.ToLowerInvariant();
 engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'delivery_publication.json'),($result|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
$result|Select-Object delivery_commit,execution_commit,branch,delivery_manifest_sha256|ConvertTo-Json
