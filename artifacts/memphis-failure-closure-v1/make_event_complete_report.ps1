param([Parameter(Mandatory)][string]$RunId)
# Streaming immutable physical JSON to visualization points; NOT a model run.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$delivery=Join-Path $repo 'artifacts/memphis-failure-closure-v1-delivery';$ev='D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run'+$RunId
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $ev ('memphis-closure-raw-scenarios-'+$RunId+'.zip')))
$csv=[Collections.Generic.List[object]]::new();$provenance=@();$injections=[Text.StringBuilder]::new()
$enumType=[Collections.Generic.IAsyncEnumerable[Text.Json.JsonElement]];$iterType=[Collections.Generic.IAsyncEnumerator[Text.Json.JsonElement]]
try{foreach($id in @('valves__A_demand_no_stuck','valves__A_demand_stuck')){
 $a=@($z.Entries|Where-Object FullName -match ('/'+$id+'/case/physics.json$'));if($a.Count -ne 1){throw 'EXACT_PHYSICAL_TRACE'};$e=$a[0]
 $s=$e.Open();try{$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}
 $fe=$z.GetEntry($e.FullName.Replace('/case/physics.json','/forward_result.json'));$rd=[IO.StreamReader]::new($fe.Open());try{$forward=$rd.ReadToEnd()|ConvertFrom-Json}finally{$rd.Dispose()}
 if($hash -cne $forward.raw_sha256.'physics.json'){throw 'REGISTERED_PHYSICS_SHA'}
 $s=$e.Open();$options=[Text.Json.JsonSerializerOptions]::new();$options.DefaultBufferSize=16384
 $enumerable=[Text.Json.JsonSerializer]::DeserializeAsyncEnumerable[Text.Json.JsonElement]($s,$options,[Threading.CancellationToken]::None)
 $iterator=$enumType.GetMethod('GetAsyncEnumerator').Invoke($enumerable,@([Threading.CancellationToken]::None))
 $move=$iterType.GetMethod('MoveNextAsync');$current=$iterType.GetProperty('Current');$points=[Collections.Generic.List[object]]::new();$minimum=[double]::PositiveInfinity;$minimumTime=$null;$firstBCold=$null
 try{while($move.Invoke($iterator,@()).AsTask().GetAwaiter().GetResult()){
  $r=$current.GetValue($iterator);$maximum=[double]::NegativeInfinity
  foreach($unit in $r.GetProperty('unit_records').EnumerateArray()){$temps=$unit.GetProperty('new_k');for($j=1;$j -le 6;$j++){$maximum=[Math]::Max($maximum,$temps[$j].GetDouble()-273.15)}}
  $t=$r.GetProperty('end_ns').GetInt64()/1e9;$flow=$r.GetProperty('load_flow_m3_h').GetDouble()
  $path=$r.GetProperty('source_path').GetString()
  if($null -eq $firstBCold -and $r.GetProperty('source_tank').GetString() -ceq 'B' -and $r.GetProperty('source_available').GetProperty($path).GetBoolean() -and $r.GetProperty('source_flow_m3_h').GetDouble() -ge 330-1e-8 -and $r.GetProperty('source_return_k').GetDouble() -le 314.5948){$firstBCold=$t}
  if($flow -lt $minimum){$minimum=$flow;$minimumTime=$t}
  $p=[ordered]@{time_s=$t;rack_C=$maximum;primary_C=$r.GetProperty('primary_inlet_c').GetDouble();load_m3_h=$flow;source_m3_h=$r.GetProperty('source_flow_m3_h').GetDouble();recharge_m3_h=$r.GetProperty('recharge_flow_m3_h').GetDouble();cold_A_m3=$r.GetProperty('tank_A_cold_m3').GetDouble();cold_B_m3=$r.GetProperty('tank_B_cold_m3').GetDouble()}
  $points.Add($p);$csv.Add([PSCustomObject]([ordered]@{id=$id;time_s=$t;rack_C=$maximum;primary_C=$p.primary_C;load_m3_h=$flow;source_m3_h=$p.source_m3_h;cold_A_m3=$p.cold_A_m3;cold_B_m3=$p.cold_B_m3}))
 }}finally{$null=[IAsyncDisposable].GetMethod('DisposeAsync').Invoke($iterator,@()).AsTask().GetAwaiter().GetResult();$s.Dispose()}
 if($points.Count -ne [int]($forward.parameters.seconds/$forward.parameters.dt_s) -or [Math]::Abs($minimum-$forward.minimum_load_m3_h) -gt 1e-9){throw 'FULL_INTERVAL_OR_EXTREMUM_COVERAGE'}
 $null=$injections.Append('data.series['+($id|ConvertTo-Json -Compress)+']='+($points.ToArray()|ConvertTo-Json -Depth 8 -Compress)+';')
 if($null -eq $firstBCold -or $firstBCold-$forward.parameters.fault_at_s -gt 90){throw 'ACTUAL_B_PATH_COLD_RECOVERY_NOT_PROVEN'}
 $bDelay=$firstBCold-$forward.parameters.fault_at_s
 $null=$injections.Append('data.results['+($id|ConvertTo-Json -Compress)+'].derived_B_path_cold_return_s='+($firstBCold|ConvertTo-Json -Compress)+';data.results['+($id|ConvertTo-Json -Compress)+'].derived_B_path_cold_return_delay_s='+($bDelay|ConvertTo-Json -Compress)+';')
 $provenance+=@{id=$id;physical_rows=$points.Count;physical_raw_sha256=$hash;minimum_load_m3_h=$minimum;minimum_time_s=$minimumTime;first_actual_B_path_cold_s=$firstBCold;actual_B_path_cold_delay_s=$bDelay;original_any_path_cold_delay_s=$forward.cold_return_delay_s;method='Every saved physical interval; no interpolation or favorable sampling'}
}}finally{$z.Dispose()}
$csv.ToArray()|Export-Csv -LiteralPath (Join-Path $delivery 'critical_event_points.csv') -NoTypeInformation -Encoding utf8BOM
$original=Join-Path $delivery 'engineering_report.html';$html=[IO.File]::ReadAllText($original)
$marker=';const select=document.getElementById';if(-not $html.Contains($marker)){throw 'EXACT_RENDERER_MARKER'}
$html=$html.Replace($marker,(';'+$injections.ToString()+'const select=document.getElementById'))
$html=$html.Replace('cold_delay_s:r.cold_return_delay_s,excitation:r.excitation','any_path_first_cold_delay_s:r.cold_return_delay_s,B_path_cold_return_s:r.derived_B_path_cold_return_s,B_path_cold_return_delay_s:r.derived_B_path_cold_return_delay_s,excitation:r.excitation')
$html=$html.Replace('lo-=pad;hi+=pad;let xmax=',"lo-=pad;if(label.includes('m³/h')||label.includes('库存'))lo=Math.max(0,lo);hi+=pad;let xmax=")
$html=$html.Replace('A/B真实阈值冷库存 m³','A/B模型真值冷库存 m³')
$note='<p class="warning">事件增强版：A隔离无卡阀/真实卡阀两例展示每0.1秒原始物理步，保留瞬时停流；其他工况曲线仍为1秒抽样，全部判据与min/max均用完整物理步。any_path是任意可用源首次合格，不等于切B完成；B路径冷返另用全步数据核对。原始官方HTML未改。<a href="critical_event_points.csv">下载两例全步数据</a></p>'
$html=$html.Replace('<h2>实际执行场景</h2>',$note+'<h2>实际执行场景</h2>')
$dest=Join-Path $delivery 'engineering_report_event_complete.html';[IO.File]::WriteAllText($dest,$html,[Text.UTF8Encoding]::new($false))
$proof=@{run=[long]$RunId;transformation='EVENT_COMPLETE_TWO_VALVE_CASES_v1';renderer_source_raw_sha256=(Get-FileHash $PSCommandPath).Hash.ToLowerInvariant();official_html_sha256=(Get-FileHash $original).Hash.ToLowerInvariant();derived_html_sha256=(Get-FileHash $dest).Hash.ToLowerInvariant();no_model_rerun=$true;cases=$provenance;engineering_approval=$false}
[IO.File]::WriteAllText((Join-Path $delivery 'critical_plot_provenance.json'),($proof|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
$provenance|ConvertTo-Json -Depth 8
