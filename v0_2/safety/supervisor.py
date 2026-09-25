"""Safety restrictions take priority over feedback intent and PLC output."""

from dataclasses import dataclass
from enum import StrEnum

from v0_2.thermal.validity import finite, require


class SafetyState(StrEnum):
    NORMAL = "NORMAL"
    FF_DISABLED = "FF_DISABLED"
    DEGRADED = "DEGRADED"
    DERATE_REQUESTED = "DERATE_REQUESTED"
    PROTECTED = "PROTECTED"
    FAULT = "FAULT"


@dataclass(frozen=True)
class SafetyPolicy:
    control_target_k: float
    operating_limit_k: float
    derate_k: float
    hard_k: float
    derate_clear_k: float
    hard_clear_k: float
    minimum_flow_kg_s: float
    maximum_dp_pa: float
    fallback_dp_pa: float
    minimum_dp_pa: float
    maximum_target_dp_pa: float
    maximum_target_rate_pa_s: float
    fault_speed: float
    dwell_ns: int = 2_000_000_000
    recovery_samples: int = 5
    source: str = "NUMERICAL_TEST_FIXTURE/ENGINEERING_ASSUMPTION/UNVALIDATED"

    def __post_init__(self):
        for name in (
            "control_target_k", "operating_limit_k", "derate_k", "hard_k", "derate_clear_k",
            "hard_clear_k", "minimum_flow_kg_s", "maximum_dp_pa", "fallback_dp_pa",
            "minimum_dp_pa", "maximum_target_dp_pa", "maximum_target_rate_pa_s", "fault_speed",
        ):
            finite(getattr(self, name), name)
        require(self.control_target_k < self.derate_k < self.hard_k, "SAFETY_CONFIG", "thermal hierarchy")
        require(self.derate_clear_k < self.derate_k and self.hard_clear_k < self.hard_k, "SAFETY_CONFIG", "hysteresis")
        require(0 < self.minimum_dp_pa <= self.fallback_dp_pa <= self.maximum_target_dp_pa, "SAFETY_CONFIG", "DP envelope")
        require(self.maximum_dp_pa > self.maximum_target_dp_pa and self.minimum_flow_kg_s >= 0, "SAFETY_CONFIG", "physical limits")
        require(self.maximum_target_rate_pa_s > 0 and 0 <= self.fault_speed <= 1, "SAFETY_CONFIG", "actuation")
        require(type(self.dwell_ns) is int and self.dwell_ns >= 0 and self.recovery_samples >= 1, "SAFETY_CONFIG", "recovery")


@dataclass(frozen=True)
class SafetyEnvelope:
    envelope_id: str
    created_ns: int
    state: SafetyState
    minimum_dp_pa: float
    maximum_dp_pa: float
    minimum_speed_fraction: float
    maximum_speed_fraction: float
    fallback_dp_pa: float
    shutdown_required: bool
    reason_codes: tuple[str, ...]
    source_measurement_ids: tuple[str, ...]
    request_id: str
    valid_until_ns: int
    accepted_target_id: str
    producer_module: str = "SAFETY"

    def __post_init__(self):
        require(self.producer_module == "SAFETY", "SAFETY_OWNERSHIP", self.envelope_id)
        require(self.minimum_dp_pa <= self.maximum_dp_pa, "SAFETY_ENVELOPE", "DP bounds")
        require(
            0 <= self.minimum_speed_fraction <= self.maximum_speed_fraction <= 1,
            "SAFETY_ENVELOPE",
            "speed bounds",
        )
        require(self.valid_until_ns >= self.created_ns, "SAFETY_ENVELOPE", "validity")


@dataclass(frozen=True)
class SafetyDecision:
    state: SafetyState
    accepted_dp_pa: float
    reasons: tuple[str, ...]
    derate_requested: bool
    envelope: SafetyEnvelope


class SafetySupervisor:
    def __init__(self, policy: SafetyPolicy):
        self.policy = policy
        self.state = SafetyState.FF_DISABLED
        self.entered_ns = 0
        self.last_sequence = -1
        self.recovery_count = 0
        self.derate_latched = False
        self.hard_latched = False
        self.last_accepted = policy.fallback_dp_pa
        self.last_time_ns = 0
        self.events = []
        self.fault_latched = False
        self.tracking_since_ns = None
        self.envelopes = []

    def reset_fault(self, now_ns: int):
        """Explicit operator/test-harness reset; never an automatic recovery."""
        require(type(now_ns) is int and now_ns >= self.entered_ns, "SAFETY_RESET", "time")
        self.fault_latched = False
        self.tracking_since_ns = None
        self.entered_ns = now_ns
        self.recovery_count = 0

    def evaluate(
        self,
        now_ns,
        measured,
        max_age_ns,
        requested_dp_pa,
        commanded_speed=None,
        *,
        accepted_target_id="not_applicable",
    ):
        p = self.policy
        reasons = []
        valid = measured is not None and all(
            measured.qualified(ch, now_ns, max_age_ns)
            for ch in ("temperature", "dp", "flow", "pump_speed", "pump_status")
        )
        if not valid or not measured.device_temperatures_k or measured.dp_pa is None or measured.flow_kg_s is None or measured.pump_speed is None:
            candidate = SafetyState.FAULT
            reasons.append("CRITICAL_LOCAL_SENSOR_INVALID")
        else:
            peak = max(t for _, t in measured.device_temperatures_k)
            if peak >= p.hard_k:
                self.hard_latched = True
            if peak >= p.derate_k:
                self.derate_latched = True
            if self.hard_latched and peak <= p.hard_clear_k:
                self.hard_latched = False
            if self.derate_latched and peak <= p.derate_clear_k:
                self.derate_latched = False
            if measured.pump_fault or not measured.pump_ready:
                candidate = SafetyState.FAULT
                reasons.append("ACTUATOR_FAULT_MEASURED")
            elif measured.dp_pa >= p.maximum_dp_pa:
                candidate = SafetyState.FAULT
                reasons.append("OVERPRESSURE_MEASURED")
            elif commanded_speed is not None and abs(commanded_speed - measured.pump_speed) > 0.15:
                if self.tracking_since_ns is None:
                    self.tracking_since_ns = now_ns
                if now_ns - self.tracking_since_ns >= 2_000_000_000:
                    candidate = SafetyState.FAULT
                    reasons.append("ACTUATOR_TRACKING_FAILURE_MEASURED")
                else:
                    candidate = SafetyState.DEGRADED
                    reasons.append("ACTUATOR_TRACKING_PENDING")
            elif self.hard_latched:
                candidate = SafetyState.PROTECTED
                reasons.append("HARD_THERMAL_MEASURED")
            elif self.derate_latched or measured.flow_kg_s < p.minimum_flow_kg_s:
                candidate = SafetyState.DERATE_REQUESTED
                reasons.append("THERMAL_OR_FLOW_CAPACITY_LIMITED")
            else:
                candidate = SafetyState.NORMAL
                self.tracking_since_ns = None
        if candidate == SafetyState.FAULT:
            self.fault_latched = True
        elif self.fault_latched:
            candidate = SafetyState.FAULT
            reasons.append("FAULT_LATCHED_RESET_REQUIRED")
        if candidate == SafetyState.NORMAL and self.state != SafetyState.NORMAL:
            if measured is not None and measured.sequence != self.last_sequence:
                self.recovery_count += 1
                self.last_sequence = measured.sequence
            if self.recovery_count < p.recovery_samples or now_ns - self.entered_ns < p.dwell_ns:
                candidate = SafetyState.FF_DISABLED
                reasons.append("RECOVERY_QUALIFICATION")
        else:
            self.recovery_count = 0
            if measured is not None:
                self.last_sequence = measured.sequence
        if candidate != self.state:
            self.state, self.entered_ns = candidate, now_ns
            self.events.append((now_ns, candidate.value, tuple(reasons)))
        finite(requested_dp_pa, "requested DP")
        accepted = min(p.maximum_target_dp_pa, max(p.minimum_dp_pa, requested_dp_pa))
        if accepted != requested_dp_pa:
            reasons.append("CONTROL_REQUEST_REJECTED")
        elapsed = max(0, now_ns - self.last_time_ns) / 1e9
        allowed = p.maximum_target_rate_pa_s * elapsed
        accepted = min(self.last_accepted + allowed, max(self.last_accepted - allowed, accepted))
        minimum_speed, maximum_speed = 0.0, 1.0
        if self.state in (SafetyState.FAULT, SafetyState.PROTECTED):
            accepted = p.fallback_dp_pa
            minimum_speed = maximum_speed = p.fault_speed
            reasons.append("SAFETY_OVERRIDE")
        elif self.state == SafetyState.DERATE_REQUESTED:
            reasons.append("CAPACITY_LIMITED")
        self.last_accepted, self.last_time_ns = accepted, now_ns
        measurement_id = getattr(measured, "measurement_record_id", "not_applicable")
        request_id = (
            f"derate-request:{now_ns}"
            if self.state in (SafetyState.DERATE_REQUESTED, SafetyState.PROTECTED, SafetyState.FAULT)
            else "not_applicable"
        )
        envelope = SafetyEnvelope(
            f"safety-envelope:{now_ns}:{self.state.value}",
            now_ns,
            self.state,
            accepted,
            accepted,
            minimum_speed,
            maximum_speed,
            p.fallback_dp_pa,
            False,
            tuple(reasons),
            (measurement_id,) if measurement_id != "not_applicable" else (),
            request_id,
            now_ns + max_age_ns,
            accepted_target_id,
        )
        self.envelopes.append(envelope)
        return SafetyDecision(
            self.state,
            accepted,
            tuple(reasons),
            self.state in (SafetyState.DERATE_REQUESTED, SafetyState.PROTECTED, SafetyState.FAULT),
            envelope,
        )
