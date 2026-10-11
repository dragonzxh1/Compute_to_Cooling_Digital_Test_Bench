"""Plain boundary marks; no decorators, tracing, context managers or FFI."""
import hashlib
import json
import math
import os
import time
from pathlib import Path

from .admission import ROOT, admit


class Progress:
    def __init__(self, path):
        self.environment_sha256 = admit()
        self.path = Path(path).resolve()
        if not self.path.is_relative_to(ROOT / "artifacts/liquid-recovery-v1"):
            raise ValueError("PROGRESS_ARTIFACT_SCOPE_DENIED")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("xb")
        self.sequence = 0
        self.bytes = 0
        self.source_inventory_sha256 = hashlib.sha256(
            (ROOT / "v0_2/tests/tools/liquid_recovery_v1/source_inventory.json").read_bytes()
        ).hexdigest()

    def mark(self, event, phase, **fields):
        if event not in ("BEGIN", "END", "ERROR") or type(phase) is not str:
            raise ValueError("BAD_PROGRESS_EVENT")
        for name, value in fields.items():
            if type(name) is not str or type(value) not in (str, int, float, bool, type(None)):
                raise ValueError("PROGRESS_PRIMITIVE_METADATA_ONLY")
            if name in {"sequence", "pid", "utc_ns", "monotonic_ns", "event", "phase",
                        "environment_sha256", "source_inventory_sha256"}:
                raise ValueError("PROGRESS_RESERVED_IDENTITY_FIELD")
            if type(value) is float and not math.isfinite(value):
                raise ValueError("PROGRESS_NONFINITE_METADATA")
        record = {
            "sequence": self.sequence, "pid": os.getpid(), "utc_ns": time.time_ns(),
            "monotonic_ns": time.monotonic_ns(), "event": event, "phase": phase,
            "environment_sha256": self.environment_sha256,
            "source_inventory_sha256": self.source_inventory_sha256, **fields,
        }
        raw = json.dumps(record, sort_keys=True, allow_nan=False).encode() + b"\n"
        if len(raw) > 8192 or self.bytes + len(raw) > 2 * 1024 * 1024:
            raise RuntimeError("PROGRESS_BUDGET_STOP_NOT_PASS")
        self.stream.write(raw)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.bytes += len(raw)
        self.sequence += 1

    def close(self):
        self.stream.close()
