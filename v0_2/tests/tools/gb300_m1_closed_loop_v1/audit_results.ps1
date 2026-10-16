param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$SourceCommit)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskResults=@{}
foreach($s in @('NEGATIVE','LOAD_STEP','PUMP_STUCK','REPEAT_LOAD_STEP','REPEAT_PUMP_STUCK','REFINE_50','REFINE_25')){
    $d=Join-Path $Root $s
    $r=Get-Content -LiteralPath (Join-Path $d 'result.json') -Raw|ConvertFrom-Json
    $n=Get-Content -LiteralPath (Join-Path $d 'job_status.json') -Raw|ConvertFrom-Json
    $p=Get-Content -LiteralPath (Join-Path $d 'external_job_identity.json') -Raw|ConvertFrom-Json
    if($r.stage -cne $s -or $r.status -cne 'PASS' -or $r.environment.source_commit -cne $SourceCommit -or
       -not $n.cleanup_complete -or $n.active_after_cleanup -ne 0 -or $n.child_exitcode -ne 0 -or
       $r.pid -ne $p.actual_python_pid -or -not $p.in_target_job -or $p.cpu_rate -ne 2500 -or $p.process_mb -ne 1024 -or $p.job_mb -ne 2048){throw ('INCOMPLETE_STAGE_EVIDENCE '+$s)}
    $taskResults[$s]=$r
}
$repeatChecks=[ordered]@{}
foreach($case in @('LOAD_STEP','PUMP_STUCK')){
    foreach($file in @('series.json','phases.json','measurements.json','physics_intervals.json','events.jsonl','result.json','m1_completed.zlib','m1_completed_index.json')){
        $a=Join-Path $Root ($case+'/case/'+$file)
        $b=Join-Path $Root ('REPEAT_'+$case+'/case/'+$file)
        $same=(Get-FileHash -LiteralPath $a -Algorithm SHA256).Hash -ceq (Get-FileHash -LiteralPath $b -Algorithm SHA256).Hash
        $repeatChecks[$case+'/'+$file]=$same
        if(-not $same){throw ('REPEAT_DRIFT '+$case+'/'+$file)}
    }
}
$coarse=$taskResults['LOAD_STEP'].payload
$medium=$taskResults['REFINE_50'].payload
$fine=$taskResults['REFINE_25'].payload
$convergence=[ordered]@{}
foreach($key in @('final_supply_c','final_return_c','final_flow_m3_s','final_dp_pa')){
    $x=[Math]::Abs($coarse.$key-$medium.$key);$y=[Math]::Abs($medium.$key-$fine.$key)
    $pass=($x -eq 0 -and $y -eq 0) -or ($y -lt $x)
    $convergence[$key]=@{coarse_medium_delta=$x;medium_fine_delta=$y;convergent=$pass;criterion='REFINEMENT_DIFFERENCE_SHRINKS_OR_EXACTLY_INVARIANT_NO_TUNED_TOLERANCE'}
    if(-not $pass){throw ('NUMERICAL_CONVERGENCE_NOT_ESTABLISHED '+$key)}
}
$classifications=[ordered]@{
    THERMAL_CAPACITY_LIMITATION='CONDITIONAL_ONLY: compare modeled supply with liquid limit; NOT equipment capacity certification'
    ACTUATOR_TRACKING_FAILURE=$taskResults['PUMP_STUCK'].payload.first_state_times_ns
    SENSOR_OR_OBSERVABILITY_FAILURE='NEGATIVE_TESTED; stale/invalid cannot earn tracking confirmation'
    CONTROL_RESPONSE_LIMITATION='PROPORTIONAL_RETURN_CONTROL_SENSITIVITY; no vendor PID or site performance claim'
    MODEL_OR_PARAMETER_UNCERTAINTY='UA/pump curve/volumes/control and protection assumptions; GPU die unmodeled; primary inlet prescribed'
}
$report=[ordered]@{schema='GB300-M1-SIX-RACK-MVP-RESULT-v1';status='INTEGRATION_MVP_PASS';source_commit=$SourceCommit;
    cases=@{LOAD_STEP=$coarse;PUMP_STUCK=$taskResults['PUMP_STUCK'].payload};repeat=$repeatChecks;convergence=$convergence;
    classifications=$classifications;C3_C_V5_RESULT='PRESERVE';NEW_INTEGRATED_SYSTEM_QUALIFICATION='NO';
    PRODUCTION_IMPLEMENTATION='NO';REAL_HARDWARE_CONTROL='NO';PHASE6='NO';hardware='CALIBRATION_REQUIRED'}
$json=ConvertTo-Json -InputObject $report -Depth 40
[IO.File]::WriteAllText((Join-Path $Root 'engineering_report.json'),$json,[Text.UTF8Encoding]::new($false))
function Plot-Series($rows,[string]$field,[string]$color,[double]$min,[double]$max){
    $points=foreach($r in $rows){
        $x=50+900*([double]$r.time_ns/120000000000)
        $v=[double]$r.$field
        if($field -in @('supply_k','return_k')){$v-=273.15}
        $y=250-200*($v-$min)/($max-$min)
        '{0},{1}' -f $x.ToString('F2',[cultureinfo]::InvariantCulture),$y.ToString('F2',[cultureinfo]::InvariantCulture)
    }
    return '<polyline fill="none" stroke="'+$color+'" stroke-width="2" points="'+($points -join ' ')+'"/>'
}
$sections=@()
foreach($case in @('LOAD_STEP','PUMP_STUCK')){
    $rows=Get-Content -LiteralPath (Join-Path $Root ($case+'/case/series.json')) -Raw|ConvertFrom-Json
    $panels=@()
    foreach($spec in @(
        @{title='Liquid supply / return degC';a='supply_k';b='return_k';min=30;max=80},
        @{title='Command / actual normalized speed';a='commanded_speed';b='actual_speed';min=0;max=1},
        @{title='Actual secondary flow m3/s';a='flow_m3_s';b='flow_m3_s';min=0;max=0.025},
        @{title='Actual pump differential pressure Pa';a='dp_pa';b='dp_pa';min=0;max=500000})){
        $svg='<svg viewBox="0 0 1000 290" role="img" aria-label="'+$spec.title+'"><rect width="1000" height="290" fill="#fff"/><path d="M50 30V250H950" fill="none" stroke="#777"/>'
        $svg+=Plot-Series $rows $spec.a '#1676b7' $spec.min $spec.max
        if($spec.a -cne $spec.b){$svg+=Plot-Series $rows $spec.b '#d25b16' $spec.min $spec.max}
        $svg+='<text x="50" y="22">'+$spec.title+'; blue='+$spec.a+' orange='+$spec.b+'</text><text x="50" y="275">0 s</text><text x="900" y="275">120 s</text><text x="0" y="45">'+$spec.max+'</text><text x="0" y="250">'+$spec.min+'</text></svg>'
        $panels+=$svg
    }
    $sections+='<h2>'+ $case +'</h2>'+($panels -join '')
}
$html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Six-rack engineering integration</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px;background:#f3f6f8;color:#152332}svg{width:100%;margin:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>六柜液冷—M1 闭环开发报告</h1><p>INTEGRATION_MVP_PASS，仅离线集成开发验证；不是新系统 C3-C、设备资格或 GPU 结温安全证明。</p><p>蓝线和橙线的变量名见各图；0–120秒。设备 UA、泵曲线、容积与控制参数为明确标注的敏感性假设。</p>'+($sections -join '')+'<h2>完整结果与限制</h2><pre>'+[Net.WebUtility]::HtmlEncode($json)+'</pre></html>'
[IO.File]::WriteAllText((Join-Path $Root 'engineering_report.html'),$html,[Text.UTF8Encoding]::new($false))
$records=foreach($f in Get-ChildItem -LiteralPath $Root -File -Recurse){
    @{path=[IO.Path]::GetRelativePath($Root,$f.FullName).Replace('\','/');bytes=$f.Length;raw_sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
[IO.File]::WriteAllText((Join-Path $Root 'artifact_hashes.json'),(ConvertTo-Json -InputObject @{source_commit=$SourceCommit;records=@($records)} -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Host 'INTEGRATION_MVP_PASS: raw evidence, repeat, convergence and Job cleanup verified; NOT C3 qualified'
