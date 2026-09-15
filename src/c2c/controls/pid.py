from dataclasses import dataclass


@dataclass
class PID:
    kp: float
    ki: float
    kd: float
    output_min: float
    output_max: float
    bias: float = 0.0
    integral: float = 0.0
    previous_error: float = 0.0

    def step(self, error: float, dt_s: float) -> float:
        derivative = (error - self.previous_error) / dt_s if dt_s > 0 else 0.0
        proposed_integral = self.integral + error * dt_s
        raw = self.bias + self.kp * error + self.ki * proposed_integral + self.kd * derivative
        output = min(self.output_max, max(self.output_min, raw))
        driving_high = raw > self.output_max and error > 0
        driving_low = raw < self.output_min and error < 0
        if not (driving_high or driving_low):
            self.integral = proposed_integral
        self.previous_error = error
        return output
