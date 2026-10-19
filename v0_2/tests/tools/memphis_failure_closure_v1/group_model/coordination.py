"""Versioned project-only measured readiness and changeover. Frozen M1 untouched."""
from dataclasses import dataclass
from math import isfinite
from .legacy_coordination import SourceObservation as LegacyObservation,Coordinator as LegacyCoordinator,ProjectProtection as LegacyProtection,SourcePLC as LegacyPLC,record,estimated_cold
from .common import check
SourceObservation=LegacyObservation

@dataclass(frozen=True)
class ClosureObservation(LegacyObservation):
    standby_near_c:float
    standby_far_c:float
    standby_flow_m3_s:float
    ready_sample_ns:int
    claimed_ready:bool
    third_available:bool
    third_near_c:float
    third_far_c:float
    third_flow_m3_s:float
    source_enable_echo:bool
    load_selector:str
    load_valve_feedback:float
    active_pumps:int
    deadleg_verified:bool
    reserve_A_k:tuple
    reserve_B_k:tuple
    source_valve_target_echo:float

CONTROL_KEYS={'extensions','strategy','tank_volume_m3','primary_target_c','startup_s','recharge','recharge_at_s','independent_recharge','source_speed_margin','use_spare','reserve_fraction_required','ready_flow_m3_h','ready_hold_s','source_ready_ttl_s','valve_response_deadline_s'}
CONTROL_KEYS.add('restore_with_four_pumps')
CONTROL_KEYS.add('design_flow_takeover')
def control_options(spec):return {k:v for k,v in spec.items() if k in CONTROL_KEYS}

class ClosureProtection:
    def __init__(self,options):
        self.o=options;self.latched=set();self.low_since=None;self.valve_since=None;self.cold_since={};self.ready={}
    def evaluate(self,o,now):
        check(o.sample_ns<=o.release_ns<=now,'SOURCE_FUTURE_MEASUREMENT')
        if now-o.sample_ns>1_000_000_000:self.latched.add('SOURCE_SENSOR_STALE')
        if o.primary_load_flow_m3_s<.8*330/3600:self.latched.add('PRIMARY_LOAD_FLOW_LOW_MEASURED')
        if o.maximum_secondary_inlet_c>=44.5:self.latched.add('SECONDARY_RACK_INLET_HIGH_REQUIRES_TAKEOVER')
        if o.wet_inlet_gauge_pa is not None and not 100000<=o.wet_inlet_gauge_pa<=600000:self.latched.add('WET_COIL_PRESSURE_RANGE_MEASURED')
        if o.source_enable_echo and o.source_speed>.2 and o.source_flow_m3_s<.8*330/3600:
            if self.low_since is None:self.low_since=now
            if now-self.low_since>=1_000_000_000:self.latched.add('SOURCE_COMMAND_WITHOUT_MEASURED_FLOW')
        else:self.low_since=None
        if abs(o.source_valve-o.source_valve_target_echo)>.01:
            if self.valve_since is None:self.valve_since=now
            if now-self.valve_since>=round(self.o.get('valve_response_deadline_s',7)*1e9):self.latched.add('VALVE_NOT_AT_REQUESTED_TARGET')
        else:self.valve_since=None
        for path,a,b,q,available in [('W2',o.standby_near_c,o.standby_far_c,o.standby_flow_m3_s,o.w2_available),('W3',o.third_near_c,o.third_far_c,o.third_flow_m3_s,o.third_available)]:
            fresh=0<=now-o.ready_sample_ns<=round(self.o.get('source_ready_ttl_s',.6)*1e9)
            numeric=all(isfinite(x) for x in (a,b,q))
            passed=fresh and numeric and max(a,b)+.2<=41.4448 and abs(a-b)<=.3 and q>=self.o.get('ready_flow_m3_h',60)/3600 and available and o.deadleg_verified
            if passed:self.cold_since.setdefault(path,now)
            else:self.cold_since.pop(path,None)
            self.ready[path]=passed and now-self.cold_since.get(path,now)>=round(self.o.get('ready_hold_s',1)*1e9)
        return record(dict(record_id='closure-safety:'+str(now),time_ns=now,measurement_id=o.record_id,codes=sorted(self.latched),
            measured_cold_ready=dict(self.ready),claimed_ready_not_authority=o.claimed_ready,
            scope='PROJECT_V1_NEW_TOPOLOGY_NOT_FROZEN_M1'))

class ClosureCoordinator:
    def __init__(self,recharge=None,recharge_at=120.,initial_path='W1',options=None):
        self.o=options or {};self.state='RUN';self.entered=0;self.path=initial_path;self.tank='A';self.load_tank='A'
        self.needed_path=initial_path;self.needed_tank='A';self.events=[];self.returned_at=None;self.recharge_done=False
        self.fan=.82308;self.integral=0.;self.last_ns=None;self.bad_since=None;self.design_low_since=None;self.handled=set();self.failure_seen=False
        self.source_fault_handled=False;self.thermal_takeover_used=False;self.startup_required=False
        self.recharge=recharge;self.recharge_at=round(recharge_at*1e9);self.wanted_pumps=3
    def transition(self,state,now,reason):
        if self.state!=state:self.events.append(dict(time_ns=now,from_state=self.state,to_state=state,reason=reason));self.state=state;self.entered=now
    def cold(self,tt):
        check(len(tt)==17,'REGISTERED17_TT_REQUIRED')
        return sum(a+.2<=314.5948 and b+.2<=314.5948 for a,b in zip(tt,tt[1:]))*self.o.get('tank_volume_m3',15)/16
    def request(self,o,safety,now):
        check(safety['data']['measurement_id']==o.record_id,'SOURCE_AUTHORITY')
        dt=0 if self.last_ns is None else (now-self.last_ns)/1e9;self.last_ns=now
        error=o.primary_inlet_c-self.o.get('primary_target_c',40.7);self.integral=max(-.7,min(.7,self.integral+error*dt*.001));self.fan=max(0,min(1,.82308+.08*error+self.integral))
        av=dict(W1=o.w1_available,W2=o.w2_available,D1=o.d1_available,D2=o.d2_available,W3=o.third_available)
        blocked=set(safety['data']['codes'])&{'SOURCE_SENSOR_STALE','WET_COIL_PRESSURE_RANGE_MEASURED','SOURCE_COMMAND_WITHOUT_MEASURED_FLOW','VALVE_NOT_AT_REQUESTED_TARGET'}
        reserve=self.cold(o.reserve_B_k)>=self.o.get('reserve_fraction_required',.85)*self.o.get('tank_volume_m3',15)
        if blocked:self.transition('PROTECTED_HOLD',now,'INDEPENDENT_PROTECTION_NO_EXTRA_AUTHORITY')
        if o.leak_A and self.load_tank!='B' and reserve and not blocked:
            self.load_tank='B';self.thermal_takeover_used=True
            self.events.append(dict(time_ns=now,from_state=self.state,to_state=self.state,reason='MEASURED_A_ISOLATION_DEMAND_B_RESERVE_PROVEN'))
        if self.o.get('use_spare') and o.active_pumps<3 and o.source_enable_echo:self.wanted_pumps=4
        if self.o.get('restore_with_four_pumps') and self.failure_seen:
            if self.cold(o.reserve_A_k)<.85*self.o.get('tank_volume_m3',15):self.wanted_pumps=4
            elif self.wanted_pumps==4 and o.active_pumps==4:
                self.wanted_pumps=3
                self.events.append(dict(time_ns=now,from_state=self.state,to_state=self.state,reason='A_RESERVE_PROVEN_RETURN_3_RUNNING_1_STANDBY'))
        if o.source_enable_echo and o.source_speed>.2 and o.source_flow_m3_s<330/3600-1e-12:
            if self.design_low_since is None:self.design_low_since=now
        else:self.design_low_since=None
        design_low=self.o.get('design_flow_takeover') and self.design_low_since is not None and now-self.design_low_since>=3_000_000_000
        bad=not av.get(self.path,False) or bool(design_low)
        if bad and self.bad_since is None:self.bad_since=now
        if not bad:self.bad_since=None
        if bad and now-self.bad_since>=1_000_000_000 and self.path not in self.handled and not blocked:
            self.handled.add(self.path);self.failure_seen=True;self.source_fault_handled=True
            choices=[p for p in ('W2','W1','W3','D2','D1') if p!=self.path and av[p]]
            # Dry capacity at46C cannot replace41C wet duty; do not grant free fallback.
            choices=[p for p in choices if p.startswith('W')]
            if choices:
                self.needed_path=choices[0];self.needed_tank='B' if o.leak_A and reserve else self.tank;self.startup_required=True
                self.transition('REVOKE_RECHARGE',now,'ACTUAL_RELEASED_SOURCE_FAULT')
            else:self.transition('NO_SOURCE',now,'NO_AVAILABLE_INDEPENDENT_SOURCE')
        if self.state=='REVOKE_RECHARGE' and o.recharge_speed<=1e-9:self.transition('STOP_SOURCE',now,'RECHARGE_ZERO_SPEED')
        if self.state=='STOP_SOURCE' and o.source_speed<=1e-9:self.transition('CLOSE',now,'MEASURED_SOURCE_ZERO_SPEED')
        if self.state=='CLOSE' and o.source_valve<=1e-9:
            self.path=self.needed_path;self.tank=self.needed_tank;self.transition('OPEN',now,'MEASURED_CLOSED_BREAK_BEFORE_MAKE')
        if self.state=='OPEN' and (o.source_path,o.source_tank)==(self.path,self.tank) and o.source_valve>=1-1e-9:self.transition('BUILD_COLD',now,'MEASURED_VALVE_OPEN_NOT_COLD_READY')
        ready=safety['data']['measured_cold_ready'].get(self.path,False)
        if self.state=='BUILD_COLD' and now-self.entered>=round(self.o.get('startup_s',20)*1e9):
            if ready:self.returned_at=now;self.startup_required=False;self.transition('RUN',now,'TIMER_AND_RELEASED_PAIRED_TT_FLOW_READY')
            else:self.transition('WAIT_COLD_READY',now,'TIMER_ONLY_IS_NOT_COLD_READY')
        if self.state=='WAIT_COLD_READY' and ready:self.returned_at=now;self.startup_required=False;self.transition('RUN',now,'RELEASED_PAIRED_TT_FLOW_READY')
        if self.state=='RUN' and self.recharge and not self.recharge_done and now>=self.recharge_at and self.o.get('independent_recharge'):
            if self.cold(o.reserve_B_k)<self.o.get('tank_volume_m3',15)*.85:self.transition('INDEPENDENT_RECHARGE',now,'SEPARATE_RC_HX_PUMP_NOT_ONLINE_W2')
        if self.state=='INDEPENDENT_RECHARGE' and self.cold(o.reserve_B_k)>=self.o.get('tank_volume_m3',15)*.85:self.transition('STOP_RECHARGE',now,'REGISTERED17_TT_UNCERTAINTY_GUARDED85PCT_ESTIMATE')
        if self.state=='STOP_RECHARGE' and o.recharge_speed<=1e-9:self.recharge_done=True;self.transition('RUN',now,'RC_ZERO_SPEED_AND_ESTIMATED_RESERVE')
        run=self.state in ('RUN','INDEPENDENT_RECHARGE','STOP_RECHARGE')
        return dict(source_tank=self.tank,source_path=self.path,source_enable=run,source_valve=0. if self.state=='CLOSE' else 1.,pumps=self.wanted_pumps,
            recharge_enable=self.state=='INDEPENDENT_RECHARGE',recharge_path='RC',fan=self.fan,load_tank=self.load_tank,coordinator_state=self.state,
            permission=safety['sha256'],observation_id=o.record_id,source_fault_handled=self.source_fault_handled,thermal_takeover_used=self.thermal_takeover_used,
            thermal_blocked_reason=None,startup_required=self.startup_required,source_speed_margin=self.o.get('source_speed_margin',0.))

class ClosurePLC:
    def __init__(self):self.prior=None
    def issue(self,r,s,o,now):
        check(r['permission']==s['sha256'] and r['observation_id']==o.record_id,'SOURCE_PLC_AUTHORITY')
        if self.prior and (r['source_tank'],r['source_path'])!=(self.prior['source_tank'],self.prior['source_path']):check(o.source_speed<=1e-9 and o.source_valve<=1e-9,'SOURCE_INTERLOCK')
        check(r['source_tank'] in ('A','B') and r['load_tank'] in ('A','B'),'ILLEGAL_AB_PARALLEL_REQUEST')
        check(not r['recharge_enable'] or r['recharge_path']=='RC','SEPARATE_RECHARGE_RESOURCE_REQUIRED')
        p=record(dict(producer='MEMPHIS_SIMULATED_SOURCE_PLC',time_ns=now,safety_sha256=s['sha256'],measurement_id=o.record_id,request=r,scope='NEW_OFFLINE_CLOSURE_NOT_HARDWARE_PLC'))
        self.prior=dict(r);return p

def Coordinator(recharge=None,recharge_at=120.,initial_path='W1',options=None):
    return (ClosureCoordinator if (options or {}).get('extensions') else LegacyCoordinator)(recharge,recharge_at,initial_path,options)
def ProjectProtection(options=None):return ClosureProtection(options) if options and options.get('extensions') else LegacyProtection()
def SourcePLC(options=None):return ClosurePLC() if options and options.get('extensions') else LegacyPLC()
