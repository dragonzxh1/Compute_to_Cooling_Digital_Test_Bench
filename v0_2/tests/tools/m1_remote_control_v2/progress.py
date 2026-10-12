"""Plain boundary marks only; no decorators, context-manager/FFI/watchdog layer."""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
_STREAM = None
_BYTES = 0
_SEQUENCE = 0
_CONTEXT = {}


def initialize(path, **context):
    global _STREAM
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'artifacts') or _STREAM is not None:
        raise ValueError('M1_PROGRESS_FRESH_ARTIFACT_REQUIRED')
    _STREAM = path.open('xb')
    _CONTEXT.update(context)


def mark(event, phase, **context):
    global _BYTES, _SEQUENCE
    if _STREAM is None:
        # Pure unit/public library helpers have no execution authority here;
        # the admitted worker always initializes before model calls.
        return
    data = {**_CONTEXT, **context}
    if any(type(key) is not str or type(value) not in (str, int, bool, type(None))
           for key, value in data.items()):
        raise ValueError('M1_PROGRESS_METADATA_PRIMITIVES_ONLY')
    raw = json.dumps({'event': event, 'phase': phase, 'sequence': _SEQUENCE,
                      'pid': os.getpid(), 'utc_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(),
                      'execution_manifest_raw_sha256': os.environ.get('C2C_M1_EXECUTION_MANIFEST_SHA256'),
                      **data}, sort_keys=True, allow_nan=False).encode() + b'\n'
    if len(raw) > 8192 or _BYTES + len(raw) > 32 * 1024 * 1024:
        raise RuntimeError('M1_DIAGNOSTIC_LOG_BUDGET_STOP_NOT_BEHAVIORAL_FAIL')
    _STREAM.write(raw)
    _STREAM.flush()
    os.fsync(_STREAM.fileno())
    _BYTES += len(raw)
    _SEQUENCE += 1


def close():
    global _STREAM
    if _STREAM is not None:
        _STREAM.close()
        _STREAM = None
