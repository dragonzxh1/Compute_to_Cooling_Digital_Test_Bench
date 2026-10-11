"""Strict outer artifact schemas and readback validation, without candidate execution."""
from functools import lru_cache
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .common import ROOT,canonical,sha
from .schemas import obj,array,INT,TEXT,BOOL,HASH,definitions,validate
from .evidence import verify


@lru_cache(maxsize=1)
def schemas():
    receipt=obj({'path':TEXT,'raw_sha256':HASH,'canonical_sha256':HASH,'bytes':{'type':'integer','minimum':0}},required=['path','raw_sha256','bytes'])
    descriptor=obj({'case_key':TEXT,'input_canonical_sha256':HASH,'input_pointer':TEXT,'replay_kind':TEXT,
        'result_canonical_sha256':HASH,'result_path':TEXT,'result_raw_sha256':HASH,'row_count':{'type':'integer','minimum':1},'stage_id':TEXT})
    comparison=obj({'mode':TEXT,'status':TEXT,'findings':array(obj({'rule':TEXT,'pointer':TEXT})),
        'compared_rows':INT,'rules':array(TEXT),'first_divergent_row':INT,'time_ns':{'type':['integer','null']}},required=['mode','status','findings','rules'])
    point=obj({'row_index':INT,'time_ns':INT,'source_id':TEXT})
    stage=obj({'PF_witnesses':{'type':'object','additionalProperties':array(point)},'checks':{'type':'object','additionalProperties':BOOL},
        'comparison':comparison,'descriptor':descriptor,'domain':{'const':'SYNCHRONOUS_VERIFIED_PLC_ISSUE'},'mode':TEXT,
        'reference_receipt':receipt,'repeat_hashes':array(HASH),'repeat_pass':BOOL,'repeat_receipts':array(receipt),
        'required_snapshot_count':{'type':'integer','minimum':2},'split_receipt':receipt,'status':{'enum':['PASS','FAIL']}})
    lengths={'type':'array','uniqueItems':True,'items':{'type':'integer','minimum':1}}
    inventory=obj({'source':{'const':'FRESH_PERSISTED_REFERENCE'},'reference_receipt':receipt,'input_sha256':HASH,
        'mandatory_prefix_lengths':lengths,'output_triggered_progress_lengths':lengths,
        'output_triggered_confirmed_lengths':lengths,'selected_prefix_lengths':lengths,
        'selection_policy':{'enum':['ITQ_FROZEN_CONDITIONAL','SUPPORT_FROZEN_ALL_PREFIXES']}},
        required=['source','reference_receipt','input_sha256','mandatory_prefix_lengths','output_triggered_progress_lengths','output_triggered_confirmed_lengths','selected_prefix_lengths'])
    prefix=obj({'status':{'enum':['PASS','FAIL']},'inventory_receipt':receipt,'selected_count':INT,
        'failures':array(obj({'length':INT,'cause':TEXT}))})
    pre_gate=obj({'returncode':INT,'timeout':BOOL,'parse_error':{'type':['string','null']},'artifacts':array(receipt),'elapsed_s':{'type':'number','minimum':0},
        'execution_controls':obj({'command':array(TEXT),'environment_overrides':{'type':'object','additionalProperties':TEXT},'worker_pid':INT,'timeout_s':{'type':'number','exclusiveMinimum':0}})})
    driver=obj({'status':{'enum':['COMPLETE','INVALID']},'pre_gate_receipt':receipt,'artifacts':array(receipt)})
    snapshot=obj({'confirmed_latched':BOOL,'state':TEXT,'deferred_demand':{'type':['object','null']},
        'progress_pair':{'type':['object','null']},'resolved_pair':{'type':['object','null']},
        **{k:array({'type':'object'}) for k in ('deferred_events','direction_events','epoch_events','lifecycle_events','progress_pair_events',
          'records','resolved_pair_events','response_history','transitions','watch_events')}})
    full_reference=obj({'frames':array({'$ref':'#/$defs/reference'}),'final':{'$ref':'#/$defs/core'},'snapshot':snapshot})
    full_split=obj({'snapshot':snapshot,'frames':array({'$ref':'#/$defs/frame'})})
    witness=obj({'descriptor_index':INT,'source_descriptor':descriptor,'row_index':INT,'time_ns':INT,'source_id':TEXT,
        'observed_preconditions':obj({'PF-%02d'%i:BOOL for i in range(1,17)}),
        'independent_expected_PRE':obj({'state':TEXT,'core_sha256':HASH,'old_command':{'type':'object'}}),
        'independent_expected_POST':obj({'state':TEXT,'core_sha256':HASH}),
        'reference_before_sha256':HASH,
        **{k:definitions()['frame']['properties'][v] for k,v in [('PRE','PRE'),('Safety','SAFETY'),('PLC','PLC'),('POST','POST')]},
        'phase_record_hashes':obj({k:HASH for k in ('PRE','SAFETY','PLC','POST')}),
        'pre_core_sha256':HASH,'authoritative_after_sha256':HASH,
        'causal_eligibility':{'const':'SYNCHRONOUS_VERIFIED_PLC_ISSUE'},
        'expected_behavior_source':TEXT,'comparison':comparison},required=[
        'descriptor_index','source_descriptor','row_index','time_ns','source_id','observed_preconditions',
        'independent_expected_PRE','independent_expected_POST','reference_before_sha256','PRE','Safety','PLC','POST',
        'phase_record_hashes','pre_core_sha256','authoritative_after_sha256','causal_eligibility','expected_behavior_source'])
    pf_row=obj({'id':TEXT,'original_classification':TEXT,'registered_sources':{'type':'array'},
        'normative_precondition':TEXT,'original_scope_result':{'enum':['FAIL','DEVELOPMENT_VALIDATED','INCOMPLETE']},
        'original_witnesses':array(witness),'failed_stages':array(INT),'formal_qualified':{'const':False},
        'supplemental_scope_result':TEXT,'qualification_readiness':TEXT})
    matrix=obj({'campaign_id':TEXT,'original_PF_count':{'const':16},'matrix':{'type':'array','minItems':16,'maxItems':16,'items':pf_row},
        'PF06_proposal':{'type':['object','null']},'original_validated_count':INT,
        'original_matrix_changed':{'const':False},'formal_qualified':{'const':False}})
    eligibility=obj({'STARTUP_ORIGINAL_HISTORICAL':TEXT,'STARTUP_VERSIONED_COMPATIBILITY':TEXT,
        'STARTUP_STRICT_P1_CAUSAL_ELIGIBILITY':TEXT,'nonqualified_case_count':INT,'cases':{'type':'array'},
        'source_provenance_investigation':{'type':'object'},'full_original_scope_ready':BOOL,'formal_qualified':{'const':False}})
    return {**definitions(),'receipt':receipt,'descriptor':descriptor,'stage_result':stage,'prefix_inventory':inventory,
        'prefix_result':prefix,'pre_gate':pre_gate,'driver':driver,'snapshot':snapshot,'full_reference':full_reference,'full_split':full_split,
        'PF_witness':witness,'PF_matrix':matrix,'eligibility':eligibility}


def schema(kind):return {'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':schemas(),'$ref':'#/$defs/'+kind}


def check(kind,data):
    import copy
    s=copy.deepcopy(schema(kind));s['$defs']['frame']={'type':'object'};s['$defs']['reference']={'type':'object'};s['$defs']['core']={'type':'object'}
    Draft202012Validator(s).validate(data)
    if kind=='full_reference':
        validate('core',data['final'])
        for frame in data['frames']:validate('reference',frame)
    elif kind=='full_split':
        for frame in data['frames']:validate('frame',frame)


def validate_run(directory):
    directory=Path(directory)
    counts={};errors=[]
    types={'stage_result.json':'stage_result','prefix_inventory.json':'prefix_inventory','prefix_result.json':'prefix_result',
        'pre_gate_manifest.json':'pre_gate','driver_stage_manifest.json':'driver',
        'PF16_witness_matrix.json':'PF_matrix','startup_eligibility.json':'eligibility'}
    for path in directory.rglob('*.json'):
        kind=types.get(path.name)
        if kind:
            data=json.loads(path.read_bytes());check(kind,data);counts[kind]=counts.get(kind,0)+1
            if kind=='driver':
                verify(data['pre_gate_receipt'])
                for r in data['artifacts']:verify(r)
            if kind=='stage_result':
                for r in [data['reference_receipt'],data['split_receipt'],*data['repeat_receipts']]:check('receipt',r);verify(r)
            if kind=='prefix_result':verify(data['inventory_receipt'])
            if kind=='prefix_inventory':
                ref=verify(data['reference_receipt'])
                n=len(ref['frames']);sets=[data[k] for k in ('mandatory_prefix_lengths','output_triggered_progress_lengths','output_triggered_confirmed_lengths')]
                if data['selected_prefix_lengths']!=sorted(set().union(*map(set,sets))) or any(i>n for i in data['selected_prefix_lengths']):raise ValueError('PREFIX_SCHEMA_SET_INTEGRITY')
                if data.get('selection_policy')=='SUPPORT_FROZEN_ALL_PREFIXES' and data['selected_prefix_lengths']!=list(range(1,n+1)):raise ValueError('SUPPORT_EXHAUSTIVE_PREFIX_REQUIRED')
            if kind=='PF_matrix':
                if [r['id'] for r in data['matrix']]!=['PF-%02d'%i for i in range(1,17)]:raise ValueError('PF_IDENTITIES_INCOMPLETE')
                for row in data['matrix']:
                    for w in row['original_witnesses']:
                        if not w['observed_preconditions'][row['id']]:raise ValueError('PF_VACUOUS_WITNESS')
                if data['PF06_proposal'] is not None:
                    p=data['PF06_proposal'];check('PF_witness',p['positive_witness'])
                    if p['self_approved'] or p['PF06_SUPPLEMENTAL_BINDING_APPROVAL']!='PENDING_USER_REVIEW':raise ValueError('PF06_SELF_APPROVAL_FORBIDDEN')
            if kind=='eligibility':
                if data['nonqualified_case_count']!=len(data['cases']):raise ValueError('ELIGIBILITY_COUNT_MISMATCH')
                for case in data['cases']:
                    if case['strict_P1_Lane_B']!='INCOMPLETE' or case['strict_P1_Lane_C']!='INCOMPLETE' or case['fake_PLC_receipts'] or case['fake_Safety_decisions'] or case['source_sensor_coerced_valid']:raise ValueError('LEGACY_CAUSAL_PROMOTION_FORBIDDEN')
    for key in schemas():Draft202012Validator.check_schema(schema(key))
    return {'passed':True,'validated_artifact_counts':counts,'source_sha256':sha(Path(__file__).read_bytes())}

