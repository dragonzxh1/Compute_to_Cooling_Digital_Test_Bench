"""Input-only extraction. Never uses historical checks/snapshots as oracle."""
from pathlib import Path
from .common import ROOT, read, sha, canonical, persist


def resolve(pointer, data):
    for key in pointer.split('/')[1:]:
        data = data[key.replace('~1', '/').replace('~0', '~')]
    return data


def extract(descriptor):
    raw = (ROOT / descriptor['result_path']).read_bytes()
    if sha(raw) != descriptor['result_raw_sha256']:
        raise ValueError('MATERIALIZER_SOURCE_MISMATCH')
    import json
    data = json.loads(raw)
    if sha(canonical(data)) != descriptor['result_canonical_sha256']:
        raise ValueError('MATERIALIZER_CANONICAL_SOURCE_MISMATCH')
    rows = resolve(descriptor['input_pointer'], data)
    if len(rows) != descriptor['row_count'] or sha(canonical(rows)) != descriptor['input_canonical_sha256']:
        raise ValueError('MATERIALIZER_INPUT_MISMATCH')
    return {'mode': 'DEVELOPMENT_ONLY_INPUT_MATERIALIZATION',
            'source_descriptor': descriptor, 'observations': rows}


def materialize_all(output):
    spec = read('phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json')
    products = []
    for index, descriptor in enumerate(spec['input_inventory']):
        data = extract(descriptor)
        products.append(persist(Path(output) / ('input-%03d.json' % index), data))
    for entry in spec['ITQ_variants']:
        raw = (ROOT / entry['input_path']).read_bytes()
        if sha(raw) != entry['input_sha256']:
            raise ValueError('FROZEN_ITQ_INPUT_MISMATCH')
    return {'count': len(products), 'ITQ_variants': len(spec['ITQ_variants']),
            'ITQ_cases': len({e['case_id'] for e in spec['ITQ_variants']}), 'products': products}



