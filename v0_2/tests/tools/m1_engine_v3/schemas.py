"""Strict serialized phase/frame schemas; binding semantics checked separately."""
from jsonschema import Draft202012Validator
from .observer import FIELDS
from .common import read
from functools import lru_cache
from jsonschema.exceptions import ValidationError
import re

INT={'type':'integer'}
TEXT={'type':'string'}
BOOL={'type':'boolean'}
HASH={'type':'string','pattern':'^[0-9a-f]{64}$'}
NULL_INT={'type':['integer','null']}
NUMBER={'type':'number'}
NULL_NUMBER={'type':['number','null']}


def obj(properties,required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}


def array(items):return {'type':'array','items':items}


@lru_cache(maxsize=1)
def definitions():
    typed={'oneOf':[
        obj({'type':{'enum':['none','absent']}}),
        obj({'type':{'const':'bool'},'value':BOOL}),
        obj({'type':{'const':'int'},'value':INT}),
        obj({'type':{'const':'str'},'value':TEXT}),
        obj({'type':{'const':'float64'},'bits':{'type':'string','pattern':'^[0-9a-f]{16}$'}}),
        obj({'type':{'enum':['list','tuple','set']},'items':array({'$ref':'#/$defs/typed'})}),
        obj({'type':{'const':'dict'},'fields':{'type':'object','additionalProperties':{'$ref':'#/$defs/typed'}}}),
        obj({'type':{'const':'dataclass'},'class':TEXT,'fields':{'type':'object','additionalProperties':{'$ref':'#/$defs/typed'}}})]}
    core=obj({k:{'$ref':'#/$defs/typed'} for k in FIELDS})
    row=obj({'time_ns':INT,'plc_command':NUMBER,'command_timestamp_ns':INT,'measured_speed':NULL_NUMBER,
        'sample_ns':NULL_INT,'release_ns':NULL_INT,'quality':TEXT,'measurement_record_id':TEXT})
    states=list(read('phase5_r5_2_1r4_7_c2_r1_timing_policy_registration.json')['safety_mapping'])
    state={'enum':states}
    base={'phase':TEXT,'record_id':TEXT,'transaction_id':TEXT,'time_ns':INT}
    measurement=obj({k:v for k,v in row['properties'].items() if k not in ('plc_command','command_timestamp_ns')}|{'provenance':{'enum':['CERTIFIED_INTERVAL_END','POST_COMMAND_EFFECT','UNKNOWN']}})
    pre=obj(base|{'phase':{'const':'PRE'},'measurement':measurement,
        'old_command':obj({'value':NUMBER,'issue_ns':INT,'identity':TEXT}),
        'old_epoch_id':{'type':['string','null']},'state':state,
        'contribution':obj({'severity':TEXT,'reason_codes':array(TEXT),'restriction':{'type':['string','null']}}),
        'evidence_commit_id':TEXT,'source_id':TEXT,'core_digest':HASH})
    safety=obj(base|{'phase':{'const':'SAFETY'},'pre_record_id':TEXT,'pre_digest':HASH,'severity':TEXT,
        'reason_codes':array(TEXT),'independent_channels':array(obj({'code':TEXT,'severity':TEXT})),
        'retained_fault_reasons':array(TEXT),'scope':{'const':'SAFETY_MAPPING_POLICY_ASSERTION'},
        'numeric_envelope_authorization':{'const':'OUT_OF_SCOPE'}})
    plc=obj(base|{'phase':{'const':'PLC'},'producer':{'const':'SIMULATED_PLC'},'scope':{'const':'SIMULATED_PLC_CAUSAL_OWNERSHIP'},
        'value_scope':{'const':'FIXTURE_EXOGENOUS_COMMAND_VALUE'},'numeric_hardware_authorization':{'const':'OUT_OF_SCOPE'},
        'command':NUMBER,'issue_ns':INT,'command_id':TEXT,'plc_cycle_id':TEXT,'safety_id':TEXT,'safety_digest':HASH})
    post=obj(base|{'phase':{'const':'POST'},'pre_id':TEXT,'plc_id':TEXT,'state':state,
        'confirmed_latched':BOOL,'enrolled_new_command':BOOL})
    link=obj({'policy':{'const':'M1-SEM01-POST-LEGACY-HISTORY-v1'},'entry_index':INT,'transaction_id':TEXT,
        'pre_id':TEXT,'pre_digest':HASH,'pre_core_digest':HASH,'plc_id':TEXT,'plc_digest':HASH,
        'source_id':TEXT,'watch_id':TEXT,'obligation_id':TEXT,'old_command_id':TEXT,'new_command_id':TEXT,
        'old_issue_ns':INT,'new_issue_ns':INT,'authoritative_entry_digest':HASH,'projected_entry_digest':HASH})
    access=obj({'actor':{'enum':['PRE','SIMULATED_PLC']},'kind':{'enum':['PRIOR_COMMAND_READ','MEASUREMENT_READ','VERIFIED_OUTPUT_TOKEN','DENIED_FUTURE_COMMAND_ACCESS']},
        'command_id':TEXT,'name':TEXT,'record_id':TEXT},required=['actor','kind'])
    core_ref={'$ref':'#/$defs/core'}
    frame=obj({'before':core_ref,'pre_core':core_ref,'after':core_ref,'authoritative_after':core_ref,'PRE':pre,'SAFETY':safety,'PLC':plc,'POST':post,
        'legacy_projection_bindings':array(link),'immutable_pre_digest':HASH,'immutable_safety_digest':HASH,
        'access_log':array(access),'commits':array(TEXT),'status':{'const':'COMPLETE'},'command_issue_status':{'const':'ISSUED'}})
    derived=obj({'kind':{'const':'DERIVED_INDEPENDENT_OLD_INTERVAL_EXPECTATION_NOT_HISTORICAL_GOLDEN'},'core':core_ref,
        'old_command':obj({'value':NUMBER,'issue_ns':INT,'identity':TEXT}),'valid':BOOL,'eligible':BOOL,'active':BOOL,'source_id':TEXT,
        'evaluation':{'type':['object','null']}})
    ref=obj({'before':core_ref,'after':core_ref,'input_provenance':TEXT,'derived_pre':derived})
    return {'typed':typed,'core':core,'input':row,'frame':frame,'reference':ref}


def schema(kind):
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':definitions(),'$ref':'#/$defs/'+kind}


def typed(value):
    if type(value) is not dict or 'type' not in value:raise ValidationError('typed object required')
    kind=value['type']
    if kind in ('none','absent'):
        if set(value)!={'type'}:raise ValidationError('null presence keys')
        return
    scalar={'bool':bool,'int':int,'str':str}
    if kind in scalar:
        if set(value)!={'type','value'} or type(value['value']) is not scalar[kind]:raise ValidationError('typed scalar identity')
    elif kind=='float64':
        if set(value)!={'type','bits'} or type(value['bits']) is not str or not re.fullmatch('[0-9a-f]{16}',value['bits']):raise ValidationError('float64 bits')
    elif kind in ('list','tuple','set'):
        if set(value)!={'type','items'} or type(value['items']) is not list:raise ValidationError('typed sequence')
        for item in value['items']:typed(item)
    elif kind in ('dict','dataclass'):
        if set(value)!=({'type','fields','class'} if kind=='dataclass' else {'type','fields'}):raise ValidationError('typed mapping keys')
        if kind=='dataclass' and type(value['class']) is not str:raise ValidationError('dataclass identity')
        if type(value['fields']) is not dict:raise ValidationError('typed fields mapping')
        for key,item in value['fields'].items():
            if type(key) is not str:raise ValidationError('typed field name')
            typed(item)
    else:raise ValidationError('unknown typed kind')


def validate_core(value):
    if type(value) is not dict or set(value)!=set(FIELDS):raise ValidationError('exact 56-field inventory required')
    for field in FIELDS:typed(value[field])


@lru_cache(maxsize=8)
def validator(kind):
    import copy
    s=copy.deepcopy(schema(kind))
    # Equivalent fast compiled core predicate replaces expensive repeated oneOf
    # traversal of growing immutable ledgers. All nested typed values checked above.
    s['$defs']['core']=obj({k:{} for k in FIELDS})
    return Draft202012Validator(s)


def validate(kind,value):
    if kind=='input':
        import math
        for key in ('plc_command','measured_speed'):
            if value.get(key) is not None and not math.isfinite(value[key]):raise ValidationError('nonfinite input not admitted')
    if kind=='frame':
        for name in ('before','pre_core','after','authoritative_after'):validate_core(value[name])
    elif kind=='reference':
        for name in ('before','after'):validate_core(value[name])
        validate_core(value['derived_pre']['core'])
    elif kind=='core':validate_core(value)
    elif kind=='typed':typed(value)
    validator(kind).validate(value)


def selfcheck():
    for key in definitions():Draft202012Validator.check_schema(schema(key))
    return True
