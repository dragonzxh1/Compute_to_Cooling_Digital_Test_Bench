# Bounded pure-file review of ORIGINAL13 issued requests, not model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$path='D:/Github/c2c-evidence-review/memphis-inverse-sizing-v1/run39136524640/memphis-inverse-raw-robust-39136524640.zip'
if((Get-FileHash $path).Hash.ToLowerInvariant() -cne '6103ea42e1b0746991c021a95a664fe212805d0e0e654a23da6785fa529f1e55'){throw 'ORIGINAL_OFFICIAL_ZIP'}
$z=[IO.Compression.ZipFile]::OpenRead($path);$records=@()
try{foreach($id in @('ROBUST_B15_13','ROBUST_C20_13')){
 $e=@($z.Entries|Where-Object FullName -match ('/'+$id+'/case/source_phases.json$'));if($e.Count -ne 1 -or $e[0].Length -gt 4000000){throw 'BOUNDED_EXACT_TRACE_REQUIRED'}
 $e=$e[0];$s=$e.Open();try{$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($s)).ToLowerInvariant()}finally{$s.Dispose()}
 $forward=$e.FullName.Replace('/case/source_phases.json','/forward_result.json');$rd=[IO.StreamReader]::new($z.GetEntry($forward).Open());try{$r=$rd.ReadToEnd()|ConvertFrom-Json}finally{$rd.Dispose()}
 if($hash -cne $r.raw_hashes.'source_phases.json'){throw 'ORIGINAL_REGISTERED_TRACE_SHA'}
 $s=$e.Open();try{$doc=[Text.Json.JsonDocument]::Parse($s)}finally{$s.Dispose()}
 $count=0;$demand=0
 try{foreach($f in $doc.RootElement.EnumerateArray()){
  $count++;$req=$f.GetProperty('request').GetProperty('load_tank').GetString()
  $issued=$f.GetProperty('PLC').GetProperty('data').GetProperty('request').GetProperty('load_tank').GetString()
  if($req -cne $issued){throw 'REQUEST_ISSUED_MISMATCH'};if($issued -ceq 'B'){$demand++}
 }}finally{$doc.Dispose()}
 if($demand -ne 0){throw 'ORIGINAL13_WAS_ACTUALLY_DEMANDED_REASSESS_DIAGNOSIS'}
 $records+=@{id=$id;source_commit='840e813dbc6ef0840c7e26850bc4ba6276dd4ffb';source_phases_raw_sha256=$hash;actual_request_and_simulated_PLC_frames=$count;issued_B_requests=$demand;status='STUCK_VALVE_NOT_EXCITED_NO_ISSUED_B_REQUEST';hardware_PLC_issue_proof='NOT_CLAIMED'}
}}finally{$z.Dispose()}
$dest=Join-Path $PSScriptRoot 'original_valve_excitation_file_proof.json'
[IO.File]::WriteAllText($dest,(@{method='PowerShell bounded JsonDocument pure-file review; no model execution';original_official_zip_sha256='6103ea42e1b0746991c021a95a664fe212805d0e0e654a23da6785fa529f1e55';cases=$records}|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
$records|ConvertTo-Json -Depth 8
