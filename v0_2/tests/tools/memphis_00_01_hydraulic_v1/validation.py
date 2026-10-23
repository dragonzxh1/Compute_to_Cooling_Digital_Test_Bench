"""Finite budget, envelope, gauge-freedom and short hydraulic diagnostics.

NO full thermal or authorized T2 proof can be inferred from these interfaces.
No pressure offsets are fed into permission decisions.
"""
import csv
import json
import math
import time
from pathlib import Path
from .network import Network,design_speed


def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)


def csvfile(p,rows):
    with p.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def execute(out,stage):
    out.mkdir();here=Path(__file__).parent
    spec=json.loads((here/'network_spec.json').read_bytes())
    basis=json.loads((here/'basis.json').read_bytes())
    save(out/'02_HYDRAULIC_NETWORK_NETLIST.json',spec)
    save(out/'04_PRESSURIZATION_BOUNDARY_MAP.json',basis['pressure_boundary'])
    csvfile(out/'01_00_01_PRESSURE_BUDGET.csv',basis['budgets'])
    checks=[]
    def check(name,condition,details):
        checks.append(dict(test=name,passed=bool(condition),details=details))
        if not condition:save(out/'checks_failed.json',checks);raise AssertionError(name)
    check('SECONDARY_SERIES_BUDGET',abs(sum(x['drop_kPa'] for x in basis['budgets'] if x['circuit']=='SECONDARY')-371.81)<1e-8,'No duplicate parallel branches')
    check('SOURCE_SEPARATE_FROM_LOAD',abs(sum(x['drop_kPa'] for x in basis['budgets'] if x['circuit']=='SOURCE')-96.52)<1e-8,'Tank decoupling; heads never stacked')
    check('LOAD_BUDGET',abs(sum(x['drop_kPa'] for x in basis['budgets'] if x['circuit']=='LOAD')-155.92)<1e-8,'110m3/h CDU equivalent; group330 is not simulated')
    envelopes=[];static=[];unique=[];branch=[]
    for ratio in (1.05,1.15,1.30):
        h0=500*ratio;k=(h0-500)/70**2
        for q in (0,34.185,68.37,70,82.044):
            envelopes.append(dict(family=ratio,flow_m3_h=q,full_speed_head_kPa=h0-k*q*q,
                required_network_head_kPa=371.81*(q/68.37)**2,
                speed_for_68_37=design_speed(ratio),efficiency=None,actual_operating_point='OEM_UNKNOWN',
                nominal_point='70m3/h_500kPa_22kW_CANDIDATE_ONLY',status='RESEARCH_ENVELOPE_NOT_GUARANTEE'))
        net=Network(spec,ratio)
        normal=net.solve(dict(open={'A':True,'B':False},speed={'A':design_speed(ratio),'B':0}))
        q=sum(normal['flow_m3_h'].get('R%02d'%r,0) for r in range(1,7))
        check('DESIGN_POINT_FAMILY_'+str(ratio),abs(q-68.37)<1e-4,dict(flow=q,relative_only=True))
        unique.append(dict(case='NORMAL_'+str(ratio),**{k:normal[k] for k in ('numerical_anchors','physical_pressure_references','connected_zones','incidence_rank','incidence_gauge_nullity','gauge_shift_edge_error_scaled','pressure_status','solver')}))
        save(out/('normal_'+str(ratio)+'.json'),normal)
    for state,opened,speeds in (
        ('NORMAL',{'A':True,'B':False},{'A':design_speed(),'B':0}),
        ('RESEARCH_BOTH_OPEN',{'A':True,'B':True},{'A':design_speed(),'B':design_speed()}),
        ('SPARE_B_ONLY',{'A':False,'B':True},{'A':0,'B':design_speed()}),
        ('DUTY_STOPPED',{'A':True,'B':False},{'A':0,'B':0}),
        ('BOTH_PUMPS_FAILED',{'A':True,'B':True},{'A':0,'B':0})):
        net=Network(spec);r=net.solve(dict(open=opened,speed=speeds));save(out/(state+'.json'),r)
        static.append(dict(case=state,scope='STATIC_CONFIGURATION_NOT_TRANSFER_PERMISSION',
            unit_flow_m3_h=sum(r['flow_m3_h'].get('R%02d'%i,0) for i in range(1,7)),
            physical_gauge=None,cross_HX_dp=None,status='PRESSURE_UNDERDETERMINED'))
        unique.append(dict(case=state,**{k:r[k] for k in ('numerical_anchors','physical_pressure_references','connected_zones','incidence_rank','incidence_gauge_nullity','gauge_shift_edge_error_scaled','pressure_status','solver')}))
        for e in r['edges']:
            branch.append(dict(case=state,edge=e['id'],flow_m3_h=e['flow_m3_s']*3600,dp_kPa=e['pressure_drop_Pa']/1000,
                confidence='BUDGET_RESOLVED_RESEARCH_ALLOCATION',actual_geometry_known=False))
    csvfile(out/'07_SECONDARY_BRANCH_LOSS_ANALYSIS.csv',branch)
    csvfile(out/'05_PUMP_QH_OPERATING_ENVELOPE.csv',envelopes)
    save(out/'08_PRESSURE_UNIQUENESS_TESTS.json',dict(status='PRESSURE_UNDERDETERMINED',tests=unique,
        caveat='Incidence nullity is a LOWER BOUND on pressure freedoms. Closed checks may increase them. Solver rank None is NOT proof of uniqueness.'))
    save(out/'static_states.json',static)
    # The source document's pressure examples are CONDITIONAL algebra, never
    # used as actual fixed pressure boundaries in any network solve.
    cross=[]
    for before in (0,20,50):
        p1=335.89+95.92;p2=60+371.81-before
        cross.append(dict(case='DESIGN_POINT_ALLOCATION_'+str(before),basis='00_B158_B163_B167_B168',
            tank_example_kPa_g=335.89,secondary_example_kPa_g=60,pre_HX_loss_kPa=before,
            P1_HX_IN_example_kPa_g=p1,P2_HX_IN_example_kPa_g=p2,example_abs_dp_kPa=abs(p1-p2),
            required_secondary_reference_min_kPa=50+before,required_secondary_reference_max_kPa=70+before,
            physical_gauge_verified=False,status='CONDITIONAL_SAME_ELEVATION_ONLY'))
    cross.append(dict(case='HISTORICAL_192_412_DECOMPOSITION',basis='run39497147240_30.5s_B',
        tank_example_kPa_g=165,secondary_example_kPa_g=100,pre_HX_loss_kPa=None,
        P1_HX_IN_example_kPa_g=284.009489196,P2_HX_IN_example_kPa_g=476.421825136,
        example_abs_dp_kPa=192.41233594,required_secondary_reference_min_kPa=None,required_secondary_reference_max_kPa=None,
        physical_gauge_verified=False,status='HISTORICAL_RESEARCH_65_PLUS_119.009489_MINUS_376.421825_NOT_CUSTOMER_PRESSURE'))
    csvfile(out/'06_HX_INLET_DIFFERENTIAL_ANALYSIS.csv',cross)
    suction=[dict(equipment=s,min_gauge_kPa=None,NPSHA_m=None,NPSHR_m=None,shutoff_head_kPa=None,MAWP_kPa=None,
        required_min_gauge_kPa=50,status='OPEN',missing='Actual boundary/elevation/OEM QH-NPSHR/relief/compliance/transients') for s in ('SOURCE_PUMP','LOAD_PUMP','CDU_A_PM1','CDU_B_PM1')]
    csvfile(out/'09_PUMP_SUCTION_AND_MAWP_CHECK.csv',suction)
    # Short hydraulic actuator timelines. Gate refuses controlled T2 without
    # measured physical cross-side pressure. Unexpected trip remains independent.
    cases=[]
    for name in ('CONTROLLED_T2_TRANSFER','UNEXPECTED_DUTY_PUMP_TRIP'):
        net=Network(spec);rows=[];start=time.monotonic()
        with (out/(name+'.ndjson')).open('x',encoding='utf8') as raw:
            for tick in range(600):
                t=round(tick*.1,8);trip=name=='UNEXPECTED_DUTY_PUMP_TRIP' and t>=10
                config=dict(open={'A':True,'B':False},speed={'A':0 if trip else design_speed(),'B':0})
                r=net.solve(config)
                qs=[r['flow_m3_h'].get('R%02d'%i,0) for i in range(1,7)]
                row=dict(t_s=t,unit_flow_m3_h=sum(qs),min_rack_flow_m3_h=min(qs),
                    pump_A_actual_speed=config['speed']['A'],pump_B_actual_speed=0,
                    measured_P1_kPa_g=None,measured_P2_kPa_g=None,permission=False,
                    state='PRESSURE_BOUNDARY_HOLD' if t>=10 else 'RESEARCH_INITIAL_OPERATION',
                    kcl_m3_s=max(abs(v) for v in r['node_mass_residual_m3_s']),power_error_W=r['power_error_W'])
                rows.append(row)
                raw.write(json.dumps(dict(row=row,network=r),allow_nan=False)+'\n')
        relevant=rows[100:]
        result=dict(case=name,physical_seconds=60,dt_s=.1,wall_s=time.monotonic()-start,
            zero_flow_duration_s=sum(.1 for r in relevant if r['min_rack_flow_m3_h']<.001),
            deficit_m3=sum(max(0,68.37-r['unit_flow_m3_h'])*.1/3600 for r in relevant),
            min_rack_flow_m3_h=min(r['min_rack_flow_m3_h'] for r in relevant),
            min_unit_flow_m3_h=min(r['unit_flow_m3_h'] for r in relevant),
            takeover_status='NOT_DYNAMICALLY_VERIFIED_PRESSURE_GATE_HOLD',
            continuity_status='FAIL' if name.endswith('TRIP') else 'CONDITIONAL_RESEARCH_INITIAL_PATH_ONLY',
            thermal_status='NOT_DYNAMICALLY_VERIFIED_THIS_HYDRAULIC_STAGE',
            check_valve_model='QUASI_STEADY_COMPLEMENTARITY_NO_CLOSURE_TIME_OR_WATERHAMMER',
            fast_protection='NOT_EXERCISED_NO_THERMAL_OR_REAL_PRESSURE_INPUT',
            engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED')
        csvfile(out/('10_T2_CONTROLLED_TRANSFER_RETEST.csv' if name.startswith('CONTROLLED') else '11_UNEXPECTED_PUMP_TRIP_RETEST.csv'),rows)
        save(out/(name+'_result.json'),result);cases.append(result)
        check(name+'_KCL',max(r['kcl_m3_s'] for r in rows)<1e-8,'Independent saved nodal balances')
        check(name+'_POWER',max(abs(r['power_error_W']) for r in rows)<.01,'Hydraulic input equals friction, no thermal claim')
        if name.endswith('TRIP'):check('TRIP_EXPOSES_FAILURE',result['zero_flow_duration_s']>49.9,'Do not aggregate into PASS')
    save(out/'checks.json',checks)
    result=dict(software_execution='PASS',physical_design='NOT_READY',cases=cases,
        SOURCE_AUTHORITY_STATUS='00_01_RAW_HASH_VERIFIED',HYDRAULIC_NETWORK_STATUS='BUDGET_RESOLVED_REDUCED_MODEL_NOT_AS_BUILT',
        PRESSURE_BOUNDARY_STATUS='OPEN',HX_DIFFERENTIAL_STATUS='PRESSURE_UNDERDETERMINED',
        PUMP_OPERATING_POINT_STATUS='CONDITIONAL_ENVELOPE_NOT_OEM',NUMERICAL_UNIQUENESS_STATUS='PRESSURE_UNDERDETERMINED',
        CONTROLLED_TRANSFER_STATUS='INCOMPLETE_PRESSURE_GATE_HOLD',SUDDEN_FAILURE_STATUS='FAIL_IN_REDUCED_MODEL',
        OEM_CALIBRATION_STATUS='CALIBRATION_REQUIRED',ENGINEERING_APPROVAL_STATUS='MEMPHIS_ENGINEERING_NOT_APPROVED')
    save(out/'stage_result.json',result);return result
