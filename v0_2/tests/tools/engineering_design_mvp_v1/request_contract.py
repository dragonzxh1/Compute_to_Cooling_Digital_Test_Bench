"""Bounded input contract. Standard library only; safe in the local file server."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = ('tank90', 'six_normal', 'six_step')
LIMITS = dict(rack_count=18, rack_inlet_max_c=45, primary_min_m3_h=330, reserve_s=90, tank_rise_max_k=.5)


def parse(raw):
    def pairs(rows):
        obj = {}
        for k, v in rows:
            if k in obj:
                raise ValueError('DUPLICATE_JSON_KEY')
            obj[k] = v
        return obj
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def check_request(req):
    if not isinstance(req, dict) or req.get('schema') != 'C2C-ENGINEERING-JOB-1' or req.get('model') not in MODELS:
        raise ValueError('UNREGISTERED_MODEL')
    text = req.get('design_json')
    if not isinstance(text, str) or len(text.encode()) > 1024 * 1024:
        raise ValueError('DESIGN_SIZE')
    if hashlib.sha256(text.encode()).hexdigest() != req.get('design_sha256'):
        raise ValueError('INPUT_HASH_MISMATCH')
    d = parse(text)
    if not isinstance(d, dict) or d.get('schema') != 'C2C-ENGINEERING-DESIGN-1' or d.get('requirements') != LIMITS:
        raise ValueError('CUSTOMER_LIMIT_DRIFT')
    contract = parse((HERE / 'data/parameter_contract.json').read_bytes())
    for k, (_, unit, low, high) in contract.items():
        p = d.get('parameters', {}).get(k, {})
        v = p.get('value')
        if p.get('unit') != unit or p.get('kind') not in ('CUSTOMER_DESIGN', 'ENGINEERING_ASSUMPTION', 'OEM_CONFIRMED', 'UNKNOWN') or not isinstance(p.get('source'), str):
            raise ValueError('PARAMETER_PROVENANCE_' + k)
        if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high):
            raise ValueError('PARAMETER_BOUND_' + k)
        if p['kind'] == 'OEM_CONFIRMED' and (not p.get('conditions') or not p.get('evidence')):
            raise ValueError('OEM_EVIDENCE_' + k)
    t = d.get('topology', {})
    for name in ('ports', 'edges', 'circuits'):
        if not isinstance(t.get(name), list) or len(t[name]) > 3000:
            raise ValueError('TOPOLOGY_CONTRACT')
    ids = [p.get('id') for p in t['ports']]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) for i in ids):
        raise ValueError('PORT_IDENTITY')
    for e in t['edges']:
        if e.get('from') not in ids or e.get('to') not in ids:
            raise ValueError('EDGE_ENDPOINT')
    return d
