import os
from copy import deepcopy
import pytest
from .validation import validate,verify_receipt
from .engineering import required_ua,equipment,curves
from .audit import digest

@pytest.fixture(autouse=True)
def remote_only():
    assert os.environ.get('MEMPHIS_VERIFIED_PID')==str(os.getpid()),'VERIFIED_REMOTE_TEST_ONLY'

@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite(value):
    with pytest.raises(ValueError,match='NONFINITE'):validate({'ua':value})

@pytest.mark.parametrize('bad',[{'units':{'temperature':'C','flow':'m3/h','pressure':'kPa'}},{'rack_limit_c':46},{'liquid_fraction':.9},{'provenance':'GUESSED'},{'provenance':'OEM_CONFIRMED'},{'ua':0},{'racks':18},{'dt':1},{'loads':[160000]*6},{'fault':'STUCK'}])
def test_registered_refusals(bad):
    with pytest.raises(ValueError):validate(bad)

def test_two_ua_conditions_distinct():
    assert 183<required_ua(894.36,41,44)['required_UA_kW_K']<184
    assert 209<required_ua(1100,41,44)['required_UA_kW_K']<210
    with pytest.raises(ValueError):required_ua(1100,44,41)

def test_missing_oem_never_upgraded():
    e=equipment()
    assert all(v['selection']!='SUITABLE_WITH_OEM_EVIDENCE' for v in e['candidates'])
    assert all(v['OEM_available_UA'] is None for v in e['UA_study'])
    assert curves()['conflict'].startswith('DESIGN_SIGNATURE_REQUIRED')

def test_first_recovery_cannot_hide_second_failure():
    from .audit import first_held,terminal_held
    rows=[{'time_ns':i*1000000000,'flow':1 if i<80 else 0} for i in range(121)]
    assert first_held(rows,lambda r:r['flow']==1)==10
    assert not terminal_held(rows,lambda r:r['flow']==1)
    assert terminal_held(rows,lambda r:r['time_ns']>=0)

def test_source_selection_pre_cut_can_precede_new_opening():
    from .audit import source_change_cut
    source_change_cut({'source_supply_valve':0.,'source_return_valve':0.,'source_speed':0.},
        {'source_supply_valve':.02,'source_return_valve':.02,'source_speed':0.})

@pytest.mark.parametrize('where,key',[('before','source_supply_valve'),('before','source_return_valve'),('before','source_speed'),('after','source_speed')])
def test_illegal_source_selection_is_not_excused_by_later_closed_valve(where,key):
    from .audit import source_change_cut
    a={'source_supply_valve':0.,'source_return_valve':0.,'source_speed':0.};b=dict(a)
    (a if where=='before' else b)[key]=.02
    with pytest.raises(ValueError,match='SOURCE_AB_NOT_ISOLATED'):source_change_cut(a,b)

@pytest.mark.parametrize('change',['producer','permission','future','hash'])
def test_false_plc_receipts(change):
    p={'data':{'time_ns':10,'measurement_id':'m'},'sha256':'p'}
    d={'time_ns':10,'producer':'MEMPHIS_SIMULATED_BACKUP_PLC','permission_sha256':'p'}
    if change=='producer':d['producer']='M1'
    if change=='permission':d['permission_sha256']='wrong'
    if change=='future':d['time_ns']=11
    r={'data':d,'sha256':digest(d)}
    if change=='hash':r['sha256']='wrong'
    with pytest.raises(ValueError):verify_receipt(r,p,'m',10)

def test_backup_starts_only_after_released_tachometer():
    from .unit import Paths,unit_config
    from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import Sensor
    from v0_2.tests.tools.memphis_project_v2.coordination import record
    from v0_2.tests.tools.m1_engine_v3.common import Record
    spec={'id':'test','racks':1};p=Paths(unit_config(spec),spec)
    physical=p.loop.snapshot(0,.9,'initial');o=Sensor(100000000).sample(physical)
    safety=Record.make({'reason_codes':[]})
    p.state='START_BACKUP';p.backup_since=0
    with pytest.raises(ValueError,match='FUTURE'):p.supervise(o,{'sample_ns':0,'release_ns':200000000,'speed':.9,'id':'b'},100000000,safety,.9)
    assert p.state=='START_BACKUP'
