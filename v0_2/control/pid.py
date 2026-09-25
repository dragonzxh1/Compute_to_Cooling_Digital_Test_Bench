"""Sampled PI/PID with measured-output tracking anti-windup."""

from dataclasses import dataclass

from v0_2.thermal.validity import finite, require


@dataclass(frozen=True)
class PIDConfig:
    kp: float
    ki: float
    kd: float
    sample_ns: int
    lower: float
    upper: float
    integral_limit: float
    tracking_gain: float = 1.0

    def __post_init__(self):
        for name in ("kp", "ki", "kd", "lower", "upper", "integral_limit", "tracking_gain"):
            finite(getattr(self, name), name)
        require(type(self.sample_ns) is int and self.sample_ns > 0, "CONTROL_CONFIG", "period")
        require(self.lower < self.upper and self.integral_limit >= 0, "CONTROL_CONFIG", "bounds")
        require(self.ki >= 0 and self.kd >= 0 and self.tracking_gain >= 0, "CONTROL_CONFIG", "gains")


class TrackingPID:
    def __init__(self, config: PIDConfig):
        self.config = config
        self.integral = 0.0
        self.previous_error = None
        self.output = 0.0

    def initialize(self, error: float, applied: float):
        finite(error, "error")
        finite(applied, "applied")
        self.integral = min(
            self.config.integral_limit,
            max(-self.config.integral_limit, applied - self.config.kp * error),
        )
        self.previous_error = error
        self.output = min(self.config.upper, max(self.config.lower, applied))

    def update(self, error: float, applied: float, *, automatic: bool = True) -> float:
        """`applied` is a qualified measured response, never raw actuator truth."""
        finite(error, "error")
        finite(applied, "measured applied output")
        c = self.config
        if not automatic:
            self.initialize(error, applied)
            return self.output
        if self.previous_error is None:
            self.initialize(error, applied)
        dt = c.sample_ns / 1e9
        derivative = c.kd * (error - self.previous_error) / dt
        proposed = c.kp * error + self.integral + derivative
        clipped = min(c.upper, max(c.lower, proposed))
        # Tracking correction uses the arrived measured actuator/controlled output.
        # A large requested output cannot accumulate unbounded integral at a hard stop.
        tracking = c.tracking_gain * (applied - proposed)
        self.integral = min(
            c.integral_limit,
            max(-c.integral_limit, self.integral + c.ki * error * dt + tracking * dt),
        )
        self.previous_error = error
        self.output = clipped
        return clipped
