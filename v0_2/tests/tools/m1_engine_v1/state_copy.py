"""Strict native/dataclass state clone with memoized alias preservation.

No pickle/reduction hooks, no mutable sharing with the qualified reference.
Unexpected runtime objects are rejected rather than silently copied.
"""
from dataclasses import fields, is_dataclass


def native_copy(value, memo=None):
    if type(value) in (type(None), bool, int, float, str, bytes):
        return value
    memo = {} if memo is None else memo
    identity = id(value)
    if identity in memo:
        return memo[identity]
    if type(value) is dict:
        result={};memo[identity]=result
        for k,v in value.items():result[native_copy(k,memo)]=native_copy(v,memo)
    elif type(value) is list:
        result=[];memo[identity]=result
        result.extend(native_copy(v,memo) for v in value)
    elif type(value) is set:
        result=set();memo[identity]=result
        result.update(native_copy(v,memo) for v in value)
    elif type(value) is tuple:
        result=tuple(native_copy(v,memo) for v in value);memo[identity]=result
    elif is_dataclass(value):
        result=object.__new__(type(value));memo[identity]=result
        for f in fields(value):object.__setattr__(result,f.name,native_copy(getattr(value,f.name),memo))
    else:
        raise TypeError('UNSUPPORTED_STATE_COPY_TYPE: '+type(value).__name__)
    return result


def clone_qualifier(q):
    clone=object.__new__(type(q))
    memo={id(q):clone}
    clone.__dict__.update(native_copy(vars(q),memo))
    return clone

