param([Parameter(Mandatory)][string]$ExpectedCommit,
      [Parameter(Mandatory)][string]$ExpectedControlSha256)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
if($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or [Environment]::MachineName -ieq 'HIPPO'){throw 'REMOTE_DETACHED_ATTESTATION_ONLY'}
if($env:GITHUB_SHA -cne $ExpectedCommit -or (git -C $repo rev-parse HEAD) -cne $ExpectedCommit){throw 'EXACT_DELIVERED_COMMIT_REQUIRED'}
$controlPath=Join-Path $PSScriptRoot 'control.json'
if((Get-FileHash -LiteralPath $controlPath).Hash.ToLowerInvariant() -cne $ExpectedControlSha256){throw 'POST_READBACK_CONTROL_DRIFT'}
$control=Get-Content -LiteralPath $controlPath -Raw|ConvertFrom-Json
foreach($b in $control.source_hashes.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $repo $b.Name)).Hash.ToLowerInvariant() -cne $b.Value){throw 'POST_READBACK_SOURCE_DRIFT'}}
$runRoot=Join-Path $repo ('artifacts/m1-c3c-v4-closure/'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT+'-CHECKS')
$resultPath=Join-Path $runRoot 'result.json'
$result=Get-Content -LiteralPath $resultPath -Raw|ConvertFrom-Json
if($result.refusal_checks.Count -ne $control.expected_refusal_check_count -or @($result.refusal_checks|Where-Object status -cne 'PASS').Count){throw 'DETACHED_REFUSAL_COUNT_OR_STATUS_DRIFT'}
$accepted=Get-Content -LiteralPath (Join-Path $runRoot 'execution_acceptance.json') -Raw|ConvertFrom-Json
$native=Get-Content -LiteralPath (Join-Path $runRoot 'job_status.json') -Raw|ConvertFrom-Json
$proof=Get-Content -LiteralPath (Join-Path $runRoot 'external_job_identity.json') -Raw|ConvertFrom-Json
$ready=Get-Content -LiteralPath (Join-Path $runRoot 'ready.json') -Raw|ConvertFrom-Json
$release=Get-Content -LiteralPath (Join-Path $runRoot 'release.json') -Raw|ConvertFrom-Json
$proofHash=(Get-FileHash -LiteralPath (Join-Path $runRoot 'external_job_identity.json')).Hash.ToLowerInvariant()
if($result.status -cne 'C3C_V4_FINAL_PACKAGE_READBACK_PASS' -or $result.source_commit -cne $ExpectedCommit -or $result.source_bindings_verified -ne $control.expected_source_binding_count -or $accepted.actual_job_verified -ne $true -or $accepted.cleanup_verified -ne $true -or $native.cleanup_complete -ne $true -or $native.active_after_cleanup -ne 0 -or $native.child_exitcode -ne 0){throw 'DETACHED_READBACK_OR_CLEANUP_NOT_PASS'}
if($proof.actual_python_pid -ne $ready.pid -or $ready.pid -ne $release.actual_python_pid -or $release.external_proof_raw_sha256 -cne $proofHash -or $proof.in_target_job -ne $true -or $proof.cpu_rate -ne 2500 -or $proof.process_mb -ne 256 -or $proof.job_mb -ne 512){throw 'DETACHED_ACTUAL_JOB_CHAIN_DRIFT'}
$raw=Get-Content -LiteralPath (Join-Path $runRoot 'raw_receipts.json') -Raw|ConvertFrom-Json
foreach($b in $raw.PSObject.Properties){if($b.Value.status -cne 'PERSISTED' -or (Get-FileHash -LiteralPath (Join-Path $runRoot $b.Name)).Hash.ToLowerInvariant() -cne $b.Value.raw_sha256){throw 'DETACHED_RAW_CAPTURE_DRIFT'}}
$dest=Join-Path $repo 'artifacts/m1-c3c-v4-final-delivery/C3_C_V4_FINAL_FREEZE_PACKAGE'
if(Test-Path -LiteralPath $dest){throw 'DO_NOT_OVERWRITE_FINAL_DELIVERY'}
New-Item -ItemType Directory -Path (Split-Path $dest)|Out-Null
Copy-Item -LiteralPath (Join-Path $repo 'C3_C_V4_FINAL_FREEZE_PACKAGE') -Destination $dest -Recurse
Copy-Item -LiteralPath $resultPath -Destination (Join-Path $dest 'INDEPENDENT_READBACK_RESULT.json')
. (Join-Path $repo 'v0_2/tests/tools/m1_c3c_v4/batch.ps1')
$definition=Get-Content -LiteralPath (Join-Path $dest 'EXECUTABLE_FREEZE_MANIFEST.json') -Raw|ConvertFrom-Json
$payload=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $dest -Recurse -File -Force){$name=$file.FullName.Substring($dest.Length+1).Replace([IO.Path]::DirectorySeparatorChar,'/');$payload[$name]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
$attestationPath=Join-Path $dest 'EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json'
$attestationHash=Write-C3Json $attestationPath @{
    schema='m1-c3c-v4-detached-post-commit-attestation-v1';status='READY_FOR_USER_SIGNATURE'
    execution_source_commit=$ExpectedCommit;delivery_commit=$ExpectedCommit
    same_commit_distinct_roles=$true;identity_origin='Exact GitHub checkout and dispatch after immutable commit; not latest branch HEAD'
    detached_output_not_inside_its_own_commit=$true
    proposal_raw_sha256=$result.proposal_raw_sha256;proposal_canonical_sha256=$result.proposal_canonical_sha256
    candidate_sha256=$definition.candidate_sha256
    formal_runner_raw_sha256=$definition.source_raw_sha256.($definition.execution.runner)
    environment_lock_raw_sha256=$definition.source_raw_sha256.($definition.execution.environment_lock)
    inventory_raw_sha256=$result.inventory_raw_sha256;registration_raw_sha256=$definition.registration_raw_sha256
    independently_verified_content_raw_sha256=$payload
    self_and_signature_sheet_hash_excluded_to_avoid_circular_reference=$true
    readback_run_id=$env:GITHUB_RUN_ID;readback_run_attempt=$env:GITHUB_RUN_ATTEMPT
    control_raw_sha256=$ExpectedControlSha256;readback_result_raw_sha256=(Get-FileHash -LiteralPath $resultPath).Hash.ToLowerInvariant()
    actual_job=@{pid=$proof.actual_python_pid;proof_raw_sha256=$proofHash;cpu_rate=$proof.cpu_rate;process_mb=$proof.process_mb;job_mb=$proof.job_mb;cleanup_complete=$true;active_after_cleanup=0}
    raw_capture_receipts=$raw;environment_before=$result.environment_before;environment_after=$result.environment_after
    source_closure_materialization=('Exact checkout plus hash-bound frozen source ZIP; all'+$control.expected_source_binding_count+' source bytes verified')
    executable_freeze_user_approved=$false;formal_execution_authorized=$false;formal_qualification_executed=$false
    production_or_hardware_or_phase6_authorized=$false
}
$resultHash=(Get-FileHash -LiteralPath $resultPath).Hash.ToLowerInvariant()
$sheet=@"
# C3-C v4 最终统一审签页

状态：READY_FOR_USER_SIGNATURE。未批准冻结，未授权正式执行，未产生 C3-C 资格成绩。

## 签署对象

版本 C3-C-v4-final-proposal；范围 M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN。

EXECUTION_SOURCE_COMMIT：``$ExpectedCommit``

DELIVERY_COMMIT：``$ExpectedCommit``

二者职责分开；本次同一确切commit同时含可执行源码和静态交付包。此页、回读结果和attestation在commit固定后生成，存于只读GitHub artifact，不写入自己所属commit，也不采用后来的branch HEAD。

Proposal RAW：``$($result.proposal_raw_sha256)``

Proposal canonical：``$($result.proposal_canonical_sha256)``

Candidate SHA-256：``$($definition.candidate_sha256)``

Formal runner SHA-256：``$($definition.source_raw_sha256.($definition.execution.runner))``

Identity attestation RAW：``$attestationHash``

Independent readback result RAW：``$resultHash``

完整$($control.expected_source_binding_count)项source bindings、101inputs/3216rows/499计划快照/969static stages+FINAL已核验。Dynamic prefix仍用原mandatory674+fresh progress/confirmed精确union及支持案例完整prefix，不预填旧成绩。Exact hash inventory RAW：``$($result.inventory_raw_sha256)``。

独立只读回读run：[$($env:GITHUB_RUN_ID)](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/$($env:GITHUB_RUN_ID))；$($result.refusal_checks.Count)项合成拒绝检查PASS、真实Python Job/四raw captures/cleanup active0核验PASS，没有candidate import或formal qualification。

环境/dependencies见ENVIRONMENT_DEPENDENCY_LOCK.json，RAW：``$($definition.source_raw_sha256.($definition.execution.environment_lock))``。只允许20261004.326.1/20261012.333.1；Python3.11.9/Windows10.0.20348/AMD64/win22及全部依赖精确锁定，每个Job前后完整身份相同。未知第三镜像STOP；不主张每个案例已在两镜像分别执行。

## 范围和登记

- limited_scope_v2.json：RAW ``$($definition.registration_raw_sha256.limited_scope)``，完整注册软件fixture域，不代表整套真实运行/控制系统。
- SEM01 addendum v3：RAW ``$($definition.registration_raw_sha256.SEM01)``。PRE/Safety/真实模拟PLC事实不可回滚，POST不得赚第二样本；complete-only及四项登记软件失败cuts必须fresh测试。ARBITRARY_POST_EXCEPTION_ATOMICITY=NOT_PROVEN，T09=IMPLEMENTATION_HOLD。
- SEM02 five-case registry v1：RAW ``$($definition.registration_raw_sha256.SEM02)``。精确一条async重建trace＋四条invalid/rejected输入，strict P1 B/C仍INCOMPLETE；原Startup50、历史49/50与versioned compatibility分开，无伪造issue。
- PF06-C8-NORMAL-SUPPLEMENT-v1：RAW ``$($definition.registration_raw_sha256.PF06_supplement)``。C8_normal row4/800ms、独立PRE/Safety/PLC/POSTcut、两原negative controls保留；original scope INCOMPLETE，补充需fresh执行，不改原C3-A。

上述四份登记bytes与v1相同；双镜像政策已单独获用户批准。这里保持独立签署栏，不代签，不把政策批准冒充新包冻结或执行许可。

真实硬件控制/production/Phase6未授权；full P history不可用，hardware CALIBRATION_REQUIRED；真实durable recovery、OS crash/power-loss原子性和未执行的跨镜像全案例等价性不在本包证明范围。不得用限定软件PASS掩盖这些缺口。

## 用户分别签署（全部待填写）

| 决定 | 用户批准/拒绝/保留意见 | 签署人及日期/时区 |
| --- | --- | --- |
| 1. 当前语义/范围登记及明确排除项 |  |  |
| 2. 上述确切包hash与EXECUTION_SOURCE_COMMIT的executable freeze |  |  |
| 3. 单独授权该身份从prepare开始full fresh formal C3-C |  |  |

EXECUTABLE_FREEZE_USER_APPROVED=NO；C3_C_FORMAL_EXECUTION_AUTHORIZED=NO；PRODUCTION_IMPLEMENTATION_AUTHORIZED=NO；HARDWARE_CONTROL_AUTHORIZED=NO；PHASE6=NO。

第2栏批准不隐含第3栏。正式执行不得借旧PASS；任一FAIL/INVALID保存并STOP，同execution不得修复重跑取PASS。最终绿色仍须独立回读行为证据及最后batch cleanup，才可作限定资格判定。
"@
$sheetPath=Join-Path $dest 'USER_APPROVAL_DECISION_SHEET.md'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes($sheet)
$file=[IO.File]::Open($sheetPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
if([Convert]::ToBase64String([IO.File]::ReadAllBytes($sheetPath)) -cne [Convert]::ToBase64String($bytes)){throw 'SIGNATURE_SHEET_PERSISTENCE_FAILURE'}
Write-Output ('READY_FOR_USER_SIGNATURE EXECUTION='+$ExpectedCommit+' DELIVERY='+$ExpectedCommit+' ATTESTATION_SHA256='+$attestationHash)
