# C2C-DTB V0.2 — Phase 5R2.1 outer-selection robustness report

Date: 2026-09-22  
**PHASE5_R2_1_GATE_STATUS = STOP FOR USER REVIEW — FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS**

## 1. Purpose

Phase 5R2.1 tests whether the original `outer_a`, `outer_b`, `outer_c` selection ordering remains
reliable at physics meshes 0.2, 0.1 and 0.05 s. It freezes the Phase 5R2 target and `inner_b`, runs
all four training scenarios for every candidate and mesh, applies a pre-registered numerical
uncertainty veto, and freezes a final R2 baseline only if the resulting candidate remains `outer_b`.

No target, plant, actuator, Safety threshold, controller candidate, event, scenario, nonphysics
clock, or selection criterion was changed.

## 2. R2 target and baseline integrity

| Item | Verified SHA-256 | Result |
|---|---|---|
| R1 baseline | `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d` | PASS |
| R2 target registration | `8b2bda84c6591e678d0fde972562e1f0dc7a10d0b22c82b76a10f34372c860a2` | PASS |
| R2 initial selection evidence | `94bd66cf9c66602ca37fd16d65f92b93536d7ff36974a8d10153723897c93e37` | PASS |
| R2 candidate baseline | `2f97cc36ff10d81be7a3a74a9c8d94cd2099222e5cd5c22ba09fad8f458f9a0a` | PASS |
| R1 control core | `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579` | PASS |
| Frozen plant source | `d240051ccdc8681ba44d3fc8c30597ce920a761b834dabbdd5d5d93d9d016254` | PASS |

The target remained exactly `313.71072595542387 K`. It was not recalculated.

## 3. Robustness registration

`phase5_r2_1_selection_robustness_registration.json` was created before the 36 runs. SHA-256:
`4942860bf06d991942b4ae5fbe1d8bfd9a28ded3263e77c716bfabaa5481f735`.

It freezes three candidates, three meshes, four training scenarios, sum aggregation, feasibility
first, and the registered order thermal IAE → control TV → pump energy → candidate ID. For a pair,
thermal IAE is numerically indistinguishable when the fine-mesh candidate difference is no larger
than the sum of both candidates' 0.1→0.05 s IAE sensitivities.

## 4. Complete 36-run matrix

All `3 candidates × 3 meshes × 4 training scenarios = 36` runs completed. All 36 were finite and
passed Safety, mass, energy, headroom, solver and ownership-lineage feasibility gates. No holdout was
used in any matrix cell or score.

| Candidate | dt (s) | Thermal IAE | Control TV | Pump energy (J) | Feasible |
|---|---:|---:|---:|---:|---|
| `outer_a` | 0.20 | 11.853641284061 | 0.473762525966 | 1583.539774358149 | Yes |
| `outer_a` | 0.10 | 12.072246233524 | 0.474982762298 | 1584.417719662229 | Yes |
| `outer_a` | 0.05 | 12.182465538164 | 0.475594613638 | 1584.854523128419 | Yes |
| `outer_b` | 0.20 | 11.842375553973 | 1.250887505457 | 1594.898888716630 | Yes |
| `outer_b` | 0.10 | 12.060783439414 | 1.253292618356 | 1596.485941667763 | Yes |
| `outer_b` | 0.05 | 12.170932018418 | 1.254498435746 | 1597.277650747673 | Yes |
| `outer_c` | 0.20 | 11.938551443014 | 2.567286858884 | 978.873041892508 | Yes |
| `outer_c` | 0.10 | 12.157960013617 | 2.570037538650 | 979.655456702743 | Yes |
| `outer_c` | 0.05 | 12.267978363281 | 2.571417447734 | 980.059214447628 | Yes |

The raw strict-floating-point IAE winner is `outer_b` at all three meshes.

## 5. Candidate IAE and numerical sensitivity

| Candidate | IAE 0.2 | IAE 0.1 | IAE 0.05 | 0.2→0.1 sensitivity | 0.1→0.05 sensitivity |
|---|---:|---:|---:|---:|---:|
| `outer_a` | 11.853641284061 | 12.072246233524 | 12.182465538164 | 0.218604949463 | 0.110219304640 |
| `outer_b` | 11.842375553973 | 12.060783439414 | 12.170932018418 | 0.218407885441 | 0.110148579004 |
| `outer_c` | 11.938551443014 | 12.157960013617 | 12.267978363281 | 0.219408570603 | 0.110018349664 |

For every candidate, the fine-pair sensitivity is smaller than the coarse-pair sensitivity, so the
registered candidate convergence behavior is acceptable.

## 6. Pairwise distinguishability

Signed differences are left candidate minus right candidate.

| Pair | Δ at 0.2 | Δ at 0.1 | Δ at 0.05 | Numerical uncertainty bound | Distinguishable |
|---|---:|---:|---:|---:|---|
| `outer_a - outer_b` | 0.011265730088 | 0.011462794110 | 0.011533519746 | 0.220367883644 | No |
| `outer_a - outer_c` | -0.084910158953 | -0.085713780094 | -0.085512825117 | 0.220237654304 | No |
| `outer_b - outer_c` | -0.096175889041 | -0.097176574203 | -0.097046344863 | 0.220166928668 | No |

The `outer_a` versus `outer_b` fine-mesh difference is only about 5.2% of its registered uncertainty
bound. Therefore the raw IAE difference cannot be used to claim that `outer_b` is physically or
performance superior. All three candidates form the thermal-equivalent set under the frozen rule.

## 7. Final selection decision

| Criterion | outer_a | outer_b | outer_c |
|---|---:|---:|---:|
| Feasible | Yes | Yes | Yes |
| Fine-mesh thermal IAE | 12.182465538164 | **12.170932018418** | 12.267978363281 |
| IAE distinguishable? | No | No | No |
| Fine-mesh control TV | **0.475594613638** | 1.254498435746 | 2.571417447734 |
| Fine-mesh pump energy (J) | 1584.854523128419 | 1597.277650747673 | **980.059214447628** |
| Final selection | **Yes** | No | No |

Because thermal IAE is numerically indistinguishable, the next registered criterion applies.
`outer_a` has the lowest fine-mesh control TV, so pump energy and candidate ID are not reached.
The final policy result is `outer_a`, which differs from the coarse Phase 5R2 result `outer_b`.

## 8. Ownership and numerical closure

The static and runtime Phase 5R1 ownership audits remain PASS, and all matrix actuator commands retain
PLC ownership and lineage. Across all 36 runs:

- maximum mass residual: `5.55111512312578e-17 kg/s`
- maximum absolute step energy residual: `6.60193677504139e-10 J`
- maximum saturation duration: `0 s`
- maximum Safety fault events per run: `0`

Existing no-TRUE/no-raw-ACTUAL/no-future-access regression tests remain passing.

## 9. Withheld downstream work

The registered rule requires an immediate stop when the final winner changes away from `outer_b`.
Consequently:

- `HOLDOUT-01-combined` historical stress characterization: **NOT EXECUTED**
- selected-baseline 0.2/0.1/0.05 convergence: **NOT EXECUTED**
- selected-baseline ten-run deterministic stability: **NOT EXECUTED**

These are withheld prerequisites, not failures and not zero-valued results. The holdout was not used
for tuning or selection.

## 10. Full regression

- Phase 5R2.1 focused tests: 7 passed.
- Complete V0.2 suite, including Phase 5R2, Phase 5R1, original Phase 5, Phase 4.1, Phase 4 and
  Phase 3: 200 passed.
- V0.1 suite: 72 passed.
- Ruff: all checks passed with cache disabled.

## 11. Final R2 baseline artifact

`phase5_r2_feedback_baseline.json` was **not created**. The existing
`phase5_r2_candidate_baseline.json` remains coarse-grid historical candidate evidence and is not
promoted to a final frozen baseline. The robustness evidence SHA-256 is
`dafa0034206912172901de8655c147886cfb7296a3c24601dcc64e3696fa2052`.

## 12. Gate

**PHASE5_R2_1_GATE_STATUS = STOP FOR USER REVIEW —
FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS. Blocking issue: the pre-registered numerical
uncertainty veto makes the three outer candidates thermally indistinguishable, after which the next
registered criterion selects `outer_a`, not `outer_b`. No final R2 baseline is frozen. STOP; do not
run Phase 5.1R2, Phase 6, or feedforward implementation.**
