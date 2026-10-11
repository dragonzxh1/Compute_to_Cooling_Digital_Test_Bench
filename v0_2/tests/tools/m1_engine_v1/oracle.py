"""Independent fixture oracle. Never consumes SUT Safety payload or declared expectations."""
from dataclasses import dataclass
import math
from .common import ROOT, canonical, sha, read
from .codec import decode

REGISTRATION_SHA256 = 'fe85843dd38923230a49ce65b50c302c9322819ef020338c8748273ad97e97e0'
PATH = 'v0_2/tests/tools/m1_engine_v1/oracle_stimulus_v1.json'


class OracleInputError(ValueError):
    pass


def registration():
    raw = (ROOT / PATH).read_bytes()
    if sha(raw) != REGISTRATION_SHA256:
        raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: stimulus identity')
    data = __import__('json').loads(raw)
    for path, expected in data['policy_bindings'].items():
        b = (ROOT / path).read_bytes()
        if sha(b) != expected['raw_sha256']:
            raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: policy ' + path)
        if 'canonical_sha256' in expected and sha(canonical(__import__('json').loads(b))) != expected['canonical_sha256']:
            raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: canonical policy')
    return data


def policy_expected(state, channels, retained=()):
    """Frozen mapping + independently supplied active channels and legitimate latch ledger."""
    mapping = read('phase5_r5_2_1r4_7_c2_r1_timing_policy_registration.json')['safety_mapping'][state]
    hierarchy = ['NORMAL', 'FF_DISABLED', 'DEGRADED', 'DERATE_REQUESTED', 'PROTECTED', 'FAULT']
    reasons = set(mapping['reason_codes']) | {c['code'] for c in channels} | set(retained)
    severities = [mapping['severity']] + [c['severity'] for c in channels]
    if retained:
        severities.append('FAULT')
    return {'reason_codes': sorted(reasons), 'severity': max(severities, key=hierarchy.index)}


@dataclass(frozen=True)
class TrustedContext:
    raw: bytes
    digest: str
    producer: object

    def valid(self):
        return type(self.producer) is OracleTrace and self.producer.verify(self) and sha(self.raw) == self.digest

    def data(self):
        return __import__('json').loads(self.raw)


class OracleTrace:
    """Registered inputs only; prefix ledger generated from trusted reference, NOT split."""
    def __init__(self, scenario, rows):
        self.reg = registration()
        if scenario not in self.reg['scenarios']:
            raise OracleInputError('QUALIFICATION_INPUT_MISSING: unregistered scenario')
        self.scenario = scenario
        self.definition = self.reg['scenarios'][scenario]
        self.rows = __import__('json').loads(canonical(rows))
        d = self.definition['descriptor']
        source = (ROOT / d['result_path']).read_bytes()
        if sha(source) != d['result_raw_sha256']:
            raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: source artifact')
        parsed = __import__('json').loads(source)
        if sha(canonical(parsed)) != d['result_canonical_sha256']:
            raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: source canonical')
        for key in d['input_pointer'].split('/')[1:]:
            parsed = parsed[key.replace('~1', '/').replace('~0', '~')]
        if sha(canonical(self.rows)) != d['input_canonical_sha256'] or self.rows != parsed or len(self.rows) != d['row_count']:
            raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: source rows')
        self._contexts = []

    def verify(self, context):
        return any(context is c for c in self._contexts)

    def channels(self, index, reference_before):
        codes = []
        for event in self.definition['independent_channel_events']:
            if event['row'] <= index:
                codes = list(event['channels'])
        row = self.rows[index]
        max_age = decode(reference_before['max_age_ns'])
        valid = (row['quality'] == 'VALID' and row['measured_speed'] is not None
                 and math.isfinite(row['measured_speed']) and row['sample_ns'] is not None
                 and row['release_ns'] is not None and row['sample_ns'] <= row['release_ns'] <= row['time_ns']
                 and 0 <= row['time_ns'] - row['sample_ns'] <= max_age)
        if not valid and 'SENSOR_INVALID' not in codes:
            codes.append('SENSOR_INVALID')
        return [{'code': c, 'severity': self.reg['channel_severity'][c]} for c in codes]

    def context(self, index, references):
        if len(references) <= index or index >= len(self.rows):
            raise OracleInputError('QUALIFICATION_INPUT_MISSING: reference prefix')
        retained = set(self.definition['initial_retained_fault_reasons'])
        for j in range(index + 1):
            frame = references[j]
            if decode(frame['after']['previous_observation']) != self.rows[j]:
                raise OracleInputError('QUALIFICATION_INPUT_CORRUPT: reference source binding')
            channels = self.channels(j, frame['before'])
            retained.update(c['code'] for c in channels if c['severity'] == 'FAULT')
            # Qualified reference confirmed latch survives withdrawal/POST; never SUT metadata.
            if decode(frame['after']['confirmed_latched']):
                retained.add('ACTUATOR_TRACKING_CONFIRMED')
        current = self.channels(index, references[index]['before'])
        payload = {'scenario': self.scenario, 'row_index': index, 'source_row': self.rows[index],
                   'source_input_sha256': self.definition['descriptor']['input_canonical_sha256'],
                   'registration_sha256': REGISTRATION_SHA256, 'independent_channels': current,
                   'retained_fault_reasons': sorted(retained), 'provenance': self.reg['provenance']}
        raw = canonical(payload)
        context = TrustedContext(raw, sha(raw), self)
        self._contexts.append(context)
        return context


