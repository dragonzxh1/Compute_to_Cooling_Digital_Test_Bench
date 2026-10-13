# M1 POST publication defect repair: development status

2026-10-13: the human user explicitly authorized GitHub dedicated-branch commits,
pushes and isolated development tests. Branch: codex/m1-post-atomicity-20261013.
This does not authorize formal C3-C, production control, hardware or Phase6.

Baseline run38418429221 completed with exactly 3 AssertionError failures and
1 passing success-path test. Its official ZIP SHA256 is
cd4bb522e2752f246b67e3a7c330fffdc633b4e8faeffcd0ade0451ebe639f33;
all 14 members, raw captures, actual PID6348 Job limits and cleanup were read back.
Original source commit3406da2ff71c119874135dd90016ef2987a2e297 is preserved.

New v4 driver inherits frozen v3 PRE/Safety/PLC/math. Only POST ordering changes:
prepare projection/history, serialize complete result, and insert completed store
before changing public q/publication/history/commit. Earlier genuine facts remain.
The identical four regression bodies are unchanged. New PASS is not yet claimed.

Baseline preregistration: exactly four named tests, three specific AssertionError
failures (projection, serialization, completed-store rejection), one successful
completion test. Any extra/missing test, ERROR, source drift, environment drift,
PID/Job mismatch or cleanup failure stops execution. A baseline workflow green
means only that the expected defect was reproduced and captured, not that v3
meets the failed no-publication assertions.

The actual interpreter must be externally verified in its Job before release:
CPU25%, process/job1024/2048MiB,480s wall budget. All old Build005 source/input
bindings remain unchanged. Every new revision has a new source/control hash;
failure evidence is never overwritten or retrospectively upgraded.

Next: execute v4 against the identical assertions, then perform affected and fresh
full-development validation plus install/use checks. These four tests alone do
not prove arbitrary OS interruptions or durable crash recovery; T09 remains hold.
