param([switch]$Seal,[switch]$Publish)
# Review the actual partial run. No candidate imports, simulation or test execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$run='39408912940';$commit='3ee9f97f31f5f395e51c1a561b2a8aed8ba2c97d'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$base='D:/Github/c2c-evidence-review/memphis-control-path-v1/run'+$run
$out=Join-Path $base 'partial-delivery';$utf=[Text.UTF8Encoding]::new($false)
function Save($name,$v){[IO.File]::WriteAllText((Join-Path $out $name),($v|ConvertTo-Json -Depth 80),$utf)}
function ReadEntry($z,$e){$r=[IO.StreamReader]::new($e.Open());try{return $r.ReadToEnd()|ConvertFrom-Json}finally{$r.Dispose()}}
function WriteEntry($e,$target){$s=$e.Open();$d=[IO.File]::Open($target,[IO.FileMode]::CreateNew);try{$s.CopyTo($d)}finally{$s.Dispose();$d.Dispose()}}
$proof=Get-Content -Raw (Join-Path $base 'independent_partial_verification.json')|ConvertFrom-Json
if($proof.execution_commit -cne $commit -or $proof.campaign -cne 'INCOMPLETE_FAILED_NEGATIVE_NOT_EXCITED' -or $proof.full_campaign_pass){throw 'PARTIAL_VERIFICATION_REQUIRED'}
if(-not(Test-Path $out)){
 New-Item -ItemType Directory -Path $out|Out-Null
 $cases=[ordered]@{};$points=[ordered]@{};$bindings=@();$smoke=@()
 foreach($a in $proof.archives|Where-Object name -like 'memphis-loop-raw-*'){
  $archive=Join-Path $base ($a.name+'.zip');$z=[IO.Compression.ZipFile]::OpenRead($archive)
  try{foreach($e in $z.Entries|Where-Object FullName -match '/loop_summary.json$'){
   $c=ReadEntry $z $e;if($c.source_commit -cne $commit -or $cases.Contains($c.id)){throw 'CASE_IDENTITY_OR_DUPLICATE'}
   $cases[$c.id]=$c;$prefix=$e.FullName.Substring(0,$e.FullName.Length-'loop_summary.json'.Length)
   $pe=$z.GetEntry($prefix+'plot_data.json');if(-not $pe){throw 'PLOT_MISSING'};$rows=@(ReadEntry $z $pe)
   # Display-only sampling; decisions remain the independently saved all-step results.
   $sampled=@();for($i=0;$i -lt $rows.Count;$i+=5){$sampled+=$rows[$i]}
   if($sampled[-1].time_s -ne $rows[-1].time_s){$sampled+=$rows[-1]}
   foreach($r in $sampled){foreach($k in @('A_profile_C','B_profile_C')){if($r.PSObject.Properties[$k]){
    $full=@($r.$k);$indices=@(0..8|ForEach-Object {[int][math]::Round($_*($full.Count-1)/8)}|Sort-Object -Unique)
    $r.$k=@($indices|ForEach-Object {$full[$_]})
   }}}
   $points[$c.id]=$sampled
   $bindings+=@{case=$c.id;official_zip=$a.name+'.zip';official_zip_sha256=$a.local_sha256;raw_summary_entry=$e.FullName;raw_plots_entry=$pe.FullName;time_display='Every fifth saved display point and final; full physical-step verdicts unchanged';profile_display='Nine actual layer values bottom to top; full arrays in official raw archive';coverage='Only stages with loop_summary included'}
   # CSV is actual saved numerical output, not regenerated simulation.
   $dataDir=Join-Path $out ('raw/'+$c.id);New-Item -ItemType Directory -Path $dataDir -Force|Out-Null
   foreach($rel in @('case/physical_path.csv','tank_port_ledger.csv','case/source_phases.json','case/branch_coverage.json','per_tank_qualification.json','FINAL_DISCHARGE.csv','PRE_SECOND_DISCHARGE.csv')){
    $entry=$z.GetEntry($prefix+$rel);if($entry){WriteEntry $entry (Join-Path $dataDir ([IO.Path]::GetFileName($rel)))}
   }
  }
  foreach($e in $z.Entries|Where-Object FullName -match '/NEW_PATH_SMOKE/.*/branch_coverage.json$'){$smoke+=@{entry=$e.FullName;data=(ReadEntry $z $e)}}
  }finally{$z.Dispose()}
 }
 Save 'ACTUAL_COMPLETED_CASES.json' $cases;Save 'DISPLAY_SAMPLING_BINDINGS.json' $bindings;Save 'SYNTHETIC_INTERFACE_ONLY.json' $smoke
 $reg=Get-Content -Raw (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/registration.json')|ConvertFrom-Json
 $attr=@();$baseline=$cases['ATTR_BASE'];foreach($key in $cases.Keys){if($key -notlike 'ATTR_*'){continue};$c=$cases[$key]
  $attr+=@{id=$key;change=($reg.cases|Where-Object id -eq $key).change;peak_C=$c.maximum_inlet_C;first90_C=$c.maximum90_inlet_C;delta_K=$c.maximum_inlet_C-$baseline.maximum_inlet_C;minimum_flow_m3_h=$c.minimum_load_m3_h;energy=$c.independent.independent_energy;scope='FIRST240S_ONLY; source assumptions, not OEM facts'}
 };Save 'FIRST_FAULT_ATTRIBUTION.json' $attr
 foreach($name in @('official_run.json','official_artifacts.json','independent_partial_verification.json','FAILED_GROUP_LOCAL_HASHES.json')){Copy-Item -LiteralPath (Join-Path $base $name) -Destination (Join-Path $out $name)}
 foreach($name in @('VENDOR_EVIDENCE_REQUIRED.csv','EVIDENCE_FIELD_DISPOSITIONS.json','BUILD001_FAILURE.md','BUILD002_FAILURE.md','runtime-pid@2x.png')){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $out $name)}
 foreach($name in @('prior_root_cause.json','customer_originals.json','DESIGNER_CONFIRMATION.md','registration.json','source_manifest.json')){Copy-Item -LiteralPath (Join-Path $repo ('v0_2/tests/tools/memphis_control_path_v1/'+$name)) -Destination (Join-Path $out $name)}
 Copy-Item -LiteralPath (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/diagram/runtime_pid.svg') -Destination (Join-Path $out 'runtime_pid.svg')
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'source-3ee9f97.zip') -Destination (Join-Path $out 'source_snapshot.zip')
 $inventory=foreach($s in $reg.cases){$actual=@($proof.stages|Where-Object stage -eq $s.id);[ordered]@{id=$s.id;group=$s.group;kind=$s.kind;execution=if($actual.Count){$actual[0].status}else{'NOT_EXECUTED'};failure=if($actual.Count){$actual[0].error}else{$null};result_in_report=$cases.Contains($s.id)}}
 Save 'REGISTERED_STAGE_DISPOSITION.json' @($inventory)
 $note=@'
<section role="alert"><h2>本轮未完成：不能判整体 PASS</h2><p><strong>INCOMPLETE · MEMPHIS_ENGINEERING_NOT_APPROVED</strong>。B阀卡滞负对照未激发B命令，门禁报NEGATIVE_B_NOT_EXCITED后停止；后续4个模型案例及FINAL未执行。本报告由已保存官方证据离线整理，不是远程FINAL交付或全量通过。</p><p>主工况B初始为48.29°C暖罐，并非本次完整首次故障实际耗用后的状态。3用3备CDU接管尚未实现。共享B分支主工况全部未到达，不能证明客户原方案不可能，也不能证明必须新增RC。</p><p>control_path.maximum_energy_residual_J的0值是未计算预留字段，状态INVALID；真实复核使用独立能量账本。17TT筛选不等于90秒Ready。图线抽取每五个保存点和末点，温剖只显示九个实际层值；完整原始数据和全部物理步判定保持不变。</p><p><a href="REGISTERED_STAGE_DISPOSITION.json">全部登记阶段与未执行清单</a> · <a href="FIRST_FAULT_ATTRIBUTION.json">单参数归因原值</a> · <a href="independent_partial_verification.json">官方字节/Job独立核验及缺口</a></p></section>
'@
 $template=Get-Content -Raw (Join-Path $repo 'v0_2/tests/tools/memphis_control_path_v1/report_template.html')
 $template=$template.Replace('<label>案例',($note+'<label>案例')).Replace('JSON.stringify(c.control_path,null,2)',"JSON.stringify(c.control_path,(key,value)=>key==='maximum_energy_residual_J'?'INVALID_UNCOMPUTED_METADATA':value,2)")
 $payload=@{cases=$cases;points=$points}|ConvertTo-Json -Compress -Depth 80
 $template=$template.Replace('PAYLOAD',$payload.Replace('</','<\/'))
 [IO.File]::WriteAllText((Join-Path $out 'engineering_report.html'),$template,$utf)
}
if(-not(Test-Path (Join-Path $out 'PACKAGE_MANIFEST.json'))){
 $htmlPath=Join-Path $out 'engineering_report.html';$html=Get-Content -Raw $htmlPath
 if(-not $html.Contains("picker.value='ORIGINAL_80';")){$html=$html.Replace('function plot(id',"picker.value='ORIGINAL_80';`nfunction plot(id")}
 $html=$html.Replace('RC仅固定1MW隔离对照；','RC登记为固定1MW隔离对照，但本轮尚未执行；')
 $html=$html.Replace('body{font:', 'body{overflow-wrap:anywhere;font:')
 [IO.File]::WriteAllText($htmlPath,$html,$utf)
 # Tank observer writes ledgers at stage root, not under case/. Recover exact
 # archived bytes if preparing a review that already exists; never recompute them.
 foreach($a in $proof.archives|Where-Object name -like 'memphis-loop-raw-*'){
  $z=[IO.Compression.ZipFile]::OpenRead((Join-Path $base ($a.name+'.zip')))
  try{foreach($e in $z.Entries|Where-Object FullName -match '/(tank_port_ledger|FINAL_DISCHARGE|PRE_SECOND_DISCHARGE)\.csv$'){
   $id=($e.FullName -split '/')[-2];$dir=Join-Path $out ('raw/'+$id)
   if(Test-Path $dir){$target=Join-Path $dir ([IO.Path]::GetFileName($e.FullName));if(-not(Test-Path $target)){WriteEntry $e $target}}
  }}finally{$z.Dispose()}
 }
 foreach($pair in @(@('saved_permission_analysis.json','saved_permission_analysis.json'),@('saved_full_absence_analysis.json','saved_full_absence_analysis.json'))){$src=Join-Path $base $pair[0];if(Test-Path $src){Copy-Item -LiteralPath $src -Destination (Join-Path $out $pair[1])}}
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PARTIAL_ENGINEERING_REPORT_ZH.md') -Destination (Join-Path $out 'ENGINEERING_REPORT_ZH.md')
 $failed=@{result=(Get-Content -Raw (Join-Path $base 'B_VALVE_STUCK/result.json')|ConvertFrom-Json);native_job=(Get-Content -Raw (Join-Path $base 'B_VALVE_STUCK/job_status.json')|ConvertFrom-Json);external_identity=(Get-Content -Raw (Join-Path $base 'B_VALVE_STUCK/external_job_identity.json')|ConvertFrom-Json);raw_stdout=(Get-Content -Raw (Join-Path $base 'B_VALVE_STUCK/stdout.raw'));scope='Original failed bytes preserved in official ZIP; JSON parses/collects them for review, not a new test'}
 Save 'FAILED_STAGE_EVIDENCE.json' $failed
 Save 'TRANSPORT_SCOPE.json' @{git='Top-level review files and source_snapshot only; candidate source is in execution commit';local='Includes raw/<case>/ original CSV/JSON';complete_original='Exact official raw artifact ZIPs retained beside this directory, see official_artifacts.json';not_a_remote_final=$true;not_all_raw_csv_published_to_git=$true}
}
if(-not $Seal -and -not $Publish){$out;return}
$report=Join-Path $out 'ENGINEERING_REPORT_ZH.md';if(-not(Test-Path $report)){throw 'CONSOLIDATED_CHINESE_REPORT_REQUIRED'}
$package=Join-Path $out 'PACKAGE_MANIFEST.json'
if(-not(Test-Path $package)){
 $m=[ordered]@{schema='MEMPHIS-CONTROL-PATH-PARTIAL-REVIEW-DELIVERY-v1';execution_commit=$commit;run=$run;campaign='INCOMPLETE_FAILED_NEGATIVE_NOT_EXCITED';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';files=[ordered]@{};no_remote_FINAL=$true;formal=$false;hardware=$false;procurement=$false;phase6=$false}
 foreach($f in Get-ChildItem $out -File -Recurse|Sort-Object FullName){$rel=[IO.Path]::GetRelativePath($out,$f.FullName).Replace('\','/');$m.files[$rel]=(Get-FileHash $f.FullName).Hash.ToLowerInvariant()}
 Save 'PACKAGE_MANIFEST.json' $m
}
$m=Get-Content -Raw $package|ConvertFrom-Json;foreach($p in $m.files.PSObject.Properties){if((Get-FileHash (Join-Path $out $p.Name)).Hash.ToLowerInvariant() -cne $p.Value){throw 'SEALED_REVIEW_DRIFT'}}
if($Publish){
 $api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$branch='codex/memphis-control-path-v1'
 function Send($ep,$v,$method='POST'){$s=($v|ConvertTo-Json -Compress -Depth 20)|gh api ($api+'/'+$ep) --method $method --input -;if($LASTEXITCODE -ne 0){throw ('GH_API '+$ep)};return $s|ConvertFrom-Json}
 $head=gh api ($api+'/git/ref/heads/'+$branch)|ConvertFrom-Json;if($head.object.sha -cne $commit){throw 'BRANCH_MOVED'}
 $parent=gh api ($api+'/git/commits/'+$commit)|ConvertFrom-Json;$entries=@()
 # Publish compact review and sources only; huge raw time series remain in exact
 # official ZIPs and the local delivery, never mislabeled as small Git evidence.
 foreach($f in Get-ChildItem $out -File|Sort-Object Name){
  $b=[IO.File]::ReadAllBytes($f.FullName);$r=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($b)}
  $h=[Text.Encoding]::ASCII.GetBytes(('blob '+$b.Length+[char]0));$sha=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($h+$b))).ToLowerInvariant();if($r.sha -cne $sha){throw 'BLOB_READBACK'}
  $entries+=@{path=('artifacts/memphis-control-path-v1/partial-delivery/'+$f.Name);mode='100644';type='blob';sha=$sha}
 }
 foreach($f in @('verify_partial.ps1','deliver_partial_review.ps1','analyze_saved_permission.ps1','analyze_saved_absence.ps1')){$b=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $f));$r=Send 'git/blobs' @{encoding='base64';content=[Convert]::ToBase64String($b)};$entries+=@{path=('artifacts/memphis-control-path-v1/'+$f);mode='100644';type='blob';sha=$r.sha}}
 $tree=Send 'git/trees' @{base_tree=$parent.tree.sha;tree=$entries};$c=Send 'git/commits' @{message='Preserve incomplete original control-path campaign, actual attribution and explicit missing coverage [skip ci]';parents=@($commit);tree=$tree.sha}
 $ref=Send ('git/refs/heads/'+$branch) @{sha=$c.sha;force=$false} 'PATCH';if($ref.object.sha -cne $c.sha){throw 'REF_READBACK'}
 $check=gh api ($api+'/git/trees/'+$tree.sha+'?recursive=1')|ConvertFrom-Json;foreach($e in $entries){if(-not($check.tree|Where-Object {$_.path -ceq $e.path -and $_.sha -ceq $e.sha})){throw 'TREE_READBACK'}}
 $receipt=@{execution=$commit;run=$run;delivery_commit=$c.sha;branch=$branch;package_manifest_sha256=(Get-FileHash $package).Hash.ToLowerInvariant();scope='Artifact-only partial review; no candidate changes, no dispatch';published=$entries}
 [IO.File]::WriteAllText((Join-Path $base 'partial_publication_receipt.json'),($receipt|ConvertTo-Json -Depth 15),$utf);$receipt|Select-Object delivery_commit,package_manifest_sha256|ConvertTo-Json
}
$out
