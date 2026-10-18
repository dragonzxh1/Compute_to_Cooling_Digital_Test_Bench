"""Project six-rack extension: six inlet volumes, six rack volumes, supply/return.

Uses existing HX, fluid, pump-energy and hydraulic solver. No prescribed target
is assigned back to actual temperature, flow or branch pressure.
"""
from math import fsum,isfinite
from dataclasses import replace
from v0_2.tests.tools.gb300_m1_closed_loop_v1.plant import SixRackPlant,PhysicalSnapshot
from v0_2.cdu.heat_exchanger import evaluate
from v0_2.hydraulics.solver import solve
from v0_2.hydraulics.pump import pump_energy
from .common import REG,RHO,CP,CV,check,rounding_bound
from .hydraulics import secondary_graph,drive

class ProjectUnit(SixRackPlant):
    def __init__(self,ua,factors):
        check(ua is not None and ua>0,'INCOMPLETE_MISSING_EQUIPMENT_UA')
        # Inherit the existing fluid/HX construction, replacing only new scenario
        # inputs. V1 source and expectations are neither edited nor reinterpreted.
        c=dict(density_kg_m3=RHO,cp_j_kg_k=CP,design_secondary_flow_m3_s=68.37/3600,
            design_secondary_dp_pa=371810.,design_speed=.9,quadratic_shutoff_factor=1.25,
            hx_ua_w_k=ua,series_resistance_fraction=.5,rack_ids=['rack'+str(i) for i in range(6)],
            secondary_supply_volume_m3=.1,secondary_return_volume_m3=.15,rack_fluid_volume_each_m3=.15,
            initial_supply_k=317.15,initial_return_k=328.676,primary_inlet_k=314.15,
            primary_flow_m3_s=110/3600,liquid_fraction=.95)
        super().__init__(c)
        self.graph,self.curve=secondary_graph(factors)
        self.drive=drive(.65)
        self.temperatures=[317.15,*([317.15]*6),*([328.676]*6),328.676]
        self.volumes=[.1,*([.025]*6),*([.15]*6),.15]
        self.capacities=[CV*v for v in self.volumes]
        self.initial_energy=self.energy();self.max_local_energy_residual_j=0.
        self.max_hydraulic_residual_pa=0.;self.max_mass_residual_kg_s=0.;self.step_count=0

    def snapshot(self,now,speed,state_id):
        h=solve(self.graph,self.curve,speed,RHO)
        self.latest_hydraulic=h
        return PhysicalSnapshot(now,max(self.temperatures[1:7]),self.temperatures[-1],
            tuple(self.temperatures[7:13]),h.total_flow_m3_s,h.branch_flows_m3_s,h.pump_head_pa,
            speed,state_id,'hydraulic:'+str(now),h.max_mass_residual_kg_s,h.pump_curve_residual_pa)

    def advance_project(self,start_ns,end_ns,speed,primary_inlet_k,primary_flow_m3_s):
        dt=(end_ns-start_ns)/1e9;old=list(self.temperatures)
        h=solve(self.graph,self.curve,speed,RHO)
        q=h.total_flow_m3_s;flows=h.branch_flows_m3_s
        hx=evaluate(self.hx,q*RHO,primary_flow_m3_s*RHO,old[-1],primary_inlet_k)
        pump=pump_energy(self.drive,h.pump_head_pa,q,dt)
        ds={d.receiver_id:0. for d in h.dissipations}
        for d in h.dissipations:ds[d.receiver_id]+=d.liquid_w
        rates=[CV*q*(old[-1]-old[0])-hx.secondary_out_w+ds['supply']]
        rates += [CV*f*(old[0]-t)+ds['inlet'+str(i)] for i,(f,t) in enumerate(zip(flows,old[1:7]))]
        rates += [CV*f*(tin-t)+155000*.95+ds['rack'+str(i)] for i,(f,tin,t) in enumerate(zip(flows,old[1:7],old[7:13]))]
        rates += [fsum(CV*f*(t-old[-1]) for f,t in zip(flows,old[7:13]))+pump.loss_to_liquid_w+ds['return']]
        adv=[q,*flows,*flows,q]
        check(max(dt*CV*f/cap for f,cap in zip(adv,self.capacities))<=.25,'CFL_REDUCE_DT')
        self.temperatures=[t+dt*r/cap for t,r,cap in zip(old,rates,self.capacities)]
        check(all(isfinite(t) and 273.15<=t<=373.15 for t in self.temperatures),'MODEL_TEMPERATURE_RANGE_STOP')
        local=[(b-a)*cap-dt*r for a,b,cap,r in zip(old,self.temperatures,self.capacities,rates)]
        for e,a,b,cap,r in zip(local,old,self.temperatures,self.capacities,rates):
            check(abs(e)<=rounding_bound(a*cap,b*cap,dt*r),'LOCAL_UNIT_ENERGY')
        self.max_local_energy_residual_j=max(self.max_local_energy_residual_j,*map(abs,local))
        self.step_count+=1
        self.max_mass_residual_kg_s=max(self.max_mass_residual_kg_s,h.max_mass_residual_kg_s)
        self.max_hydraulic_residual_pa=max(self.max_hydraulic_residual_pa,h.max_pressure_residual_pa)
        hydraulic=fsum(d.liquid_w for d in h.dissipations)
        liquid_pump=pump.loss_to_liquid_w+hydraulic
        check(abs(liquid_pump-pump.electrical_w)<=rounding_bound(liquid_pump,pump.electrical_w),'PUMP_HEAT_OWNERSHIP')
        residual=self.energy()-fsum(t*c for t,c in zip(old,self.capacities))-dt*(883500+liquid_pump-hx.secondary_out_w)
        self.max_step_residual_j=max(self.max_step_residual_j,abs(residual))
        for key,value in dict(it_j=930000,liquid_load_j=883500,air_load_j=46500,
            pump_electrical_j=pump.electrical_w,pump_liquid_j=liquid_pump,pump_ambient_j=0.,hx_to_primary_j=hx.secondary_out_w).items():
            self.totals[key]+=dt*value
        return dict(start_ns=start_ns,end_ns=end_ns,old_k=old,new_k=list(self.temperatures),
            primary_inlet_k=primary_inlet_k,primary_flow_m3_s=primary_flow_m3_s,
            branch_flow_m3_s=list(flows),flow_m3_s=q,dp_pa=h.pump_head_pa,
            edge_drops_pa=dict(h.edge_drops_pa),node_pressures_relative_pa=dict(h.pressures_pa),
            rack_it_w=[155000]*6,rack_liquid_w=[147250]*6,pump_electrical_w=pump.electrical_w,
            pump_to_liquid_w=liquid_pump,hx_w=hx.secondary_out_w,primary_outlet_k=hx.primary_outlet_k,
            local_rates_w=rates,max_local_residual_j=max(map(abs,local)),energy_residual_j=residual)
