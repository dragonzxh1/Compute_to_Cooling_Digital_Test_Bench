# File-only causal witness; never imports candidate code or feeds a controller.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$base='D:/Github/c2c-evidence-review/memphis-control-path-v1/run39408912940'
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $base 'memphis-loop-raw-mesh-39408912940.zip'))
try{
 $e=$z.Entries|Where-Object FullName -match '/ORIGINAL_80/case/source_phases.json$'
 $s=$e.Open();try{$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}
 $r=[IO.StreamReader]::new($e.Open());try{$frames=$r.ReadToEnd()|ConvertFrom-Json}finally{$r.Dispose()}
 $eligible=@();$commands=0
 foreach($f in $frames){
  if($f.time_ns -lt $f.measurement.release_ns -or $f.measurement.release_ns -lt $f.measurement.sample_ns){throw 'FUTURE_MEASUREMENT'}
  if($f.request.source_tank -ceq 'B'){$commands++}
  if($f.time_ns -ge 120000000000 -and $f.time_ns -lt 1500000000000 -and $f.request.coordinator_state -ceq 'RUN' -and $f.safety.data.current_cold_return_confirmed){$eligible+=$f}
 }
 $max=($eligible|ForEach-Object {[double]$_.request.A_CONTIGUOUS_TT_LOWER_ESTIMATE_m3}|Measure-Object -Maximum).Maximum
 $budget=8.25+330/3600*(10+30)
 $v=@{schema='SAVED-PERMISSION-WITNESS-v1';run='39408912940';execution='3ee9f97f31f5f395e51c1a561b2a8aed8ba2c97d';case='ORIGINAL_80';raw_entry=$e.FullName;raw_sha256=$hash;window_s=@(120,1500);eligible_frames=$eligible.Count;first_eligible_s=$eligible[0].time_ns/1e9;last_eligible_s=$eligible[-1].time_ns/1e9;max_contiguous_A_estimate_m3=$max;registered_budget_m3=$budget;observation_budget_gap_m3=$budget-$max;B_commands=$commands;interpretation='CONTROL_ESTIMATE_BUDGET_GAP; NOT extra tank volume, hardware deficit or RC sizing; finite window only';method='Independent saved JSON arithmetic, no model execution'}
 [IO.File]::WriteAllText((Join-Path $base 'saved_permission_analysis.json'),($v|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false));$v|ConvertTo-Json -Depth 4
}finally{$z.Dispose()}
