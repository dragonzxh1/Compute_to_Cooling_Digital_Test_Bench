# C2C-DTB V0.2 Phase 5R4.1 Local Bidirectional PI Refinement

## 1. Why this local refinement was needed

Phase 5R4 found no bidirectionally feasible controller in its coarser grid. Increasing outer integral gain helped the cold start but began to drive the warm start below the permitted temperature band. R4.1 therefore tested only the preregistered local interval Kp = 2500–5000 and Ki = 100–120, without changing the controller architecture or the plant.

## 2. Frozen experiment and preregistration

Only outer PI gains changed. The target remained 313.71072595542387 K; inner controller `inner_b` remained Kp = 1.5e-5, Ki = 4e-6, Kd = 0. The 120 W/device workload, physical warm/cold preparation states, 180 s duration, ±0.5 K band, 15 s dwell, final 30 s window, numerical conservation limits, plant, timing, sensors, pump/actuator constraints, PLC ownership, and Safety policy remained frozen. The warm and cold preparation state hashes exactly matched Phase 5.1R2. No controller prehistory or integrator warm-start was used.

The [registration](phase5_r4_1_local_pi_refinement_registration.json) was written before the first local-gain evaluation; its SHA-256 is `87ee1de2312de45fe598712f951c3e08621a06f68dbf5f64bceb98c46cdf8925`. Source R2 baseline SHA-256: `891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1`. Source R4 evidence SHA-256: `ad32d1f8a54dd1f2d586ea6bee3d2d229781e831983e2e4aaddee3c6d09a44cd`. Historical source artifacts were not edited.

## 3. Local grid and Stage A

The exact Cartesian grid contained six Kp values (2500, 3000, 3500, 4000, 4500, 5000) and five Ki values (100, 105, 110, 115, 120), with Kd = 0 for all 30 candidates. All 60 registered warm/cold runs completed at physics dt = 0.2 s; **60 were valid and zero passed both directions**. One earlier execution experienced a transient error in a single run, so the entire registered matrix was rerun; only the complete 60/60-valid run is used below. No candidate was added or removed after the outcome was seen.

The table uses `—` for no valid settling time through the end of the frozen 180 s run. No worst-side settling time exists unless both sides settle.

| Candidate | Warm settle (s) | Cold settle (s) | Warm final mean (K) | Cold final mean (K) | Worst settle (s) | Thermal result |
|---|---:|---:|---:|---:|---:|---|
| R41-KP2500-KI100 | 110.6 | — | 313.410 | 313.170 | — | WARM_ONLY |
| R41-KP2500-KI105 | — | — | 313.392 | 313.185 | — | NEITHER |
| R41-KP2500-KI110 | — | — | 313.374 | 313.201 | — | NEITHER |
| R41-KP2500-KI115 | — | 139.4 | 313.357 | 313.216 | — | COLD_ONLY |
| R41-KP2500-KI120 | — | 125.4 | 313.340 | 313.232 | — | COLD_ONLY |
| R41-KP3000-KI100 | 110.4 | — | 313.418 | 313.163 | — | WARM_ONLY |
| R41-KP3000-KI105 | 109.8 | — | 313.400 | 313.178 | — | WARM_ONLY |
| R41-KP3000-KI110 | — | — | 313.383 | 313.193 | — | NEITHER |
| R41-KP3000-KI115 | — | — | 313.365 | 313.208 | — | NEITHER |
| R41-KP3000-KI120 | — | 131.4 | 313.348 | 313.224 | — | COLD_ONLY |
| R41-KP3500-KI100 | 110.4 | — | 313.427 | 313.156 | — | WARM_ONLY |
| R41-KP3500-KI105 | 109.8 | — | 313.409 | 313.171 | — | WARM_ONLY |
| R41-KP3500-KI110 | 109.2 | — | 313.391 | 313.186 | — | WARM_ONLY |
| R41-KP3500-KI115 | — | — | 313.374 | 313.201 | — | NEITHER |
| R41-KP3500-KI120 | — | 141.2 | 313.357 | 313.216 | — | COLD_ONLY |
| R41-KP4000-KI100 | 110.4 | — | 313.436 | 313.149 | — | WARM_ONLY |
| R41-KP4000-KI105 | 109.8 | — | 313.418 | 313.164 | — | WARM_ONLY |
| R41-KP4000-KI110 | 109.2 | — | 313.400 | 313.178 | — | WARM_ONLY |
| R41-KP4000-KI115 | — | — | 313.383 | 313.193 | — | NEITHER |
| R41-KP4000-KI120 | — | — | 313.366 | 313.208 | — | NEITHER |
| R41-KP4500-KI100 | 110.4 | — | 313.444 | 313.142 | — | WARM_ONLY |
| R41-KP4500-KI105 | 109.8 | — | 313.427 | 313.157 | — | WARM_ONLY |
| R41-KP4500-KI110 | 109.0 | — | 313.409 | 313.171 | — | WARM_ONLY |
| R41-KP4500-KI115 | 108.4 | — | 313.392 | 313.186 | — | WARM_ONLY |
| R41-KP4500-KI120 | — | — | 313.375 | 313.201 | — | NEITHER |
| R41-KP5000-KI100 | 110.4 | — | 313.453 | 313.136 | — | WARM_ONLY |
| R41-KP5000-KI105 | 109.6 | — | 313.435 | 313.150 | — | WARM_ONLY |
| R41-KP5000-KI110 | 109.0 | — | 313.418 | 313.164 | — | WARM_ONLY |
| R41-KP5000-KI115 | 108.4 | — | 313.400 | 313.179 | — | WARM_ONLY |
| R41-KP5000-KI120 | 107.8 | — | 313.383 | 313.193 | — | WARM_ONLY |

## 4. Two-dimensional feasibility map

| Kp \ Ki | 100 | 105 | 110 | 115 | 120 |
|---:|---|---|---|---|---|
| 2500 | WARM_ONLY | NEITHER | NEITHER | COLD_ONLY | COLD_ONLY |
| 3000 | WARM_ONLY | WARM_ONLY | NEITHER | NEITHER | COLD_ONLY |
| 3500 | WARM_ONLY | WARM_ONLY | WARM_ONLY | NEITHER | COLD_ONLY |
| 4000 | WARM_ONLY | WARM_ONLY | WARM_ONLY | NEITHER | NEITHER |
| 4500 | WARM_ONLY | WARM_ONLY | WARM_ONLY | WARM_ONLY | NEITHER |
| 5000 | WARM_ONLY | WARM_ONLY | WARM_ONLY | WARM_ONLY | WARM_ONLY |

The map contains 18 warm-only, 4 cold-only, 8 neither, and **0 BOTH_PASS** cells. Lower integral gains tend to preserve warm regulation but leave the cold side below the lower band. Higher integral gains can recover the cold side at lower Kp, but then the warm side exits the band. The gap is visible in the fixed registered grid; it does not prove that no controller outside that grid can work.

## 5. Oscillation, finalists, and numerical robustness

The newly preregistered oscillation checks explicitly reject a temperature exit after the first 15 s in-band dwell, growing alternating extrema, repeated final-window crossings of both band edges, and pump-limit cycling. Twelve warm runs showed an in-band dwell followed by exit; the report does not call slow monotonic approaches oscillatory. The original through-end settling rule also failed those runs. No run was rescued by disregarding the oscillation check.

Because no Stage A candidate passed both sides, the stop rule prevented finalists, Stage B dt = 0.1/0.05 s, fine-mesh convergence checks, numerical-uncertainty comparisons, and selected-candidate repeatability. No final candidate or `phase5_r4_1_candidate_baseline.json` was created. The conditional finalist/heatmap PNG was not generated because its trigger requires at least one feasible candidate; the map above and in the evidence JSON is the required zero-overlap visual record.

## 6. Safety, ownership, and conservation

All 30 cold runs reproduced the same candidate-independent startup `DEGRADED / ACTUATOR_TRACKING_PENDING` event, lasting 0.4 s before recovery. It remains a separate blocker for full feedback qualification; it was not counted as a thermal-tuning failure and Safety was not altered.

PLC ownership and command provenance passed, and every ranked run passed mass and energy conservation. The maximum mass residual was 2.7755575615628914e-17 kg/s; maximum absolute step energy residual was 6.746674330315727e-10 J. Controller input stayed on the released measured-data path; no truth, future disturbance, or historical HOLDOUT-01 was used for selection.

## 7. Limitations and gate

WARM_CAPTURE and COLD_CAPTURE are tuning cases, **not independent validation**. These results are from a generic numerical fixture and do not validate OEM/NVIDIA/GB300 hardware. The Safety startup issue also remains unresolved. The local grid was not widened; no derivative action, asymmetric gains, anti-windup revision, target change, final feedback baseline, or Phase 6 feedforward work was attempted.

**PHASE5_R4_1_GATE_STATUS: `NO_LOCAL_PI_OVERLAP_REGION_FOUND`.**

Full machine-readable evidence: [phase5_r4_1_local_pi_refinement_evidence.json](phase5_r4_1_local_pi_refinement_evidence.json).

## 8. Regression verification

R4.1-specific tests passed (7/7). The complete V0.2 control, plant, and thermal suites passed (84 + 49 + 100 = 233 tests), covering the historical Phase 5/R4 and Phase 3/4 regressions. The V0.1 suite passed (72 tests). Ruff and `git diff --check` passed. Historical gate outcomes remain unchanged.
