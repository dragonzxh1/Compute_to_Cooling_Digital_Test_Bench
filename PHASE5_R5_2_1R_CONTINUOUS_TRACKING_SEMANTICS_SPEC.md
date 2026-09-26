# Phase 5R5.2.1R — continuous tracking semantics (offline only)

Status: `TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT` — **blocked** after a post-validation boundary audit. This is a specification and offline test engine, not production Safety code. The R5.2.1 blocker was missing qualified observability/timing parameters; R5.2.2 closed that fixture-only calibration gap. Its profile SHA-256 is `9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8`. The historical R5.3 block remains part of the audit trail.

## Information and scope

The qualifier receives current/prior PLC command and timestamp plus **released** measured pump speed, sample/release timestamps and quality. Released DP/flow and existing Safety state/timers are permissible future inputs, but the offline engine does not need them. It never reads raw ACTUAL, hidden actuator state, fault identity, scenario labels, future data or plant truth; it never emits an `ActuatorCommand`. Frozen directional PI remains Kp 4500, Ki_hot 110, Ki_cold 130, Kd 0, blend halfwidth 0.1 K, one integral state and unchanged anti-windup. No production controller, actuator, sensor, plant or Safety code changed.

## States and two lifetimes

The six internal states are `STEADY_TRACKING` (valid, no unresolved demand and within profile tolerance after progress), `HANDOFF_PENDING` (observable demand exists but a fair response opportunity has not opened), `TRACKING_PROGRESS` (qualified released directional motion), `TRACKING_FAULT_SUSPECTED` (open opportunity and insufficient progress), `TRACKING_FAULT_CONFIRMED` (frozen R5.2 valid-sample deficit confirmed), and `INSUFFICIENT_MEASUREMENT` (missing/stale/invalid speed). These are **not** top-level SafetyState values. Top-level precedence remains FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL.

The **tracking epoch** is directional: it stores its ID, start, command/measured anchors, latest command, expected direction, oldest unresolved demand, response opening, status, qualified progress, suspicion/confirmation times, measurement ID and completion reason. The **unresolved-motion watch** independently stores ID, oldest start, released-speed anchor, maximum observable demand, motion flag, last valid measurement, carried deficit count and resolution reason. An epoch may change direction; an unresponsive watch cannot be reset by command changes.

## Demand, response and progress

Command demand is classified as immaterial, observable material, not observable for tracking qualification, or material reversal. Materiality uses the frozen profile delta; observability additionally requires that the frozen delay/ramp/lag plus sample/release model predict movement beyond its frozen minimum observable speed change. Response opening is the first such **released sample**—there is no universal 0.4 s, 1.0 s or 1.2 s grace. Frozen R5.2 expected-progress/ratio thresholds determine suspicion and confirmation; confirmation needs its exact two consecutive qualified valid samples. Progress needs released valid speed moving in the new direction by at least the profile floor and the frozen R5.2 recovery ratio. Raw float inequality is insufficient.

Small command updates change the latest command without changing epoch/watch age or suspicion. Same-direction observable material updates evolve the response envelope but retain both oldest age and suspicion. Material reversal closes the old directional epoch and starts a new one from the current released valid speed. If prior qualified motion occurred, its watch resolves; otherwise the watch, oldest age and deficit evidence carry across. This is the timer-reset and reversal-attack barrier. Qualified motion resolves the watch, but does **not** grant permanent immunity: later observable material demands establish new obligations. After qualified progress, command/measured-speed error within the frozen tracking tolerance resolves the epoch to steady.

Suspected fault can return to progress only on qualified released directional motion before confirmation, not on elapsed time or command update. A confirmed tracking diagnosis remains latched for audit even if motion later resumes; only existing top-level Safety reset/recovery authority may clear FAULT. Invalid measurement displays `INSUFFICIENT_MEASUREMENT`, retains epoch/watch/suspicion, lets causal wall-clock age advance and contributes **zero** confirmation samples. The first recovered valid released sample is checked against the retained context, without new grace.

## Transition table

| From | Event/guard | To | Context action |
| --- | --- | --- | --- |
| Steady/progress | New observable material demand | Pending | Start/attach epoch and watch |
| Pending | Qualified directional motion | Progress | Resolve watch |
| Pending | Response open, frozen suspect deficit | Suspected | Retain oldest age |
| Suspected | Qualified motion before confirmation | Progress | Resolve watch |
| Suspected | Frozen consecutive qualified deficit | Confirmed | Latch evidence |
| Progress | Frozen tracking tolerance met | Steady | Close epoch |
| Any non-confirmed state | Invalid released measurement | Insufficient | Preserve context; no sample count |
| Insufficient | Valid measurement returns | Re-evaluate preserved context | No new grace |
| Confirmed | Motion resumes | Confirmed | Record restored evidence; no auto-clear |
| Active directional epoch | Material reversal | Pending/new epoch | Carry watch unless prior qualified motion |

Epoch lifecycle: start on observable demand; same-direction update preserves start; reversal closes and re-anchors direction; qualified steady or confirmation closes it. Watch lifecycle: start at oldest unresolved demand; carry across updates and no-motion reversal; resolve only on qualified measured motion.

## Validation and limitations

The preregistration was frozen before outcomes (SHA-256 `a5ccc13dc8a7ecc7a2aa5205a11a6c2635f78c1bba51d564cb72aceb156731ca`). S1–S16, including S16 variant, all pass. Eight registered invariants and prefix-causality replay pass. Exact traces, transitions, epoch/watch events and source hash checks are in [evidence](phase5_r5_2_1r_continuous_tracking_semantics_evidence.json); the [machine-readable spec](phase5_r5_2_1r_continuous_tracking_semantics_spec.json) and [figure](docs/results/phase5_r5_2_1r_continuous_tracking_semantics.png) accompany this document. The first validation found only a reversed boolean expression in invariant 4's **test assertion**; its correction changed no preregistered rule, fixture parameter or engine logic.

However, an additional post-validation boundary audit found a production-critical gap not covered by the registered sequences: a stationary speed of 0.5 with PLC commands 0.5 → 0.6 → 0.7 → 0.8 at 0.2 s intervals remains `STEADY_TRACKING` through 3 s, creates **zero** epochs, and never starts a watch. Each 0.1 update is below the 0.15 material threshold, but cumulative 0.3 demand is observable. The engine compares only against the immediately previous command, contradicting the preregistered *previous qualified command* reference. Thus repeated small same-direction changes can mask a silent-stuck actuator. No semantic rule, profile or engine was changed after this outcome; a new revision must define and validate cumulative demand accounting before any production Safety port. The green S1–S16 and eight registered invariants are necessary but insufficient for the gate.

The state-machine concepts are intended to be profile-driven, but portability cannot pass while cumulative-demand accounting is unresolved. This does **not** validate real GB300 or OEM hardware. Real speed-sensor resolution/noise, timestamp accuracy and jitter, actuator delay/slew/lag, telemetry delay, validity policy, tracking tolerance and observability margins all require hardware calibration. A trajectory that never creates a profile-observable persistent demand cannot support a universal stuck-actuator claim. No R5.3R port, final feedback baseline freeze or Phase 6 work is included. Stop here for user review.
