"""Proposed neutral load buffer behind fluid-isolating A/B heat exchangers.

The customer A/B primary liquids NEVER share a simultaneous hydraulic path.
The load/CDU loop is a NEW third fluid domain, with NEW continuous pumps,
buffer and two separately isolated heat exchanger branches. Only the selected
one transfers heat; no double-counted free cooling. This is NOT the00/01 plant.
All Q-H curves, geometry, HX UA and motor dynamics remain engineering assumptions.
"""
from dataclasses import replace
from math import fsum
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.sources import ClosurePlant
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.hydraulics import primary_load_graph
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import CV,RHO,p,check,rounding_bound
from v0_2.hydraulics.solver import solve
from v0_2.hydraulics.pump import pump_energy
from v0_2.cdu.heat_exchanger import evaluate
from v0_2.thermal.provenance import ParameterRecord


class NeutralBufferPlant(ClosurePlant):
    def __init__(self,spec):
        self.neutral_volume=spec['neutral_buffer_m3']
        self.neutral_k=spec.get('neutral_initial_c',40.5)+273.15
        self.neutral_cap=CV*self.neutral_volume
        self.neutral_hx=None
        check(self.neutral_volume>0,'NEUTRAL_BUFFER_POSITIVE_VOLUME')
        super().__init__(spec)

    def energy(self):
        return super().energy()+self.neutral_cap*self.neutral_k

    def advance(self,start_ns,end_ns,units,speeds,issued):
        dt=(end_ns-start_ns)/1e9
        before=self.energy()+fsum(u.energy() for u in units)
        old_buffer=self.neutral_k
        command=self.actuate(dt,issued)
        # The old selected A/B load path is now the proposed HX transfer loop.
        # Its real valves and Q-H solution still determine actual transfer flow.
        transfer,source,recharge,th,sh,rh=self.flows(command)
        if self.common_load_failed:
            main=0.;mh=None
        else:
            g,c=primary_load_graph(1.)
            mh=solve(g,c,.9,RHO);main=mh.total_flow_m3_s
        mp=0. if mh is None else pump_energy(self.primary_drive,mh.pump_head_pa,main,dt).electrical_w
        tp=0. if th is None else pump_energy(self.primary_drive,th.pump_head_pa,transfer,dt).electrical_w
        primary=old_buffer+(mp/(CV*main) if main else 0.)
        self.last_primary_inlet=primary
        records=[u.advance_project(start_ns,end_ns,s,primary,main/3) for u,s in zip(units,speeds)]
        load_heat=fsum(r['hx_w'] for r in records)
        hot=primary+(load_heat/(CV*main) if main else 0.)
        tank=self.tanks[self.load_tank]
        transfer_in=tank.t[0]+(tp/(CV*transfer) if transfer else 0.)
        if self.neutral_hx is None:
            # New component has its own bound/provenance; old HX is untouched.
            ua=self.spec['neutral_hx_ua_w_k']
            provenance=ParameterRecord('NEW_NEUTRAL_HX_UA',ua,'W/K','ENGINEERING_ASSUMPTION',
                'memphis_hydraulic_continuity_v1 registration/scenarios; NEW uncalibrated HX, not existing00/01',
                0.,'2026-10-19',(ua,ua),'CALIBRATION_REQUIRED')
            self.neutral_hx=replace(units[0].hx,ua=provenance,
                secondary_fluid=replace(units[0].hx.secondary_fluid,fluid_id='NEW_NEUTRAL_LOAD_LOOP'),
                primary_fluid=replace(units[0].hx.primary_fluid,fluid_id='SELECTED_ISOLATED_A_OR_B_TRANSFER'),
                valid_secondary_flow=(0.,300.),valid_primary_flow=(0.,300.),rated_capacity_w=None)
        exchange=evaluate(self.neutral_hx,main*RHO,transfer*RHO,hot,transfer_in)
        exchanged=exchange.secondary_out_w
        transfer_return=transfer_in+(exchanged/(CV*transfer) if transfer else 0.)
        buffer_gain=self.spec.get('neutral_buffer_UA_W_K',20.)*(319.15-old_buffer)
        buffer_rate=load_heat+mp-exchanged+buffer_gain
        self.neutral_k=old_buffer+dt*buffer_rate/self.neutral_cap
        check(273.15<=self.neutral_k<=373.15,'NEUTRAL_BUFFER_TEMPERATURE_RANGE')
        buffer_residual=self.neutral_cap*(self.neutral_k-old_buffer)-dt*buffer_rate
        check(abs(buffer_residual)<=rounding_bound(self.neutral_cap*old_buffer,self.neutral_cap*self.neutral_k,dt*buffer_rate),'NEUTRAL_BUFFER_ENERGY')
        sp=0. if sh is None else pump_energy(self.primary_drive,sh.pump_head_pa,source,dt).electrical_w
        rp=0. if rh is None else pump_energy(self.primary_drive,rh.pump_head_pa,recharge,dt).electrical_w
        inlet=self.tanks[self.source_tank].t[-1]+(sp/(CV*source) if source else 0.)
        cap=self.capacity(source,inlet-273.15,start_ns)
        reject=cap*self.fan if self.available.get(self.source_path,False) else 0.
        cold=inlet-reject/(CV*source) if source else inlet
        returned=self.pipes[self.source_path].advance(dt,source,cold)
        rc_hot=self.tanks['B'].t[-1]+(rp/(CV*recharge) if recharge else 0.)
        rc_reject=min(self.spec.get('rc_capacity_kW',1000)*1000,CV*recharge*max(0.,rc_hot-313.65)) if recharge else 0.
        rc_return=self.pipes['RC'].advance(dt,recharge,rc_hot-rc_reject/(CV*recharge)) if recharge else self.tanks['B'].t[0]
        tank_records={};ambient=buffer_gain
        for name,t in self.tanks.items():
            fl=transfer if name==self.load_tank else 0.
            fs=(source if name==self.source_tank else 0.)+(recharge if name=='B' else 0.)
            tin=((source*returned if name==self.source_tank else 0.)+(recharge*rc_return if name=='B' else 0.))/fs if fs else t.t[0]
            rec=t.advance(dt,fl,fs,transfer_return,tin,self.spec.get('mixing_m3_s',0.),self.spec.get('short_circuit',0.))
            gain=self.spec.get('tank_ambient_UA_W_K',0.)*(319.15-fsum(t.t)/t.n)
            t.t=[x+gain*dt/(t.cap*t.n) for x in t.t];ambient+=gain
            rec.update(new_k=list(t.t),environment_heat_w=gain);tank_records[name]=rec
        self.last_source_q=source;self.last_load_q=main
        aux_pump=aux_reject=0.;aux_flows={}
        for name in ('W2','W3','RC'):
            if name not in self.pipes:continue
            ambient+=self.pipe_heat_gain(name,dt)
            if name=='RC' and recharge>0:continue
            a,b,c=self._loop(name,dt,end_ns/1e9);aux_pump+=a;aux_reject+=b;ambient+=c
            if a:aux_flows[name]=self.pre_q[name]*3600
        electric=mp+tp+sp+rp+aux_pump
        secondary=fsum(r['pump_electrical_w'] for r in records)
        total_reject=reject+rc_reject+aux_reject
        after=self.energy()+fsum(u.energy() for u in units)
        residual=after-before-dt*(2650500+electric+secondary+ambient-total_reject)
        check(abs(residual)<=rounding_bound(before,after,dt*2650500,operations=8192),'NEUTRAL_WHOLE_ENERGY')
        self.input_electrical_j+=electric*dt;self.rejected_j+=total_reject*dt
        self.max_residual_j=max(self.max_residual_j,abs(residual));self.unit_hx_j+=load_heat*dt
        self.wet_inlet_pressure=None if self.variant=='V9' else 335890+(dict(sh.pressures_pa)['sm'] if sh else 0.)
        return dict(start_ns=start_ns,end_ns=end_ns,primary_inlet_c=primary-273.15,load_flow_m3_h=main*3600,
            source_flow_m3_h=source*3600,recharge_flow_m3_h=recharge*3600,transfer_flow_m3_h=transfer*3600,
            source_return_k=returned,source_cold_k=cold,source_inlet_k=inlet,source_speed=self.speed,source_valve=self.valve,
            source_tank=self.source_tank,load_tank=self.load_tank,source_path=self.source_path,source_available=dict(self.available),
            load_valve=self.load_valve,source_supply_valve=self.source_supply_valve,source_return_valve=self.source_return_valve,
            load_supply_valve=1. if main else 0.,load_return_valve=1. if main else 0.,
            fan_actual=self.fan,source_capacity_w=cap,rejected_w=total_reject,main_rejected_w=reject,aux_rejected_w=aux_reject,rc_rejected_w=rc_reject,
            primary_pump_electrical_w=electric,secondary_pump_electrical_w=secondary,aux_pump_w=aux_pump,ambient_gain_w=ambient,
            actual_primary_return_c=hot-273.15,unit_hx_w=load_heat,global_residual_j=residual,stored_j=after,unit_records=records,tank_records=tank_records,
            tank_A_cold_m3=self.tanks['A'].cold_volume(),tank_B_cold_m3=self.tanks['B'].cold_volume(),actual_source_pumps=self.actual_pumps,
            active_module_count=self.module_count,load_resistance_factor=self.load_resistance_factor,source_header_available=self.header_available,
            preconditioning_flows_m3_h={k:v*3600 for k,v in self.pre_q.items()},aux_actual_flows_m3_h=aux_flows,
            actual_load_request=self.load_requested,recharge_actual_speed=self.recharge_speed,
            neutral=dict(old_k=old_buffer,new_k=self.neutral_k,capacity_j_k=self.neutral_cap,volume_m3=self.neutral_volume,
                main_pump_w=mp,transfer_pump_w=tp,transfer_heat_w=exchanged,transfer_in_k=transfer_in,transfer_return_k=transfer_return,
                environment_w=buffer_gain,energy_residual_j=buffer_residual,main_dp_pa=0. if mh is None else mh.pump_head_pa,
                transfer_dp_pa=0. if th is None else th.pump_head_pa,AB_direct_mass_connection=False,
                pressure_transient='NOT_VERIFIED_QUASI_STEADY_QH_ONLY',static_pressure='NOT_VERIFIED',NPSH='NOT_VERIFIED'))


def SourcePlant(spec):
    if spec.get('architecture')=='NEUTRAL_BUFFER':return NeutralBufferPlant(spec)
    return ClosurePlant(spec)
