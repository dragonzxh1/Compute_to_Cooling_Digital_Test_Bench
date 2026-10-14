# Mechanical exact-byte proposal assembly only; no approval or workload execution.
param([Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$target=[IO.Path]::GetFullPath($OutputDirectory)
$allowed=[IO.Path]::GetFullPath((Join-Path $repo 'artifacts/m1-c3c-v1-freeze'))
if($target -cne $allowed -or (Test-Path -LiteralPath $target)){throw 'FRESH_EXACT_PROPOSAL_DIRECTORY_REQUIRED'}
$parentPath=Join-Path $repo 'v0_2/tests/tools/m1_campaign_v4/execution_manifest.json'
if((Get-FileHash -LiteralPath $parentPath).Hash.ToLowerInvariant() -cne 'eef95f5ace0e33e862b098087cc7030718f73c2099b60695251f8feaf4682446'){throw 'SEALED_PARENT_MANIFEST_DRIFT'}
$parent=Get-Content -LiteralPath $parentPath -Raw|ConvertFrom-Json
$spec=Get-Content -LiteralPath (Join-Path $repo 'phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json') -Raw|ConvertFrom-Json
if($spec.input_inventory.Count -ne 101){throw 'INPUT_INVENTORY_DRIFT'}
. (Join-Path $PSScriptRoot 'batch.ps1')
New-Item -ItemType Directory -Path $target|Out-Null
$inputs=@();$required=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$checkIds=@($parent.check_stage_ids)+@('C3_AUTHORITY_UNIT')
foreach($id in $checkIds){$null=$required.Add([string]$id)}
for($i=0;$i -lt 101;$i++){
    $d=$spec.input_inventory[$i]
    $inputs+=@{index=$i;row_count=$d.row_count;input_canonical_sha256=$d.input_canonical_sha256}
    foreach($phase in @('REFERENCE','SELECT','SPLIT','SEAL','SCHEMA')){$null=$required.Add(('CASE-{0:d3}-{1}' -f $i,$phase))}
    $count=if($d.stage_id -in @('C-history','S-history','P15-history')){11}else{2}
    for($j=1;$j -lt $count;$j++){$null=$required.Add(('CASE-{0:d3}-REPEAT-{1}' -f $i,$j))}
}
for($i=0;$i -lt 50;$i++){$null=$required.Add('STARTUP-'+$i)}
$null=$required.Add('REFERENCE_GROUPS')
$ordinalStages=[string[]]@($required)
[Array]::Sort($ordinalStages,[StringComparer]::Ordinal)
$scope=[ordered]@{
    schema='m1-c3c-limited-software-scope-v1';status='PROPOSED_NOT_USER_APPROVED'
    scope='M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN';descriptor_count=101;startup_node_count=50
    required_static_stage_ids=$ordinalStages
    final_current_stage='FINAL_ACCEPTANCE';final_current_batch_post_cleanup_readback_required=$true
    prefix_scope='Original ITQ conditional selector: mandatory674 plus fresh protected reference progress/confirmed union; support U/ST/C/S/P15 exhaustive prefixes'
    prefix_counts_not_prepopulated_from_previous_run=$true
    repeat_scope='ITQ/U/ST2 full snapshots; C/S/P15 baseline plus10; all fresh'
    ordinary_library_metadata_is_not_formal_authority=$true
    qualification_result_requires_fresh_formal_execution=$true
    SEM01_required='Complete-only publication remains mandatory; registered software failure cuts included; no arbitrary OS/interrupt/durable guarantee'
    SEM02_required='Exactly5 historical/invalid causal exclusions remain INCOMPLETE for strict P1 B/C; preserve original50/49-50 and separate versioned PASS'
    PF06_required='Original scope INCOMPLETE; separately approved C8_normal row4/800ms supplement; both original negative controls retained'
    limitations=@{ARBITRARY_POST_EXCEPTION_ATOMICITY='NOT_PROVEN';PF06_ORIGINAL_SCOPE='INCOMPLETE';FULL_P_HISTORY_VALIDATION_AVAILABLE='NO';T09='IMPLEMENTATION_HOLD';REAL_HARDWARE='CALIBRATION_REQUIRED';PRODUCTION_IMPLEMENTATION_AUTHORIZED='NO';HARDWARE_CONTROL_AUTHORIZED='NO';PHASE6='NO'}
}
$scopePath=Join-Path $target 'limited_scope.json';$scopeHash=Write-C3Json $scopePath $scope
$sem01=[ordered]@{
    schema='m1-c3c-sem01-detached-post-addendum-v3';status='PROPOSED_NOT_USER_APPROVED'
    candidate_sha256='70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce'
    policy='Detached POST legacy projection; actual immutable old-obligation PRE and Safety facts precede PLC-only issue; POST no additional source-sample credit'
    complete_only_publication_required=$true
    registered_failure_cuts=@('explicit before-publication failure','projection preparation failure','result Record serialization failure','completed-store insertion failure')
    required_fresh_stage='V4_ATOMICITY_UNIT';required_test_count=4
    defect_identity='M1-DEF-POST-001';prior_V3_failure_evidence_not_erased=$true
    publication_before_projection_risk='Closed only for tested V4 prepare-before-publication paths; original Build005/V3 defect remains in historical evidence'
    ARBITRARY_POST_EXCEPTION_ATOMICITY='NOT_PROVEN'
    T09='IMPLEMENTATION_HOLD'
    mandatory_source_locations=@('contracts/14_control_input_permission_contract.md','contracts/15_safety_supervisor_contract.md','contracts/15A_tracking_safety_policy_amendment.md','PHASE5_R5_2_1R4_7_C2_R1_CONTRACT15A_PUBLICATION_TIMING_CLARIFICATION_V1.md','phase5_r5_2_1r4_7_c3_a_split_interface_spec.json','phase5_r5_2_1r4_7_c3_a_comparator_registration.json')
    scoped_claim='Exactly preregistered offline software fixture behavior and explicit registered failure cuts, not full external runtime durability or arbitrary asynchronous exception atomicity'
    unfulfilled_mandatory_requirement_is_not_waived=$true
}
$sem01Path=Join-Path $target 'SEM01_addendum_v3.json';$sem01Hash=Write-C3Json $sem01Path $sem01
# These are exact copies of independently reviewed bindings, not newly generated
# SUT golden expectations. Original files/status/history remain unchanged.
$sem02Path=Join-Path $target 'SEM02_five_case_registry_v1.json'
$pf06Path=Join-Path $target 'PF06_C8_NORMAL_SUPPLEMENT_v1.json'
Copy-Item -LiteralPath (Join-Path $repo 'docs/M1_V4_SEM02_PROPOSED_BINDING.json') -Destination $sem02Path
Copy-Item -LiteralPath (Join-Path $repo 'docs/M1_V4_PF06_PROPOSED_BINDING.json') -Destination $pf06Path
$registrations=[ordered]@{limited_scope='artifacts/m1-c3c-v1-freeze/limited_scope.json';SEM01='artifacts/m1-c3c-v1-freeze/SEM01_addendum_v3.json';SEM02='artifacts/m1-c3c-v1-freeze/SEM02_five_case_registry_v1.json';PF06_supplement='artifacts/m1-c3c-v1-freeze/PF06_C8_NORMAL_SUPPLEMENT_v1.json'}
$hashes=[ordered]@{}
foreach($map in @($parent.bundle_entry_raw_hashes,$parent.remote_source_raw_hashes)){
    foreach($b in $map.PSObject.Properties){if($hashes.Contains($b.Name) -and $hashes[$b.Name] -cne $b.Value){throw 'CONFLICTING_PROTECTED_BINDING'};$hashes[$b.Name]=$b.Value}
}
$files=@(Get-ChildItem -LiteralPath $PSScriptRoot -File|ForEach-Object {'v0_2/tests/tools/m1_c3c_v1/'+$_.Name})
$files+=@('.github/workflows/liquid-cooling-recovery.yml','.github/workflows/m1-c3c-full.yml','.github/actions/m1-c3c-runtime/action.yml','v0_2/tests/tools/m1_campaign_v4/execution_manifest.json','docs/M1_SOFTWARE_USER_GUIDE.md','docs/V02_PHYSICS_PARAMETER_REFERENCE.md','docs/LEGACY_SCENARIO_PARAMETER_REFERENCE.md')
$files+=@($registrations.Values)
foreach($p in $files){$hashes[$p]=(Get-FileHash -LiteralPath (Join-Path $repo $p)).Hash.ToLowerInvariant()}
$registrationHashes=[ordered]@{};foreach($k in $registrations.Keys){$registrationHashes[$k]=$hashes[$registrations[$k]]}
$execution=[ordered]@{runner='v0_2/tests/tools/m1_c3c_v1/run.ps1';worker='v0_2/tests/tools/m1_c3c_v1/worker.py';workflow='.github/workflows/m1-c3c-full.yml';environment_lock='v0_2/tests/tools/m1_c3c_v1/environment_lock.json';artifact_schema='v0_2/tests/tools/m1_c3c_v1/artifact_schema.json';stop_rules='v0_2/tests/tools/m1_c3c_v1/stop_rules.json'}
$manifest=[ordered]@{
    schema='m1-c3c-executable-proposal-v1';status='FINALIZED_AWAITING_USER_APPROVAL';scope=$scope.scope
    candidate_sha256=$sem01.candidate_sha256;source_raw_sha256=$hashes;inputs=$inputs
    limitations=$scope.limitations;startup_count=50;historical_startup_result='49/50';versioned_startup_result_is_separate=$true
    strict_causal_exclusion_count=5;observer_field_count=56;comparator_rule_count=18
    complete_only_publication_required=$true;PF06_supplemental_binding_id='PF06-C8-NORMAL-SUPPLEMENT-v1';prior_pass_credit=$false
    registration_paths=$registrations;registration_raw_sha256=$registrationHashes;execution=$execution
    check_stage_ids=$checkIds;bundle_path=$parent.bundle_path;bundle_raw_sha256=$parent.bundle_raw_sha256;bundle_entry_raw_hashes=$parent.bundle_entry_raw_hashes
    resource_policy=$parent.resource_policy
    snapshot_parent_commit=(git -C $repo rev-parse HEAD)
    executable_source_commit_supplied_only_by_separate_user_approval=$true
    self_hash_excluded_to_avoid_circular_hash=$true
    source_closure_and_final_package_hash_require_independent_pre_sign_validation=$true
    PF06_phase_hash_normativity='Original phase hashes are historical diagnostic bindings; this run validates its own fresh hashes and frozen independent predicates/unchanged comparator'
    approval_generated=$false;formal_execution_started=$false
}
$manifestPath=Join-Path $target 'executable_proposal.json'
$manifestHash=Write-C3Json $manifestPath $manifest
@{status='PROPOSAL_ASSEMBLED_NOT_APPROVED_OR_EXECUTED';output_directory=$target;proposal_raw_sha256=$manifestHash;source_bindings=$hashes.Count;required_static_stage_ids=$required.Count;input_count=$inputs.Count;registration_hashes=$registrationHashes}|ConvertTo-Json -Depth 8
