"""One/six rack physical failover; qualified solver and M1 are imported unchanged."""
from dataclasses import asdict,replace
from math import fsum
from pathlib import Path
from v0_2.tests.tools.memphis_single_rack_v1.cases import config,ROOT
from v0_2.tests.tools.memphis_single_rack_v1.plant import RackLoop,p,check
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import Sensor,SilentStuckActuator,IndependentSafety,IntegrationPLC,measurement_view,actuator_config
from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.stream_trace import CompletedJournal,read_row
from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import read,write
from v0_2.tests.tools.memphis_project_v2.coordination import record


def unit_config(spec):
    c=config(dict(id=spec['id'],rack_count=spec.get('racks',6),boundary='NORMAL' if spec.get('normal') else 'HOT',load_step=spec.get('step',False),unbalanced=spec.get('unbalanced',False),inventory_scale=spec.get('inventory',1)))
    c['hx_ua_w_k']=spec.get('ua',220000)*c['rack_count']/6
    c['dt_ns']=round(spec.get('dt',.1)*1e9)
    c['fault']=spec.get('fault');c['fault_at_ns']=10_000_000_000
    if spec.get('loads'):c['load_profile'][0]['rack_it_w']=spec['loads']
    return c


class Paths:
    """Two isolated CDU paths; each has two isolated pump branches.

    Actual travel is rate-limited; hydraulic resistance follows valve opening.
    No simultaneous pump/CDU parallel sharing, which would need another curve.
    """
    def __init__(self,c,spec):
        self.loop=RackLoop(c);self.base_graph=self.loop.graph;self.base_curve=self.loop.curve
        self.c=c;self.spec=spec;self.cdu=0;self.pump=0;self.state='RUN';self.destination=None
        self.opening=1.;self.backup_speed=0.;self.backup_command=0.;self.low_since=None
        self.backup_since=None;self.failed_cdu=False;self.restricted=False;self.second=False
        self.events=[];self.receipt=None

    def inject(self,seconds):
        # Fault schedule is plant-only, never provided to supervisor or M1.
        if seconds>=10 and self.spec.get('fault')=='CDU_LOSS':self.failed_cdu=True
        if seconds>=10 and self.spec.get('fault')=='RESTRICTION':self.restricted=True
        if seconds>=80 and self.spec.get('second_failure'):self.second=True

    def configure(self,main_speed):
        healthy=not(self.cdu==0 and self.failed_cdu)
        speed=main_speed if (self.cdu,self.pump)==(0,0) else self.backup_speed
        if not healthy or self.opening<=1e-9 or self.second:speed=0.
        factor=1/max(self.opening,.001)**2
        if self.restricted and self.cdu==0:factor*=4
        def change(e):return replace(e,coefficient=p(e.edge_id+'.actualValve',e.coefficient.value*factor,'Pa/(m3/s)^2'))
        self.loop.graph=replace(self.base_graph,supply_series=tuple(change(e) for e in self.base_graph.supply_series),return_series=tuple(change(e) for e in self.base_graph.return_series))
        self.loop.curve=replace(self.base_curve,shutoff_head_pa=p('actual.curve.H0',self.base_curve.shutoff_head_pa.value*self.spec.get('pump_factor',1),'Pa'))
        return speed,factor

    def advance(self,dt,now):
        travel=self.spec.get('valve_s',5.)
        if self.state=='CLOSE':
            self.opening=max(0.,self.opening-dt/travel)
            if self.opening<=1e-9:
                self.opening=0.;self.cdu,self.pump=self.destination
                self.state='OPEN';self.events.append(dict(event='OLD_PATH_ISOLATED',time_ns=now,cdu=self.cdu,pump=self.pump))
        elif self.state=='OPEN':
            self.opening=min(1.,self.opening+dt/travel)
            if self.opening>=1-1e-9:self.opening=1.;self.state='RUN'
        if self.backup_since is not None and now-self.backup_since>=200_000_000:
            target=0. if self.spec.get('backup_fail') or self.second else self.backup_command
            self.backup_speed+=max(-.2*dt,min(.2*dt,target-self.backup_speed))

    def supervise(self,obs,backup_obs,now,safety,prior_command):
        # Only released sensor values enter this method. No spec fault flags.
        check(obs.sample_ns<=obs.available_ns<=now,'UNRELEASED_MAIN_OBSERVATION')
        valid=obs.quality=='VALID' and now-obs.sample_ns<=1_000_000_000
        low=valid and obs.flow_m3_s<.75*self.c['design_flow_m3_s'] and prior_command>=.85
        high=valid and obs.supply_k>=317.65
        if low and self.low_since is None:self.low_since=now
        if not low:self.low_since=None
        codes=list(safety.data()['reason_codes'])
        if self.low_since is not None and now-self.low_since>=1_000_000_000:codes.append('FAST_LOW_FLOW')
        request=None
        if self.backup_since is None and valid and ('FAST_LOW_FLOW' in codes or high):
            # A following speed with low flow requests an alternate CDU path;
            # lagging speed requests the other pump within the operating CDU.
            request=(0,1) if obs.pump_speed is not None and prior_command-obs.pump_speed>=.15 else (1,0)
        permission=record(dict(time_ns=now,measurement_id=obs.measurement_record_id,safety_digest=safety.digest,
            codes=codes,backup_allowed=valid and obs.dp_pa<self.c['pressure_fault_pa'],load_cap_applied=False))
        if request is not None and permission['data']['backup_allowed']:
            self.receipt=record(dict(producer='MEMPHIS_SIMULATED_BACKUP_PLC',time_ns=now,measurement_id=obs.measurement_record_id,
                permission_sha256=permission['sha256'],destination=list(request),speed=.9,scope='OFFLINE_SIMULATED_ISSUE'))
            from .validation import verify_receipt
            verify_receipt(self.receipt,permission,obs.measurement_record_id,now)
            self.destination=request;self.state='START_BACKUP';self.backup_command=.9;self.backup_since=now
            self.events.append(dict(event='BACKUP_REQUESTED',time_ns=now,cdu=request[0],pump=request[1],receipt=self.receipt['sha256']))
        if self.state=='START_BACKUP' and backup_obs is not None:
            check(backup_obs['sample_ns']<=backup_obs['release_ns']<=now,'BACKUP_FUTURE_OBSERVATION')
            if now-backup_obs['sample_ns']<=1_000_000_000 and backup_obs['speed']>=.85:
                self.state='CLOSE';self.events.append(dict(event='BACKUP_STARTED',time_ns=now,measurement_id=backup_obs['id']))
        return permission,self.receipt


def run(spec,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);c=unit_config(spec)
    write(directory/'input.json',dict(config=c,spec=spec))
    paths=Paths(c,spec);profile=read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json')
    actuator=SilentStuckActuator(actuator_config(profile),c['initial_speed'])
    engine=SplitEngine(profile,read(ROOT/'phase5_r5_2_silent_tracking_fault_registration.json')['classifier'])
    plc=IntegrationPLC(c['initial_speed']);sensor=Sensor(c['sensor_delay_ns']);supervisor=IndependentSafety(c)
    journal=CompletedJournal(directory/'m1_completed.zlib');engine._completed=journal
    series=[];physics=[];observations=[];phases=[];backup_samples=[];pending_backup=[];backup_obs=None
    last=None;integral=0.;loads=c['load_profile'][0]['rack_it_w']
    try:
        for now in range(0,c['duration_ns']+c['dt_ns'],c['dt_ns']):
            if now:
                actuator.advance(now-c['dt_ns'],now);paths.advance(c['dt_ns']/1e9,now)
                effective,factor=paths.configure(actuator.actual)
                s=paths.loop.advance(now-c['dt_ns'],now,effective,loads,c['primary_inlet_k'])
                s.update(effective_speed=effective,common_factor=factor,cdu=paths.cdu,pump=paths.pump,opening=paths.opening,
                    ua_w_k=c['hx_ua_w_k'],pump_factor=spec.get('pump_factor',1))
                physics.append(s)
            if now==10_000_000_000 and spec.get('step'):loads=[155000]*c['rack_count']
            paths.inject(now/1e9)
            if now>=10_000_000_000 and spec.get('fault')=='STUCK':actuator.silent_hold=True
            effective,factor=paths.configure(actuator.actual)
            physical=paths.loop.snapshot(now,effective,'path:'+str(now))
            # Tachometer for original duty pump remains original duty pump after
            # transfer. M1 latch cannot be cleared by relabeling backup speed.
            measured=replace(physical,actual_speed=actuator.actual,actuator_state_id=actuator.actuator_state_id)
            if now%c['sensor_period_ns']==0:
                b=dict(id='backup-sensor:'+str(now),sample_ns=now,release_ns=now+c['sensor_delay_ns'],speed=paths.backup_speed)
                pending_backup.append(b);backup_samples.append(b)
                if not(now>=10_000_000_000 and spec.get('fault')=='SENSOR_DELAY'):
                    quality='MISSING' if now>=10_000_000_000 and spec.get('fault')=='SENSOR_LOSS' else 'VALID'
                    observations.append(asdict(sensor.sample(measured,quality)))
            o=sensor.release(now)
            arrived=[b for b in pending_backup if b['release_ns']<=now]
            if arrived:backup_obs=max(arrived,key=lambda b:b['sample_ns'])
            pending_backup=[b for b in pending_backup if b['release_ns']>now]
            if o is not None and (now-c['sensor_delay_ns'])%c['control_period_ns']==0:
                m=measurement_view(o,now,c['sensor_max_age_ns']);prior=plc.prior
                pre=engine.pre(m,prior,spec['id']+':'+str(now));safety=engine.safety(pre,supervisor.channels(o,now,c['sensor_max_age_ns']))
                envelope=supervisor.envelope(safety)
                delta=0 if last is None else (now-last)/1e9;last=now
                if m.quality=='VALID':
                    excess=max(0,max(o.rack_return_k)-o.supply_k-8)
                    integral=min(.9-c['initial_speed'],max(0,integral+.02*excess*delta))
                    request=min(.9,max(.3,c['initial_speed']+.08*excess+integral))
                else:request=None
                output,command=plc.issue(request,envelope,safety,m);engine.accept_plc(output);actuator.command(command,now)
                f=engine.post();permission,backup=paths.supervise(o,backup_obs,now,safety,prior.value)
                check(f['PRE']['old_command']==asdict(prior),'PRE_FUTURE_COMMAND')
                check(Record.make(f['PRE']).digest==pre.digest and Record.make(f['SAFETY']).digest==safety.digest,'IMMUTABLE_PHASES')
                phases.append(dict(time_ns=now,**{k:f[k] for k in ('PRE','SAFETY','PLC','POST')},immutable_pre_digest=pre.digest,
                    immutable_safety_digest=safety.digest,envelope=envelope.data(),actuator_command=asdict(command),
                    fast_permission=permission,backup_PLC=backup,backup_measurement=backup_obs,controller_request=request))
            series.append(dict(**asdict(physical),main_speed=actuator.actual,main_command=actuator.commanded,
                main_actuator_state_id=actuator.actuator_state_id,
                backup_speed=paths.backup_speed,backup_command=paths.backup_command,active_cdu=paths.cdu,active_pump=paths.pump,
                valve_opening=paths.opening,selector_state=paths.state,rack_it_w=list(loads),
                supply_valve=paths.opening,return_valve=paths.opening,provenance='ENGINEERING_ASSUMPTION'))
            if now and now%30_000_000_000==0:print('UNIT_PROGRESS '+spec['id']+' '+str(now/1e9),flush=True)
        for row in journal.rows:read_row(journal.path,row)
        write(directory/'m1_completed_index.json',journal.rows)
    finally:journal.close()
    for name,value in [('series',series),('physics',physics),('measurements',observations),('backup_measurements',backup_samples),('phases',phases),('events',paths.events)]:write(directory/(name+'.json'),value)
    return dict(case_id=spec['id'],ledger=paths.loop.ledger(),execution='COMPLETED',equipment='NOT_VERIFIED')
