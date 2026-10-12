"""Captured original Startup nodes, exact legacy identity, no 50/50 relabel."""
import json
import os
from pathlib import Path
from .common import ROOT, read
from .evidence import write, receipt


def collect(directory):
    import pytest
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    code=pytest.main(['--collect-only','-q','v0_2/tests/control/test_phase5_r5_2_1r4_3_startup.py',
        '-o','addopts=','-p','no:cacheprovider','-p','v0_2.tests.data.tracking_qualification.r45c_i_pytest_capture',
        '--c2c-evidence-dir',str(directory)])
    data=json.loads((directory/'pytest_results.json').read_bytes())
    ids=data['collected_nodeids']
    if code!=0 or not data['session_complete'] or data['collection_errors'] or len(ids)!=50 or len(set(ids))!=50:
        raise ValueError('STARTUP_FULL_COLLECTION_INVALID')
    return {'status':'PASS','collection_only':True,'nodeids':ids,'source_path':read('phase5_r5_2_1r4_5c_i_startup_legacy_signature.json')['source_path']}


def execute(index,directory,inventory_path):
    import pytest
    inventory=json.loads(Path(inventory_path).read_bytes())
    ids=inventory['nodeids']
    if inventory['status']!='PASS' or len(ids)!=50 or not 0<=index<50:
        raise ValueError('STARTUP_SHARD_NOT_REGISTERED')
    node=ids[index];directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    os.environ['C2C_STARTUP_NODE_ID']=node
    code=pytest.main(['-q',node,'-o','addopts=','-p','no:cacheprovider',
        '-p','v0_2.tests.tools.m1_engine_v3.startup_shard_plugin',
        '-p','v0_2.tests.data.tracking_qualification.r45c_i_pytest_capture',
        '--c2c-evidence-dir',str(directory),'--m1-domain-log',str(directory/'domain_reports.jsonl'),
        '--junitxml',str(directory/'junit.xml')])
    data=json.loads((directory/'pytest_results.json').read_bytes())
    reports=data['reports']; phases={r['when']:r for r in reports}
    if (not data['session_complete'] or data['collection_errors'] or data['collected_nodeids']!=[node]
        or len(reports)!=3 or set(phases)!={'setup','call','teardown'}
        or any(r['nodeid']!=node or r['wasxfail'] is not None for r in reports)
        or any(phases[p]['outcome']!='passed' for p in ('setup','teardown'))):
        raise ValueError('STARTUP_SHARD_EVIDENCE_INCOMPLETE')
    legacy=False
    if phases['call']['outcome']=='failed':
        signature=read('phase5_r5_2_1r4_5c_i_startup_legacy_signature.json')
        identity=phases['call'].get('failure_identity') or {}
        keys=('source_path','source_raw_sha256','assertion_line_1based','assertion_ast','semantic_identifier','exception_type')
        if code!=1 or node!=signature['nodeid'] or any(identity.get(k)!=signature[k] for k in keys):
            raise ValueError('UNEXPECTED_STARTUP_ASSERTION_FAIL')
        legacy=True
    elif phases['call']['outcome']!='passed' or code!=0:
        raise ValueError('STARTUP_SHARD_UNEXPECTED_OUTCOME')
    domains=[json.loads(line) for line in (directory/'domain_reports.jsonl').read_bytes().splitlines()]
    result={'status':'PASS','execution_acceptance':'EXACT_EXPECTED_LEGACY_FAILURE_PENDING_FRESH_U_V2' if legacy else 'ORIGINAL_TEST_PASS',
        'historical_test_pass':not legacy,'pytest_exitcode':int(code),'nodeid':node,'structured_result':data,
        'domain_reports':domains,'legacy_assertion_preserved':legacy,
        'receipts':[receipt(p) for p in directory.iterdir() if p.is_file()]}
    write(directory/'node_result.json',result)
    return result


def aggregate(root,inventory_path,case_root):
    from v0_2.tests.data.tracking_qualification.r45c_i_startup_guard import judge_startup
    from .evidence import verify
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
    write(root/'combined_pytest_results.json',combined);write(root/'startup_result.json',output)
    return output
