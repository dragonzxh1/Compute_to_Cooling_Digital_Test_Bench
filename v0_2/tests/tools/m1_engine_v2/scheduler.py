"""Restricted measurement view and private, exogenous simulated PLC schedule."""
from dataclasses import dataclass, asdict
from .common import Record


class CapabilityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MeasurementView:
    time_ns: int
    measured_speed: float | None
    sample_ns: int | None
    release_ns: int | None
    quality: str
    measurement_record_id: str
    provenance: str = 'CERTIFIED_INTERVAL_END'

    def __post_init__(self):
        if self.release_ns is not None and self.release_ns > self.time_ns:
            raise CapabilityError('UNRELEASED_MEASUREMENT_DENIED')
        if self.sample_ns is not None and self.release_ns is not None and self.sample_ns > self.release_ns:
            raise CapabilityError('FUTURE_MEASUREMENT_WINDOW_DENIED')

    @classmethod
    def from_row(cls, row, provenance='CERTIFIED_INTERVAL_END'):
        return cls(**{name: row[name] for name in cls.__dataclass_fields__ if name != 'provenance'},
                   provenance=provenance)

    def request(self, name, access_log):
        if name not in self.__dataclass_fields__:
            access_log.append({'actor': 'PRE', 'kind': 'DENIED_FUTURE_COMMAND_ACCESS', 'name': name})
            raise CapabilityError(name)
        access_log.append({'actor': 'PRE', 'kind': 'MEASUREMENT_READ', 'name': name})
        return getattr(self, name)


@dataclass(frozen=True)
class PriorCommand:
    value: float
    issue_ns: int
    identity: str


@dataclass(frozen=True)
class IssuedOutput:
    record: Record
    _producer: object

    def data(self):
        return self.record.data()

    @property
    def digest(self):
        return self.record.digest

    def authenticated(self):
        return type(self._producer) is SimulatedPLC and self._producer.verify(self)


class SimulatedPLC:
    def __init__(self, rows):
        self.__rows = tuple(dict(row) for row in rows)
        self.__cursor = 0
        first = self.__rows[0]
        self.prior = PriorCommand(first['plc_command'], first['command_timestamp_ns'],
                                  'released-command:' + str(first['command_timestamp_ns']))
        self.__outputs = []

    @property
    def outputs(self):
        return tuple(self.__outputs)

    def verify(self, output):
        return any(candidate is output for candidate in self.__outputs)

    def issue(self, safety, measurement):
        decision = safety.data()
        if decision['phase'] != 'SAFETY' or decision['time_ns'] != measurement.time_ns:
            raise CapabilityError('PLC_REQUIRES_CURRENT_SAFETY')
        row = self.__rows[self.__cursor]
        if row['time_ns'] != measurement.time_ns:
            raise CapabilityError('PLC_SCHEDULE_TIME_MISMATCH')
        if (row['plc_command'], row['command_timestamp_ns']) != (self.prior.value, self.prior.issue_ns):
            if row['command_timestamp_ns'] != row['time_ns']:
                raise CapabilityError('TEST_INPUT_CAUSALITY_UNRESOLVED')
        output = Record.make({'phase': 'PLC', 'transaction_id': decision['transaction_id'],
            'time_ns': measurement.time_ns, 'producer': 'SIMULATED_PLC',
            'scope': 'SIMULATED_PLC_CAUSAL_OWNERSHIP',
            'value_scope': 'FIXTURE_EXOGENOUS_COMMAND_VALUE',
            'numeric_hardware_authorization': 'OUT_OF_SCOPE',
            'command': row['plc_command'], 'issue_ns': row['command_timestamp_ns'],
            'command_id': 'released-command:' + str(row['command_timestamp_ns']),
            'plc_cycle_id': decision['transaction_id'] + ':PLC',
            'safety_id': decision['record_id'], 'record_id': decision['transaction_id'] + ':PLC'})
        data = output.data()
        data['safety_digest'] = safety.digest
        output = IssuedOutput(Record.make(data), self)
        self.prior = PriorCommand(output.data()['command'], output.data()['issue_ns'], output.data()['command_id'])
        self.__outputs.append(output)
        self.__cursor += 1
        return output


