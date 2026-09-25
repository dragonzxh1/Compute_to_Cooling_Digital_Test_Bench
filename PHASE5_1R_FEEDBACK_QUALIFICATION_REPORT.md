# C2C-DTB V0.2 — Phase 5.1R frozen R1 feedback qualification

Date: 2026-09-21  
**PHASE5_1R_GATE_STATUS = BLOCKED — A_NO_FEASIBLE_REGULATION_REGION**

## 1. Purpose

This restart asks whether the frozen Phase 5R1 controller can be qualified in a pre-registered,
plant-bracketed, non-capacity-limited generic operating region. It does not retune the controller,
modify the plant, change the 305 K target, or start Phase 6.

## 2. R1 baseline integrity and no-retune confirmation

| Item | SHA-256 | Result |
|---|---|---|
| `phase5_r1_feedback_baseline.json` | `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d` | PASS |
| Frozen R1 control core | `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579` | PASS |
| R1 revision registration | `9ef5cd97c2d4bf3f2540739a58d676bf2c64c4e6be0421fe8a21a4482cb36066` | PASS |
| R1 selection evidence | `fe9f5e78cbf27197ffbe61ea68f7b5ab76264ae6f864fa0494b6fdc6d5c1c6d5` | PASS |

`phase5_1r_qualification_registration.json` was frozen before this scan. It fixes the original
inner/outer gains, target, actuator bounds/dynamics, sensor and nonphysics clocks. No frozen R1 file
or control/plant implementation was modified.

## 3. Plant-only feasibility policy

Seven equally spaced loads include both existing fixture endpoints, 120 and 240 W/device. For each
candidate the frozen plant runs open-loop for 180 s at speed 0.3 and 0.9. The mean maximum device
temperature over the fixed final 30 s is used. Outer PI, PLC feedback and closed-loop performance
metrics do not participate in selection.

A candidate must satisfy both `T_low > 305.5 K` and `T_max < 304.5 K`. The deterministic selection
would choose the highest bracketed load.

## 4. Complete candidate table and bracketing result

| Candidate | IT Load W/device | Low-cooling T K | Max-cooling T K | Target bracketed | Selected |
|---|---:|---:|---:|---|---|
| LOAD-120 | 120 | 314.724326 | 312.697126 | No | No |
| LOAD-140 | 140 | 317.347474 | 315.094718 | No | No |
| LOAD-160 | 160 | 319.970623 | 317.492311 | No | No |
| LOAD-180 | 180 | 322.593772 | 319.889903 | No | No |
| LOAD-200 | 200 | 325.216920 | 322.287495 | No | No |
| LOAD-220 | 220 | 327.840069 | 324.685087 | No | No |
| LOAD-240 | 240 | 330.463218 | 327.082679 | No | No |

The low-cooling inequality passes for every candidate, but the maximum-cooling inequality fails for
every candidate. At the easiest 120 W/device point, maximum qualified cooling is still
`312.697126 K`, exceeding the required `304.5 K` endpoint by `8.197126 K`. Higher-load endpoint
temperatures increase monotonically.

## 5. Nominal selection and closed-loop disposition

No candidate is plant-bracketed, so `NOMINAL-FEASIBLE-01` does not exist and
`nominal_fixture_sha256` is null. In accordance with the frozen registration, the nominal
closed-loop transaction was not started. The null settling, saturation, DP and energy metrics in
`phase5_1r_nominal_result.json` mean **not executed after a failed prerequisite**, not measured zero.

No nominal plot was generated and the capacity-limited stress plot was not relabeled as nominal.
Changing the target, load range, pump maximum, plant parameters or controller would be a new phase,
not qualification.

## 6. Conservation during the feasibility scan

All fourteen plant-only endpoint runs retained zero reported maximum mass residual and a maximum
absolute step energy residual below `6.0e-10 J`, comfortably inside the registered `1e-8 kg/s` and
`0.001 J` numerical gates. This validates scan execution but cannot create a missing control bracket.

## 7. Ownership, provenance and historical stress

The frozen Phase 5R1 ownership audit remains the authoritative PASS evidence: Safety owns envelopes,
PLC owns final commands, and actuator provenance is complete. Since no nominal run was authorized by
the feasibility gate, there are no new nominal commands whose lineage could be scored.

`HOLDOUT-01-combined` remains the **CAPACITY-LIMITED HISTORICAL STRESS REGRESSION** with its frozen R1
evidence intact. It was not used for candidate selection, not presented as nominal settling, and not
rerun after the hard feasibility blocker. The existing anti-windup and stress regression evidence
remain unchanged rather than being repurposed to pass this gate.

## 8. Downstream qualification items not executed

Closed-loop settling, final-window temperature, saturation, three-mesh nominal convergence,
nominal ownership/provenance, ten-run nominal stability and the nominal six-panel figure are
`NOT_EVALUABLE` because their registered prerequisite—one bracketed plant candidate—failed. Running
them anyway would violate the selection protocol.

## 9. Regression and documentation

Phase 5.1R tests cover baseline hashes, no-retune fields, deterministic grid, plant-only isolation,
bracketing, blocked selection, scan conservation and absence of a false nominal figure. The complete
Phase 5.1R subset passed 8 tests; the complete V0.2 suite passed 186 tests, the V0.1 suite passed
72 tests, and Ruff passed with cache disabled. README and result documentation retain the historical
defect, R1 correction, blocked restart and strict V0.1/V0.2 feedforward split. Local Markdown links
and the explicit absence of a false nominal figure are validated at final handoff.

## 10. Gate

**PHASE5_1R_GATE_STATUS = BLOCKED. Classification:
A_NO_FEASIBLE_REGULATION_REGION. Blocking issue: the frozen 305 K target is below the maximum-cooling
endpoint for every pre-registered load, including the original 120 W/device initial load. STOP. Do
not retune, modify the plant, generate nominal claims, or enter Phase 6.**
