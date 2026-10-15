"""Versioned read-only-input wrappers over frozen aggregate checks.

Only generated-output destinations change. No old evidence file is overwritten.
"""
import json
from pathlib import Path
from v0_2.tests.tools.m1_engine_v3.common import read
from v0_2.tests.tools.m1_engine_v3.evidence import write, receipt, verify
from v0_2.tests.tools.m1_engine_v3.witness_matrix import cut_witness
from v0_2.tests.tools.m1_engine_v3.pf16 import predicates, native
from v0_2.tests.tools.m1_engine_v3.materializer import extract

def aggregate_startup(root,inventory_path,case_root,output_root):
    from v0_2.tests.data.tracking_qualification.r45c_i_startup_guard import judge_startup
    from v0_2.tests.tools.m1_engine_v3.evidence import verify
    root=Path(root);inventory=json.loads(Path(inventory_path).read_bytes())
    combined={'schema':'c2c-pytest-structured-v1','session_complete':True,
        'collected_nodeids':inventory['nodeids'],'reports':[],'collection_errors':[],'exit_status':1}
    domains=[];raw_refs=[]
    for i,node in enumerate(inventory['nodeids']):
        path=root/('%03d'%i)/'node_result.json';data=verify(receipt(path))
        if data['status']!='PASS' or data['nodeid']!=node:raise ValueError('STARTUP_NODE_SOURCE_MISMATCH')
        combined['reports'].extend(data['structured_result']['reports'])
        domains.extend(data['domain_reports']);raw_refs.extend(data['receipts'])
        for item in data['receipts']:verify(item)
    judged=judge_startup(combined,1,read('phase5_r5_2_1r4_5c_i_startup_legacy_signature.json'))
    if judged['status']!='PASS':raise ValueError('ORIGINAL_STARTUP_EXACT_GUARD_FAIL: '+str(judged))
    fresh=[verify(receipt(Path(case_root)/('%03d'%i)/'stage_result.json')) for i in (0,12)]
    compatible=all(r['status']=='PASS' for r in fresh)
    output={'historical_guard':judged,'versioned_compatibility':'PASS' if compatible else 'FAIL',
        'legacy_or_quarantined_cases':[r for r in domains if r['domain_events']],
        'causal_status':'INCOMPLETE' if any(r['domain_events'] for r in domains) else 'PASS','receipts':raw_refs}
    write(Path(output_root)/'combined_pytest_results.json',combined);write(Path(output_root)/'startup_result.json',output)
    return output

def collect_witnesses(root,descriptors,stages,output_root):
    definitions=read('phase5_r5_2_1r4_7_c3_a_pf16_comparison_matrix.json')['rows']
    matrix=[]
    for definition in definitions:
        key=definition['id'];w=[];failed=[]
        for index,summary in stages.items():
            if key not in summary['PF_witnesses']:continue
            stage=verify(summary['stage_receipt'])
            if stage['status']!='PASS':failed.append(index);continue
            points=stage['PF_witnesses'][key]
            if not points:continue
            reference=verify(stage['reference_receipt']);actual=verify(stage['split_receipt'])
            for point in points:
                witness=cut_witness(index,descriptors[index],point['row_index'],reference,actual)
                if witness['observed_preconditions'][key] is not True:raise ValueError('PF_VACUOUS_WITNESS')
                witness['comparison']=stage['comparison'];w.append(witness)
        matrix.append({'id':key,'original_classification':definition['original_classification'],
            'registered_sources':definition['sources'],
            'normative_precondition':definition['original_C1_registered_row']['original_registered_path']['precondition'],
            'original_scope_result':'FAIL' if failed else 'DEVELOPMENT_VALIDATED' if w else 'INCOMPLETE',
            'original_witnesses':w,'failed_stages':failed,'formal_qualified':False,
            'supplemental_scope_result':'NOT_PROPOSED','qualification_readiness':'PENDING_INDEPENDENT_FREEZE_NOT_FORMAL_PASS' if w else 'INCOMPLETE'})
    proposal=None
    candidate_index=next(i for i,d in enumerate(descriptors) if d['stage_id']=='C-history' and d['case_key']=='C8_normal')
    if candidate_index in stages:
        summary=stages[candidate_index];stage=verify(summary['stage_receipt'])
        reference=verify(stage['reference_receipt']);actual=verify(stage['split_receipt'])
        row_index=4
        witness=cut_witness(candidate_index,descriptors[candidate_index],row_index,reference,actual)
        positive=witness['observed_preconditions']['PF-06'] and witness['time_ns']==800000000 and stage['status']=='PASS'
        negatives=[]
        for index,d in enumerate(descriptors):
            if d['stage_id'] not in ('ITQ-24-full','ITQ-27-full') or index not in stages:continue
            negative_stage=verify(stages[index]['stage_receipt']);ref=verify(negative_stage['reference_receipt'])
            rows=extract(d)['observations'];observations=[]
            for n,(f,row) in enumerate(zip(ref['frames'],rows)):
                if row['plc_command']!=f['derived_pre']['old_command']['value']:
                    before=native(f['before']);pre=native(f['derived_pre']['core'])
                    observations.append({'row_index':n,'time_ns':row['time_ns'],
                        'old_epoch_active':bool(before['epoch'] and before['epoch']['completion_reason'] is None),
                        'old_completion_reason':before['epoch']['completion_reason'] if before['epoch'] else None,
                        'PRE_confirmed':pre['confirmed_latched'],'PF06_precondition':predicates(f,row)['PF-06']})
            negatives.append({'descriptor':d,'comparison':negative_stage['comparison'],
                'all_PF06_absent':not any(predicates(f,row)['PF-06'] for f,row in zip(ref['frames'],rows)),
                'observations':observations})
        valid=positive and len(negatives)==2 and all(n['all_PF06_absent'] and n['comparison']['status']=='PASS' for n in negatives)
        proposal={'version':'PF06-C8-NORMAL-SUPPLEMENT-v1','status':'CANDIDATE_FOR_USER_REVIEW',
            'PF06_ORIGINAL_SCOPE':'INCOMPLETE','PF06_SUPPLEMENTAL_SOURCE':'DEVELOPMENT_VALIDATED' if valid else 'INCOMPLETE',
            'PF06_SUPPLEMENTAL_BINDING_APPROVAL':'PENDING_USER_REVIEW',
            'positive_witness':witness,'comparison':stage['comparison'],'negative_controls':negatives,
            'original_matrix_modified':False,'inputs_modified':False,'predicate_modified':False,
            'thresholds_timers_modified':False,'self_approved':False,'campaign_id':root.name}
        for row in matrix:
            if row['id']=='PF-06':row['supplemental_scope_result']=proposal['PF06_SUPPLEMENTAL_SOURCE']
        write(Path(output_root)/'PF06_supplemental_binding_proposal.json',proposal)
    return {'campaign_id':root.name,'original_PF_count':16,'matrix':matrix,'PF06_proposal':proposal,
        'original_validated_count':sum(r['original_scope_result']=='DEVELOPMENT_VALIDATED' for r in matrix),
        'original_matrix_changed':False,'formal_qualified':False}

