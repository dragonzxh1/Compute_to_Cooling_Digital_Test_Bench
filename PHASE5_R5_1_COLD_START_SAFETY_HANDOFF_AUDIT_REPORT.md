# Phase 5R5.1 — Cold-start Safety handoff audit

Status: `NORMAL_HANDOFF_MISCLASSIFIED_AS_DEGRADED` (diagnostic gate, not a Safety change or final feedback baseline).

## Purpose and frozen scope

R5 found a directional outer PI candidate that regulates both capture directions but produced a 0.4 s cold-start `DEGRADED / ACTUATOR_TRACKING_PENDING` event. This audit asks whether the pump actually fails or whether the Safety predicate flags the expected open-loop-to-closed-loop handoff. The frozen controller is Kp=4500, Ki_hot=110, Ki_cold=130, Kd=0, blend half-width=0.1 K, one continuous integral state and unchanged anti-windup. Target, inner_b, physical plant, actuator dynamics, sensor/PLC clocks, Safety thresholds/state machine, command ownership and provenance are unchanged. The warm and cold R5 runs remain tuning evidence, not independent validation.

Registration: `phase5_r5_1_safety_handoff_audit_registration.json`, SHA-256 `a6564f7425ab1cff533944364048812a1ae2ff9d9a4bd5d5bd890e3e5a32e8da`. Source R5 registration SHA-256 `61f48d159f208ce4ba8a7e5e958ccad31b659e24bfee69f199133fdf2cf52791`; source R5 evidence SHA-256 `1707b3b854291e5eeb29a5ec10ad665ddc81dbc3f9f42a9ec8dededc84efc171`. The preparation is the verified 120 W/device, 180 s open-loop state, normalized to t=0, with no controller prehistory or integrator warm start. Warm uses 0.3 pump speed; cold uses 0.9.

## Nominal handoff

The cold first PLC command at t=0 is 0.648, 0.252 below the prepared speed 0.9. The frozen command delay is 0.2 s; a physical response is first permitted at t=0.2 s and appears at the next recorded physics event, t=0.4 s. The actual and released measured pump echoes both move from 0.9 to 0.86 at t=0.4 s. This -0.04 change over 0.2 s exactly reaches the frozen 0.2 fraction/s ramp limit; the offline expected-response model and actual speed agree to the recorded numerical precision (maximum absolute difference 0). The measured tracking error falls from 0.252 at t=0 to about 0.157 at 0.4 s and 0.073 at 0.6 s. The first 5 s contain 26 native scheduled event rows; the complete nominal run continues to 180 s.

| Metric | Warm nominal | Cold nominal |
|---|---:|---:|
| Prepared pump speed | 0.300 | 0.900 |
| First PLC command | 0.300 | 0.648 |
| First-command delta | 0 | -0.252 |
| First possible response after a material command | 0.4 s (material command at 0.2 s) | 0.2 s |
| First actual response | 0.6 s | 0.4 s |
| First measured response | 0.6 s | 0.4 s |
| Peak actual tracking error in first 5 s | 0.0302 | 0.252 |
| Error starts shrinking | Not applicable to zero first-command delta | 0.4 s |
| DEGRADED duration | 0 s | 0.4 s |
| Final Safety state at 180 s | NORMAL | NORMAL |

Cold Safety transitions are exactly t=0.2 s `DEGRADED / ACTUATOR_TRACKING_PENDING`, t=0.6 s `FF_DISABLED / RECOVERY_QUALIFICATION`, and t=2.6 s `NORMAL`. The warm case stays `FF_DISABLED` until t=2.0 s, then `NORMAL`. No cold thermal, flow or pressure Safety threshold is violated in the first 5 s: maximum released die temperature 312.802 K versus derate 335 K; minimum released flow 0.211 kg/s versus minimum 0.02 kg/s; maximum released DP 42,525 Pa versus fault limit 60,000 Pa. No nominal actuator saturation/fault is observed.

## Why the current Safety predicate trips

`SafetySupervisor.evaluate` tests `abs(commanded_speed - measured.pump_speed) > 0.15` on a qualified released pump measurement. At t=0.2 s, command=0.648 while measured echo remains 0.9, so the difference is 0.252 and the pending branch sets `DEGRADED`. A mismatch persisting 2.0 s would become latched `FAULT`; instead the difference drops below 0.15 by t=0.6 s and the existing 5-sample / 2-s dwell recovery path passes through `FF_DISABLED` to `NORMAL` at 2.6 s. This predicate compares the newest command to a pump that still obeys the 0.2-s command delay; it does not explicitly account for handoff timing, first-order lag, ramp or sample cadence. Local measurement release delay is 0, but the 0.2-s sampling/event cadence makes the first recorded movement t=0.4 s. At t=0.2 s the actuator cannot physically meet the 0.15 tolerance from the new command under the frozen dynamics. This is a semantic mismatch in this numerical fixture, not proof of a device defect.

## Nominal versus stuck

The fault uses the existing `Disturbance(time_ns=0, pump_stuck=True)` mechanism with the same cold preparation and R5 controller. The existing fixture exposes `pump_fault=True` and `pump_ready=False` in the released measurement immediately; Safety enters latched `FAULT / ACTUATOR_FAULT_MEASURED` at t=0 and commands its frozen 0.5 fault speed. The stuck pump remains at 0.9; no actual or measured response occurs. No Safety bypass was introduced.

| Signal | Cold nominal | Cold stuck | Distinguishable with permitted measurements? |
|---|---|---|---|
| Released pump response | 0.9 → 0.86 at 0.4 s; -0.1301 by 5 s | Remains 0.9 | Yes |
| Measured tracking-error trend | Falls by 0.4 s; below 0.15 by 0.6 s | Does not shrink | Yes |
| Released flow / DP | Change with pump response | Stay at approximately 0.246 kg/s / 42,525 Pa | Yes |
| Safety state | DEGRADED 0.2–0.6 s, then recovery | Latched FAULT from t=0 | Yes |
| Time to recovery | NORMAL at 2.6 s | No automatic recovery by 180 s | Yes |

`MEASURED_ONLY_SEPARATION_PASS`: using only released pump echo and PLC command/timestamps, nominal speed falls by 0.13005 in the first 5 s while stuck speed falls by exactly 0; nominal measured error first shrinks at 0.4 s whereas stuck never shrinks. The released pump-fault bit gives additional, immediate distinction. Raw ACTUAL is used only by the offline audit, not by this measured-only judgment.

## Ownership, causality, conservation, repeatability

Every first-5-s event has complete intent → accepted target → Safety envelope → PLC cycle → PLC command → actuator state → released measurement → hydraulic-solution lineage. `Safety` produces envelopes only, PLC remains the sole typed `ActuatorCommand` producer, and the actuator consumes PLC commands. The auditor runs only after the controlled loop returns and cannot feed Safety, PLC or outer control; a dedicated test snapshots control output before/after audit. The source SHA guards cover unchanged Safety and actuator modules.

The 180-s warm, cold and stuck runs conserve mass and energy within numerical residuals. Maximum mass residual is 2.78e-17 kg/s; maximum absolute energy residual is 6.10e-10 J. Cold nominal and cold stuck each reproduce the first-5-s diagnostic result hash and exact Safety/first-response timings in 10/10 runs. The nominal expected-response envelope is satisfied at all recorded early events. The stuck trajectory is intentionally outside that nominal envelope.

## Limits and gate

This is numerical-fixture evidence, not OEM hardware validation. The available stuck fixture advertises its own measured fault status; this audit also demonstrates trajectory separation, but does **not** prove that an unannounced or intermittent fault can be detected with the same timing. No qualified separate excessive-delay/tracking-failure fixture was found: `EXCESSIVE_TRACKING_FAULT_FIXTURE_NOT_AVAILABLE`. The first-5-s trace is complete at the fixture's native 0.2-s event cadence, not continuous-time telemetry. No independent holdout validation was run. A future Safety revision would need to retain measurable fault discrimination and must not simply ignore tracking for a fixed grace period.

Gate: `NORMAL_HANDOFF_MISCLASSIFIED_AS_DEGRADED`. In plain language: the pump takes a big new command, waits and moves exactly as the model says it should; the existing alarm labels that normal short wait as degraded. A truly stuck pump still looks different to the available measured sensors and remains in FAULT. This report recommends **review of Safety semantics in a separate authorized phase**, not a change here. R5 remains a candidate, and Phase 6 is not authorized.

Regression: R5.1 dedicated tests, complete V0.2 suite (including R5, R4.2/R4.1/R4, R3, R2.2/R2.1/R2, R1, Phase 5 and Phase 4.1/4/3), and separate V0.1 suite passed. Ruff `--no-cache` passed and `git diff --check` passed. The two pytest roots must be invoked separately because both contain a `test_hydraulics.py` module name; collecting them in one invocation produces a pytest import-name collision, not a test failure. Ruff's persistent cache also produced an internal package-root panic in one combined lint attempt; `--no-cache` completed cleanly. No historical artifact was edited.

Artifacts: `phase5_r5_1_safety_handoff_audit_evidence.json`, `docs/results/phase5_r5_1_cold_start_safety_handoff.png`, and the R5.1-only audit runner/tests.
