param([Parameter(Mandatory)][string]$RunId)
# Bounded UTF8/JsonDocument decoding only. No physical model or Python execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$ev='D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$RunId
function Hash-Entry($e){$s=$e.Open();try{return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}}
function Forward-Result($z,$entry){$e=$z.GetEntry($entry.FullName.Replace('/case/source_phases.json','/forward_result.json'));if(-not $e -or $e.Length -gt 2000000){throw 'EXACT_FORWARD_RESULT'};$rd=[IO.StreamReader]::new($e.Open());try{return $rd.ReadToEnd()|ConvertFrom-Json}finally{$rd.Dispose()}}
function Trace-Entry($z,[string]$id){$a=@($z.Entries|Where-Object FullName -match ('/'+$id+'/case/source_phases.json$'));if($a.Count -ne 1 -or $a[0].Length -gt 10000000){throw 'BOUNDED_EXACT_TRACE'};return $a[0]}
$records=@();$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $ev ('memphis-closure-raw-scenarios-'+$RunId+'.zip')))
try{foreach($id in @('valves__A_demand_no_stuck','valves__A_demand_stuck')){
 $e=Trace-Entry $z $id;$r=Forward-Result $z $e;$hash=Hash-Entry $e
 if($hash -cne $r.raw_sha256.'source_phases.json'){throw 'REGISTERED_TRACE_SHA'}
 $s=$e.Open();try{$doc=[Text.Json.JsonDocument]::Parse($s)}finally{$s.Dispose()}
 $count=0;$requestedB=0;$nonresponse=0;$firstRequest=$null;$firstActualLoadB=$null;$firstActualSourceB=$null;$minimum=[double]::PositiveInfinity
 try{foreach($f in $doc.RootElement.EnumerateArray()){
  $count++;$now=$f.GetProperty('time_ns').GetInt64();$m=$f.GetProperty('measurement');$q=$f.GetProperty('request');$issued=$f.GetProperty('PLC').GetProperty('data').GetProperty('request')
  if($m.GetProperty('sample_ns').GetInt64() -gt $m.GetProperty('release_ns').GetInt64() -or $m.GetProperty('release_ns').GetInt64() -gt $now){throw 'FUTURE_OBSERVATION'}
  foreach($key in @('load_tank','source_tank')){if($q.GetProperty($key).GetString() -cne $issued.GetProperty($key).GetString()){throw 'REQUEST_ISSUED_MISMATCH'}}
  $load=$m.GetProperty('load_selector').GetString();$source=$m.GetProperty('source_tank').GetString()
  $minimum=[Math]::Min($minimum,$m.GetProperty('primary_load_flow_m3_s').GetDouble()*3600)
  if($q.GetProperty('load_tank').GetString() -ceq 'B'){$requestedB++;if($null -eq $firstRequest){$firstRequest=$now/1e9};if($load -ceq 'A'){$nonresponse++}}
  if($load -ceq 'B' -and $null -eq $firstActualLoadB){$firstActualLoadB=$now/1e9}
  if($source -ceq 'B' -and $null -eq $firstActualSourceB){$firstActualSourceB=$now/1e9}
 }}finally{$doc.Dispose()}
 if($requestedB -eq 0 -or $null -eq $firstActualSourceB){throw 'REAL_B_DEMAND_AND_SOURCE_FOLLOW_REQUIRED'}
 if($id -ceq 'valves__A_demand_stuck'){if($nonresponse -eq 0 -or $null -ne $firstActualLoadB){throw 'STUCK_VALVE_NOT_PROVEN'}}elseif($null -eq $firstActualLoadB){throw 'UNSTUCK_LOAD_TRANSFER_NOT_PROVEN'}
 $records+=@{id=$id;source_phases_raw_sha256=$hash;frames=$count;issued_B_requests=$requestedB;nonresponse_frames=$nonresponse;first_B_request_s=$firstRequest;first_actual_load_B_s=$firstActualLoadB;first_actual_source_B_s=$firstActualSourceB;minimum_published_load_m3_h=$minimum;minimum_all_physical_steps_load_m3_h=$r.minimum_load_m3_h;grades=$r.grades;hardware_PLC='NOT_CLAIMED'}
}}finally{$z.Dispose()}
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $ev ('memphis-closure-raw-precool-'+$RunId+'.zip')))
try{
 $e=Trace-Entry $z 'readiness_negatives__source_publication_loss';$r=Forward-Result $z $e;$hash=Hash-Entry $e
 if($hash -cne $r.raw_sha256.'source_phases.json'){throw 'DROPOUT_TRACE_SHA'}
 $s=$e.Open();try{$doc=[Text.Json.JsonDocument]::Parse($s)}finally{$s.Dispose()}
 $firstStale=$null;$firstStaleStop=$null;$lastFrame=$null;$samples=[Collections.Generic.HashSet[long]]::new()
 try{foreach($f in $doc.RootElement.EnumerateArray()){
  $now=$f.GetProperty('time_ns').GetInt64();$m=$f.GetProperty('measurement');$sample=$m.GetProperty('sample_ns').GetInt64();$null=$samples.Add($sample)
  if($sample -ge 40000000000 -or $m.GetProperty('release_ns').GetInt64() -gt $now){throw 'DROPOUT_NOT_REAL_OR_FUTURE_DATA'}
  $stale=@($f.GetProperty('safety').GetProperty('data').GetProperty('codes').EnumerateArray()|ForEach-Object {$_.GetString()}) -contains 'SOURCE_SENSOR_STALE'
  if($stale -and $null -eq $firstStale){$firstStale=$now/1e9}
  if($stale -and -not $f.GetProperty('request').GetProperty('source_enable').GetBoolean() -and $null -eq $firstStaleStop){$firstStaleStop=$now/1e9}
  $lastFrame=$now/1e9
 }}finally{$doc.Dispose()}
 if($null -eq $firstStale -or $null -eq $firstStaleStop -or $lastFrame -lt 239){throw 'CLOCK_FAIL_CLOSED_NOT_PERSISTED'}
 $records+=@{id=$r.id;source_phases_raw_sha256=$hash;last_actual_sample_s=(@($samples)|Measure-Object -Maximum).Maximum/1e9;distinct_published_samples_used=$samples.Count;last_protection_evaluation_s=$lastFrame;first_stale_s=$firstStale;first_stale_stop_permission_s=$firstStaleStop;status='PUBLISHED_SAMPLE_LOSS_AND_CLOCK_FAIL_CLOSED_VERIFIED';not_extra_M1_credit=$true}
}finally{$z.Dispose()}
$proof=@{run=[long]$RunId;method='Independent bounded JsonDocument decoding of immutable original traces; no model execution';cases=$records;engineering='MEMPHIS_ENGINEERING_NOT_APPROVED';hardware=$false}
$path=Join-Path $ev 'independent_event_boundary_file_proof.json';[IO.File]::WriteAllText($path,($proof|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
$records|ConvertTo-Json -Depth 8
