# 15A — Actuator tracking to Safety policy amendment (R5 development)

Revision: 1.0. Status: scoped, owner-authorized **generic-development** policy; not OEM or hardware certification.

This file supplements only the actuator-tracking-to-Safety mapping in frozen [Contract 15](15_safety_supervisor_contract.md). Contract 15 remains unchanged and authoritative for every non-tracking rule. Within this narrow tracking mapping, 15A is authoritative for subsequent R5 development. Frozen [Contract 14](14_control_input_permission_contract.md) remains unchanged: Safety issues restrictions/envelopes; PLC alone produces the final `ActuatorCommand`; neither tracking nor Safety reads raw actuator ACTUAL.

## Tracking contribution contract

The validated qualifier produces an internal `TrackingSafetyContribution` with `tracking_internal_state`, `severity_contribution`, `reason_codes`, `restriction_contribution`, `latched`, `recovery_authority`, `tracking_epoch_id`, `tracking_evidence_id`, and `measurement_quality_dependency`. It is a contribution to the multi-channel reducer, **not** a direct write to final SafetyState or a command. Tracking detection (response, progress, confirmation, epoch/watch and command anchor) remains owned by the already-frozen qualifier; this amendment adds no tracking threshold or timer.

| Internal tracking state | Severity contribution | Top-level reason | Tracking restriction | Latched | Recovery authority |
| --- | --- | --- | --- | --- | --- |
| `STEADY_TRACKING` | `NORMAL` identity | none | none | no | qualifier on later demand |
| `HANDOFF_PENDING` | `NORMAL` identity | none restrictive | none | no | qualifier on response opportunity |
| `TRACKING_PROGRESS` | `NORMAL` identity | none | none | no | qualifier on later demand |
| `TRACKING_FAULT_SUSPECTED` | `DEGRADED` | `ACTUATOR_TRACKING_SUSPECTED` | none tracking-specific | no | frozen qualified progress before confirmation |
| `TRACKING_FAULT_CONFIRMED` | `FAULT` | `ACTUATOR_TRACKING_CONFIRMED` | existing FAULT policy only | top-level FAULT latch | existing explicit Safety reset/recovery authority |
| `INSUFFICIENT_MEASUREMENT` | `NORMAL` identity from tracking | none asserting actuator fault | none tracking-specific | no new latch; retain earlier valid evidence | sensor-quality channel owns invalidity; qualifier resumes on valid release |

Normative boundary: legitimate `HANDOFF_PENDING` alone **SHALL NOT** contribute `DEGRADED`, `ACTUATOR_TRACKING_SUSPECTED` or `ACTUATOR_TRACKING_CONFIRMED`. It has not yet had a fair response opportunity. `TRACKING_FAULT_SUSPECTED` may contribute `DEGRADED` only after the frozen qualifier has found observable demand, open response opportunity, valid released measurement and insufficient qualified progress. The Safety mapping must not re-derive those tests. Confirmed is similarly already-qualified evidence, not an invitation to add a second timer or threshold.

## Reasons and reduction

`ACTUATOR_TRACKING_SUSPECTED` uniquely means valid measured-only insufficient progress after a fair response opportunity but before frozen confirmation. It is a nonlatched `DEGRADED` reason and introduces no tracking-specific speed/DP restriction. `ACTUATOR_TRACKING_CONFIRMED` uniquely means frozen confirmed measured-only non-response, contributes `FAULT`, and invokes the **existing** FAULT latch and fallback envelope; it adds no new actuator restriction or command. Neither collides with thermal, pressure, sensor, FF or `ACTUATOR_FAULT_MEASURED` (explicit measured equipment fault/status) semantics.

The old `ACTUATOR_TRACKING_PENDING` identifier is retained for historical evidence/legacy log interpretation: previously it denoted a raw command-versus-speed mismatch during the waiting interval and could produce the false cold-start `DEGRADED`. It is **not** a restrictive reason for legitimate `HANDOFF_PENDING` under 15A. Do not silently relabel historical logs.

Reduce all currently active channel severities by Contract 15 precedence `FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL`. Retain **every** active channel reason in `SafetyDecision.reasons` and `SafetyEnvelope.reason_codes`, including reasons below final severity. Current `SafetyDecision` has no primary-reason field; do not add one. If a future interface requires one, choose from final-highest-severity reasons, preserve any already-frozen deterministic production tie-break, otherwise use diagnostic `PRESSURE > THERMAL > SENSOR > ACTUATOR_TRACKING > FF > OTHER`. Primary selection never changes severity, envelope or the retained reason collection. This contract rule does not claim that the current production `if/elif` code already implements all-reason retention; that is a future port obligation.

`SUSPECTED` adds no tracking-specific envelope. `CONFIRMED` uses the current generic FAULT action: fallback DP and the existing policy fault-speed bounds via Safety's envelope; **PLC** still creates the final actuator command. No separate envelope reducer or speed rule is added. Other channel restrictions remain active. Pressure restriction has precedence over a conflicting thermal cooling request under Contract 15. Tracking does not weaken thermal `PROTECTED`, pressure `FAULT`, sensor-invalid `FAULT`, derate, FF-disabled behavior, or same-tick Safety-before-PLC authority. Existing infeasible-restriction rules remain Contract 15's authority.

## Recovery and sensor quality

Before confirmation, frozen qualified progress may remove only the tracking channel's `DEGRADED` contribution; other active channels still reduce normally. After confirmation, later restored motion is audit evidence and **cannot** clear top-level latched `FAULT`; use existing explicit Safety reset, valid sensors and recovery qualification. Invalid/stale pump-speed telemetry contributes no *new* actuator-tracking confirmation. The sensor-quality channel independently applies Contract 15's critical-sensor behavior, with no raw ACTUAL fallback. Prior valid suspected evidence is retained internally but does not turn an invalid sample into tracking confirmation. Prior **confirmed** tracking evidence stays latched while sensor telemetry is invalid; both confirmed and sensor reasons remain active. Sensor recovery alone does not create a new tracking grace or clear a confirmed FAULT.

## Normative combinations

| Case | Tracking and other active channel | Final Safety | Required active reasons / restriction source |
| --- | --- | --- | --- |
| A1 | Steady, otherwise normal | NORMAL | none / identity |
| A2 | Handoff pending, otherwise normal | NORMAL | none restrictive / identity |
| A3 | Progress, otherwise normal | NORMAL | none / identity |
| A4 | Suspected only | DEGRADED | tracking suspected / no tracking restriction |
| A5 | Confirmed only | FAULT | tracking confirmed / existing FAULT fallback |
| A6 | Insufficient measurement + sensor invalid | FAULT | sensor invalid only / existing FAULT fallback |
| A7 | Suspected + pressure FAULT | FAULT | pressure and tracking reasons retained / pressure-FAULT authority |
| A8 | Confirmed + pressure FAULT | FAULT | both reasons retained / pressure-FAULT authority |
| A9 | Suspected + thermal PROTECTED | PROTECTED | both reasons retained / thermal protection |
| A10 | Confirmed + thermal PROTECTED | FAULT | both reasons retained / existing FAULT fallback |
| A11 | Suspected + DERATE_REQUESTED | DERATE_REQUESTED | both reasons retained / existing derate path |
| A12 | Confirmed + DERATE_REQUESTED | FAULT | both reasons retained / existing FAULT fallback |
| A13 | Earlier suspected, then sensor invalid | FAULT | sensor invalid current reason; prior suspicion evidence retained internally |
| A14 | Earlier confirmed, then sensor invalid | FAULT | confirmed and sensor reasons retained / existing FAULT fallback |
| A15 | Progress + FF_DISABLED | FF_DISABLED | FF reason retained; local feedback/PLC continue |
| A16 | Confirmed, later measured motion restored | FAULT | confirmed reason/latch retained until explicit reset |

Contract 14 audit: deny-default measurements, Safety restriction-only authority, PLC sole final command owner and no direct tracking actuator control remain mandatory. Contract 15 audit: unchanged thermal/pressure/sensor/FF policy, hierarchy, pressure priority, generic FAULT fallback/recovery and same-tick authority remain mandatory. This amendment authorizes **only** the mapping policy and two reason definitions. It does not change production Safety code, the original frozen contracts, actuator physics or hardware calibration. A later R2R must revalidate this contract before any R5.3R port.
