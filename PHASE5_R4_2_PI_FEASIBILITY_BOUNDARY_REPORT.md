# C2C-DTB V0.2 Phase 5R4.2 PI Feasibility Boundary Report

## 1. Why a boundary search was needed

The R4.1 grid had warm-only points at lower Ki, cold-only points at higher Ki, and no both-pass point. A discrete grid cannot show how wide the gap between pass regions is, or whether a narrow overlap lies between two sampled Ki values. R4.2 therefore located the warm-pass and cold-pass transitions for six fixed Kp values using preregistered deterministic bisection, not a new uniform grid or an optimizer.

## 2. Frozen scope and registration

The target remained 313.71072595542387 K, inner controller `inner_b` remained Kp = 1.5e-5, Ki = 4e-6, Kd = 0, and all plant, workload, FWS/CDU, hydraulic, pump/actuator, sensor, PLC, Safety, preparation, 180 s exam, ±0.5 K band, 15 s dwell, final 30 s window, and conservation requirements remained unchanged. Only outer Ki was varied for fixed Kp in {2500, 3000, 3500, 4000, 4500, 5000}; Kd stayed zero.

The [R4.2 registration](phase5_r4_2_pi_boundary_search_registration.json) was written before any new boundary gain was executed. SHA-256: `6c24855e76b4967c9fa3327a57dfcf796a54e58447208c233dff0b07820b1070`. Frozen source R4.1 registration SHA-256: `87ee1de2312de45fe598712f951c3e08621a06f68dbf5f64bceb98c46cdf8925`; source R4.1 evidence SHA-256: `f7282097e7ca1d961148b34b465f8998ea88dadc69ba08abca5462b400dce976`. Both historical artifacts remained unchanged.

## 3. Method, pass rule, and uncertainty

Ki was restricted to [95, 125]. Each Kp was first checked at Ki = 95, 100, 105, 110, 115, 120, 125 at physics dt = 0.2 s. The 100–120 records at that mesh were reused from the frozen 60/60-valid R4.1 evidence; 95 and 125 were newly executed. Each side's ordered pass/fail series was checked for the expected local monotonic ordering before and after every bisection point. Bisection ran only on a valid pass/fail bracket until its Ki width was at most 0.10.

A side passed only with the frozen through-end temperature, final-window, pump-interior, direction, oscillation, finite-state, ownership, mass/energy, and forbidden-Safety-state gates. The common cold-start `DEGRADED / ACTUATOR_TRACKING_PENDING` was recorded separately, not counted as thermal failure. All runs used the released measured-data path, not true state or future disturbances. No historical HOLDOUT-01 was used for selection.

The numbers below are **bounds**, not exact mathematical transition points. Warm PASS-side lower bound minus cold PASS-side upper bound would establish a conservative overlap. Cold FAIL-side lower bound minus warm FAIL-side upper bound establishes a conservative gap. Midpoints are estimates only and were not used alone to declare overlap or gap.

## 4. Monotonicity verification

All six Kp values passed the ordered initial-probe check and every added bisection-point check on both warm and cold sides. No higher-Ki warm-pass restoration after a confirmed warm fail, and no higher-Ki cold-pass loss after a confirmed cold pass, was observed at the executed points. This is local evidence within the sampled domain; it is not a global mathematical monotonicity proof.

## 5. Canonical 0.2 s boundaries and overlap/gap

| Kp | Warm PASS through Ki | Warm FAIL from Ki | Cold FAIL through Ki | Cold PASS from Ki | Conservative gap (Ki) | Classification |
|---:|---:|---:|---:|---:|---:|---|
| 2500 | 103.984375 | 104.062500 | 113.515625 | 113.593750 | 9.453125 | CONFIRMED_GAP |
| 3000 | 107.109375 | 107.187500 | 116.171875 | 116.250000 | 8.984375 | CONFIRMED_GAP |
| 3500 | 110.234375 | 110.312500 | 118.750000 | 118.828125 | 8.437500 | CONFIRMED_GAP |
| 4000 | 113.437500 | 113.515625 | 121.406250 | 121.484375 | 7.890625 | CONFIRMED_GAP |
| 4500 | 116.718750 | 116.796875 | 124.062500 | 124.140625 | 7.265625 | CONFIRMED_GAP |
| 5000 | 120.078125 | 120.156250 | 125.000000 | >125 / unbracketed | n/a | DOMAIN_NO_OVERLAP |

Each actual bracket has width 0.078125 Ki, below the preregistered 0.10 tolerance. The estimated warm/cold midpoint pairs are, respectively: Kp 2500 (104.023438, 113.554688), 3000 (107.148438, 116.210938), 3500 (110.273438, 118.789062), 4000 (113.476562, 121.445312), 4500 (116.757812, 124.101562). At Kp 5000, cold failed at every initial probe through Ki = 125, so no cold PASS boundary was extrapolated outside the domain.

In plain language, increasing Ki far enough to make the cold case pass occurs **after** Ki has already become too high for the warm case at every bracketed Kp. The smallest certified canonical gap was 7.265625 Ki at Kp 4500—not a boundary-touching ambiguity.

## 6. Fine-mesh near-gap confirmation

The two smallest certified canonical gaps were Kp 4500 and 4000. For these two Kp values only, the entire initial-probe and boundary-bisection procedure was repeated at 0.1 s and 0.05 s, with the same Ki domain, 0.10 tolerance, and pass rule. No historical metric was reused at either fine mesh.

| Kp | Physics dt (s) | Warm PASS | Warm FAIL | Cold FAIL | Cold PASS | Conservative gap (Ki) | Result |
|---:|---:|---:|---:|---:|---:|---:|---|
| 4500 | 0.1 | 116.562500 | 116.640625 | 123.906250 | 123.984375 | 7.265625 | CONFIRMED_GAP |
| 4500 | 0.05 | 116.484375 | 116.562500 | 123.906250 | 123.984375 | 7.343750 | CONFIRMED_GAP |
| 4000 | 0.1 | 113.281250 | 113.359375 | 121.328125 | 121.406250 | 7.968750 | CONFIRMED_GAP |
| 4000 | 0.05 | 113.203125 | 113.281250 | 121.250000 | 121.328125 | 7.968750 | CONFIRMED_GAP |

All four fine-mesh searches passed local monotonicity checks and retained a positive gap much larger than the 0.10 Ki search uncertainty. The boundary plot is [phase5_r4_2_pi_feasibility_boundaries.png](docs/results/phase5_r4_2_pi_feasibility_boundaries.png); the vertical bars show the bracket uncertainty and grey segments show certified gaps.

## 7. Candidate, Safety, ownership, and conservation

No overlap candidate was found, so no all-mesh six-run candidate confirmation, 10+10 repeatability sequence, or `phase5_r4_2_candidate_baseline.json` was triggered. The common cold-start Safety event remains `STARTUP_SAFETY_BLOCKER_PENDING`, with approximately 0.4 s in `DEGRADED`; Safety policy was not modified and full feedback qualification remains blocked independently of the thermal gap.

The PLC remained the sole ActuatorCommand producer; the ownership audit and every run's command lineage passed. All 254 available point records (60 frozen R4.1 records plus 194 newly executed R4.2 records) passed mass and energy conservation. There were no invalid retained boundary runs and no out-of-domain gains.

## 8. Limitations and gate

The result is limited to the six registered Kp values, Ki in [95, 125], this frozen plant, this target, and these warm/cold **training** fixtures. It does not prove that no PI controller exists for other Kp values, other Ki ranges, or physical hardware. It is tuning/feasibility evidence, not independent hardware validation. No derivative term, asymmetric controller, gain scheduling, anti-windup revision, Feedforward, or Phase 6 work was performed.

**PHASE5_R4_2_GATE_STATUS: `NO_PI_OVERLAP_CONFIRMED_IN_R42_DOMAIN`.**

The next engineering choice, if authorized separately, would be a controller-structure revision rather than automatically continuing this PI search. Full machine-readable evidence: [phase5_r4_2_pi_boundary_search_evidence.json](phase5_r4_2_pi_boundary_search_evidence.json).

## 9. Regression verification

R4.2-specific tests passed (7/7). The complete V0.2 control, plant, and thermal suites passed (91 + 49 + 100 = 240 tests), including the historical Phase 5/R4.1 and Phase 3/4 regressions. The V0.1 suite passed (72 tests). Ruff and `git diff --check` passed. Historical registrations, evidence, baselines, and gate statuses were not modified.
