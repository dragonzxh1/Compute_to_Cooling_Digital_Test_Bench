# Phase 5R5.2.1R4.1 — Deferred Demand and Measurement Recovery (blocked candidate)

This is an **offline development semantic candidate**, not a production Safety change or OEM/NVIDIA/GB300/hardware validation. The [pre-registration](phase5_r5_2_1r4_1_deferred_demand_recovery_registration.json) was fixed before changing the R4 candidate. The [machine-readable rules](phase5_r5_2_1r4_1_deferred_demand_recovery_semantics.json) and [evidence](phase5_r5_2_1r4_1_deferred_demand_recovery_evidence.json) contain the detailed source hashes and results.

## 1–3. R4 stop, C11 defect, demand versus measurement

R4 removed TUNE-01's paired-reference false confirmation but missed historical C11. The command became material during invalid measurement at 0.4 s. At 1.2 s valid measurement returned without a new command, so R4 never opened the obligation. Existence of command demand and sufficiency of measurement to judge response are separate facts.

## 4–6. Deferred demand, first timestamp, insufficient measurement

`DeferredObservableDemand` records the first observable command timestamp, current signed net demand, resolved pair, direction, prior valid suspicion/watch, and source command. It is bookkeeping, **not a seventh state**. Invalid samples remain `INSUFFICIENT_MEASUREMENT`, never fabricate progress or non-response, and never advance either reference pair. Same-direction updates preserve the first observable timestamp.

## 7–10. Recovery trigger, grace, and motion credit

The first valid measurement is an evaluation event even with no new PLC command. If deferred demand remains material, the candidate opens a paired epoch using the preserved first-observable time, not the recovery time. It evaluates the recovered measurement against the preserved pair **before** any checkpoint refresh. Thus real motion during outage can be credited, while recovery grants no new full response window.

## 11–14. Pairs, cancellation, prior evidence, reversal

The R4 resolved-anchor and progress-checkpoint pairs remain separate and atomic. A deferred-only demand that returns below the frozen material threshold with no prior valid non-response evidence cancels without fault. Existing valid suspicion/watch evidence is not erased by invalidity or cancellation. During invalidity, a material reversal updates directional deferred context without inventing movement or clearing valid evidence; recovery reevaluates the current direction.

## 15–16. C11 and R41-1–R41-8

C11 again reaches SUSPECTED at 1.2 s and CONFIRMED at 1.8 s; its first observable demand is 0.4 s. The mini-suite result is **7 PASS / 1 FAIL**. R41-7 fails: an invalid-measurement reversal is logged, but at recovery the pre-loss positive-direction epoch is not replaced. The current negative demand is never evaluated, and the stuck actuator remains HANDOFF_PENDING. R41-1 through R41-6 and R41-8 pass. The TUNE-01 trace is a reconstructed development prefix, not the original failed production capture.

## 17–20. P1–P20, C/S history, invariants

Full validation stopped at the R41-7 mini-suite failure. Therefore P1–P20, S1–S16 plus variant, complete C acceptance, prefix causality, repeatability, and the full invariant set are **not claimed to pass**. An exploratory unchanged C9R comparison (not a formal full regression) also found that the frozen R1a A→B→C anchor times are 0, 1.2, and 4.0 s, while R4 and R4.1 both produce 0, 1.0, and 3.8 s. Its values remain 0.35, 0.51, and 0.67. This timing difference predates R4.1 and would require separate review. Original C9 remains historically invalid/out of profile domain.

## 21–24. Frozen authorities, compatibility, limitations, gate

The R5.2.2 profile, Contract 15A, R2R state-to-Safety mapping, and all registered production behavior sources remain unchanged. No new numeric tracking calibration parameter, Safety state, or reason code was added. The six internal state names are unchanged, so the mapping remains applicable in principle, but no production port is authorized. No figure was generated because full validation was not reached. The gate is `MEASUREMENT_RECOVERY_STILL_MASKS_SILENT_FAULT`; work stops for user review. No Git commit/push, R5.3R-B, R5.4, final feedback baseline, or Phase 6.
