# Phase 5R5.2.1R3 — Tracking Safety Policy Amendment Report

## Decision and scope

R2 stopped at `TRACKING_STATE_TO_SAFETY_LEVEL_UNDERSPECIFIED`: the tracking qualifier had defined detection semantics, but no authorized mapping from its suspected/confirmed states to top-level Safety. This revision records the owner's explicit policy in a versioned amendment, [Contract 15A](contracts/15A_tracking_safety_policy_amendment.md), and a [machine-readable contract](phase5_r5_2_1r3_tracking_safety_policy_contract.json). Original Contract 15 and Contract 14 remain unchanged. The amendment is authoritative only for the actuator-tracking-to-Safety mapping and the two new tracking reason definitions; thermal, pressure, sensor, FF, command ownership, and other original rules are not revised.

Registration preceded validation. Its SHA-256 is `e3ecfbd1de129ba230062ac15a775d5458d7c6deaff4d260a31c2aff344aad5d`. Contract 14 SHA-256 is `efd8d325753163b91170578ceeb3de02dafafbf8fb0a208a279c76c964d7b144`; original Contract 15 SHA-256 is `1e93c50037e2b211494e98b30f951e638399e041d1c07b9c0daa2426fb00e073`. Contract 15A SHA-256 is `b741a05925a043706dbdc93351faf37fdbd6f1d41ad22360143c8184dd08e280`.

## Authorized six-state mapping

| Tracking state | Safety contribution | Top-level tracking reason | Tracking restriction | Latched | Recovery authority |
|---|---|---|---|---|---|
| `STEADY_TRACKING` | NORMAL identity | None | None | No | Qualifier on later demand |
| `HANDOFF_PENDING` | NORMAL identity | None | None | No | Qualifier after fair response opportunity |
| `TRACKING_PROGRESS` | NORMAL identity | None | None | No | Qualifier on later demand |
| `TRACKING_FAULT_SUSPECTED` | DEGRADED | `ACTUATOR_TRACKING_SUSPECTED` | None specific to tracking | No | Frozen qualified progress before confirmation |
| `TRACKING_FAULT_CONFIRMED` | FAULT | `ACTUATOR_TRACKING_CONFIRMED` | Existing generic FAULT policy only | Existing FAULT latch | Explicit Safety FAULT reset and qualified recovery |
| `INSUFFICIENT_MEASUREMENT` | NORMAL identity; no *new* actuator fault | None newly generated | None | No new latch | Sensor-quality channel; retain prior valid tracking evidence |

`HANDOFF_PENDING` means the actuator has not yet had a fair response opportunity; it cannot produce DEGRADED or either new tracking fault reason. `TRACKING_FAULT_SUSPECTED` is different: the validated qualifier has already established observable demand, an open response opportunity, valid measurement, and insufficient qualified progress. Safety does not recalculate those thresholds. `TRACKING_FAULT_CONFIRMED` is likewise accepted as already-qualified evidence, not subjected to a second arbitrary confirmation threshold.

The historical `ACTUATOR_TRACKING_PENDING` identifier remains for legacy logs/evidence only; the new mapping does not use it restrictively. The two newly authorized reason identifiers do not collide with existing production identifiers. No new tracking-specific pump command or speed envelope is created. Restored motion can clear a pre-confirmation suspected contribution through the frozen qualifier, but cannot directly clear a confirmed top-level FAULT; the existing explicit reset/recovery authority controls that. Missing telemetry alone never confirms actuator failure; the sensor-quality channel determines the current sensor response while previously valid tracking evidence remains available.

## Multi-channel Safety contract

Tracking is one contribution to the existing hierarchy: `FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL`. The final severity is the highest active contribution; all active reason codes remain in the decision evidence. Current `SafetyDecision` has no primary-reason field, so no primary was invented or emitted. If a future API requires one, select from the final highest-severity reasons using existing deterministic production priority, or the amendment's diagnostic-only tie-break; this cannot affect severity, envelope, or retention of other reasons.

Pressure restriction priority over thermal cooling demand is unchanged. Suspected tracking contributes no envelope restriction; confirmed tracking uses the existing generic FAULT envelope, including when another channel is active. Safety remains the restriction authority and the PLC remains the sole final `ActuatorCommand` producer. Safety restrictions apply before PLC consumption where the frozen same-tick scheduler requires it. Contract 14 deny-default permissions remain intact. FF-disabled operation retains local feedback/PLC behavior.

## Offline validation

The test-only declarative harness [mapping_contract.py](v0_2/examples/phase5_r5_2_1r3_mapping_contract.py) consumed the preregistered cases and contract; it did not run or modify production Safety. Results are recorded in [evidence](phase5_r5_2_1r3_tracking_safety_policy_evidence.json) and the [policy flow figure](docs/results/phase5_r5_2_1r3_tracking_safety_policy.png).

| Case | Combination | Result |
|---|---|---|
| A1 | Steady + normal | PASS |
| A2 | Handoff pending + normal; no false DEGRADED | PASS |
| A3 | Tracking progress + normal | PASS |
| A4 | Suspected only → DEGRADED | PASS |
| A5 | Confirmed only → FAULT | PASS |
| A6 | Insufficient measurement + invalid sensor; no fabricated actuator FAULT | PASS |
| A7 | Suspected + pressure FAULT | PASS |
| A8 | Confirmed + pressure FAULT | PASS |
| A9 | Suspected + thermal PROTECTED | PASS |
| A10 | Confirmed + thermal PROTECTED | PASS |
| A11 | Suspected + DERATE_REQUESTED | PASS |
| A12 | Confirmed + DERATE_REQUESTED | PASS |
| A13 | Previous suspected evidence + invalid sensor | PASS |
| A14 | Previous confirmed evidence + invalid sensor | PASS |
| A15 | Tracking progress + FF_DISABLED | PASS |
| A16 | Confirmed + later restored motion; no automatic FAULT clear | PASS |

Reason-retention, legacy pending, reason-code uniqueness, hierarchy, pressure priority, thermal protection, sensor authority, FF behavior, recovery/latch, absence of new tracking restriction, and PLC ownership checks passed. Contract 14 audit and compatibility with the unchanged Contract 15 rules passed. The policy maps qualified states and contains no fixture timing, speed-bound, C9R, OEM, NVIDIA, or GB300 certification claim; calibration stays in the unchanged profile.

## Limits and gate

This is contract-level validation, **not production behavior certification**. In particular, current production `v0_2/safety/supervisor.py` uses a single-branch `if/elif` decision path. Its current `SafetyDecision.reasons` tuple can represent multiple reasons, but the existing implementation does not yet construct the amendment's complete multi-channel reason set. That is a future production-port obligation, not an R3 production change or a claim that current behavior already passes A1–A16. The offline reducer is deterministic and the existing generic FAULT path is sufficient as a contract source; no separate policy revision or new actuator command was required here.

Frozen production Safety, controller, actuator, sensor, and plant source hashes matched registration. No production behavior source was changed. Focused R3 tests and full V0.2 test suite passed; Ruff and `git diff --check` passed. Historical BLOCKED/INVALID gates remain historical.

`PHASE5_R5_2_1R3_GATE_STATUS = TRACKING_SAFETY_POLICY_AMENDMENT_SPECIFIED_AND_VALIDATED`

This permits **R2R contract revalidation only after user review**. It does not start R2R, production R5.3R, final baseline freeze, Phase 6, or a Git commit/push.
