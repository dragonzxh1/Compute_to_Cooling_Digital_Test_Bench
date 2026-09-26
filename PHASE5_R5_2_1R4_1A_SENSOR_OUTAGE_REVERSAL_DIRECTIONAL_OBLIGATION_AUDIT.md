# Phase 5R5.2.1R4.1A — Sensor-outage reversal directional-obligation audit

**Audit-only.** No tracking semantics, tests, production Safety, controller, plant, profile, or Contract 15A were changed. This is an offline generic numerical fixture, not OEM/NVIDIA/GB300 or hardware evidence. R4.1 remains blocked; this report does not authorize R4.2 or a production port.

## Scope and immutable inputs

R41-7 is the pre-registered `synthetic` fixture: initial command and measured speed 0.5; command 0.7 at 0.2 s, 0.3 at 0.6 s; released speed unavailable for 0.4–<1.2 s; actuator stuck at 0.5; duration 3.0 s. Measurement period is 0.2 s. The frozen `material_command_delta` is 0.15. Canonical sorted-JSON input trace SHA-256 is `28a3db5b806c4f5670fb2aafe476f21380e9cb47fd3f6167befe3c953f7997bd`. R4.1 engine SHA-256 is `0dfbee95c9fd288074fe095475516c6e893111aaf3834fd2a09f1b5973ca7438`; R4 paired engine SHA-256 is `ecf473f703ac6d11b49b83de6b7684c6653a9ad42e5eada66034178e4e668334`; fixture test SHA-256 is `a79578d7b1728ec34679f692969bcffaf32d1db294b2e854590ce1d66c7efc11`. Frozen profile SHA-256 remains `9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8`.

## Direction and evidence timeline

`Δcmd` is the change from the preceding released command. `Net` is current command minus resolved command anchor; `+`/`−` is its sign. `Epoch dir` and `Deferred dir` are internal directions, not inferred actuator motion. Watch age is relative to its original 0.2 s start. All commands and pair values are normalized pump-speed fractions.

| t (s) | Released cmd | Δcmd | Resolved cmd/meas | Progress cmd/meas | Net / sign | Epoch dir | Deferred dir | Watch age (s) | Measurement | State |
|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|---:|:---:|:---|
| 0.0 | 0.5 | — | 0.5 / 0.5 | — | 0 / 0 | — | — | — | VALID 0.5 | STEADY_TRACKING |
| 0.2 | 0.7 | +0.2 | 0.5 / 0.5 | 0.5 / 0.5 | +0.2 / + | + | — | 0.0 | VALID 0.5 | HANDOFF_PENDING |
| 0.4 | 0.7 | 0 | 0.5 / 0.5 | 0.5 / 0.5 | +0.2 / + | + | + | 0.2 | MISSING | INSUFFICIENT_MEASUREMENT |
| **0.6** | **0.3** | **−0.4** | **0.5 / 0.5** | **0.5 / 0.5** | **−0.2 / −** | **+** | **−** | **0.4** | **MISSING** | INSUFFICIENT_MEASUREMENT |
| 0.8 | 0.3 | 0 | 0.5 / 0.5 | 0.5 / 0.5 | −0.2 / − | + | − | 0.6 | MISSING | INSUFFICIENT_MEASUREMENT |
| 1.0 | 0.3 | 0 | 0.5 / 0.5 | 0.5 / 0.5 | −0.2 / − | + | − | 0.8 | MISSING | INSUFFICIENT_MEASUREMENT |
| **1.2** | **0.3** | **0** | **0.5 / 0.5** | **0.5 / 0.5** | **−0.2 / −** | **+** | **− before consumption** | **1.0** | **VALID 0.5** | **HANDOFF_PENDING** |
| 1.4–3.0 | 0.3 | 0 | 0.5 / 0.5 | 0.5 / 0.5 | −0.2 / − | + | inactive | 1.2–2.8 | VALID 0.5 | HANDOFF_PENDING throughout |

The first valid recovery measurement is `synthetic-measurement:1200000000` at 1.2 s, value 0.5. It shows **no** movement in either direction. Invalid samples earned neither progress nor fault evidence. The watch ID stays `motion-watch:1`, its start stays 0.2 s, and its age is not reset. Prior valid suspicion count is zero. The unresolved **age** is preserved correctly; the active **direction** is stale.

## First incorrect continuation and exact code path

The first tick at which the old positive directional obligation no longer represents current material net demand is **0.6 s**. The net demand moves from +0.2 to −0.2 relative to the same resolved command anchor 0.5; both magnitudes exceed the frozen 0.15 material threshold, and the frozen response-opening model accepts the −0.2 demand. This is a genuine sign reversal of the current net obligation, not merely a negative command derivative or a small move back toward the anchor. Because measurement is invalid, 0.6 s is a **bookkeeping/directional** divergence, not a tick at which actuator fault can be judged.

At 0.6 s, [`_process_invalid`](v0_2/examples/phase5_r5_2_1r4_1_deferred_engine.py) updates `deferred_demand.expected_direction` to −1 and logs `REVERSAL`, but does not supersede the active positive epoch. The R4 base's material-reversal branch requires both `command_event` and `observable`; its `observable` also requires valid measurement. It therefore does not run during the outage. The base nevertheless records `last_command = 0.3` at that tick.

At **1.2 s**, recovery logs `RECOVERY_REEVALUATION`, but [`_process_recovery`](v0_2/examples/phase5_r5_2_1r4_1_deferred_engine.py) creates a directional epoch only when no active epoch exists or the old one has closed. The old positive epoch is still active, so no negative epoch is installed. The base then sees no new command event (0.3 was already recorded at 0.6 s), so it also skips its reversal branch. The deferred record is consumed. With epoch direction +1 and command 0.3 below the 0.5 progress command reference, calculated directional demand is clamped to zero; expected motion stays zero and `HANDOFF_PENDING` persists through 3.0 s.

The first **observable failure to evaluate the actuator** occurs at the valid 1.2 s recovery tick. This is distinct from the first directional bookkeeping divergence at 0.6 s.

## Root-cause classification

| Proposed class | Audit verdict | Evidence |
|---|---|---|
| `DIRECTIONAL_OBLIGATION_NOT_SUPERSEDED` | **Primary** | At 0.6 s deferred direction becomes −1 while the active epoch remains +1; no new epoch event occurs. |
| `REVERSAL_CLASSIFICATION_WRONG` | Not supported | Both instantaneous command change (−0.4) and current net demand (−0.2) are negative; the net demand is material, not just a partial retreat toward 0.5. |
| `RECOVERY_REEVALUATION_USES_STALE_DIRECTION` | **Secondary manifestation** | Recovery records reevaluation at 1.2 s but keeps the +1 epoch; no new command event remains to trigger the base reversal path. |
| `PAIRED_REFERENCE_DIRECTION_CONFLICT` | Not evidenced by this trace | Resolved pair and progress pair are both 0.5/0.5 throughout. No unilateral reference reset occurs. A future revision must still prove pair consistency for any superseding obligation. |

The audit supports separating watch/evidence continuity from active directional obligation. It **does not** decide when or how a new direction should supersede an epoch, how to transfer or qualify fault evidence across direction changes, or whether a checkpoint must be re-established. Those are R4.2 design decisions to pre-register and test, not changes made here.

Ten identical R41-7 replays produced the same canonical snapshot SHA-256, `6a4450319cdff87085e64bd09c3960991c3741e428d7a8474ac1bbae80ffb814`. Every replayed input prefix produced the same record prefix as the full replay. The failure is deterministic and prefix-causal on this fixture; these checks do not turn the blocked candidate into a valid controller.

## C9R non-gate comparison

On the unchanged, in-domain C9R source, the historical R1a anchor sequence is A=0.35 at 0.0 s, B=0.51 at 1.2 s, C=0.67 at 4.0 s. R4 and R4.1 both produce the same command-anchor values at 0.0, 1.0, and 3.8 s; paired measurement anchors at B and C are approximately 0.39992 and 0.55323. Epochs start at 0.6 and 3.4 s in both versions; R4/R4.1 close them 0.2 s earlier. R4.1 deferred-demand logic adds no change here. This is **non-gate context only**: no C9R pass/fail verdict is assigned by R4.1A, and no causal connection to the R41-7 directional bug is established.

## Audit disposition

`R4_1A_ROOT_CAUSE_CLASS = DIRECTIONAL_OBLIGATION_NOT_SUPERSEDED` with secondary recovery use of stale direction. R4.1 remains `MEASUREMENT_RECOVERY_STILL_MASKS_SILENT_FAULT`. No R4.2 semantics, production port, final feedback baseline, Phase 6, or Git commit/push were performed.
