Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 09 — Thermal-Matched Benchmark B

## Inputs / Outputs

Input: PERFORMANCE ExperimentSpec, registered safety/hardware/source/noise profile, RequiredHeadroom_i, per-device thermal_limit_i, shared constraints, candidate registry and training/holdout split.
Output: per-mode feasibility, chosen candidate and all attempted candidates, Pump Electrical Energy, average electrical W, control effort, flow/ΔP/supply T, match validity and qualified conclusion.

## Frozen execution policy

RequiredHeadroom is configurable; Generic numerical benchmark default5 K (ENGINEERING_ASSUMPTION), not an NVIDIA limit. Absolute thermal_limit_i must be supplied with provenance; no GB300 default fabricated. Objective min_i,t(limit_i−T_i)>=RequiredHeadroom_i; all flow, pressure, CDU capacity, actuator and model-validity constraints also hold. No tolerance that permits a violation is implicit. Roundoff comparison tolerance1e-9K only.

Default matching whitelist has exactly one outer-loop parameter: base_dp_fraction b∈{0,0.05,...,1} (21 candidates), translating to dp_min+b×(dp_max−dp_min) in Pa. dp_min/max are fixed complete profile parameters; they do NOT vary between strategies. Supply-temperature policy, PLC gains, FF/FB gains, bounds and ramp remain fixed. This contract defines a finite search, not a claim of global optimum. Alternative whitelist/search requires a new registration version before outcomes, never a post-hoc extra knob.

Both strategies evaluate same21 candidates on same training traces and seeds. No adaptive extra budget; failed candidates counted. Choose feasible candidate with lowest mean pump energy across training cases, then lower control total variation, then smallest b. Feasibility requires all registered training cases, not only average. If none -> INFEASIBLE; no relaxed headroom. Freeze selected candidate per mode before holdout; no retune on holdout, no more than one evaluation per selected candidate per holdout/seed.
On holdout, both must still meet all constraints. Otherwise B result INFEASIBLE, raw thermal/energy reported, no matched-efficiency claim.

For paired stochastic evaluation default seeds [7,17,27,37,47], fixed before runs; same seed per pair, sensor-index noise keyed per06. Training/holdout workload IDs must be disjoint and fully specified before execution; missing dataset profile is CONFIG_INVALID, not auto-generated after looking at results.

## KPI and meaningful benefit

Pump energy from05 over common window; total variation Σ|Δu| on fixed command event sequence, no numerical-step-dependent vibration proxy. Thermal targets for IAE/ISE shared, T_target_i=thermal_limit_i−RequiredHeadroom_i. Flow kg/s, ΔP Pa, supply K, electrical J/W explicit.
Frozen practical energy threshold=max(1J,1%×baseline mean electrical energy). Claim FF reduces pump energy only if matched feasibility holds and paired reduction exceeds threshold; publish all seed differences, mean/min/max and numerical sensitivity. With random seeds additionally require lower bound of two-sided95% Student-t paired-mean interval > threshold (df=n−1, n>=5). This is limited evidence, not population universality or guaranteed GB300 benefit. If deterministic/noise-free, report deterministic scope, no invented statistical interval.
Cooling energy claim limited to pump electricity unless full facility input boundary supplied.

Numerical uncertainty veto: an improvement must also exceed the sum of each mode's absolute 0.1→0.05s change in that KPI from contract11. Passing a1% convergence tolerance alone does not establish a1% energy benefit. If this veto fails, refine the integrator under the same registration or report No meaningful benefit; do not relax the benefit threshold.

## Failure / acceptance specifications

TM-01: same headroom5K, identical hardware/inner-loop/sensors, search21 each.
TM-02: lower peak temperature with more energy is not automatically an efficiency win.
TM-03: unknown limit/missing constraint blocks RUN; no feasible candidate returns INFEASIBLE.
TM-04: holdout retune or unlisted parameter change -> FAIR_COMPARISON FAIL.
TM-05: report all candidates and failed points, not selected points only.
