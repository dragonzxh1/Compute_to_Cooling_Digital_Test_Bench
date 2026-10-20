"""Two physical CDU branches serving ONE six-rack heat load, never two loads.

Secondary circuits share only the documented rack interface. Primary A and B
remain separate heat-exchanger fluids. All dimensions/curves are assumptions.
"""
from math import sqrt,fsum,isfinite
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.plant import ProjectUnit
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import CV,RHO,rounding_bound,check
from v0_2.cdu.heat_exchanger import evaluate

QD=68.37/3600

def coupled_secondary(speeds,valves):
    """Positive quadratic parallel-pump solution with shared load resistance.
    Pump curve and total single-running resistance equal prior design point.
    Non-return behavior is explicit; zero flow is never replaced by demand.
    """
    h0=371810*1.25/.9**2;kp=371810/QD**2*.25
    kc=171630/QD**2
    ks=[200180/QD**2/max(v,.001)**2 for v in valves]
    heads=[h0*s*s if v>1e-9 else 0. for s,v in zip(speeds,valves)]
    lo=0.;hi=max(heads)
    for _ in range(56):
        dp=(lo+hi)/2;qs=[sqrt(max(0.,h-dp)/(kp+k)) for h,k in zip(heads,ks)]
        if fsum(qs)>sqrt(dp/kc):lo=dp
        else:hi=dp
    dp=(lo+hi)/2;qs=[sqrt(max(0.,h-dp)/(kp+k)) for h,k in zip(heads,ks)]
    return qs,dp,[h0*s*s-kp*q*q for s,q in zip(speeds,qs)],ks

class DualUnit:
    def __init__(self,spec,index):
        base=ProjectUnit(spec['ua_w_k']*spec.get('cdu_ua_factor',1),[1.]*6,spec)
        self.hx=base.hx;self.temperatures=list(base.temperatures)
        self.capacities=list(base.capacities);self.index=index;self.spec=spec
        self.hot=[self.temperatures[-1]]*2;self.cold=[self.temperatures[0]]*2
        self.branch_cap=CV*.05
        self.speed=[.9,0.];self.primary_valve=[1.,0.];self.secondary_valve=[1.,0.]
        self.primary_target=[1.,0.];self.secondary_target=[1.,0.]
        self.primary_block=[False,False];self.secondary_failed=[False,False]
        self.ready=[True,True];self.latest={};self.max_local=0.
    def energy(self):return fsum(t*c for t,c in zip(self.temperatures,self.capacities))+self.branch_cap*fsum(self.hot+self.cold)
    def actuate(self,dt,pump_commands,valve_commands):
        self.primary_target,self.secondary_target=map(list,valve_commands)
        for i in range(2):
            target=0. if self.secondary_failed[i] else pump_commands[i]
            self.speed[i]+=max(-.5*dt,min(.5*dt,target-self.speed[i]))
            for actual,request in ((self.primary_valve,self.primary_target),(self.secondary_valve,self.secondary_target)):
                if self.spec.get('standby_valve_stuck') and i==1:continue
                actual[i]+=max(-dt/self.spec['valve_s'],min(dt/self.spec['valve_s'],request[i]-actual[i]))
    def advance(self,start,end,primary_t,primary_q,primary_dp):
        dt=(end-start)/1e9;old=list(self.temperatures);before=self.energy()
        qs,dp,heads,ks=coupled_secondary(self.speed,self.secondary_valve);q=fsum(qs);flows=[q/6]*6
        power=[h*f/.65 for h,f in zip(heads,qs)]
        hx=[evaluate(self.hx,qq*RHO,pp*RHO,th,tp) for qq,pp,th,tp in zip(qs,primary_q,self.hot,primary_t)]
        # Rack/common passive dissipation and each branch's hydraulic/motor
        # loss add to exactly the total pump electrical power, once.
        common=dp*q;branch_heat=[k*f**3+(p-h*f) for k,f,p,h in zip(ks,qs,power,heads)]
        rates=[fsum(CV*f*(t-old[0]) for f,t in zip(qs,self.cold))]
        rates += [CV*f*(old[0]-t)+common*.1/6 for f,t in zip(flows,old[1:7])]
        rates += [CV*f*(tin-t)+147250+common*.9/6 for f,tin,t in zip(flows,old[1:7],old[7:13])]
        rates += [fsum(CV*f*(t-old[-1]) for f,t in zip(flows,old[7:13]))]
        hot_rates=[CV*f*(old[-1]-t)+p for f,t,p in zip(qs,self.hot,branch_heat)]
        cold_rates=[CV*f*(h-c)-x.secondary_out_w for f,h,c,x in zip(qs,self.hot,self.cold,hx)]
        check(dt*CV*max(q,1e-30)/min(self.capacities[0],self.capacities[-1])<=.5,'UNIT_HEADER_CFL')
        check(dt*CV*max(qs)/self.branch_cap<=.5,'CDU_BRANCH_CFL')
        self.temperatures=[t+dt*r/c for t,r,c in zip(old,rates,self.capacities)]
        oldhot=list(self.hot);oldcold=list(self.cold)
        self.hot=[t+dt*r/self.branch_cap for t,r in zip(self.hot,hot_rates)]
        self.cold=[t+dt*r/self.branch_cap for t,r in zip(self.cold,cold_rates)]
        # First-order face values are old states; HX duty belongs only to the
        # downstream cold control volume and its opposite primary heat receipt.
        check(all(isfinite(x) and 273.15<=x<=373.15 for x in self.temperatures+self.hot+self.cold),'DUAL_UNIT_MODEL_RANGE_STOP')
        local=[(b-a)*c-dt*r for a,b,c,r in zip(old,self.temperatures,self.capacities,rates)]
        local += [(b-a)*self.branch_cap-dt*r for aa,bb,rr in ((oldhot,self.hot,hot_rates),(oldcold,self.cold,cold_rates)) for a,b,r in zip(aa,bb,rr)]
        self.max_local=max(self.max_local,*map(abs,local))
        total_hx=fsum(x.secondary_out_w for x in hx)
        residual=self.energy()-before-dt*(883500+fsum(power)-total_hx)
        check(abs(residual)<=rounding_bound(before,self.energy(),dt*883500,operations=8192),'DUAL_UNIT_ENERGY')
        check(abs(common+fsum(branch_heat)-fsum(power))<1e-7,'SECONDARY_PUMP_HEAT_ONCE')
        self.latest=dict(unit=self.index,start_ns=start,end_ns=end,rack_inlet_C=[x-273.15 for x in self.temperatures[1:7]],
            rack_return_C=[x-273.15 for x in self.temperatures[7:13]],secondary_branch_m3_h=[x*3600 for x in flows],
            secondary_total_m3_h=q*3600,secondary_common_dp_pa=dp,energy_J=self.energy(),energy_residual_J=residual,
            control_volume_audit=dict(old_k=old+oldhot+oldcold,new_k=list(self.temperatures)+self.hot+self.cold,capacities_J_K=self.capacities+[self.branch_cap]*4,branch_resistance=ks),
            cdu=[dict(cdu_id=f'U{self.index}'+('A' if i==0 else 'B'),tank='A' if i==0 else 'B',
                primary_m3_h=primary_q[i]*3600,secondary_m3_h=qs[i]*3600,primary_inlet_C=primary_t[i]-273.15,
                primary_outlet_C=hx[i].primary_outlet_k-273.15,secondary_inlet_C=oldhot[i]-273.15,secondary_outlet_C=oldcold[i]-273.15,
                hx_W=hx[i].secondary_out_w,pump_electrical_W=power[i],secondary_head_pa=heads[i],primary_relative_dp_pa=primary_dp[i],
                speed=self.speed[i],primary_valve=self.primary_valve[i],secondary_valve=self.secondary_valve[i],ready=self.ready[i]) for i in range(2)])
        return self.latest
