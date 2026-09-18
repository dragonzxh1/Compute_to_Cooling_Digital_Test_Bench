Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 10 — Energy-Matched Benchmark C

## Inputs / Outputs

Input: same PERFORMANCE profile and shared hardware as09; predeclared electrical energy target E_reference_j>0, abs_match_tol_j=1J, rel_match_tol=0.01 (Generic design policies).
Output: MATCHED / MATCH_FAILED with actual energies and errors; only MATCHED allows matched thermal conclusions. These tolerances must be in registration before any benchmark results, cannot adapt to FF advantage.

## Matching / selection

Same21-candidate base_dp_fraction whitelist, symmetric budget/seeds and train/holdout rules as09. E_reference is an externally preregistered budget for each workload/window; its source may be separate pilot data but cannot be fitted to reported holdout outcomes. Missing budget blocks run; do not guess an equipment energy number.
tol=max(abs_match_tol,rel_match_tol×E_reference).
Training selection per mode: minimize abs(mean_E−E_reference), then lower b; no thermal-outcome tie break/cherry-picking. Each selected mean must be within tol/2 of E_reference so pair is within tol on training. Freeze candidates before holdout.
For each holdout pair require BOTH abs(E_mode−E_reference)<=tol/2 and abs(E_FF−E_PID)<=tol; report individual-pair matching, all pairs must match for overall MATCHED. If distribution shift prevents match -> MATCH_FAILED, not tune again, rescale energy, shorten window, or adjust tolerance. Different workload budgets may be preregistered independently.

Hardware/flow/pressure/actuator/physical validity required. Temperature-limit violation does not itself invalidate C comparison if within physical model range: it is one of C's outcomes, unlike B's thermal feasibility. Both still PERFORMANCE; no derating. If limit corresponds to model invalidity, stop and no matched-performance claim.

## Thermal KPI definitions

Shared T_target_i=limit_i−RequiredHeadroom_i. Per-device IAE=integral abs(T_i−target_i)dt; ISE=integral squared error dt. Report each plus worst-device metric, not just rack average. Peak=max T_i(t); minimum headroom=min(limit_i−T_i); variance=time-weighted variance of each T trajectory. Violation duration=time union where any T_i>limit_i (and per-device duration), count boundary equality safe.
Compute from same dense/integrated output policy; do not inflate samples by dt. Numerics must pass11.
Meaningful temperature/headroom threshold0.1K; IAE/ISE/variance/duration threshold1% of baseline magnitude with absolute floors respectively0.1K·s,0.01K²·s,0.01K²,0.1s. Report zero baselines using floors, no division by zero. For random seeds use paired95% interval rule09 plus these thresholds; disclose all metrics and any worsening. No blanket victory because a single metric improves.

## Conclusions / acceptance specifications

Energy-matched thermal improvement supports “FF improves thermal response”; B governs efficiency. A reports raw trade-offs. Pareto on same search budget uses energy vs thermal-shortfall integral and minimum headroom separately; no universal scalar “FF better”. Frontier shift must exceed numerical/practical thresholds in tested candidate scope. Otherwise No meaningful benefit / Trade-off only / regression, as appropriate.
The numerical uncertainty veto in09 also applies to each claimed thermal improvement and Pareto dominance. Thermal-shortfall integral is integral max(RequiredHeadroom_i−Headroom_i,0)dt, per-device and fixed-weight rack sum (weights>=0, sum1). Candidate dominates another only if no worse in both energy and the selected risk metric and better by the applicable practical/numerical margin in at least one; min-headroom plot reverses the risk ordering explicitly.
EM-01: equal budget within limits qualifies; failure of any matching inequality returns MATCH_FAILED.
EM-02: same energy but thermal violation differs -> report difference, do not derate.
EM-03: mutated energy totals/windows/tolerances or retuned holdout invalidates comparison.
