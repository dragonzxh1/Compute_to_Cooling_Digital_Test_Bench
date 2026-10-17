"""Causal single-rack/six-rack loop; injectors never enter control interfaces."""
from dataclasses import asdict
from pathlib import Path
from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.stream_trace import CompletedJournal,read_row
from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import write,read
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import Sensor,measurement_view,IndependentSafety,IntegrationPLC,SilentStuckActuator,actuator_config
from .cases import ROOT,validate
from .plant import RackLoop,check

class Feedback:
    def __init__(self,c):
        self.base=c['initial_speed'];self.kp=c['controller_kp_per_K'];self.ki=c['controller_ki_per_K_s']
        self.reference=c['controller_deltaT_reference_K'];self.integral=0.;self.previous=None
    def request(self,o,now,age):
        m=measurement_view(o,now,age)
        dt=0. if self.previous is None else (now-self.previous)/1e9;self.previous=now
        if m.quality!='VALID':return None
        excess=max(0.,max(o.rack_return_k)-o.supply_k-self.reference)
        self.integral=min(.9-self.base,max(0.,self.integral+self.ki*excess*dt))
        return min(.9,max(.3,self.base+self.kp*excess+self.integral))

def run(c,directory):
    validate(c);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    write(directory/'input.json',c)
    plant=RackLoop(c);profile=read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json')
    actuator=SilentStuckActuator(actuator_config(profile),c['initial_speed'])
    engine=SplitEngine(profile,read(ROOT/'phase5_r5_2_silent_tracking_fault_registration.json')['classifier'])
    sensor=Sensor(c['sensor_delay_ns']);feedback=Feedback(c);policy=IndependentSafety(c);plc=IntegrationPLC(c['initial_speed'])
    journal=CompletedJournal(directory/'m1_completed.zlib');engine._completed=journal
    series=[];physics=[];measurements=[];phases=[];cursor=0;loads=c['load_profile'][0]['rack_it_w']
    dt=c['dt_ns'];primary=c['primary_inlet_k']
    try:
        for now in range(0,c['duration_ns']+dt,dt):
            if now:
                actuator.advance(now-dt,now)
                physics.append(plant.advance(now-dt,now,actuator.actual,loads,primary))
            while cursor+1<len(c['load_profile']) and c['load_profile'][cursor+1]['time_ns']<=now:
                cursor+=1;loads=c['load_profile'][cursor]['rack_it_w']
            active=now>=c['fault_at_ns']
            if active and c['fault']=='STUCK':actuator.silent_hold=True
            primary=c['primary_inlet_k']+(4. if active and c['fault']=='PRIMARY_WARM' else 0.)
            physical=plant.snapshot(now,actuator.actual,actuator.actuator_state_id)
            if now%c['sensor_period_ns']==0 and not(active and c['fault']=='STALE'):
                measurements.append(asdict(sensor.sample(physical,'MISSING' if active and c['fault']=='MISSING' else 'VALID')))
            o=sensor.release(now)
            if o is not None and (now-c['sensor_delay_ns'])%c['control_period_ns']==0:
                m=measurement_view(o,now,c['sensor_max_age_ns']);prior=plc.prior
                pre=engine.pre(m,prior,c['case_id']+':'+str(now));safety=engine.safety(pre,policy.channels(o,now,c['sensor_max_age_ns']))
                envelope=policy.envelope(safety);request=feedback.request(o,now,c['sensor_max_age_ns'])
                output,command=plc.issue(request,envelope,safety,m);engine.accept_plc(output);actuator.command(command,now)
                f=engine.post()
                check(f['PRE']['old_command']==asdict(prior),'PRE_FUTURE_COMMAND_STOP')
                check(Record.make(f['PRE']).digest==pre.digest and Record.make(f['SAFETY']).digest==safety.digest,'IMMUTABLE_BYTES_STOP')
                check(not any(x['kind']=='DENIED_FUTURE_COMMAND_ACCESS' for x in f['access_log']),'FUTURE_ACCESS_STOP')
                phases.append(dict(time_ns=now,PRE=f['PRE'],SAFETY=f['SAFETY'],PLC=f['PLC'],POST=f['POST'],
                    immutable_pre_digest=pre.digest,immutable_safety_digest=safety.digest,envelope=envelope.data(),
                    controller_request=request,actuator_command=asdict(command)))
            series.append(dict(**asdict(physical),rack_it_w=list(loads),commanded_speed=actuator.commanded,
                measured_id=o.measurement_record_id if o else None,safety=phases[-1]['SAFETY']['severity'] if phases else None))
        for row in journal.rows:read_row(journal.path,row)
        write(directory/'m1_completed_index.json',journal.rows)
    finally:journal.close()
    for name,value in [('series',series),('physics',physics),('measurements',measurements),('phases',phases)]:write(directory/(name+'.json'),value)
    result=dict(status='MODEL_EXECUTED_NOT_QUALIFIED',ledger=plant.ledger(),IT_full_load_not_derated=True,
        maximum_inlet_C=max(x['supply_k'] for x in series)-273.15,
        maximum_return_C=max(max(x['rack_return_k']) for x in series)-273.15,
        final_inlet_C=series[-1]['supply_k']-273.15,final_return_C=max(series[-1]['rack_return_k'])-273.15,
        final_flow_m3_h=series[-1]['flow_m3_s']*3600,transactions=len(phases),formal_C3C=False,OEM='CALIBRATION_REQUIRED')
    write(directory/'result.json',result)
    return result
