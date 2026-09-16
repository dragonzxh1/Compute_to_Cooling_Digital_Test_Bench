# Review corrections — 2026-09-16

## Corrected behavior

- RC integration includes conductances on both sides of internal nodes and coolant advection when bounding timestep. It rejects unsafe/non-finite updates instead of accepting the counterexample that produced -9820°C.
- Both benchmark cases use identical feedback before the first load step. Feedforward is enabled at the step. The legacy controller-response metric now consistently measures valve response, while setpoint response has a separate field. A command change is not proof of completed thermal response.
- Invalid sensor measurements freeze only the affected PID and hold that actuator. Invalid, future or stale supervisory intents use local fallback. Recovery is tested.
- Configuration validation and reports share discrete reporting-window definitions. Incomplete, duplicated or non-finite time series produce INVALID instead of PASS. No percentage comparison is calculated with zero baseline energy.
- Plots use an Agg canvas, independent of desktop Tk configuration. CI installs the actual wheel into an isolated environment and executes English and Chinese reports outside the repository.
- Fractional transport delay is interpolated. Startup and post-step supply deviations are separated. Energy integration follows the engine's held-input convention.

## Historical result before setpoint slew limiting

With the original 3 K supply-deviation criterion, the controlled feedforward case reaches about 3.062 K and correctly fails that check. No threshold was relaxed to obtain a green report. Feedback passes. Equivalent-hotspot peaks remain below the assumed 90°C threshold. Valve response is approximately 104 s versus 1 s; feedforward setpoint response is 0 s. These are controller-output thresholds, not cooling-completion times or OEM performance claims.

## Remaining model boundaries

Update: temperature-setpoint slew limiting is now enabled at 0.1 K/s. The default tracking check passes, but final-target error is reported separately and remains above 3 K during transition. See [physics](physics.md#7-controls) for rate semantics, refinement results and limitations; the preceding abrupt-setpoint result is retained as historical context.

The four-node network treats CPU/other liquid heat as part of the equivalent hotspot. Labels now disclose that meaning while CSV keys stay compatible. Separate CPU/GPU thermal paths need parameterization and calibration before changing that physics.

The initial rack state is not a solved joint plant equilibrium. The reported startup transient is intentional and separately identified. Fractional FIFO transport does not establish a fixed pipe inventory or full transient energy conservation at varying flow. A rack-node conservation test and a steady heat-balance check are provided; full pipe storage validation remains open.

The scenario provenance record retains sources and dates, but calibration evidence (operating envelope, residuals and parameter version) still requires manual review. No new calibration or hardware validation is claimed by this correction.
