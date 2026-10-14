"""Explicit SUT constructor selection under already-verified formal authority.

No lifecycle math, read-only observer, comparison rule or assertion is changed.
The old integration_bindings module remains development-only and is not called.
"""
import importlib
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


@contextmanager
def sut_bindings():
    from .runtime_admission import admit
    admit()
    from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
    modules = [importlib.import_module("v0_2.tests.tools.m1_engine_v3." + name)
               for name in ("selfcheck", "adapters", "replay_stream", "test_projection", "test_state_copy")]
    constructed = []
    def factory(*args, **kwargs):
        value = SplitEngine(*args, **kwargs)
        constructed.append({"class": type(value).__module__ + "." + type(value).__name__,
                            "post_module": value.post.__module__})
        return value
    with ExitStack() as stack:
        for module in modules:
            stack.enter_context(patch.object(module, "SplitEngine", factory))
        yield constructed
