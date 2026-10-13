# Verify saved original reports only. Never invokes pytest or candidate code.
param([Parameter(Mandatory)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path -LiteralPath $EvidenceRoot).Path
$base=Join-Path $root 'final'
$run=Join-Path $base 'm1-autonomous-development/stream-38423165745-1'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$signature=Get-Content (Join-Path $repo 'phase5_r5_2_1r4_5c_i_startup_legacy_signature.json') -Raw|ConvertFrom-Json
if((Get-FileHash (Join-Path $repo $signature.source_path) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $signature.source_raw_sha256){throw 'ORIGINAL_STARTUP_SOURCE_DRIFT'}
$inventory=Get-Content (Join-Path $run 'startup_inventory.json') -Raw|ConvertFrom-Json
if($inventory.status -cne 'PASS' -or @($inventory.nodeids).Count -ne 50 -or @($inventory.nodeids|Select-Object -Unique).Count -ne 50){throw 'ORIGINAL_STARTUP_INVENTORY_INVALID'}
$pass=0;$fail=0;$raw=0;$rows=@()
for($i=0;$i -lt 50;$i++){
    $folder=Join-Path $run ('startup/{0:d3}' -f $i)
    $node=Get-Content (Join-Path $folder 'node_result.json') -Raw|ConvertFrom-Json
    $d=$node.structured_result
    if($node.status -cne 'PASS' -or $node.nodeid -cne $inventory.nodeids[$i] -or -not $d.session_complete -or @($d.collection_errors).Count -ne 0 -or @($d.reports).Count -ne 3 -or @($d.collected_nodeids).Count -ne 1 -or $d.collected_nodeids[0] -cne $node.nodeid){throw 'STARTUP_STRUCTURED_REPORT_INVALID'}
    $call=@($d.reports|Where-Object{$_.when -ceq 'call'})
    $other=@($d.reports|Where-Object{$_.when -in @('setup','teardown')})
    if($call.Count -ne 1 -or $other.Count -ne 2 -or @($other|Where-Object{$_.outcome -cne 'passed'}).Count){throw 'STARTUP_PHASES_INVALID'}
    foreach($report in $d.reports){if($report.nodeid -cne $node.nodeid -or $null -ne $report.wasxfail){throw 'STARTUP_NODE_OR_XFAIL_CHANGED'}}
    if($call[0].outcome -ceq 'failed'){
        $fail++
        if($node.nodeid -cne $signature.nodeid -or $node.pytest_exitcode -ne 1 -or -not $node.legacy_assertion_preserved){throw 'UNEXPECTED_STARTUP_FAILURE'}
        foreach($key in @('source_path','source_raw_sha256','assertion_line_1based','assertion_ast','semantic_identifier','exception_type')){if($call[0].failure_identity.$key -cne $signature.$key){throw ('STARTUP_EXACT_FAILURE_IDENTITY '+$key)}}
    }elseif($call[0].outcome -ceq 'passed' -and $node.pytest_exitcode -eq 0 -and $node.historical_test_pass){$pass++}else{throw 'STARTUP_UNEXPECTED_OUTCOME'}
    foreach($receipt in $node.receipts){
        if(-not $receipt.path.StartsWith('artifacts/')){throw 'STARTUP_RECEIPT_ROOT'}
        $p=[IO.Path]::GetFullPath((Join-Path $base $receipt.path.Substring(10)))
        if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $receipt.raw_sha256 -or (Get-Item -LiteralPath $p).Length -ne $receipt.bytes){throw 'STARTUP_RAW_RECEIPT_DRIFT'}
        $raw++
    }
    $rows+=@{index=$i;nodeid=$node.nodeid;original_outcome=$call[0].outcome;node_result_sha256=(Get-FileHash (Join-Path $folder 'node_result.json') -Algorithm SHA256).Hash.ToLowerInvariant()}
}
if($pass -ne 49 -or $fail -ne 1){throw 'ORIGINAL_STARTUP_COUNT_DRIFT'}
$eligibility=Get-Content (Join-Path $run 'startup_eligibility.json') -Raw|ConvertFrom-Json
if(@($eligibility.cases).Count -ne 5 -or $eligibility.STARTUP_STRICT_P1_CAUSAL_ELIGIBILITY -cne 'INCOMPLETE' -or $eligibility.STARTUP_VERSIONED_COMPATIBILITY -cne 'PASS'){throw 'STARTUP_CAUSAL_GAPS_OR_COMPATIBILITY_CHANGED'}
foreach($i in @(0,12)){
    $stage=Get-Content (Join-Path $run ('cases/{0:d3}/stage_result.json' -f $i)) -Raw|ConvertFrom-Json
    $prefix=Get-Content (Join-Path $run ('cases/{0:d3}/prefix_result.json' -f $i)) -Raw|ConvertFrom-Json
    if($stage.status -cne 'PASS' -or -not $stage.repeat_pass -or $prefix.status -cne 'PASS'){throw 'FRESH_U_OR_V2_NOT_PASS'}
}
$summary=@{run_id=38423165745;status='INDEPENDENT_STARTUP_FILE_READBACK_PASS';original_historical='49/50';versioned_compatibility='PASS';strict_P1_causal_eligibility='INCOMPLETE';causal_gap_case_count=5;original_source_raw_sha256=$signature.source_raw_sha256;original_tests_modified=$false;raw_receipts_verified=$raw;nodes=$rows;local_test_execution=$false;formal_qualification=$false}
$bytes=[Text.Encoding]::UTF8.GetBytes(($summary|ConvertTo-Json -Depth 8))
$f=[IO.File]::Open((Join-Path $root 'startup-file-readback.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
'ORIGINAL_STARTUP49_50_EXACT_FAILURE_AND_VERSIONED_COMPATIBILITY_FILE_READBACK_PASS'
