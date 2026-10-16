"""Bounded remote-only development checks. No local model execution."""
import os
if os.environ.get('MEMPHIS_VERIFIED_PID')!=str(os.getpid()):raise RuntimeError('VERIFIED_REMOTE_TEST_ONLY')
from dataclasses import replace
from math import fsum
import pytest
from .common import REG,CV
from .plant import ProjectUnit
from .hydraulics import secondary_graph,source_graph,source_comparison,RHO
from .tank import Tank,primary_rates,TransportPipe
from .sources import SourcePlant,tower_capacity
from .coordination import SourceObservation,ProjectProtection,Coordinator,SourcePLC,record,estimated_cold
from v0_2.hydraulics.solver import solve

def observation(**kw):
    d=dict(sample_ns=0,release_ns=100000000,record_id='m',source_speed=.8,source_valve=1.,source_tank='A',source_path='W1',source_flow_m3_s=330/3600,recharge_speed=0.,w1_available=True,w2_available=True,leak_A=False,primary_inlet_c=41.,tank_A_tt_k=(314.,314.,314.,321.),tank_B_tt_k=(314.,314.,314.,321.),primary_load_flow_m3_s=330/3600,wet_inlet_gauge_pa=400000.,maximum_secondary_inlet_c=44.,d1_available=True,d2_available=True)
    d.update(kw);return SourceObservation(**d)

def test_exact_load():assert sum(REG['six_rack']['rack_it_w'])*.95==883500
def test_ua_missing():
    with pytest.raises(ValueError,match='MISSING_EQUIPMENT_UA'):ProjectUnit(None,[1]*6)
def test_ua_not_manufacturer():assert REG['six_rack']['actual_oem_ua_w_k'] is None
def test_individual_flows():
    g,c=secondary_graph([.8,1,1.2,1.4,.9,1.1]);h=solve(g,c,.9,RHO)
    assert len(set(h.branch_flows_m3_s))==6
    assert abs(fsum(h.branch_flows_m3_s)-h.total_flow_m3_s)<1e-14
def test_volumes():assert abs(sum(ProjectUnit(220000,[1]*6).volumes)-1.3)<1e-14
def test_pump_heat_once():
    u=ProjectUnit(220000,[1]*6);r=u.advance_project(0,100000000,.9,314.15,110/3600)
    assert abs(r['pump_to_liquid_w']-r['dp_pa']*r['flow_m3_s']/.65)<1e-8
def test_temperature_not_target_clamp():
    u=ProjectUnit(110000,[1]*6);old=list(u.temperatures);u.advance_project(0,100000000,.9,320.,110/3600)
    assert u.temperatures!=old
def test_tank_flux_conserves():
    t=[314.,315.,320.,321.];r=primary_rates(t,.09,.06,323.,310.,.001,.2)
    assert abs(fsum(r)-CV*(.09*(323-t[0])+.06*(310-t[-1])))<1e-7
def test_tank_full_inventory():
    t=Tank();assert t.volume==15 and t.n==20 and t.cold_volume()==10.5
def test_mixing_not_extra_heat():
    t=[314.,315.,320.,321.]
    assert abs(fsum(primary_rates(t,.09,.06,323,310,.001,.2))-fsum(primary_rates(t,.09,.06,323,310)))<1e-7
def test_a_b_isolated():
    p=SourcePlant(dict());before=list(p.tanks['B'].t);p.tanks['A'].advance(.1,.09,.06,323,310)
    assert p.tanks['B'].t==before
def test_pipe_has_finite_inventory():
    p=TransportPipe();assert p.volume==2.75 and p.n==10
    old=p.t[-1];assert p.advance(.1,.09,310)==old
def test_pid_shutoff_cap():
    assert abs(source_graph('PID')[1].shutoff_head_pa.value/(RHO*9.80665)-18)<1e-10
def test_v9_separate_pressure():
    r=source_comparison();assert all(x['conditional_gauge_pa'] is None for x in r['rows'] if x['variant']=='V9')
def test_npshr_not_inferred():assert source_comparison()['actual_npshr_m'] is None
def test_hot_dry_cannot_cool_to41():assert tower_capacity('D1',.09,41,db=46)==0
def test_safety_location():
    s=ProjectProtection();assert 'SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER' not in s.evaluate(observation(primary_inlet_c=45),100000000)['data']['codes']
    assert 'SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER' in s.evaluate(observation(maximum_secondary_inlet_c=44.6),100000000)['data']['codes']
def test_future_rejected():
    with pytest.raises(ValueError,match='FUTURE'):ProjectProtection().evaluate(observation(),0)
def test_source_wrong_safety_rejected():
    o=observation();s=ProjectProtection().evaluate(o,100000000);r=Coordinator().request(o,s,100000000);r['permission']='wrong'
    with pytest.raises(ValueError,match='BINDING'):SourcePLC().issue(r,s,o,100000000)
def test_open_path_change_rejected():
    o=observation();s=ProjectProtection().evaluate(o,100000000);r=Coordinator().request(o,s,100000000);p=SourcePLC();p.issue(r,s,o,100000000)
    r=dict(r,source_path='W2')
    with pytest.raises(ValueError,match='MOVING_PATH_CHANGE'):p.issue(r,s,o,100000000)
def test_two_roles_rejected():
    o=observation();s=ProjectProtection().evaluate(o,100000000);r=Coordinator().request(o,s,100000000);r.update(source_path='W2',recharge_enable=True)
    with pytest.raises(ValueError,match='TWO_ROLES'):SourcePLC().issue(r,s,o,100000000)
def test_cold_estimator_not_truth():assert estimated_cold((314,314,314,321))==10
def test_seven_grades():assert len(REG['grading'])==7 and 'OEM_CALIBRATION_STATUS' in REG['grading']
