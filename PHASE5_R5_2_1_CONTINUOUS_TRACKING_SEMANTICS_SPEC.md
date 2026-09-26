# Phase 5R5.2.1 — continuous actuator-tracking semantics boundary

**Gate: `TRACKING_SEMANTICS_REQUIRE_CALIBRATION_PARAMETERS`.** This is a specification and offline source audit, not a production Safety revision. The registered pre-validation stop condition fired before S1–S16 could be run against a production-portable state machine. No R5.3 retry, final feedback freeze, or Phase 6 work is authorized.

## Motivation, evidence, scope and non-goals

R5 selected the directional PI *candidate* (Kp 4500, Ki_hot 110, Ki_cold 130, Kd 0, 0.1 K blend). R5.1 showed the nominal cold handoff was falsely marked `DEGRADED`. R5.2 showed that its *initial-handoff diagnostic* distinguishes the registered nominal, silent-stuck, delayed and sluggish numerical fixtures from released measurements without a fault bit. The blocked first R5.3 attempt identified the missing continuous semantics; no production file changed.

This phase concerns actuator-command tracking only. It does not design pump-health diagnosis, change controller gains, modify plant/actuator/sensor/PLC/Safety sources, add a top-level Safety state, or claim OEM validation. Safety remains restriction/envelope authority; the PLC remains the only `ActuatorCommand` producer. A future qualifier may consume only PLC command provenance and time, Safety-maintained command history, released measured speed/time/quality, released DP/flow, existing Safety state/timers and a qualified static profile. It may not consume raw ACTUAL, hidden actuator state, fault/scenario identity, future data or true plant state.

## Terminology and epoch fields

The six proposed **internal** statuses are `STEADY_TRACKING`, `HANDOFF_PENDING`, `TRACKING_PROGRESS`, `TRACKING_FAULT_SUSPECTED`, `TRACKING_FAULT_CONFIRMED`, and `INSUFFICIENT_MEASUREMENT`. They are not `SafetyState` values. A tracking epoch is a causal interval assessing response to a qualified material demand. Its proposed record holds `tracking_epoch_id`, start timestamp, anchor and latest commands, anchor measured speed, direction, response window, measurement-quality state, status, progress evidence, suspected/confirmed times and completion reason. An unresolved demand has one original age; ordinary PLC ticks must not restart it.

## Parameter interface and response window

The numerical model has typed `PumpActuatorConfig.command_delay_ns`, `tau_s`, `ramp_per_s`, bounds and `SensorConfig.sample_ns`, `local_delay_ns`, `max_age_ns`. R5.2 registers material delta 0.15, minimum measured response 0.01, suspect expected progress 0.03 and ratio 0.5, confirm expected progress 0.12 and ratio 0.35 for two qualified samples. Its generic initial-step reference is `min(ramp × elapsed_after_delay, step × (1 − exp(−elapsed_after_delay / tau)))`. These are **uncalibrated numerical-fixture values**, not equipment limits.

The earliest fair observation can be expressed symbolically as command time plus qualified actuator delay plus the next sensor sample/release opportunity. That answers *when response could be observable*. It does not answer *how much measured movement must be distinguishable from sensor quantization/noise*, or how a continuously changing/reversing command trajectory should be bounded. The typed sensor profile has no speed-resolution/noise bound; R5.2 does not qualify a continuous progress-loss guard, reversal observability horizon or steady-tracking tolerance. Consequently a latest expected progress/confirmation window for hardware cannot be derived. The missing fields are tagged `CALIBRATION_REQUIRED` in the machine-readable specification; no observed 0.4-, 0.8- or 1.2-second fixture timestamp has been promoted to a universal rule.

Hardware integration must replace profile values after calibration, not rewrite semantic equations. Existing typed fixture values can still support **initial-handoff offline diagnostics**. They cannot certify a continuous production tracker, especially when repeated reversals occur faster than an independently observable response. With only finite-rate released measurements, a functioning actuator and a stuck actuator can produce indistinguishable sample prefixes under some short alternating command demands; a persistent-demand/observability contract is needed before promising bounded detection.

## Partial transition table — not an implementable complete state machine

| Current internal state | Event / evidence | Next state | Timer and epoch behavior | Qualification |
|---|---|---|---|---|
| STEADY_TRACKING | New material demand | HANDOFF_PENDING | Start one epoch | Conceptual; material threshold is fixture-only |
| HANDOFF_PENDING | Qualified directed measured progress | TRACKING_PROGRESS | Keep original epoch age | R5.2 initial handoff only |
| HANDOFF_PENDING | Observable but insufficient progress | TRACKING_FAULT_SUSPECTED | Keep epoch age | R5.2 initial handoff only |
| TRACKING_FAULT_SUSPECTED | Two qualified confirming deficits | TRACKING_FAULT_CONFIRMED | Keep evidence | R5.2 initial handoff only |
| TRACKING_FAULT_SUSPECTED | Qualified progress | TRACKING_PROGRESS | Clear suspicion only on evidence | R5.2 initial handoff only |
| TRACKING_PROGRESS | Tracking resolves | STEADY_TRACKING | Complete epoch | **Missing qualified steady guard** |
| TRACKING_PROGRESS or STEADY_TRACKING | Later progress loss | TRACKING_FAULT_SUSPECTED | New qualification required | **Missing continuous trajectory guard** |
| HANDOFF_PENDING or TRACKING_FAULT_SUSPECTED | Pump-speed telemetry invalid | INSUFFICIENT_MEASUREMENT | Preserve prior evidence; sensor Safety policy applies | Recovery/re-anchor guard **missing** |
| INSUFFICIENT_MEASUREMENT | Telemetry valid again | Context-dependent | Must not grant unlimited new grace | **Missing deterministic re-entry rule** |
| TRACKING_FAULT_CONFIRMED | Response resumes | No automatic top-level NORMAL | Existing Safety fault reset/recovery remains authoritative | Evidence-restored semantics **missing** |

The table deliberately exposes undefined paths. Treating it as complete would violate this phase's gate.

## Partial epoch lifecycle table

| Situation | Existing epoch | New epoch? | Preserve original age? | Re-anchor? |
|---|---|---|---|---|
| First material command | None | Yes | New age | Released measurement only |
| Small same-direction update | Active | No | Yes | No |
| Material same-direction update | Active | No | Yes | No; safe expected-envelope update unresolved |
| Material reversal | Active | Replacement needed | Anti-reset evidence retention unresolved | Directional re-anchor requires qualified measurement |
| Successful completion | Active | No | Completed history retained | Next material demand may start a new epoch |
| Post-steady new demand | Resolved | Yes | New demand age | Released measurement only |
| Sensor invalid or recovery | Active | No automatic restart | Yes | Recovery rule unresolved |
| Suspected fault + update | Active | No ordinary reset | Yes | No |
| Confirmed fault + update | Fault-confirmed | No automatic clear | Yes | Existing Safety reset only |

Repeated same-direction updates must not mask a stuck pump by resetting age. A material reversal needs one directional context, but simply replacing and resetting on every reversal permits an adversarial reset loop. The R5.2 registration and diagnostic do not specify a qualified anti-mask rule for that case. Nor may `TRACKING_PROGRESS` be permanent immunity: R5.2 explicitly qualified the *initial* handoff only and its diagnostic latches progress for the remainder of that handoff. A later material demand or loss of progress requires a fresh continuous rule, which is not yet qualified.

## Suspected, confirmed, measurement and recovery boundaries

For the initial generic handoff, suspicion begins when the registered expected displacement is at least 0.03 and valid directed progress is insufficient; confirmation requires expected displacement at least 0.12 and a ratio below 0.35 for two qualified samples. Valid progress can move suspected back to progress. Those frozen rules do not define a later steady-state fault or progress-loss guard. A missing/stale pump-speed measurement means `INSUFFICIENT_MEASUREMENT`, never a confirmed actuator fault from absence alone; existing `CRITICAL_LOCAL_SENSOR_INVALID` Safety handling remains authoritative. Prior suspicion must not be silently erased by telemetry loss, but a precise recovery/re-anchor policy remains unqualified. A confirmed tracking observation cannot clear top-level `FAULT`; [Safety's existing reset path](v0_2/safety/supervisor.py) retains that authority.

## Synthetic validation and invariants

The registration listed S1–S16 before validation. A complete offline state-machine harness was **not executed**: the pre-validation calibration/observability stop condition prevents constructing a production-portable oracle for S5–S16 without inventing guards. Historical R5.2 results remain available for S1–S4 as *prior initial-handoff evidence*, not as new R5.2.1 passes. The evidence JSON marks every new sequence `NOT_RUN_PRE_VALIDATION_STOP`; it does not claim success. Invariants 1, 4, 5, 7 and 8 are design constraints supported by the existing information/ownership boundary, but invariants 2, 3 and 6 cannot be validated until the missing continuous/reversal guards exist. No future sample may relabel an earlier result; that prefix-causality test likewise awaits a complete harness.

## Limitations and gate

The exact missing production requirements are: qualified measured-speed resolution/noise, a continuous progress-loss and steady-completion guard, an observable persistent-demand/reversal anti-mask rule, and deterministic re-entry after telemetry recovery. These are not supplied by R5.2 or by current typed hardware profiles. The generic initial-handoff numerical fixture remains specified separately. **`PHASE5_R5_2_1_GATE_STATUS = TRACKING_SEMANTICS_REQUIRE_CALIBRATION_PARAMETERS`**; this gate takes precedence over claiming a complete state machine. Stop before production R5.3. The R5 controller remains a candidate; do not freeze the final feedback baseline or start Phase 6.
