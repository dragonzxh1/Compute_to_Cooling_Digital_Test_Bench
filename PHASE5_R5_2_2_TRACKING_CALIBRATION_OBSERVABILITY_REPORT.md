# Phase 5R5.2.2 — tracking calibration and observability

**Gate: `FIXTURE_TRACKING_CALIBRATION_AND_OBSERVABILITY_CLOSED` — generic numerical fixture only.** No production Safety, controller, actuator, sensor or plant file was changed. This authorizes review of a future R5.2.1R specification attempt, **not** a direct R5.3 production port, final feedback baseline or Phase 6.

## Why this phase exists

R5.1 identified a false `DEGRADED` during a normal cold actuator handoff. R5.2 distinguished initial nominal movement from silent non-response using released speed, but R5.2.1 stopped because continuous tracking lacked a calibrated observation foundation. This phase measures what the current *generic simulator fixture* can reveal; it does not design continuous Safety epoch/recovery logic. The R5 directional PI candidate remains Kp 4500, Ki_hot 110, Ki_cold 130, Kd 0, 0.1 K blend, one integral state and unchanged anti-windup. Its controller is not run during these open-loop calibration tests.

Registration SHA-256: `3f847abbe78f1705d4a23b18f13f4655701e99e4179ff30b806e538753aa24fc`. The source R5/R5.1/R5.2 and R5.2.1 hashes were checked before experiments. The first R5.3 attempt remains historically blocked. The pre-registered step set, three meshes, margin rule and test-only faults were not changed after results were observed.

## Model and parameter audit

| Parameter | A/B/C/D | Source | Fixture calibratable? | Real hardware later? |
|---|---|---|---|---|
| Command delay, bounds, ramp, lag | A | `PumpActuatorConfig` | Yes, current configured values | Vendor/bench/system identification |
| Sensor period, release delay, validity age | A | `SensorConfig` | Yes, current configured values | Controller/DAQ timing measurements |
| Nominal expected displacement and response opening | B | Actuator lag/ramp/delay plus sensor schedule | Yes | Validated device model and timestamp timing |
| Stationary released-speed variation and mesh spread | C | Registered open-loop runs | Yes | Bench measurement and uncertainty analysis |
| Modeled stochastic speed noise | A: absent | `LocalMeasurement.sample` copies actuator speed without random perturbation | Exactly zero **in this model** | Sensor datasheet/bench noise |
| Speed quantization / physical resolution | D: not modeled | No digitization in `LocalMeasurement.sample` | No physical resolution can be inferred | Sensor datasheet/bench resolution |
| Timestamp representation | B | Integer nanosecond fields | 1 ns representation, **not** clock accuracy | Clock/synchronization measurement |
| Material step and old tracking mismatch | A | R5.2 registration and `SafetySupervisor` | Audit provenance only | New hardware qualification; not copied as defaults |

The required [generic profile schema](phase5_tracking_profile_schema.json) defines `ActuatorTrackingProfile`, `SensorObservationProfile` and `TrackingQualificationProfile` with units, provenance, ranges and calibration status. The [fixture profile](phase5_r5_2_2_fixture_tracking_profile.json) supplies current simulator values with per-parameter provenance and explicit `NOT OEM / NOT NVIDIA GB300 / NOT HARDWARE VALIDATION` labels. No production loader was added.

## Static released-speed characterization

Each fixed 0.3/0.5/0.7/0.9 command was held for 3 s, with the final 2 s analyzed at each 0.2/0.1/0.05-s physics mesh; ten deterministic runs were performed per speed/mesh. All pump-speed measurements in the stable window were `VALID`, released at their sample timestamps. The measurement model has no stochastic speed-noise injection and no speed quantization. Zero stationary variation below is a property of this deterministic numerical fixture, **not** a claim that real sensors have zero noise or infinite resolution.

| Command | Physics dt (s) | Mean measured speed | Peak-to-peak | Std dev | Max sample delta | Source of observed variation |
|---:|---:|---:|---:|---:|---:|---|
| 0.3 | 0.2 / 0.1 / 0.05 | 0.3 | 0 | 0 | 0 | None in modeled speed channel |
| 0.5 | 0.2 / 0.1 / 0.05 | 0.5 | 0 | 0 | 0 | None in modeled speed channel |
| 0.7 | 0.2 / 0.1 / 0.05 | 0.7 | 0 | 0 | 0 | None in modeled speed channel |
| 0.9 | 0.2 / 0.1 / 0.05 | 0.9 | 0 | 0 | 0 | None in modeled speed channel |

The maximum common-timestamp measured-speed difference between coarse and fine meshes was also 0. This does not equate floating-point epsilon with sensor resolution. The preregistered floor is `max(stationary peak-to-peak, mesh spread, modeled quantization) = 0` for this fixture. The preregistered conservative threshold is `max(R5.2 diagnostic 0.01, 2 × floor) = 0.01` speed fraction. The factor 2 and R5.2 floor were fixed *before* fault runs; neither was tuned to make the stuck case pass.

## Open-loop step observability and response window

Initial speed 0.5; registered magnitudes 0.02, 0.1, 0.2 and 0.3 in both directions; 4-s run at each mesh. The released measured-only evaluator sees only command/time, released speed/time/quality and the precomputed fixture profile. Offline raw ACTUAL movement is retained separately for audit and is never an evaluator input.

| Step magnitude | Direction | First qualified released progress at dt 0.2 / 0.1 / 0.05 s | Observable? | Notes |
|---:|---|---|---|---|
| 0.02 | Up and down | 1.0 / 1.0 / 1.0 s | Yes | Small step needs longer to exceed 0.01 |
| 0.1 | Up and down | 0.4 / 0.4 / 0.4 s | Yes | Sample/release timing dominates |
| 0.2 | Up and down | 0.4 / 0.4 / 0.4 s | Yes | Medium repeat group: 10/10 identical each direction |
| 0.3 | Up and down | 0.4 / 0.4 / 0.4 s | Yes | Within 0.3–0.9 bounds |

These values are *observed fixture outputs*. The parameter-derived opening calculation finds the first released sample after command delay for which `min(ramp × active_time, step × (1−exp(−active_time/tau))) >= 0.01`. Here `active_time = max(0, sample_time − command_time − configured_delay)`. It predicts the same 0.4/1.0-s qualifying samples. The first offline ACTUAL movement can occur at 0.4/0.3/0.25 s for the three physics meshes; only released measurements, not that hidden timing, qualify progress. Response opening is distinct from any future fault-confirmation requirement. An arbitrarily smaller command that cannot cross 0.01 in the registered window must be `NOT_OBSERVABLE_FOR_TRACKING_QUALIFICATION`, not “stuck.” The old 0.15 tracking *error tolerance* measures mismatch size, whereas 0.01 measures visible *movement*; they are not interchangeable. The R5.2 material delta 0.15 is `SUPPORTED_BY_FIXTURE_OBSERVABILITY` because all registered 0.1–0.3 steps were visible, but remains an unapproved diagnostic fixture threshold.

## Reversal, moving command and later silent non-response

The test-only reversal issues 0.5→0.7→0.3 and 0.5→0.3→0.7, reversing at 1.0 s before full settlement. The released speed at the reversal is the new measured anchor. In both directions the first new-direction displacement of at least 0.01 is released at 1.4 s. The previous direction's trend persists through the 1.2-s sample because the new target is subject to the configured delay; the new trend is visible at 1.4 s. Each reversal trace repeated identically 10/10. This characterizes observable evidence only; it does **not** define epoch reset or fault escalation.

With same-direction commands 0.6, 0.7 and 0.8 issued at 0, 0.4 and 0.8 s, a normal actuator reaches qualified measured progress at 0.4 s while a test-only silently stuck actuator never does in the registered 4-s window. After a successful 0.5→0.7 startup, a later 0.9 command at 3.0 s with test-only physical sticking at that instant produces **no** qualified new-direction progress by 6.0 s. Thus loss of visible progress after startup is measurable in this fixture, but deciding a *continuous Safety fault* still belongs to R5.2.1R/R5.3R.

## Measurement loss and recovery

The existing sensor's pump-speed channel is made `MISSING` from 0.4 to before 1.2 s; no fallback raw ACTUAL is used. The first valid released speed after recovery is at 1.2 s with the frozen 0.2-s sample period and zero local release delay. Invalid samples never qualify as progress. The recovered sample can be observed at 1.2 s, but whether a future Safety qualifier must re-anchor or retain earlier suspicion is **not specified here**. The current fixture's normal released-speed age at sample ticks is 0; its configured maximum validity is 1.0 s. Neither is a hardware latency limit.

## Offline boundaries, conservation, repeatability and uncertainty

The evaluator has a typed whitelist and each prefix produces the same decisions as the matching prefix of the full trace; no scenario/fault identity, raw ACTUAL or future sample enters it. The command objects are typed as PLC-produced *test-harness* open-loop commands; Safety still produces no commands. All physical runs pass the registered conservation bounds. Maximum mass residual was `2.78e-17 kg/s`, maximum absolute per-step energy residual `5.60e-10 J`. Static 0.3/0.5/0.7/0.9 each repeated 10/10 at each mesh; positive/negative medium steps, both reversals and post-startup stuck each repeated 10/10 with identical trace hashes. The threshold-driving stationary and mesh floors are both 0, so the 0.01 fixture threshold does not change across the three meshes.

The uncertainty is bounded **only inside this deterministic model**. Stochastic sensor noise, ADC quantization, clock error, command quantization and hardware response dispersion are unmodeled. Real equipment needs vendor/bench speed resolution and noise, timestamp and telemetry delay characterization, actuator delay/ramp/lag identification and validation under reversals and moving commands. No current fixture number is a hardware default. See [machine-readable evidence](phase5_r5_2_2_tracking_calibration_evidence.json) and the [eight-panel figure](docs/results/phase5_r5_2_2_tracking_observability.png).

## Gate

`PHASE5_R5_2_2_GATE_STATUS = FIXTURE_TRACKING_CALIBRATION_AND_OBSERVABILITY_CLOSED`. This means the **generic numerical fixture** now has a pre-registered, measured-only observability threshold and characterized response timing, reversals, moving commands, later non-response and sensor loss. It does **not** close real-hardware calibration or continuous Safety semantics. **STOP for user review**; do not automatically rerun R5.2.1, modify production Safety, restart R5.3, freeze final feedback, or start Phase 6.
