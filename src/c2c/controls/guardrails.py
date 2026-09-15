def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def deadband(value: float, width: float) -> float:
    if width < 0:
        raise ValueError("deadband width must be non-negative")
    if abs(value) <= width:
        return 0.0
    return value - width if value > 0 else value + width


def rate_limit(target: float, current: float, max_rate_per_s: float, dt_s: float) -> float:
    change = clamp(target - current, -max_rate_per_s * dt_s, max_rate_per_s * dt_s)
    return current + change
