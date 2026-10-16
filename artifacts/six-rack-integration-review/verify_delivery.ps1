param([Parameter(Mandatory)][string]$Root,[Parameter(Mandatory)][string]$ExpectedCommit)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
# Pure-file independent readback. No Python, model or native child is launched.
$rootPath=(Resolve-Path -LiteralPath $Root).Path
$inventory=Get-Content -LiteralPath (Join-Path $rootPath 'artifact_hashes.json') -Raw|ConvertFrom-Json
if($inventory.source_commit -cne $ExpectedCommit){throw 'ARTIFACT_SOURCE_COMMIT_MISMATCH'}
$count=0
foreach($b in $inventory.records){
    $path=[IO.Path]::GetFullPath((Join-Path $rootPath $b.path))
    if(-not $path.StartsWith($rootPath+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'ARTIFACT_PATH_ESCAPE'}
    if((Get-Item -LiteralPath $path).Length -ne $b.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.raw_sha256){throw ('ARTIFACT_RAW_DRIFT '+$b.path)}
    $count++
}
$caseAudits=@{}
foreach($case in @('LOAD_STEP','PUMP_STUCK')){
    $base=Join-Path $rootPath ($case+'/case')
    $input=Get-Content -LiteralPath (Join-Path $base 'input.json') -Raw|ConvertFrom-Json
    $series=Get-Content -LiteralPath (Join-Path $base 'series.json') -Raw|ConvertFrom-Json
    $phases=Get-Content -LiteralPath (Join-Path $base 'phases.json') -Raw|ConvertFrom-Json
    $measurements=Get-Content -LiteralPath (Join-Path $base 'measurements.json') -Raw|ConvertFrom-Json
    $intervals=Get-Content -LiteralPath (Join-Path $base 'physics_intervals.json') -Raw|ConvertFrom-Json
    $c=$input.config
    $bySample=@{};$byTime=@{};$seen=@{}
    foreach($s in $series){$byTime[[string]$s.time_ns]=$s}
    foreach($m in $measurements){
        if($m.available_ns -ne $m.sample_ns+$c.sensor_delay_ns){throw 'SENSOR_DELAY_DRIFT'}
        $truth=$byTime[[string]$m.sample_ns]
        if($m.pump_speed -ne $truth.actual_speed -or $m.dp_pa -ne $truth.dp_pa -or $m.flow_m3_s -ne $truth.flow_m3_s){throw 'MEASUREMENT_SAMPLE_SOURCE_MISMATCH'}
        $bySample[$m.measurement_record_id]=$m
    }
    $previous=$null
    foreach($f in $phases){
        $pre=$f.PRE;$safety=$f.SAFETY;$plc=$f.PLC;$post=$f.POST;$m=$pre.measurement
        if($m.sample_ns -gt $m.release_ns -or $m.release_ns -gt $f.time_ns -or $seen.ContainsKey($m.measurement_record_id)){throw 'FUTURE_OR_DUPLICATE_MEASUREMENT'}
        $seen[$m.measurement_record_id]=$true
        $arrived=$bySample[$m.measurement_record_id]
        if($m.measured_speed -ne $arrived.pump_speed -or $m.sample_ns -ne $arrived.sample_ns -or $m.release_ns -ne $arrived.available_ns){throw 'PRE_MEASUREMENT_BINDING_DRIFT'}
        if($null -ne $previous -and ($pre.old_command.value -ne $previous.command -or $pre.old_command.issue_ns -ne $previous.issue_ns)){throw 'PRE_DID_NOT_USE_PREVIOUS_COMMAND'}
        if($safety.pre_record_id -cne $pre.record_id -or $safety.pre_digest -cne $f.immutable_pre_digest -or
           $plc.safety_id -cne $safety.record_id -or $plc.safety_digest -cne $f.immutable_safety_digest -or
           $post.pre_id -cne $pre.record_id -or $post.plc_id -cne $plc.record_id){throw 'PHASE_CAUSAL_BINDING_DRIFT'}
        if($plc.issue_ns -gt $f.time_ns -or $f.actuator_command.producer_module -cne 'PLC' -or
           $f.actuator_command.applied_command_before_actuator_dynamics -ne $plc.command -or
           $plc.command -lt $f.envelope.minimum_speed -or $plc.command -gt $f.envelope.maximum_speed){throw 'COMMAND_OWNER_OR_ENVELOPE_VIOLATION'}
        $request=[Math]::Min(.9,[Math]::Max(.3,$c.initial_speed+$c.feedback_gain_fraction_per_k*(($arrived.rack_return_k|Measure-Object -Maximum).Maximum-$c.return_target_k)))
        if([Math]::Abs($request-$f.controller_request) -gt 32*2.220446049250313e-16*[Math]::Max(1,[Math]::Abs($request))){throw 'CONTROLLER_NOT_ARRIVED_OBSERVATION_DRIVEN'}
        if($pre.state -ceq 'TRACKING_FAULT_CONFIRMED' -and $safety.severity -cne 'FAULT'){throw 'CONFIRMED_NOT_FAULT'}
        $previous=$plc
    }
    foreach($s in $series){
        $q=$c.design_secondary_flow_m3_s*$s.actual_speed/$c.design_speed
        $dp=$c.design_secondary_dp_pa*[Math]::Pow($s.actual_speed/$c.design_speed,2)
        # Independent analytic affinity-law check; 32 double rounding ULPs at
        # each scale, not the model's stored residual or a thermal-success gate.
        if([Math]::Abs($q-$s.flow_m3_s) -gt 32*2.220446049250313e-16*[Math]::Max([Math]::Abs($q),1e-300) -or
           [Math]::Abs($dp-$s.dp_pa) -gt 32*2.220446049250313e-16*[Math]::Max([Math]::Abs($dp),1e-300)){throw 'HYDRAULIC_NOT_ACTUAL_SPEED_DRIVEN'}
        if($case -ceq 'PUMP_STUCK' -and $s.time_ns -ge $c.silent_stuck_at_ns){
            $held=$byTime[[string]$c.silent_stuck_at_ns]
            if($s.actual_speed -ne $held.actual_speed -or $s.flow_m3_s -ne $held.flow_m3_s -or $s.dp_pa -ne $held.dp_pa){throw 'STUCK_FLOW_OVERRIDDEN'}
        }
    }
    $liquid=0.;$it=0.;$hx=0.
    foreach($p in $intervals){
        $event=$c.load_profile[0]
        foreach($e in $c.load_profile){if($e.time_ns -le $p.start_ns){$event=$e}}
        if((ConvertTo-Json -InputObject @($p.rack_it_w) -Compress) -cne (ConvertTo-Json -InputObject @($event.rack_it_w) -Compress)){throw 'LOAD_STEP_TIME_OR_SOURCE_DRIFT'}
        $seconds=($p.end_ns-$p.start_ns)/1e9
        foreach($w in $p.rack_it_w){$it+=$w*$seconds;$liquid+=$w*$c.liquid_fraction*$seconds}
        $hx+=$p.hx_to_primary_w*$seconds
    }
    $caseResult=Get-Content -LiteralPath (Join-Path $base 'result.json') -Raw|ConvertFrom-Json
    $l=$caseResult.ledger
    if([Math]::Abs($liquid-$l.liquid_load_j) -gt $l.roundoff_bound_j -or [Math]::Abs($it-$l.it_j) -gt $l.roundoff_bound_j -or
       [Math]::Abs($hx-$l.hx_to_primary_j) -gt $l.roundoff_bound_j -or
       [Math]::Abs($l.stored_change_j-$liquid-$l.pump_liquid_j+$hx) -gt $l.roundoff_bound_j){throw 'INDEPENDENT_ENERGY_READBACK_FAILED'}
    $caseAudits[$case]=@{phase_count=$phases.Count;measurement_count=$measurements.Count;physics_intervals=$intervals.Count;
        causal_timing=$true;command_ownership=$true;actual_hydraulics=$true;independent_heat_ledger=$true;no_truth_controller_input=$true}
}
@{status='INDEPENDENT_PURE_FILE_REVIEW_PASS';source_commit=$ExpectedCommit;raw_files_verified=$count;cases=$caseAudits}|ConvertTo-Json -Depth 10
