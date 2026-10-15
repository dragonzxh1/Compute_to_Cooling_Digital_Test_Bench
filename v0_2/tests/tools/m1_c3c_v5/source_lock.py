"""Explicit formal source lock; no call to a sealed development-only entry."""
import json
from pathlib import Path
from .authority import SCOPE, require
from .runtime_admission import admit, package


def create():
    checked = admit()
    _, data = package()
    from v0_2.tests.tools.m1_engine_v3.common import guard
    guard()  # Original document/reference identity checks still apply.
    return {"scope": SCOPE, "source_raw_hashes": data["source_raw_sha256"],
            "execution_identity": checked["execution_identity"]}


def verify(path):
    lock = json.loads(Path(path).read_bytes())
    expected = create()
    require(lock == expected, "C3C_FROZEN_SOURCE_LOCK_DRIFT")
    return lock
