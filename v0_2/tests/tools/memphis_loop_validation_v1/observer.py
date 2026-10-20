"""Saved physical state, per-tank port ownership and independent FV audit."""
import csv
from math import fsum
from .plant import Plant
from v0_2.tests.tools.memphis_topology_audit_v1.verify import CV,verify_layer_rates,verify_cv
from v0_2.tests.tools.memphis_topology_audit_v1.discharge import full_discharge

class ObservedPlant(Plant):
    def __init__(self,spec,directory):
        self.directory=directory;self.hot_return_peak=48.29;self.pre_second=None;self.maximum_residual=0.;self.steps=0
        self.net={n:dict(load_J=0.,source_J=0.,ambient_J=0.,delta_U_J=0.) for n in ('A','B')}
        self.handle=(directory/'tank_port_ledger.csv').open('x',encoding='utf-8',newline='');self.writer=None
        super().__init__(spec)

    def advance(self,start_ns,end_ns,units,speeds,issued):
        if start_ns==round(self.spec.get('second_fault_at_s',-1)*1e9):
            self.pre_second=full_discharge({n:list(t.t) for n,t in self.tanks.items()},self.spec,self.hot_return_peak,self.directory/'PRE_SECOND_DISCHARGE.csv')
        r=super().advance(start_ns,end_ns,units,speeds,issued);dt=(end_ns-start_ns)/1e9;self.steps+=1
        self.hot_return_peak=max(self.hot_return_peak,r['actual_primary_return_c'])
        for name,t in r['tank_records'].items():
            verify_layer_rates(t,dt,self.tanks[name].volume,self.spec)
            ql=t['load_m3_s'];qs=t['source_m3_s'];old=t['old_k'];new=t['new_k'];cap=self.tanks[name].cap
            load=CV*ql*(t['return_k']-old[0]);source=CV*qs*(t['source_in_k']-old[-1]);env=t['environment_heat_w']
            du=cap*(fsum(new)-fsum(old));res=verify_cv(du,dt*(load+source+env),cap*fsum(old),cap*fsum(new),dt*load,dt*source)
            self.maximum_residual=max(self.maximum_residual,abs(res))
            for k,v in dict(load_J=load*dt,source_J=source*dt,ambient_J=env*dt,delta_U_J=du).items():self.net[name][k]+=v
            row=dict(time_s=end_ns/1e9,tank=name,load_m3_h=ql*3600,source_plus_RC_m3_h=qs*3600,
                main_source_m3_h=r['source_flow_m3_h'] if name==r['source_tank'] else 0.,
                RC_m3_h=r['recharge_flow_m3_h'] if name==r['rc_tank'] else 0.,
                source_tank=r['source_tank'],rc_tank=r['rc_tank'],load_tank=r['load_tank'],
                bottom_C=new[0]-273.15,top_C=new[-1]-273.15,load_W=load,source_W=source,environment_W=env,
                delta_U_J=du,independent_residual_J=res,**{'cumulative_'+k:v for k,v in self.net[name].items()})
            if self.writer is None:self.writer=csv.DictWriter(self.handle,fieldnames=list(row));self.writer.writeheader()
            self.writer.writerow(row)
        return r

    def finish(self):
        self.handle.close()
        return dict(steps=self.steps,tank_energy=self.net,maximum_tank_residual_J=self.maximum_residual,
                    pre_second_challenge=self.pre_second,return_boundary_C=self.hot_return_peak)
