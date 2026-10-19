"""New project-only measured shared recharge. Frozen M1 and prior policy untouched."""
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.coordination import (
    ClosureCoordinator,ClosureProtection,ClosurePLC,record,CONTROL_KEYS)

KEYS=CONTROL_KEYS|{'shared_recharge','shared_at_s','shared_charge_s','active_reserve_fraction','reserve_done_fraction','architecture'}

def control_options(spec):
    # No fault schedule, future injector values, hidden temperatures or flow truth.
    return {k:v for k,v in spec.items() if k in KEYS}


class ContinuityCoordinator(ClosureCoordinator):
    def __init__(self,recharge=None,recharge_at=120.,initial_path='W1',options=None):
        super().__init__(recharge,recharge_at,initial_path,options)
        self.planned_transfer=False;self.charge_started=None;self.cycles=0

    def request(self,o,safety,now):
        r=super().request(o,safety,now)
        shared=self.o.get('shared_recharge',False)
        blocked=self.state in ('PROTECTED_HOLD','NO_SOURCE')
        ready=safety['data']['measured_cold_ready'].get(self.path,False)
        # A cold-source startup needs actual circulation to measure readiness.
        # Enable is NOT a cold-ready claim and never bypasses closed/zero-speed
        # selector interlocks or an independent protection stop.
        if self.state in ('BUILD_COLD','WAIT_COLD_READY') and not blocked:
            r['source_enable']=True
        if self.planned_transfer and self.state in ('BUILD_COLD','WAIT_COLD_READY') and ready:
            self.transition('RUN',now,'SAME_SOURCE_REESTABLISHED_ACTUAL_FLOW_AND_PAIRED_TT')
            r.update(source_enable=True,coordinator_state=self.state)
            self.planned_transfer=False
        if not shared or blocked:return r
        volume=self.o.get('tank_volume_m3',15.)
        ca=self.cold(o.reserve_A_k);cb=self.cold(o.reserve_B_k)
        done=self.o.get('reserve_done_fraction',.9)*volume
        if self.state=='RUN' and self.tank=='A':
            self.wanted_pumps=4 if ca<done else 3
            if ca>=done and cb>=done:
                self.recharge_done=True
            elif not self.recharge_done and now>=round(self.o.get('shared_at_s',120)*1e9) and ca>=self.o.get('active_reserve_fraction',.9)*volume and not o.leak_A:
                self.needed_tank='B';self.needed_path=self.path
                self.planned_transfer=True;self.charge_started=None
                self.transition('STOP_SOURCE',now,'MEASURED_A_RESERVE_PERMITS_B_SEGMENT_NO_AB_PARALLEL')
        elif self.state=='RUN' and self.tank=='B':
            if self.charge_started is None:self.charge_started=now
            elapsed=(now-self.charge_started)/1e9
            if cb>=done or elapsed>=self.o.get('shared_charge_s',10.) or ca<8.25:
                self.needed_tank='A';self.needed_path=self.path
                self.planned_transfer=True;self.cycles+=1
                self.transition('STOP_SOURCE',now,'BOUNDED_B_CHARGE_RETURN_A_PRIORITY')
        r.update(pumps=self.wanted_pumps,source_enable=self.state in ('RUN','BUILD_COLD','WAIT_COLD_READY'),
            source_valve=0. if self.state=='CLOSE' else 1.,coordinator_state=self.state,
            shared_charge_cycles=self.cycles,shared_reserve_done=self.recharge_done)
        return r


def Coordinator(recharge=None,recharge_at=120.,initial_path='W1',options=None):
    return ContinuityCoordinator(recharge,recharge_at,initial_path,options)

def ProjectProtection(options=None):return ClosureProtection(options)
def SourcePLC(options=None):return ClosurePLC()
