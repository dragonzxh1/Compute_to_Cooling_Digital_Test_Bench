Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 05 — Pump Energy Contract

## Inputs / Outputs

Input: ΔP_pump (pump outlet−inlet Pa, not arbitrary rack ΔP), volumetric_flow Q (m³/s), speed, registered VFD/motor/pump map, loss fractions, hydraulic resistance ledger.
Outputs: P_electrical_w (upstream VFD input), P_hydraulic_w, eta_total, P_motor_loss, P_vfd_loss, P_internal_loss, hydraulic_dissipation_w by edge, heat_to_coolant_w by CV, heat_to_ambient_w, cumulative_pump_electrical_energy_j. Off-state standby power explicit.

```text
Electrical supply P_electrical
 -> VFD [P_vfd_loss]
 -> Motor [P_motor_loss]
 -> Pump shaft
 -> Pump [P_internal_loss]
 -> Hydraulic power ΔP_pump × Q
 -> pipe/valve/connector/coldplate resistances
 -> Hydraulic thermal dissipation
Each loss -> declared coolant/ambient receiver (not implicitly all coolant)
```

## Invariants / accounting

P_hydraulic=ΔP_pump×Q.
P_electrical=P_hydraulic+P_vfd_loss+P_motor_loss+P_internal_loss (quasi-steady drive).
eta_total=P_hydraulic/P_electrical for P_electrical>0; both zero -> N/A, standby/nonzero electrical with zero hydraulic ->0.
Motoring map only, P_electrical>=P_hydraulic>=0 and nonnegative losses. Regeneration/reverse pumping is MODEL_INVALID unless a future version adds an explicit model.

Each component k has f_k_liquid+f_k_ambient=1 within1e-12, both [0,1]. Names include motor_loss_to_liquid_fraction, motor_loss_to_ambient_fraction, vfd_loss_to_ambient_fraction; remaining VFD share enters liquid only for explicitly modeled liquid-cooled drive. Internal pump loss has own partition and receiver location. Unknown fractions are CALIBRATION_REQUIRED, not default1.

Quasi-steady closed-loop hydraulic sum dissipation=Phyd; each resistance edge D_e=ΔP_e×Q_e>=0. Heat-to-liquid=sum allocated losses to liquid + sum edge dissipation liquid fractions. Ambient receives complements. Pump provides mechanical hydraulic work, NOT a second heat source at pump equal to Phyd if resistance edges already dissipate it. Do not add Pelec as heat. Drive mechanical inertia/storage is excluded from this version's quasi-steady energy model; speed lag is kinematic, not an extra unaccounted kinetic-energy term. Future inertia requires E_mech and derivative balance revision.

Facility electricity sums electrical inputs only, never heat or hydraulic power. Pump thermal ledger is separate. Full thermal CV includes only pump losses/dissipation deposited within it (12), excluding ambient drive losses.

## Failure / fallback

Unknown map/loss destinations, eta outside[0,1], negative dissipation or balance >max(1e-6W,1e-9×Pelec) -> PUMP_ENERGY_BALANCE_FAIL; stop qualified plant. Idle branch supported explicitly; no division by zero. Physical capacity shortage is separate from arithmetic failure.

## Acceptance specifications

PE-01: electrical100W, hydraulic60W, VFD10W to ambient, motor20W half liquid, internal10W liquid and hydraulic60W liquid -> liquid80W, ambient20W, not160/180W.
PE-02: per-edge hydraulic dissipation counted once; changing CV placement changes receivers, not total.
PE-03: pump off zero flow, idle/standby and missing efficiency behave per policy.
PE-04: report all five mandated metrics independently; integrate electrical input over exact interval.

