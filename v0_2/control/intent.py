from dataclasses import dataclass

from v0_2.thermal.validity import finite, require


@dataclass(frozen=True)
class ControlIntent:
    intent_id: str
    source: str
    created_ns: int
    available_ns: int
    expires_ns: int
    requested_dp_pa: float
    fb_component_pa: float
    ff_component_pa: float = 0.0
    validity: str = "VALID"
    reason: str = "FEEDBACK_ONLY"

    def __post_init__(self):
        require(self.source == "FEEDBACK" and self.ff_component_pa == 0, "FF_FORBIDDEN", self.intent_id)
        require(0 <= self.created_ns <= self.available_ns < self.expires_ns, "INTENT_TIME", self.intent_id)
        finite(self.requested_dp_pa, "requested DP")
        finite(self.fb_component_pa, "FB component")


@dataclass(frozen=True)
class AcceptedTarget:
    accepted_target_id: str
    created_ns: int
    requested_dp_pa: float
    producer_module: str
    fb_intent_id: str
    reason: str
    source_ids: tuple[str, ...]

    def __post_init__(self):
        require(self.producer_module == "SUPERVISOR", "TARGET_OWNERSHIP", self.accepted_target_id)
        require(type(self.created_ns) is int and self.created_ns >= 0, "TARGET_TIME", self.accepted_target_id)
        finite(self.requested_dp_pa, "accepted target DP")


class IntentSupervisor:
    """Phase 5 accepts feedback intents only; safety applies the final envelope."""

    def __init__(self, fallback_dp_pa: float):
        finite(fallback_dp_pa, "fallback DP")
        self.fallback_dp_pa = fallback_dp_pa
        self.last_sequence = -1
        self.targets = []

    def accept(self, intent: ControlIntent | None, now_ns: int):
        target = self.accept_target(intent, now_ns)
        return target.requested_dp_pa, target.reason

    def accept_target(self, intent: ControlIntent | None, now_ns: int) -> AcceptedTarget:
        if intent is None:
            return self._target(now_ns, self.fallback_dp_pa, "NO_INTENT", "not_applicable")
        require(intent.source == "FEEDBACK" and intent.ff_component_pa == 0, "FF_FORBIDDEN", intent.intent_id)
        if intent.available_ns > now_ns:
            return self._target(now_ns, self.fallback_dp_pa, "INTENT_NOT_AVAILABLE", intent.intent_id)
        if intent.expires_ns <= now_ns:
            return self._target(now_ns, self.fallback_dp_pa, "INTENT_EXPIRED", intent.intent_id)
        if intent.validity != "VALID":
            return self._target(now_ns, self.fallback_dp_pa, "INTENT_INVALID", intent.intent_id)
        return self._target(now_ns, intent.requested_dp_pa, "FB_ACCEPTED", intent.intent_id)

    def _target(self, now_ns: int, value: float, reason: str, intent_id: str) -> AcceptedTarget:
        self.last_sequence += 1
        target = AcceptedTarget(
            f"accepted-target:{now_ns}:{self.last_sequence}",
            now_ns,
            value,
            "SUPERVISOR",
            intent_id,
            reason,
            (intent_id,) if intent_id != "not_applicable" else (),
        )
        self.targets.append(target)
        return target
