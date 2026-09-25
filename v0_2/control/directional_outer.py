"""R5 numerical-fixture outer feedback with one continuous directional PI state."""

from __future__ import annotations

from dataclasses import replace

from v0_2.control.outer_feedback import OuterConfig, OuterFeedback
from v0_2.thermal.validity import finite, require


class DirectionalOuterFeedback(OuterFeedback):
    """Change only the integration gain selected from released measured error."""

    BLEND_HALFWIDTH_K = 0.1

    def __init__(self, config: OuterConfig, ki_hot: float, ki_cold: float):
        super().__init__(config)
        finite(ki_hot, "Ki hot")
        finite(ki_cold, "Ki cold")
        require(ki_hot >= 0 and ki_cold >= 0, "DIRECTIONAL_KI", "nonnegative Ki")
        require(config.pid.kd == 0, "DIRECTIONAL_KI", "R5 derivative forbidden")
        self.ki_hot = ki_hot
        self.ki_cold = ki_cold
        self.ticks: list[dict] = []

    def effective_ki(self, error_k: float) -> tuple[float, str]:
        finite(error_k, "measured temperature error")
        if error_k <= -self.BLEND_HALFWIDTH_K:
            return self.ki_cold, "COLD"
        if error_k >= self.BLEND_HALFWIDTH_K:
            return self.ki_hot, "HOT"
        alpha = (error_k + self.BLEND_HALFWIDTH_K) / (2 * self.BLEND_HALFWIDTH_K)
        return (1 - alpha) * self.ki_cold + alpha * self.ki_hot, "BLEND"

    def update(self, now_ns, measured, accepted_dp_pa, max_age_ns):
        require(measured is not None and measured.qualified("temperature", now_ns, max_age_ns), "FEEDBACK_MEASUREMENT", "released temperature required")
        require(bool(measured.device_temperatures_k), "FEEDBACK_MEASUREMENT", "no measured devices")
        error_k = max(t for _, t in measured.device_temperatures_k) - self.config.target_k
        ki_eff, region = self.effective_ki(error_k)
        old_config = self.pid.config
        before_integral = self.pid.integral
        previous_error = self.pid.previous_error
        applied_echo = accepted_dp_pa - self.config.base_dp_pa
        requested_before = self.last_intent.requested_dp_pa if self.last_intent else None
        dt = old_config.sample_ns / 1e9
        derivative = 0.0 if previous_error is None else old_config.kd * (error_k - previous_error) / dt
        proposed_before_switch = old_config.kp * error_k + before_integral + derivative
        self.pid.config = replace(old_config, ki=ki_eff)
        proposed_after_switch = self.pid.config.kp * error_k + before_integral + derivative
        intent = super().update(now_ns, measured, accepted_dp_pa, max_age_ns)
        after_integral = self.pid.integral
        if previous_error is None:
            expected_after = after_integral
            continuity_pass = True
        else:
            tracking = old_config.tracking_gain * (applied_echo - proposed_before_switch)
            expected_after = min(old_config.integral_limit, max(-old_config.integral_limit, before_integral + ki_eff * error_k * dt + tracking * dt))
            continuity_pass = abs(after_integral - expected_after) <= 1e-8
        self.ticks.append({
            "time_ns": now_ns,
            "error_k": error_k,
            "region": region,
            "ki_eff": ki_eff,
            "integral_before": before_integral,
            "integral_after": after_integral,
            "expected_integral_after": expected_after,
            "integral_continuity_pass": continuity_pass,
            "instantaneous_gain_jump_pa": proposed_after_switch - proposed_before_switch,
            "applied_measured_dp_echo_pa": accepted_dp_pa,
            "requested_dp_before_pa": requested_before,
            "requested_dp_after_pa": intent.requested_dp_pa,
        })
        return intent
