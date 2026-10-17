"""Registered engineering assumptions; not OEM identification or new policy."""
import json
from copy import deepcopy
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def registration():
    return json.loads((HERE/'registration.json').read_bytes())

def config(spec):
    a=deepcopy(registration()['assumptions'])
    n=spec['rack_count'];hot=spec.get('boundary','HOT')=='HOT'
    a.update(rack_count=n,case_id=spec['id'],duration_ns=120_000_000_000,
        dt_ns=spec.get('dt_ns',100_000_000),control_period_ns=200_000_000,
        design_flow_m3_s=(68.37 if hot else 49.19)/6*n/3600,
        primary_inlet_k=(41 if hot else 37)+273.15,
        primary_flow_m3_s=110/6*n/3600,
        hx_ua_w_k=220000/6*n*spec.get('ua_scale',1.),
        design_dp_pa=(171630+10000) if n==1 else 371810,
        branch_dp_pa=171630 if n==1 else 171630,
        volumes_m3=([.02]+[.05]+[.02]) if n==1 else ([.1]+[.05]*6+[.1]),
        initial_supply_k=(44 if hot else 40)+273.15,
        initial_speed=.35 if spec.get('load_step') else .9,
        fault=spec.get('fault'),fault_at_ns=10_000_000_000 if spec.get('fault')=='STUCK' else 20_000_000_000,
        load_profile=[{'time_ns':0,'rack_it_w':[38750 if spec.get('load_step') else 155000]*n}])
    if spec.get('load_step'):a['load_profile'].append({'time_ns':10_000_000_000,'rack_it_w':[155000]*n})
    if spec.get('unbalanced'):a['branch_factors']=[.8,1,1.2,1.4,.9,1.1]
    else:a['branch_factors']=[1.]*n
    if not hot:
        # Normal hydraulic reference is a distinct document budget, NOT the
        # same resistance curve validated at both temperature/design points.
        a['design_dp_pa']=219730 if n==6 else 171630*(49.19/68.37)**2+10000
        a['branch_dp_pa']=171630*(49.19/68.37)**2
    a['volumes_m3']=[v*spec.get('inventory_scale',1.) for v in a['volumes_m3']]
    return a

def validate(c):
    from math import isfinite
    def walk(v):
        if isinstance(v,dict):
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,float) and not isfinite(v):raise ValueError('NONFINITE_INPUT')
    walk(c)
    if c['rack_count'] not in (1,6):raise ValueError('ONLY_ONE_OR_SIX_RACKS')
    if c['hx_ua_w_k'] is None or c['hx_ua_w_k']<=0:raise ValueError('MISSING_UA_NOT_OEM_GUARANTEED')
    if len(c['volumes_m3'])!=c['rack_count']+2 or min(c['volumes_m3'])<=0:raise ValueError('INVENTORY_REQUIRED')
    if c['dt_ns'] not in (100_000_000,50_000_000,25_000_000):raise ValueError('BOUNDED_DT')
    if c['duration_ns']!=120_000_000_000:raise ValueError('BOUNDED_HORIZON')
    if c['supply_hard_k']!=318.15 or c['liquid_fraction']!=.95:raise ValueError('FINAL_DESIGN_IDENTITY')
    if c['authority']!='CONDITIONAL_OFFLINE_DEVELOPMENT_NO_QUALIFICATION':raise ValueError('AUTHORITY')
