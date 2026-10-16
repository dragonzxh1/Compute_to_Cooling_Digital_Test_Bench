"""Exact bounded matrix; all ranges are exploration assumptions, not confidence intervals."""
from copy import deepcopy
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
V1=HERE.parent/'gb300_m1_closed_loop_v1'


def matrix():
    s=json.loads((HERE/'study.json').read_bytes())
    result={}
    for setting in s['settings']:
        for case in ('LOAD_STEP','PUMP_STUCK'):
            name=setting['id']+'__'+case
            result[name]=dict(id=name,setting=setting,case=case,fault=None,
                group='baseline' if setting['id']=='BASE' else ('sensitivity-a' if setting['id'] in ('UA_LOW','UA_HIGH','PUMP_LOW') else 'sensitivity-b'))
    for fault in s['faults']:
        result[fault['id']]=dict(id=fault['id'],setting=s['settings'][0],case='LOAD_STEP',fault=fault,group='fault')
    for dt in (50,25):
        name='REFINE_STUCK_'+str(dt)
        result[name]=dict(id=name,setting=s['settings'][0],case='PUMP_STUCK',fault=None,dt_ns=dt*10**6,group='baseline')
    return result


def config(spec):
    c=json.loads((V1/'scenario.json').read_bytes())
    c['hx_ua_w_k']*=spec['setting']['ua_scale']
    for key in ('secondary_supply_volume_m3','secondary_return_volume_m3','rack_fluid_volume_each_m3'):
        c[key]*=spec['setting']['inventory_scale']
    c['physics_dt_ns']=spec.get('dt_ns',c['physics_dt_ns'])
    return c
