from math import isfinite
from .audit import need

def validate(spec):
    def walk(v):
        if isinstance(v,dict):
            for x in v.values():walk(x)
        elif isinstance(v,(list,tuple)):
            for x in v:walk(x)
        elif isinstance(v,float):need(isfinite(v),'NONFINITE_INPUT')
    walk(spec)
    need(spec.get('units',{'temperature':'K','flow':'m3/s','pressure':'Pa'})=={'temperature':'K','flow':'m3/s','pressure':'Pa'},'WRONG_UNITS')
    need(spec.get('rack_limit_c',45)==45,'CUSTOMER_LIMIT_DRIFT')
    need(spec.get('liquid_fraction',.95)==.95,'LIQUID_FRACTION_DRIFT')
    need(spec.get('provenance','ENGINEERING_ASSUMPTION') in ('OEM_CONFIRMED','CUSTOMER_DESIGN','ENGINEERING_ASSUMPTION','DERIVED_REQUIREMENT','UNKNOWN'),'PARAMETER_PROVENANCE')
    if spec.get('provenance')=='OEM_CONFIRMED':need(bool(spec.get('OEM_source')) and bool(spec.get('OEM_hash')),'OEM_EVIDENCE_MISSING')
    if 'loads' in spec:need(len(spec['loads'])==6 and all(0<=w<=155000 for w in spec['loads']),'RACK_LOAD_DOMAIN')
    if 'ua' in spec:need(spec['ua']>0,'UA_REQUIRED')
    need(spec.get('dt',.1) in (.1,.05,.025),'BOUNDED_TIME_STEP')
    need(spec.get('racks',6) in (1,6),'RACK_DOMAIN')

def verify_receipt(receipt,permission,measurement_id,now):
    from .audit import digest
    need(digest(receipt['data'])==receipt['sha256'],'RECEIPT_HASH')
    need(receipt['data']['producer']=='MEMPHIS_SIMULATED_BACKUP_PLC','WRONG_PLC_PRODUCER')
    need(receipt['data']['permission_sha256']==permission['sha256'] and permission['data']['measurement_id']==measurement_id,'WRONG_PLC_RECEIPT')
    need(receipt['data']['time_ns']<=now and permission['data']['time_ns']<=now,'FUTURE_PLC_RECEIPT')
