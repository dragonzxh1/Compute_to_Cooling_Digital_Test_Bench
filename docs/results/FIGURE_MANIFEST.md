# Figure manifest

All captions inherit: **Generic numerical fixture / unvalidated hardware parameters.** Code version is the checked-out repository state; `phase5_feedback_baseline.json` records the frozen code digest after qualification.

| Figure ID / file | Source command | Data / scenario | Meaning | Limitation |
|---|---|---|---|---|
| F1 `system_architecture.svg` | `python -m v0_2.tools.generate_docs_figures` | Architecture and Phase 5 module boundaries | Feedback-only measured-state control path around the physical plant | Diagram, not performance data; Phase 6 FF is not implemented |
| F2 `coldplate_rth_flow.png` | same | Phase 3 `GenericColdplate`, `phase4_1_figure_source.json` policy | Runtime Rth decreases with local hydraulic flow | Generic constitutive curve, not an OEM coldplate map |
| F3 `hydraulic_operating_point.png` | same | Phase 4 fixture pump/system coefficients | Pump curves intersect the solved system curve at two speeds | Single-pump quadratic generic network |
| F4 `phase4_1_control_authority.png` | `python -m v0_2.examples.phase4_1_validation` then figure command | `phase4_1_figure_source.json`, speed sweep | Speed → flow → Rth → heat transfer → device temperature | Prescribed speed in Phase 4.1; actuator dynamics begin in Phase 5 |
| F5 `branch_restriction.png` | same | baseline versus branch-0 K×1.5 | Flow redistribution and thermal consequence | Generic two-branch fixture |
| F6 `phase5_closed_loop_holdout.png` | `python -m v0_2.examples.phase5_evidence` then figure command | `phase5_evidence.json`, `HOLDOUT-01-combined` | Released measured temperature drives outer DP target, PLC, commanded/actual/measured pump and flow | Capacity-limited combined stress holdout; not nominal-settling or Phase 5.1 qualification evidence |
| F7 `safety_state_timeline.png` | same | Phase 5 holdout state records | Executed safety-state history | Normal holdout is not a hardware trip qualification |
| F8 `phase5_r2_target_authority.png` | `python -m v0_2.examples.phase5_r2_figures` | `phase5_r2_selection_evidence.json`; R2 registration `8b2bda84...60a2`; R1 baseline `24a0198d...920d`; control core `b79eaf9c...2579` | Frozen 120 W/device speed endpoints and exact midpoint target | Generic target-feasibility fixture only; not OEM/NVIDIA/GB300, not closed-loop qualification |

The renderer writes figures directly from validation data. No spreadsheet, manually transcribed table, image editing or y-axis truncation is used.

Phase 5.1R registered `phase5_nominal_regulation_r1.png` as a PASS-only deliverable, but did not
generate it because `phase5_1r_feasibility_scan.json` found no plant-bracketed candidate. The frozen
R1 baseline SHA is `24a0198d...920d`, the Phase 5.1R registration SHA is
`1f7dd7f...43e7`, and the control-core SHA is `b79eaf9c...2579`. There is no nominal fixture hash;
the scenario was never selected. F6 remains the capacity-limited stress figure and is not a
substitute for nominal evidence.

F8 SHA-256 is `112ca7c6d3da5649accd371bcae56bd79b5e48d8edcef046d7806a120f16048c`.
Its source selection evidence SHA-256 is
`94bd66cf9c66602ca37fd16d65f92b93536d7ff36974a8d10153723897c93e37`. The displayed ±0.5 K
band is the future qualification band, not a demonstrated regulation result.

Phase 5R2.1 produced no new figure. Its 36-run mesh-robustness evidence found the outer candidates
numerically indistinguishable under the pre-registered rule and selected `outer_a` by control TV,
which differs from the coarse R2 candidate. Therefore F8 remains authority/target-feasibility
evidence only and no final-baseline, stress, convergence, stability or nominal-regulation graphic is
available.

Phase 5R2.2 subsequently froze the user-authorized `inner_b + outer_a` baseline after stress,
convergence, ownership and stability checks passed. No new nominal-regulation figure was generated:
Phase 5.1R2 remains not started, so F8 continues to show authority derivation rather than settling
performance.
