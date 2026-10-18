param([Parameter(Mandatory)][ValidateSet('PREP','GROUP','FINAL')][string]$Mode,[string]$Group='',[string]$Root='review')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or $env:ImageVersion -notin @('20261004.326.1','20261012.333.1')){throw 'PINNED_REMOTE_FILE_REVIEW_ONLY'}
$repo=(Get-Location).Path;$rootPath=[IO.Path]::GetFullPath((Join-Path $repo $Root));New-Item -ItemType Directory -Path $rootPath -Force|Out-Null
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench';$utf8=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Save([string]$p,$x){[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 40),$utf8)}
function Get-Json([string]$endpoint){$r=gh api ($api+'/'+$endpoint);if($LASTEXITCODE -ne 0){throw ('API_READ '+$endpoint)};return $r|ConvertFrom-Json}
function Get-Zip($a){
 $p=Join-Path $rootPath ($a.name+'.zip')
 if(-not(Test-Path $p)){gh api ($api+'/actions/artifacts/'+$a.id+'/zip') > $p;if($LASTEXITCODE -ne 0){throw 'DOWNLOAD_SAME_RUN_REQUIRED'}}
 if((Get-Item $p).Length -ne $a.size_in_bytes -or 'sha256:'+(Get-FileHash $p).Hash.ToLowerInvariant() -cne $a.digest){throw 'OFFICIAL_ZIP_HASH'}
 return $p
}
function Entry([string]$zip,[string]$name,[string]$dest){
 $z=[IO.Compression.ZipFile]::OpenRead($zip)
 try{$e=@($z.Entries|Where-Object Name -ceq $name);if($e.Count -ne 1){throw ('EXACT_ZIP_ENTRY '+$name)};$s=$e[0].Open();$o=[IO.File]::Create($dest);try{$s.CopyTo($o)}finally{$s.Dispose();$o.Dispose()}}finally{$z.Dispose()}
}
function Quote([string]$v){return '"'+$v.Replace('"','\"')+'"'}
function Controlled([string]$stage){
 & ./v0_2/tests/tools/m1_remote_executor_v1/build.ps1 | Write-Host
 if($LASTEXITCODE -ne 0){throw 'REVIEW_EXECUTOR_BUILD'}
 $build=Join-Path $repo 'artifacts/m1-remote-executor-v1/build';$d=Join-Path $rootPath ('runtime/'+$stage);New-Item -ItemType Directory -Path $d -Force|Out-Null
 $status=Join-Path $d 'job_status.json';$start=Join-Path $d 'job_start.json';$cancel=Join-Path $d 'cancel.request';$stdout=Join-Path $d 'stdout.raw';$stderr=Join-Path $d 'stderr.raw'
 $python=(Get-Command python).Source
 $args=@($status,$start,$cancel,$stdout,$stderr,'480000','2500','1024','2048',$python,'-B',(Join-Path $PSScriptRoot 'file_review.py'),$stage,$rootPath,$d)
 $p=Start-Process -FilePath (Join-Path $build 'ControlledJob.exe') -WindowStyle Hidden -ArgumentList (($args|ForEach-Object {Quote $_}) -join ' ') -WorkingDirectory $repo -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
 $timer=[Diagnostics.Stopwatch]::StartNew()
 try{
  while(-not(Test-Path (Join-Path $d 'ready.json'))){if($p.HasExited -or $timer.ElapsedMilliseconds -gt 30000){throw 'FILE_REVIEW_READY'};Start-Sleep -Milliseconds 50}
  $ready=Get-Content (Join-Path $d 'ready.json') -Raw|ConvertFrom-Json;$job=Get-Content $start -Raw|ConvertFrom-Json;$proof=Join-Path $d 'external_job_identity.json'
  $v=Start-Process -FilePath (Join-Path $build 'VerifyTarget.exe') -WindowStyle Hidden -ArgumentList ((@($job.job_name,[string]$ready.pid,'1024','2048',$proof,'2500')|ForEach-Object {Quote $_}) -join ' ') -PassThru
  if(-not $v.WaitForExit(5000) -or $v.ExitCode -ne 0){throw 'FILE_REVIEW_ACTUAL_JOB'}
  Save (Join-Path $d 'release.json') @{actual_python_pid=$ready.pid;external_proof_raw_sha256=(Get-FileHash $proof).Hash.ToLowerInvariant()}
  while(-not $p.WaitForExit(5000)){if($timer.ElapsedMilliseconds -gt 495000){throw 'FILE_REVIEW_OUTER_TIMEOUT'};Get-Content $stdout -Tail 1 -ErrorAction SilentlyContinue|Write-Host}
 }catch{Save $cancel @{requested=$true};if(-not $p.WaitForExit(3000)){$p.Kill()};throw}
 $s=Get-Content $status -Raw|ConvertFrom-Json
 if(-not $s.cleanup_complete -or $s.active_after_cleanup -ne 0 -or $s.child_exitcode -ne 0 -or $s.outcome -cne 'EXITED' -or $p.ExitCode -ne 0){Get-Content $stderr -Tail 30;throw ('FILE_REVIEW_EXECUTION_FAILURE '+$stage)}
 Write-Host ('PURE_FILE_REVIEW_END '+$stage+' PASS')
 return $d
}
if($Mode -ceq 'PREP'){
 if((git rev-parse HEAD) -cne $env:GITHUB_SHA){throw 'REVIEW_CHECKOUT_DRIFT'}
 $frozen=Get-Content 'v0_2/tests/tools/m1_remote_control_v3/execution_manifest.json' -Raw|ConvertFrom-Json
 foreach($b in $frozen.bundle_entry_raw_hashes.PSObject.Properties){if(Test-Path -LiteralPath $b.Name){$h=(Get-FileHash -LiteralPath $b.Name).Hash.ToLowerInvariant();$transport=$b.Name -ceq 'v0_2/tests/tools/m1_remote_control_v1/source_inventory.json' -and $h -ceq 'dd016d1bafd016c6f014520d277ce9ab79024e7a3b224bca5c5d8c7426a2a3f9' -and $b.Value -ceq '02d336b2c5217ef279ced4f9ebefafc7ec2b9110ec567da7341052f0b073fa39';if($h -cne $b.Value -and -not $transport){throw 'PROTECTED_SOURCE_DRIFT'}}}
 . ./v0_2/tests/tools/m1_remote_control_v3/restore_snapshot.ps1
 $null=Restore-M1Snapshot -Repo $repo -ExpectedManifestSha256 '6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93'
 $pkg='v0_2/tests/tools/memphis_equipment_validation_v2';if((Get-FileHash ($pkg+'/source_manifest.json')).Hash.ToLowerInvariant() -cne '5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16'){throw 'EXECUTABLE_MANIFEST_CHANGED'}
 $m=Get-Content ($pkg+'/source_manifest.json') -Raw|ConvertFrom-Json;$closure=@{};$count=0
 foreach($map in @($m.source_raw_sha256,$m.v1_source_raw_sha256,(Get-Content 'artifacts/m1-c3c-v5-freeze/executable_proposal.json' -Raw|ConvertFrom-Json).source_raw_sha256)){foreach($b in $map.PSObject.Properties){if((Get-FileHash -LiteralPath $b.Name).Hash.ToLowerInvariant() -cne $b.Value){throw ('SOURCE_DRIFT '+$b.Name)};if($closure.ContainsKey($b.Name) -and $closure[$b.Name] -cne $b.Value){throw 'CONFLICTING_SOURCE_BINDING'};$closure[$b.Name]=$b.Value;$count++}}
 $reg=Get-Content ($pkg+'/registration.json') -Raw|ConvertFrom-Json;$original=Get-Content (Join-Path $PSScriptRoot 'local_original_hashes.json') -Raw|ConvertFrom-Json
 foreach($id in @('00','01')){if($original.records.$id.sha256 -cne $reg.input_hashes.$id){throw 'CUSTOMER_ORIGINAL_HASH'}}
 Save (Join-Path $rootPath 'source_closure.json') @{source_bindings=$count;source_file_raw_sha256=$closure;review_commit=$env:GITHUB_SHA}
 $run=Get-Json 'actions/runs/39088951176';if($run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.head_sha -cne '6031e0ef7d32bec0109f328f85ebd5dfef8fe048' -or $run.run_attempt -ne 1){throw 'EXACT_ORIGINAL_RUN'}
 Save (Join-Path $rootPath 'run_metadata.json') $run
 $index=Get-Json 'actions/runs/39088951176/artifacts?per_page=100';Save (Join-Path $rootPath 'official_artifact_index.json') $index
 Save (Join-Path $rootPath 'prior_artifact_index.json') (Get-Json 'actions/runs/39087966476/artifacts?per_page=100')
 $verified=@()
 foreach($a in $index.artifacts|Where-Object {$_.name -like 'memphis-equipment-compact-*' -or $_.name -like 'memphis-equipment-report-*'}){
  $zip=Get-Zip $a;$verified+=@{name=$a.name;digest=$a.digest;bytes=$a.size_in_bytes}
  if($a.name -like 'memphis-equipment-report-*'){
   Entry $zip 'consolidated_report.json' (Join-Path $rootPath 'consolidated_report.json')
   New-Item -ItemType Directory -Path (Join-Path $rootPath 'report-complete') -Force|Out-Null
   Copy-Item (Join-Path $rootPath 'consolidated_report.json') (Join-Path $rootPath 'report-complete/consolidated_report.json')
   Entry $zip 'engineering_report.html' (Join-Path $rootPath 'report-complete/engineering_report.html')
  }
 }
 Save (Join-Path $rootPath 'prepared_receipt.json') @{verified_current_zips=$verified;review_commit=$env:GITHUB_SHA;model_executed=$false}
}elseif($Mode -ceq 'GROUP'){
 $index=Get-Content (Join-Path $rootPath 'official_artifact_index.json') -Raw|ConvertFrom-Json;$a=@($index.artifacts|Where-Object name -ceq ('memphis-equipment-raw-'+$Group+'-39088951176'));if($a.Count -ne 1){throw 'GROUP_ARTIFACT'}
 $zip=Get-Zip $a[0];$full=Join-Path $rootPath 'full';[IO.Compression.ZipFile]::ExtractToDirectory($zip,$full)
 $prior=Get-Content (Join-Path $rootPath 'prior_artifact_index.json') -Raw|ConvertFrom-Json;$old=@($prior.artifacts|Where-Object name -ceq ('memphis-equipment-compact-'+$Group+'-39087966476'));if($old.Count -ne 1){throw 'PRIOR_ARTIFACT'}
 $priorZip=Get-Zip $old[0];Entry $priorZip 'artifact_hashes.json' (Join-Path $rootPath 'prior_inventory.json')
 $d=Controlled $Group
 Save (Join-Path $d 'download_receipt.json') @{current_zip=@{name=$a[0].name;digest=$a[0].digest;bytes=$a[0].size_in_bytes};prior_zip=@{name=$old[0].name;digest=$old[0].digest};model_executed=$false}
}else{
 gh api ($api+'/actions/runs/39088951176/logs') > (Join-Path $rootPath 'raw_logs.zip');if($LASTEXITCODE -ne 0){throw 'ORIGINAL_LOG_DOWNLOAD'}
 $d=Controlled 'FINAL'
 & (Join-Path $PSScriptRoot 'build_delivery.ps1') -Root $rootPath
 $batch=@(Get-ChildItem (Join-Path $rootPath 'group-results') -Recurse -Filter job_status.json)+@(Get-Item (Join-Path $d 'job_status.json'))
 $records=foreach($file in $batch){$s=Get-Content $file.FullName -Raw|ConvertFrom-Json;if(-not $s.cleanup_complete -or $s.active_after_cleanup -ne 0 -or $s.child_exitcode -ne 0){throw 'POST_EXIT_REVIEW_CLEANUP'};@{stage=$file.Directory.Name;job_status_sha256=(Get-FileHash $file.FullName).Hash.ToLowerInvariant();active_after_cleanup=0;child_exitcode=0}}
 Save (Join-Path $rootPath 'delivery/independent_review_post_exit_batch.json') @{review_commit=$env:GITHUB_SHA;original_model_commit='6031e0ef7d32bec0109f328f85ebd5dfef8fe048';records=$records;model_rerun=$false;formal=$false;hardware=$false;phase6=$false}
 & (Join-Path $PSScriptRoot 'build_delivery.ps1') -Root $rootPath
}
