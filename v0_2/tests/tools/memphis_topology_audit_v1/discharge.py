"""Persist complete90s component challenge; exact original rule, no relaxed limit."""
import csv
from math import fsum
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.tank import Tank
from .verify import CV,verify_cv

def full_discharge(profiles,spec,hot_c,path):
    result=[];dt=.05;q=330/3600
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=None
        for name in ('A','B'):
            actual=profiles[name];vol=spec.get('tank_volume_m3',15.)
            for mult in (1,2):
                n=len(actual)*mult;t=Tank(n,volume=vol);t.t=[x for x in actual for _ in range(mult)]
                initial=t.t[0];before=t.energy();worst=initial;net=0.;first_failure=None;net_before_failure=None
                cold=sum(x<=314.5948 for x in actual)*vol/len(actual)
                if initial>314.5948:first_failure=0.;net_before_failure=0.
                for i in range(round(90/dt)):
                    old=t.t[0];u=t.energy();r=t.advance(dt,q,0.,hot_c+273.15,t.t[0],0.,spec.get('short_circuit',0.))
                    step=CV*q*(hot_c+273.15-old)*dt;verify_cv(t.energy()-u,step,u,t.energy(),step)
                    net+=step;worst=max(worst,t.t[0])
                    if first_failure is None and (t.t[0]>314.5948 or t.t[0]-initial>.5):first_failure=(i+1)*dt;net_before_failure=net
                    row=dict(tank=name,layers=n,time_s=(i+1)*dt,flow_m3_h=330,hot_return_C=hot_c,outlet_C=t.t[0]-273.15,
                        rise_K=t.t[0]-initial,maximum_outlet_C=worst-273.15,stored_J=t.energy(),cumulative_absorbed_hot_return_J=net,
                        step_residual_J=r['residual_j'],initial_cold_m3=cold,initial_inventory_gate=cold>=.85*vol)
                    if writer is None:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader()
                    writer.writerow(row)
                result.append(dict(tank=name,layers=n,maximum_outlet_C=worst-273.15,rise_K=worst-initial,
                    status='PASS' if worst<=314.5948 and cold>=.85*vol and worst-initial<=.5 else 'FAIL',
                    first_temperature_or_rise_failure_s=first_failure,absorbed_until_first_failure_J=net_before_failure,
                    total_absorbed_J=net,initial_energy_J=before,final_energy_J=t.energy(),
                    scope='COMPONENT_NO_SOURCE; actual final or pre-event profile, no ideal reset'))
    return result
