# C2C-DTB V0.2 Phase 5.1R2 Feedback Qualification Report

## 1. What was tested

The final frozen Phase 5R2 feedback baseline was tested at a constant 120 W/device for 180 s from independently prepared warm and cold plant states. No controller gain, target, plant parameter, timing, actuator, sensor, Safety, FWS, CDU, or hydraulic setting was changed. The controller received released measured data only and started with no hidden history or integrator warm-start.

The result is **BLOCKED**. Warm capture passed. Cold capture moved in the correct direction but did not enter the frozen target band by 180 s.

## 2. Why two starting directions were used

The target, 313.71072595542387 K, is the midpoint of the frozen plant authority endpoints at pump speeds 0.3 and 0.9. A valid nominal controller therefore has to reach it from both a hotter, low-cooling state and a colder, high-cooling state. Passing only one direction is insufficient.

## 3. Baseline integrity

| Item | Result |
| --- | --- |
| Final R2 baseline file SHA-256 | `891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1` |
| Qualification registration SHA-256 | `a7466babe2cd32a016db138dc83ccd1c9b9367ca6a3fd43af0f67490cab33c5b` |
| Control-core SHA-256 | `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579` |
| Frozen plant SHA-256 | `d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254` |
| Referenced baseline hashes | PASS; every SHA-256 field was accounted for and verified against its live artifact or historical provenance |
| Frozen target / controller | 313.71072595542387 K; `inner_b`; `outer_a` |
| Integrity gate | **PASS** |

The warm and cold preparation endpoints reproduced their historical final-window means exactly: 314.7243256180813 K and 312.69712629276637 K. Their normalized initial-state hashes are `463c24e3d0b70ec0f52292fc6276d9978b933131aba9bb1868453dac55273f7f` and `f0ae5c3f34a1db08438a64f464308f43d23c3891c15dad93ec26986fa37544d5`.

## 4. Warm capture result

At the registered 0.2 s physics step, the released measured temperature started at 315.074463 K, peaked at 315.422287 K, and settled at 125.4 s. The final 30 s mean was 313.732295 K with a 313.570135–313.901852 K range, fully inside the 313.210726–314.210726 K band. Final measured temperature was 313.570135 K.

The final actual pump speed was 0.722266. Initial minimum-bound occupancy was permitted by the registration; command and actual bound occupancy were both zero in the final 30 s. Safety was `FF_DISABLED` for 2.0 s and then `NORMAL` for the rest of the run. Control direction was correct.

**WARM_CAPTURE: PASS.**

## 5. Cold capture result

At the registered 0.2 s physics step, the released measured temperature started at 312.783458 K and moved upward as required, reaching a peak of 313.080359 K. It never entered the lower qualification boundary of 313.210726 K. The final 30 s mean was 312.955254 K with a 312.908434–312.998798 K range. Final measured temperature was 312.908434 K.

The final actual pump speed was 0.674176 and was strictly interior. Final-window bound occupancy was zero. The cold start nevertheless entered `DEGRADED` for 0.4 s because of `ACTUATOR_TRACKING_PENDING`, then used `FF_DISABLED` recovery before reaching `NORMAL` at 2.6 s. Control direction was correct, but the frozen Safety acceptance allowed startup `FF_DISABLED`, not a restrictive `DEGRADED` interval.

**COLD_CAPTURE: FAIL — finite settling was not achieved.**

## 6. Settling result

| Case | dt 0.2 s | dt 0.1 s | dt 0.05 s | All meshes pass |
| --- | ---: | ---: | ---: | --- |
| WARM_CAPTURE | 125.4 s | 125.2 s | 125.2 s | PASS |
| COLD_CAPTURE | not settled | not settled | not settled | FAIL |

Warm adjacent settling-time differences were 0.2 s and 0.0 s, below the registered 2.0 s limit. Cold settling-time consistency cannot pass because no cold mesh produced a finite settling time.

## 7. Final pump operating point

All six final actual pump speeds were interior: warm 0.722216–0.722266 and cold 0.674176–0.674205. Every run had zero final-window commanded and actual bound time. The failure is therefore not `CAPACITY_BOUND_REGULATION`.

## 8. Safety behavior

Warm runs used only the permitted startup `FF_DISABLED` state followed by `NORMAL`. Every cold mesh reproduced the same 0.4 s `DEGRADED` interval caused by actuator tracking qualification, followed by `FF_DISABLED` recovery and then `NORMAL`. No `DERATE_REQUESTED`, `PROTECTED`, or `FAULT` state occurred. Under the pre-registered acceptance rule, the cold `DEGRADED` interval is classified as `E_SAFETY_RESTRICTION_REQUIRED`.

## 9. Physics-step convergence

Warm qualification passed on all meshes. Cold continuous metrics were numerically close: the 0.1-to-0.05 s final-window mean difference was 0.000227 K, temperature IAE difference 0.035774 K·s, DP IAE difference 13.944 Pa·s, and pump-energy relative difference 0.000145. These values meet their numeric tolerances.

The formal convergence gate is still **FAIL**, because the frozen rule requires every mesh to settle. This is a qualification failure consistently reproduced across meshes, not evidence that the physics solution changes materially with step size.

## 10. Ownership and provenance

The R1 static and runtime ownership audit passed. PLC remained the sole `ActuatorCommand` producer, Safety supplied restrictions/envelopes only, actuator inputs came from PLC output, and the recorded control lineage was complete in all six runs. No TRUE temperature, future input, or raw actual actuator state was supplied to the controller.

**OWNERSHIP / PROVENANCE: PASS.**

## 11. Mass and energy conservation

All six runs passed. The maximum mass residual was 2.7755575615628914e-17 kg/s, below 1e-8 kg/s. The maximum absolute step energy residual was 5.727507357278228e-10 J, below 0.001 J.

## 12. Repeatability

Ten consecutive WARM_CAPTURE executions at dt = 0.2 s produced the identical result hash `f3ea9b958a47c4355948c7727e8a61074077345b7befad358cd65a4089f90af5`. The post-GC retained live-object memory span was 224 bytes, below the registered 3,000,000-byte limit.

**REPEATED STABILITY: PASS.**

## 13. Limitations

This is a generic numerical fixture, not OEM, NVIDIA, GB300, hardware, or production-PLC validation. The test proves neither feedforward behavior nor disturbance rejection. The run duration and acceptance thresholds were frozen before closed-loop results; extending the cold run or changing gains would be a new phase, not a repair inside this qualification.

The occasional Windows native Python process exit observed during batch reruns did not change completed-run hashes or qualification metrics; successful isolated reruns were used for the evidence. This environment issue should remain separate from the deterministic control result.

## 14. Gate result

**PHASE5_1R2_GATE_STATUS: BLOCKED_FINAL_FROZEN_FEEDBACK_NOMINAL_REGULATION_NOT_QUALIFIED**

Blocking classifications:

- `B_COLD_SIDE_CANNOT_SETTLE`
- `E_SAFETY_RESTRICTION_REQUIRED`
- `F_NUMERICAL_CONVERGENCE_FAILURE` (because all meshes must settle)

No retuning was performed. Phase 6 and feedforward remain not started.

Evidence:

- `phase5_1r2_qualification_registration.json`
- `phase5_1r2_nominal_result.json`
- `docs/results/phase5_1r2_nominal_regulation.png`
