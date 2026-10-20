"""One causal clock, project physical state private, source/secondary PLC lanes explicit."""
from dataclasses import asdict,replace
from math import fsum
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import (
    Sensor,SilentStuckActuator,IndependentSafety,IntegrationPLC,measurement_view,actuator_config)
from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.stream_trace import CompletedJournal,read_row
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.common import HERE,REG,read,write,check,CV,rounding_bound
from v0_2.tests.tools.memphis_failure_closure_v1.group_model.plant import ProjectUnit
from .plant import SourcePlant
from .coordination import Coordinator,ProjectProtection,SourcePLC,record,control_options
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.streaming import StreamArray

ROOT=HERE.parents[4]

class ProjectSensor(Sensor):
    def __init__(self,unit,options):
        fast=options.get('use_fast_sensor_channel',False) and not options.get('fast_channel_failed',False)
        super().__init__(round((options.get('fast_sensor_delay_s',.1) if fast else options.get('sensor_delay_s',.1))*1e9));self.unit=unit+(':FAST_INDEPENDENT' if fast else '');self.bias=options.get('sensor_bias_K',0.)
    def sample(self,s,quality='VALID'):
        o=super().sample(s,quality)
        o=replace(o,measurement_record_id=self.unit+':'+o.measurement_record_id,
            supply_k=o.supply_k+self.bias if o.supply_k is not None else None,
            return_k=o.return_k+self.bias if o.return_k is not None else None)
        self.pending[-1]=o;return o

def run(spec,directory):
    check(spec['ua_w_k'] is not None,'INCOMPLETE_MISSING_EQUIPMENT_UA')
    directory.mkdir(parents=True,exist_ok=False)
    write(directory/'input.json',dict(spec=spec,registration=REG))
    group=spec['scope']=='GROUP18';count=3 if group else 1
    factors=REG['assumptions']['branch_K_factors_unbalanced' if spec.get('unbalanced') else 'branch_K_factors_balanced']
    units=[ProjectUnit(spec['ua_w_k'],factors,spec) for _ in range(count)]
    profile=read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json')
    classifier=read(ROOT/'phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
    sensors=[ProjectSensor('U'+str(i),spec) for i in range(count)]
    actuators=[SilentStuckActuator(actuator_config(profile),spec.get('initial_speed',.9)) for _ in units]
    plcs=[IntegrationPLC(a.actual) for a in actuators];engines=[SplitEngine(profile,classifier) for _ in units]
    journals=[];records=[];measurements=[];series=[];physics=StreamArray(directory/'physics.json');source_frames=[];source_observations=[]
    c=read(ROOT/'v0_2/tests/tools/gb300_m1_closed_loop_v1/scenario.json')
    c.update(supply_control_target_k=317.15,supply_derate_k=317.65,supply_hard_k=318.15)
    supervisors=[IndependentSafety(c) for _ in units]
    for i,e in enumerate(engines):
        j=CompletedJournal(directory/('m1_U'+str(i)+'.zlib'));e._completed=j;journals.append(j)
    source=SourcePlant(spec) if group else None
    options=control_options(spec) if spec.get('extensions') else spec
    coordinator=Coordinator(spec.get('recharge'),spec.get('recharge_at_s',120),spec.get('initial_path','W1'),options)
    protection=ProjectProtection(options);source_plc=SourcePLC(options);pending=[];latest_source=None
    initial=dict(source_tank='A',source_path=spec.get('initial_path','W1'),source_enable=True,source_valve=1.,pumps=3,
        recharge_enable=False,fan=.82308,load_tank='A',coordinator_state='INITIAL_CONDITION',permission='NONE',observation_id='NONE')
    issued=record(dict(producer='INITIAL_CONDITION_NO_PLC_ISSUE_PROOF',request=initial))
    source_safety=None;last_source_id=None;last_source_evaluation_ns=None
    dt_ns=round(spec['dt_s']*1e9);duration=round(spec['seconds']*1e9)
    period=5_000_000_000 if group else 1_000_000_000
    initial_energy=fsum(u.energy() for u in units)+(source.energy() if group else 0.)
    hx_out_j=0.;it_j=liquid_j=pump_j=reject_j=gained_j=0.;max_global_residual=0.;last_record=None
    if spec.get('extensions'):
        write(directory/'component_prelude.json',dict(ledger=source.prelude,history=source.pre_history))
    try:
        for now in range(0,duration+dt_ns,dt_ns):
            if now:
                for a in actuators:a.advance(now-dt_ns,now)
                if group:
                    last_record=source.advance(now-dt_ns,now,units,[a.actual for a in actuators],issued)
                    physics.append(last_record)
                    electric=last_record['secondary_pump_electrical_w']+last_record['primary_pump_electrical_w']
                    reject=last_record['rejected_w'];max_global_residual=max(max_global_residual,abs(last_record['global_residual_j']))
                else:
                    r=units[0].advance_project(now-dt_ns,now,actuators[0].actual,314.15,110/3600)
                    last_record=dict(start_ns=now-dt_ns,end_ns=now,unit_records=[r],primary_inlet_c=41.,
                        load_flow_m3_h=110.,source_flow_m3_h=None,primary_return_c=r['primary_outlet_k']-273.15)
                    physics.append(last_record);electric=r['pump_electrical_w'];reject=r['hx_w'];hx_out_j+=reject*spec['dt_s']
                it_j+=count*930000*spec['dt_s'];liquid_j+=count*883500*spec['dt_s']
                pump_j+=electric*spec['dt_s'];reject_j+=reject*spec['dt_s']
                gained_j+=last_record.get('ambient_gain_w',0.)*spec['dt_s']
            # Plant-only injector, after old interval. Not a controller argument.
            if spec.get('stuck'):actuators[0].silent_hold=True
            if group:
                source.inject(now/1e9)
                sampling_lost=spec.get('extensions') and now/1e9>=spec.get('source_sensor_loss_at_s',float('inf'))
                if now%200000000==0 and not sampling_lost:
                    obs=source.observation(now,units);pending.append(obs);source_observations.append(asdict(obs))
                arrived=[o for o in pending if o.release_ns<=now]
                if arrived:latest_source=max(arrived,key=lambda o:o.sample_ns)
                pending=[o for o in pending if o.release_ns>now]
                watchdog_due=spec.get('extensions') and last_source_evaluation_ns is not None and now-last_source_evaluation_ns>=200000000
                if latest_source is not None and (latest_source.record_id!=last_source_id or watchdog_due):
                    source_safety=protection.evaluate(latest_source,now)
                    request=coordinator.request(latest_source,source_safety,now)
                    issued=source_plc.issue(request,source_safety,latest_source,now)
                    source_frames.append(dict(time_ns=now,measurement=asdict(latest_source),safety=source_safety,
                        request=request,PLC=issued,actual_primary_inlet_c=source.last_primary_inlet-273.15))
                    last_source_id=latest_source.record_id
                    last_source_evaluation_ns=now
            physical=[]
            for i,(u,a,sensor,engine,plc,supervisor) in enumerate(zip(units,actuators,sensors,engines,plcs,supervisors)):
                s=u.snapshot(now,a.actual,a.actuator_state_id)
                physical.append(dict(**asdict(s),inlet_k=list(u.temperatures[1:7]),
                    supply_header_k=u.temperatures[0],secondary_stored_j=u.energy(),
                    edge_drops_pa=dict(u.latest_hydraulic.edge_drops_pa),node_pressure_relative_pa=dict(u.latest_hydraulic.pressures_pa),
                    command=a.commanded))
                if now%200000000==0:measurements.append(dict(unit=i,**asdict(sensor.sample(s))))
                obs=sensor.release(now)
                if obs is not None and (now-100000000)%period==0:
                    m=measurement_view(obs,now,1000000000);old=plc.prior
                    pre=engine.pre(m,old,spec['id']+':U'+str(i)+':'+str(now))
                    channels=supervisor.channels(obs,now,1000000000)
                    if group and source_safety and source_safety['data']['codes']:
                        channels += [dict(code=x,severity='FAULT') for x in source_safety['data']['codes']]
                    safety=engine.safety(pre,channels);envelope=supervisor.envelope(safety)
                    # Only an arrived flow observation affects the secondary
                    # pump request. Target is a design requirement, not actual flow.
                    request=min(.9,max(.3,old.value+.02*((68.37/3600-obs.flow_m3_s)*3600))) if m.quality=='VALID' else None
                    output,command=plc.issue(request,envelope,safety,m)
                    engine.accept_plc(output);a.command(command,now);frame=engine.post()
                    check(frame['PRE']['old_command']==asdict(old),'PRE_FUTURE_COMMAND')
                    check(Record.make(frame['PRE']).digest==pre.digest and Record.make(frame['SAFETY']).digest==safety.digest,'IMMUTABLE_PHASE_DRIFT')
                    check(not any(x['kind']=='DENIED_FUTURE_COMMAND_ACCESS' for x in frame['access_log']),'FUTURE_ACCESS')
                    records.append(dict(unit=i,time_ns=now,PRE=frame['PRE'],SAFETY=frame['SAFETY'],PLC=frame['PLC'],POST=frame['POST'],
                        envelope=envelope.data(),actuator_command=asdict(command),controller_request=request,immutable_pre_digest=pre.digest,immutable_safety_digest=safety.digest))
            if now%1_000_000_000==0 or now==duration:
                series.append(dict(time_ns=now,units=physical,primary_inlet_c=41. if not group else source.last_primary_inlet-273.15,
                    tank_A_k=None if not group else list(source.tanks['A'].t),tank_B_k=None if not group else list(source.tanks['B'].t),
                    source_pipe_k=None if not group else {k:list(p.t) for k,p in source.pipes.items()},
                    source_supply_valve=None if not group else source.source_supply_valve,
                    source_return_valve=None if not group else source.source_return_valve,
                    load_supply_valve=None if not group else source.load_supply_valve,
                    load_return_valve=None if not group else source.load_return_valve,
                    source_selector=None if not group else source.source_tank,
                    source_path=None if not group else source.source_path,
                    source_actual_speed=None if not group else source.speed,
                    source_state=coordinator.state if group else 'FIXED_PRIMARY_BOUNDARY_FOR_UNIT_ONLY',
                    cold_A_m3=None if not group else source.tanks['A'].cold_volume(),cold_B_m3=None if not group else source.tanks['B'].cold_volume(),
                    source_flow_m3_h=None if not group else source.last_source_q*3600,
                    actual_load_selector=None if not group else source.load_tank,actual_load_valve=None if not group else source.load_valve,
                    stored_j=fsum(u.energy() for u in units)+(source.energy() if group else 0.)))
                if spec.get('extensions'):series[-1]['source_pipe_volumes_m3']={k:v.volume for k,v in source.pipes.items()}
                if hasattr(source,'neutral_k'):
                    series[-1].update(neutral_buffer_k=source.neutral_k,neutral_buffer_m3=source.neutral_volume)
            if now and now%60_000_000_000==0:print('MEMPHIS_PROGRESS '+spec['id']+' '+str(now/1e9)+'s',flush=True)
        for i,j in enumerate(journals):
            for row in j.rows:read_row(j.path,row)
            write(directory/('m1_U'+str(i)+'_index.json'),j.rows)
    finally:
        for j in journals:j.close()
        physics.close()
    final_energy=fsum(u.energy() for u in units)+(source.energy() if group else 0.)
    residual=final_energy-initial_energy-liquid_j-pump_j+reject_j-gained_j
    ops=4096*(len(physics)+1);u_round=2**-53;gamma=ops*u_round/(1-ops*u_round)
    bound=gamma*(abs(initial_energy)+abs(final_energy)+liquid_j+pump_j+reject_j)
    check(abs(residual)<=bound,'INDEPENDENT_GLOBAL_LEDGER')
    output=dict(spec_id=spec['id'],status='MODEL_EXECUTION_COMPLETED',scope='CONDITIONAL_MODEL_NOT_OEM_QUALIFICATION',
        units=count,rack_count=count*6,IT_w=count*930000,IT_liquid_w=count*883500,
        primary_boundary='DYNAMIC_TANK_PUMP_SOURCE_COUPLED' if group else '41C110M3H_UNIT_DESIGN_BOUNDARY_ONLY',
        source_variant=source.variant if group else None,source_variant_approval='UNSELECTED_CONDITIONAL_ALTERNATIVE',
        energy=dict(initial_j=initial_energy,final_j=final_energy,it_j=it_j,liquid_j=liquid_j,air_j=it_j-liquid_j,
            all_pump_electrical_to_liquid_j=pump_j,rejected_or_exported_j=reject_j,environment_gain_j=gained_j,residual_j=residual,roundoff_bound_j=bound,
            heat_source_ownership='IT_SPLIT_ONCE; EACH_PUMP_ELECTRIC_ONCE; HX_CANCELS_GROUP; NO_EXTRA10.86_OR33.06KW'),
        max_global_step_residual_j=max_global_residual,max_unit_local_residual_j=max(u.max_local_energy_residual_j for u in units),
        maximum_inlet_c=max(max(u['inlet_k'])-273.15 for row in series for u in row['units']),
        maximum_rack_return_c=max(max(u['rack_return_k'])-273.15 for row in series for u in row['units']),
        minimum_branch_flow_m3_h=min(min(u['branch_flows_m3_s'])*3600 for row in series for u in row['units']),
        final_units=series[-1]['units'],transaction_count=len(records),source_transaction_count=len(source_frames),
        source_timeline=coordinator.events,source_returned_at_ns=coordinator.returned_at,
        requested_recharge_screen_met=coordinator.recharge_done if group else None,
        hardware='CALIBRATION_REQUIRED',formal_C3_C='NOT_RUN',production=False,phase6=False)
    write(directory/'series.json',series);write(directory/'phases.json',records)
    write(directory/'measurements.json',measurements);write(directory/'source_phases.json',source_frames)
    write(directory/'source_observations.json',source_observations);write(directory/'result.json',output)
    return output
