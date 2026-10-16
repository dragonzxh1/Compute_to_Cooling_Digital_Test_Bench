"""One causal clock; new forcing is private to the plant injector."""
import json
import os
from dataclasses import asdict
from pathlib import Path

from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.stream_trace import CompletedJournal, read_row
from .plant import SixRackPlant, check
from .interfaces import (Sensor, Feedback, IndependentSafety, IntegrationPLC,
    SilentStuckActuator, actuator_config, measurement_view)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()+b'\n'
    with path.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    check(path.read_bytes() == raw, 'EVIDENCE_READBACK_FAILED')


def validate_config(c):
    from math import isfinite
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, float): check(isfinite(x), 'NONFINITE_SCENARIO')
    walk(c)
    check(c['schema'] == 'GB300-M1-SIX-RACK-DEVELOPMENT-v1', 'SCENARIO_SCHEMA')
    check(len(c['rack_ids']) == 6 and len(set(c['rack_ids'])) == 6, 'EXACT_SIX_DISTINCT_RACKS')
    for key in ('duration_ns', 'physics_dt_ns', 'control_period_ns', 'sensor_period_ns', 'sensor_delay_ns'):
        check(type(c[key]) is int and c[key] > 0, 'INTEGER_TIME_REQUIRED:'+key)
    dt = c['physics_dt_ns']
    check(25_000_000 <= dt <= 100_000_000 and c['duration_ns'] <= 120_000_000_000,
          'BOUNDED_INTEGRATION_REQUIRED')
    check(all(c[k] % dt == 0 for k in ('duration_ns','control_period_ns','sensor_period_ns','sensor_delay_ns')),
          'ALIGNED_LOGICAL_CLOCKS_REQUIRED')
    times = [x['time_ns'] for x in c['load_profile']]
    check(times[0] == 0 and times == sorted(set(times)) and all(type(t) is int and t % dt == 0 for t in times),
          'STRICT_LOAD_PROFILE_TIMES')
    check(all(len(x['rack_it_w']) == 6 and all(0 <= p <= 155000 for p in x['rack_it_w'])
              for x in c['load_profile']), 'LOAD_DOMAIN')
    check(c['ua_basis'] == 'EXPLICIT_SENSITIVITY_NOT_VENDOR_DATA' and c['hx_ua_w_k'] > 0,
          'EXPLICIT_UNCALIBRATED_UA_REQUIRED')
    check(0 <= c['liquid_fraction'] <= 1 and 0 < c['series_resistance_fraction'] < 1
          and c['quadratic_shutoff_factor'] > 1, 'PHYSICAL_PARAMETER_DOMAIN')
    check(c['new_integrated_system_qualification'] is False, 'QUALIFICATION_NOT_INHERITED')
    check(c['supply_control_target_k'] < c['supply_derate_k'] < c['supply_hard_k']
          and c['supply_derate_clear_k'] < c['supply_derate_k']
          and c['supply_hard_clear_k'] < c['supply_hard_k'], 'SAFETY_THRESHOLD_HIERARCHY')
    check(c['safety_dwell_ns'] >= 2_000_000_000 and c['safety_recovery_samples'] >= 5
          and c['minimum_branch_flow_kg_s'] > 0 and c['pressure_fault_pa'] > 0
          and c['safety_experiment_mode'] == 'PERFORMANCE_REQUEST_ONLY_NO_IT_MUTATION',
          'MANDATORY_SAFETY_CONFIGURATION')


def run(c, case, directory):
    validate_config(c)
    check(case in ('LOAD_STEP', 'PUMP_STUCK'), 'UNKNOWN_SCENARIO')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write(directory/'input.json', dict(case=case, config=c))
    profile = read(ROOT/'phase5_r5_2_2_fixture_tracking_profile.json')
    classifier = read(ROOT/'phase5_r5_2_silent_tracking_fault_registration.json')['classifier']
    plant = SixRackPlant(c)
    actuator = SilentStuckActuator(actuator_config(profile), c['initial_speed'])
    sensor, feedback, independent, plc = Sensor(c['sensor_delay_ns']), Feedback(c), IndependentSafety(c), IntegrationPLC(c['initial_speed'])
    engine = SplitEngine(profile, classifier)
    journal = CompletedJournal(directory/'m1_completed.zlib')
    engine._completed = journal  # existing immutable-record storage interface
    rows, phases, physics, measurements, transitions = [], [], [], [], []
    prior_state = None
    dt, until = c['physics_dt_ns'], c['duration_ns']
    forcing_cursor = 0
    loads = c['load_profile'][0]['rack_it_w']
    sample_ids = set()
    last_physics = None
    trace = (directory/'events.jsonl').open('xb')
    try:
        for now in range(0, until+dt, dt):
            order = []
            if now:
                # Commands created at now are not visible to this old interval.
                actuator.advance(now-dt, now)
                last_physics = plant.advance(now-dt, now, actuator.actual, loads)
                physics.append(last_physics)
                order.append('PHYSICS_OLD_INTERVAL')
            # Injector alone owns the current forcing; never passed to control.
            while forcing_cursor+1 < len(c['load_profile']) and c['load_profile'][forcing_cursor+1]['time_ns'] <= now:
                forcing_cursor += 1
                loads = c['load_profile'][forcing_cursor]['rack_it_w']
            if case == 'PUMP_STUCK' and now >= c['silent_stuck_at_ns']:
                actuator.silent_hold = True
            snapshot = plant.snapshot(now, actuator.actual, actuator.actuator_state_id)
            if now % c['sensor_period_ns'] == 0:
                measurements.append(asdict(sensor.sample(snapshot)))
            observation = sensor.release(now)
            order.append('RELEASE_AVAILABLE_ONLY')
            if observation is not None and (now-c['sensor_delay_ns']) % c['control_period_ns'] == 0:
                m = measurement_view(observation, now, c['sensor_max_age_ns'])
                check(m.measurement_record_id not in sample_ids, 'DUPLICATE_CREDIT_IN_E2E')
                sample_ids.add(m.measurement_record_id)
                txid = case+':'+str(now)
                old = plc.prior
                pre = engine.pre(m, old, txid)
                order.append('PRE_OLD_COMMAND')
                safety = engine.safety(pre, independent.channels(observation, now, c['sensor_max_age_ns']))
                envelope = independent.envelope(safety)
                order.append('SAFETY_COMMIT')
                request = feedback.request(observation, now, c['sensor_max_age_ns'])
                output, command = plc.issue(request, envelope, safety, m)
                order.append('PLC_ISSUE')
                engine.accept_plc(output)
                actuator.command(command, now)
                frame = engine.post()
                order.append('POST_COMMIT')
                check(frame['immutable_pre_digest'] == pre.digest and frame['immutable_safety_digest'] == safety.digest,
                      'IMMUTABLE_EVIDENCE_CHANGED')
                check(Record.make(frame['PRE']).digest == pre.digest and Record.make(frame['SAFETY']).digest == safety.digest,
                      'PHASE_BYTES_CHANGED')
                check(frame['PRE']['old_command'] == asdict(old), 'PRE_FUTURE_COMMAND_LEAK')
                check(not any(e['kind']=='DENIED_FUTURE_COMMAND_ACCESS' for e in frame['access_log']), 'UNEXPECTED_FORBIDDEN_ACCESS')
                state = frame['PRE']['state']
                if state != prior_state:
                    transitions.append(dict(time_ns=now, state=state, measurement_id=m.measurement_record_id))
                    prior_state = state
                phases.append(dict(time_ns=now, PRE=frame['PRE'], SAFETY=frame['SAFETY'],
                    envelope=envelope.data(), controller_request=request, PLC=frame['PLC'],
                    actuator_command=asdict(command), POST=frame['POST'],
                    immutable_pre_digest=pre.digest, immutable_safety_digest=safety.digest,
                    command_selection_scope='NEW_INTEGRATION_CURRENT_FEEDBACK_NOT_QUALIFIED_FIXTURE_DOMAIN'))
                if len(phases) % 100 == 0:
                    print(json.dumps(dict(event='CASE_PROGRESS', case=case, time_ns=now, tracking=state)), flush=True)
            rows.append(dict(**asdict(snapshot), rack_it_w=list(loads), commanded_speed=actuator.commanded,
                measured_speed=observation.pump_speed if observation else None,
                measurement_record_id=observation.measurement_record_id if observation else None,
                sample_ns=observation.sample_ns if observation else None,
                release_ns=observation.available_ns if observation else None,
                tracking=prior_state, safety=phases[-1]['SAFETY']['severity'] if phases else 'BOOTSTRAP_NO_CONTROL',
                controller_request=phases[-1]['controller_request'] if phases else None))
            trace.write(json.dumps(dict(time_ns=now, order=order), separators=(',', ':')).encode()+b'\n')
        trace.flush(); os.fsync(trace.fileno())
        # Read all completed POST transactions back, not just the last result.
        for entry in journal.rows:
            read_row(journal.path, entry)
        write(directory/'m1_completed_index.json', journal.rows)
    finally:
        trace.close()
        journal.close()
    write(directory/'series.json', rows)
    write(directory/'physics_intervals.json', physics)
    write(directory/'measurements.json', measurements)
    write(directory/'phases.json', phases)
    ledger = plant.ledger()
    state_times = {s:next((x['time_ns'] for x in transitions if x['state']==s), None) for s in
        ('HANDOFF_PENDING','TRACKING_PROGRESS','TRACKING_FAULT_SUSPECTED','TRACKING_FAULT_CONFIRMED')}
    result = dict(case=case, status='INTEGRATION_MVP_INCOMPLETE', ledger=ledger,
        transitions=transitions, first_state_times_ns=state_times,
        final_supply_c=rows[-1]['supply_k']-273.15, final_return_c=rows[-1]['return_k']-273.15,
        final_flow_m3_s=rows[-1]['flow_m3_s'], final_dp_pa=rows[-1]['dp_pa'],
        final_actual_speed=rows[-1]['actual_speed'], final_command=rows[-1]['commanded_speed'],
        max_supply_c=max(r['supply_k'] for r in rows)-273.15,
        max_rack_return_c=max(max(r['rack_return_k']) for r in rows)-273.15,
        transaction_count=len(phases), unique_measurements=len(sample_ids),
        phantom_progress_forced=False, fault_bit_used=False, new_integrated_system_qualification=False,
        hardware='CALIBRATION_REQUIRED')
    checks = dict(energy=ledger['energy_closed'], heat_sources=ledger['heat_source_closed'],
        pump_energy=ledger['pump_energy_closed'], transactions=len(phases)==len(journal.rows)==len(sample_ids),
        load_step_affects_heat=any(p['liquid_heat_w'] != physics[0]['liquid_heat_w'] for p in physics),
        commands_observation_bound=all(x['PLC']['time_ns'] >= x['PRE']['measurement']['release_ns'] for x in phases),
        thermal_response=max(r['return_k'] for r in rows)-rows[0]['return_k'] > 0,
        mass=ledger['max_mass_residual_kg_s'] <= 1e-9+1e-8*c['density_kg_m3']*c['design_secondary_flow_m3_s'])
    confirmed = state_times['TRACKING_FAULT_CONFIRMED']
    if case == 'LOAD_STEP':
        checks.update(no_false_confirmation=confirmed is None,
            feedback_changes_command=max(x['PLC']['command'] for x in phases)-c['initial_speed'] >= .15,
            hydraulic_response=rows[-1]['flow_m3_s']>rows[0]['flow_m3_s'])
    else:
        stuck = [r for r in rows if r['time_ns']>=c['silent_stuck_at_ns']]
        checks.update(stuck_physics=len({r['actual_speed'] for r in stuck})==1,
            stuck_flow=len({r['flow_m3_s'] for r in stuck})==1,
            new_issued_demand=max(x['PLC']['command'] for x in phases)-stuck[0]['actual_speed']>=.15,
            eligible_confirmation=confirmed is not None,
            safety_fault_latched=confirmed is not None and all(x['SAFETY']['severity']=='FAULT' for x in phases if x['time_ns']>=confirmed),
            no_explicit_equipment_fault=all(not r['pump_fault'] and r['pump_ready'] for r in measurements))
    result['checks'] = checks
    result['status'] = 'PASS' if all(checks.values()) else 'INTEGRATION_MVP_INCOMPLETE'
    write(directory/'result.json', result)
    return result
