# C2C-DTB V0.2 — Phase 5R2.2 final baseline report

Date: 2026-09-22  
**PHASE5_R2_2_GATE_STATUS = PASS — FINAL BASELINE FROZEN / awaiting user review**

## 1. User-authorized final selection

The user accepted the pre-registered Phase 5R2.1 result and authorized the final generic feedback
configuration:

| Item | Frozen value |
|---|---:|
| Research target | 313.71072595542387 K |
| Inner candidate | `inner_b` (`Kp=1.5e-5`, `Ki=4e-6`, `Kd=0`) |
| Outer candidate | `outer_a` (`Kp=1000`, `Ki=20`, `Kd=0`) |

No selection was rerun and no target, grid, priority, plant, actuator, sensor, Safety policy,
controller equation, clock, scenario, ownership rule or historical R2/R2.1 artifact was changed.

## 2. Integrity checks

| Item | SHA-256 | Result |
|---|---|---|
| Phase 5R1 baseline | `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d` | PASS |
| R2 target registration | `8b2bda84c6591e678d0fde972562e1f0dc7a10d0b22c82b76a10f34372c860a2` | PASS |
| R2 initial selection evidence | `94bd66cf9c66602ca37fd16d65f92b93536d7ff36974a8d10153723897c93e37` | PASS |
| R2.1 robustness registration | `4942860bf06d991942b4ae5fbe1d8bfd9a28ded3263e77c716bfabaa5481f735` | PASS |
| R2.1 robustness evidence | `dafa0034206912172901de8655c147886cfb7296a3c24601dcc64e3696fa2052` | PASS |
| R1 control core | `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579` | PASS |
| Frozen plant source | `d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254` | PASS |

## 3. Historical stress characterization

`HOLDOUT-01-combined` ran only after the final candidate was authorized. It remains historical
stress characterization, not a selection input, blind holdout, or nominal-regulation result.

| Metric | Result |
|---|---:|
| Peak device temperature | 319.478060879153 K |
| Temperature IAE | 94.992767598477 K·s |
| Temperature ISE | 383.770522703955 K²·s |
| DP tracking IAE | 123967.970906399 Pa·s |
| Pump electrical energy | 720.236719694839 J |
| Control total variation | 0.421311348826 |
| Actuator tracking IAE | 0.190096004112 fraction·s |
| Saturation duration | 0 s |
| Safety events / faults | 1 / 0 |
| Safety state duration | FF_DISABLED 2.0 s; NORMAL 58.0 s |
| Maximum mass residual | 4.16333634234434e-17 kg/s |
| Maximum energy residual | 4.24378754360077e-10 J |

The null settling value remains a stress-case observation; it is not a Phase 5.1R2 qualification
failure or pass because nominal qualification has not started.

## 4. Selected-baseline numerical convergence

All nonphysics clocks and event timestamps remained fixed while only physics dt changed.

| dt (s) | Peak T (K) | Temperature IAE | DP IAE | Pump energy (J) | TV | Saturation (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.20 | 316.070318489469 | 11.853641284061 | 78528.221659336 | 433.025787468385 | 0.298559791518 | 0 |
| 0.10 | 316.079409218397 | 12.072246233524 | 78679.837464124 | 433.450756834770 | 0.299011088278 | 0 |
| 0.05 | 316.083954831200 | 12.182465538164 | 78755.862968548 | 433.661375397310 | 0.299237173258 | 0 |

Fine-pair differences were `0.004545613 K` peak temperature, `0.110219305 K·s` temperature IAE,
`76.025504 Pa·s` DP IAE, `0.04857%` pump energy, `0.000226085` TV, zero saturation difference and
`0.000112457 fraction·s` actuator tracking IAE. Every value is inside the existing registered
convergence tolerance. Status: PASS.

## 5. Ownership, conservation and stability

The Phase 5R1 static/runtime ownership audit remains PASS. Safety produces restrictive envelopes,
the PLC is the sole `ActuatorCommand` producer, the actuator accepts PLC commands only, and the
validated stress/convergence command lineage is complete.

Across stress, convergence and repeated runs, maximum mass residual was
`4.16333634234434e-17 kg/s` and maximum absolute step energy residual was
`6.60193677504140e-10 J`. Both pass.

Ten consecutive identical-profile executions completed without exception and produced the same
result hash `dfca4f532c6425c6cb89c00dfb3ff7d826a5f0b1e79c05210e7c86a15d416701`.
Retained-memory span was `10646 bytes`, inside the bounded-memory gate. Status: PASS.

## 6. Full regression

- Phase 5R2.2 focused tests: 7 passed.
- Combined R2/R2.1/R2.2 focused tests: 21 passed.
- Complete V0.2 suite, including R1, original Phase 5, Phase 4.1, Phase 4 and Phase 3: 207 passed.
- V0.1 isolated rerun: 72 passed. An earlier combined-shell attempt encountered one transient
  Windows native access violation; the clean isolated rerun passed without source changes.
- Ruff: all checks passed with cache disabled.

## 7. Final baseline artifact

`phase5_r2_feedback_baseline.json` is frozen with status
`FROZEN_GENERIC_TEST_BASELINE_REVISION_2_NOT_OEM`.

- complete file SHA-256: `891aba6f348e14a0d36c350ac407004635da780f07e4d29a92b526b558aca8d1`
- canonical noncircular payload SHA-256 stored inside the artifact:
  `a68733669ca07cfad6d591c2288d3f279727ba40e66a5d9b01386d2dc21439b3`
- finalization evidence SHA-256:
  `f33eb500ee224fbbd4a80b88affcaa77902ea08c33714c10ae4493c76d576208`
- superseded R1 baseline SHA-256:
  `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d`

The in-file hash explicitly covers canonical JSON before the hash and scope fields are added; the
complete serialized file hash is recorded in the finalization evidence and this report, avoiding an
impossible self-referential hash.

## 8. Limitations

This baseline is a generic numerical research fixture with unvalidated hardware parameters. It does
not prove nominal settling, GB300/OEM validity, hardware safety, production-PLC readiness,
feedforward performance, or Phase 6 readiness. Phase 5.1R2 has not started.

## 9. Gate

**PHASE5_R2_2_GATE_STATUS = PASS. Blocking issues: none within Phase 5R2.2 scope. The revised generic
Phase 5 feedback baseline is frozen with a plant-feasible research target and the user-authorized,
mesh-robust selection `inner_b + outer_a`. STOP; await user review. Do not enter Phase 5.1R2,
Phase 6, or feedforward implementation.**
