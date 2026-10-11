import json
import numpy as np
import pytest
from v0_2.tests.tools.liquid_recovery_remote_v1_1.scalars import scalar


@pytest.mark.parametrize("value", [np.float64(1.125), np.float32(1.125), 1.125])
def test_numeric_value_preserved(value):
    result = scalar(value)
    assert type(result) is float and result == 1.125
    assert json.loads(json.dumps(result, allow_nan=False)) == 1.125


@pytest.mark.parametrize("value", [np.int64(2**60 + 1), 2**60 + 1])
def test_integer_no_float_precision_loss(value):
    assert type(scalar(value)) is int and scalar(value) == 2**60 + 1


def test_numpy_boolean_remains_boolean():
    assert scalar(np.bool_(True)) is True
    assert scalar(np.bool_(False)) is False


@pytest.mark.parametrize("value", [np.float64(np.nan), np.float64(np.inf), float('-inf')])
def test_nonfinite_rejected(value):
    with pytest.raises(ValueError, match="NONFINITE_DIAGNOSTIC_SCALAR"):
        scalar(value)


def test_unknown_hooks_never_invoked():
    class Trap:
        def __float__(self):
            raise AssertionError("UNSAFE_FLOAT_HOOK")
        def __repr__(self):
            raise AssertionError("UNSAFE_REPR_HOOK")
    with pytest.raises(TypeError, match="UNSUPPORTED_DIAGNOSTIC_SCALAR"):
        scalar(Trap())


def test_arrays_complex_and_numeric_strings_rejected():
    for value in (np.array([1.0]), np.complex128(1), "1.0"):
        with pytest.raises(TypeError, match="UNSUPPORTED_DIAGNOSTIC_SCALAR"):
            scalar(value)
