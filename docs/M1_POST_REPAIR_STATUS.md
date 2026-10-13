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
The identical four regression bodies are unchanged (RAW SHA256
d3e7990569fed30424fd66c5d4f21c5b358c4b571be9afaaaf7bc1d5d7850b1f).
Repair run38419427761:4/4 PASS/0FAIL/0ERROR, official ZIP
d40201c872f2a0ed85412e34547ee220d62833705ed98fd5177202389da1b807.

Affected run38420108200:27/27 PASS/0FAIL/0ERROR (the four new assertions plus
23 unchanged projection/state-copy/infrastructure tests). The versioned adapter
records 16 actual v4 constructor bindings, never changing reference/expectations.
Source4939b64b29a7434874f19fc0945255789bad575b; control manifest
8b73d58387fabb3c45e4bca8f32cc6c9e2e421624cc6ae6741803bb749632e66.
Official ZIP16c79c274d15ec47331738b2f83b97fe1e38b9859c2bd1865ff542d80b82e106
was independently read back:15 members,4 raw captures, actualPID7384 in bounded
Job,CPU25%,process/job1024/2048MiB,exit0/cleanup complete/active0; before/after
environment identities identical. Result RAW SHA256
173bc73da005ba4665b12d73655d2c4c537c56f8eef893af71d4230ebc2823f7.

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

Status: M1-DEF-POST-001 tested failure paths are repaired and affected development
regression passed. This is not full candidate release acceptance. Next: fresh
complete-development campaign against v4, installation/package/use verification,
and final source/input/environment/artifact readback. Do not borrow Build005 PASS.
The fresh full campaign control is now versioned under m1_campaign_v4. Source-
closure admission retains every old check and additionally binds the V4 driver,
worker, runtime action and workflow. All reference/split/selector/repeat/Startup/
schema/final execution is fresh. Actual SUT constructor identity is captured in
each executing worker; frozen-V3 parent byte identity is labelled separately.

No arbitrary OS interruptions/durable crash recovery qualification is claimed;
T09 remains hold; full P history unavailable; real hardware calibration required.

Full fresh development run38423165745 is LIVE, not accepted complete yet.
Execution source717a98dd89ece8d3b6944a80727b32f20a311b8b;
control manifesteef95f5ace0e33e862b098087cc7030718f73c2099b60695251f8feaf4682446;
runner138ad299058888d59500416150f7ff0228f04944e7830f35f5db8d0b4e774aef.
Initial GitHub snapshot: prepare succeeded,9/10 fresh reference groups completed,
one still running, no failed job. This is progress only; no final PASS claim.
Continue following this exact run; never restart because an observation expires.
