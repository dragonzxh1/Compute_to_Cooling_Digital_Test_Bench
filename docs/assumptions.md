# V0.1 assumptions and parameter provenance

All initial numeric values are planning assumptions for a **Generic GB300-Class Compute Profile** and a **Generic 1 MW-Class CDU**. They are not NVIDIA or OEM specifications.

| Parameter | Symbol | Unit | V0.1 source type | Needed for | Replacement path |
|---|---|---:|---|---|---|
| GPU count | `N_gpu` | 1 | ASSUMED | rack power | inventory/DCGM |
| GPU idle/max power | `P_idle`, `P_max` | W/GPU | ASSUMED | power curve | NVIDIA/OEM or measured DCGM |
| Power limit | `P_limit` | W/GPU | ASSUMED | clamp | DCGM/NVIDIA |
| CPU/other rack power | `P_cpu`, `P_other` | W | ASSUMED | heat split | measured PDU |
| Liquid capture fractions | `alpha_*` | 1 | ASSUMED | liquid/air split | calorimetry/calibration |
| Die/package/cold-plate/coolant capacitance | `C_*` | J/K | ASSUMED | transient response | OEM/FAT/calibration |
| Die-package/package-plate/plate-coolant resistance | `R_*` | K/W | ASSUMED | temperature rise | OEM/literature/calibration |
| Transport delay | `tau_transport` | s | ASSUMED | CDU return delay | pipe volume/flow or step test |
| Coolant density and heat capacity | `rho`, `cp` | kg/m3, J/kg/K | LITERATURE approximation | energy balance | validated property library |
| System resistance coefficient | `K_system` | Pa/(m3/s)^2 | ASSUMED | flow/DP | FAT pump-loop curve |
| Pump shutoff DP/reference flow/efficiency | pump curve | Pa, m3/s, 1 | ASSUMED | operating point/energy | OEM/FAT |
| Clean heat-exchanger conductance | `UA_clean` | W/K | ASSUMED | heat rejection | OEM/FAT calibration |
| Fouling factor | `f_UA` | 1 | ASSUMED | degradation | calibrated trend |
| Primary inlet temperature/flow | `T_p,in`, `q_p` | degC, m3/s | ASSUMED | heat rejection | BMS/OEM |
| PID gains, deadbands, ramps, limits | control config | mixed | ASSUMED | PLC behavior | OEM PLC/FAT |
| LCI target delta-T and margin | LCI config | K | ASSUMED | recommendation | commissioning optimization |
| Throttle temperature | `T_throttle` | degC | ASSUMED | benchmark metric | NVIDIA-supported telemetry/spec |

Each YAML parameter record contains `value`, `unit`, `source_type`, `source`, `date`, `confidence`, and `notes`. Runtime loaders consume `value`; reports preserve the full provenance record.

Known V0.1 omissions: spatial hot spots, two-phase flow, temperature-dependent properties, manifold imbalance, compressibility, detailed valve curves, pump inertia, facility plant dynamics, and real PLC scan semantics.
