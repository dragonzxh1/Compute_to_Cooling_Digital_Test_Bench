"""Unsealed, versioned primary-loop proposal; no third neutral fluid circuit.

All pump curves, 54s cold startup, tank mixing, valve travel and RC sink remain
engineering assumptions, not OEM calibration or an installed hydraulic design.
"""
from dataclasses import dataclass,asdict
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.sources import ClosurePlant
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.coordination import ClosureObservation
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.legacy_sources import recharge_requested_speed
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import check
from .direct_advance import advance

@dataclass(frozen=True)
class LoopObservation(ClosureObservation):
    actual_rc_tank:str
    rc_valve_feedback:float
    current_source_near_c:float
    current_source_far_c:float
    rc_pipe_near_c:float
    rc_pipe_far_c:float

class Plant(ClosurePlant):
    advance=advance
    def __init__(self,spec):
        check(spec['architecture'] in ('ORIGINAL_SHARED','SELECTABLE_RC'),'REGISTERED_ARCHITECTURE')
        check(spec.get('preconditioning_mode')=='NONE' and spec.get('prelude_s',0)==0,'NO_UNREGISTERED_AUXILIARY_COLD_SERVICE')
        self.rc_tank='B';self.rc_valve=0.;self.cold_started={};self.repair_seen=False
        super().__init__(spec)
        self.cold_started[self.source_path]=-1e20
        self.initial_energy=self.energy()

    def inject(self,seconds):
        super().inject(seconds)
        # Explicit maintenance scenario, not an assumed self-repair. Plant only.
        if seconds>=self.spec.get('repair_W1_at_s',float('inf')):
            self.available['W1']=True
            if not self.repair_seen:self.cold_started.pop('W1',None);self.repair_seen=True
        if seconds>=self.spec.get('second_fault_at_s',float('inf')):self.available['W2']=False

    def startup_elapsed(self,now):
        return max(0.,now/1e9-self.cold_started.get(self.source_path,now/1e9))

    def capacity(self,flow,hot_c,now):
        if flow>0:self.cold_started.setdefault(self.source_path,now/1e9)
        if self.startup_elapsed(now)<self.spec['physical_startup_s']:return 0.
        return super().capacity(flow,hot_c,now)

    def rc_capacity(self,now):
        return 0. if now/1e9>=self.spec.get('rc_sink_loss_at_s',float('inf')) else self.spec['rc_capacity_kW']

    def actuate(self,dt,issued):
        r=issued['data']['request'];old=self.recharge_speed
        # Common RC hardware is permitted only in its explicitly registered case.
        if r.get('rc_tank',self.rc_tank)!=self.rc_tank:
            check(old<=1e-9 and self.rc_valve<=1e-9,'RC_PHYSICAL_BREAK_BEFORE_MAKE')
            self.rc_tank=r['rc_tank']
        request=dict(r,recharge_enable=False)
        super().actuate(dt,dict(issued,data=dict(issued['data'],request=request)))
        self.last_request=r
        travel=self.spec.get('valve_s',5.)
        target=r.get('rc_valve',0.)
        if not self.spec.get('rc_valve_stuck'):
            self.rc_valve+=max(-dt/travel,min(dt/travel,target-self.rc_valve))
        on=r.get('recharge_enable',False)
        check(not on or (self.spec['independent_recharge'] and self.rc_valve>=1-1e-9),'RC_ENABLE_REQUIRES_OPEN_LEGAL_PAIR')
        speed=min(1.,recharge_requested_speed(self.spec['recharge_dp_kpa']*1000)) if on else 0.
        self.recharge_speed=old+max(-.5*dt,min(.5*dt,speed-old))
        check(self.recharge_speed<=1e-9 or self.rc_valve>=1-1e-9,'RC_PUMP_WITH_CLOSING_VALVE')
        self.rc_valve=max(0.,min(1.,self.rc_valve))
        return r

    def observation(self,now,units):
        o=asdict(super().observation(now,units));o['wet_inlet_gauge_pa']=None
        t=self.pipes[self.source_path].t;rc=self.pipes.get('RC')
        return LoopObservation(**o,actual_rc_tank=self.rc_tank,rc_valve_feedback=self.rc_valve,
            current_source_near_c=t[0]-273.15,current_source_far_c=t[-1]-273.15,
            rc_pipe_near_c=rc.t[0]-273.15 if rc else 99.,rc_pipe_far_c=rc.t[-1]-273.15 if rc else 99.)

def SourcePlant(spec):return Plant(spec)
