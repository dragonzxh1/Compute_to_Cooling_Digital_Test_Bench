"""Complete engineering gate; original readiness/causal gaps remain explicit."""
import json
from pathlib import Path
from .common import read
from .evidence import write, receipt, verify
from .stream_trace import TraceReader


def groups(case_root, *, reference=False):
    from .adapters import suite_checks
    descriptors=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
    output={}
    for label,kind,count in (('C-history','C',13),('S-history','S',19)):
        selected=[(i,d) for i,d in enumerate(descriptors) if d['stage_id']==label]
        if len(selected)!=count:raise ValueError('HISTORY_GROUP_CASE_INVENTORY')
        snapshots={}
        for i,d in selected:
            path=Path(case_root)/('%03d'%i)/('reference.json' if reference else 'split.json')
            reader=TraceReader(path);reader.verify_headers()
            snapshots[d['case_key']]=reader.metadata['snapshot']
        checks=suite_checks(kind,snapshots)
        output[kind]={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks}
    if any(r['status']!='PASS' for r in output.values()):raise ValueError('HISTORY_GROUP_ACCEPTANCE_FAIL')
    return output


def case_schema(index,directory):
    from .artifact_schemas import check
    directory=Path(directory)
    for name in ('reference.json','split.json'):
        TraceReader(directory/name).verify_all()
    stage=verify(receipt(directory/'stage_result.json'));check('stage_result',stage)
    inv=verify(receipt(directory/'prefix_inventory.json'));check('prefix_inventory',inv)
    result=verify(receipt(directory/'prefix_result.json'));check('prefix_result',result)
    lengths=inv['selected_prefix_lengths']
    expected=sorted(set(inv['mandatory_prefix_lengths']+inv['output_triggered_progress_lengths']+inv['output_triggered_confirmed_lengths']))
    if lengths!=expected or result['status']!='PASS' or result['selected_count']!=len(lengths):
        raise ValueError('EXACT_PREFIX_COVERAGE_FAIL')
    if inv['selection_policy']=='SUPPORT_FROZEN_ALL_PREFIXES' and lengths!=list(range(1,len(TraceReader(directory/'reference.json'))+1)):
        raise ValueError('SUPPORT_ALL_PREFIXES_MISSING')
    for n in lengths:
        p=verify(receipt(directory/('prefix-%06d-result.json'%n)))
        if p['status']!='PASS' or p['replayed_prefix_lengths']!=[n] or p['compared_complete_frames']!=n or not p['starts_from_t0']:
            raise ValueError('PREFIX_INDIVIDUAL_PROOF_INVALID')
        rows=verify(p['row_receipts'])
        if len(rows)!=n or any(r['row']!=i or r['reference_sha256']!=r['full_reference_sha256'] or r['split_sha256']!=r['full_split_sha256'] for i,r in enumerate(rows)):
            raise ValueError('PREFIX_COMPLETE_FRAME_HASH_PROOF_INVALID')
    item=write(directory/'schema_readback.json',{'status':'PASS','index':index,'all_selected_prefixes':len(lengths),'all_original_frame_fields_checked':True})
    return {'status':'PASS','receipt':item}


def finalize(root):
    from .witness_matrix import collect
    from .eligibility import evaluate
    from .startup_execution import aggregate
    root=Path(root);case_root=root/'cases'
    descriptors=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
    stages={};selections={};prefixes={}
    for i in range(101):
        folder=case_root/('%03d'%i)
        stage=verify(receipt(folder/'stage_result.json'))
        if stage['status']!='PASS' or not stage['repeat_pass'] or stage['comparison']['status']!='PASS':
            raise ValueError('CASE_NOT_COMPLETE_PASS')
        if verify(receipt(folder/'schema_readback.json'))['status']!='PASS':raise ValueError('CASE_SCHEMA_NOT_PASS')
        stages[i]={**stage,'stage_receipt':receipt(folder/'stage_result.json')}
        selections[i]=verify(receipt(folder/'prefix_inventory.json'))
        prefixes[i]=verify(receipt(folder/'prefix_result.json'))
    reference_groups=groups(case_root,reference=True);split_groups=groups(case_root)
    startup=aggregate(root/'startup',root/'startup_inventory.json',case_root)
    matrix=collect(root,descriptors,stages)
    eligibility=evaluate(startup)
    write(root/'startup_eligibility.json',eligibility)
    write(root/'PF16_witness_matrix.json',matrix)
    complete=(len(stages)==101 and all(p['status']=='PASS' for p in prefixes.values())
        and startup['versioned_compatibility']=='PASS' and matrix['original_validated_count']==15
        and matrix['PF06_proposal'] is not None and matrix['PF06_proposal']['PF06_SUPPLEMENTAL_SOURCE']=='DEVELOPMENT_VALIDATED')
    result={'status':'M1_DEVELOPMENT_COMPLETE_FULL_SCOPE_PENDING' if complete else 'M1_DEVELOPMENT_INCOMPLETE',
        'engineering_checks_passed':complete,'original_frozen_full_scope_ready':False,'descriptor_count':101,
        'pass_count':len(stages),'selected_prefixes':sum(p['selected_count'] for p in prefixes.values()),
        'all_selected_prefixes_complete':all(p['status']=='PASS' for p in prefixes.values()),
        'original_startup_historical':startup['historical_guard']['ORIGINAL_STARTUP_HISTORICAL_RESULT'],
        'startup_versioned_compatibility':startup['versioned_compatibility'],'startup_causal_status':startup['causal_status'],
        'reference_groups':reference_groups,'split_groups':split_groups,'PF16_original_validated':matrix['original_validated_count'],
        'PF06_original_scope':'INCOMPLETE','PF06_proposal':matrix['PF06_proposal'],'startup_eligibility':eligibility,
        'formal_qualification':False,'production':False,'phase6':False,'T09':'IMPLEMENTATION_HOLD',
        'full_P_history_available':False,'hardware':'CALIBRATION_REQUIRED','old_scores_borrowed':False}
    item=write(root/'development_result.json',result)
    return {'status':'PASS' if complete else 'FAIL','result_receipt':item,'engineering_result':result['status']}
