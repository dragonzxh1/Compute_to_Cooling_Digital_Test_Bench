"""Explicit hypothetical added plant. No claim these circuits exist in00/01.

Private W2/W3 preconditioning uses its own90m3/h pump,20kPa circuit;
mode C uses a separately specified thermal sink, not free cooling.
RC is an additional isolated1MW HX/cooling service, NEVER online W2 twice.
"""
from math import fsum,exp
from dataclasses import asdict,replace
from .legacy_sources import SourcePlant as LegacyPlant,tower_capacity,tower_ratings,recharge_requested_speed
from .hydraulics import source_graph,primary_load_graph
from .tank import TransportPipe
from .common import CV,RHO,check,rounding_bound,p
from .coordination import ClosureObservation
from v0_2.hydraulics.solver import solve
from v0_2.hydraulics.pump import pump_energy

class ClosurePlant(LegacyPlant):
    def __init__(self,spec):
        super().__init__(spec);self.last_request={};self.pre_q={};self.pre_history=[];self.ready_at={};self.additional_pump_w=0.;self.failed_pumps=0;self.module_count=5
        self.source_stuck=False;self.feedback_lie=False;self.pre_failed=False;self.common_load_failed=False;self.deadleg_opened=False
        if spec.get('third_source'):
            self.pipes['W3']=TransportPipe(volume=spec.get('header_volume_m3',2.75));self.available['W3']=True
        if spec.get('independent_recharge'):
            self.pipes['RC']=TransportPipe(volume=spec.get('header_volume_m3',2.75));self.available['RC']=True
        if spec.get('deadleg_m3'):
            self.pipes['DEADLEG']=TransportPipe(volume=spec['deadleg_m3']);self.available['DEADLEG']=False
        for name,t in self.tanks.items():
            fraction=spec.get('cold_fraction_'+name,spec.get('cold_fraction',.85))
            if not(name=='B' and spec.get('backup_initial')=='WARM'):
                t.t=[spec.get('cold_initial_c',40.5)+273.15 if i<round(fraction*t.n) else 321.44 for i in range(t.n)]
            if spec.get('initial_profile')=='SMEARED':
                for _ in range(10):
                    old=list(t.t);rates=[0.]*t.n
                    for i in range(t.n-1):delta=.25*(old[i+1]-old[i]);rates[i]+=delta;rates[i+1]-=delta
                    t.t=[a+b for a,b in zip(old,rates)]
        self._precondition_prelude();self.initial_energy=self.energy()
    def _loop(self,path,dt,now_s):
        if path not in self.pipes or self.spec.get('preconditioning_mode','NONE')=='NONE':self.pre_q[path]=0.;return 0.,0.,0.
        if path==self.source_path and self.last_source_q>1e-9:self.pre_q[path]=self.last_source_q;return 0.,0.,0.
        if self.pre_failed:self.pre_q[path]=0.;return 0.,0.,0.
        # Independent quadratic Q-H intersection:25kPa H0,5kPa curve drop
        # at Qd,20kPa system at Qd. Flow is NOT a controller-assigned330.
        qd=self.spec.get('precool_flow_m3_h',90.)/3600
        q=(25000/(20000/qd**2+5000/qd**2))**.5;pump=q*20000/.65
        pipe=self.pipes[path];hot=pipe.t[-1]+pump/(CV*q);floor=self.spec.get('precool_floor_c',40.5)+273.15
        power=self.spec.get('precool_capacity_kW',100.)*1000
        if self.spec.get('preconditioning_mode')=='A' and path!='RC':
            power=min(power,tower_capacity('W2',q,hot-273.15,db=self.spec.get('dry_bulb_c',46),wb=self.spec.get('wet_bulb_c',30))) if self.available.get(path,False) else 0.
        reject=min(power,CV*q*max(0,hot-floor));pipe.advance(dt,q,hot-reject/(CV*q));self.pre_q[path]=q
        return pump,reject,0.
    def pipe_heat_gain(self,path,dt):
        # Stopping the preconditioning pump does NOT remove ambient heat gain.
        # Registered UA applies to the proposed W2/W3/RC preconditioned paths.
        pipe=self.pipes[path];gain=self.spec.get('pipe_ambient_UA_W_K',500.)*(319.15-fsum(pipe.t)/pipe.n)
        pipe.t=[x+gain*dt/(pipe.cap*pipe.n) for x in pipe.t]
        return gain
    def _precondition_prelude(self):
        paths=[x for x in ('W2','W3','RC') if x in self.pipes]
        before=self.energy();pump=reject=gain=0.;initial_temperatures={k:[x-273.15 for x in self.pipes[k].t] for k in paths}
        # Standby-only component prelude; online IT circuit remains outside
        # this independent component ledger, not silently assigned zero IT.
        for tick in range(round(self.spec.get('prelude_s',0))):
            for name in paths:
                a,b,c=self._loop(name,1.,tick+1);pump+=a;reject+=b;gain+=c+self.pipe_heat_gain(name,1.)
                if max(self.pipes[name].t)<=314.3948:self.ready_at.setdefault(name,tick+1)
            if tick%10==9:self.pre_history.append(dict(time_s=tick+1,temperatures_C={k:[x-273.15 for x in self.pipes[k].t] for k in paths},pump_W=sum(self.pre_q.get(k,0)*20000/.65 for k in paths)))
        residual=self.energy()-before-pump+reject-gain
        check(abs(residual)<=rounding_bound(before,self.energy(),pump,reject,gain,operations=8192*max(1,self.spec.get('prelude_s',0))),'PRELUDE_ENERGY')
        self.prelude=dict(initial_J=before,final_J=self.energy(),pump_J=pump,rejected_J=reject,ambient_J=gain,residual_J=residual,ready_times_s=dict(self.ready_at),duration_s=self.spec.get('prelude_s',0),component_scope='STANDBY_PIPES_ONLY_NOT_WHOLE_SITE_ZERO_LOAD',paths=paths,initial_temperatures_C=initial_temperatures,final_temperatures_C={k:[x-273.15 for x in self.pipes[k].t] for k in paths})
    def inject(self,seconds):
        super().inject(seconds)
        if self.spec.get('fault')=='A_LOAD_RESTRICTION' and seconds>=self.spec.get('fault_at_s',30):self.leak_A=True
        self.failed_pumps=int(seconds>=self.spec.get('pump_loss_at_s',float('inf')))
        self.module_count=4 if self.spec.get('module_loss') and self.source_path=='W1' and seconds>=self.spec.get('fault_at_s',30) else 5
        self.source_stuck=bool(self.spec.get('source_valve_stuck') and self.source_path in ('W2','W3'))
        self.feedback_lie=bool(self.spec.get('valve_feedback_lie') and self.source_path=='W2')
        self.pre_failed=seconds>=self.spec.get('preconditioning_loss_at_s',float('inf'))
        self.common_load_failed=seconds>=self.spec.get('common_load_loss_at_s',float('inf'))
        if seconds>=self.spec.get('common_source_loss_at_s',float('inf')):self.available['W1']=self.available['W2']=False;self.header_available=False
        if 'DEADLEG' in self.pipes and seconds>=self.spec.get('deadleg_open_at_s',80):self.deadleg_opened=True
    def actuate(self,dt,command):
        r=command['data']['request'];self.last_request=r
        if (self.source_tank,self.source_path)!=(r['source_tank'],r['source_path']):
            check(self.speed<=1e-9 and max(self.source_supply_valve,self.source_return_valve)<=1e-9,'PHYSICAL_SOURCE_ISOLATION')
            self.source_tank,self.source_path=r['source_tank'],r['source_path']
        target=min(1.,source_graph(self.variant)[2]*(1+r.get('source_speed_margin',0))) if r['source_enable'] else 0.
        self.speed+=max(-.5*dt,min(.5*dt,target-self.speed));travel=self.spec.get('valve_s',5.)
        self.valve+=max(-dt/travel,min(dt/travel,r['source_valve']-self.valve))
        if self.source_stuck or self.feedback_lie:self.valve=0.
        self.source_supply_valve=self.source_return_valve=self.valve
        recharge_target=min(1.,recharge_requested_speed(self.spec.get('recharge_dp_kpa',115.82)*1000)) if r['recharge_enable'] else 0.
        self.recharge_speed+=max(-.5*dt,min(.5*dt,recharge_target-self.recharge_speed));self.fan+=max(-.05*dt,min(.05*dt,r['fan']-self.fan))
        self.load_requested=r['load_tank']
        if self.load_requested!=self.load_tank:self.load_switch_phase='CLOSE'
        if self.load_switch_phase=='CLOSE':
            if not self.spec.get('load_valve_stuck'):self.load_valve=max(0,self.load_valve-dt/travel)
            if self.load_valve<=1e-9:self.load_tank=self.load_requested;self.load_switch_phase='OPEN'
        else:self.load_valve=min(1,self.load_valve+dt/travel)
        if self.common_load_failed:self.load_valve=0.
        self.load_supply_valve=self.load_return_valve=self.load_valve
        return r
    def flows(self,r):
        def scale_graph(g,f):
            def edge(e):return replace(e,coefficient=p(e.edge_id+'.closure',e.coefficient.value*f,'Pa/(m3/s)^2'))
            return replace(g,supply_series=tuple(map(edge,g.supply_series)),branches=tuple(tuple(map(edge,b)) for b in g.branches),return_series=tuple(map(edge,g.return_series)))
        lh=sh=rh=None;load=source=recharge=0.;self.actual_pumps=max(1,r['pumps']-self.failed_pumps)
        self.load_resistance_factor=self.spec.get('A_restriction_factor',4.) if self.leak_A and self.load_tank=='A' else 1.
        if self.load_valve>1e-9:
            g,c=primary_load_graph(self.load_valve);g=scale_graph(g,self.load_resistance_factor);lh=solve(g,c,.9,RHO);load=lh.total_flow_m3_s
        if (self.header_available or self.source_path=='W3') and self.valve>1e-9 and self.speed>1e-9:
            g,c,_=source_graph(self.variant,self.actual_pumps,'WET' if self.source_path.startswith('W') else 'DRY',self.valve)
            if self.source_path.startswith('W') and self.module_count==4:g=replace(g,branches=g.branches[:4])
            c=replace(c,shutoff_head_pa=p('closure.H0',c.shutoff_head_pa.value*self.spec.get('source_head_factor',1.),'Pa'))
            sh=solve(g,c,self.speed,RHO);source=sh.total_flow_m3_s
        if self.recharge_speed>1e-9:
            check(self.spec.get('independent_recharge') and 'RC' in self.pipes,'UNREGISTERED_RC_HARDWARE')
            g,c,_=source_graph('PID',3);g=scale_graph(g,self.spec.get('recharge_dp_kpa',115.82)*1000/96520)
            c=replace(c,shutoff_head_pa=p('closure.RC.H0',c.shutoff_head_pa.value*self.spec.get('recharge_head_factor',1),'Pa'))
            rh=solve(g,c,self.recharge_speed,RHO);recharge=rh.total_flow_m3_s
        return load,source,recharge,lh,sh,rh
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
        rc_hot=self.tanks['B'].t[-1]+(rp/(CV*recharge) if recharge else 0)
        rc_reject=min(self.spec.get('rc_capacity_kW',1000)*1000,CV*recharge*max(0,rc_hot-313.65)) if recharge else 0
        rc_return=self.pipes['RC'].advance(dt,recharge,rc_hot-rc_reject/(CV*recharge)) if recharge else self.tanks['B'].t[0]
        tank_records={};ambient=0
        for name,t in self.tanks.items():
            fl=load if name==self.load_tank else 0;fs=(source if name==self.source_tank else 0)+(recharge if name=='B' else 0)
            tin=((source*returned if name==self.source_tank else 0)+(recharge*rc_return if name=='B' else 0))/fs if fs else t.t[0]
            rec=t.advance(dt,fl,fs,hot,tin,self.spec.get('mixing_m3_s',0),self.spec.get('short_circuit',0))
            gain=self.spec.get('tank_ambient_UA_W_K',0)*(319.15-fsum(t.t)/t.n);t.t=[x+gain*dt/(t.cap*t.n) for x in t.t];ambient+=gain
            rec.update(new_k=list(t.t),environment_heat_w=gain);tank_records[name]=rec
        self.last_source_q=source;self.last_load_q=load;aux_pump=aux_reject=0.;aux_flows={}
        for name in ('W2','W3','RC'):
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
            recharge_actual_speed=self.recharge_speed,recharge_requested_speed_unclipped=recharge_requested_speed(self.spec.get('recharge_dp_kpa',115.82)*1000),
            source_return_k=returned,source_cold_k=cold,source_inlet_k=inlet,source_speed=self.speed,source_valve=self.valve,load_valve=self.load_valve,
            source_tank=self.source_tank,load_tank=self.load_tank,source_path=self.source_path,source_available=dict(self.available),
            source_supply_valve=self.source_supply_valve,source_return_valve=self.source_return_valve,load_supply_valve=self.load_supply_valve,load_return_valve=self.load_return_valve,
            fan_actual=self.fan,source_capacity_w=cap,rejected_w=total_reject,main_rejected_w=reject,aux_rejected_w=aux_reject,rc_rejected_w=rc_reject,
            primary_pump_electrical_w=electric,secondary_pump_electrical_w=secondary,aux_pump_w=aux_pump,ambient_gain_w=ambient,
            actual_primary_return_c=hot-273.15,unit_hx_w=hx,global_residual_j=res,stored_j=after,unit_records=records,tank_records=tank_records,
            tank_A_cold_m3=self.tanks['A'].cold_volume(),tank_B_cold_m3=self.tanks['B'].cold_volume(),actual_source_pumps=self.actual_pumps,
            active_module_count=self.module_count,load_resistance_factor=self.load_resistance_factor,source_header_available=self.header_available,
            preconditioning_flows_m3_h={k:v*3600 for k,v in self.pre_q.items()},aux_actual_flows_m3_h=aux_flows,actual_load_request=self.load_requested)
    def capacity(self,flow,hot_c,now):
        if flow<=0:return 0.
        c=CV*flow;scale=self.spec.get('capacity_scale',1.);db=self.spec.get('dry_bulb_c',46);wb=self.spec.get('wet_bulb_c',30);r=tower_ratings()
        if self.source_path.startswith('D'):return min(3200000*scale,c*(1-exp(-r['dry_ua']*scale/c))*max(0,hot_c-db))
        scale*=self.module_count/5
        if flow<.018333333333333333:return 0.
        return min(3300000*scale,c*max(0,hot_c-(wb+5)),c*(1-exp(-r['wet_ua']*scale/c))*max(0,hot_c-wb))
    def observation(self,now,units):
        base=asdict(super().observation(now,units));bias=self.spec.get('sensor_bias_K',0)
        if self.spec.get('use_fast_sensor_channel') and not self.spec.get('fast_channel_failed'):
            base['release_ns']=now+round(self.spec.get('fast_sensor_delay_s',.1)*1e9);base['record_id']='source-FAST-INDEPENDENT:'+str(now)
        def pair(name):
            if name not in self.pipes:return 99.,99.,0.
            t=self.pipes[name].t
            # Ready is proven by the installed measured preconditioning loop
            # until actual main flow exists, then by measured main flow.
            q=self.last_source_q if name==self.source_path and self.last_source_q>1e-9 else self.pre_q.get(name,0)
            return t[0]-273.15+bias,t[-1]-273.15+bias,q
        near,far,q=pair('W2');a,b,c=pair('W3')
        if self.spec.get('precool_sensor_stuck_low'):near=40.
        if self.feedback_lie:base['source_valve']=1.
        reserve=lambda name:tuple(self.tanks[name].t[round(i*(self.tanks[name].n-1)/16)]+bias for i in range(17))
        return ClosureObservation(**base,standby_near_c=near,standby_far_c=far,standby_flow_m3_s=q,
            ready_sample_ns=now-round(self.spec.get('ready_extra_age_s',0)*1e9),claimed_ready=bool(self.spec.get('false_ready_claim')),
            third_available=self.available.get('W3',False),third_near_c=a,third_far_c=b,third_flow_m3_s=c,
            source_enable_echo=self.last_request.get('source_enable',False),load_selector=self.load_tank,load_valve_feedback=self.load_valve,
            active_pumps=getattr(self,'actual_pumps',3),deadleg_verified='DEADLEG' not in self.pipes,
            reserve_A_k=reserve('A'),reserve_B_k=reserve('B'),source_valve_target_echo=self.last_request.get('source_valve',1.))

def SourcePlant(spec):return ClosurePlant(spec) if spec.get('extensions') else LegacyPlant(spec)
