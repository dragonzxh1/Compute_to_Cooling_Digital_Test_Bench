param([Parameter(Mandatory)][string]$Delivery)
# Post-exit arithmetic on already persisted evidence only; NO forward simulation.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$utf=[Text.UTF8Encoding]::new($false);$actual=Get-Content (Join-Path $Delivery 'ACTUAL_AUDIT_RESULTS.json') -Raw|ConvertFrom-Json
$result=[ordered]@{method='PURE_PERSISTED_CSV_AND_PROFILE_ARITHMETIC_NO_MODEL_EXECUTION';tanks=[ordered]@{};numerics=@()}
foreach($name in @('A','B')){
 $file=Join-Path $Delivery $(if($name -eq 'A'){'05_A_TANK_ENERGY_LEDGER.csv'}else{'06_B_TANK_ENERGY_LEDGER.csv'})
 $load=0.;$source=0.;$ambient=0.;$rows=0;$last=$null
 Import-Csv -LiteralPath $file|ForEach-Object{$load+=[double]$_.load_net_heat_W*[double]$_.dt_s;$source+=[double]$_.source_net_heat_W*[double]$_.dt_s;$ambient+=[double]$_.ambient_W*[double]$_.dt_s;$rows++;$last=$_}
 $delta=[double]$last.cumulative_delta_U_J
 if([Math]::Abs($load+$source+$ambient-$delta) -gt .1){throw ('PERSISTED_ATTRIBUTION_IMBALANCE '+$name)}
 $old=$actual.BASELINE_EXACT.initial_profiles.PSObject.Properties[$name].Value
 $new=$actual.BASELINE_EXACT.keyframes[-1].profile.PSObject.Properties[$name].Value
 $layers=for($i=0;$i -lt $new.Count;$i++){
  [pscustomobject]@{layer_bottom_zero_based=$i;volume_m3=15/$new.Count;initial_C=[double]$old[$i]-273.15;final_C=[double]$new[$i]-273.15;
  delta_U_MJ=(1009*4000*15/$new.Count)*([double]$new[$i]-[double]$old[$i])/1e6;qualifies_threshold=([double]$new[$i] -le 314.5948)}
 }
 $layers|Export-Csv -LiteralPath (Join-Path $Delivery ($name+'_LAYER_ENERGY_CHANGES.csv')) -NoTypeInformation -Encoding utf8NoBOM
 $result.tanks[$name]=@{rows=$rows;load_loop_net_MJ=$load/1e6;source_loop_net_MJ=$source/1e6;ambient_MJ=$ambient/1e6;stored_delta_MJ=$delta/1e6;
   attribution_residual_J=$load+$source+$ambient-$delta;classification='Net port enthalpy; pump andHX already inside port temperature; do not add twice'}
}
$frame=$actual.BASELINE_EXACT.keyframes[-1];$t=$frame.tanks.A;$ql=[double]$t.load_m3_s;$qs=[double]$t.source_m3_s
if($ql -gt $qs -and $ql -gt 0){
 $steady=($qs*[double]$t.source_in_k+($ql-$qs)*[double]$t.old_k[1])/$ql
 $result.bottom_cell_identity=@{actual_start_C=[double]$t.old_k[0]-273.15;source_return_C=[double]$t.source_in_k-273.15;next_layer_C=[double]$t.old_k[1]-273.15;
 source_m3_h=$qs*3600;transfer_m3_h=$ql*3600;zero_rate_mixing_temperature_C=$steady-273.15;
 difference_from_current_K=$steady-[double]$t.old_k[0];scope='Instantaneous zero-rate solution excluding tinyambient term, not a future-temperature prediction or real diffuser calibration'}
}
foreach($id in @('MESH20','MESH40','BASELINE_EXACT','MESH160','DT005')){
 $a=$actual.PSObject.Properties[$id].Value;$profile=$a.keyframes[-1].profile.A
 $firstColdToWarm=$null
 for($i=0;$i -lt $profile.Count-1;$i++){
  if([double]$profile[$i] -le 314.5948 -and [double]$profile[$i+1] -gt 314.5948){
   $f=(314.5948-[double]$profile[$i])/([double]$profile[$i+1]-[double]$profile[$i]);$firstColdToWarm=($i+.5+$f)/$profile.Count;break
  }
 }
 $result.numerics+=@{case=$id;layers=$profile.Count;cell_volume_m3=15/$profile.Count;dt_s=$a.parameters.dt_s;
 cold_threshold_crossing_height_fraction=$firstColdToWarm;crossing_scope='Linear interpolation of cellcenter temperatures; not measured thermocline geometry';
 actual_A_discharge=@($a.final_challenge|Where-Object tank -eq 'A');volume_precision='CELL_COUNT_QUANTIZED';real_mixing='NUMERICAL_INCOMPLETE_CALIBRATION_REQUIRED'}
}
[IO.File]::WriteAllText((Join-Path $Delivery 'PERSISTED_ENERGY_ATTRIBUTION.json'),($result|ConvertTo-Json -Depth 20),$utf)
$result|ConvertTo-Json -Depth 12
