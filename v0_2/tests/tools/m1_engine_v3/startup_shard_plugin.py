"""Versioned one-node collection guard; original test body/source unchanged."""
import os
from pathlib import Path
from .startup_plugin import pytest_addoption, pytest_runtest_setup, pytest_runtest_teardown
from .adapters import StartupSplitAdapter


def pytest_collection_modifyitems(items):
    expected=os.environ.get('C2C_STARTUP_NODE_ID')
    if not expected or len(items)!=1 or items[0].nodeid!=expected:
        raise RuntimeError('STARTUP_SHARD_COLLECTION_INTEGRITY')
    if Path(items[0].module.__file__).name!='test_phase5_r5_2_1r4_3_startup.py':
        raise RuntimeError('STARTUP_SHARD_SOURCE_INTEGRITY')
    items[0].module.StartupTrackingQualifier=StartupSplitAdapter
