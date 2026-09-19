from enum import StrEnum
from math import isfinite


class ValidityStatus(StrEnum):
    VALID = "VALID"
    CONFIG_INVALID = "CONFIG_INVALID"
    MODEL_INVALID = "MODEL_INVALID"
    MODEL_OUT_OF_RANGE = "MODEL_OUT_OF_RANGE"


class SolverStatus(StrEnum):
    CONVERGED = "CONVERGED"
    RETRYABLE = "RETRYABLE"
    FAILED = "FAILED"


class ThermalError(ValueError):
    def __init__(self, code, detail, status=ValidityStatus.CONFIG_INVALID):
        self.code, self.status = code, status
        super().__init__(f"{code}: {detail}")


def require(condition, code, detail, status=ValidityStatus.CONFIG_INVALID):
    if not condition:
        raise ThermalError(code, detail, status)


def finite(value, name):
    require(
        isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value),
        "NONFINITE",
        name,
    )


def interval(t_ns, dt_ns):
    require(
        type(t_ns) is int and t_ns >= 0 and type(dt_ns) is int and dt_ns > 0,
        "INVALID_TIME",
        "nonnegative integer start and positive integer ns duration required",
    )
