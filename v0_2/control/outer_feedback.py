"""Temperature-only outer feedback; output is a DP target, never pump speed."""

from dataclasses import dataclass

from v0_2.control.intent import ControlIntent
from v0_2.control.pid import PIDConfig, TrackingPID
from v0_2.thermal.validity import require


@dataclass(frozen=True)
class OuterConfig:
    pid: PIDConfig
    base_dp_pa: float
    target_k: float
    mode: str = "DP_TARGET"

    def __post_init__(self):
        require(self.mode == "DP_TARGET", "CONTROL_MODE", "Phase 5 validates exclusive DP target only")


class OuterFeedback:
    def __init__(self, config: OuterConfig):
        self.config = config
        self.pid = TrackingPID(config.pid)
        self.last_intent = None

    def update(self, now_ns, measured, accepted_dp_pa, max_age_ns):
        require(measured is not None and measured.qualified("temperature", now_ns, max_age_ns), "FEEDBACK_MEASUREMENT", "released temperature required")
        require(bool(measured.device_temperatures_k), "FEEDBACK_MEASUREMENT", "no measured devices")
        peak = max(t for _, t in measured.device_temperatures_k)
        correction = self.pid.update(peak - self.config.target_k, accepted_dp_pa - self.config.base_dp_pa)
        self.last_intent = ControlIntent(
            f"fb:{now_ns}", "FEEDBACK", now_ns, now_ns,
            now_ns + 2 * self.config.pid.sample_ns,
            self.config.base_dp_pa + correction, correction, 0.0,
        )
        return self.last_intent
