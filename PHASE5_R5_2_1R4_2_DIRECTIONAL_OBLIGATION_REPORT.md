# R4.2 directional obligation repair — incomplete qualification

Status: **BLOCKED_INHERITED_STARTUP_BASELINE_GAP**. This is an offline candidate.
No production port, final baseline freeze, or hardware qualification is claimed.

The original R4.1 mini-suite was reproduced: 7 passed and R41-7 failed. The new
candidate preserves unresolved watch time and prior evidence while recording a
new material net-demand direction during an outage. Recovery evaluates that
direction against the preserved paired references. Expected motion starts no
earlier than the actual reversal command; recovery itself grants no fresh grace.

Candidate verification command:

```
.venv\Scripts\python.exe -m pytest v0_2/tests/control/test_phase5_r5_2_1r4_2_directional_obligation.py -q
```

Result: **17 passed**. Includes the unchanged R41 assertions, healthy reversals,
partial retreat, repeated reversals, deferred-only reversal, retained suspicion,
repeatability and prefix causality. The original suspicion control incorrectly
expected a nonzero confirmation-evidence count at 1.2 seconds. Its unchanged
input remains as a suspected-state/zero-count control; a separate later-outage
control proves preservation of a count of one. No profile threshold was changed.

R41-7 now becomes SUSPECTED at 1.2 seconds and CONFIRMED at 2.0 seconds. The watch
still starts at 0.2 seconds; the directional obligation starts at 0.6 seconds.

Expanded historical probing found that S2, S4, S6, S8_stuck, S12, S15, S16 and
S16_variant still lack required confirmation. R4.1 exhibits the same startup
problem. The paired engine only creates an initial resolved pair when command
and valid measurement already agree within tolerance. Without that pair, net
demand remains undefined, no epoch opens, and valid samples can be reported as
STEADY_TRACKING indefinitely despite a stuck actuator.

Reproduce the comparison and source hashes:

```
.venv\Scripts\python.exe -m v0_2.examples.phase5_r5_2_1r4_2_validation
```

Machine evidence: `phase5_r5_2_1r4_2_directional_obligation_evidence.json`.
This comparison is not a substitute for full S/C/P acceptance. Historical
R4/R4.1 files and their known-failing test remain unchanged as frozen evidence.

Next required work: define startup tracking without falsely declaring a resolved
command/measurement baseline, retain actual released-measurement provenance,
then replay the full historical gates and the new reversal controls. Also audit
outage cancellation/reintroduction and direction changes after recovery before
considering any production integration. The thread goal remains unfinished.
