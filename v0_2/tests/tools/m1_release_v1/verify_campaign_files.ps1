# Read saved bytes only. No qualifier, controller, plant or native test is run.
param([Parameter(Mandatory)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path -LiteralPath $EvidenceRoot).Path
$base=Join-Path $root 'final'
$casesRoot=Join-Path $base 'm1-autonomous-development/stream-38423165745-1/cases'
$repo='C:/Users/Aiden Zhang/.codex/worktrees/m1-remote-development/Compute_to_Cooling_Digital_Test_Bench'
$planPath=Join-Path $base 'm1-autonomous-development/stream-38423165745-1/prefix_plan.json'
$planRawSha=(Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant()
$plan=Get-Content -LiteralPath $planPath -Raw|ConvertFrom-Json
if($plan.source_commit -cne '717a98dd89ece8d3b6944a80727b32f20a311b8b' -or $plan.manifest_sha256 -cne 'eef95f5ace0e33e862b098087cc7030718f73c2099b60695251f8feaf4682446'){throw 'V4_PLAN_IDENTITY_DRIFT'}
$control=Get-Content (Join-Path $repo 'v0_2/tests/tools/m1_campaign_v4/execution_manifest.json') -Raw|ConvertFrom-Json
$specPath=Join-Path $repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json'
if((Get-FileHash $specPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $control.bundle_entry_raw_hashes.'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json'){throw 'FROZEN_INPUT_SPEC_DRIFT'}
$spec=Get-Content -LiteralPath (Join-Path $repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
function Receipt-File($Receipt){
    if(-not $Receipt.path.StartsWith('artifacts/')){throw 'RECEIPT_ROOT_INVALID'}
    $p=[IO.Path]::GetFullPath((Join-Path $base $Receipt.path.Substring(10)))
    if(-not $p.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'RECEIPT_PATH_ESCAPE'}
    if((Get-Item -LiteralPath $p).Length -ne $Receipt.bytes -or
       (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Receipt.raw_sha256){throw 'RAW_RECEIPT_DRIFT'}
    return $p
}
function Frame-Hashes([string]$IndexPath){
    $idx=Get-Content -LiteralPath $IndexPath -Raw|ConvertFrom-Json
    $path=Receipt-File $idx.frames_receipt
    $null=Receipt-File $idx.document_receipt
    $file=[IO.File]::OpenRead($path);$sha=[Security.Cryptography.SHA256]::Create()
    $result=[Collections.Generic.List[string]]::new()
    try{
        foreach($row in $idx.rows){
            $file.Position=$row.offset;$packed=[byte[]]::new([int]$row.stored_bytes);$got=0
            while($got -lt $packed.Length){$n=$file.Read($packed,$got,$packed.Length-$got);if($n -eq 0){throw 'FRAME_TRUNCATED'};$got+=$n}
            $input=[IO.MemoryStream]::new($packed,$false)
            $z=[IO.Compression.ZLibStream]::new($input,[IO.Compression.CompressionMode]::Decompress)
            $output=[IO.MemoryStream]::new([int]$row.bytes)
            try{$z.CopyTo($output);$bytes=$output.ToArray()}finally{$z.Dispose();$input.Dispose();$output.Dispose()}
            if($bytes.Length -ne $row.bytes -or $bytes[-1] -ne 10 -or
               [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant() -cne $row.raw_sha256){throw 'FRAME_SAVED_BYTES_DRIFT'}
            $result.Add([BitConverter]::ToString($sha.ComputeHash($bytes,0,$bytes.Length-1)).Replace('-','').ToLowerInvariant())
        }
    }finally{$file.Dispose();$sha.Dispose()}
    if($result.Count -ne $idx.frame_count){throw 'FRAME_COUNT_DRIFT'}
    return ,$result.ToArray()
}
$sourceFiles=0
foreach($b in $plan.case_source_raw_hashes.PSObject.Properties){
    $p=Join-Path $base $b.Name.Substring(10)
    if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $b.Value){throw 'FULL_PREREQUISITE_DRIFT'}
    $sourceFiles++
}
$summaries=@();$prefixes=0;$pairs=0;$frames=0;$snapshots=0
for($index=0;$index -lt 101;$index++){
    $dir=Join-Path $casesRoot ('{0:d3}' -f $index)
    $stage=Get-Content -LiteralPath (Join-Path $dir 'stage_result.json') -Raw|ConvertFrom-Json
    $inv=Get-Content -LiteralPath (Join-Path $dir 'prefix_inventory.json') -Raw|ConvertFrom-Json
    $agg=Get-Content -LiteralPath (Join-Path $dir 'prefix_result.json') -Raw|ConvertFrom-Json
    $schema=Get-Content -LiteralPath (Join-Path $dir 'schema_readback.json') -Raw|ConvertFrom-Json
    $descriptor=$spec.input_inventory[$index]
    if($stage.status -cne 'PASS' -or -not $stage.repeat_pass -or $stage.comparison.status -cne 'PASS' -or
       $schema.status -cne 'PASS' -or $schema.index -ne $index -or $agg.status -cne 'PASS' -or
       $stage.descriptor.input_canonical_sha256 -cne $descriptor.input_canonical_sha256){throw 'CASE_IDENTITY_OR_RESULT_INVALID'}
    $expectedCount=if($descriptor.stage_id -in @('C-history','S-history','P15-history')){11}else{2}
    if(@($stage.repeat_hashes).Count -ne $expectedCount -or @($stage.repeat_receipts).Count -ne $expectedCount-1 -or
       @($stage.repeat_hashes|Select-Object -Unique).Count -ne 1){throw 'REPEAT_COUNT_OR_HASH_INVALID'}
    $null=Receipt-File $stage.reference_receipt;$null=Receipt-File $stage.split_receipt
    foreach($receipt in $stage.repeat_receipts){
        $null=Receipt-File $receipt
        if($receipt.raw_sha256 -cne $stage.split_receipt.raw_sha256 -or $receipt.canonical_sha256 -cne $stage.split_receipt.canonical_sha256){throw 'FULL_REPEAT_DOCUMENT_NOT_IDENTICAL'}
    }
    $ref=Frame-Hashes (Join-Path $dir 'reference.trace_index.json')
    $split=Frame-Hashes (Join-Path $dir 'split.trace_index.json')
    if($ref.Count -ne $descriptor.row_count -or $split.Count -ne $descriptor.row_count){throw 'CASE_ROW_COUNT_DRIFT'}
    $union=@(($inv.mandatory_prefix_lengths+$inv.output_triggered_progress_lengths+$inv.output_triggered_confirmed_lengths)|Sort-Object -Unique)
    if(($inv.selected_prefix_lengths -join ',') -cne ($plan.cases[$index].selected_prefix_lengths -join ',') -or
       ($union -join ',') -cne ($inv.selected_prefix_lengths -join ',') -or
       $agg.selected_count -ne @($inv.selected_prefix_lengths).Count -or $schema.all_selected_prefixes -ne $agg.selected_count){throw 'SELECTED_PREFIX_MEMBERSHIP_DRIFT'}
    if($inv.selection_policy -ceq 'SUPPORT_FROZEN_ALL_PREFIXES' -and
       ($inv.selected_prefix_lengths -join ',') -cne ((1..$descriptor.row_count) -join ',')){throw 'SUPPORT_PREFIX_MISSING'}
    $casePairs=0
    foreach($n in $inv.selected_prefix_lengths){
        $p=Get-Content -LiteralPath (Join-Path $dir ('prefix-{0:d6}-result.json' -f $n)) -Raw|ConvertFrom-Json
        if($p.status -cne 'PASS' -or -not $p.starts_from_t0 -or $p.compared_complete_frames -ne $n -or
           ($p.replayed_prefix_lengths -join ',') -cne [string]$n){throw 'PREFIX_NOT_COMPLETE_FROM_ZERO'}
        $rows=Get-Content -LiteralPath (Receipt-File $p.row_receipts) -Raw|ConvertFrom-Json
        if(@($rows).Count -ne $n){throw 'PREFIX_RECEIPT_ROW_COUNT'}
        for($i=0;$i -lt $n;$i++){
            if($rows[$i].row -ne $i -or $rows[$i].reference_sha256 -cne $ref[$i] -or
               $rows[$i].full_reference_sha256 -cne $ref[$i] -or $rows[$i].split_sha256 -cne $split[$i] -or
               $rows[$i].full_split_sha256 -cne $split[$i]){throw 'PREFIX_VS_FULL_FRAME_DRIFT'}
            $casePairs++
        }
    }
    $prefixes+=@($inv.selected_prefix_lengths).Count;$pairs+=$casePairs;$frames+=$ref.Count+$split.Count;$snapshots+=$expectedCount
    $summaries+=@{index=$index;stage_id=$descriptor.stage_id;row_count=$descriptor.row_count;prefixes=$agg.selected_count;
        frame_pairs=$casePairs;snapshots=$expectedCount;readback='PASS'}
    Write-Host ('CASE_FILE_READBACK_PASS '+$index+' prefixes='+$agg.selected_count)
}
$declaredPrefixes=0
foreach($case in $plan.cases){$declaredPrefixes+=@($case.selected_prefix_lengths).Count}
if($prefixes -ne $declaredPrefixes -or $sourceFiles -ne @($plan.case_source_raw_hashes.PSObject.Properties).Count){throw 'FULL_AGGREGATE_INVENTORY_DRIFT'}
$summary=@{scope='M1_REMOTE_DEVELOPMENT_ONLY';run_id=38423165745;source_commit=$plan.source_commit;readback='PASS';
    plan_raw_sha256=$planRawSha;cases_verified=101;selected_prefixes_verified=$prefixes;complete_frame_pairs_verified=$pairs;
    reference_and_split_frames_hashed=$frames;fresh_snapshots_verified=$snapshots;prerequisite_source_files_hashed=$sourceFiles;
    case_readbacks=$summaries;local_python_native_model_executed=$false;formal_qualification=$false}
$path=Join-Path $root 'full-case-file-readback.json'
$bytes=[Text.Encoding]::UTF8.GetBytes(($summary|ConvertTo-Json -Depth 10))
$f=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
Write-Host ('FULL_CASE_FILE_READBACK_PASS prefixes='+$prefixes+' pairs='+$pairs+' snapshots='+$snapshots)
