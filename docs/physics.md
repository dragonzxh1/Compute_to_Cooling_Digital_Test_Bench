# V0.1 mathematical model

## 1. Workload and electrical power

For `N` identical GPUs, utilization `u` is mapped to board power with an affine profile:

`P_gpu = P_idle + u (P_max - P_idle)`, bounded by the configured power limit. Total compute electrical power also includes optional CPU and other rack power.

## 2. Compute-to-heat split

`Q_liquid = alpha_gpu N P_gpu + alpha_cpu P_cpu + alpha_other P_other`

`Q_air = (1-alpha_gpu) N P_gpu + (1-alpha_cpu) P_cpu + (1-alpha_other) P_other`

The capture fractions are calibration parameters, not universal constants.

## 3. Lumped thermal dynamics

V0.1 uses four stored-energy nodes: GPU die, package, cold plate, and secondary coolant. For each node:

`C_i dT_i/dt = sum_j ((T_j - T_i) / R_ij) + Q_i`

The directed heat path is equivalent hotspot -> package -> cold plate -> coolant. All liquid heat, including CPU/other capture, is injected at the equivalent hotspot; legacy GPU-named output fields retain this aggregate meaning. Explicit Euler integration checks `dt <= 0.5 min(C_i / sum_j G_ij)`, including both neighboring conductive paths and coolant advection `m_dot*cp`. This conservative bound keeps the homogeneous update coefficients non-negative. Unsafe steps are rejected before changing state. A FIFO with linear interpolation represents fractional pipe delays without rounding positive sub-step delays to zero.

## 4. Coolant energy balance

At the rack boundary:

`Q_to_coolant = m_dot_s cp_s (T_return - T_supply)`

Water properties are constant in V0.1. PG25 is a separate configuration with constant approximate properties and must not be presented as a temperature/concentration correlation.

## 5. Hydraulic operating point

System pressure loss is `DeltaP_system = K_system q^2`. A variable-speed pump is represented by:

`DeltaP_pump(q, n) = n^2 DeltaP_shutoff_ref - K_pump q^2`

where `n` is speed fraction. Equating pump and system curves gives the operating point. Hydraulic power is `DeltaP q`; electrical power divides by configured efficiency. Negative head, flow, or power is forbidden.

## 6. CDU heat exchanger

For secondary and primary capacity rates `C_h = m_dot_s cp_s` and `C_c = m_dot_p cp_p`:

`C_min = min(C_h, C_c)`, `C_r = C_min/C_max`, `NTU = UA_effective/C_min`.

Counterflow effectiveness is:

`epsilon = (1-exp(-NTU(1-C_r))) / (1-C_r exp(-NTU(1-C_r)))`

and `epsilon = NTU/(1+NTU)` as `C_r -> 1`. `UA_effective = UA_clean * fouling_factor`. Heat rejected is bounded by `epsilon C_min (T_hot,in - T_cold,in)` and available hot-side energy.

## 7. Controls

The PLC has two positional PID loops with output clamps and conditional-integration anti-windup:

- secondary differential pressure error -> pump speed;
- secondary supply temperature error -> primary valve position.

The LCI feedforward estimate computes required flow from predicted liquid heat and an allowable secondary delta-T. In shadow mode its recommendation is logged but not applied. In the comparison case, its setpoint intent passes through PLC clamp and ramp-rate guards before affecting the plant.

The comparison case enables supervisory control only at the first workload step. Before it, both cases follow identical local feedback control. Future-dated, expired or non-finite intents fall back to local targets. A non-finite sensor holds its affected actuator and freezes that PID's state; the other loop continues, and valid measurements resume normal operation. This is a simulation fault policy, not a hardware emergency cooling design.

Temperature requests are clamped to an accepted final target, then slewed at `controls.temp_setpoint_ramp_k_s` (positive finite K/s, default 0.1). The temperature PID uses this actual ramped setpoint. The same slew applies when returning to local fallback. At zero timestep the setpoint does not move; an invalid temperature sensor freezes both its setpoint and PID. Requested, accepted and actual setpoints remain distinct telemetry fields. The 3 K reporting check evaluates actual-setpoint tracking, while `max_accepted_target_deviation_k` separately discloses error to the final target and is not part of that check. A tracking PASS does not certify immediate final-target compliance.

With the default ramp, timestep 1 / 0.5 / 0.25 / 0.125 s gives post-step tracking peaks of 1.838 / 1.848 / 1.854 / 1.857 K and hotspot peaks of 77.972 / 77.978 / 77.981 / 77.983°C. The two finest runs differ by less than 0.01 K on these metrics. This is a default-scenario refinement check, not validation over the full operating envelope. Rates 0.05, 0.1 and 0.2 K/s were compared; 0.1 is a provisional compromise between tracking error and response speed, not a calibrated optimum.

Power is held constant over each simulated interval; reported energy uses left-endpoint integration, matching that time convention. The initial rack state is steady for its assumed supply, but the CDU initial valve may cause a startup transient. Startup and post-step deviations are therefore reported separately. The current steady rack heat check does not certify transient rack-plus-pipe energy closure.

## Validation before fidelity

Every layer has an analytical or invariant test: heat split closure, RC monotonicity, coolant balance, pump affinity/positivity, exchanger temperature bounds, PID saturation, intent clamp, and PLC survival during LCI loss.
