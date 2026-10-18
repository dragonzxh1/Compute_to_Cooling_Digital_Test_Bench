param([Parameter(Mandatory)][string]$Group)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or $env:ImageVersion -notin @('20261004.326.1','20261012.333.1')){throw 'REMOTE_ONLY'}
$repo=(Get-Location).Path;$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
if((Get-FileHash 'v0_2/tests/tools/memphis_inverse_sizing_v1/source_manifest.json').Hash.ToLowerInvariant() -cne '33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f'){throw 'BOUND_MODEL_MANIFEST'}
$root=Join-Path $repo ('hydraulic-review/'+$Group);New-Item -ItemType Directory -Path $root -Force|Out-Null
$utf8=[Text.UTF8Encoding]::new($false)
function Save($p,$x){[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 30),$utf8)}
$run=gh api ($api+'/actions/runs/39136524640')|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.head_sha -cne '840e813dbc6ef0840c7e26850bc4ba6276dd4ffb' -or $run.run_attempt -ne 1){throw 'EXACT_COMPLETED_CALCULATION_REQUIRED'}
$listing=gh api ($api+'/actions/runs/39136524640/artifacts?per_page=100')|ConvertFrom-Json
$a=@($listing.artifacts|Where-Object name -ceq ('memphis-inverse-raw-'+$Group+'-39136524640'));if($a.Count -ne 1){throw 'GROUP_ARTIFACT'}
$zip=Join-Path $root 'official.zip';gh api ($api+'/actions/artifacts/'+$a[0].id+'/zip') > $zip
if($LASTEXITCODE -ne 0 -or 'sha256:'+(Get-FileHash $zip).Hash.ToLowerInvariant() -cne $a[0].digest){throw 'OFFICIAL_ZIP_DIGEST'}
Save (Join-Path $root 'download_receipt.json') @{model_run=39136524640;source_commit=$run.head_sha;artifact=$a[0];review_commit=$env:GITHUB_SHA;reviewer_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'file_review.py')).Hash.ToLowerInvariant()}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($zip,(Join-Path $root 'full'))
& ./v0_2/tests/tools/m1_remote_executor_v1/build.ps1
if($LASTEXITCODE -ne 0){throw 'CONTROLLED_EXECUTOR_BUILD'}
$build=Join-Path $repo 'artifacts/m1-remote-executor-v1/build';$python=(Get-Command python).Source
function Quote($v){return '"'+([string]$v).Replace('"','\"')+'"'}
$reg=Get-Content 'v0_2/tests/tools/memphis_inverse_sizing_v1/registration.json' -Raw|ConvertFrom-Json
$stages=@($reg.cases|Where-Object {$_.group -ceq $Group -and $_.kind -in @('group','critical','joint','robust')}|ForEach-Object id)
foreach($stage in $stages){
 $d=Join-Path $root ('runtime/'+$stage);New-Item -ItemType Directory -Path $d -Force|Out-Null
 $status=Join-Path $d 'job_status.json';$start=Join-Path $d 'job_start.json';$cancel=Join-Path $d 'cancel.request';$stdout=Join-Path $d 'stdout.raw';$stderr=Join-Path $d 'stderr.raw'
 $argsList=@($status,$start,$cancel,$stdout,$stderr,'480000','2500','1024','2048',$python,'-B',(Join-Path $PSScriptRoot 'file_review.py'),$stage,$root,$d)
 $p=Start-Process -FilePath (Join-Path $build 'ControlledJob.exe') -WindowStyle Hidden -ArgumentList (($argsList|ForEach-Object {Quote $_}) -join ' ') -WorkingDirectory $repo -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
 $timer=[Diagnostics.Stopwatch]::StartNew()
 try{
  while(-not(Test-Path (Join-Path $d 'ready.json'))){if($p.HasExited -or $timer.ElapsedMilliseconds -gt 30000){throw 'READY_OR_EXIT'};Start-Sleep -Milliseconds 50}
  $ready=Get-Content (Join-Path $d 'ready.json') -Raw|ConvertFrom-Json;$job=Get-Content $start -Raw|ConvertFrom-Json;$proof=Join-Path $d 'external_job_identity.json'
  $v=Start-Process -FilePath (Join-Path $build 'VerifyTarget.exe') -WindowStyle Hidden -ArgumentList ((@($job.job_name,[string]$ready.pid,'1024','2048',$proof,'2500')|ForEach-Object {Quote $_}) -join ' ') -PassThru
  if(-not $v.WaitForExit(5000) -or $v.ExitCode -ne 0){throw 'ACTUAL_PYTHON_JOB'}
  Save (Join-Path $d 'release.json') @{actual_python_pid=$ready.pid;external_proof_raw_sha256=(Get-FileHash $proof).Hash.ToLowerInvariant()}
  while(-not $p.WaitForExit(5000)){if($timer.ElapsedMilliseconds -gt 495000){throw 'OUTER_TIMEOUT'}}
 }catch{Save $cancel @{requested=$true};if(-not $p.WaitForExit(3000)){$p.Kill()};throw}
 $s=Get-Content $status -Raw|ConvertFrom-Json
 if(-not $s.cleanup_complete -or $s.active_after_cleanup -ne 0 -or $s.child_exitcode -ne 0 -or $s.outcome -cne 'EXITED' -or $p.ExitCode -ne 0){Get-Content $stderr -Tail 30;throw ('INDEPENDENT_PRIMARY_REVIEW_FAILED '+$stage)}
 Write-Host ('INDEPENDENT_PRIMARY_REVIEW_PASS '+$stage)
}
