"""V2 scenario effects on physics/measurement only; no core or V1 edits."""
from dataclasses import replace
from math import exp

from v0_2.thermal.provenance import ParameterRecord
from v0_2.tests.tools.gb300_m1_closed_loop_v1.plant import SixRackPlant, check
from v0_2.tests.tools.gb300_m1_closed_loop_v1.interfaces import Sensor, SilentStuckActuator


def parameter(name, value, unit):
    return ParameterRecord(name, value, unit, 'ENGINEERING_ASSUMPTION',
        'gb300_m1_closed_loop_v2/study.json: explicit uncalibrated OAT/injected fault',
        0., '2026-10-16', (value,value), 'CALIBRATION_REQUIRED')


class StudyPlant(SixRackPlant):
    def __init__(self, c, setting):
        super().__init__(c)
        self.curve = replace(self.curve, shutoff_head_pa=parameter('head.sensitivity',
            self.curve.shutoff_head_pa.value*setting['pump_head_scale'], 'Pa'))
        self.resistance_multiplier = 1.

    def restrict_network(self, factor):
        check(self.resistance_multiplier == 1. and 1 < factor <= 100, 'BOUND_SINGLE_RESISTANCE_EVENT')
        def edge(e):
            return replace(e, coefficient=parameter(e.edge_id+'.restricted.K',
                e.coefficient.value*factor, 'Pa/(m3/s)^2'))
        self.graph = replace(self.graph, supply_series=tuple(map(edge,self.graph.supply_series)),
            branches=tuple(tuple(map(edge,b)) for b in self.graph.branches),
            return_series=tuple(map(edge,self.graph.return_series)))
        self.resistance_multiplier = factor


class FaultActuator(SilentStuckActuator):
    def __init__(self, config, initial):
        super().__init__(config, initial)
        self.degraded = False
        self.degraded_ever = False

    def _advance_segment(self, seconds):
        if self.silent_hold or seconds <= 0: return
        if not self.degraded:
            return super()._advance_segment(seconds)
        # Existing registered test-only R5.2 SLOW_RAMP_0_05 physical response.
        # Published nominal profile and measured equipment fault bits unchanged.
        exact = self.target+(self.actual-self.target)*exp(-seconds/4.)
        delta = min(.05*seconds,max(-.05*seconds,exact-self.actual))
        self.actual = min(self.config.maximum,max(self.config.minimum,self.actual+delta))


class FaultSensor(Sensor):
    def __init__(self, delay_ns):
        super().__init__(delay_ns)
        self.missing = self.withheld = False

    def sample(self, snapshot, quality='VALID'):
        if self.withheld:
            return None  # no fabricated fresh sample, timestamp or ID
        return super().sample(snapshot, 'MISSING' if self.missing else quality)


def apply_fault(fault, now, actuator, sensor, plant):
    active = bool(fault) and fault['start_ns'] <= now < fault['end_ns']
    kind = fault['kind'] if fault else None
    actuator.silent_hold = active and kind == 'SILENT_STUCK_THEN_RELEASE'
    actuator.degraded = active and kind == 'RAMP_0_05_TAU_4'
    actuator.degraded_ever |= actuator.degraded
    sensor.missing = active and kind == 'MISSING_QUALITY'
    sensor.withheld = active and kind == 'STOP_PUBLISHING_SAMPLES'
    if active and kind == 'NETWORK_RESISTANCE_100X' and plant.resistance_multiplier == 1:
        plant.restrict_network(100.)
