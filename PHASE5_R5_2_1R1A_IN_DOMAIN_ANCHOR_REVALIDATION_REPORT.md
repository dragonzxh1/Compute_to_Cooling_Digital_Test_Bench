# Phase 5R5.2.1R1a — In-domain anchor-advancement revalidation

Gate: `CUMULATIVE_COMMAND_DEMAND_SEMANTICS_VALIDATED_IN_PROFILE_DOMAIN`. This is a **test-fixture replacement**, not a change to tracking semantics or production Safety. Evidence applies to the generic numerical fixture only; it is not OEM, NVIDIA GB300 or real-hardware validation.

## Why a separate R1a was needed

R1 stopped at `CUMULATIVE_COMMAND_DEMAND_VALIDATION_FIXTURE_OUT_OF_PROFILE_DOMAIN`: its original C9 commanded 1.0 while the frozen tracking profile permits only `[0.3, 0.9]`. That original C9 remains **INVALID** in the untouched R1 registration, trace, evidence and gate. It has not been relabeled PASS or deleted. R1's other C cases, S1–S16, invariants 1–12 and prefix causality had passed. R1a repairs only C9's validation input and uses the exact unchanged R1 offline semantic engine.

Before the replacement was run, [R1a registration](phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json) froze the source hashes, profile SHA-256 `9064b95358fb1166b0c3a2e6653e81497f56bec92fdafca5d925eabe895eb9d8`, profile speed bounds read from `ActuatorTrackingProfile`, and the exact normal-actuator schedule below. Registration SHA-256 is recorded in the [evidence](phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json). The sequence was selected because each individual update is below the frozen 0.15 material threshold, but each stage's signed net demand is 0.16, above it; all commands are strictly inside the frozen speed range. No command was clamped.

| Time (s) | PLC command | Purpose |
| ---: | ---: | --- |
| 0.0 | 0.35 | Directly observed qualified anchor A |
| 0.2 | 0.40 | Stage 1 small step |
| 0.4 | 0.45 | Stage 1 small step |
| 0.6 | 0.51 | First net-observable demand relative to A |
| 3.0 | 0.56 | Stage 2 small step after B is established |
| 3.2 | 0.61 | Stage 2 small step |
| 3.4 | 0.67 | Second net-observable demand relative to B |

The frozen normal actuator and released sensor produced qualified progress. Epoch 1 began at 0.6 s, then resolved; **A=0.35 → B=0.51 at 1.2 s**, with no earlier anchor advance. Stage 2 used B: at 3.4 s, net demand was `0.67−0.51=0.16`, not `0.67−0.35` and not the last individual command step. Epoch 2 began at 3.4 s, progressed and resolved; **B=0.51 → C=0.67 at 4.0 s**. Each anchor event records previous/new anchor, timestamp, reason and source tracking epoch. The entire two-stage audit table—including time, command, anchor, net demand, class, epoch/watch IDs, released speed, state and anchor update—is in the evidence JSON.

## Regression and invariants

New `C9R_IN_DOMAIN_ANCHOR_ADVANCEMENT`: PASS, including every registered domain, trigger, resolution and A→B→C criterion. Valid historical C1–C8 and C10–C12: all PASS. **Original C9: INVALID historical evidence, not rerun as a passing case.** Unchanged S1–S16 and S16 variant: all PASS. Original invariants 1–12: all PASS. New invariant 13 (every semantic-evidence command in frozen profile domain) and 14 (post-advancement net demand uses newest anchor): PASS. Prefix causality on every valid C/S case and C9R: PASS.

The frozen R1 semantic engine SHA-256 remained `e9bb0de5c15c10a9ccbdbe899c3fd1cb1f5e05145af79c2e142b9990cd7020ef`. Profile, thresholds, response window, confirmation rule, sensor behavior and all production Safety/controller/actuator/sensor/plant hashes remained unchanged. No recalibration or new numeric tracking parameter was used. The [eight-panel figure](docs/results/phase5_r5_2_1r1a_in_domain_anchor_revalidation.png) visualizes bounds, command, anchor, net demand, epoch/watch, measured speed, anchor lifecycle, historical distinction and regression.

This closes **only** the R1 validation-fixture blocker. Hardware-specific speed bounds, sensor resolution/noise, timestamp behavior, actuator response and tracking tolerances still require calibration. R5 directional PI remains a candidate. Do not modify production Safety, start R5.3R or Phase 6, or freeze the final feedback baseline without a separate user-reviewed task.
