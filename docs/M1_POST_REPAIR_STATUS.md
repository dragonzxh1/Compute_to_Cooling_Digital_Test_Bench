# M1 POST publication defect repair: development status

2026-10-13: the human user explicitly authorized GitHub dedicated-branch commits,
pushes and isolated development tests. Branch: codex/m1-post-atomicity-20261013.
This does not authorize formal C3-C, production control, hardware or Phase6.

Current delivery: source-bound RCA baseline execution harness and four unchanged
regression assertions. No repaired v4 engine or new PASS is claimed yet.

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

Next: independently download/hash/read baseline artifact, confirm the exact
failure witnesses, then implement a versioned v4 POST commit fix and rerun the
same assertions. Complete-development and install/use verification remain ahead.
