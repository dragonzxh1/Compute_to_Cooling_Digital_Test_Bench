"""Integration-owned views/PLC adapter. The qualified M1 engine is unmodified."""
from dataclasses import dataclass, asdict
from math import isfinite

from v0_2.actuators.pump import PumpActuator, PumpActuatorConfig
from v0_2.control.inner_loop import ActuatorCommand
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.m1_engine_v3.scheduler import MeasurementView, SimulatedPLC
from .plant import check


@dataclass(frozen=True, slots=True)
class Observation:
    sample_ns: int
    available_ns: int
    measurement_record_id: str
    quality: str
    pump_speed: float | None
    supply_k: float | None
    return_k: float | None
    rack_return_k: tuple
    flow_m3_s: float | None
    branch_flows_m3_s: tuple
    dp_pa: float | None
    pump_ready: bool
    pump_fault: bool
    source_ids: tuple


class Sensor:
    """Only this producer can read a PhysicalSnapshot. No truth fallback."""
    def __init__(self, delay_ns):
        self.delay_ns = delay_ns
        self.pending = []
        self.latest = None

    def sample(self, s, quality='VALID'):
        valid = quality == 'VALID'
        r = Observation(s.time_ns, s.time_ns+self.delay_ns, 'measurement:'+str(s.time_ns), quality,
            s.actual_speed if valid else None, s.supply_k if valid else None,
            s.return_k if valid else None, s.rack_return_k if valid else (),
            s.flow_m3_s if valid else None, s.branch_flows_m3_s if valid else (), s.dp_pa if valid else None,
            True, False, (s.actuator_state_id, s.hydraulic_solution_id))
        self.pending.append(r)
        return r

    def release(self, now):
        due = [r for r in self.pending if r.available_ns <= now]
        if due:
            self.latest = max(due, key=lambda r:r.sample_ns)
        self.pending = [r for r in self.pending if r.available_ns > now]
        return self.latest


def measurement_view(o, now, max_age):
    check(o is not None and o.available_ns <= now and o.sample_ns <= o.available_ns,
          'UNRELEASED_OR_FUTURE_MEASUREMENT')
    numbers = (o.pump_speed, o.supply_k, o.return_k, o.flow_m3_s, o.dp_pa, *o.rack_return_k)
    check(all(x is None or isfinite(x) for x in numbers), 'NONFINITE_OBSERVATION')
    valid = o.quality == 'VALID' and now-o.sample_ns <= max_age
    return MeasurementView(now, o.pump_speed if valid else None, o.sample_ns, o.available_ns,
        'VALID' if valid else 'MISSING', o.measurement_record_id)


class Feedback:
    """Return-temperature proportional request; only an arrived observation enters.

    This is a sensitivity controller, NOT a vendor PLC tuning or supply limit.
    It deliberately has no plant, injector, scenario or future-load reference.
    """
    def __init__(self, c):
        self.base = c['initial_speed']
        self.target = c['return_target_k']
        self.gain = c['feedback_gain_fraction_per_k']

    def request(self, observation, now, max_age):
        view = measurement_view(observation, now, max_age)
        if view.quality != 'VALID':
            return None
        return min(.9, max(.3, self.base+self.gain*(max(observation.rack_return_k)-self.target)))


class IndependentSafety:
    """No command-speed mismatch timer. M1 alone owns tracking confirmation.

    Independent limits apply to measured LIQUID supply, not GPU die temperature.
    FAULT latch lives in the unchanged M1 Safety reducer; no automatic reset.
    """
    def __init__(self, c):
        self.limit = c['supply_operating_limit_k']
        self.pressure = c['pressure_fault_pa']
        self.fallback = c['fault_speed']
        self.c = c
        self.derate = self.hard = False
        self.clear_start = None
        self.clear_ids = set()
        self.entered = 0

    def channels(self, o, now, max_age):
        m = measurement_view(o, now, max_age)
        if m.quality != 'VALID' or any(x is None for x in (o.supply_k, o.dp_pa, o.flow_m3_s)):
            self.clear_start = None
            self.clear_ids.clear()
            return [{'code':'CRITICAL_LOCAL_SENSOR_INVALID', 'severity':'FAULT'}]
        result = []
        c = self.c
        if o.supply_k >= c['supply_hard_k']:
            if not self.hard: self.entered = now
            self.hard = True
        if o.supply_k >= c['supply_derate_k']:
            if not self.derate: self.entered = now
            self.derate = True
        clears = o.supply_k <= c['supply_derate_clear_k'] and o.supply_k <= c['supply_hard_clear_k']
        if clears:
            if self.clear_start is None: self.clear_start = now
            self.clear_ids.add(o.measurement_record_id)
            if (now-self.entered >= c['safety_dwell_ns'] and now-self.clear_start >= c['safety_dwell_ns']
                    and len(self.clear_ids) >= c['safety_recovery_samples']):
                self.derate = self.hard = False
        else:
            self.clear_start = None
            self.clear_ids.clear()
        if self.hard:
            result.append({'code':'LIQUID_SUPPLY_LIMIT_MEASURED', 'severity':'PROTECTED'})
        if self.derate:
            result.append({'code':'LIQUID_DERATE_REQUEST_ONLY', 'severity':'DERATE_REQUESTED'})
        if min(o.branch_flows_m3_s)*c['density_kg_m3'] < c['minimum_branch_flow_kg_s']:
            result.append({'code':'LOW_BRANCH_FLOW_MEASURED', 'severity':'FAULT'})
        if o.dp_pa >= self.pressure:
            result.append({'code':'OVERPRESSURE_MEASURED', 'severity':'FAULT'})
        if o.pump_fault or not o.pump_ready:
            result.append({'code':'ACTUATOR_FAULT_MEASURED', 'severity':'FAULT'})
        return result

    def envelope(self, safety):
        s = safety.data()
        reasons = s['reason_codes']
        # Pressure restriction wins over a cooling increase. No contradictory
        # temperature request can override it. Policies are integration fixtures.
        if 'OVERPRESSURE_MEASURED' in reasons:
            low = high = .3
        elif s['severity'] in ('FAULT', 'PROTECTED'):
            low = high = self.fallback
        else:
            low, high = .3, .9
        return Record.make({'record_id':s['record_id']+':envelope', 'safety_id':s['record_id'],
            'safety_digest':safety.digest, 'time_ns':s['time_ns'], 'minimum_speed':low,
            'maximum_speed':high, 'reason_codes':reasons,
            'derate_request_only':s['severity'] in ('DERATE_REQUESTED','PROTECTED','FAULT'),
            'load_cap_applied':False, 'standby_inventory':[], 'reset_authorized':False,
            'scope':'INTEGRATION_DEVELOPMENT_RESTRICTIONS_NOT_PRODUCTION_POLICY'})


class IntegrationPLC:
    """Select ONLY the current controller request after committed Safety.

    Use the exact qualified SimulatedPLC issuer to create a genuine in-process
    producer token. Never monkeypatch authentication or construct IssuedOutput.
    Its original FIXTURE_EXOGENOUS_COMMAND_VALUE tag is preserved: numerical
    closed-loop selection here is NEW integration scope, not qualified by M1.
    """
    def __init__(self, initial):
        from v0_2.tests.tools.m1_engine_v3.scheduler import PriorCommand
        self.prior = PriorCommand(initial, 0, 'INITIAL_CONDITION_NOT_PRIOR_EXECUTION_PROOF')

    def issue(self, request, envelope, safety, measurement):
        e, s = envelope.data(), safety.data()
        check(e['safety_digest'] == safety.digest and e['safety_id'] == s['record_id']
              and e['time_ns'] == measurement.time_ns, 'WRONG_SAFETY_ENVELOPE_BINDING')
        requested = self.prior.value if request is None else request
        check(isfinite(requested), 'NONFINITE_CONTROLLER_REQUEST')
        value = min(e['maximum_speed'], max(e['minimum_speed'], requested))
        # Retain the issue identity when holding a prior command. A new value
        # must get a genuine new issue at this time; never backdate it.
        issue = measurement.time_ns if value != self.prior.value else self.prior.issue_ns
        if self.prior.identity == 'INITIAL_CONDITION_NOT_PRIOR_EXECUTION_PROOF':
            issue = measurement.time_ns
        issuer = SimulatedPLC([dict(time_ns=measurement.time_ns, plc_command=value, command_timestamp_ns=issue)])
        issuer.prior = self.prior
        output = issuer.issue(safety, measurement)
        self.prior = issuer.prior
        d = output.data()
        command = ActuatorCommand(d['command_id'], measurement.time_ns, 'PLC', d['plc_cycle_id'],
            'feedback:'+measurement.measurement_record_id, e['record_id'], requested, value,
            'SAFETY_CONSTRAINED_CURRENT_FEEDBACK', 'OFFLINE_INTEGRATION',
            (measurement.measurement_record_id, s['record_id'], d['record_id']))
        return output, command


class SilentStuckActuator(PumpActuator):
    def __init__(self, config, initial):
        super().__init__(config, initial)
        self.silent_hold = False

    def _advance_segment(self, seconds):
        if not self.silent_hold:
            super()._advance_segment(seconds)


def actuator_config(profile):
    a = profile['ActuatorTrackingProfile']
    return PumpActuatorConfig(a['speed_min']['value'], a['speed_max']['value'],
        a['lag_time_constant_s']['value'], a['speed_rate_limit_per_s']['value'],
        round(a['command_delay_s']['value']*1e9))
