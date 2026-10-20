"""Versioned direct-CDU derivative: no neutral loop, no original file changes."""
from math import fsum
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import CV,check,rounding_bound
from v0_2.hydraulics.pump import pump_energy
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.legacy_sources import recharge_requested_speed

def advance(self,start_ns,end_ns,units,speeds,issued):
    dt=(end_ns-start_ns)/1e9;before=self.energy()+fsum(u.energy() for u in units);command=self.actuate(dt,issued)
    load,source,recharge,lh,sh,rh=self.flows(command);tank=self.tanks[self.load_tank]
    lp=0 if lh is None else pump_energy(self.primary_drive,lh.pump_head_pa,load,dt).electrical_w
    primary=tank.t[0]+(lp/(CV*load) if load else 0);self.last_primary_inlet=primary
    records=[u.advance_project(start_ns,end_ns,s,primary,load/3) for u,s in zip(units,speeds)];hx=fsum(u['hx_w'] for u in records)
    hot=primary+(hx/(CV*load) if load else 0)
    sp=0 if sh is None else pump_energy(self.primary_drive,sh.pump_head_pa,source,dt).electrical_w
    rp=0 if rh is None else pump_energy(self.primary_drive,rh.pump_head_pa,recharge,dt).electrical_w
    inlet=self.tanks[self.source_tank].t[-1]+(sp/(CV*source) if source else 0)
    cap=self.capacity(source,inlet-273.15,start_ns);reject=cap*self.fan if self.available.get(self.source_path,False) else 0
    cold=inlet-reject/(CV*source) if source else inlet;returned=self.pipes[self.source_path].advance(dt,source,cold)
    rc_hot=self.tanks[self.rc_tank].t[-1]+(rp/(CV*recharge) if recharge else 0)
    rc_reject=min(self.rc_capacity(start_ns)*1000,CV*recharge*max(0,rc_hot-313.65)) if recharge else 0
    rc_return=self.pipes['RC'].advance(dt,recharge,rc_hot-rc_reject/(CV*recharge)) if recharge else self.tanks[self.rc_tank].t[0]
    tank_records={};ambient=0
    for name,t in self.tanks.items():
        fl=load if name==self.load_tank else 0;fs=(source if name==self.source_tank else 0)+(recharge if name==self.rc_tank else 0)
        tin=((source*returned if name==self.source_tank else 0)+(recharge*rc_return if name==self.rc_tank else 0))/fs if fs else t.t[0]
        rec=t.advance(dt,fl,fs,hot,tin,self.spec.get('mixing_m3_s',0),self.spec.get('short_circuit',0))
        gain=self.spec.get('tank_ambient_UA_W_K',0)*(319.15-fsum(t.t)/t.n);t.t=[x+gain*dt/(t.cap*t.n) for x in t.t];ambient+=gain
        rec.update(new_k=list(t.t),environment_heat_w=gain);tank_records[name]=rec
    self.last_source_q=source;self.last_load_q=load;aux_pump=aux_reject=0.;aux_flows={}
    for name in ('W1','W2','RC'):
        if name not in self.pipes:continue
        ambient+=self.pipe_heat_gain(name,dt)
        if name=='RC' and recharge>0:continue
        a,b,c=self._loop(name,dt,end_ns/1e9);aux_pump+=a;aux_reject+=b;ambient+=c
        if a:aux_flows[name]=self.pre_q[name]*3600
    if self.deadleg_opened:
        dead=self.pipes['DEADLEG'];pipe=self.pipes['W2'];transfer=CV*.005*(fsum(dead.t)/dead.n-pipe.t[0])*dt
        pipe.t[0]+=transfer/pipe.cap;dead.t=[x-transfer/(dead.cap*dead.n) for x in dead.t]
    electric=lp+sp+rp+aux_pump;secondary=fsum(r['pump_electrical_w'] for r in records);total_reject=reject+rc_reject+aux_reject
    after=self.energy()+fsum(u.energy() for u in units);res=after-before-dt*(2650500+electric+secondary+ambient-total_reject)
    check(abs(res)<=rounding_bound(before,after,dt*2650500,operations=4096),'CLOSURE_WHOLE_ENERGY')
    self.input_electrical_j+=electric*dt;self.rejected_j+=total_reject*dt;self.max_residual_j=max(self.max_residual_j,abs(res));self.unit_hx_j+=hx*dt
    self.wet_inlet_pressure=None if self.variant=='V9' else 335890+(dict(sh.pressures_pa)['sm'] if sh else 0)
    return dict(start_ns=start_ns,end_ns=end_ns,primary_inlet_c=primary-273.15,load_flow_m3_h=load*3600,source_flow_m3_h=source*3600,recharge_flow_m3_h=recharge*3600,
        recharge_actual_speed=self.recharge_speed,rc_tank=self.rc_tank,rc_valve=self.rc_valve,rc_target=self.rc_tank,source_startup_elapsed_s=self.startup_elapsed(start_ns),recharge_requested_speed_unclipped=recharge_requested_speed(self.spec.get('recharge_dp_kpa',115.82)*1000),
        source_return_k=returned,source_cold_k=cold,source_inlet_k=inlet,source_speed=self.speed,source_valve=self.valve,load_valve=self.load_valve,
        source_tank=self.source_tank,load_tank=self.load_tank,source_path=self.source_path,source_available=dict(self.available),
        source_supply_valve=self.source_supply_valve,source_return_valve=self.source_return_valve,load_supply_valve=self.load_supply_valve,load_return_valve=self.load_return_valve,
        fan_actual=self.fan,source_capacity_w=cap,rejected_w=total_reject,main_rejected_w=reject,aux_rejected_w=aux_reject,rc_rejected_w=rc_reject,
        primary_pump_electrical_w=electric,secondary_pump_electrical_w=secondary,aux_pump_w=aux_pump,ambient_gain_w=ambient,
        actual_primary_return_c=hot-273.15,unit_hx_w=hx,global_residual_j=res,stored_j=after,unit_records=records,tank_records=tank_records,
        tank_A_cold_m3=self.tanks['A'].cold_volume(),tank_B_cold_m3=self.tanks['B'].cold_volume(),actual_source_pumps=self.actual_pumps,
        active_module_count=self.module_count,load_resistance_factor=self.load_resistance_factor,source_header_available=self.header_available,
        preconditioning_flows_m3_h={k:v*3600 for k,v in self.pre_q.items()},aux_actual_flows_m3_h=aux_flows,actual_load_request=self.load_requested,
        source_pipe_after_k=list(self.pipes[self.source_path].t),rc_pipe_after_k=list(self.pipes['RC'].t) if 'RC' in self.pipes else None)
