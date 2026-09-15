from dataclasses import dataclass


@dataclass(frozen=True)
class LiquidTemperatureSpRequest:
    requested_c: float
    timestamp_s: float
