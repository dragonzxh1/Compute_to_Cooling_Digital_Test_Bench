"""Per-CDU primary networks and opposite tank heat receipts; no extra RC."""
from math import sqrt,fsum
from dataclasses import dataclass,asdict
from v0_2.tests.tools.memphis_control_path_v1.plant import Plant as PriorPlant,LoopObservation
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.sources import ClosurePlant
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import CV,rounding_bound,check

@dataclass(frozen=True)
class Observation(LoopObservation):
    actual_A_load_m3_s:float
    actual_B_load_m3_s:float

def primary_network(valves,blocked,speed):
    qd=330/3600;qb=110/3600;h0=155920*1.25/.9**2;kp=155920/qd**2*.25
    kcommon=20000/qd**2;ks=[135920/qb**2/max(v,.001)**2 for v in valves]
    coeff=fsum(1/sqrt(k) if v>1e-9 and not b else 0. for k,v,b in zip(ks,valves,blocked))
    if coeff==0 or speed<=1e-9:return [0.]*3,0.,0.
    total=sqrt(h0*speed**2/(kp+kcommon+1/coeff**2));dp=(total/coeff)**2
    flows=[sqrt(dp/k) if v>1e-9 and not b else 0. for k,v,b in zip(ks,valves,blocked)]
    head=h0*speed**2-kp*total**2
    return flows,head,head*total/.7

def primary_target(count):
    if not count:return 0.
    q=count*110/3600;qd=330/3600
    return sqrt((135920+20000*(q/qd)**2+(155920/qd**2*.25)*q*q)/(155920*1.25/.9**2))

class Plant(PriorPlant):
    def __init__(self,spec):
        super().__init__(spec);self.load_speeds=[.9,0.];self.load_targets=[.9,0.];self.actual_loads=[330/3600,0.]
        self.second_applied=False;self.second_failed=None
        if spec.get('warm_B'):self.tanks['B'].t=[321.44]*self.tanks['B'].n
    def inject(self,seconds):
        ClosurePlant.inject(self,seconds)
        if self.spec['fault']=='W1_LOSS' and seconds>=self.spec.get('repair_W1_at_s',float('inf')):
            self.available['W1']=True
            if not self.repair_seen:self.cold_started.pop('W1',None);self.repair_seen=True
        second=self.spec.get('second_fault_at_s')
        if second is not None and seconds>=second and not self.second_applied:
            self.second_failed=self.source_path;self.second_applied=True
        if self.second_failed:self.available[self.second_failed]=False
        if self.spec.get('B_source_valve_stuck') and self.source_tank=='B':self.source_stuck=True
        if self.spec.get('B_source_pump_no_flow'):self.header_available=self.source_tank!='B'
    def observation(self,now,units):
        return Observation(**asdict(super().observation(now,units)),actual_A_load_m3_s=self.actual_loads[0],actual_B_load_m3_s=self.actual_loads[1])
    def advance_dual(self,start,end,units,issued):
        dt=(end-start)/1e9;before=self.energy()+fsum(u.energy() for u in units)
        command=self.actuate(dt,issued);_,source,rc,_,sh,_=self.flows(command);check(rc==0,'NO_RC_HARDWARE')
        flows=[];heads=[];powers=[]
        for j in range(2):
            target=self.load_targets[j]
            self.load_speeds[j]+=max(-.5*dt,min(.5*dt,target-self.load_speeds[j]))
            q,h,p=primary_network([u.primary_valve[j] for u in units],[u.primary_block[j] for u in units],self.load_speeds[j]);flows.append(q);heads.append(h);powers.append(p)
        totals=[fsum(q) for q in flows];self.actual_loads=totals
        primary=[self.tanks[k].t[0]+(p/(CV*q) if q else 0.) for k,p,q in zip(('A','B'),powers,totals)]
        records=[u.advance(start,end,primary,[flows[j][i] for j in range(2)],heads) for i,u in enumerate(units)]
        duties=[fsum(r['cdu'][j]['hx_W'] for r in records) for j in range(2)]
        hot=[t+(h/(CV*q) if q else 0.) for t,h,q in zip(primary,duties,totals)]
        sp=0. if sh is None else sh.pump_head_pa*source/.7
        inlet=self.tanks[self.source_tank].t[-1]+(sp/(CV*source) if source else 0.)
        cap=self.capacity(source,inlet-273.15,start);reject=cap*self.fan if self.available.get(self.source_path,False) else 0.
        cold=inlet-reject/(CV*source) if source else inlet;returned=self.pipes[self.source_path].advance(dt,source,cold)
        tank_records={};ambient=0.
        for j,name in enumerate(('A','B')):
            tank=self.tanks[name];qsource=source if name==self.source_tank else 0.
            rec=tank.advance(dt,totals[j],qsource,hot[j],returned,self.spec.get('mixing_m3_s',0.))
            gain=self.spec['tank_ambient_UA_W_K']*(319.15-fsum(tank.t)/tank.n)
            tank.t=[x+gain*dt/(tank.cap*tank.n) for x in tank.t];ambient+=gain
            rec.update(new_k=list(tank.t),environment_heat_w=gain);tank_records[name]=rec
        for name in ('W1','W2'):ambient+=self.pipe_heat_gain(name,dt)
        secondary=fsum(x['pump_electrical_W'] for r in records for x in r['cdu']);pumps=sp+fsum(powers)+secondary
        after=self.energy()+fsum(u.energy() for u in units);res=after-before-dt*(2650500+pumps+ambient-reject)
        check(abs(res)<=rounding_bound(before,after,dt*2650500,operations=16384),'DUAL_WHOLE_ENERGY')
        self.last_load_q=fsum(totals);self.last_source_q=source;self.last_primary_inlet=primary[0]
        return dict(start_ns=start,end_ns=end,unit_records=records,source_tank=self.source_tank,source_path=self.source_path,
            source_flow_m3_h=source*3600,source_speed=self.speed,source_valve=self.valve,source_supply_valve=self.source_supply_valve,source_return_valve=self.source_return_valve,
            source_head_pa=sh.pump_head_pa if sh else None,source_pumps=self.actual_pumps,source_cold_C=cold-273.15,source_return_C=returned-273.15,
            primary_A_m3_h=totals[0]*3600,primary_B_m3_h=totals[1]*3600,primary_total_m3_h=fsum(totals)*3600,
            primary_load_speeds=list(self.load_speeds),primary_relative_heads_pa=heads,primary_inlet_C=[x-273.15 for x in primary],
            primary_return_C=[x-273.15 for x in hot],tank_records=tank_records,source_W=reject,pump_W=pumps,ambient_W=ambient,stored_J=after,energy_residual_J=res,
            source_startup_elapsed_s=self.startup_elapsed(start),source_available=dict(self.available),tank_A_cold_m3=self.tanks['A'].cold_volume(),tank_B_cold_m3=self.tanks['B'].cold_volume())
