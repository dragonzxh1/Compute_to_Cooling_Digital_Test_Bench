"""Exact original PF scope plus prospective PF06 source, never self-approved."""
import json
from .common import ROOT,read,canonical,sha
from .codec import decode
from .pf16 import predicates,native
from .evidence import verify,write
from .materializer import extract


def cut_witness(index,descriptor,row_index,reference,actual):
    ref=reference['frames'][row_index];frame=actual['frames'][row_index]
    row=decode(ref['after']['previous_observation'])
    return {'descriptor_index':index,'source_descriptor':descriptor,'row_index':row_index,
        'time_ns':row['time_ns'],'source_id':row['measurement_record_id'],
        'observed_preconditions':predicates(ref,row),
        'independent_expected_PRE':{'state':decode(ref['derived_pre']['core']['state']),
            'core_sha256':sha(canonical(ref['derived_pre']['core'])),
            'old_command':ref['derived_pre']['old_command']},
        'independent_expected_POST':{'core_sha256':sha(canonical(ref['after'])),
            'state':decode(ref['after']['state'])},
        'reference_before_sha256':sha(canonical(ref['before'])),
        'PRE':frame['PRE'],'Safety':frame['SAFETY'],'PLC':frame['PLC'],'POST':frame['POST'],
        'phase_record_hashes':{k:sha(canonical(frame[k])) for k in ('PRE','SAFETY','PLC','POST')},
        'pre_core_sha256':sha(canonical(frame['pre_core'])),
        'authoritative_after_sha256':sha(canonical(frame['authoritative_after'])),
        'causal_eligibility':'SYNCHRONOUS_VERIFIED_PLC_ISSUE',
        'expected_behavior_source':'FROZEN_ORIGINAL_PRECONDITION_AND_PROTECTED_REFERENCE_MATH_NOT_SUT_OUTPUT'}


def collect(root,descriptors,stages):
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
        write(root/'PF06_supplemental_binding_proposal.json',proposal)
    return {'campaign_id':root.name,'original_PF_count':16,'matrix':matrix,'PF06_proposal':proposal,
        'original_validated_count':sum(r['original_scope_result']=='DEVELOPMENT_VALIDATED' for r in matrix),
        'original_matrix_changed':False,'formal_qualified':False}
