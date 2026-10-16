"""Project fast protection and source take-over; no M1 tracking timer here."""
from dataclasses import dataclass,asdict
from hashlib import sha256
import json
from .common import check

@dataclass(frozen=True)
class SourceObservation:
    sample_ns:int
    release_ns:int
    record_id:str
    source_speed:float
    source_valve:float
    source_tank:str
    source_path:str
    source_flow_m3_s:float
    recharge_speed:float
    w1_available:bool
    w2_available:bool
    leak_A:bool
    primary_inlet_c:float
    tank_A_tt_k:tuple
    tank_B_tt_k:tuple
    primary_load_flow_m3_s:float
    wet_inlet_gauge_pa:float|None
    maximum_secondary_inlet_c:float
    d1_available:bool
    d2_available:bool

def record(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return dict(data=value,sha256=sha256(raw).hexdigest())

def estimated_cold(tt):
    # Four equally spaced, explicitly assumed instruments. A segment is counted
    # only when both measured endpoints are cold; estimator not a real tank gauge.
    return sum(a<=314.5948 and b<=314.5948 for a,b in zip(tt,tt[1:]))*5.

class ProjectProtection:
    def __init__(self):self.latched=set()
    def evaluate(self,obs,now):
        check(obs.sample_ns<=obs.release_ns<=now,'PROJECT_FUTURE_MEASUREMENT')
        if obs.leak_A:self.latched.add('LEAK_SENSOR_A_MEASURED')
        if obs.primary_load_flow_m3_s<.8*330/3600:self.latched.add('PRIMARY_LOAD_FLOW_LOW_MEASURED')
        if obs.wet_inlet_gauge_pa is not None and not 100000<=obs.wet_inlet_gauge_pa<=600000:self.latched.add('WET_COIL_PRESSURE_RANGE_MEASURED')
        if not obs.w1_available and not obs.w2_available:self.latched.add('NO_AVAILABLE_WET_SOURCE_MEASURED')
        if now-obs.sample_ns>1_000_000_000:self.latched.add('SOURCE_SENSOR_STALE')
        if obs.maximum_secondary_inlet_c>=44.5:self.latched.add('SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER')
        return record(dict(record_id='project-safety:'+str(now),time_ns=now,
            measurement_id=obs.record_id,codes=sorted(self.latched),scope='PROJECT_DEVELOPMENT_FAST_PROTECTION_NOT_M1_TRACKING'))

class Coordinator:
    def __init__(self,recharge=None,recharge_at=120.,initial_path='W1'):
        self.state='RUN';self.entered=0;self.bad_since=None;self.recharge=recharge
        self.recharge_at_ns=round(recharge_at*1e9);self.path=initial_path;self.tank='A'
        self.needed_path='W2';self.needed_tank='A';self.load_tank='A';self.resume='RUN';self.recharge_done=False
        self.fan=.82308;self.integral=0.;self.last_ns=None;self.events=[];self.failure_seen=False
        self.revoke_at=None;self.start_fault_at=None;self.returned_at=None

    def transition(self,state,now,reason):
        if state!=self.state:
            self.events.append(dict(time_ns=now,from_state=self.state,to_state=state,reason=reason))
            self.state=state;self.entered=now

    def request(self,obs,safety,now):
        check(safety['data']['measurement_id']==obs.record_id,'PROJECT_SAFETY_BINDING')
        dt=0 if self.last_ns is None else (now-self.last_ns)/1e9;self.last_ns=now
        error=obs.primary_inlet_c-41;self.integral=max(-.7,min(.7,self.integral+error*dt*.001))
        self.fan=max(0.,min(1.,.82308+.08*error+self.integral))
        available=dict(W1=obs.w1_available,W2=obs.w2_available,D1=obs.d1_available,D2=obs.d2_available)
        bad=not available[self.path] or obs.leak_A
        if bad and self.bad_since is None:self.bad_since=now
        if not bad:self.bad_since=None
        fault=bad and now-self.bad_since>=1_000_000_000
        if fault and not self.failure_seen:
            self.failure_seen=True;self.start_fault_at=now;self.revoke_at=now
            self.needed_path={'W1':'W2','W2':'W1','D1':'D2','D2':'D1'}[self.path]
            self.needed_tank='B' if obs.leak_A else self.tank
            self.resume='RUN';self.transition('REVOKE_RECHARGE',now,'INDEPENDENT_MEASURED_FAULT')
        if fault and not obs.w1_available and not obs.w2_available:self.transition('NO_SOURCE',now,'COMMON_FAILURE_NOT_CURED_BY_TOWER_SWITCH')
        if ('SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER' in safety['data']['codes']
            and self.state=='RUN' and not self.failure_seen):
            if estimated_cold(obs.tank_B_tt_k)>=8.25:
                self.failure_seen=True;self.needed_tank='B';self.load_tank='B';self.needed_path=self.path
                self.resume='RUN';self.transition('REVOKE_RECHARGE',now,'SECONDARY_INLET44_5_AND_MEASURED_B_RESERVE')
        if 'WET_COIL_PRESSURE_RANGE_MEASURED' in safety['data']['codes']:self.transition('PRESSURE_STOP',now,'INDEPENDENT_PRESSURE_PROTECTION')
        if self.state=='RUN' and self.recharge and not self.recharge_done and now>=self.recharge_at_ns and not self.failure_seen:
            if self.recharge=='INDEPENDENT':self.transition('INDEPENDENT_RECHARGE',now,'PLAN_WITHOUT_SOURCE_DIVERSION')
            elif estimated_cold(obs.tank_A_tt_k)>=8.25:
                self.needed_tank='B';self.needed_path=self.path;self.resume='STAGED_RECHARGE'
                self.transition('STOP_SOURCE',now,'SHARED_RECHARGE_PERMISSION_MEASURED_INVENTORY')
        if self.state=='REVOKE_RECHARGE' and obs.recharge_speed<=1e-9:self.transition('STOP_SOURCE',now,'RECHARGE_ZERO_SPEED_BEFORE_RELEASE')
        if self.state=='STOP_SOURCE' and obs.source_speed<=1e-9:self.transition('CLOSE',now,'SOURCE_ZERO_SPEED_PROVEN')
        if self.state=='CLOSE' and obs.source_valve<=1e-9:self.transition('SELECT',now,'OLD_PATH_CLOSED_PROVEN')
        if self.state=='SELECT':
            self.path=self.needed_path;self.tank=self.needed_tank;self.transition('OPEN',now,'BREAK_BEFORE_MAKE_SELECTOR')
        if self.state=='OPEN' and obs.source_tank==self.tank and obs.source_path==self.path and obs.source_valve>=1-1e-9:
            self.transition('BUILD_COLD' if self.failure_seen else self.resume,now,'NEW_PATH_VALVES_OPEN')
        if self.state=='BUILD_COLD' and now-self.entered>=54_000_000_000:
            self.returned_at=now;self.transition('RUN',now,'ASSUMED_STANDBY54S_STARTUP_COMPLETED')
        if self.state=='STAGED_RECHARGE' and (now-self.entered>=60_000_000_000 or estimated_cold(obs.tank_A_tt_k)<5.):
            self.needed_tank='A';self.needed_path=self.path;self.resume='RESTORE_A';self.transition('STOP_SOURCE',now,'BOUNDED_DIVERSION_END_OR_MEASURED_RESERVE')
        if self.state=='RESTORE_A' and estimated_cold(obs.tank_A_tt_k)>=10.:
            if estimated_cold(obs.tank_B_tt_k)>=8.25:self.recharge_done=True;self.transition('RUN',now,'B_BACKUP_READY_AND_A_RESTORED')
            else:self.needed_tank='B';self.resume='STAGED_RECHARGE';self.transition('STOP_SOURCE',now,'A_RESTORED_ALLOW_NEXT_B_STAGE')
        if self.state=='INDEPENDENT_RECHARGE' and estimated_cold(obs.tank_B_tt_k)>=8.25:
            self.transition('STOP_RECHARGE',now,'B_MEASURED_READY')
        if self.state=='STOP_RECHARGE' and obs.recharge_speed<=1e-9:self.recharge_done=True;self.transition('RUN',now,'RECHARGE_ZERO_SPEED_AND_BACKUP_READY')
        run=self.state in ('RUN','STAGED_RECHARGE','RESTORE_A','INDEPENDENT_RECHARGE','STOP_RECHARGE')
        valve=0. if self.state=='CLOSE' else 1.
        recharge=self.state=='INDEPENDENT_RECHARGE' and not self.failure_seen
        return dict(source_tank=self.tank,source_path=self.path,source_enable=run,source_valve=valve,
            pumps=4 if self.state=='RESTORE_A' else 3,recharge_enable=recharge,fan=self.fan,
            load_tank='B' if obs.leak_A else self.load_tank,coordinator_state=self.state,
            permission=safety['sha256'],observation_id=obs.record_id)

class SourcePLC:
    """Genuine in-process issuer for this NEW project lane, not a hardware receipt."""
    def __init__(self):self.prior=None;self.records=[]
    def issue(self,request,safety,obs,now):
        check(request['permission']==safety['sha256'] and request['observation_id']==obs.record_id,'SOURCE_PLC_AUTHORITY_BINDING')
        changed=self.prior is not None and (request['source_tank'],request['source_path'])!=(self.prior['source_tank'],self.prior['source_path'])
        if changed:check(obs.source_speed<=1e-9 and obs.source_valve<=1e-9,'FORBIDDEN_OPEN_OR_MOVING_PATH_CHANGE')
        check(not(request['recharge_enable'] and request['source_path']=='W2'),'ONE_WET_UNIT_TWO_ROLES')
        token=record(dict(producer='MEMPHIS_SIMULATED_SOURCE_PLC',time_ns=now,
            safety_sha256=safety['sha256'],measurement_id=obs.record_id,request=request,
            scope='NEW_OFFLINE_PROJECT_CAUSAL_ISSUE_NOT_PHYSICAL_PLC_PROOF'))
        self.prior=dict(request);return token
