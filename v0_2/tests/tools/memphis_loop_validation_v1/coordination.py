"""Source-bound project controller. No fault schedule or hidden profile access.

Inventory/temperature estimates are explicitly NOT full 90s reserve qualification.
The independent saved-profile challenge and real second event remain separate.
"""
from math import isfinite
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.coordination import ClosureProtection,ClosurePLC,record
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import check

KEYS={'extensions','architecture','tank_volume_m3','primary_target_c','source_speed_margin',
      'shared_at_s','shared_charge_s','return_budget_s','ready_hold_s','valve_response_deadline_s'}
def control_options(spec):return {k:v for k,v in spec.items() if k in KEYS}

class Protection(ClosureProtection):
    def evaluate(self,o,now):
        base=super().evaluate(o,now)
        # No assumed installed standby preconditioning. Online paired TT+FT
        # is evidence of current cold return, not permission to skip startup.
        fresh=0<=now-o.sample_ns<=600000000
        cold=(fresh and all(isfinite(x) for x in (o.current_source_near_c,o.current_source_far_c))
              and max(o.current_source_near_c,o.current_source_far_c)+.2<=41.4448
              and o.source_flow_m3_s>=330/3600-1e-12)
        name=o.source_path
        if cold:self.cold_since.setdefault('CURRENT_'+name,now)
        else:self.cold_since.pop('CURRENT_'+name,None)
        current=cold and now-self.cold_since.get('CURRENT_'+name,now)>=round(self.o.get('ready_hold_s',1)*1e9)
        return record(dict(base['data'],current_cold_return_confirmed=current,
                           installed_standby_precooling=False,absolute_pressure='NOT_VERIFIED'))

class Controller:
    def __init__(self,recharge=None,recharge_at=120.,initial_path='W1',options=None):
        self.o=options or {};self.state='RUN';self.entered=0;self.path=initial_path;self.tank='A'
        self.target=(self.path,self.tank);self.events=[];self.returned_at=None;self.recharge_done=False
        self.bad_since=None;self.last_ns=None;self.fan=.82308;self.integral=0.;self.wanted_pumps=3
        self.charge_started=None;self.cycles=0;self.pump_degraded=False
        self.rc_state='IDLE';self.rc_tank='B';self.rc_wanted='B';self.rc_entered=0
        self.b_done=False;self.rc_pending=False

    def transition(self,state,now,reason):
        if self.state!=state:
            self.events.append(dict(time_ns=now,from_state=self.state,to_state=state,reason=reason))
            self.state=state;self.entered=now

    def rc_transition(self,state,now,reason):
        if state!=self.rc_state:
            self.events.append(dict(time_ns=now,from_state='RC_'+self.rc_state,to_state='RC_'+state,reason=reason))
            self.rc_state=state;self.rc_entered=now

    @staticmethod
    def cold(tt):
        check(len(tt)==17 and all(isfinite(x) for x in tt),'REGISTERED17_TT')
        return sum(a+.2<=314.5948 and b+.2<=314.5948 for a,b in zip(tt,tt[1:]))*15/16

    @classmethod
    def screening(cls,tt):
        # Stronger observed screen, still not a discharge guarantee or hidden truth.
        return cls.cold(tt)>=14.0625 and max(tt[:16])-min(tt[:16])<=.25

    def switch(self,path,tank,now,reason):
        self.target=(path,tank);self.transition('STOP_SOURCE',now,reason)

    def request(self,o,safety,now):
        check(o.release_ns<=now and safety['data']['measurement_id']==o.record_id,'RELEASED_AUTHORITY')
        dt=0. if self.last_ns is None else (now-self.last_ns)/1e9;self.last_ns=now
        error=o.primary_inlet_c-self.o.get('primary_target_c',40.7)
        self.integral=max(-.7,min(.7,self.integral+error*dt*.001));self.fan=max(0.,min(1.,.82308+.08*error+self.integral))
        ca,cb=self.cold(o.reserve_A_k),self.cold(o.reserve_B_k)
        sa,sb=self.screening(o.reserve_A_k),self.screening(o.reserve_B_k)
        self.b_done=sb;self.recharge_done=sa and sb
        blocked=set(safety['data']['codes'])&{'SOURCE_SENSOR_STALE','SOURCE_COMMAND_WITHOUT_MEASURED_FLOW','VALVE_NOT_AT_REQUESTED_TARGET'}
        if blocked:self.transition('PROTECTED_HOLD',now,'INDEPENDENT_PROTECTION_LATCHED')
        # A running-circuit flow deficit cannot be cured by closing its load selector.
        if o.source_enable_echo and o.source_speed>.2 and o.source_valve>=1-1e-9 and o.active_pumps<self.wanted_pumps:
            self.pump_degraded=True
            if self.tank=='B' and self.state not in ('PROTECTED_HOLD','NO_SOURCE'):
                self.switch(self.path,'A',now,'PUMP_DEGRADED_ABORT_PLANNED_B_RECHARGE')
        available={'W1':o.w1_available,'W2':o.w2_available}
        bad=not available.get(self.path,False)
        if bad and self.bad_since is None:self.bad_since=now
        if not bad:self.bad_since=None
        if bad and now-self.bad_since>=1000000000 and self.state not in ('PROTECTED_HOLD','STOP_SOURCE','CLOSE','OPEN'):
            candidates=[p for p in ('W2','W1') if p!=self.path and available[p]]
            if candidates:self.switch(candidates[0],'A',now,'RELEASED_SOURCE_UNAVAILABLE_KEEP_A_LOAD_RUNNING')
            else:self.transition('NO_SOURCE',now,'NO_AVAILABLE_WET_SOURCE_NO_INVENTED_W3')
        if self.state=='STOP_SOURCE' and o.source_speed<=1e-9:self.transition('CLOSE',now,'SOURCE_ZERO_SPEED')
        if self.state=='CLOSE' and o.source_valve<=1e-9:
            self.path,self.tank=self.target;self.transition('OPEN',now,'OLD_SUPPLY_RETURN_CLOSED')
        if self.state=='OPEN' and (o.source_path,o.source_tank)==(self.path,self.tank) and o.source_valve>=1-1e-9:
            self.transition('BUILD_COLD',now,'PAIR_OPEN_START_FLOW_NOT_A_COLD_RETURN_CLAIM')
        if self.state=='BUILD_COLD' and safety['data']['current_cold_return_confirmed']:
            self.returned_at=now;self.transition('RUN',now,'RELEASED_PAIRED_TT_AND_DESIGN_FT_COLD_RETURN')
        # Four-pump recovery is bounded by actual curves; no imposed 440m3/h.
        self.wanted_pumps=4 if (not sa or self.pump_degraded) and self.tank=='A' else 3
        now_s=now/1e9
        if self.o['architecture']=='ORIGINAL_SHARED' and self.state=='RUN':
            if self.tank=='A' and now_s>=self.o.get('shared_at_s',120.) and not sb and sa and not self.pump_degraded:
                # Entire absence budget includes both stop/close/open/start legs.
                need=8.25+330/3600*(self.o.get('shared_charge_s',10.)+self.o.get('return_budget_s',30.))
                if ca>=need:
                    self.charge_started=None;self.switch(self.path,'B',now,'OBSERVED_A_SCREEN_AND_WHOLE_ABSENCE_BUDGET_ALLOW_SEGMENT')
            elif self.tank=='B':
                if self.charge_started is None:self.charge_started=now
                if sb or (now-self.charge_started)/1e9>=self.o.get('shared_charge_s',10.) or ca<11.:
                    self.cycles+=1;self.switch(self.path,'A',now,'BOUNDED_SEGMENT_RETURN_A_BEFORE_EXHAUSTION')
        # Even while B has not become cold, start the return before the full A
        # budget is consumed. Time origin is actual selector ownership, not RUN.
        if self.tank=='B' and self.state=='BUILD_COLD':
            if self.charge_started is None:self.charge_started=now
            if (now-self.charge_started)/1e9>=self.o.get('shared_charge_s',10.) or ca<11.:
                self.cycles+=1;self.switch(self.path,'A',now,'B_COLD_NOT_ESTABLISHED_ABORT_BEFORE_A_RESERVE_LOSS')
        rc_enabled=self.o['architecture']=='SELECTABLE_RC' and not blocked and now_s>=self.o.get('shared_at_s',120.)
        if not rc_enabled and self.rc_state not in ('IDLE','STOP','CLOSE'):
            self.rc_pending=False
            self.rc_transition('STOP',now,'RC_PERMISSION_WITHDRAWN')
        if rc_enabled and self.rc_state=='IDLE':
            choice='B' if not sb else 'A' if not sa else None
            if choice:
                self.rc_wanted=choice;self.rc_pending=True
                self.rc_transition('STOP',now,'OBSERVED_RESERVE_SCREEN_DEMAND_'+choice)
        if self.rc_state=='STOP' and o.recharge_speed<=1e-9:self.rc_transition('CLOSE',now,'RC_ZERO_SPEED')
        if self.rc_state=='CLOSE' and o.rc_valve_feedback<=1e-9:
            self.rc_tank=self.rc_wanted
            self.rc_transition('OPEN' if rc_enabled and self.rc_pending else 'IDLE',now,'RC_OLD_PAIR_CLOSED_SAME_TANK_SUPPLY_RETURN')
        if self.rc_state=='OPEN' and o.actual_rc_tank==self.rc_tank and o.rc_valve_feedback>=1-1e-9:
            self.rc_transition('RUN',now,'RC_PAIR_OPEN_ALLOW_ACTUAL_PUMP_RAMP')
        if self.rc_state=='RUN' and (sb if self.rc_tank=='B' else sa):
            self.rc_transition('STOP',now,'SELECTED_TANK_SCREEN_MET_NOT_FULL_DISCHARGE_QUALIFICATION')
            self.rc_wanted='A' if self.rc_tank=='B' else 'B'
            self.rc_pending=not (sa if self.rc_wanted=='A' else sb)
        if self.rc_state in ('STOP','CLOSE','OPEN') and now-self.rc_entered>8000000000:
            # RC timeout stops RC only; independent project safety retains A flow.
            if self.rc_state=='OPEN':
                self.rc_pending=False;self.rc_transition('STOP',now,'RC_VALVE_TIMEOUT_ABORT')
        return dict(source_tank=self.tank,source_path=self.path,source_enable=self.state in ('RUN','BUILD_COLD'),
            source_valve=0. if self.state=='CLOSE' else 1.,pumps=self.wanted_pumps,
            recharge_enable=self.rc_state=='RUN' and rc_enabled,recharge_path='RC',rc_tank=self.rc_tank,
            rc_valve=0. if self.rc_state in ('IDLE','CLOSE') else 1.,rc_state=self.rc_state,
            fan=self.fan,load_tank='A',coordinator_state=self.state,permission=safety['sha256'],observation_id=o.record_id,
            source_speed_margin=self.o.get('source_speed_margin',0.),B_RECHARGE_DONE=sb,
            A_RESERVE_SCREEN=sa,B_RESERVE_SCREEN=sb,DUAL_RESERVE_SCREEN=sa and sb,
            DUAL_RESERVE_READY='NOT_CERTIFIED_BY_TT_SCREEN',SECOND_FAULT_QUALIFIED='OFFLINE_TEST_ONLY',
            shared_charge_cycles=self.cycles,pump_degraded=self.pump_degraded)

class PLC(ClosurePLC):
    def issue(self,r,s,o,now):
        check(r['rc_tank'] in ('A','B'),'ILLEGAL_RC_TANK')
        if self.prior and r['rc_tank']!=self.prior['rc_tank']:
            check(o.recharge_speed<=1e-9 and o.rc_valve_feedback<=1e-9,'RC_PLC_BREAK_BEFORE_MAKE')
        check(not r['recharge_enable'] or o.rc_valve_feedback>=1-1e-9,'RC_PLC_OPEN_PAIR_REQUIRED')
        return super().issue(r,s,o,now)

def Coordinator(recharge=None,recharge_at=120.,initial_path='W1',options=None):return Controller(recharge,recharge_at,initial_path,options)
def ProjectProtection(options=None):return Protection(options)
def SourcePLC(options=None):return PLC()
