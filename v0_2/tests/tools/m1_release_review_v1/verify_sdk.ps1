# Persisted-byte audit only; never invokes Python, native helpers, or models.
param([Parameter(Mandatory)][string]$EvidenceRoot,
      [Parameter(Mandatory)][string]$CampaignRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read([string]$Path){Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json}
function Require([bool]$Ok,[string]$Why){if(-not $Ok){throw $Why}}
function BoundPath([string]$Base,[string]$Relative){
    $b=[IO.Path]::GetFullPath($Base).TrimEnd('\')+'\'
    $p=[IO.Path]::GetFullPath((Join-Path $Base $Relative))
    Require ($p.StartsWith($b,[StringComparison]::OrdinalIgnoreCase)) 'EVIDENCE_PATH_ESCAPE'
    return $p
}
function VerifyReceipt([string]$Base,$Receipt,[string]$Name,[string]$Digest){
    $p=BoundPath $Base $Name
    Require ((Get-Item -LiteralPath $p).Length -eq $Receipt.bytes -and (Hash $p) -ceq $Digest) ('RECEIPT_DRIFT '+$Name)
}
function Frames([string]$Folder,[string]$Kind,[int]$Count){
    $idx=Read (Join-Path $Folder ($Kind+'.trace_index.json'))
    Require ($idx.frame_count -eq $Count -and $idx.rows.Count -eq $Count) 'FULL_FRAME_COVERAGE'
    foreach($receipt in @($idx.frames_receipt,$idx.document_receipt)){
        VerifyReceipt $Folder $receipt ([IO.Path]::GetFileName($receipt.path)) $receipt.raw_sha256
    }
    $f=[IO.File]::OpenRead((Join-Path $Folder ([IO.Path]::GetFileName($idx.frames_receipt.path))))
    $sha=[Security.Cryptography.SHA256]::Create()
    $next=0L
    try{
        foreach($row in $idx.rows){
            Require ($row.offset -eq $next -and $row.compression -ceq 'zlib') 'FRAME_OFFSET_OR_ENCODING'
            $f.Position=$row.offset
            $packed=[byte[]]::new([int]$row.stored_bytes);$got=0
            while($got -lt $packed.Length){$n=$f.Read($packed,$got,$packed.Length-$got);Require ($n -gt 0) 'TRUNCATED_FRAME';$got+=$n}
            $input=[IO.MemoryStream]::new($packed,$false)
            $z=[IO.Compression.ZLibStream]::new($input,[IO.Compression.CompressionMode]::Decompress)
            $output=[IO.MemoryStream]::new()
            try{$z.CopyTo($output);$raw=$output.ToArray()}finally{$z.Dispose();$input.Dispose();$output.Dispose()}
            Require ($raw.Length -eq $row.bytes -and $raw[-1] -eq 10) 'DECOMPRESSED_FRAME_LENGTH'
            Require ([BitConverter]::ToString($sha.ComputeHash($raw)).Replace('-','').ToLowerInvariant() -ceq $row.raw_sha256) 'DECOMPRESSED_FRAME_SHA'
            $next+=$row.stored_bytes
        }
        Require ($next -eq $f.Length) 'UNINDEXED_FRAME_BYTES'
    }finally{$f.Dispose();$sha.Dispose()}
    return $idx
}
$controlPath=Join-Path $repo 'v0_2/tests/tools/m1_release_v3/delivery_control.json'
$controlHash=Hash $controlPath
Require ($controlHash -ceq '4d7d8de8573c8be168884169ec94a1fc6a32c08dfe28108122b87b6f86ab0328') 'CONTROL_DRIFT'
$control=Read $controlPath
foreach($b in $control.source_hashes.PSObject.Properties){Require ((Hash (Join-Path $repo $b.Name)) -ceq $b.Value) ('PROTECTED_SOURCE_DRIFT '+$b.Name)}
$inventory=@(Read (Join-Path $EvidenceRoot 'artifact-inventory-observation.json'))
Require ($inventory.Count -eq 11) 'OFFICIAL_ARTIFACT_COUNT'
$groups=[Collections.Generic.List[object]]::new();$seen=[Collections.Generic.HashSet[int]]::new()
$rows=0;$files=0;$frames=0;$captures=0;$elapsedMax=0.0
for($g=0;$g -le 10;$g++){
    $name='m1-sdk-streaming-'+$g
    $official=@($inventory|Where-Object name -CEQ $name)
    Require ($official.Count -eq 1 -and -not $official[0].expired) 'OFFICIAL_ARTIFACT_IDENTITY'
    Require ((Hash (Join-Path $EvidenceRoot ($name+'.zip'))) -ceq $official[0].digest.Substring(7)) 'OFFICIAL_ZIP_DIGEST'
    $dir=Join-Path $EvidenceRoot ($name+'/m1-sdk-streaming/38493762797-1-SDK-'+$g)
    Require (-not(Test-Path (Join-Path $dir 'failure.json'))) 'SDK_EXECUTION_FAILURE'
    $result=Read (Join-Path $dir 'result.json');$accept=Read (Join-Path $dir 'execution_acceptance.json')
    Require ($result.status -ceq 'SDK_STREAMING_INSTALLED_GROUP_PASS' -and $accept.status -ceq $result.status) 'SDK_GROUP_NOT_PASS'
    Require ($result.source_commit -ceq '9f0b2e87a7c324a841274bc92303b009fbebbb63' -and $result.control_manifest_sha256 -ceq $controlHash -and $result.group -eq $g) 'SDK_EXECUTION_IDENTITY'
    Require ($result.sdk_source_commit -ceq $control.sdk_source_commit -and $result.archive_sha256 -ceq $control.sdk_zip_sha256 -and -not $result.formal_qualification -and -not $result.full_campaign_credit) 'SDK_SCOPE_DRIFT'
    $start=Read (Join-Path $dir 'job_start.json');$native=Read (Join-Path $dir 'job_status.json')
    $proof=Read (Join-Path $dir 'external_job_identity.json');$ready=Read (Join-Path $dir 'ready.json');$release=Read (Join-Path $dir 'release.json')
    Require ($ready.pid -eq $proof.actual_python_pid -and $ready.pid -eq $release.actual_python_pid -and $proof.in_target_job -and $proof.target_job_name -ceq $start.job_name) 'ACTUAL_PYTHON_JOB_IDENTITY'
    Require ($release.external_proof_raw_sha256 -ceq (Hash (Join-Path $dir 'external_job_identity.json')) -and $ready.executable -ceq $result.venv_python) 'RELEASE_OR_EXECUTABLE_IDENTITY'
    Require ($proof.cpu_rate -eq 2500 -and $proof.cpu_flags -eq 5 -and $proof.process_mb -eq 1024 -and $proof.job_mb -eq 2048 -and $proof.max_active_processes -eq 4 -and 'python.exe' -in $proof.modules_before_workload) 'JOB_LIMITS'
    Require ($start.cpu_rate -eq 2500 -and $start.process_memory_mb -eq 1024 -and $start.job_memory_mb -eq 2048 -and $start.wall_ms -eq 480000 -and $start.kill_on_close) 'LAUNCH_LIMITS'
    Require ($native.pid -eq $start.pid -and $native.assigned_before_resume -and $native.resumed -and $native.cleanup_complete -and $native.active_after_cleanup -eq 0 -and $native.child_exitcode -eq 0 -and $native.outcome -ceq 'EXITED') 'NATIVE_CLEANUP'
    $receipts=Read (Join-Path $dir 'raw_receipts.json')
    foreach($b in $receipts.PSObject.Properties){Require ($b.Value.status -ceq 'PERSISTED') 'RAW_CAPTURE_MISSING';VerifyReceipt $dir $b.Value $b.Name $b.Value.raw_sha256;$captures++}
    $lock=Read (Join-Path $repo 'v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json')
    Require (($result.dependencies.PSObject.Properties.Name.Count) -eq ($lock.dependencies.PSObject.Properties.Name.Count)) 'DEPENDENCY_COUNT'
    foreach($b in $lock.dependencies.PSObject.Properties){Require ($result.dependencies.($b.Name) -ceq $b.Value) 'PINNED_DEPENDENCY_DRIFT'}
    Require ($result.working_directory -ceq 'D:\a\_temp\m1-sdk-streaming-use-workspace') 'SDK_CWD_NOT_INDEPENDENT'
    VerifyReceipt $dir $result.describe_receipt $result.describe_receipt.name $result.describe_receipt.sha256
    $description=Read (Join-Path $dir $result.describe_receipt.name)
    Require ($description.verified_files -eq 675 -and $description.source_commit -ceq $control.sdk_source_commit) 'PACKAGE_675_BYTE_VERIFICATION'
    $events=@(Get-Content (Join-Path $dir 'events.jsonl')|ForEach-Object{$_|ConvertFrom-Json})
    Require (@($events|Where-Object event -EQ 'STOP').Count -eq 0) 'STOP_EVENT'
    $expected=@($control.cases|Where-Object {$_.index -ge $g*10 -and $_.index -lt [Math]::Min(($g+1)*10,101)})
    Require ($result.case_count -eq $expected.Count -and $result.cases.Count -eq $expected.Count) 'GROUP_CASE_COUNT'
    $groupRows=0
    for($j=0;$j -lt $expected.Count;$j++){
        $case=$result.cases[$j];$e=$expected[$j]
        Require ($seen.Add([int]$case.index) -and $case.index -eq $e.index -and $case.row_count -eq $e.row_count -and $case.input_canonical_sha256 -ceq $e.input_canonical_sha256 -and $case.status -ceq 'PASS') 'INPUT_UNION_OR_IDENTITY'
        VerifyReceipt $dir $case.output_receipt $case.output_receipt.name $case.output_receipt.sha256
        $out=Read (Join-Path $dir $case.output_receipt.name)
        Require ($out.comparison.status -ceq 'PASS' -and $out.comparison.compared_rows -eq $e.row_count -and $out.example_prefix_rows -eq $e.row_count -and $out.comparison.rules.Count -eq 18) 'FULL_INDEPENDENT_COMPARISON'
        Require ($case.imported_sut_file -ceq 'D:\a\_temp\m1-sdk-streaming-unpacked\v0_2\tests\tools\m1_engine_v4\engine.py' -and $out.sut -ceq 'v0_2.tests.tools.m1_engine_v4.engine.SplitEngine') 'INSTALLED_V4_IMPORT'
        $begins=@($events|Where-Object {$_.event -ceq 'CASE_BEGIN' -and $_.index -eq $e.index});$ends=@($events|Where-Object {$_.event -ceq 'CASE_END' -and $_.index -eq $e.index})
        Require ($begins.Count -eq 1 -and $ends.Count -eq 1 -and $begins[0].elapsed_s -le $ends[0].elapsed_s -and $ends[0].output_sha256 -ceq $case.output_receipt.sha256) 'CASE_EVENT_CHAIN'
        foreach($receipt in $case.exported_trace_receipts){VerifyReceipt $dir $receipt $receipt.path $receipt.sha256;$files++}
        $trace=Split-Path (BoundPath $dir ($case.exported_trace_receipts|Where-Object path -Like '*/split.trace_index.json').path)
        foreach($kind in @('reference','split')){
            $idx=Frames $trace $kind $e.row_count
            $old=Read (Join-Path $CampaignRoot ('cases/{0:d3}/{1}.trace_index.json' -f $e.index,$kind))
            Require (($idx.rows.raw_sha256 -join ',') -ceq ($old.rows.raw_sha256 -join ',')) 'FULL_FRAME_BYTES_DIFFER_FROM_VERIFIED_V4_CAMPAIGN'
            $frames+=$idx.frame_count
        }
        Require ((Hash (Join-Path $trace 'reference.json')) -ceq $case.reference_sha256 -and (Hash (Join-Path $trace 'split.json')) -ceq $case.split_sha256) 'DOCUMENT_BINDING'
        $rows+=$e.row_count;$groupRows+=$e.row_count
    }
    Require ($result.rows -eq $groupRows -and $result.elapsed_s -lt 480) 'GROUP_DURATION_OR_ROWS'
    $elapsedMax=[Math]::Max($elapsedMax,$result.elapsed_s)
    $groups.Add(@{group=$g;cases=$result.case_count;rows=$groupRows;elapsed_s=$result.elapsed_s;result_raw_sha256=(Hash (Join-Path $dir 'result.json'));artifact_sha256=$official[0].digest.Substring(7);actual_python_pid=$ready.pid;launcher_pid=$start.pid;status='INDEPENDENT_FILE_READBACK_PASS'})
}
Require ($seen.Count -eq 101 -and $rows -eq ($control.cases.row_count|Measure-Object -Sum).Sum) 'FULL_101_COVERAGE'
@{schema='m1-streaming-sdk-v3-independent-readback-v1';status='INDEPENDENT_FILE_READBACK_PASS';run_id=38493762797;source_commit='9f0b2e87a7c324a841274bc92303b009fbebbb63';sdk_source_commit=$control.sdk_source_commit;control_manifest_sha256=$controlHash;sdk_zip_sha256=$control.sdk_zip_sha256;groups=$groups.ToArray();case_count=$seen.Count;input_rows=$rows;complete_frames_decompressed_and_hashed=$frames;exported_trace_files_verified=$files;raw_captures_verified=$captures;payload_files_per_install=675;source_bindings_verified=@($control.source_hashes.PSObject.Properties).Count;max_group_elapsed_s=$elapsedMax;actual_python_job_and_cleanup='PASS';full_frames_equal_to_independently_verified_v4_campaign=$true;local_python_native_model_executed=$false;formal_qualification=$false;production=$false;hardware='CALIBRATION_REQUIRED'}|ConvertTo-Json -Depth 8
