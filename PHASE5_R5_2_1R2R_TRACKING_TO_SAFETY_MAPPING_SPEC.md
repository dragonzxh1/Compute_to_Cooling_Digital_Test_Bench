# Phase 5R5.2.1R2R — Tracking-to-Safety Mapping Specification

Authority, in order: Contract 14 (ownership/permissions), original Contract 15 (base Safety), Contract 15A (tracking amendment), frozen validated tracking semantics (state qualification), R5.2.2 profile (fixture observability). The historical R2 stop `TRACKING_STATE_TO_SAFETY_LEVEL_UNDERSPECIFIED` remains unchanged. This document only revalidates already-qualified states; it creates no tracking detector, timer, threshold, actuator command, or production Safety implementation.

| Tracking state | Safety contribution | Reason | Tracking restriction | Latching | Recovery authority |
|---|---|---|---|---|---|
| `STEADY_TRACKING` | NORMAL identity | None | None | No | Qualifier on later demand |
| `HANDOFF_PENDING` | NORMAL identity | None | None | No | Qualifier after response opportunity |
| `TRACKING_PROGRESS` | NORMAL identity | None | None | No | Qualifier on later demand |
| `TRACKING_FAULT_SUSPECTED` | DEGRADED | `ACTUATOR_TRACKING_SUSPECTED` | None | No | Frozen qualified progress before confirmation |
| `TRACKING_FAULT_CONFIRMED` | FAULT | `ACTUATOR_TRACKING_CONFIRMED` | Existing generic FAULT only | Existing FAULT latch | Explicit Safety reset and qualified recovery |
| `INSUFFICIENT_MEASUREMENT` | NORMAL identity/no new actuator fault | None newly generated | None | No new latch | Sensor channel; retain prior valid tracking evidence |

`TrackingSafetyContribution` conceptually carries `internal_tracking_state`, `severity_contribution`, `reason_codes`, `restriction_contribution`, `latched`, `recovery_authority`, `tracking_epoch_id`, `tracking_evidence_id`, and `measurement_quality_dependency`. It is an offline contract object, not a production command. Thermal, pressure, sensor quality, actuator tracking, FF and derate/protection contribute independently. The reducer selects `FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL`, preserves every active reason, and keeps pressure restriction priority over competing thermal demand. Suspected adds no tracking-specific envelope; confirmed uses the existing generic FAULT fallback/speed restriction. Safety owns restrictions; PLC alone produces `ActuatorCommand`.

| Reason | Existing/New | Severity | Channel | May coexist? | Recovery authority |
|---|---|---|---|---|---|
| `ACTUATOR_TRACKING_PENDING` | Legacy, historical only | No new mapping severity | Tracking | Historical evidence only | Legacy; not used by 15A |
| `ACTUATOR_TRACKING_SUSPECTED` | New | DEGRADED | Tracking | Yes | Qualified progress before confirmation |
| `ACTUATOR_TRACKING_CONFIRMED` | New | FAULT | Tracking | Yes | Explicit Safety FAULT reset |
| `OVERPRESSURE_MEASURED` | Existing | FAULT | Pressure | Yes | Existing pressure/FAULT rules |
| `HARD_THERMAL_MEASURED` | Existing | PROTECTED | Thermal | Yes | Existing thermal qualification |
| `THERMAL_OR_FLOW_CAPACITY_LIMITED` | Existing | DERATE_REQUESTED | Thermal/flow | Yes | Existing derate qualification |
| `CRITICAL_LOCAL_SENSOR_INVALID` | Existing | FAULT | Sensor quality | Yes | Existing sensor/FAULT rules |
| `RECOVERY_QUALIFICATION` | Existing | FF_DISABLED | FF/recovery | Yes | Existing valid-sample/dwell rule |

| Contract requirement | Current production type supports it? | Implementation currently uses it fully? | R5.3R change needed? | Schema revision needed? |
|---|---|---|---|---|
| Multiple active reasons | Yes: `SafetyDecision.reasons` and `SafetyEnvelope.reason_codes` are tuples | No: single-branch selection | Yes | No |
| Severity contribution | Yes: `SafetyState` | No tracking channel reducer yet | Yes | No |
| Safety envelope | Yes: DP/speed bounds, fallback, state and reasons | Existing FAULT fallback, not 15A mapping | Yes | No |
| Latched FAULT evidence | Yes: supervisor latch/reset and reasons | Existing fault path; not qualifier-driven | Yes | No |
| Tracking evidence/provenance | Linkable by envelope ID to an auditable qualifier evidence record; `source_measurement_ids` is measurement-only | No tracking epoch/evidence link yet | Yes, add linked evidence record; do not overload reason or measurement IDs | No core SafetyDecision/SafetyEnvelope revision |
| Sensor-quality reason coexistence | Yes: reason tuples | Current invalid-sensor branch suppresses others | Yes | No |

The source audit is representability, not a claim of current compliance. `SafetySupervisor.evaluate` currently selects one major cause through `if/elif`, so simultaneous active reasons are not fully populated. That is implementation work for R5.3R. The existing FAULT fallback and explicit reset exist; confirmed tracking needs no newly invented pump restriction. There is no mandatory primary-reason field, and none is added. If a future primary field is introduced, Contract 15A's diagnostic rule applies without affecting severity or envelope.

Normative case inputs and exact outputs are in [the machine-readable contract](phase5_r5_2_1r2r_tracking_to_safety_mapping_contract.json); M1–M16 include pressure, thermal, sensor, FF, retained prior evidence and restored-motion cases. Contract 14 deny-default, Contract 15 unchanged hierarchy/same-tick/ownership/recovery, and Contract 15A exact mapping remain binding. This is a generic development contract, not OEM/NVIDIA/GB300 certification.
