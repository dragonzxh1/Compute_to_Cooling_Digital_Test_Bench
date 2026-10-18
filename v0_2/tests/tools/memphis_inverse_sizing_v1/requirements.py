"""Independent analytic bounds/surfaces. Effective ambient conductance != OEM UA."""
import csv,json
from math import log,fsum
from pathlib import Path
RHO=1009.;CP=4000.;CV=RHO*CP;Q=330/3600;DUTY=2716.15
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False),encoding='utf-8')
def csvout(p,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def analytic(directory):
    from v0_2.tests.tools.memphis_equipment_validation_v2.engineering import required_ua
    from .group_model.hydraulics import source_comparison,source_graph,primary_load_graph
    from v0_2.hydraulics.solver import solve
    surfaces={}
    for mode in ('dry','wet'):
        rows=[]
        for ambient in range(20,47):
            for flow in (264.,300.,330.,360.,400.):
                for outlet in (35.,37.,41.):
                    c=CV*flow/3600000;inlet=outlet+DUTY/c
                    possible=ambient<outlet
                    ua=c*log((inlet-ambient)/(outlet-ambient)) if possible else None
                    rows.append(dict(mode=mode,ambient_C=ambient,ambient_type='DB' if mode=='dry' else 'WB',flow_m3_h=flow,
                        required_kW=DUTY,inlet_C=inlet,outlet_C=outlet,approach_K=outlet-ambient,
                        ideal_thermodynamic_feasibility='CONDITIONALLY_FEASIBLE' if possible else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',
                        effective_fluid_to_ambient_conductance_kW_K=ua,
                        assumed_wet5K_approach_feasible=mode!='wet' or outlet>=ambient+5,
                        actual_air_side_UA=None,fan_or_spray_kW=None,OEM_GUARANTEED_VALUE=None))
        csvout(directory/(mode+'_performance_surface.csv'),rows);surfaces[mode]=rows
    pumps=source_comparison();g,c=primary_load_graph();h=solve(g,c,.9,RHO)
    _,rc,_=source_graph('PID',3);old=rc.shutoff_head_pa.value
    recharge_min=120000+rc.curve_k.value*Q**2
    recharge=dict(required_total_m3_h=330.,required_loop_dp_kPa=120.,required_H0_kPa_at_existing_K=recharge_min/1000,
        old_H0_kPa=old/1000,minimum_H0_factor=recharge_min/old,at_old_H0_maximum_allowed_loop_dp_kPa=(old-rc.curve_k.value*Q**2)/1000,
        minimum_extra_head_kPa=(recharge_min-old)/1000,full_curve_shutoff18m_compliance='NOT_VERIFIED_REQUIRES_RESELECT_OR_RESISTANCE_REDUCTION',
        note='Two alternatives, not combine: raise H0 with same K OR reduce system K; evaluate18m constraint independently')
    budget=dict(IT_kW=2790.,liquid_kW=2650.5,reference_total_reject_kW=DUTY,
        reference_pump_budget_kW=DUTY-2650.5,rule='Forward actual total electrical-to-liquid replaces pump budget; never add both')
    tank=dict(ideal_effective_cold_m3=Q*90,ideal_fraction_in15m3=Q*90/15,
        usable_energy_MJ_at_registered_return=CV*Q*90*(321.44-314.0948)/1e6,
        duty90_energy_MJ=DUTY*90/1000,full_15m3_sensible_energy_MJ=CV*15*(321.44-314.0948)/1e6,
        heat_reference='Sensible energy relative to48.29C return, not latent storage;0.5K outlet requirement still needs forward stratification',
        initial_cold_C=40.9448,return_C=48.29,wall_capacity='UNKNOWN; baseline no wall credit; lumped isothermal wall sensitivity separately')
    precool=[]
    for volume in (1.,2.75,5.):
        for initial in (40.9448,41.,41.5,42.,43.,44.,46.,48.29):
            energy=max(0.,CV*volume*(initial-40.9448))/1e6
            for ready_s in (120.,300.,900.):
                precool.append(dict(volume_m3=volume,initial_C=initial,target_C=40.9448,excess_heat_MJ=energy,
                    ready_time_s=ready_s,ideal_minimum_cooling_kW=energy*1000/ready_s,
                    ideal_minimum_plug_displacement_flow_m3_h=volume/ready_s*3600,
                    condition='Necessary optimistic transport/energy bounds; mixing, heat gain and pump heat increase requirement'))
    csvout(directory/'precool_energy_bounds.csv',precool)
    makeup=[]
    for latent in (2300.,2430.,2450.):
        for coc in (3.,5.):
            ev=DUTY*7200/latent/1000
            makeup.append(dict(latent_kJ_kg=latent,latent_heat_fraction=1.,cycles_of_concentration=coc,
                evaporation_2h_m3=ev,makeup_plus_blowdown_2h_m3=ev*coc/(coc-1),
                drift_leaks_sump_dead_volume_m3=None,OEM_actual_water_m3=None,
                note='Conditional all-latent illustration, not measured actual consumption; sensible fraction and water treatment absent'))
    result=dict(status='ANALYTIC_BOUNDS_COMPUTED_NOT_SYSTEM_APPROVAL',budget=budget,tank=tank,
        CDU=[required_ua(888.12,37,40,secondary_m3_h=49.19),required_ua(894.36,41,44),required_ua(1100,41,44)],
        source_pumps=pumps,recharge=recharge,primary_load=dict(flow_m3_h=h.total_flow_m3_s*3600,head_kPa=h.pump_head_pa/1000,
            electrical_kW_by_efficiency={str(e):Q*h.pump_head_pa/e/1000 for e in (.6,.7,.8)},
            NPSHr_m=None,weakest_MAWP=None,transient_max_pressure=None),
        dry=dict(single_duty_kW=DUTY,three_module_minimum_each_kW=DUTY/3,
            Nminus1_minimum_each_of_two_kW=DUTY/2,DB29_Tout37_Tin=37+DUTY/(CV*Q/1000),
            physical_DB_ceiling_for37C='strictly below37C; usable approach requires OEM air-flow map',
            DB46_Tout41='NO_FEASIBLE_DESIGN_FOR_DRY_ALONE_NO_REFRIGERATION'),
        wet=dict(single_duty_kW=DUTY,five_module_minimum_each_kW=DUTY/5,Nminus1_minimum_each_of_four_kW=DUTY/4,
            WB30_Tout41_Tin=41+DUTY/(CV*Q/1000),WB30_Tout35_Tin=35+DUTY/(CV*Q/1000),
            max_WB_ideal_for41='strictly below41C; under assumed5K approach<=36C, NOT OEM capability',spray_and_fan_requirements=None),
        makeup=makeup,readiness_definitions={
            'SOURCE_READY':'available selected source, open actual valve and actual pump motion; does NOT prove cold water',
            'COLD_WATER_READY':'actual far-end source pipe return<=41.4448C at actual available330; offline truth without installed TT is not controller permission',
            'HYDRAULIC_READY':'actual source/load>=330 and secondary branches>=68.37/6; NPSH/static/transient remain NOT_VERIFIED',
            'THERMAL_READY':'actual rack inlet<=45 with registered full load;40/44 targets separately',
            'FULL_LOAD_RECOVERED':'all above maintained final5s;90s window max<=45; standalone tank0.5K remains independent'},
        fan_electric_kW=None,pump_efficiency_minimum=None,reason_unknown_efficiency='No input motor-power/heat allowance upper bound or OEM eta map; sweep0.6/0.7/0.8, no unique minimum',
        surfaces=surfaces,OEM_CALIBRATION_REQUIRED=True)
    save(directory/'analytic_requirements.json',result)
    return result
