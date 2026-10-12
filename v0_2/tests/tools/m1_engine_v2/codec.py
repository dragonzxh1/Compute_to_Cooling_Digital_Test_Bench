"""Typed, presence-preserving, binary64 exact core representation."""
from dataclasses import fields, is_dataclass
import math
import struct
from .common import canonical


def encode(value):
    if value is None:
        return {'type': 'none'}
    if type(value) is bool:
        return {'type': 'bool', 'value': value}
    if type(value) is int:
        return {'type': 'int', 'value': value}
    if type(value) is float:
        # Preserve raw invalid binary64 identity for negative-input diagnostic
        # snapshots. Admission/qualification still rejects nonfinite samples.
        return {'type': 'float64', 'bits': struct.pack('>d', value).hex()}
    if type(value) is str:
        return {'type': 'str', 'value': value}
    if is_dataclass(value):
        return {'type': 'dataclass', 'class': type(value).__module__ + '.' + type(value).__qualname__,
                'fields': {f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise TypeError('NON_STRING_CORE_KEY')
        return {'type': 'dict', 'fields': {key: encode(v) for key, v in value.items()}}
    if type(value) in (list, tuple):
        return {'type': type(value).__name__, 'items': [encode(v) for v in value]}
    if type(value) is set:
        return {'type': 'set', 'items': sorted((encode(v) for v in value), key=canonical)}
    raise TypeError('UNSUPPORTED_CORE_TYPE: ' + type(value).__name__)


def decode(value):
    kind = value['type']
    if kind in ('none', 'absent'):
        return None
    if kind == 'float64':
        return struct.unpack('>d', bytes.fromhex(value['bits']))[0]
    if kind in ('str', 'int', 'bool'):
        return value['value']
    if kind in ('dict', 'dataclass'):
        return {k: decode(v) for k, v in value['fields'].items()}
    if kind in ('list', 'tuple', 'set'):
        items = [decode(v) for v in value['items']]
        return tuple(items) if kind == 'tuple' else items
    raise ValueError('UNKNOWN_TYPED_CORE')


def first_difference(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return path + ':type'
    if type(expected) is dict:
        if set(expected) != set(actual):
            return path + ':keys'
        for key in sorted(expected):
            different = first_difference(expected[key], actual[key], path + '/' + key)
            if different:
                return different
    elif type(expected) is list:
        if len(expected) != len(actual):
            return path + ':length'
        for index, (a, b) in enumerate(zip(expected, actual)):
            different = first_difference(a, b, path + '/' + str(index))
            if different:
                return different
    elif expected != actual:
        return path
    return None



