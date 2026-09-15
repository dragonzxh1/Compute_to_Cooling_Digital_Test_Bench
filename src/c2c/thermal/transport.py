from collections import deque
from math import floor, isfinite


class TransportDelay:
    def __init__(self, delay_s: float, dt_s: float, initial_value: float):
        if not isfinite(dt_s) or dt_s <= 0:
            raise ValueError("dt_s must be greater than zero")
        if not isfinite(delay_s) or delay_s < 0:
            raise ValueError("delay_s must be non-negative")
        self.steps = floor(delay_s / dt_s)
        self.fraction = delay_s / dt_s - self.steps
        self._values = deque([initial_value] * (self.steps + 2), maxlen=self.steps + 2)

    def step(self, value: float) -> float:
        if not isfinite(value):
            raise ValueError("transport input must be finite")
        self._values.append(float(value))
        newer = self._values[-self.steps - 1]
        older = self._values[-self.steps - 2]
        return (1 - self.fraction) * newer + self.fraction * older
