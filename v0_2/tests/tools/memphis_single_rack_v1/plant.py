"""Generic 1/6 rack finite-volume bench; existing physical solvers unchanged."""
from math import fsum,isfinite,sqrt
from v0_2.cdu.heat_exchanger import Arrangement,HeatExchanger,evaluate
from v0_2.fluids.properties import ConstantCpFluid
from v0_2.hydraulics.graph import HydraulicGraph,HydraulicEdge,PressureNode,EdgeKind
from v0_2.hydraulics.pump import PumpCurve,PumpDrive,pump_energy
from v0_2.hydraulics.solver import solve
from v0_2.thermal.provenance import ParameterRecord
from v0_2.tests.tools.gb300_m1_closed_loop_v1.plant import PhysicalSnapshot,check

def p(name,value,unit):
    return ParameterRecord(name,value,unit,'ENGINEERING_ASSUMPTION',
        'memphis_single_rack_v1/registration.json: explicitly uncalibrated bench',
        0.,'2026-10-17',(value,value),'CALIBRATION_REQUIRED')

def bound(*terms,ops=4096):
    u=2**-53;g=ops*u/(1-ops*u)
    return g*max(1.,fsum(abs(v) for v in terms))

class RackLoop:
    def __init__(self,c):
        self.c=c;self.n=c['rack_count'];self.cv=c['density_kg_m3']*c['cp_j_kg_k']
        rho,cp=c['density_kg_m3'],c['cp_j_kg_k']
        def fluid(name):return ConstantCpFluid(name,p(name+'.rho',rho,'kg/m3'),p(name+'.cp',cp,'J/(kg*K)'),p(name+'.Tref',300.,'K'),(273.15,373.15),p(name+'.basis',1.,'count'))
        self.hx=HeatExchanger(p('UA',c['hx_ua_w_k'],'W/K'),Arrangement.COUNTERFLOW,
            fluid('bench.secondary'),fluid('bench.primary'),(0,100),(0,100),None,p('HX',1.,'count'))
        q=c['design_flow_m3_s'];qb=q/self.n;dp=c['design_dp_pa'];b=c['branch_dp_pa']
        def edge(name,a,z,k,receiver):return HydraulicEdge(name,a,z,EdgeKind.GENERIC_RESISTANCE,
            p(name+'.K',k,'Pa/(m3/s)^2'),(0.,1.),receiver,p(name+'.liquid',1.,'fraction'),p(name+'.basis',1.,'count'))
        self.common_k=(dp-b)/q**2
        self.branch_k=[b*f/qb**2 for f in c['branch_factors']]
        self.graph=HydraulicGraph(tuple(PressureNode(x,'SECONDARY') for x in ('r','p','sm','rm')),
            'r','p','sm','rm',(edge('supply','p','sm',self.common_k/2,'supply'),),
            tuple((edge('rack'+str(i),'sm','rm',k,'rack'+str(i)),) for i,k in enumerate(self.branch_k)),
            (edge('return','rm','r',self.common_k/2,'return'),),'pump')
        self.curve=PumpCurve(p('H0',dp*c['quadratic_shutoff_factor']/c['design_speed']**2,'Pa'),
            p('Kcurve',dp*(c['quadratic_shutoff_factor']-1)/q**2,'Pa/(m3/s)^2'),(0.,1.),(0.,1.),p('curve',1.,'count'))
        self.drive=PumpDrive(p('vfd',.95,'fraction'),p('motor',.9,'fraction'),p('pump',c['wire_efficiency']/(.95*.9),'fraction'),
            p('vfd.toLiquid',1.,'fraction'),p('motor.toLiquid',1.,'fraction'),p('pump.toLiquid',1.,'fraction'),'return',p('drive',1.,'count'),p('standby',0.,'W'))
        h=solve(self.graph,self.curve,c['initial_speed'],rho)
        initial=c['load_profile'][0]['rack_it_w']
        ret=[c['initial_supply_k']+w*.95/(self.cv*f) for w,f in zip(initial,h.branch_flows_m3_s)]
        self.t=[c['initial_supply_k'],*ret,fsum(f*t for f,t in zip(h.branch_flows_m3_s,ret))/h.total_flow_m3_s]
        self.cap=[self.cv*v for v in c['volumes_m3']];self.initial=self.energy()
        self.sums={k:0. for k in ('it_j','liquid_j','air_j','pump_j','hx_j')};self.steps=0

    def energy(self):return fsum(t*cap for t,cap in zip(self.t,self.cap))

    def snapshot(self,now,speed,state_id):
        h=solve(self.graph,self.curve,speed,self.c['density_kg_m3'])
        return PhysicalSnapshot(now,self.t[0],self.t[-1],tuple(self.t[1:-1]),h.total_flow_m3_s,
            h.branch_flows_m3_s,h.pump_head_pa,speed,state_id,'hydraulic:'+str(now),h.max_mass_residual_kg_s,h.pump_curve_residual_pa)

    def advance(self,start,end,speed,loads,primary_k):
        dt=(end-start)/1e9;c=self.c;old=list(self.t)
        check(len(loads)==self.n and all(0<=w<=155000 for w in loads),'FULL_DESIGN_LOAD_DOMAIN')
        h=solve(self.graph,self.curve,speed,c['density_kg_m3']);q=h.total_flow_m3_s;flows=h.branch_flows_m3_s
        check(max(dt*f/v for f,v in zip([q,*flows,q],c['volumes_m3']))<=.25,'CFL_STOP')
        hx=evaluate(self.hx,q*c['density_kg_m3'],c['primary_flow_m3_s']*c['density_kg_m3'],old[-1],primary_k)
        power=pump_energy(self.drive,h.pump_head_pa,q,dt)
        diss={d.edge_id:d.liquid_w for d in h.dissipations}
        rates=[self.cv*q*(old[-1]-old[0])-hx.secondary_out_w+diss['supply']]
        rates += [self.cv*f*(old[0]-t)+.95*w+diss['rack'+str(i)] for i,(f,t,w) in enumerate(zip(flows,old[1:-1],loads))]
        rates += [fsum(self.cv*f*(t-old[-1]) for f,t in zip(flows,old[1:-1]))+power.loss_to_liquid_w+diss['return']]
        self.t=[t+dt*r/cap for t,r,cap in zip(old,rates,self.cap)]
        check(all(isfinite(t) and 273.15<=t<=373.15 for t in self.t),'TEMPERATURE_VALIDITY_STOP')
        for a,b,r,cap in zip(old,self.t,rates,self.cap):check(abs((b-a)*cap-dt*r)<=bound(a*cap,b*cap,dt*r),'LOCAL_ENERGY_STOP')
        check(abs(power.electrical_w-power.loss_to_liquid_w-fsum(diss.values()))<=bound(power.electrical_w),'PUMP_HEAT_ONCE')
        for k,v in dict(it_j=fsum(loads),liquid_j=.95*fsum(loads),air_j=.05*fsum(loads),pump_j=power.electrical_w,hx_j=hx.secondary_out_w).items():self.sums[k]+=v*dt
        self.steps+=1
        return dict(start_ns=start,end_ns=end,old_k=old,new_k=list(self.t),rack_it_w=list(loads),
            flow_m3_s=q,branch_flows_m3_s=list(flows),dp_pa=h.pump_head_pa,actual_speed=speed,
            primary_k=primary_k,primary_outlet_k=hx.primary_outlet_k,hx_w=hx.secondary_out_w,
            pump_electrical_w=power.electrical_w,pump_liquid_loss_w=power.loss_to_liquid_w,
            hydraulic_w=fsum(diss.values()),rates_w=rates)

    def ledger(self):
        residual=self.energy()-self.initial-self.sums['liquid_j']-self.sums['pump_j']+self.sums['hx_j']
        tolerance=bound(self.initial,self.energy(),*self.sums.values(),ops=8192*(self.steps+1))
        check(abs(residual)<=tolerance,'GLOBAL_ENERGY_STOP')
        return dict(**self.sums,initial_j=self.initial,final_j=self.energy(),residual_j=residual,bound_j=tolerance)
