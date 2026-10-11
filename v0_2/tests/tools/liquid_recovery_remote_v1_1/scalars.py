"""Explicit NumPy scalar -> JSON/log primitives; never changes plant values."""
import math
import numpy as np


def scalar(value):
    kind = type(value)
    if kind in (float, np.float64, np.float32):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("NONFINITE_DIAGNOSTIC_SCALAR")
        return result
    if kind in (int, np.int64, np.int32):
        return int(value)
    if kind in (bool, np.bool_):
        return bool(value)
    raise TypeError("UNSUPPORTED_DIAGNOSTIC_SCALAR")
