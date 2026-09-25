# C2C-DTB V0.2 Phase 5R3 Bidirectional Controller Revision Report

## 1. Why Phase 5R3 exists

Phase 5.1R2 showed that the frozen `outer_a` controller passed WARM_CAPTURE but did not settle from COLD_CAPTURE within the pre-registered 180 s window. Phase 5R3 therefore re-evaluated the three existing outer candidates with bidirectional regulation as a hard feasibility condition. It did not create or tune any new gains.

## 2. What remained frozen

The target remained 313.71072595542387 K and the inner controller remained `inner_b` with Kp = 1.5e-5, Ki = 4e-6, Kd = 0. The plant, 120 W/device workload, FWS, CDU/HX, hydraulics, coldplate model, base DP, pump limits and dynamics, sensor/controller clocks, Safety policy, ownership, measurement architecture, warm/cold preparation, 180 s duration, final 30 s window, and settling definition were unchanged.

Registration SHA-256: `7636af8958f6c87a2516ba1cc90ac357fd7f1812a4234ed97749a434c5a2bbf6`.

Source R2 baseline SHA-256: `891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1`.

## 3. Eighteen-run matrix

| Candidate | Warm 0.2 | Cold 0.2 | Warm 0.1 | Cold 0.1 | Warm 0.05 | Cold 0.05 | Bidirectional Feasible |
|---|---|---|---|---|---|---|---|
| `outer_a` | PASS, 125.4 s | FAIL, no settle | PASS, 125.2 s | FAIL, no settle | PASS, 125.2 s | FAIL, no settle | FAIL |
| `outer_b` | PASS, 120.6 s | FAIL, no settle | PASS, 120.6 s | FAIL, no settle | PASS, 120.4 s | FAIL, no settle | FAIL |
| `outer_c` | PASS, 116.6 s | FAIL, no settle | PASS, 116.6 s | FAIL, no settle | PASS, 116.6 s | FAIL, no settle | FAIL |

All 18 registered runs completed. There were no solver-invalid, ownership-invalid, or conservation-invalid runs.

## 4. Warm-side results

All three candidates passed WARM_CAPTURE on all three physics meshes. At the canonical 0.2 s mesh, increasing outer gain reduced settling time from 125.4 s (`outer_a`) to 120.6 s (`outer_b`) and 116.6 s (`outer_c`). Their final-window means were 313.732295 K, 313.649120 K, and 313.575977 K. All were inside the frozen target band, with interior final pump speeds and zero final-window saturation.

## 5. Cold-side results

All three candidates moved in the correct direction, reduced pump speed to an interior operating point, and avoided final-window saturation. None entered the lower target-band boundary of 313.210726 K by 180 s on any mesh.

At dt = 0.2 s:

- `outer_a` final-window mean: 312.955254 K; final actual pump: 0.674176.
- `outer_b` final-window mean: 313.001035 K; final actual pump: 0.649830.
- `outer_c` final-window mean: 313.046466 K; final actual pump: 0.627074.

`outer_c` came closest but remained about 0.164 K below the lower qualification boundary in its final-window mean. The fixed 180 s window was not extended.

## 6. Candidate feasibility

| Candidate | Warm settle | Cold settle | Warm IAE | Cold IAE | Total TV | Pump energy | Safety PASS |
|---|---:|---:|---:|---:|---:|---:|---|
| `outer_a` | 125.4 s | no settle | 169.8800 | 129.6750 | 0.72017 | 3213.34 J | FAIL |
| `outer_b` | 120.6 s | no settle | 165.3161 | 126.6318 | 0.80563 | 3273.20 J | FAIL |
| `outer_c` | 116.6 s | no settle | 162.0006 | 123.5982 | 0.89143 | 3331.42 J | FAIL |

Bidirectional feasibility is evaluated before IAE, TV, or energy. Therefore none of the candidates can be selected, even though `outer_c` has the lowest total canonical thermal IAE.

## 7. Safety behavior

Every warm run used `FF_DISABLED` for 2.0 s and then remained `NORMAL`. Every cold run, for every candidate and mesh, reproduced the same startup sequence:

1. `DEGRADED` for 0.4 s with `ACTUATOR_TRACKING_PENDING`.
2. `FF_DISABLED` recovery until 2.6 s.
3. `NORMAL` for the remainder of the run.

The restrictive startup behavior violates the unchanged Phase 5.1R2 Safety acceptance rule. However, `COMMON_STARTUP_SAFETY_ACCEPTANCE_BLOCKER` does not apply because all candidates also failed the independent cold thermal settling and final-window temperature requirements.

## 8. Numerical sensitivity

The 0.1-to-0.05 s total-IAE sensitivities were small and the candidate differences were distinguishable:

| Pair | Canonical IAE difference | Numerical uncertainty bound | Result |
|---|---:|---:|---|
| `outer_a` vs `outer_b` | 7.60717 K·s | 0.17233 K·s | distinguishable |
| `outer_a` vs `outer_c` | 13.95621 K·s | 0.16924 K·s | distinguishable |
| `outer_b` vs `outer_c` | 6.34904 K·s | 0.16534 K·s | distinguishable |

All candidates reproduced the same warm-pass/cold-fail decision at dt = 0.2, 0.1, and 0.05 s. The gate result is therefore not caused by mesh ambiguity.

## 9. Final candidate selection

Selected candidate: **none**.

No candidate passed the required bidirectional feasibility prerequisite. No `phase5_r3_candidate_baseline.json` was created, and the frozen R2 baseline was not overwritten.

## 10. Ownership and conservation

The static and runtime R1 ownership audit passed. PLC remained the sole final `ActuatorCommand` producer, and all 18 run lineages were complete. No hidden TRUE state or future data was supplied to a controller.

All 18 runs passed conservation. Maximum mass residual was 2.7755575615628914e-17 kg/s. Maximum absolute step energy residual was 5.909441824769601e-10 J.

## 11. Limitations

This is a generic numerical fixture, not OEM, NVIDIA, GB300, hardware, or production-PLC validation. Historical HOLDOUT-01 was not used or executed for selection. Phase 5R3 tests only three previously registered gain sets; it does not prove that no possible feedback controller can meet the requirement.

## 12. Gate status

**PHASE5_R3_GATE_STATUS: NO_EXISTING_OUTER_CANDIDATE_HAS_BIDIRECTIONAL_REGULATION**

Blocking issues:

- All three existing candidates fail COLD_CAPTURE settling at all three meshes.
- All three cold cases finish outside the final target band.
- All three reproduce the restrictive startup `DEGRADED / ACTUATOR_TRACKING_PENDING` event.

No new PID was invented. A future tuning phase requires a new pre-registration and explicit user authorization. Phase 6 remains unauthorized.

## Regression

The isolated V0.2 control, plant, and thermal test suites passed: 220/220 tests, including 9 Phase 5R3 tests and the historical Phase 5.1R2 tests. V0.1 passed 72/72 tests. Ruff passed with cache bypassed. The historical Phase 5.1R2 blocked result and its file hash remained unchanged.
