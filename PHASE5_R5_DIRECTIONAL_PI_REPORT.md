# C2C-DTB V0.2 Phase 5R5 Directional Outer PI Structure Revision

## 1. Why symmetric PI was set aside

Phase 5R4.2 located a certified symmetric-PI feasibility gap at every bracketed Kp in its registered domain. At fixed Kp = 4500, the warm side still passed through Ki = 116.718750 but failed from 116.796875, while the cold side failed through Ki = 124.062500 and passed from 124.140625. A single common Ki could not satisfy both training cases inside that search domain. R5 tested the smallest new hypothesis: one proportional gain, one continuous integral state, and a measured-error-dependent integration gain. These historical boundaries guided the R5 grid; they were not assumed to predict directional behavior.

## 2. Structure, frozen scope, and preregistration

Kp was frozen at 4500 Pa/K and Kd at zero. The new [directional outer feedback](v0_2/control/directional_outer.py) chooses `Ki_hot` when released **measured** maximum device temperature is at least 0.1 K above target, `Ki_cold` when it is at least 0.1 K below target, and linearly blends the two within ±0.1 K. For error `e = T_measured − target`, blend `alpha = (e + 0.1) / 0.2` and `Ki_eff = (1 − alpha) × Ki_cold + alpha × Ki_hot`. This fixed law is an engineering assumption in a numerical test fixture, not a validated hardware control law.

There is only **one** `TrackingPID.integral` state. At each outer tick R5 changes only the immutable PID configuration's Ki value before calling the original PID update; the measured-actuator-echo back-calculation, clamping, proportional term, and derivative term remain unchanged. No direction-triggered reset or integral preload occurs. R5 substitutes this new outer class only while its dedicated simulation runs; the historical `pid.py`, `outer_feedback.py`, and `controlled_loop.py` files and their frozen hashes were not edited. The controller receives no scenario label, true temperature, raw actuator truth, or future disturbances.

The target remained 313.71072595542387 K; `inner_b`, plant, 120 W/device workload, FWS/CDU, hydraulics, coldplate, actuator, sensors, PLC, Safety, preparation states, all clocks, 180 s duration, ±0.5 K qualification band, 15 s dwell, final 30 s window, and conservation limits remained frozen. Warm/cold initial physical-state hashes matched the historical Phase 5.1R2 states; no controller prehistory or integral warm-start was used.

The [R5 registration](phase5_r5_directional_pi_registration.json) was written before any new directional-gain run. SHA-256: `61f48d159f208ce4ba8a7e5e958ccad31b659e24bfee69f199133fdf2cf52791`. Frozen source R4.2 registration SHA-256: `6c24855e76b4967c9fa3327a57dfcf796a54e58447208c233dff0b07820b1070`; R4.2 evidence SHA-256: `f84ac5dfb2694ae815fdcb9f6f069b05613e1409171e326b7087954fb7ebb47b`.

## 3. Exact candidate grid and Stage A

The 16 candidates were the full Cartesian product of `Ki_hot` = 110, 112, 114, 116 and `Ki_cold` = 124, 126, 128, 130, at physics dt = 0.2 s for both WARM_CAPTURE and COLD_CAPTURE. All **32/32 runs executed validly**. Twelve candidates passed both thermal directions; the four with `Ki_cold = 124` were warm-only. No candidate was added after seeing results.

The following table retains characterization metrics even for failed candidates. A finite cold settling time alone does not guarantee pass: the `Ki_cold = 124` runs failed the frozen final-window qualification gate. Energy is pump electrical joules summed across warm and cold runs.

| Candidate | Ki_hot | Ki_cold | Warm settle (s) | Cold settle (s) | Worst settle (s) | Total IAE (K·s) | TV | Energy (J) | BOTH_PASS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R5-KP4500-H110-C124 | 110 | 124 | 109.0 | 151.2 | 151.2 | 270.00 | 1.125 | 3453.56 | NO |
| R5-KP4500-H110-C126 | 110 | 126 | 109.0 | 138.4 | 138.4 | 269.59 | 1.128 | 3447.10 | YES |
| R5-KP4500-H110-C128 | 110 | 128 | 109.0 | 131.8 | 131.8 | 269.18 | 1.131 | 3440.68 | YES |
| R5-KP4500-H110-C130 | 110 | 130 | 109.0 | 127.2 | 127.2 | 268.77 | 1.134 | 3434.30 | YES |
| R5-KP4500-H112-C124 | 112 | 124 | 108.8 | 151.2 | 151.2 | 269.95 | 1.130 | 3468.99 | NO |
| R5-KP4500-H112-C126 | 112 | 126 | 108.8 | 138.4 | 138.4 | 269.54 | 1.133 | 3462.53 | YES |
| R5-KP4500-H112-C128 | 112 | 128 | 108.8 | 131.8 | 131.8 | 269.13 | 1.136 | 3456.11 | YES |
| R5-KP4500-H112-C130 | 112 | 130 | 108.8 | 127.2 | 127.2 | 268.72 | 1.139 | 3449.73 | YES |
| R5-KP4500-H114-C124 | 114 | 124 | 108.6 | 151.2 | 151.2 | 269.90 | 1.135 | 3484.43 | NO |
| R5-KP4500-H114-C126 | 114 | 126 | 108.6 | 138.4 | 138.4 | 269.49 | 1.138 | 3477.97 | YES |
| R5-KP4500-H114-C128 | 114 | 128 | 108.6 | 131.8 | 131.8 | 269.08 | 1.141 | 3471.55 | YES |
| R5-KP4500-H114-C130 | 114 | 130 | 108.6 | 127.2 | 127.2 | 268.67 | 1.145 | 3465.16 | YES |
| R5-KP4500-H116-C124 | 116 | 124 | 108.4 | 151.2 | 151.2 | 269.85 | 1.140 | 3499.89 | NO |
| R5-KP4500-H116-C126 | 116 | 126 | 108.4 | 138.4 | 138.4 | 269.45 | 1.143 | 3493.42 | YES |
| R5-KP4500-H116-C128 | 116 | 128 | 108.4 | 131.8 | 131.8 | 269.04 | 1.147 | 3487.00 | YES |
| R5-KP4500-H116-C130 | 116 | 130 | 108.4 | 127.2 | 127.2 | 268.62 | 1.150 | 3480.61 | YES |

### Ki_hot × Ki_cold feasibility map

| Ki_hot \ Ki_cold | 124 | 126 | 128 | 130 |
|---:|---|---|---|---|
| 110 | WARM_ONLY | BOTH_PASS | BOTH_PASS | BOTH_PASS |
| 112 | WARM_ONLY | BOTH_PASS | BOTH_PASS | BOTH_PASS |
| 114 | WARM_ONLY | BOTH_PASS | BOTH_PASS | BOTH_PASS |
| 116 | WARM_ONLY | BOTH_PASS | BOTH_PASS | BOTH_PASS |

In plain language, the cold side needed the stronger cold-direction integral gain, while the warm side retained a lower hot-direction gain. Splitting the gain by **measured error direction** produced overlap in this registered training grid, without a second integrator or scenario awareness.

## 4. Blend, continuity, oscillation, and chatter audit

Every outer-controller tick records measured error, region, Ki_eff, integral state before/after, measured applied-DP echo, and requested DP before/after. Every entry/exit of the ±0.1 K blend region additionally records integral and accepted DP immediately before/after the transition. All 32 Stage A runs passed the explicit integral-update/back-calculation equality and zero instantaneous output-jump checks. The effective Ki stayed between each candidate's registered hot and cold gains. The selected warm run crossed into the blend and then cold region with one continuous integral; its cold run remained in the cold region. It had one complete HOT↔COLD traversal across both cases in the final 60 s. The maximum for any Stage A run was one, below the preregistered chatter-fail threshold of more than six. No Stage A run failed the blend/oscillation audit.

## 5. Fine-mesh finalists and selected candidate

The top five feasible Stage A candidates were retested at physics dt = 0.1 and 0.05 s. Each passed warm and cold on all three meshes, the adjacent-settling tolerance, and the existing continuous-metric convergence tolerances. The following entries give warm/cold settling times in seconds:

| Finalist | 0.2 s | 0.1 s | 0.05 s | Convergence |
|---|---:|---:|---:|---|
| R5-KP4500-H110-C130 | 109.0 / 127.2 | 109.0 / 126.8 | 109.0 / 126.6 | PASS |
| R5-KP4500-H112-C130 | 108.8 / 127.2 | 108.8 / 126.8 | 108.8 / 126.6 | PASS |
| R5-KP4500-H114-C130 | 108.6 / 127.2 | 108.6 / 126.8 | 108.4 / 126.6 | PASS |
| R5-KP4500-H116-C130 | 108.4 / 127.2 | 108.2 / 126.8 | 108.2 / 126.6 | PASS |
| R5-KP4500-H110-C128 | 109.0 / 131.8 | 109.0 / 131.2 | 109.0 / 131.0 | PASS |

The preregistered ranking and 0.1-to-0.05 numerical-uncertainty veto selected **R5-KP4500-H110-C130**. Its canonical warm/cold settling times were 109.0/127.2 s, worst side 127.2 s, imbalance 18.2 s, total IAE 268.767668 K·s, total control TV 1.134067, and pump energy 3434.304165 J. The pairwise uncertainty evidence is in the JSON; among near-equal C130 candidates, earlier ranking metrics were numerically indistinguishable and later registered criteria decided the order. A [candidate baseline](phase5_r5_directional_pi_candidate_baseline.json) was created for user review, **not** as a frozen final feedback baseline.

The [R5 tuning figure](docs/results/phase5_r5_directional_pi_tuning.png) shows the feasibility map, finalist temperature traces, ±0.5 K target band, ±0.1 K blend region, selected candidate Ki_eff/integral history, pump command/actual/measured histories, and Safety timeline. It is explicitly labeled tuning evidence, not independent validation or OEM/NVIDIA/GB300 validation.

## 6. Safety, ownership, information isolation, and conservation

All 16 cold Stage A cases reproduced the same candidate-independent startup `DEGRADED / ACTUATOR_TRACKING_PENDING` event for about 0.4 s. It was recorded separately from thermal tuning, and no new restrictive Safety behavior appeared. This remains `STARTUP_SAFETY_BLOCKER_PENDING`; R5 is **not** a full feedback qualification pass. Safety thresholds/state machine were not changed.

Directional gain selection used only the released measured maximum-device-temperature error. The new outer class has no scenario input and emits a feedback DP intent; Supervisor/Safety/PLC/Actuator ownership remained unchanged. The ownership audit and every run's PLC command lineage passed. All 32 Stage A and 20 finalist runs passed mass and energy conservation; maximum mass residual was 2.7755575615628914e-17 kg/s and maximum absolute step energy residual was 6.90672408154569e-10 J.

## 7. Repeatability, limitations, and gate

For the selected candidate, ten WARM_CAPTURE and ten COLD_CAPTURE repeats at dt = 0.2 s completed without exception. Each scenario produced one identical result hash across its ten runs, and retained-memory span remained below the registered limit (224 bytes observed in each sequence).

Warm and cold cases are **training** cases, not independent validation. The result is from a generic numerical fixture, not hardware or OEM/NVIDIA/GB300 qualification. No historical HOLDOUT-01 or future Phase 6 case was used for selection. No target, plant, inner, actuator, Safety, Kp, blend width, anti-windup behavior, or controller ownership change was made beyond the registered directional Ki law. A later, separately authorized phase must use unseen preregistered validation cases and resolve/review the startup Safety blocker before any final feedback baseline is frozen.

**PHASE5_R5_GATE_STATUS: `DIRECTIONAL_PI_CANDIDATE_FOUND_WITH_STARTUP_SAFETY_BLOCKER`.**

Full machine-readable evidence: [phase5_r5_directional_pi_evidence.json](phase5_r5_directional_pi_evidence.json).

## 8. Regression verification

R5-specific tests passed (7/7). The complete V0.2 control, plant, and thermal suites passed (98 + 49 + 100 = 247 tests), covering historical Phase 5/R4.2 and Phase 3/4 regressions. The V0.1 suite passed (72 tests). Ruff and `git diff --check` passed. Historical source hashes and blocked gate outcomes remain unchanged.
