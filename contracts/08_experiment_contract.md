Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 08 — Experiment Contract

## Inputs / Outputs

ExperimentSpec: id, experiment_type (PERFORMANCE / SAFETY_PROTECTION), benchmark_class (A/B/C for PERFORMANCE; PROTECTION for safety), registered profile/version/hashes, source trace, t0/t1, initial state, seed set, evaluation windows, controller modes, validation status.
Output: per-mode trace, events, offered/delivered/curtailed energy, FAIR_COMPARISON, match status and physical validity. Result paths and manifests separate by experiment_type, never merge a protection run into performance rank.

## PERFORMANCE

True per-leaf electrical trace and allocation immutable and shared; controllers, PLC, supervisor, thermal throttling model and protection cannot modify it. This is an OFFLINE experiment rule, not a recommendation to disable real hardware protections.
Thermal violation/capacity shortage logs THERMAL_LIMIT_EVENT / DERATE_REQUESTED / COOLING_CAPACITY_INSUFFICIENT; request actuation is suppressed with experiment-mode reason. Thermal KPI retains violations, no temperature/power clipping.
Input mutation -> FAIR_COMPARISON=FAIL and INVALID COMPARISON. Compare offered to applied trace per leaf AND mode to mode; equal curtailed traces on both sides still fail.
If valid model cannot represent unsafe region, stop physical scoring as INVALID; do not pretend unchanged trace was simulated to completion.

## SAFETY_PROTECTION

Same offered trace/hardware/protection thresholds, state machine and response latency in both modes. Shared protection logic may trigger at different measured times; delivered traces may therefore differ.
Only synthetic load gate may apply requested limit; recorded real power is immutable evidence (cannot counterfactually edit recorded data and call it measured). A measured hardware throttle belongs to recorded source behavior, not controller-authorized write.
delivered=min(offered,accepted cap), nonnegative, per leaf; limits/latency/recovery ramp preregistered, same modes. Request/ack independent; without ack state cannot claim successful protection.
curtailed=max(offered−delivered,0), energy_not_served=integral curtailed W dt (J, NOT tasks or computational work).
Log request_time, activation_time, activation_latency, derate_duration (union active intervals), recovery_time (first sustained safe window), requested/delivered cap, missing-ack/fault reasons.
No activation/recovery in window -> null + censored flag, not zero. Actual derating and thermal recovery are distinct events.

## Common timing / scoring

Window [t0,t1), all modes same warm-up length and exact initial states; source held right-continuously. KPI integrates interval quantities, event duration measured in seconds not count×nominal dt. Report warm-up separately; safety/max violations over entire run cannot be hidden by warm-up exclusion. Energy-matched scoring uses the declared same window and boundary.
Protection results report delivered energy and thermal safety, never claim pump saving from reduced work as performance efficiency. Feedback-only and FF+FB primary comparisons; FF-only diagnostic retains PLC and protection.

## Acceptance specifications

EXP-01: attempt to edit any applied PERFORMANCE leaf power (even equal-total redistribution) fails.
EXP-02: same derate request is log-only in PERFORMANCE and actual after configured latency in SAFETY_PROTECTION.
EXP-03: identical protection logic hash across modes, differing activation times allowed.
EXP-04: energy_not_served integrates exact capped intervals, censored recovery is not0.

