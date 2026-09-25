# C2C-DTB V0.2 — Phase 5 Revision 2 control-target feasibility report

Date: 2026-09-22  
**PHASE5_R2_GATE_STATUS = STOP FOR USER REVIEW — OUTER_SELECTION_CHANGED_DUE_TO_TARGET_REVISION**

## 1. Reason for Revision 2 and Phase 5.1R blocker

Phase 5.1R proved that the frozen `305 K` research target is outside the frozen generic plant's
cooling authority at every registered load. Phase 5R2 therefore revises only the generic numerical
control target using a rule frozen before execution. It does not change plant, actuator, sensor,
Safety thresholds, candidate gains, control-core code, or implement feedforward.

## 2. R1 baseline integrity

| Artifact | SHA-256 | Result |
|---|---|---|
| R1 baseline | `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d` | PASS |
| R1 control core | `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579` | PASS |
| R1 revision registration | `9ef5cd97c2d4bf3f2540739a58d676bf2c64c4e6be0421fe8a21a4482cb36066` | PASS |
| R1 selection evidence | `fe9f5e78cbf27197ffbe61ea68f7b5ab76264ae6f864fa0494b6fdc6d5c1c6d5` | PASS |
| Frozen plant source | `d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254` | PASS |

The historical authority endpoints were reproduced exactly within the registered `0.01 K`
tolerance. All prior Phase 5, Phase 5.1, Phase 5R1 and Phase 5.1R evidence remains present.

## 3. Target derivation registration and authority reproduction

`phase5_r2_target_registration.json` was frozen before the target-selection run. Its SHA-256 is
`8b2bda84c6591e678d0fde972562e1f0dc7a10d0b22c82b76a10f34372c860a2`.

| Quantity | Value |
|---|---:|
| Target derivation load | 120 W/device |
| Low authority speed | 0.3 |
| T_low | 314.7243256180813 K |
| High authority speed | 0.9 |
| T_high | 312.69712629276637 K |
| Derived target | 313.71072595542387 K |
| Upper margin | 1.013599662657441 K |
| Lower margin | 1.013599662657498 K |
| Registered minimum margin | 0.75 K |
| Hard-stop minimum margin | 0.5 K |
| Authority rule | exact binary64 midpoint |

The target is a **GENERIC NUMERICAL CONTROL TARGET / ENGINEERING_ASSUMPTION / UNVALIDATED**. It is
not a GB300 target, NVIDIA limit, OEM setpoint, or hardware safety threshold. The target remains
strictly below the unchanged `335 K` derate and `345 K` hard thresholds.

## 4. Inner reselection

The original Stage A scenarios, candidates and ordering were reused. `false` means no physical or
Safety feasibility failure.

| Candidate | Feasibility failed | DP metric (Pa·s) | TV | Pump energy (J) | Selected |
|---|---|---:|---:|---:|---|
| `inner_a` | false | 194682.144476 | 0.304312 | 1547.855633 | No |
| `inner_b` | false | 130574.341029 | 0.473763 | 1583.539774 | **Yes** |

The selected inner candidate remains `inner_b`, as required.

## 5. Outer reselection and mandatory stop

The exact original outer grid was re-evaluated on the four registered training scenarios with the
new target. The combined historical holdout did not participate.

| Candidate | Feasibility failed | Thermal IAE aggregate (K·s) | TV | Pump energy (J) | Selected |
|---|---|---:|---:|---:|---|
| `outer_a` | false | 11.853641 | 0.473763 | 1583.539774 | No |
| `outer_b` | false | **11.842376** | 1.250888 | 1594.898889 | **Yes** |
| `outer_c` | false | 11.938551 | 2.567287 | 978.873042 | No |

The frozen priority compares feasibility and then thermal IAE before TV and pump energy. Therefore
`outer_b` replaces R1's `outer_c`. This is not an automatic failure, but it triggers the registered
mandatory classification `OUTER_SELECTION_CHANGED_DUE_TO_TARGET_REVISION` and stops the phase for
user review.

## 6. Training, ownership and numerical evidence

The R1 ownership audit remains PASS: Safety owns constraints, the PLC remains the sole final-command
producer, and lineage remains complete. Across all R2 training runs, maximum mass residual was
`5.55111512312578e-17 kg/s` and maximum absolute step energy residual was
`6.13241013525112e-10 J`, within the registered numerical gates. No truth/raw ACTUAL/future access,
warm start, initial-integrator adjustment, or future-trace tuning was added.

## 7. Stress characterization, convergence and repeated stability

`HOLDOUT-01-combined` remains registered solely as historical stress characterization and was not
used for target derivation or candidate selection. Because the outer selection changed, the
registered stop occurred before the selected R2 controller could run the historical stress,
0.2/0.1/0.05 s convergence, or ten-run stability protocols. These items are **NOT EXECUTED**, not
failed and not zero. No nominal-regulation or settling claim is made.

## 8. Candidate baseline and artifact linkage

Only `phase5_r2_candidate_baseline.json` was created. It records the full-precision target,
`inner_b + outer_b`, unchanged clocks/actuator/sensor/Safety physical fields, R1 control-core hash,
R2 registration hash and selection-evidence hash. Its SHA-256 is
`2f97cc36ff10d81be7a3a74a9c8d94cd2099222e5cd5c22ba09fad8f458f9a0a`.

`phase5_r2_feedback_baseline.json` is deliberately absent. No final baseline was frozen and the R1
baseline is not claimed as unchanged after the target revision.

## 9. Regression and GitHub documentation

- Phase 5R2 focused gate: 7 passed.
- Complete V0.2 suite, including Phase 5R1, Phase 5, Phase 4.1, Phase 4 and Phase 3: 193 passed.
- V0.1 suite: 72 passed.
- Ruff: all checks passed with cache disabled.
- The authority figure is generated from the R2 selection JSON and explicitly labels the generic,
  non-OEM meaning. No nominal Phase 5.1 figure was created or promoted.

## 10. Limitations and gate

The midpoint establishes two-sided frozen-plant authority only at the registered 120 W/device
fixture and endpoint definition. It does not prove closed-loop settling, broad-load feasibility,
hardware safety, production control quality, GB300 calibration, or OEM validity.

**PHASE5_R2_GATE_STATUS = STOP FOR USER REVIEW —
OUTER_SELECTION_CHANGED_DUE_TO_TARGET_REVISION. Blocking issue: the registered reselection changed
the outer candidate from `outer_c` to `outer_b`. The final R2 baseline, historical stress run,
convergence and repeated-stability evidence are withheld pending explicit user acceptance. STOP. Do
not enter Phase 5.1R2, Phase 6, or feedforward implementation.**
