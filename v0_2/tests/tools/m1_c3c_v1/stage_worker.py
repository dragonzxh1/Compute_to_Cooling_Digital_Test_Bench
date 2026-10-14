"""Formal dispatcher with original checks and a separately authorized driver."""
import json
import os
import sys
import unittest
from pathlib import Path
from .runtime_admission import ROOT, admit
from v0_2.tests.tools.m1_remote_control_v3.progress import mark

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
        from .source_lock import create as source_lock
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
    if stage=='STARTUP_COLLECT':
        from v0_2.tests.tools.m1_engine_v3.startup_execution import collect
        data=collect(root/'startup_collection')
        write(Path(os.environ['C2C_M1_REFERENCE_ROOT']).parent/'startup_inventory.json',data)
        return data
    if stage.startswith('STARTUP-'):
        from v0_2.tests.tools.m1_engine_v3.startup_execution import execute as startup_execute
        inventory=Path(os.environ['C2C_M1_REFERENCE_ROOT']).parent/'startup_inventory.json'
        return startup_execute(int(stage.split('-')[1]),inventory.parent/'startup'/('%03d'%int(stage.split('-')[1])),inventory)
    if stage=='REFERENCE_GROUPS':
        from v0_2.tests.tools.m1_engine_v3.final_validation import groups
        return {'status':'PASS','groups':groups(os.environ['C2C_M1_REFERENCE_ROOT'],reference=True)}
    if stage=='FINAL_ACCEPTANCE':
        from .final_gate import finalize
        return finalize(Path(os.environ['C2C_M1_REFERENCE_ROOT']).parent)
    pieces=stage.split('-')
    if len(pieces)<3 or pieces[0]!='CASE':raise ValueError('UNKNOWN_STREAM_CONTROL_STAGE')
    index,kind=int(pieces[1]),pieces[2]
    if not 0<=index<101:raise ValueError('UNREGISTERED_DESCRIPTOR')
    from .stream_worker import execute as run_stage
    if kind=='SCHEMA':
        from v0_2.tests.tools.m1_engine_v3.final_validation import case_schema
        return case_schema(index,Path(os.environ['C2C_M1_REFERENCE_ROOT'])/('%03d'%index))
    if kind=='PREFIX_BATCH':
        import time
        lengths=json.loads(os.environ['C2C_M1_PREFIX_BATCH_LENGTHS'])
        if not lengths or len(lengths)!=len(set(lengths)) or any(type(n) is not int for n in lengths):
            raise ValueError('PREFIX_BATCH_INVENTORY_INVALID')
        directory=Path(os.environ['C2C_M1_REFERENCE_ROOT'])/('%03d'%index)
        started=time.monotonic();completed=[]
        for n in lengths:
            # This is an external execution budget, NOT a tracking/fixture timer.
            # Yield only between complete fresh-from-t0 replays, never within one.
            if completed and time.monotonic()-started>=60:
                break
            result=run_stage('PREFIX_ONE',index,directory,root/'source_lock.json',prefix_length=n)
            if result['status']!='PASS':
                return {'status':'FAIL','completed_lengths':completed,'failed_prefix':n,'result':result}
            completed.append(n)
        if not completed:raise ValueError('PREFIX_BATCH_MADE_NO_PROGRESS')
        return {'status':'PASS','coverage_status':'COMPLETE_BATCH' if len(completed)==len(lengths) else 'PARTIAL_BATCH_EXPLICIT_REMAINING',
            'completed_lengths':completed,'remaining_lengths':lengths[len(completed):],
            'each_replay_new_model_from_t0':True,'individual_result_files_required':True}
    kwargs={}
    if kind=='PREFIX_ONE':kwargs['prefix_length']=int(pieces[3])
    if kind=='REPEAT':kwargs['repeat_index']=int(pieces[3])
    directory=Path(os.environ['C2C_M1_REFERENCE_ROOT'])/('%03d'%index)
    return run_stage(kind,index,directory,root/'source_lock.json',**kwargs)
