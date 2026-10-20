"""One-six-rack plant adapter; boundaries and all uncalibrated values registered."""
import math
import numpy as np
from .hydraulics import Network


class Plant:
    def __init__(self,graph,registration,case):
        self.g=graph;self.reg=registration;self.a=registration['assumptions'];self.case=case
        self.sec=Network(graph,'PG25_SECONDARY_U1',self.a)
        self.pri=Network(graph,'PG25_PRIMARY',self.a,True)
        self.devices={d['tag']:d for d in graph['components'] if d.get('parent') in ('G01-C01A','G01-C01B')
            or d.get('parent','').startswith('G01-U1-R')}
        self.valves={t:0. for t,d in self.devices.items() if d['kind'] in ('motor_valve','isolation_valve')}
        for t in self.valves:
            if '-P1-' in t:
                self.valves[t]=float('C01A-' in t and not any(s in t for s in ('-CV-B','-F02-')))
            elif '-R0' in t:self.valves[t]=float(t.endswith(('CV-AS','CV-AR')))
            else:self.valves[t]=float('C01A-' in t and '-F02-' not in t)
        self.speeds={t:0. for t,d in self.devices.items() if d['kind']=='pump'}
        self.speeds['G01-C01A-P2-PM1']=.92
        self.targets=dict(self.valves);self.speed_targets=dict(self.speeds)
        self.faults={};self.alarms={'A':False,'B':False};self.master='A';self.guard_refusals=[]
        n=len(self.sec.names);self.T=np.full(n,40.);self.volumes=np.full(n,self.a['generic_node_volume_m3'])
        for side in 'AB':
            tag='G01-C01'+side
            for p,i in self.sec.port_index.items():
                if tag in p and side=='B':self.T[i]=case['initial_spare_C']
            for p in (f'G01-U1-P2-{side}:SUP',f'G01-U1-P2-{side}:RET'):
                self.volumes[self.sec.node(p)]=self.a['header_volume_m3']
            self.volumes[self.sec.node(tag+'-HX:P2-OUT')]=self.a['hx_out_volume_m3']
        for r in range(1,7):
            tag=f'G01-U1-R{r:02d}-LOAD'
            self.volumes[self.sec.node(tag+':IN')]=self.a['rack_inlet_volume_m3']
            self.volumes[self.sec.node(tag+':OUT')]=self.a['rack_outlet_volume_m3']
            self.T[self.sec.node(tag+':OUT')]=52.
        self.cv=self.a['rho_kg_m3']*self.a['cp_J_kgK'];self.capacity=self.cv*self.volumes
        self.energy_reference=float(np.dot(self.capacity,self.T));self.integrated_net_J=0.
        self.last_energy={};self.hx={};self.powers={};self.solve()

    def guard(self,command):
        """Separate actuator admission; not the frozen M1 or a real PLC receipt."""
        vals=dict(self.targets);vals.update(command.get('valves',{}))
        for side in 'AB':
            prefix='G01-C01'+side+'-P1-CV-'
            a=[vals.get(prefix+s,0.)>0 for s in ('AS','AR')]
            b=[vals.get(prefix+s,0.)>0 for s in ('BS','BR')]
            if any(a) and any(b):return 'ILLEGAL_PRIMARY_AB_REQUEST'
            if a[0]!=a[1] or b[0]!=b[1]:return 'UNPAIRED_PRIMARY_REQUEST'
        requested=command.get('master',self.master)
        if requested not in ('A','B',None):return 'PRESSURE_MASTER_CONFLICT'
        if requested=='B' and (self.master=='A' or self.speeds['G01-C01A-P2-PM1']>.001
            or any(self.valves[t]>.001 for t in self.valves if '-R0' in t and t.endswith(('CV-AS','CV-AR')))):
            return 'MASTER_GRANTED_BEFORE_OLD_ZERO_AND_ISOLATION'
        return None

    def issue(self,command,now):
        refusal=self.guard(command)
        if refusal:self.guard_refusals.append(dict(t=now,reason=refusal));return refusal
        self.targets.update(command.get('valves',{}));self.speed_targets.update(command.get('speeds',{}))
        if 'master' in command:self.master=command['master']
        return None

    def apply_fault(self,t):
        if t+1e-9<self.case['fault_s']:return
        self.alarms['A']=True
        kind=self.case['kind']
        self.faults.update(filter_block=kind=='FILTER_BLOCK',low_ua=kind=='LOW_UA')

    def actuate(self,dt,t):
        self.apply_fault(t)
        for tag,target in self.targets.items():
            if self.case['kind']=='RACK_VALVE_STUCK' and t>=self.case['fault_s'] and tag=='G01-U1-R03-CV-BS':target=0.
            delta=dt/self.a['valve_travel_s'];self.valves[tag]+=max(-delta,min(delta,target-self.valves[tag]))
        for tag,target in self.speed_targets.items():
            if t>=self.case['fault_s']:
                if self.case['kind']=='DUTY_PUMP_LOSS' and 'C01A-' in tag:self.speeds[tag]=0.;continue
                if self.case['kind']=='SPARE_NO_FLOW' and 'C01B-' in tag:self.speeds[tag]=0.;continue
                if self.case['kind']=='EARLY_DUTY_EXIT' and 'C01A-' in tag:target=0.
                if self.case['kind']=='OVERLAP_TIMEOUT' and 'C01A-' in tag:target=.92
            delta=dt*self.a['pump_speed_change_per_s'];self.speeds[tag]+=max(-delta,min(delta,target-self.speeds[tag]))

    def solve(self):
        self.sec.solve(self.valves,self.speeds,self.faults)
        self.pri.solve(self.valves,self.speeds,self.faults)
        self.powers={'sec':self.sec.power(self.speeds),'pri':self.pri.power(self.speeds)}

    def hx_exchange(self,tag):
        qs=max(0.,self.sec.hx_flow(tag));qp=max(0.,self.pri.hx_flow(tag));cs=self.cv*qs;cp=self.cv*qp
        total_primary=self.pri.last_flows.get('RESEARCH_BOUNDARY_LP_A',0.)
        pin=self.a['primary_inlet_boundary_C']+(self.powers['pri']['electric_W']/(self.cv*total_primary) if total_primary>1e-10 else 0.)
        tin=float(self.T[self.sec.node(tag+'-HX:P2-IN')]);ua=self.a['UA_clean_W_K']
        if self.faults.get('low_ua') and tag.endswith('B'):ua*=.1
        if min(cs,cp)<1e-9:heat=0.;effectiveness=0.
        else:
            small,big=min(cs,cp),max(cs,cp);ratio=small/big;ntu=ua/small
            if abs(ratio-1)<1e-10:effectiveness=ntu/(1+ntu)
            else:
                ex=math.exp(-ntu*(1-ratio));effectiveness=(1-ex)/(1-ratio*ex)
            heat=effectiveness*small*(tin-pin)
        return dict(primary_flow_m3_h=qp*3600,secondary_flow_m3_h=qs*3600,
            primary_inlet_C=pin,primary_outlet_C=pin+(heat/cp if cp else 0.),
            secondary_hx_inlet_C=tin,secondary_hx_equilibrium_outlet_C=tin-(heat/cs if cs else 0.),
            heat_W=heat,effectiveness=effectiveness,
            primary_dp_kPa=(self.pri.pressure(tag+'-HX:P1-IN')-self.pri.pressure(tag+'-HX:P1-OUT'))/1000,
            secondary_dp_kPa=(self.sec.pressure(tag+'-HX:P2-IN')-self.sec.pressure(tag+'-HX:P2-OUT'))/1000,
            hx_inlet_gauge_difference_kPa=abs(self.pri.pressure(tag+'-HX:P1-IN')-self.sec.pressure(tag+'-HX:P2-IN'))/1000)

    def thermal_step(self,dt):
        rate=self.powers['sec']['node_heat_W'].copy();self.hx={}
        for e in self.sec.last_active:
            q=self.sec.last_flows[e['id']];i,j=e['i'],e['j']
            if q<0:q=-q;i,j=j,i
            energy=self.cv*q*self.T[i];rate[i]-=energy;rate[j]+=energy
        load=0.
        for r in range(1,7):
            tag=f'G01-U1-R{r:02d}-LOAD';w=147250.;rate[self.sec.node(tag+':OUT')]+=w;load+=w
        cooling=0.
        for side in 'AB':
            tag='G01-C01'+side;hx=self.hx_exchange(tag);self.hx[side]=hx
            rate[self.sec.node(tag+'-HX:P2-OUT')]-=hx['heat_W'];cooling+=hx['heat_W']
        before=float(np.dot(self.capacity,self.T));self.T+=dt*rate/self.capacity
        after=float(np.dot(self.capacity,self.T));net=load+self.powers['sec']['electric_W']-cooling
        error=(after-before)-net*dt;self.integrated_net_J+=net*dt
        cumulative_error=(after-self.energy_reference)-self.integrated_net_J
        # Energy leaving primary return to constant-temperature reservoir is explicit.
        primary_boundary_rejection=cooling+self.powers['pri']['electric_W']
        self.last_energy=dict(stored_before_J=before,stored_after_J=after,load_W=load,
            secondary_pump_electric_W=self.powers['sec']['electric_W'],hx_secondary_to_primary_W=cooling,
            primary_pump_electric_W=self.powers['pri']['electric_W'],primary_boundary_rejection_W=primary_boundary_rejection,
            energy_step_error_J=error,energy_cumulative_error_J=cumulative_error,
            hydraulic_power_balance_error_W=self.powers['sec']['power_balance_error_W'])
        if abs(error)>self.a['energy_step_tolerance_J']:raise RuntimeError('SECONDARY_ENERGY_LEDGER_FAILURE '+str(error))
        if not np.all(np.isfinite(self.T)) or np.max(np.abs(self.T))>200:raise RuntimeError('THERMAL_MODEL_OUT_OF_RANGE')

    def physical(self,t):
        result={'t':t,'master':self.master,'alarm_A':self.alarms['A'],'alarm_B':self.alarms['B'],
            'valves':dict(self.valves),'speeds':dict(self.speeds),'cdus':{},'racks':{},
            'secondary_mass_residual':self.sec.last_stats['relative_mass_residual'],
            'primary_mass_residual':self.pri.last_stats['relative_mass_residual'],'energy':dict(self.last_energy)}
        for side in 'AB':
            tag='G01-C01'+side;hx=self.hx.get(side) or self.hx_exchange(tag)
            result['cdus'][side]=dict(hx,supply_C=float(self.T[self.sec.node(tag+'-HX:P2-OUT')]),
                suction_kPa_g=self.sec.pressure(tag+'-P2-XV-RET:OUT')/1000,
                outlet_kPa_g=self.sec.pressure(tag+'-HX:P2-OUT')/1000,
                header_dp_kPa=(self.sec.pressure(tag+'-HX:P2-OUT')-self.sec.pressure(tag+'-P2-XV-RET:OUT'))/1000,
                speed=self.speeds[tag+'-P2-PM1'])
        for r in range(1,7):
            tag=f'G01-U1-R{r:02d}';q=self.sec.flow(tag+'-LOAD')
            result['racks'][str(r)]=dict(flow_m3_h=q*3600,
                supply_C=float(self.T[self.sec.node(tag+'-LOAD:IN')]),return_C=float(self.T[self.sec.node(tag+'-LOAD:OUT')]),
                dp_kPa=(self.sec.pressure(tag+'-LOAD:IN')-self.sec.pressure(tag+'-LOAD:OUT'))/1000,
                A_supply_m3_h=self.sec.flow(tag+'-CV-AS')*3600,B_supply_m3_h=self.sec.flow(tag+'-CV-BS')*3600,
                A_return_m3_h=self.sec.flow(tag+'-CV-AR')*3600,B_return_m3_h=self.sec.flow(tag+'-CV-BR')*3600)
        result['unit_flow_m3_h']=sum(r['flow_m3_h'] for r in result['racks'].values())
        return result
