from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class SimulationClock:
    dt_s: float
    duration_s: float

    def steps(self):
        if self.dt_s <= 0:
            raise ValueError("dt_s must be greater than zero")
        if self.duration_s < 0:
            raise ValueError("duration_s must be non-negative")
        count = floor(self.duration_s / self.dt_s)
        for index in range(count + 1):
            yield index, index * self.dt_s
