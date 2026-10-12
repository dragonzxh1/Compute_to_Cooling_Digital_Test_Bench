"""Development only: exact original checks plus versioned streaming adapter."""
import json
import os
import sys
import unittest
from pathlib import Path
from .admission import ROOT, admit
from .progress import mark

UNIT_GROUPS = {'CORE_UNIT_PROJECTION':('test_projection',12),
    'CORE_UNIT_STATE_COPY':('test_state_copy',3),'CORE_UNIT_INFRASTRUCTURE':('test_infrastructure',8),
    'CORE_UNIT_CAMPAIGN_PROTOCOL':('test_campaign_protocol',4)}


class BoundaryResult(unittest.TextTestResult):
    def startTest(self,test):
        mark('BEGIN','UNIT_TEST',test_id=test.id()); super().startTest(test)
    def stopTest(self,test):
        super().stopTest(test); mark('END','UNIT_TEST',test_id=test.id())


def execute(stage, root):
    admit()
    root=Path(root)
    from v0_2.tests.tools.m1_engine_v3.common import read, guard, sha
    from v0_2.tests.tools.m1_engine_v3.evidence import write
    if stage=='INPUT_INTEGRITY':
        from v0_2.tests.tools.m1_engine_v3.materializer import materialize_all
        from v0_2.tests.tools.m1_engine_v3.runner import source_lock
        guard(); inventory=materialize_all(root/'inputs')
        if (inventory['count'],inventory['ITQ_cases'],inventory['ITQ_variants'])!=(101,23,51):
            raise ValueError('COMPLETE_INPUT_INVENTORY_MISMATCH')
        item=write(root/'source_lock.json',source_lock())
        return {'status':'PASS','input_inventory':inventory,'source_lock_receipt':item}
    if stage=='CORE_IDENTITY':
        from v0_2.tests.tools.m1_engine_v3.schemas import selfcheck
        selfcheck()
        for name in ('engine.py','codec.py','comparator.py','scheduler.py','state_copy.py','pre_oracle.py','projection.py','pf16.py','schemas.py'):
            if (ROOT/'v0_2/tests/tools/m1_engine_v3'/name).read_bytes()!=(ROOT/'v0_2/tests/tools/c3b_v14_1'/name).read_bytes():
                raise ValueError('NINE_CORE_SOURCE_DRIFT')
        return {'status':'PASS','nine_core_files_identical':True}
    if stage in UNIT_GROUPS:
        module,count=UNIT_GROUPS[stage]
        tests=unittest.defaultTestLoader.loadTestsFromName('v0_2.tests.tools.m1_engine_v3.'+module)
        if tests.countTestCases()!=count:raise ValueError('ORIGINAL_UNIT_CASE_COUNT_DRIFT')
        result=unittest.TextTestRunner(verbosity=2,resultclass=BoundaryResult).run(tests)
        return {'status':'PASS' if result.wasSuccessful() and result.testsRun==count else 'FAIL',
            'tests_run':result.testsRun,'expected_count':count,'failures':len(result.failures),'errors':len(result.errors)}
    if stage=='CMP_NEGATIVE':
        from v0_2.tests.tools.m1_engine_v3.selfcheck import main
        original=sys.argv; sys.argv=['selfcheck','--output-root',str(root/'CMP'/'artifacts')]
        try:main()
        finally:sys.argv=original
        files=list((root/'CMP').rglob('development-evidence.json'))
        if len(files)!=1:raise ValueError('CMP_EVIDENCE_MISSING')
        data=json.loads(files[0].read_bytes())
        if len(data['checks'])!=18 or not all(c['passed'] for c in data['checks']):raise ValueError('CMP_NEGATIVE_FAIL')
        return {'status':'PASS','check_count':18,'evidence_raw_sha256':sha(files[0].read_bytes())}
    if stage.startswith('STREAM_EQ_'):
        index=int(stage.split('_')[-1])
        if index not in (0,12,15,65):raise ValueError('UNREGISTERED_EQUIVALENCE_INPUT')
        from v0_2.tests.tools.m1_engine_v3.test_stream import equivalence
        return equivalence(index,root/stage)
    pieces=stage.split('-')
    if len(pieces)<3 or pieces[0]!='CASE':raise ValueError('UNKNOWN_STREAM_CONTROL_STAGE')
    index,kind=int(pieces[1]),pieces[2]
    if not 0<=index<101:raise ValueError('UNREGISTERED_DESCRIPTOR')
    from v0_2.tests.tools.m1_engine_v3.stream_worker import execute as run_stage
    kwargs={}
    if kind=='PREFIX_ONE':kwargs['prefix_length']=int(pieces[3])
    if kind=='REPEAT':kwargs['repeat_index']=int(pieces[3])
    directory=Path(os.environ['C2C_M1_REFERENCE_ROOT'])/('%03d'%index)
    return run_stage(kind,index,directory,root/'source_lock.json',**kwargs)
