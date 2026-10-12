from pathlib import Path
from .adapters import StartupSplitAdapter
from .adapters import STARTUP_DOMAIN_EVENTS
import json
import os
from pathlib import Path


def pytest_addoption(parser):parser.addoption('--m1-domain-log',default=None)


def pytest_runtest_setup(item):
    STARTUP_DOMAIN_EVENTS.clear()


def pytest_runtest_teardown(item):
    destination=item.config.getoption('--m1-domain-log')
    if destination:
        path=Path(destination);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('ab') as f:
            f.write(json.dumps({'nodeid':item.nodeid,'domain_events':STARTUP_DOMAIN_EVENTS},sort_keys=True,allow_nan=False).encode()+b'\n')
            f.flush();os.fsync(f.fileno())


def pytest_collection_modifyitems(items):
    modules={item.module for item in items}
    if len(items)!=50 or any(Path(m.__file__).name!='test_phase5_r5_2_1r4_3_startup.py' for m in modules):
        raise RuntimeError('STARTUP_COLLECTION_INTEGRITY')
    for module in modules:module.StartupTrackingQualifier=StartupSplitAdapter

