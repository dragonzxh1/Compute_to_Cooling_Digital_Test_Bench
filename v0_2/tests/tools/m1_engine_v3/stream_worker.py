"""Fresh full-case stages and each selected prefix in bounded owned children."""
import json
from pathlib import Path
from .common import read, canonical, sha
from .package_guard import development
from .materializer import extract
from .evidence import write, receipt, verify
from .stream_trace import TraceReader, OracleBridge
from .replay_stream import write_reference, write_split, reference_frames, split_frames
from .adapters import individual


def execute(kind, index, directory, lock_path, *, prefix_length=None, repeat_index=None):
    development(lock_path)
    descriptor = read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')['input_inventory'][index]
    rows = extract(descriptor)['observations']
    profile = read('phase5_r5_2_2_fixture_tracking_profile.json')
    classifier = read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
    directory = Path(directory)
    if kind == 'REFERENCE':
        item = write_reference(rows, profile, classifier, directory/'reference.json', replay_kind=descriptor['replay_kind'])
        write(directory/'reference_receipt.json', item)
        reference = TraceReader(directory/'reference.json', item)
        u = None
        if descriptor['stage_id'] == 'ST-12':
            u = verify(receipt(directory.parent/'000'/'reference_checks.json'))
        checks = individual(descriptor, reference.metadata['snapshot'], fresh_u_checks=u)
        write(directory/'reference_checks.json', checks)
        if not all(checks.values()):
            raise ValueError('FROZEN_REFERENCE_EXPECTATION_FAIL: '+str(checks))
        return {'status':'PASS','receipt':item,'row_count':len(rows),'checks':checks}
    reference_receipt = json.loads((directory/'reference_receipt.json').read_bytes())
    reference = TraceReader(directory/'reference.json', reference_receipt)
    reference.verify_headers()
    if kind == 'SELECT':
        from v0_2.tests.data.tracking_qualification.r46_prefix import select
        selection = select(rows, reference.metadata['snapshot']['records'])
        conditional = descriptor['stage_id'].startswith('ITQ-')
        if not conditional:
            selection['mandatory_prefix_lengths'] = list(range(1,len(rows)+1))
            selection['selected_prefix_lengths'] = list(range(1,len(rows)+1))
        rebuilt = select(rows, reference.metadata['snapshot']['records'])
        if not conditional:
            rebuilt['mandatory_prefix_lengths'] = list(range(1,len(rows)+1))
            rebuilt['selected_prefix_lengths'] = list(range(1,len(rows)+1))
        if selection != rebuilt:
            raise ValueError('PREFIX_SELECTION_NONDETERMINISTIC')
        inventory = {'source':'FRESH_PERSISTED_REFERENCE','reference_receipt':reference_receipt,
            'selection_policy':'ITQ_FROZEN_CONDITIONAL' if conditional else 'SUPPORT_FROZEN_ALL_PREFIXES',
            'input_sha256':descriptor['input_canonical_sha256'],**selection}
        item = write(directory/'prefix_inventory.json', inventory)
        write(directory/'prefix_inventory_receipt.json', item)
        verify(item)
        return {'status':'PASS','inventory_receipt':item,'selected_count':len(selection['selected_prefix_lengths'])}
    invreceipt = json.loads((directory/'prefix_inventory_receipt.json').read_bytes())
    inventory = verify(invreceipt)
    if inventory['reference_receipt'] != reference_receipt or inventory['input_sha256'] != descriptor['input_canonical_sha256']:
        raise ValueError('PREFIX_INPUT_BINDING_MISMATCH')
    repeat_count = 11 if descriptor['stage_id'] in ('C-history','S-history','P15-history') else 2
    if kind == 'SPLIT':
        split_receipt = write_split(rows, profile, classifier, directory/'split.json', case=descriptor['replay_kind'])
        split = TraceReader(directory/'split.json', split_receipt)
        from .oracle import OracleTrace
        from .comparator import compare_traces
        from .pf16 import witnesses
        comparison = compare_traces(reference, split, oracle=OracleBridge(OracleTrace('source-'+str(index),rows),reference))
        u = None
        if descriptor['stage_id'] == 'ST-12':
            uresult = verify(receipt(directory.parent/'000'/'stage_result.json'))
            if uresult['status'] != 'PASS':
                raise ValueError('FRESH_U_NOT_PASS')
            u = uresult['checks']
        checks = individual(descriptor, split.metadata['snapshot'], fresh_u_checks=u)
        preliminary = {'descriptor':descriptor,'checks':checks,'comparison':comparison,
            'PF_witnesses':witnesses(descriptor,reference,rows),'reference_receipt':reference_receipt,
            'split_receipt':split_receipt,'required_snapshot_count':repeat_count,
            'status':'PASS' if comparison['status']=='PASS' and all(checks.values()) else 'FAIL'}
        item = write(directory/'split_preliminary.json', preliminary)
        return {'status':preliminary['status'],'preliminary_receipt':item,'comparison':comparison,'checks':checks}
    if kind == 'REPEAT':
        if type(repeat_index) is not int or not 1 <= repeat_index < repeat_count:
            raise ValueError('REPEAT_NOT_PREREGISTERED')
        first = verify(receipt(directory/'split_preliminary.json'))
        if first['status'] != 'PASS':
            raise ValueError('REPEAT_REQUIRES_VALID_SPLIT')
        repeated = write_split(rows, profile, classifier, directory/('repeat-%02d.json'%repeat_index), case=descriptor['replay_kind'])
        if repeated['canonical_sha256'] != first['split_receipt']['canonical_sha256']:
            raise ValueError('REPEAT_NONDETERMINISTIC')
        return {'status':'PASS','repeat_receipt':repeated}
    if kind == 'SEAL':
        first = verify(receipt(directory/'split_preliminary.json'))
        repeated = [receipt(directory/('repeat-%02d.json'%i)) for i in range(1,repeat_count)]
        hashes = [first['split_receipt']['canonical_sha256']]
        for item in repeated:
            repeated_trace = TraceReader(directory/Path(item['path']).name,item)
            repeated_trace.verify_headers()
            hashes.append(item['canonical_sha256'])
        repeat_ok = len(hashes)==repeat_count and len(set(hashes))==1
        stage = {**first,'repeat_hashes':hashes,'repeat_receipts':repeated,'repeat_pass':repeat_ok,
                 'domain':'SYNCHRONOUS_VERIFIED_PLC_ISSUE','mode':'DEVELOPMENT_ONLY_NOT_QUALIFICATION'}
        stage['status'] = 'PASS' if first['status']=='PASS' and repeat_ok else 'FAIL'
        from .artifact_schemas import check
        check('stage_result',stage)
        item = write(directory/'stage_result.json',stage)
        return {k:stage[k] for k in ('status','checks','comparison','repeat_pass','PF_witnesses')}|{'stage_receipt':item}
    if kind == 'PREFIX_ONE':
        if type(prefix_length) is not int or prefix_length not in inventory['selected_prefix_lengths']:
            raise ValueError('UNSELECTED_PREFIX_REPLAY_FORBIDDEN')
        stage = verify(receipt(directory/'stage_result.json'))
        if stage['status']!='PASS':
            raise ValueError('PREFIX_REQUIRES_VALID_STAGE')
        full_split = TraceReader(directory/'split.json',stage['split_receipt']); full_split.verify_headers()
        prefix_dir = directory/'prefixes'/('%06d'%prefix_length)
        prefix_dir.mkdir(parents=True,exist_ok=False)
        ref_iter = reference_frames(rows[:prefix_length],profile,classifier,replay_kind=descriptor['replay_kind'])
        split_iter = split_frames(rows[:prefix_length],profile,classifier,prefix_dir/'completed.jsonl',case=descriptor['replay_kind'])
        results=[]; failures=[]
        try:
            for i,(r,s) in enumerate(zip(ref_iter,split_iter)):
                rraw,sraw = canonical(r),canonical(s)
                r_expected,s_expected = reference.raw(i),full_split.raw(i)
                if rraw!=r_expected or sraw!=s_expected:
                    for label,raw in (('reference_actual',rraw),('split_actual',sraw),('reference_expected',r_expected),('split_expected',s_expected)):
                        write(prefix_dir/('divergent-%03d-%s.json'%(i,label)),raw)
                    failures.append({'length':prefix_length,'cause':'REFERENCE_PREFIX_DRIFT' if rraw!=r_expected else 'SPLIT_PREFIX_DRIFT'})
                    break
                results.append({'row':i,'reference_sha256':sha(rraw),'split_sha256':sha(sraw),
                    'full_reference_sha256':sha(r_expected),'full_split_sha256':sha(s_expected)})
                del r,s,rraw,sraw,r_expected,s_expected
        finally:
            ref_iter.close(); split_iter.close()
        if len(results)!=prefix_length and not failures:
            raise ValueError('PREFIX_ROW_COUNT_INCOMPLETE')
        item = write(prefix_dir/'row_comparison_receipts.json',results)
        result = {'status':'PASS' if not failures else 'FAIL','inventory_receipt':invreceipt,
            'selected_count':len(inventory['selected_prefix_lengths']),'failures':failures,
            'replayed_prefix_lengths':[prefix_length],'all_selected_prefixes_replayed':inventory['selected_prefix_lengths']==[prefix_length],
            'compared_complete_frames':len(results),'row_receipts':item,'starts_from_t0':True}
        write(directory/('prefix-%06d-result.json'%prefix_length),result)
        return result
    raise ValueError('UNKNOWN_STREAM_STAGE')
