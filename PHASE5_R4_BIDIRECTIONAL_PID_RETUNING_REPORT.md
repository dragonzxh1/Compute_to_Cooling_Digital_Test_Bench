# C2C-DTB V0.2 Phase 5R4 Bidirectional Outer PI Retuning Report

## 1. Why the old range was insufficient

Phase 5R3 tested the existing outer controllers and found that each passed WARM_CAPTURE but failed COLD_CAPTURE within the frozen 180 s window. Phase 5R4 was authorized to test a bounded, pre-registered grid of stronger outer PI gains. This is tuning evidence for a generic numerical fixture, not independent validation.

## 2. What changed and what remained frozen

Only the outer PI gains varied. The target stayed at 313.71072595542387 K, the inner controller stayed `inner_b` (Kp 1.5e-5, Ki 4e-6, Kd 0), and all plant, FWS, CDU/HX, hydraulic, coldplate, pump, sensor, clock, PLC, Safety, ownership, and measurement parameters stayed frozen. The workload remained 120 W/device. Both physical initial states reproduced the exact historical Phase 5.1R2 state hashes before candidate evaluation.

The R4 registration was written before the first new-gain run. Its SHA-256 is `b75eb532e825eea4960956c0812e19eb70ca3055c22a483b5b435f665a1e93b8`. The source R2 baseline SHA-256 is `891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1`, and the source R3 evidence SHA-256 is `51c5fc07b5739cad6995a9d479ae4fa978fa3b0f4f9c46423e340738b83371cd`.

## 3. The 16-candidate grid

The registered grid was the Cartesian product of Kp = 3000, 4000, 5000, 6000 and Ki = 60, 80, 100, 120, with Kd = 0 throughout. `R4-KP3000-KI60` is the historical `outer_c` anchor. No additional candidate was introduced after seeing results.

## 4. Stage A: 32-run result

All 16 candidates completed both 180 s training cases at physics dt = 0.2 s. All 32 runs were valid. `—` means no finite settling time in the frozen window, so worst-side settling is also unavailable.

| Candidate | Warm settle (s) | Cold settle (s) | Worst settle (s) | Warm IAE (K·s) | Cold IAE (K·s) | Total TV | Pump energy (J) | Thermal feasible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R4-KP3000-KI60 | 116.6 | — | — | 162.00 | 123.60 | 0.891 | 3331.42 | FAIL |
| R4-KP3000-KI80 | 113.4 | — | — | 160.28 | 119.64 | 0.974 | 3413.91 | FAIL |
| R4-KP3000-KI100 | 110.4 | — | — | 159.29 | 115.59 | 1.064 | 3501.78 | FAIL |
| R4-KP3000-KI120 | — | 131.4 | — | 158.81 | 111.45 | 1.157 | 3594.55 | FAIL |
| R4-KP4000-KI60 | 116.6 | — | — | 161.36 | 124.47 | 0.910 | 3309.38 | FAIL |
| R4-KP4000-KI80 | 113.2 | — | — | 159.54 | 120.58 | 0.977 | 3387.86 | FAIL |
| R4-KP4000-KI100 | 110.4 | — | — | 158.48 | 116.61 | 1.059 | 3471.76 | FAIL |
| R4-KP4000-KI120 | — | — | — | 157.95 | 112.54 | 1.147 | 3560.59 | FAIL |
| R4-KP5000-KI60 | 116.6 | — | — | 160.76 | 125.31 | 0.938 | 3287.79 | FAIL |
| R4-KP5000-KI80 | 113.2 | — | — | 158.81 | 121.49 | 0.995 | 3362.39 | FAIL |
| R4-KP5000-KI100 | 110.4 | — | — | 157.67 | 117.58 | 1.063 | 3442.42 | FAIL |
| R4-KP5000-KI120 | 107.8 | — | — | 157.10 | 113.60 | 1.144 | 3527.43 | FAIL |
| R4-KP6000-KI60 | 116.6 | — | — | 160.21 | 126.13 | 0.970 | 3266.69 | FAIL |
| R4-KP6000-KI80 | 113.2 | — | — | 158.12 | 122.37 | 1.021 | 3337.52 | FAIL |
| R4-KP6000-KI100 | 110.2 | — | — | 156.89 | 118.53 | 1.079 | 3413.81 | FAIL |
| R4-KP6000-KI120 | 107.8 | — | — | 156.25 | 114.61 | 1.149 | 3495.09 | FAIL |

The IAE, TV, and pump energy columns are recorded characterization values, not a ranking that can override the hard bidirectional requirement.

## 5. Warm and cold balance

Fourteen candidates settled from the warm side; only `R4-KP3000-KI120` settled from the cold side. That candidate reached cold settling at 131.4 s, with a final 30 s mean of 313.223504 K, just inside the lower band edge of 313.210726 K. Its warm run ended at 313.163367 K, below that edge, and did not settle through the end. Thus stronger integral action fixed one direction at the cost of the other in the observed grid. The neighboring `R4-KP4000-KI120` failed both directions; its cold final-window mean was 313.208051 K, just below the lower edge.

The failed runs did not show sustained final-window pump saturation or wrong control direction. The target and physical authority were not changed to rescue them.

## 6. Fine-mesh finalists and final R4 candidate

Stage A produced zero bidirectionally feasible candidates. The pre-registered stop condition therefore prevented selection of finalists. Stage B at dt = 0.1 and 0.05 s was **NOT EXECUTED**; settling-time consistency, fine-mesh continuous convergence, numerical distinguishability, and selected-candidate repeatability are **NOT APPLICABLE**. No final R4 candidate was selected. No `phase5_r4_candidate_baseline.json` or final R4 baseline was created.

## 7. Safety startup blocker

All 16 cold cases reproduced the same candidate-independent startup sequence: `DEGRADED` with `ACTUATOR_TRACKING_PENDING` at 0.2 s, `FF_DISABLED` recovery at 0.6 s, and `NORMAL` at 2.6 s. The `DEGRADED` duration was 0.4 s. Warm cases used permitted startup `FF_DISABLED` then `NORMAL`. The Safety state machine was not modified. This common startup issue remains a separate blocker for future full feedback qualification, but it was not the cause of the zero thermally feasible R4 candidates.

## 8. Ownership, information boundaries, mass, and energy

The R1 ownership audit and every executed run's PLC command lineage passed. Tuning used released measured data through the existing controlled-loop path, without future disturbances or HOLDOUT-01. All 32 runs passed mass and energy conservation. The maximum mass residual was 2.7755575615628914e-17 kg/s and maximum absolute step energy residual was 6.199272206686146e-10 J.

## 9. Repeatability, limitations, and gate

No candidate was selected, so the pre-registered 10 warm plus 10 cold repeatability sequence was not triggered. WARM_CAPTURE and COLD_CAPTURE are now training cases; they cannot later be described as unseen validation. A future frozen R4 controller, if one is found in a separately authorized revision, needs new independently pre-registered validation cases. This model is a generic numerical fixture, not OEM/NVIDIA/GB300/hardware validation.

**PHASE5_R4_GATE_STATUS: NO_R4_GRID_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION.**

The grid was not expanded. No target, plant, Safety, or inner-loop change was made. Phase 6 and Feedforward remain unauthorized.

Evidence: `phase5_r4_outer_tuning_registration.json` and `phase5_r4_outer_tuning_evidence.json`.

## 10. Regression verification

The dedicated R4 tests passed (6/6). The complete V0.2 control, plant, and thermal suites passed (77 + 49 + 100 = 226 tests). The V0.1 suite passed (72 tests). Ruff and `git diff --check` passed for the R4 code and working tree. No fine-mesh or repeatability run was performed because the Stage A stop condition was reached.
