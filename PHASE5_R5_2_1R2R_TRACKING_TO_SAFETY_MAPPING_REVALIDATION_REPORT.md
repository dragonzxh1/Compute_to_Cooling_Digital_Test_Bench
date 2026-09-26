# Phase 5R5.2.1R2R — Tracking-to-Safety Mapping Revalidation

## Outcome and authority

The original R2 attempt stopped at `TRACKING_STATE_TO_SAFETY_LEVEL_UNDERSPECIFIED`: suspected tracking had no authorized place in the Safety hierarchy. R3 closed that policy gap with immutable [Contract 15A](contracts/15A_tracking_safety_policy_amendment.md), authorizing suspected → DEGRADED, confirmed → FAULT, legitimate pending → no degradation, and measurement insufficiency → sensor-channel authority. This R2R phase revalidates mapping only; it neither redetects tracking failure nor changes production Safety.

Source authority: Contract 14 controls permissions and PLC command ownership; original Contract 15 controls the unchanged Safety architecture; Contract 15A controls only tracking-to-Safety mapping; frozen continuous tracking semantics determine internal state; the unchanged R5.2.2 profile determines fixture observability. All source and production hashes in the preregistration matched. Registration SHA-256: `c29b911a7dd5e9320d13991a1f17236191c8ffc5433dd2025d388b756a7e0aa5`. Contract 14/15/15A SHA-256: `efd8d325753163b91170578ceeb3de02dafafbf8fb0a208a279c76c964d7b144`, `1e93c50037e2b211494e98b30f951e638399e041d1c07b9c0daa2426fb00e073`, `b741a05925a043706dbdc93351faf37fdbd6f1d41ad22360143c8184dd08e280`.

The normative six-state table, reason-code table, and representation/readiness table are in the [mapping specification](PHASE5_R5_2_1R2R_TRACKING_TO_SAFETY_MAPPING_SPEC.md), with executable cases in the [machine-readable contract](phase5_r5_2_1r2r_tracking_to_safety_mapping_contract.json). The exact mapping is: STEADY, HANDOFF_PENDING, TRACKING_PROGRESS → NORMAL identity/no tracking reason; SUSPECTED → DEGRADED/`ACTUATOR_TRACKING_SUSPECTED`/no new restriction; CONFIRMED → FAULT/`ACTUATOR_TRACKING_CONFIRMED`/existing FAULT restriction and explicit recovery; INSUFFICIENT_MEASUREMENT → no new actuator fault, existing sensor channel owns invalid telemetry. Historical `ACTUATOR_TRACKING_PENDING` is not reused to degrade legitimate handoff.

## Reason model and production representation

The existing frozen production `SafetyDecision.reasons` and `SafetyEnvelope.reason_codes` are `tuple[str, ...]`: multiple active reasons are representable in the actual decision/evidence structures, not merely in logs. `SafetyDecision.state` and `SafetyEnvelope.state` represent severity; the envelope carries DP/speed bounds, fallback, measurement IDs, and an envelope ID. `SafetySupervisor` already has a FAULT latch and explicit `reset_fault`. No mandatory primary-reason field exists, so no new primary policy was imposed. Tracking epoch/evidence IDs can be linked to a separate auditable qualifier evidence record keyed by the existing envelope ID; `source_measurement_ids` remains measurement-only, and reasons must not be overloaded with provenance. R5.3R must implement that link and verify it end-to-end.

Current production `SafetySupervisor.evaluate` still uses a single-branch `if/elif` cause selector and an old raw-speed-mismatch tracking path. It **does not currently populate all simultaneously active reasons**, even though its data types can carry them. This is an implementation gap permitted for R5.3R, not evidence that the production behavior already meets Contract 15A. No core SafetyDecision/SafetyEnvelope shape or semantic change is required for the mapped outputs; production-port verification remains mandatory.

## Channel, envelope, and recovery checks

Thermal, pressure, sensor quality, tracking, FF, and derate/protection are independent contributions. The offline reducer selects `FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL`, retaining all active reasons. Tracking DEGRADED cannot weaken pressure FAULT or thermal PROTECTED. Tracking FAULT dominates thermal PROTECTED and DERATE_REQUESTED while their reasons remain visible. Pressure restriction priority over competing thermal demand is unchanged. Sensor invalidity cannot fabricate tracking confirmation; prior valid suspected context or confirmed latch is retained. FF_DISABLED continues local feedback/PLC operation under the original contract when no stronger channel is active.

Suspected tracking adds no pump-speed or DP restriction and may clear only after frozen qualified progress before confirmation; other active channel restrictions remain. Confirmed tracking uses the existing generic FAULT fallback/speed envelope, not a new tracking-specific actuator command. Restored measured motion alone cannot clear its latched top-level FAULT; explicit Safety reset and qualified recovery remain authoritative. Safety issues only restrictions; PLC alone produces the final `ActuatorCommand` under the frozen same-tick authority chain.

## M1–M16 offline validation

| Case | Expected interaction | Result |
|---|---|---|
| M1 | Steady baseline | PASS |
| M2 | Legitimate handoff stays NORMAL | PASS |
| M3 | Tracking progress stays NORMAL | PASS |
| M4 | Suspected alone → DEGRADED | PASS |
| M5 | Confirmed alone → FAULT | PASS |
| M6 | Insufficient measurement + invalid sensor; no fabricated actuator fault | PASS |
| M7 | Suspected + pressure FAULT; both reasons | PASS |
| M8 | Confirmed + pressure FAULT; both reasons | PASS |
| M9 | Suspected + thermal PROTECTED; both reasons | PASS |
| M10 | Confirmed + thermal PROTECTED; both reasons | PASS |
| M11 | Suspected + DERATE_REQUESTED; both reasons | PASS |
| M12 | Confirmed + DERATE_REQUESTED; both reasons | PASS |
| M13 | Prior suspected context + sensor invalid | PASS |
| M14 | Prior confirmed latch + sensor invalid; both reasons | PASS |
| M15 | Tracking progress + FF_DISABLED | PASS |
| M16 | Confirmed + restored motion; no automatic FAULT clear | PASS |

All M cases were evaluated by the [offline harness](v0_2/examples/phase5_r5_2_1r2r_mapping_validation.py); [evidence](phase5_r5_2_1r2r_tracking_to_safety_mapping_evidence.json) records exact reasons, envelope sources, recovery authority and source/type audits. The [figure](docs/results/phase5_r5_2_1r2r_tracking_to_safety_mapping.png) shows the mapping/ownership chain. This harness is contract-only and must not become parallel permanent Safety logic.

## Audits, limitations, and next allowed work

Contract 14: PASS (deny-default, Safety envelope authority, PLC command ownership). Original Contract 15: PASS (hierarchy, pressure priority, thermal/sensor/FF behavior, same-tick authority, generic FAULT envelope/reset). Contract 15A: PASS (exact six-state mapping, two new reasons, all-reason retention, no new tracking restriction). Production Safety, controller, actuator, sensor, plant and PLC/authority source hashes matched registration; no production file was modified.

R5.3R may replace the old raw mismatch branch with the validated qualifier-state mapping, reduce all active channels and fill the existing reason tuples, preserve the existing pressure/thermal and FAULT envelope behavior, link tracking epoch/evidence in an auditable record, and test same-tick PLC authority and explicit reset. It may not invent new tracking timers, profile thresholds, speed commands, or an alternative command owner. The current contract pass is not production behavior validation or OEM/NVIDIA/GB300 certification. Historical BLOCKED/INVALID gates remain historical.

Focused R2R tests and V0.2 regression, Ruff, and `git diff --check` passed. No blocking schema/reducer/FAULT-restriction conflict was found.

`PHASE5_R5_2_1R2R_GATE_STATUS = TRACKING_TO_SAFETY_MAPPING_CONTRACT_REVALIDATED`

Stop after user review. Do not start R5.3R automatically; do not freeze the final feedback baseline, start Phase 6, or commit/push GitHub.
