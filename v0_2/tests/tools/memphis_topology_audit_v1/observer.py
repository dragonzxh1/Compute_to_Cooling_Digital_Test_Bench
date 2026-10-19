"""Read-only observer around the exact old forward implementation.

All capture happens after the old functions return; never assign physical state,
controller requests or measurements. Original six forward files must reproduce.
"""
import csv,json
from math import fsum
from pathlib import Path
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.plant import NeutralBufferPlant
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.checks import reserve_challenge
from .verify import CV,verify_layer_rates,verify_cv

class Csv:
    def __init__(self,path):self.f=path.open('x',encoding='utf-8',newline='');self.w=None
    def add(self,row):
        if self.w is None:self.w=csv.DictWriter(self.f,fieldnames=list(row));self.w.writeheader()
        self.w.writerow(row)
    def close(self):self.f.close()

class ObserverPlant(NeutralBufferPlant):
    def __init__(self,spec,directory):
        self.capture=False;self.directory=directory;self.sums={};self.max_residual={};self.keyframes=[];self.steps=0
        self.ports=[];self.curves=[];self.pre_second=None
        self.tank_csv={n:Csv(directory/('05_A_TANK_ENERGY_LEDGER.csv' if n=='A' else '06_B_TANK_ENERGY_LEDGER.csv')) for n in ('A','B')}
        self.cv_csv=Csv(directory/'07_ALL_CONTROL_VOLUME_LEDGER.csv')
        self.profile_file=(directory/'08_TANK_TEMPERATURE_PROFILES.jsonl').open('x',encoding='utf-8')
        super().__init__(spec)
        self.initial={n:list(t.t) for n,t in self.tanks.items()}
        self.capture=True

    def flows(self,command):
        values=super().flows(command);self.audit_flows=values;return values

    def _loop(self,path,dt,now_s):
        result=super()._loop(path,dt,now_s)
        if self.capture:self.loop_events.append((path,*result))
        return result

    def pipe_heat_gain(self,path,dt):
        gain=super().pipe_heat_gain(path,dt)
        if self.capture:self.gains[path]=gain
        return gain

    def cv(self,time,tag,old,new,hin,hout,pump,external,dt,mass_in=0.,mass_out=0.,kind='FINITE_VOLUME'):
        balance=hin-hout+pump+external;du=new-old
        residual=verify_cv(du,balance*dt,old,new,hin*dt,hout*dt,pump*dt,external*dt)
        sums=self.sums.setdefault(tag,dict(enter_J=0.,leave_J=0.,pump_J=0.,external_J=0.,delta_U_J=0.,residual_J=0.))
        for k,v in dict(enter_J=hin*dt,leave_J=hout*dt,pump_J=pump*dt,external_J=external*dt,delta_U_J=du,residual_J=residual).items():sums[k]+=v
        self.max_residual[tag]=max(self.max_residual.get(tag,0.),abs(residual))
        if abs(mass_in-mass_out)>1e-9:raise ValueError('CV_MASS_IMBALANCE:'+tag)
        self.cv_csv.add(dict(time_s=time,cv=tag,kind=kind,mass_in_kg_s=mass_in,mass_out_kg_s=mass_out,
            inlet_enthalpy_W=hin,outlet_enthalpy_W=hout,pump_direct_W=pump,external_W=external,
            U_old_J=old,U_new_J=new,delta_U_J=du,residual_J=residual,**{'cumulative_'+k:v for k,v in sums.items()}))
        return residual

    def advance(self,start_ns,end_ns,units,speeds,issued):
        self.loop_events=[];self.gains={}
        pipes={k:list(p.t) for k,p in self.pipes.items()}
        # Preserve the complete, true pre-second-fault state, before interval1800.
        if start_ns==round(self.spec.get('second_fault_at_s',-1)*1e9):
            row=dict(time_ns=start_ns,**{'tank_'+n+'_k':list(t.t) for n,t in self.tanks.items()})
            self.pre_second=reserve_challenge(row,self.spec,max(48.29,self.hot_return_peak))
        r=super().advance(start_ns,end_ns,units,speeds,issued)
        dt=(end_ns-start_ns)/1e9;time=end_ns/1e9;n=r['neutral'];self.steps+=1
        self.hot_return_peak=max(getattr(self,'hot_return_peak',48.29),r['actual_primary_return_c'])
        transfer,source,recharge,th,sh,rh=self.audit_flows
        sp=0. if sh is None else sh.pump_head_pa*source/.7
        rp=0. if rh is None else rh.pump_head_pa*recharge/.7
        tp=n['transfer_pump_w'];mp=n['main_pump_w']
        for name,t in r['tank_records'].items():
            verify_layer_rates(t,dt,self.tanks[name].volume,self.spec)
            old=t['old_k'];new=t['new_k'];cap=self.tanks[name].cap
            ql=t['load_m3_s'];qs=t['source_m3_s'];hot=t['return_k'];cold=t['source_in_k']
            # h=cp*(T-273.15); reference enthalpy never double-counts pump/CDU.
            incoming=CV*(ql*(hot-273.15)+qs*(cold-273.15))
            outgoing=CV*(ql*(old[0]-273.15)+qs*(old[-1]-273.15))
            u0=cap*fsum(x-273.15 for x in old);u1=cap*fsum(x-273.15 for x in new)
            env=t['environment_heat_w']
            residual=self.cv(time,'TANK_'+name,u0,u1,incoming,outgoing,0.,env,dt,(ql+qs)*1009,(ql+qs)*1009)
            rows=dict(time_s=time,dt_s=dt,top_C=old[-1]-273.15,bottom_C=old[0]-273.15,
                top_hot_in_m3_h=ql*3600,bottom_cold_out_m3_h=ql*3600,top_hot_out_m3_h=qs*3600,bottom_cold_in_m3_h=qs*3600,
                top_hot_in_C=hot-273.15,bottom_cold_in_C=cold-273.15,
                load_net_heat_W=CV*ql*(hot-old[0]),source_net_heat_W=CV*qs*(cold-old[-1]),
                incoming_enthalpy_W=incoming,outgoing_enthalpy_W=outgoing,pump_direct_W=0.,
                pump_heat_note='ALREADY_IN_PORT_ENTHALPY_NOT_ADDED_AGAIN',ambient_W=env,
                delta_U_J=u1-u0,residual_J=residual,cold_threshold_C=41.4448,
                cold_m3=sum(x<=314.5948 for x in new)*self.tanks[name].volume/len(new),
                extractable_sensible_to_threshold_J=cap*fsum(max(0.,314.5948-x) for x in new),
                internal_vertical_net_m3_h=(qs-ql)*3600,
                interface_direction='UPWARD' if qs>=ql else 'DOWNWARD',
                cumulative_delta_U_J=self.sums['TANK_'+name]['delta_U_J'])
            self.tank_csv[name].add(rows)
        # Main/transfer HXs are algebraic. Opposite heat rates, zero mass transfer.
        qmain=r['load_flow_m3_h']/3600
        hot=r['actual_primary_return_c']+273.15
        hx_cold=hot-(n['transfer_heat_w']/(CV*qmain) if qmain else 0.)
        self.cv(time,'HX_NEUTRAL_SIDE',0.,0.,CV*qmain*(hot-273.15),CV*qmain*(hx_cold-273.15),0.,-n['transfer_heat_w'],dt,qmain*1009,qmain*1009,'ALGEBRAIC_NO_HX_INVENTORY')
        self.cv(time,'HX_TRANSFER_SIDE',0.,0.,CV*transfer*(n['transfer_in_k']-273.15),CV*transfer*(n['transfer_return_k']-273.15),0.,n['transfer_heat_w'],dt,transfer*1009,transfer*1009,'ALGEBRAIC_NO_HX_INVENTORY')
        self.cv(time,'NEUTRAL_BUFFER_AND_ALGEBRAIC_PRIMARY',n['capacity_j_k']*(n['old_k']-273.15),n['capacity_j_k']*(n['new_k']-273.15),r['unit_hx_w'],n['transfer_heat_w'],mp,n['environment_w'],dt,qmain*1009,qmain*1009)
        for i,u in enumerate(r['unit_records']):
            vol=[.1,*([.025]*6),*([.15]*6),.15]
            u0=CV*fsum(v*(t-273.15) for v,t in zip(vol,u['old_k']));u1=CV*fsum(v*(t-273.15) for v,t in zip(vol,u['new_k']))
            self.cv(time,'CDU'+str(i+1)+'_SECONDARY_RING',u0,u1,0.,u['hx_w'],u['pump_electrical_w'],883500.,dt,u['flow_m3_s']*1009,u['flow_m3_s']*1009)
            qp=u['primary_flow_m3_s']
            self.cv(time,'CDU'+str(i+1)+'_PRIMARY_HX',0.,0.,CV*qp*(u['primary_inlet_k']-273.15),CV*qp*(u['primary_outlet_k']-273.15),0.,u['hx_w'],dt,qp*1009,qp*1009,'ALGEBRAIC_PRIMARY_NO_PIPE_STORAGE')
        # Source + its transport pipe, RC + pipe; all others private standby loops.
        for path,p in self.pipes.items():
            old=pipes[path];new=p.t;u0=p.cap*fsum(x-273.15 for x in old);u1=p.cap*fsum(x-273.15 for x in new)
            q=0.;hin=hout=pump=external=0.
            if path==r['source_path']:
                q=source;top=r['tank_records'][r['source_tank']]['old_k'][-1]
                hin=CV*q*(top-273.15);hout=CV*q*(r['source_return_k']-273.15);pump=sp;external-=r['main_rejected_w']
            if path=='RC' and recharge>0:
                q=recharge;top=r['tank_records']['B']['old_k'][-1]
                hin=CV*q*(top-273.15);hout=CV*q*(old[-1]-273.15);pump=rp;external-=r['rc_rejected_w']
            for tag,ap,ar,ag in self.loop_events:
                if tag==path:pump+=ap;external+=ag-ar
            external+=self.gains.get(path,0.)
            self.cv(time,'SOURCE_AND_PIPE_'+path,u0,u1,hin,hout,pump,external,dt,q*1009,q*1009)
        # Explicit selected transfer loop has pump heat but no modeled transport volume.
        bottom=r['tank_records'][r['load_tank']]['old_k'][0]
        self.cv(time,'TRANSFER_PUMP_AND_HX',0.,0.,CV*transfer*(bottom-273.15),CV*transfer*(n['transfer_return_k']-273.15),tp,n['transfer_heat_w'],dt,transfer*1009,transfer*1009,'OVERLAPPING_DIAGNOSTIC_CV_DO_NOT_SUM_WITH_HX_SIDE')
        profile=dict(time_s=time,A=r['tank_records']['A']['new_k'],B=r['tank_records']['B']['new_k'],pipes={k:list(p.t) for k,p in self.pipes.items()})
        self.profile_file.write(json.dumps(profile,separators=(',',':'),allow_nan=False)+'\n')
        if end_ns%1000000000==0:
            self.curves.append(dict(time_s=time,A_cold_m3=r['tank_A_cold_m3'],B_cold_m3=r['tank_B_cold_m3'],
                rack_C=max(max(u['new_k'][1:7])-273.15 for u in r['unit_records']),source_m3_h=source*3600,transfer_m3_h=transfer*3600,
                source_return_C=r['source_return_k']-273.15,load_heat_kW=r['unit_hx_w']/1000,transfer_kW=n['transfer_heat_w']/1000,
                source_kW=r['main_rejected_w']/1000,RC_kW=r['rc_rejected_w']/1000,pump_kW=r['primary_pump_electrical_w']/1000,
                A_delta_U_MJ=self.sums['TANK_A']['delta_U_J']/1e6,B_delta_U_MJ=self.sums['TANK_B']['delta_U_J']/1e6))
        targets=(30.,31.1,42.9,62.9,84.7,120.1,635.9,638.1,1800.)
        if any(abs(time-x)<dt/3 for x in targets) or end_ns==round(self.spec['seconds']*1e9):
            self.keyframes.append(dict(time_s=time,profile=profile,tanks=r['tank_records'],source_tank=r['source_tank'],load_tank=r['load_tank'],
                source_path=r['source_path'],source_m3_h=source*3600,transfer_m3_h=transfer*3600,recharge_m3_h=recharge*3600,
                main_m3_h=qmain*3600,source_pump_kW=sp/1000,rc_pump_kW=rp/1000,transfer_pump_kW=tp/1000,
                source_heat_kW=r['main_rejected_w']/1000,rc_heat_kW=r['rc_rejected_w']/1000,transfer_heat_kW=n['transfer_heat_w']/1000,
                valves=dict(source=r['source_valve'],transfer=r['load_valve']),pressure_absolute_kPa=None,
                main_dp_kPa=n['main_dp_pa']/1000,transfer_dp_kPa=n['transfer_dp_pa']/1000))
        return r

    def finish(self):
        for f in [*self.tank_csv.values(),self.cv_csv]:f.close()
        self.profile_file.close()
        return dict(steps=self.steps,integrals=self.sums,max_CV_step_residual_J=self.max_residual,keyframes=self.keyframes,
            curves=self.curves,initial_profiles=self.initial,second_fault_preconditions=self.pre_second,
            enthalpy_reference='PG25 rho1009 kg/m3 cp4000 J/kgK; h=cp*(T-273.15K); frozen engineering assumptions, not OEM property curve',
            double_count_warning='Nested diagnostic CVs overlap; never sum their energy columns. Whole-system identity separately checked.',
            capture='Read-only subclass; exact six historical raw hashes required for baseline')
