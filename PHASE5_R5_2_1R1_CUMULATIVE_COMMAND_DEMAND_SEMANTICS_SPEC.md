# Phase 5R5.2.1R1 — cumulative command demand (offline revision)

Gate: `CUMULATIVE_COMMAND_DEMAND_VALIDATION_FIXTURE_OUT_OF_PROFILE_DOMAIN` — **blocked**. No production Safety change or R5.3R port is authorized from this result.

## Why this revision exists

R5.2.1R found that a pump stuck at measured speed 0.5 could receive PLC commands 0.5 → 0.6 → 0.7 → 0.8 without a tracking epoch. Each 0.1 step was below the frozen material threshold, though the **net** displacement from the last resolved operating point became 0.3. Its historical gate, `TRACKING_EPOCH_SEMANTICS_CAN_MASK_SILENT_FAULT`, remains unchanged in the prior evidence. The earlier S1–S16, original invariants 1–8 and prefix-causality checks passed; they simply missed this path.

## Revised semantic contract

The `qualified_command_anchor` is the PLC command for the most recent successfully resolved qualified tracking obligation. At takeover, no previous PLC command is invented from preparation speed. A directly observed valid PLC command and released pump-speed pair within the *frozen* tracking tolerance may establish an initial steady baseline; otherwise the previous startup handoff applies and the anchor is absent until resolution. Every anchor change logs its reason, timestamp, previous/new value and source epoch.

Current signed net demand is `current_plc_command - qualified_command_anchor`. Only its magnitude is compared to the frozen material threshold and frozen delay/ramp/lag/sensor observability model. **Never** sum absolute PLC command travel: 0.5 → 0.6 → 0.5 → 0.6 → 0.5 repeatedly has net demand near zero, not an accumulating fault demand. The first profile-qualified cumulative net demand creates an epoch at that command timestamp; earlier small steps are not backdated. The response window uses the frozen profile, never a new fixed grace.

During an unresolved epoch the qualified anchor remains fixed. Later same-direction commands may update latest command and expected envelope, but neither epoch/watch age nor valid fault evidence is reset. A larger demand cannot postpone an already-earned response opportunity. Partial qualified motion enters the frozen `TRACKING_PROGRESS` state but does not itself advance the anchor. Only valid, qualified resolution to `STEADY_TRACKING` within the frozen tracking tolerance advances it. Returning to the anchor **before** any qualifying epoch creates no fault evidence. Returning **after** an epoch starts cannot erase an unresolved watch or accrued valid deficit. Material reversal retains the R5.2.1R directional-epoch replacement and no-motion-watch carry rules; the anchor never jumps to a reversal command.

Invalid or stale released speed displays `INSUFFICIENT_MEASUREMENT` and retains anchor, epoch, watch and causal age. Invalid samples neither establish motion nor increment confirmation. At first valid recovery, the prior context is evaluated without new grace. The six states, frozen suspected/confirmed criteria, suspected recovery and top-level confirmed-fault reset authority are unchanged. The adapter reads only released command/measurement history and the frozen profile—no raw ACTUAL, fixture identity, future measurement or production ActuatorCommand.

## Validation outcome

Pre-registration SHA-256: `349faabfeda2661c472044bf572e6073d49c76d9f4042bc1158d37ff13a8ead1`. Frozen profile SHA-256: `9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8`. The first execution of the registered suite reported semantic passes for C1–C12, S1–S16 plus S16 variant, invariants 1–12 and prefix causality. A subsequent domain audit found registered **C9 invalid**: its second command series reaches 1.0 while the immutable fixture `speed_max` is 0.9. Therefore C9 is a validation **FAIL**, despite its observed state transitions; the overall gate cannot pass. C9 input, profile, thresholds and engine were not changed after outcomes.

| Case | Result | What it checks |
| --- | --- | --- |
| C1 | PASS | Small steps start epoch, then suspect and confirm stuck |
| C2 | PASS | Normal response progresses and resolves anchor |
| C3 | PASS | Downward normal/stuck variants |
| C4 | PASS | Chatter does not accumulate path length |
| C5 | PASS | Epoch starts at first net qualification timestamp |
| C6 | PASS | Return before qualification leaves no obligation |
| C7 | PASS | Return after response opportunity retains watch |
| C8 | PASS | Normal/stuck material reversal retains prior rules |
| C9 | **FAIL** | Registered 1.0 command exceeds profile maximum 0.9 |
| C10 | PASS | Partial progress does not advance anchor |
| C11 | PASS | Sensor loss retains cumulative obligation |
| C12 | PASS | Mixed small-step attack reaches stuck confirmation |

Historical S1–S16 and S16 variant: all PASS. Original invariants 1–8 and added invariants 9–12: all PASS within the executed traces. Prefix-causality replay: PASS. These green checks do not cure C9's out-of-domain fixture input.

The required audit tables for C1, C2, C4, C7, C9 and C12 are stored as `audit_tables` in [evidence](phase5_r5_2_1r1_cumulative_command_demand_evidence.json), with time, PLC command, qualified anchor, signed net demand, demand class, epoch/watch activity, released speed and tracking state. The [machine-readable spec](phase5_r5_2_1r1_cumulative_command_demand_spec.json) and [eight-panel figure](docs/results/phase5_r5_2_1r1_cumulative_command_demand.png) accompany this report.

## Portability and stop boundary

The bookkeeping is parameterized by a tracking profile, but fixture-domain validation is incomplete. Real pump sensor noise/resolution, timestamp jitter, actuator delay/slew/lag, telemetry validity and tracking tolerance all require hardware calibration. Nothing here is OEM, NVIDIA GB300 or real-hardware validation. The R5 directional PI remains a candidate, not a frozen final baseline. Production Safety, controller, actuator, sensor and plant sources remain hash-frozen. Stop for review; a newly registered revision must correct the invalid C9 fixture case before claiming `CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED`.
