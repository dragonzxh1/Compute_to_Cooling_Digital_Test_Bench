param([Parameter(Mandatory)][string]$RunId,[Parameter(Mandatory)][string]$Commit)
# Arithmetic on actual saved files only. No Python or forward model.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$base='D:/Github/c2c-evidence-review/memphis-loop-validation-v1/run'+$RunId
$api='repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$run=gh api ($api+'/actions/runs/'+$RunId)|ConvertFrom-Json
if($run.head_sha -cne $Commit){throw 'RUN_SOURCE_IDENTITY'}
$listing=gh api ($api+'/actions/runs/'+$RunId+'/artifacts?per_page=100')|ConvertFrom-Json
$evidence=@();$expectedNames=@("memphis-loop-raw-mesh-$RunId","memphis-loop-compact-mesh-$RunId")
foreach($a in $listing.artifacts|Where-Object {$_.name -in $expectedNames}){
 $p=Join-Path $base ($a.name+'.zip');if(('sha256:'+(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()) -cne $a.digest){throw 'ZIP_IDENTITY'}
 $evidence+=@{name=$a.name;sha256=$a.digest}
}
if($evidence.Count -ne 2){throw 'BOTH_MESH_ARCHIVES_REQUIRED'}
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $base ('memphis-loop-compact-mesh-'+$RunId+'.zip')))
try{
 $entry=@($z.Entries|Where-Object {$_.FullName -match '/SHARED_80/plot_data.json$'});if($entry.Count -ne 1){throw 'PLOT_IDENTITY'}
 $reader=[IO.StreamReader]::new($entry[0].Open());try{$points=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
 $entry=@($z.Entries|Where-Object {$_.FullName -match '/SHARED_80/loop_summary.json$'});$reader=[IO.StreamReader]::new($entry[0].Open());try{$summary=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
}finally{$z.Dispose()}
$targets=@(30,43,45,60,90,120,150,423,424,435,1800);$snapshots=@()
foreach($target in $targets){
 $p=@($points|Where-Object time_s -le $target|Sort-Object time_s|Select-Object -Last 1)
 if($p.Count){$snapshots+=@{requested_time_s=$target;actual_saved_time_s=$p[0].time_s;rack_C=$p[0].rack_C;primary_C=$p[0].primary_C;source_return_C=$p[0].source_return_C;source_m3_h=$p[0].source_m3_h;load_m3_h=$p[0].load_m3_h;A_cold_m3=$p[0].cold_A_m3;B_cold_m3=$p[0].cold_B_m3;source_tank=$p[0].source_tank;source_path=$p[0].source_path}}
}
$z=[IO.Compression.ZipFile]::OpenRead((Join-Path $base ('memphis-loop-raw-mesh-'+$RunId+'.zip')))
$ledger=@()
try{
 $entry=@($z.Entries|Where-Object {$_.FullName -match '/SHARED_80/tank_port_ledger.csv$'});if($entry.Count -ne 1){throw 'LEDGER_IDENTITY'}
 $reader=[IO.StreamReader]::new($entry[0].Open())
 try{
  $headers=$reader.ReadLine().Split(',');$ix=@{};for($i=0;$i -lt $headers.Count;$i++){$ix[$headers[$i]]=$i}
  while(-not $reader.EndOfStream){
   $v=$reader.ReadLine().Split(',');if($v[$ix.tank] -cne 'A'){continue}
   $t=[double]::Parse($v[$ix.time_s],[Globalization.CultureInfo]::InvariantCulture)
   if(@($targets|Where-Object {[Math]::Abs($_-$t) -lt .000001}).Count){
    $row=[ordered]@{time_s=$t}
    foreach($key in @('bottom_C','top_C','load_W','source_W','cumulative_load_J','cumulative_source_J','cumulative_ambient_J','cumulative_delta_U_J')){$row[$key]=[double]::Parse($v[$ix[$key]],[Globalization.CultureInfo]::InvariantCulture)}
    $ledger+=,$row
   }
  }
 }finally{$reader.Dispose()}
}finally{$z.Dispose()}
$out=[ordered]@{schema='SAVED_SOURCE_ADMISSION_FILE_ANALYSIS_v1';run=$RunId;execution_commit=$Commit;case='SHARED_80';official_archives=$evidence;
 snapshots=$snapshots;A_tank_ledger=$ledger;events=$summary.events;
 actual_source_flow_during_restoration_m3_h=$summary.proposal_checks.A_restoration_min_source_m3_h;
 source_qualified_cold_delay_s=$summary.source_cold_delay_s;
 B_recharge_actually_exercised=@($summary.events|Where-Object reason -match 'ALLOW_SEGMENT').Count -gt 0;
 controller_gate='New conservative17TT screen and complete absence budget; NOT a customer-approved readiness definition';
 physical_assumptions='Standby line48.29C and ZERO source rejection until54s after new flow begins; not an OEM startup curve';
 conclusion_scope='File-level causal clues only, not proof original customer design fails or RC is necessary';engineering='MEMPHIS_ENGINEERING_NOT_APPROVED'}
$path=Join-Path $base 'saved_source_admission_analysis.json'
if(Test-Path $path){throw 'PRESERVE_FILE_ANALYSIS_VERSION'}
[IO.File]::WriteAllText($path,($out|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
$out|Select-Object case,actual_source_flow_during_restoration_m3_h,source_qualified_cold_delay_s,B_recharge_actually_exercised,snapshots|ConvertTo-Json -Depth 7
