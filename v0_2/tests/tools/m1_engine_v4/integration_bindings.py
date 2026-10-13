"""Versioned development adapter over unchanged affected test bodies.

Only their constructor binding is selected; reference math, inputs, comparator,
test assertions and byte identities remain unchanged. Never used for formal C3-C.
"""
import importlib
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


@contextmanager
def sut_bindings():
    from .engine import SplitEngine
    modules = [importlib.import_module("v0_2.tests.tools.m1_engine_v3." + name)
               for name in ("selfcheck", "adapters", "test_projection", "test_state_copy")]
    constructed = []

    def factory(*args, **kwargs):
        instance = SplitEngine(*args, **kwargs)
        constructed.append({"class": type(instance).__module__ + "." + type(instance).__name__,
                            "post_module": instance.post.__module__})
        return instance

    with ExitStack() as stack:
        for module in modules:
            stack.enter_context(patch.object(module, "SplitEngine", factory))
        yield constructed
