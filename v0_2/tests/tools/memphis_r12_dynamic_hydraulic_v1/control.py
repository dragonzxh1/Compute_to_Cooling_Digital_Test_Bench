"""New research controller. Released model measurements only, never the plant object.

This is not a modified or requalified frozen M1 implementation. Command admission
and fast temperature latch are separate functions; all receipts are simulated.
"""
import copy
import math


class Measurements:
    def __init__(self,a,case):self.a=a;self.case=case;self.queue=[];self.last=None;self.filtered=None
    def sample(self,physical,t,dt):
        if self.case['kind']=='INSTRUMENT_STALE' and t>=self.case['fault_s']:return
        frame=copy.deepcopy(physical)
        if self.filtered is not None:
            alpha=1-math.exp(-dt/self.a['instrument_lag_s'])
            for collection in ('cdus','racks'):
                for tag,values in frame[collection].items():
                    for key,value in values.items():
                        if isinstance(value,(int,float)) and not isinstance(value,bool):
                            values[key]=self.filtered[collection][tag][key]+alpha*(value-self.filtered[collection][tag][key])
        self.filtered=copy.deepcopy(frame)
        frame.update(sampled_at=t,release_at=t+self.a['instrument_release_delay_s'],
            evidence_type='RELEASED_MODELED_SENSOR_FRAME_NOT_FIELD_MEASUREMENT',
            channels='CH1_CH2_DESIGN_REGISTRY_NO_PHYSICAL_INDEPENDENCE_CLAIM')
        self.queue.append(frame)
    def release(self,t):
        while self.queue and self.queue[0]['release_at']<=t+1e-9:self.last=self.queue.pop(0)
        return copy.deepcopy(self.last)


def fast_protection(frame,latched):
    if frame and any(r['supply_C']>45 for r in frame['racks'].values()):latched=True
    return latched


class Controller:
    def __init__(self,reg):
        self.a=reg['assumptions'];self.req=reg['requirements'];self.state='DUTY_A'
        self.events=[];self.stable_since=None;self.overlap_since=None;self.fault_latch=False
        self.completed_at=None;self.last_now=-1.;self.refusal=None
        self.master_reference={};self.follower_reference=None
    def event(self,t,state,reason):
        if self.state!=state:self.events.append(dict(t=t,old=self.state,new=state,reason=reason));self.state=state
    def command(self,frame,now,dt):
        if now<self.last_now:raise RuntimeError('CONTROL_TIME_REVERSED')
        self.last_now=now;cmd={'valves':{},'speeds':{}}
        if frame is None:return cmd
        if frame['sampled_at']>frame['release_at'] or frame['release_at']>now+1e-9:raise RuntimeError('FUTURE_MEASUREMENT')
        if now-frame['sampled_at']>self.a['measurement_max_age_s']:
            self.event(now,'MEASUREMENT_HOLD','Released frame expired; no new transfer permission');return cmd
        self.fault_latch=fast_protection(frame,self.fault_latch)
        if self.fault_latch:
            self.event(now,'SAFETY_LATCH','Independent 45C inlet trip; load is not deleted');return cmd
        a,b=frame['cdus']['A'],frame['cdus']['B']
        if frame['master'] in ('A','B'):
            side=frame['master'];meas=sum(r['dp_kPa'] for r in frame['racks'].values())/6*1000
            target=self.a['rack_drop_at_design_Pa']*(1+self.a['pressure_control_flow_margin_fraction'])**2
            old=self.master_reference.get(side,frame['speeds']['G01-C01'+side+'-P2-PM1'])
            ref=max(0.,min(1.,old+self.a['pressure_master_gain_speed_per_Pa_s']*(target-meas)*dt))
            self.master_reference[side]=ref;cmd['speeds']['G01-C01'+side+'-P2-PM1']=ref
        if self.state=='DUTY_A' and frame['alarm_A']:
            self.event(now,'PREPARE_B','Released duty-CDU diagnostic, not a source fault')
        if self.state=='PREPARE_B':
            prefix='G01-C01B-'
            for suffix in ('P1-CV-AS','P1-CV-AR','P1-HV-I','P1-HV-O','P1-F01-I','P1-F01-O',
                'P2-XV-RET','P2-PM1-I','P2-PM1-O','P2-F01-I','P2-F01-O'):cmd['valves'][prefix+suffix]=1.
            desired_dp=max(0.,a['outlet_kPa_g']-b['suction_kPa_g'])*1000
            cmd['speeds'][prefix+'P2-PM1']=min(.99,math.sqrt(desired_dp/self.a['pump_shutoff_head_Pa']))
            dt_match=abs(a['supply_C']-b['supply_C'])
            dp_match=abs(a['outlet_kPa_g']-b['outlet_kPa_g'])
            match=(dt_match<=self.req['match_delta_T_K'] and dp_match<=self.req['match_delta_p_kPa']
                and b['primary_flow_m3_h']>0 and b['speed']>.01)
            if match:
                if self.stable_since is None:self.stable_since=now
            else:self.stable_since=None
            if self.stable_since is not None and now-self.stable_since>=self.req['match_stable_s']-1e-9:
                self.overlap_since=now;self.follower_reference=b['speed']
                self.event(now,'OVERLAP','Measured dT/dp continuously within limits for 5s')
        if self.state in ('OVERLAP','STOP_OLD','ISOLATE_OLD'):
            close_allowance=self.a['valve_travel_s']+self.a['instrument_release_delay_s']+self.a['instrument_sample_s']
            if now-self.overlap_since>=self.req['overlap_max_s']-close_allowance:
                for r in range(1,7):
                    for end in ('BS','BR'):cmd['valves'][f'G01-U1-R{r:02d}-CV-'+end]=0.
                cmd['valves']['G01-C01B-P2-XV-SUP']=0.
                cmd['speeds']['G01-C01B-P2-PM1']=0.
                self.event(now,'OVERLAP_ABORT','30s actual-overlap bound: close early by registered travel/release allowance; no completion');return cmd
            cmd['valves']['G01-C01B-P2-XV-SUP']=1.
            for r in range(1,7):
                for end in ('BS','BR'):cmd['valves'][f'G01-U1-R{r:02d}-CV-'+end]=1.
            # Flow-following open-loop ramp is an explicit research strategy, not OEM logic.
            self.follower_reference=min(.94,self.follower_reference+.03*dt)
            cmd['speeds']['G01-C01B-P2-PM1']=self.follower_reference
        if self.state=='OVERLAP':
            threshold=self.a['flow_established_fraction']
            established=(b['secondary_flow_m3_h']>=threshold*self.req['unit_flow_hot_m3_h']
                and all(r['B_supply_m3_h']>=threshold*self.req['each_rack_flow_hot_m3_h'] for r in frame['racks'].values()))
            if established:
                cmd['master']=None;cmd['speeds']['G01-C01A-P2-PM1']=0.
                self.event(now,'STOP_OLD','New branch actual local flows established; revoke old master then stop')
        if self.state=='STOP_OLD':
            cmd['master']=None;cmd['speeds']['G01-C01A-P2-PM1']=0.
            if a['speed']<.001 and abs(a['secondary_flow_m3_h'])<.01:
                self.event(now,'ISOLATE_OLD','Released zero-speed and near-zero-flow proof')
        if self.state=='ISOLATE_OLD':
            cmd['master']=None;cmd['speeds']['G01-C01A-P2-PM1']=0.
            for tag in frame['valves']:
                if tag.startswith('G01-C01A-') or ('-R0' in tag and tag.endswith(('CV-AS','CV-AR'))):cmd['valves'][tag]=0.
            closed=all(v<.001 for tag,v in frame['valves'].items() if tag.startswith('G01-C01A-') or ('-R0' in tag and tag.endswith(('CV-AS','CV-AR'))))
            if closed:
                cmd['master']='B';self.event(now,'PROVE_B','Old path actually isolated; grant one new master')
        if self.state=='PROVE_B':
            valid=(frame['master']=='B' and all(r['B_supply_m3_h']>=self.req['each_rack_flow_hot_m3_h'] for r in frame['racks'].values()))
            if valid:
                self.completed_at=now;self.event(now,'RUN_B','Actual per-rack flow after master grant')
        return cmd
