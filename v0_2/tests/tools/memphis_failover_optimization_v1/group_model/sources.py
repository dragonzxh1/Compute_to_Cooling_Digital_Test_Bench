"""Two isolated primary tanks, shared source header, four available source paths.

Thermal boundaries evolve from energy balance; 41C is a CONTROL target only.
Dry/wet rating-reduction algebra is ported from existing dynamic_v4, explicitly
uncalibrated. Source changes require observed zero speed/closed valves.
"""
from math import exp,log,fsum
from .common import REG,CV,RHO,check,rounding_bound
from .hydraulics import source_graph,primary_load_graph,drive
from .tank import Tank,TransportPipe
from .coordination import SourceObservation
from v0_2.hydraulics.solver import solve
from v0_2.hydraulics.pump import pump_energy

def tower_ratings():
    c=CV*330/3600
    return dict(dry_ua=c*log(((37+3200000/c)-29)/(37-29))*.9,
        wet_ua=c*log((43.92-30)/(35-30)))

def tower_capacity(path,flow,hot_c,wet_derating=1.,db=46.,wb=30.):
    if flow<=0:return 0.
    ratings=tower_ratings();c=CV*flow
    if path.startswith('D'):return min(3200000.,c*(1-exp(-ratings['dry_ua']/c))*max(0.,hot_c-db))
    if flow+1e-12<.018333333333333333:return 0.
    return min(3300000.*wet_derating,c*max(0.,hot_c-35),c*(1-exp(-ratings['wet_ua']/c))*max(0.,hot_c-wb))

def recharge_requested_speed():
    _,c,_=source_graph('PID',3)
    return ((120000+c.curve_k.value*(330/3600)**2)/c.shutoff_head_pa.value)**.5

class SourcePlant:
    def __init__(self,spec):
        self.spec=spec;self.variant=spec.get('source_variant','PID')
        self.tanks={k:Tank(spec.get('layers',20),spec.get('tank_kind','STRATIFIED'),
            warm=k=='B' and spec.get('backup_initial')=='WARM') for k in ('A','B')}
        initial_path=spec.get('initial_path','W1')
        self.pipes={p:TransportPipe(cold=p==initial_path or (p=='W2' and spec.get('standby_line_precooled',False)),
            volume=spec.get('header_volume_m3',2.75)) for p in ('D1','D2','W1','W2')}
        self.available={p:True for p in self.pipes};self.header_available=True;self.leak_A=False
        self.source_tank='A';self.source_path=initial_path;self.speed=source_graph(self.variant)[2];self.valve=1.
        self.recharge_speed=0.;self.fan=.82308;self.load_tank='A';self.load_valve=1.;self.load_requested='A';self.load_switch_phase='OPEN'
        self.last_source_q=330/3600;self.last_primary_inlet=314.15
        self.last_load_q=330/3600;self.wet_inlet_pressure=None if self.variant=='V9' else 400000.
        self.primary_drive=drive(.7);self.load_graph,self.load_curve=primary_load_graph()
        self.input_electrical_j=0.;self.rejected_j=0.;self.unit_hx_j=0.;self.max_residual_j=0.
        self.initial_energy=self.energy();self.last_flows={'A':(0.,0.),'B':(0.,0.)}
        self.source_started_at=None
        self.source_supply_valve=self.source_return_valve=1.
        self.load_supply_valve=self.load_return_valve=1.

    def energy(self):return fsum([*(t.energy() for t in self.tanks.values()),*(p.energy() for p in self.pipes.values())])

    def inject(self,seconds):
        # Only plant injector sees the fault schedule. Its fields never enter
        # controller/M1 APIs; observations carry only sampled physical state.
        active=seconds>=self.spec.get('fault_at_s',float('inf'))
        if active and self.spec.get('fault')=='W1_LOSS':self.available['W1']=False
        if active and self.spec.get('fault')=='D1_LOSS':self.available['D1']=False
        if active and self.spec.get('fault')=='SHARED_HEADER_LOSS':self.header_available=False
        if active and self.spec.get('fault')=='A_LEAK_SIGNAL':self.leak_A=True
        if seconds>=60 and self.spec.get('second_source_failure'):self.available['W2']=False

    def observation(self,now,units):
        return SourceObservation(now,now+100000000,'source-sample:'+str(now),self.speed,self.valve,
            self.source_tank,self.source_path,self.last_source_q,self.recharge_speed,
            self.available['W1'] and self.header_available,self.available['W2'] and self.header_available,
            self.leak_A,self.last_primary_inlet-273.15,self.tanks['A'].measured_layers(),self.tanks['B'].measured_layers(),
            self.last_load_q,self.wet_inlet_pressure,max(max(u.temperatures[1:7])-273.15 for u in units),
            self.available['D1'] and self.header_available,self.available['D2'] and self.header_available)

    def actuate(self,dt,command):
        r=command['data']['request']
        target=source_graph(self.variant)[2] if r['source_enable'] else 0.
        if (self.source_tank,self.source_path)!=(r['source_tank'],r['source_path']):
            check(self.speed<=1e-9 and max(self.source_supply_valve,self.source_return_valve)<=1e-9,'PHYSICAL_PATH_INTERLOCK')
            self.source_tank,self.source_path=r['source_tank'],r['source_path']
        self.speed+=max(-.5*dt,min(.5*dt,target-self.speed))
        travel=self.spec.get('valve_s',5.)
        self.valve+=max(-dt/travel,min(dt/travel,r['source_valve']-self.valve))
        self.source_supply_valve=self.source_return_valve=self.valve
        # Actual normalized VFD speed saturates at the declared physical1.0.
        # Required speed>1 remains a sizing shortfall, never raises the guard.
        recharge_target=min(1.,recharge_requested_speed()) if r['recharge_enable'] else 0.
        self.recharge_speed+=max(-.5*dt,min(.5*dt,recharge_target-self.recharge_speed))
        self.fan+=max(-.05*dt,min(.05*dt,r['fan']-self.fan))
        self.load_requested=r['load_tank']
        if self.load_requested!=self.load_tank:self.load_switch_phase='CLOSE'
        if self.load_switch_phase=='CLOSE':
            if not self.spec.get('load_valve_stuck'):self.load_valve=max(0.,self.load_valve-dt/travel)
            if self.load_valve<=1e-9:self.load_tank=self.load_requested;self.load_switch_phase='OPEN'
        else:self.load_valve=min(1.,self.load_valve+dt/travel)
        self.load_supply_valve=self.load_return_valve=self.load_valve
        # Paired valves are synchronized by an explicit engineering assumption;
        # a stuck pair never silently changes the actual selector.
        return r

    def flows(self,r):
        load_h=None
        if self.load_valve>1e-9:
            g,c=primary_load_graph(self.load_valve);load_h=solve(g,c,.9,RHO)
            load=load_h.total_flow_m3_s
        else:load=0.
        source=0.;source_h=None
        if self.header_available and self.valve>1e-9 and self.speed>1e-9:
            g,c,_=source_graph(self.variant,r['pumps'],'WET' if self.source_path.startswith('W') else 'DRY',self.valve)
            source_h=solve(g,c,self.speed,RHO);source=source_h.total_flow_m3_s
        recharge=0.;recharge_h=None
        if self.recharge_speed>1e-9:
            # Independent PID proposal:330m3/h@120kPa and max18m synthetic
            # whole-loop curve. It does not borrow the online shared header.
            g,c,_=source_graph('PID',3)
            # Existing solver remains the authority for actual curve/network
            # intersection; explicit resistance scales96520 ->120000.
            from dataclasses import replace
            from .common import p
            def e(x):return replace(x,coefficient=p(x.edge_id+'.recharge',x.coefficient.value*120000/96520,'Pa/(m3/s)^2'))
            g=replace(g,supply_series=tuple(map(e,g.supply_series)),branches=tuple(tuple(map(e,b)) for b in g.branches),return_series=tuple(map(e,g.return_series)))
            # Choose the permitted variable-speed point for the same18m cap,
            # not a fixed imposed flow; pump ramp remains physical.
            recharge_h=solve(g,c,self.recharge_speed,RHO);recharge=recharge_h.total_flow_m3_s
        return load,source,recharge,load_h,source_h,recharge_h

    def advance(self,start_ns,end_ns,units,speeds,issued):
        dt=(end_ns-start_ns)/1e9;before=self.energy()+fsum(u.energy() for u in units)
        command=self.actuate(dt,issued);load,source,recharge,lh,sh,rh=self.flows(command)
        tank=self.tanks[self.load_tank];loadpump=0. if lh is None else pump_energy(self.primary_drive,lh.pump_head_pa,load,dt).electrical_w
        primary=tank.t[0]+(loadpump/(CV*load) if load>0 else 0.)
        self.last_primary_inlet=primary
        unit_records=[u.advance_project(start_ns,end_ns,speed,primary,load/3) for u,speed in zip(units,speeds)]
        hx=fsum(x['hx_w'] for x in unit_records)
        return_hot=primary+(hx/(CV*load) if load>0 else 0.)
        srcpump=0. if sh is None else pump_energy(self.primary_drive,sh.pump_head_pa,source,dt).electrical_w
        rechpump=0. if rh is None else pump_energy(self.primary_drive,rh.pump_head_pa,recharge,dt).electrical_w
        # Source pump work and drive losses enter SOURCE inlet exactly once.
        # Total electrical is used here; passive hydraulic heat is not re-added.
        inlet=self.tanks[self.source_tank].t[-1]+(srcpump/(CV*source) if source>0 else 0.)
        cap=tower_capacity(self.source_path,source,inlet-273.15,self.spec.get('wet_derating',1.),self.spec.get('dry_bulb_c',46.))
        rejected=cap*self.fan if self.available[self.source_path] else 0.
        cooled=inlet-rejected/(CV*source) if source>0 else inlet
        returned=self.pipes[self.source_path].advance(dt,source,cooled)
        b_hot=self.tanks['B'].t[-1]+(rechpump/(CV*recharge) if recharge>0 else 0.)
        b_cap=tower_capacity('W2',recharge,b_hot-273.15,self.spec.get('wet_derating',1.))
        b_rejected=b_cap if self.available['W2'] else 0.
        check(not(recharge>0 and self.source_path=='W2' and source>0),'SHARED_W2_ROLE_CONFLICT')
        # B recharge uses its own source line. When W2 is online, the pipe was
        # already advanced above; never advance one volume twice in an interval.
        b_cold=b_hot-b_rejected/(CV*recharge) if recharge>0 else b_hot
        b_return=self.pipes['W2'].advance(dt,recharge,b_cold) if self.source_path!='W2' else self.pipes['W2'].t[-1]
        tank_records={}
        for name,t in self.tanks.items():
            fl=load if name==self.load_tank else 0.
            fs=(source if name==self.source_tank else 0.)+(recharge if name=='B' else 0.)
            cold=fsum([source*returned if name==self.source_tank else 0.,recharge*b_return if name=='B' else 0.])/fs if fs else t.t[0]
            tank_records[name]=t.advance(dt,fl,fs,return_hot,cold,
                self.spec.get('mixing_m3_s',0.),self.spec.get('short_circuit',0.))
            self.last_flows[name]=(fl,fs)
        electric=loadpump+srcpump+rechpump
        secondary_pump=fsum(x['pump_electrical_w'] for x in unit_records)
        after=self.energy()+fsum(u.energy() for u in units)
        residual=after-before-dt*(2650500+secondary_pump+electric-rejected-b_rejected)
        check(abs(residual)<=rounding_bound(before,after,dt*2650500,operations=4096),'WHOLE_PRIMARY_SECONDARY_ENERGY')
        self.max_residual_j=max(self.max_residual_j,abs(residual));self.unit_hx_j+=hx*dt
        self.input_electrical_j+=electric*dt;self.rejected_j+=(rejected+b_rejected)*dt
        self.last_source_q=source
        self.last_load_q=load
        self.wet_inlet_pressure=None if self.variant=='V9' or self.source_path.startswith('D') else 335890+(dict(sh.pressures_pa)['sm'] if sh is not None else 0.)
        return dict(start_ns=start_ns,end_ns=end_ns,primary_inlet_c=primary-273.15,
            load_flow_m3_h=load*3600,source_flow_m3_h=source*3600,recharge_flow_m3_h=recharge*3600,
            recharge_actual_speed=self.recharge_speed,recharge_requested_speed_unclipped=recharge_requested_speed(),
            source_return_k=returned,source_cold_k=cooled,source_inlet_k=inlet,
            source_speed=self.speed,source_valve=self.valve,load_valve=self.load_valve,source_tank=self.source_tank,
            load_tank=self.load_tank,source_path=self.source_path,source_available=dict(self.available),
            source_supply_valve=self.source_supply_valve,source_return_valve=self.source_return_valve,
            load_supply_valve=self.load_supply_valve,load_return_valve=self.load_return_valve,
            fan_actual=self.fan,source_capacity_w=cap,rejected_w=rejected+b_rejected,
            primary_pump_electrical_w=electric,secondary_pump_electrical_w=secondary_pump,
            actual_primary_return_c=return_hot-273.15,unit_hx_w=hx,global_residual_j=residual,
            stored_j=after,unit_records=unit_records,tank_records=tank_records,
            tank_A_cold_m3=self.tanks['A'].cold_volume(),tank_B_cold_m3=self.tanks['B'].cold_volume())
