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

The directed heat path is die -> package -> cold plate -> coolant. Explicit Euler integration is used with a timestep checked against the smallest configured `R*C` time constant. A FIFO delay line represents pipe transport from rack outlet to CDU return.

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

The PLC has two positional PID loops with output clamps and back-calculation anti-windup:

- secondary differential pressure error -> pump speed;
- secondary supply temperature error -> primary valve position.

The LCI feedforward estimate computes required flow from predicted liquid heat and an allowable secondary delta-T. In shadow mode its recommendation is logged but not applied. In the comparison case, its setpoint intent passes through PLC clamp and ramp-rate guards before affecting the plant.

## Validation before fidelity

Every layer has an analytical or invariant test: heat split closure, RC monotonicity, coolant balance, pump affinity/positivity, exchanger temperature bounds, PID saturation, intent clamp, and PLC survival during LCI loss.
