# GitHub Documentation Audit

Date: 2026-09-21  
Scope: repository landing page, V0.2 documentation, results, examples, CI, and upload hygiene.

## Inventory and assessment

| Area | Existing strengths | Outdated or missing before Phase 5 | Action |
|---|---|---|---|
| Root `README.md` | Bilingual purpose, scope disclaimer, reproducible commands, Phase 3/4 evidence, Apache-2.0 | Landing page was dominated by V0.1 and Phase 4; Phase 4.1 and feedback status were described as unpublished; no compact architecture or result gallery | Reorganized around project purpose, current phase status, architecture, quick start, validation summary, selected figures, limitations and roadmap |
| `v0_2/README.md` | Clear isolation from V0.1, thermal ownership and numerical policy | Title still said Phase 3; physical loop and Phase 5 commands/status were secondary | Updated to V0.2 through Phase 5 and added feedback-only boundary |
| Reports | Detailed Phase 2/3/4 evidence; Phase 4 figures and standalone HTML | No Phase 5 report or central results index | Added `PHASE5_FEEDBACK_CONTROL_REPORT.md` and `docs/results/README.md` |
| Figures | Phase 4 report figures were reproducible | No landing architecture, Phase 4.1 authority gallery, feedback holdout or source manifest | Added six selected landing figures plus safety timeline and source JSON |
| CI | Separate V0.1/V0.2 tests, Ruff, wheel build and Phase 4 installed-wheel reproduction | No Phase 5 validation or figure-generation smoke check | Added Python 3.11 Phase 5 evidence/figure smoke step |
| Upload hygiene | Environments, caches, temporary reports, build products, logs and result dumps already ignored | `docs/results/` needed a distinction between curated evidence and arbitrary raw dumps | Curated small JSON/PNG/SVG evidence stays tracked; `.tmp-*`, `results/`, caches and build output remain ignored |

## Content placement decisions

- The root README contains only the architecture and five primary result views. Safety state and detailed artifacts remain under `docs/results/`.
- Full contracts, hashes, raw numerical tables, test names and self-review checklists remain in technical reports rather than the landing page.
- Phase 3 `R_test_bath` is explicitly labeled as a validation-only topology. Phase 4/5 use the advective coolant loop, finite CDU/HX and FWS boundary.
- No fixed test count is placed in the README; CI and phase reports carry run-specific totals.
- Phase 6 feedforward appears only as planned work. No FF comparison, energy-saving claim or Phase 9 A/B/C benchmark was added.
- The root benchmark commands are labeled **Legacy V0.1 benchmark**. Its simplified
  feedback/feedforward comparison is not represented as V0.2 architecture or Phase 6 evidence.
- Phase 5.1 found a frozen actuation-ownership contract violation. GitHub-facing status is
  therefore Original Implementation PASS / Original Baseline Superseded, not “always correct.”
- Phase 5R1 transparently corrects the ownership path and passes its revision gate, but remains
  frozen after user approval. Phase 5.1R was explicitly restarted but the plant-only scan found no
  load that brackets the frozen 305 K target, so qualification is BLOCKED without retuning. Phase 6
  has not started.
- No `phase5_nominal_regulation_r1.png` is published: generating or substituting a nominal figure
  after the feasibility prerequisite failed would misrepresent the result. The existing Phase 5
  image remains explicitly labeled as a capacity-limited stress case.
- Phase 5R2 replaces the infeasible 305 K research target with the pre-registered 120 W/device
  frozen-authority midpoint (`313.71072595542387 K`). This is labeled a generic research setpoint,
  not a hardware limit. Because the registered outer reselection changed from `outer_c` to
  `outer_b`, only selection evidence, an authority figure and a candidate baseline are published;
  final baseline, stress/convergence/stability claims and Phase 5.1R2 remain withheld.
- Phase 5R2.1 completed the pre-registered 36-run three-mesh robustness matrix. Although `outer_b`
  remained the raw IAE winner at each mesh, all candidate differences were numerically
  indistinguishable under the frozen sensitivity bound. The next criterion selected `outer_a` on
  control TV, triggering `FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS`. No final R2 baseline or
  downstream qualification claim is published.
- Phase 5R2.2 records the user's explicit acceptance of the R2.1 `outer_a` result, completes stress,
  selected-baseline convergence, ownership and ten-run stability gates, and freezes the final
  `inner_b + outer_a` generic R2 baseline. Documentation continues to state that Phase 5.1R2 and
  Phase 6 have not started and that no nominal-settling or hardware claim follows from the freeze.

## Required disclaimer

Every new result figure is generated from repository validation outputs and marked **Generic numerical fixture / unvalidated hardware parameters**. None of the values are calibrated GB300 performance, NVIDIA limits, OEM pump/CDU maps, or hardware safety certification.
