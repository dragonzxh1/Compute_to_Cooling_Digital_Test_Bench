# M1-DEF-POST-001 development repair workspace

Status: BASELINE_DEFECT_REPRODUCED; v4 POST repair 4/4 and affected regression27/27
passed in independently verified hosted Windows runs38419427761/38420108200.
No candidate freeze, full requalification or production readiness is claimed.

The failure is a transaction state corruption pattern: v3 commits public state
before projection validation, completed-result serialization and completed-store
insertion have succeeded. PRE/Safety/issued PLC facts must survive failure; an
unfinished POST must not become a fresh successful publication. This is mandatory
under C2-R1 complete-only and C3-A CMP-C05, not a relaxable comparison criterion.

`test_post_atomicity.py` uses unchanged ST-15 inputs and unchanged v3 helpers.
Its three failure assertions are the same for baseline and repair. It also tests
ordinary completion and idempotent result lookup. A passing ordinary completion
test cannot substitute for the failure-path tests.

On a separately authorized isolated development runner ONLY:

```powershell
$env:M1_POST_TEST_TARGET='v3'
python -m unittest v0_2.tests.tools.m1_engine_v4.test_post_atomicity -v
```

The baseline must expose actual failures of the no-new-publication assertions.
Preserve stdout/stderr, exact exit code, input/source/environment hashes and each
test identity. Then implement a new v4 driver, and run the identical assertions
with `M1_POST_TEST_TARGET=v4`. Do not alter v3 or frozen tests to obtain PASS.

Do not run this Python command on the user's hard-hanging workstation. The user
explicitly authorized dedicated-branch GitHub submission, push and development
testing on 2026-10-13. `run_remote.ps1` and `atomicity_worker.py` provide source-
bound, actual-PID/Job-verified hosted Windows execution. Baseline acceptance is
BASELINE_DEFECT_REPRODUCED, not a relabelling of the failed assertions as PASS.
No formal C3-C, hardware or production permission is implied.

Future verification must cover a fresh complete software development campaign
and installation/use checks before release delivery. Universal OS
crash/hardware transaction atomicity is still not asserted by these software tests.
