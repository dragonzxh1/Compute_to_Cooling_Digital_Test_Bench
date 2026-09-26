# Phase 5R5.2.1R4.3B — Observable progress compatibility

## 1–2. Purpose and accepted R4.3A decision

This is a narrow offline-candidate compatibility change. R4.3A classified S3
and S14 as historical regressions because the frozen public-state acceptance
requires an observable `TRACKING_PROGRESS` before `STEADY_TRACKING`.
Same-sample qualified progress and internal resolution remain physically and
causally valid; they may not suppress that public milestone under the current
contract. C9R's 1.0/3.8 s paired-anchor timing is accepted for this candidate
pending separate specification clarification, not retuned to old 1.2/4.0 s.

## 3–4. Implementation delta: internal resolution versus sampled state

Only `v0_2/examples/phase5_r5_2_1r4_3_startup_engine.py` changes semantics.
The existing `_resolve()` still closes the epoch/watch and establishes the
atomic resolved command/measurement pair on the **actual qualified sample**.
If this epoch has not previously published progress, the same sample now
publishes `TRACKING_PROGRESS` rather than `STEADY_TRACKING`. The next sample
runs the ordinary qualifier logic; it may publish STEADY, a new handoff state,
or INSUFFICIENT_MEASUREMENT according to actual input. An epoch that already
published qualified progress resolves directly to STEADY. The candidate tracks
only the last epoch ID whose progress was published. No new public state,
physical delay, threshold, calibrated timer, or response grace was added.

This is not fake progress: `_resolve()` is reached only after the inherited
measured-motion qualification succeeds. The record on the first resolution
sample has `qualified_progress=true`; its resolved-pair and watch-resolution
events remain timestamped on that same sample.

## 5–6. S3 and S14

Both use the unchanged frozen `DELAY_0_6` trace. The old engine published
SUSPECTED → PROGRESS at 1.0 s → STEADY at 1.2 s. R4.3 published SUSPECTED →
STEADY at 1.0 s, with real qualified progress but no public PROGRESS sample.
R4.3B now publishes SUSPECTED → PROGRESS at 1.0 s → STEADY at 1.2 s. On the
1.0 s PROGRESS record, qualified progress is true, the unresolved watch is
closed, and the resolved pair is already established. Neither historical
input, exact timing oracle, nor tracking profile was changed.

| Case | Old sampled order | R4.3 sampled order | R4.3B sampled order | Internal pair event |
|---|---|---|---|---|
| S3 | SUSPECTED → PROGRESS → STEADY | SUSPECTED → STEADY | SUSPECTED → PROGRESS → STEADY | 1.0 s, unchanged |
| S14 | same | same omission | restored | 1.0 s, unchanged |

## 7. C9R anchor behavior and proposed clarification

The in-domain C9R paired command anchors remain A=0.35 at 0.0 s, B=0.51 at
1.0 s, and C=0.67 at 3.8 s. B/C are **not** delayed to the old R1a 1.2/4.0 s.
They are established at the qualified resolution sample even though the
published state on that sample is PROGRESS. The command/measurement components
still come from one causal observation.

Proposed specification clarification for separate review only:

> A resolved anchor pair advances on the first qualified sample that also
> satisfies resolution conditions. The prior engine's later anchor timestamps
> are not normative unless a case explicitly preregisters them. An externally
> observable progress milestone may precede the steady publication while the
> internal anchor is already resolved.

No frozen contract, C9R registration, or old expected output is amended here.

## 8–9. Startup, C and S regression

The original 46 startup-focused cases and four new compatibility cases pass:
**50/50**. New cases check both S3/S14 same-sample resolution and the next
sample after a command withdrawal or invalid measurement. All **11/11** valid
historical C acceptance groups and **17/17** historical S acceptance groups
pass against R4.3B. Original C9 remains out of domain, not a passing case.
The 14 adapted historical invariants also remain true. These are candidate
regressions, not full P1–P20 historical qualification.

R41-7's original R4.1 engine still fails its historical expected-direction
condition. The same unchanged R41-7 input under R4.3B passes: the recovery
creates a negative-direction epoch without retroactive progress. The old
failure is not hidden or recast as an old-engine pass.

## 10–12. Intervening events, watch/evidence and anchors

After S3's 1.0 s qualified PROGRESS publication, a 1.2 s material command
withdrawal produces `HANDOFF_PENDING`, **not** a forced STEADY or same-sample
fault. A 1.2 s invalid measurement produces `INSUFFICIENT_MEASUREMENT`; the
1.0 s resolved-pair event remains intact. Ordinary S3/S14 next samples become
STEADY. Thus the compatibility step does not blindly queue a steady state.

Separate startup diagnostics preserve the previous R4.3 rules. Withdrawal
before valid fault evidence cancels the old watch; a later sustained command
starts a new watch at its own time. After one valid fault-evidence sample,
withdrawal pauses the direction but the evidence count stays at 1 and the
watch still starts at 0.0 s. Reissue does not confirm on that same sample;
continued stuck demand can confirm later. No old evidence is sanitized by the
new PROGRESS publication. C9R anchor values/timestamps and matched-pair
semantics remain unchanged.

## 13–14. Prefix causality and determinism

Every prefix of the S/C/C9R/R41-7 and two new intervening-event traces has
the same earlier published records as its full replay. In particular, future
invalidity or command withdrawal does not retroactively remove the published
1.0 s progress state. Ten complete runs each of S3, S14, C9R, R41-7, and the
two intervening-event traces have identical output hashes per case. The
machine evidence records every hash, not only the summary verdict.

## 15–17. P-history limitation, production boundary, gate

P15 remains a deterministic reconstruction **candidate**. The other 19 P
cases remain partially recovered, with no frozen executable P-specific
history. No P case is declared a formal historical PASS/FAIL. Hence even with
the narrow compatibility gate passing, **full historical validation and
production readiness cannot be claimed**.

The frozen profile, Contract 15A, and all R4-registered production-source
hashes match. Production Safety, controller, plant, and actuator were not
changed; no R5.3 production port, Phase 6, Git commit, or push occurred.
Verification was performed against the offline numerical candidate only.

`R4_3B_GATE = OBSERVABLE_PROGRESS_COMPATIBILITY_RESTORED`.

Next recommendation: `P_HISTORY_RECOVERY_POLICY_AND_CANDIDATE_FREEZE_REVIEW`.
Do not begin production reintegration before separate review and complete
historical input coverage.
