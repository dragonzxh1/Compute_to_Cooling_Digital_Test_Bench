# Phase 5R5.2 — Silent actuator tracking fault qualification

Gate: `MEASURED_ONLY_SILENT_TRACKING_FAULT_SEPARATION_PASS` — **diagnostic evidence only**. No production Safety, controller, actuator or sensor behavior was changed. This does not freeze the R5 feedback candidate and does not authorize Phase 6.

## Why this audit exists and what stayed frozen

R5.1 showed that the ordinary cold handoff was labeled `DEGRADED` before the pump could physically follow the new PLC command. Its stuck fixture, however, also raised an explicit measured fault bit. R5.2 removes that easy signal from the test: it asks whether released speed, command history and timestamps are enough to distinguish a normally delayed pump from one that silently fails to move.

The controller remains Kp=4500, Ki_hot=110, Ki_cold=130, Kd=0, blend half-width=0.1 K, with one integral state and unchanged anti-windup. The target, inner_b, physical plant, all normal actuator settings (0.2-s delay, 1-s lag, 0.2 fraction/s ramp, 0.3–0.9 bounds), sensor/PLC timing, Safety source and thresholds, command ownership and provenance remain frozen. Cold preparation reuses the verified 120 W/device, 0.9-speed, 180-s open-loop state with no controller prehistory or integrator warm start. Every physical case runs for 180 s, and every scheduled event in the first 10 s is retained.

Registration SHA-256: `ff23daf0708e54235a4127b4b0559115f63e839b8f61ebb43de7034bc99d8878`. Source R5.1 registration SHA-256: `a6564f7425ab1cff533944364048812a1ae2ff9d9a4bd5d5bd890e3e5a32e8da`; source R5.1 evidence SHA-256: `624d082f1ae19ca5433a365b68a16049091989caa7fb79ddbfe535676b3648f7`.

## Diagnostic-only fixtures and information boundary

The silent-stuck fixture subclasses the actuator only inside the R5.2 run and holds physical speed at 0.9 while continuing to accept ordinary typed PLC commands. It leaves `fault_stuck=False`; all released `pump_fault` measurements are false and pump-ready status remains healthy. It is a physical non-response, not a failed sensor. Delay fixtures only defer internal command due times to 0.6, 1.0 or 2.0 s. Two sluggish fixtures reduce only the physical response to ramp/tau pairs 0.1 fraction/s and 2 s, or 0.05 fraction/s and 4 s. All are tagged `NUMERICAL_TEST_FIXTURE / FAULT_INJECTION / NOT_OEM`; none changes the published nominal actuator configuration or production source.

The read-only online auditor accepts a typed whitelist observation: current/previous PLC command and timestamp, released pump speed and quality/age/timestamps, measured DP/flow/temperature, and current Safety state/reasons. **There is no pre-takeover PLC command history:** the first previous-command field is `null`, and the initial material step is assessed against the already released measured pump speed. It has **no** raw ACTUAL speed, actuator internals, fault identity, scenario label, explicit pump-fault bit or future sample. A source/API boundary test and prefix-by-prefix replay test enforce that each diagnostic label is made from information available at that timestamp. The auditor never feeds control, PLC or Safety. An output snapshot before/after audit is identical.

The pre-registered material command threshold is 0.15 speed fraction, below the historical 0.252 cold command step. The diagnostic reference computes expected displacement from the frozen delay, lag and ramp; it suspects insufficient measured progress only after the response window opens, and confirms only after the registered displacement deficit persists for two qualified samples. Once this **initial handoff** has demonstrated sufficient directed progress, it is qualified rather than continually re-judged against its first command. These are diagnostic states, not proposed production Safety states or hardware limits.

## Nominal versus silent stuck

The nominal t=0 PLC command is 0.648 (delta -0.252). The frozen delay permits physical response after 0.2 s; the first released measured movement is at 0.4 s, exactly reproducing R5.1. Its online diagnostic goes `HANDOFF_PENDING → TRACKING_PROGRESS` at 0.4 s and never confirms a fault. The *unchanged* Safety path still runs `DEGRADED` at 0.2 s, `FF_DISABLED` at 0.6 s and `NORMAL` at 2.6 s.

Silent stuck receives the same first command and exposes **no measured fault bit**. Speed, flow and DP remain flat despite the material command. The diagnostic remains pending at 0.2 s, becomes `TRACKING_FAULT_SUSPECTED` at 0.4 s and `TRACKING_FAULT_CONFIRMED` at 1.2 s. Current Safety instead enters `DEGRADED` at 0.2 s and its unchanged measured-tracking failure branch enters latched `FAULT` at 2.2 s. The diagnostic confirms 1.0 s before current Safety in this fixture; this is an audit comparison, not a production timing promise.

| Metric | Nominal | Silent stuck |
|---|---:|---:|
| First command delta | -0.252 | -0.252 |
| First measured speed change | 0.4 s | None in first 10 s |
| Absolute tracking error at 0.2 s | 0.252 | 0.252 |
| Absolute tracking error at 0.4 s | 0.15656 | 0.252 |
| Absolute tracking error at 0.6 s | 0.06724 | 0.252 |
| Measured speed slope at 0.4 s | -0.2 fraction/s | 0 |
| Flow change at 0.4 s | -0.01095 kg/s | 0 |
| DP change at 0.4 s | -3,696 Pa | 0 |
| First diagnostic suspect | None | 0.4 s |
| First diagnostic confirmation | Never | 1.2 s |
| Current Safety outcome | NORMAL after recovery | Latched FAULT at 2.2 s |
| Diagnostic outcome | TRACKING_PROGRESS | TRACKING_FAULT_CONFIRMED |

## Excessive delay and sluggish response

Early delay behavior is initially indistinguishable from nominal; there is no demand to identify a fault at 0.2 s. The table shows what the **pre-registered numerical diagnostic** actually distinguishes, not OEM allowable-delay limits.

| Injected physical delay | First measured response | First suspected | First confirmed | Final diagnostic |
|---:|---:|---:|---:|---|
| Nominal 0.2 s | 0.4 s | — | — | TRACKING_PROGRESS |
| 0.6 s | 0.8 s | 0.4 s | — | TRACKING_PROGRESS from 1.0 s |
| 1.0 s | 1.2 s | 0.4 s | 1.2 s | TRACKING_FAULT_CONFIRMED |
| 2.0 s | 2.2 s | 0.4 s | 1.2 s | TRACKING_FAULT_CONFIRMED |

Current Safety returns to `NORMAL` for the 0.6- and 1.0-s injected delays, but latches `FAULT` for 2.0 s. The 0.1 fraction/s sluggish case shows sufficient progress and is not confirmed; the 0.05 fraction/s case is confirmed at 1.2 s. These cases locate this fixture's evidence boundary; they do not prove any manufacturer fault specification.

## Flow/DP, sensor quality and false-positive/negative results

At 0.4 s, nominal measured flow and DP have fallen, while silent-stuck flow and DP remain at their prepared values. They corroborate the pump-speed distinction, but adding them to the audit did **not** advance any confirmation timestamp. The speed-only and speed+DP+flow results have the same labels and latencies; DP/flow are redundant corroboration here, not a required future Safety dependency.

An existing sensor-quality disturbance invalidates the pump-speed channel: the auditor returns `INSUFFICIENT_MEASUREMENT` throughout and never confirms tracking failure. Current Safety, separately, enters `FAULT / CRITICAL_LOCAL_SENSOR_INVALID` immediately under its frozen rules. A separate **auditor-only** 0.4-s telemetry-withholding replay of the nominal run starts with insufficient measurement, then reaches `TRACKING_PROGRESS` without false confirmation. This replay tests the evidence path's latency handling; it does not simulate a changed production sensor delay or a different Safety response.

| Case | Final diagnostic | False positive? | False negative? | Confirmation latency from t=0 |
|---|---|---|---|---:|
| Nominal cold | TRACKING_PROGRESS | No | N/A | — |
| Silent stuck, no fault bit | TRACKING_FAULT_CONFIRMED | N/A | No | 1.2 s |
| Delay 0.6 s | TRACKING_PROGRESS | N/A | N/A — boundary not a hardware fault label | — |
| Delay 1.0 s | TRACKING_FAULT_CONFIRMED | N/A | N/A — numerical deviation | 1.2 s |
| Delay 2.0 s | TRACKING_FAULT_CONFIRMED | N/A | N/A — numerical deviation | 1.2 s |
| Sluggish 0.1 fraction/s | TRACKING_PROGRESS | N/A | N/A — numerical deviation | — |
| Sluggish 0.05 fraction/s | TRACKING_FAULT_CONFIRMED | N/A | N/A — numerical deviation | 1.2 s |
| Invalid pump-speed measurement | INSUFFICIENT_MEASUREMENT | No confirmed tracking fault | N/A | — |

## Ownership, causality, conservation and repeatability

All actuator commands remain PLC-produced; Safety still produces only envelopes/restrictions. No new command path was added. All released measurements used by the auditor have release timestamps at or before the decision timestamp; a prefix-replay test shows no online label changes when later samples are withheld. The diagnostic-only fixtures change physical response, not command ownership or sensor fault status. All eight 180-s physical runs pass mass/energy conservation, with maximum mass residual 2.78e-17 kg/s and maximum absolute energy residual 5.74e-10 J. First-10-s diagnostic result hashes, transition times and confirmation times match in 10/10 nominal, 10/10 silent-stuck and 10/10 delay-1.0-s repeats.

The first internal run exposed a diagnostic implementation defect: after an initial handoff had already demonstrated valid progress, it could be reclassified against the stale first command later. This was corrected as state-handling logic, **without changing any pre-registered numerical threshold**, and every case was rerun. The initial `NOMINAL_REPRODUCED` check also compared JSON list/tuple reason-code representations incorrectly; that comparison was normalized. A subsequent information-boundary review removed an invalid representation of prepared speed as a prior PLC command; the first prior-command field is now correctly absent and the auditor uses the released measured speed. All cases and repeatability checks were rerun after this correction. None of these issues involved production control or Safety code.

Regression: the complete V0.2 suite passed, covering R5.2/R5.1/R5, R4.2/R4.1/R4, R3, R2.2/R2.1/R2, R1, Phase 5, Phase 4.1/4 and Phase 3. The separate V0.1 suite passed. Ruff `--no-cache` and `git diff --check` passed. The R5.1 registration/evidence and frozen production Safety/actuator hashes match their pre-registered values exactly. The two pytest roots are run separately because they contain duplicate `test_hydraulics.py` module names when collected together.

## Limits and next decision

This proves measured-only discrimination for the registered numerical cases, not hardware performance. The classifier qualifies the **initial handoff only**; it is not a continuous post-handoff fault monitor. The 0.15 material-step rule and progress ratios are audit thresholds, not approved Safety settings. Small command changes, intermittent faults, biased/noisy pump-speed telemetry, simultaneous hydraulic faults and broader sensor-delay behavior remain unqualified. The nominal case is still tuning evidence, not independent holdout validation. A future R5.3 may review Safety semantics against these traces, but must separately design and qualify any production change; a blind fixed grace period is not supported.

Gate: `MEASURED_ONLY_SILENT_TRACKING_FAULT_SEPARATION_PASS`. In plain language: with the fault light disconnected, a healthy pump starts moving when physics allows, while a silently stuck pump stays still. We can tell the difference from measurements without treating the initial wait as a confirmed fault. **STOP for user review.**

Artifacts: `phase5_r5_2_silent_tracking_fault_registration.json`, `phase5_r5_2_silent_tracking_fault_evidence.json`, `docs/results/phase5_r5_2_silent_tracking_fault_qualification.png`, and R5.2-only runner/tests.
