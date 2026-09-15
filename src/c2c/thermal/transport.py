from collections import deque


class TransportDelay:
    def __init__(self, delay_s: float, dt_s: float, initial_value: float):
        if dt_s <= 0:
            raise ValueError("dt_s must be greater than zero")
        if delay_s < 0:
            raise ValueError("delay_s must be non-negative")
        steps = round(delay_s / dt_s)
        self._values = deque([initial_value] * steps, maxlen=steps) if steps else None

    def step(self, value: float) -> float:
        if self._values is None:
            return float(value)
        delayed = self._values[0]
        self._values.append(float(value))
        return delayed
