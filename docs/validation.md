# Validation plan

## Release claims

V0.1 may claim deterministic execution, SI-unit consistency, equation/invariant coverage, and traceable assumptions. It may not claim GB300 prediction accuracy, OEM CDU performance, FAT equivalence, or production control readiness.

## Required checks

1. **Analytical:** compute heat split closes; zero heat yields no forced temperature rise; epsilon-NTU stays in `[0,1]` and respects inlet bounds.
2. **Conservation:** integrated liquid heat, stored thermal energy, and CDU rejection close within a documented numerical tolerance after transport storage is included.
3. **Monotonicity:** more heat at fixed flow cannot reduce delta-T; more flow at fixed heat reduces steady delta-T; degraded UA cannot improve heat rejection.
4. **Controls:** PID clamps, anti-windup, ramp limits, communication timeout, local fallback, and LCI-loss independence.
5. **Acceptance thresholds:** generated summaries record actual value, comparator, configured limit, unit, and pass/fail status. Process deviation from a setpoint is reported separately from an accepted setpoint crossing a PLC guardrail.
6. **Regression:** seeded 30%->95% workload step writes six required artifacts, including the plot. Tests require truthful threshold results, including the default controlled-feedforward supply-deviation failure.

## Automated coverage and remaining work

Automated regressions cover RC node energy balance, the previously unstable two-sided-conduction counterexample, coolant-advection timestep limits, fractional delays, identical pre-step control trajectories, separate setpoint/valve response, invalid/missing samples, one-sample windows, zero-energy comparisons, invalid intents and sensor recovery. Report generation uses a noninteractive Agg canvas. CI installs the built wheel in a fresh virtual environment and runs both locales outside the checkout.

Full transient plant conservation (item 2) including a physically defined pipe inventory remains a validation target, not a passed check. Fixed-temperature FIFO delay at changing flow does not yet model a fixed pipe mass. Operating-envelope, residual and parameter-version evidence must still be reviewed before accepting calibrated data; the current provenance schema alone does not enforce that ladder.

## Calibration ladder

The model advances from ASSUMED to LITERATURE/OEM/MEASURED/CALIBRATED only when the source, date, operating envelope, residual metric, and parameter version are recorded. FAT calibration targets flow versus pump speed, DP versus flow, pump power, heat-exchanger performance, coolant volume, and transient time constants.
