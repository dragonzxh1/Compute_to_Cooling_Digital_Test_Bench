# M1 remote v2.1 — split the unit execution budget, not the test semantics

v2 run 38203137214 is preserved as INVALID: native TIMEOUT at CORE_SELF_CHECK,
26 completed tests, last protocol test unfinished, cleanup complete / active 0.
Earlier v1's same 27 tests took 107.469s inside a 120s child, with 116.265s of
logged stage work. Child startup/admission plus host scheduling can exhaust the
remaining margin. This is an execution-budget defect, not an observed assertion
failure or evidence of the original local whole-machine hang's root cause.

v2.1 runs the exact unchanged v2 test bodies in four separate owned children:
12 projection + 3 state-copy + 8 infrastructure + 4 campaign-protocol = 27.
Schema/nine-core identity checks get a separate child. No test is omitted and no
assertion changed. Each test has BEGIN/END logs. CPU 1%, memory 256/512 MiB and
120s per child remain unchanged. The external workflow budget is 45 minutes.

The sealed v2 engine/source manifest is delegated by its exact raw SHA. A new,
separately hashed external control manifest binds the regrouping/launcher files.
Registration and logs distinguish engine manifest from control manifest. External
source checks still occur before/after every child; old Python admission checks
retain their real engine/source/environment verification. No guard is bypassed.

Native failure is recorded BEFORE reading optional Python result.json, so timeout
cannot be obscured by a missing-result ItemNotFoundException. Raw capture remains
durable before gate. Any failure stops this fresh execution without retry.

Then run the same three long traces and terminal prefixes from a fresh start.
All selected-prefix shards/full campaign/formal qualification remain NOT_RUN.
Production / Phase 6 / hardware authority remain unchanged. v1/v2 artifacts,
candidate, profiles, contracts, Safety, fixtures and expectations are immutable.
