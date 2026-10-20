param([Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$Commit)
# Offline saved-file analysis only; never a controller input or model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$base='D:/Github/c2c-evidence-review/memphis-control-path-v1/run'+$RunId
$listing=Get-Content -LiteralPath (Join-Path $base 'official_artifacts.json') -Raw|ConvertFrom-Json
$output=@()
foreach($a in $listing.artifacts|Where-Object name -like 'memphis-loop-raw-*'){
 $path=Join-Path $base ($a.name+'.zip')
 if(('sha256:'+(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()) -cne $a.digest){throw 'OFFICIAL_DIGEST'}
 $z=[IO.Compression.ZipFile]::OpenRead($path)
 try{foreach($e in $z.Entries|Where-Object FullName -match '/loop_summary.json$'){
  $rd=[IO.StreamReader]::new($e.Open());try{$c=$rd.ReadToEnd()|ConvertFrom-Json}finally{$rd.Dispose()}
  if($c.source_commit -cne $Commit){throw 'SOURCE_IDENTITY'}
  $prefix=$e.FullName.Substring(0,$e.FullName.Length-'loop_summary.json'.Length)
  $csv=$z.GetEntry($prefix+'case/physical_path.csv');if(-not $csv){throw 'PHYSICAL_PATH_MISSING'}
  $rd=[IO.StreamReader]::new($csv.Open());try{$rows=@($rd.ReadToEnd()|ConvertFrom-Csv)}finally{$rd.Dispose()}
  $segments=@($c.events|Where-Object reason -eq 'MEASURED_CONTIGUOUS_A_AND_WHOLE_ABSENCE_BUDGET_ALLOW_SEGMENT_NOT_READY_CLAIM')
  $intervals=@()
  for($i=0;$i -lt $segments.Count;$i++){
   $start=$segments[$i].time_ns/1e9
   $limit=if($i+1 -lt $segments.Count){$segments[$i+1].time_ns/1e9}else{[double]$c.parameters.seconds}
   $slice=@($rows|Where-Object {[double]$_.time_s -ge $start -and [double]$_.time_s -le $limit})
   $b=@($slice|Where-Object source_tank -eq B|Select-Object -First 1)
   $returned=if($b.Count){@($slice|Where-Object {[double]$_.time_s -gt [double]$b[0].time_s -and $_.source_tank -eq 'A' -and [double]$_.source_m3_h -ge 329.99999999 -and [double]$_.source_return_C -le 41.4448}|Select-Object -First 1)}else{@()}
   $end=if($returned.Count){[double]$returned[0].time_s}else{$null}
   $within=@($slice|Where-Object {$null -eq $end -or [double]$_.time_s -le $end})
   $intervals+=@{requested_stop_A_s=$start;first_actual_B_selection_s=if($b.Count){[double]$b[0].time_s}else{$null};
    first_qualified_A_return_s=$end;full_absence_until_cold_return_s=if($null -ne $end){$end-$start}else{$null};
    A_cold_at_request_m3=if($within.Count){[double]$within[0].cold_A_m3}else{$null};
    minimum_A_cold_m3=if($within.Count){($within|ForEach-Object {[double]$_.cold_A_m3}|Measure-Object -Minimum).Minimum}else{$null};
    status=if($null -ne $end){'OBSERVED_COMPLETE_ABSENCE_WINDOW'}else{'NO_QUALIFIED_RETURN_WITHIN_REGISTERED_WINDOW'}}
  }
  $output+=@{id=$c.id;source=$Commit;selector_B_segments_scope='Original control_path.segments only covers actual selectorB; excludes outbound stop and final A rebuild';full_absence_windows=$intervals}
 }}finally{$z.Dispose()}
}
$dest=Join-Path $base 'saved_full_absence_analysis.json'
if(Test-Path -LiteralPath $dest){throw 'PRESERVE_PRIOR_ANALYSIS'}
[IO.File]::WriteAllText($dest,(@{schema='SAVED-PHYSICAL-ABSENCE-FILE-ANALYSIS-v1';run=$RunId;execution=$Commit;method='Official ZIP digest checked; actual saved PLC event and physical CSV only; no local model';cases=$output}|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
$dest
