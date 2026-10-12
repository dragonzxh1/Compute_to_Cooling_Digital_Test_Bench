"""One isolated stage; guard authorization and bytes before candidate imports."""
import argparse
import json
from pathlib import Path
from .package_guard import development,formal_authorization


def execute(kind,index,directory,lock_path,*,expected_reference_sha=None,expected_stage_sha=None,formal=None,prefix_length=None):
    if formal is not None:raise ValueError('REMOTE_DEVELOPMENT_FORBIDS_FORMAL_C3_C')
    if formal is None:lock,_=development(lock_path)
    else:
        lock=formal_authorization(*formal)
        from . import common
        common.MODE='FORMAL_C3_C'
    # Lazy imports after source/environment checks.
    from .common import read,sha,canonical
    from .materializer import extract
    from .evidence import write,verify
    from .schemas import validate
    descriptors=read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory']
    descriptor=descriptors[index];rows=extract(descriptor)['observations']
    for row in rows:validate('input',row)
    profile=read('phase5_r5_2_2_fixture_tracking_profile.json')
    classifier=read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
    directory=Path(directory)
    if kind=='REFERENCE':
        from .observer import reference_rows
        result=reference_rows(rows,profile,classifier,replay_kind=descriptor['replay_kind'])
        plain=reference_rows(rows,profile,classifier,observed=False,replay_kind=descriptor['replay_kind'])
        if plain['final']!=result['final'] or plain['snapshot']!=result['snapshot']:raise ValueError('OBSERVER_INTERFERENCE')
        for frame in result['frames']:validate('reference',frame)
        receipt=write(directory/'reference.json',result)
        write(directory/'reference_receipt.json',receipt)
        from .adapters import individual
        u=None
        if descriptor['stage_id']=='ST-12':
            u=json.loads((directory.parent/'000'/'reference_checks.json').read_bytes())
        checks=individual(descriptor,result['snapshot'],fresh_u_checks=u)
        write(directory/'reference_checks.json',checks)
        if not all(checks.values()):raise ValueError('FROZEN_REFERENCE_EXPECTATION_FAIL: '+str(checks))
        return {'status':'PASS','receipt':receipt,'row_count':len(rows)}
    if kind=='SELECT':
        from v0_2.tests.data.tracking_qualification.r46_prefix import select
        ref_receipt=json.loads((directory/'reference_receipt.json').read_bytes())
        if not expected_reference_sha or ref_receipt['raw_sha256']!=expected_reference_sha:raise ValueError('REFERENCE_RECEIPT_IDENTITY_MISMATCH')
        ref=verify(ref_receipt)
        selection=select(rows,ref['snapshot']['records'])
        conditional=descriptor['stage_id'].startswith('ITQ-')
        if not conditional:
            selection['mandatory_prefix_lengths']=list(range(1,len(rows)+1))
            selection['selected_prefix_lengths']=list(range(1,len(rows)+1))
        inventory={'source':'FRESH_PERSISTED_REFERENCE','reference_receipt':ref_receipt,
            'selection_policy':'ITQ_FROZEN_CONDITIONAL' if conditional else 'SUPPORT_FROZEN_ALL_PREFIXES',
            'input_sha256':descriptor['input_canonical_sha256'],**selection}
        selected=write(directory/'prefix_inventory.json',inventory)
        write(directory/'prefix_inventory_receipt.json',selected)
        verify(selected)
        # Rebuild from the persisted reference, before any split import/execution.
        rebuilt=select(rows,verify(ref_receipt)['snapshot']['records'])
        if not conditional:
            rebuilt['mandatory_prefix_lengths']=list(range(1,len(rows)+1))
            rebuilt['selected_prefix_lengths']=list(range(1,len(rows)+1))
        if selection!=rebuilt:raise ValueError('PREFIX_SELECTION_NONDETERMINISTIC')
        return {'status':'PASS','inventory_receipt':selected,'selected_count':len(selection['selected_prefix_lengths'])}
    if kind=='SPLIT':
        reference_receipt=json.loads((directory/'reference_receipt.json').read_bytes())
        if not expected_reference_sha or reference_receipt['raw_sha256']!=expected_reference_sha:raise ValueError('REFERENCE_RECEIPT_IDENTITY_MISMATCH')
        reference=verify(reference_receipt)
        sealed=json.loads((directory/'prefix_inventory_receipt.json').read_bytes())
        if not expected_stage_sha or sealed['raw_sha256']!=expected_stage_sha:raise ValueError('PREFIX_INVENTORY_IDENTITY_MISMATCH')
        inventory=verify(sealed)
        if inventory['reference_receipt']!=reference_receipt or inventory['input_sha256']!=descriptor['input_canonical_sha256']:raise ValueError('PREFIX_INPUT_BINDING_MISMATCH')
        from .adapters import replay,individual
        from .oracle import OracleTrace
        from .comparator import compare_traces
        from .pf16 import witnesses
        result=replay(rows,profile,classifier,case=descriptor['replay_kind'])
        for frame in result['frames']:validate('frame',frame)
        output_receipt=write(directory/'split.json',result)
        oracle=OracleTrace('source-'+str(index),rows)
        comparison=compare_traces(reference['frames'],result['frames'],oracle=oracle)
        u=None
        if descriptor['stage_id']=='ST-12':
            parent=directory.parent/'000'/'stage_result.json'
            uresult=json.loads(parent.read_bytes())
            if uresult['status']!='PASS':raise ValueError('FRESH_U_NOT_PASS')
            u=uresult['checks']
        checks=individual(descriptor,result['snapshot'],fresh_u_checks=u)
        # Repeat in a fresh instance; IDs have deterministic adapter prefix.
        repeat_count=11 if descriptor['stage_id'] in ('C-history','S-history','P15-history') else 2
        repeat_hashes=[sha(canonical(result))]
        repeat_receipts=[]
        for repeat_index in range(1,repeat_count):
            repeated=replay(rows,profile,classifier,case=descriptor['replay_kind'])
            repeat_receipts.append(write(directory/('repeat-%02d.json'%repeat_index),repeated))
            repeat_hashes.append(sha(canonical(repeated)))
            if repeat_hashes[-1]!=repeat_hashes[0]:break
        repeat_ok=len(repeat_hashes)==repeat_count and len(set(repeat_hashes))==1
        matched=witnesses(descriptor,reference['frames'],rows)
        stage={'status':'PASS' if comparison['status']=='PASS' and all(checks.values()) and repeat_ok else 'FAIL',
            'descriptor':descriptor,'checks':checks,'comparison':comparison,'repeat_pass':repeat_ok,
            'PF_witnesses':matched,'reference_receipt':reference_receipt,'split_receipt':output_receipt,'repeat_receipts':repeat_receipts,
            'repeat_hashes':repeat_hashes,'required_snapshot_count':repeat_count,
            'domain':'SYNCHRONOUS_VERIFIED_PLC_ISSUE','mode':'FORMAL_C3_C' if formal else 'DEVELOPMENT_ONLY_NOT_QUALIFICATION'}
        stage_receipt=write(directory/'stage_result.json',stage)
        return {k:stage[k] for k in ('status','checks','comparison','repeat_pass','PF_witnesses')}|{'stage_receipt':stage_receipt}
    if kind in ('PREFIX','PREFIX_ONE'):
        from .evidence import receipt
        from .adapters import replay
        from .observer import reference_rows
        from .oracle import OracleTrace
        from .comparator import compare_traces
        from v0_2.tests.data.tracking_qualification.r46_prefix import select
        stage_raw=(directory/'stage_result.json').read_bytes()
        if not expected_stage_sha or sha(stage_raw)!=expected_stage_sha:raise ValueError('STAGE_RESULT_IDENTITY_MISMATCH')
        stage=json.loads(stage_raw)
        if stage['status']!='PASS':raise ValueError('PREFIX_REQUIRES_VALID_STAGE')
        reference_receipt=stage['reference_receipt']
        reference=verify(reference_receipt)
        invreceipt=json.loads((directory/'prefix_inventory_receipt.json').read_bytes())
        inventory=verify(invreceipt)
        selection={key:inventory[key] for key in ('mandatory_prefix_lengths','output_triggered_progress_lengths','output_triggered_confirmed_lengths','selected_prefix_lengths')}
        conditional=descriptor['stage_id'].startswith('ITQ-')
        rebuilt=select(rows,verify(reference_receipt)['snapshot']['records'])
        if not conditional:
            rebuilt['mandatory_prefix_lengths']=list(range(1,len(rows)+1))
            rebuilt['selected_prefix_lengths']=list(range(1,len(rows)+1))
        if selection!=rebuilt:raise ValueError('PREFIX_SELECTION_NONDETERMINISTIC')
        full=verify(stage['split_receipt'])
        failures=[]
        lengths=selection['selected_prefix_lengths']
        if kind=='PREFIX_ONE':
            if type(prefix_length) is not int or prefix_length not in lengths:raise ValueError('UNSELECTED_PREFIX_REPLAY_FORBIDDEN')
            lengths=[prefix_length]
        for n in lengths:
            reference_partial=reference_rows(rows[:n],profile,classifier,replay_kind=descriptor['replay_kind'])
            if reference_partial['frames']!=reference['frames'][:n]:failures.append({'length':n,'cause':'REFERENCE_PREFIX_DRIFT'});break
            partial=replay(rows[:n],profile,classifier,case=descriptor['replay_kind'])
            # Exact all phase records and 56 fields, not records-only check.
            if partial['frames']!=full['frames'][:n]:failures.append({'length':n,'cause':'SPLIT_PREFIX_DRIFT'});break
        result={'status':'PASS' if not failures else 'FAIL','inventory_receipt':invreceipt,
            'selected_count':len(selection['selected_prefix_lengths']),'failures':failures}
        if kind=='PREFIX_ONE':
            result.update(replayed_prefix_lengths=lengths,
                all_selected_prefixes_replayed=lengths==selection['selected_prefix_lengths'])
        write(directory/('prefix_result.json' if kind=='PREFIX' else 'prefix-%06d-result.json'%prefix_length),result)
        return result
    raise ValueError('UNKNOWN_WORKER_KIND')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',required=True);parser.add_argument('--index',type=int,required=True)
    parser.add_argument('--directory',required=True);parser.add_argument('--lock',required=True)
    parser.add_argument('--expected-reference-sha');parser.add_argument('--expected-stage-sha')
    parser.add_argument('--formal-manifest');parser.add_argument('--authorization');parser.add_argument('--manifest-sha256')
    args=parser.parse_args()
    formal=(args.formal_manifest,args.authorization,args.manifest_sha256) if args.formal_manifest else None
    if formal:formal_authorization(*formal)
    print(json.dumps(execute(args.kind,args.index,args.directory,args.lock,expected_reference_sha=args.expected_reference_sha,
        expected_stage_sha=args.expected_stage_sha,formal=formal),sort_keys=True,allow_nan=False))


if __name__=='__main__':main()
