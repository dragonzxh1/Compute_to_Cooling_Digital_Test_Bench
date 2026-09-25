# V0.2 — thermal, physical-loop and feedback-control implementation

Generic numerical fixtures only; no calibrated GB300 model. Apache-2.0, as in the repository license.
No imports from or changes to the V0.1 `src/c2c` package are required.

## Run from the repository root

```powershell
.venv/Scripts/python.exe -m pytest -c v0_2/pyproject.toml v0_2/tests -W error
.venv/Scripts/python.exe -m v0_2.examples.phase3_single_device
.venv/Scripts/python.exe -m v0_2.examples.phase3_gpu_coldplate_step
.venv/Scripts/python.exe -m v0_2.examples.phase3_validation
.venv/Scripts/python.exe -m v0_2.examples.phase4_validation
.venv/Scripts/python.exe -m v0_2.examples.phase4_1_validation
.venv/Scripts/python.exe -m v0_2.examples.phase5_validation
.venv/Scripts/python.exe -m v0_2.examples.phase5_evidence
```

The existing interpreter can run the tests without installation. For independent use, create a
separate environment and install `./v0_2`; never replace the legacy environment or its dependencies.
Runtime requires Python >=3.11 and NumPy >=1.26; tests additionally require pytest. Numerical results
in the root `PHASE3_THERMAL_REPORT.md` identify the actual environment, not a dependency lock.

## Model and ownership

Electrical leaves map once to solid nodes. Immutable node storage uses `E=C*(T-T_ref)`.
`EnthalpyLaw` defines a future variable-capacity extension; this release implements **constant C only**.
The integrator owns all temperature advancement, including local coolant storage. Each interface
creates one signed transfer, posted with equal/opposite signs to adjacent nodes. The ledger audits
nodes, declared device volumes and the thermal subsystem; it is not a rack hydraulic/full-loop model.

The generic chain is die → package → TIM resistance → coldplate solid → flow-dependent resistance
→ local coolant. The package has a parallel air path. The coolant connects to an externally prescribed
test bath through a fixed resistance: this is an imposed thermal boundary, **not** an implemented CDU,
FWS, heat exchanger or coolant advection model. Prescribed local flow only controls coldplate Rth.

Programmatic fixtures in `thermal/fixtures.py` build public model/config dataclasses. R, C and coldplate
coefficients carry `ParameterRecord` provenance; all test values remain `ENGINEERING_ASSUMPTION`,
`NUMERICAL_TEST_FIXTURE` and `UNVALIDATED`. Test-domain bounds and the 400 K numerical headroom reference
are also fixture policies, not hardware limits. Model validity means inside the declared numerical
domain; it does not mean OEM calibration. Coldplate manufacturer imports are schema validation only.

## Numerical policy

Backward Euler is the verified default for these constant-coefficient thermal fixtures. Explicit Euler
is a positivity-checked debug reference. An independent symmetric eigensystem gives exact linear RC
temperature and integrated interface energy for interval-held inputs. Events split integer-nanosecond
intervals; inputs are held between events. No control or future-workload logic is present.

Solves are direct linear solves (one solve per attempt); the frozen nonlinear iteration ceiling of 25
is reserved for a future nonlinear solver, not represented as implemented nonlinear functionality.
`StepResult.iterations` reports total linear attempts including retries. Retries halve the interval,
at most 10 levels, with a minimum 1 microsecond. A failed step returns the original state and empty
committed ledger. There is no Euler fallback, temperature clipping, fake flow or power adjustment.

Convergence requires identical models/inputs/events/duration/method and three distinct effective meshes.
Temperature trajectories use linear interpolation at the union of accepted times. Frozen peak/headroom
limits are 0.1 K. Node trajectory 0.1 K and heat-export `max(1 J, 1% of finest heat)` are additional
explicit **fixture criteria**, not amendments or misattributions to frozen Contract 11. Every run must
also satisfy all per-step and cumulative energy gates, including sum of absolute residuals.

The Phase 3 bath fixture remains independently runnable. Phase 4 adds a separate physical coolant-loop
topology in `plant/`, with finite-volume upwind transport, pressure/flow network, pump electrical and
thermal accounts, and a finite CDU reservoir coupled to an epsilon-NTU heat exchanger. The physical
topology refuses an external liquid test bath, fixed FIFO transport on the same path, or a second
posting of pump hydraulic work. Its generic fixture is uncalibrated; see the repository-root
`PHASE4_PHYSICAL_PLANT_REPORT.md` for raw evidence and OEM gaps. No controller, live adapter,
FAIR_COMPARISON, feedforward or real GB300 calibration is included.

## Phase 5 feedback-only boundary

Phase 5 wraps the frozen physical plant with a deterministic local measurement boundary, an outer
temperature PI that requests a DP target, a Safety/intent supervisor, a measured-DP local PLC and a
dynamic pump actuator. Commanded, actual and measured actuator states remain separate. Controller and
Safety inputs contain released `MEASURED` records only; no controller receives raw plant truth, raw
actuator actual state, future workload/FWS/restriction schedules or an auditor reference.

Phase 5 Revision 1 corrects the ownership defect found by the first Phase 5.1 audit. Safety now
produces a typed restrictive envelope; the PLC is the sole producer of typed final actuator commands;
the actuator rejects any non-PLC command. End-to-end IDs connect FB intent, accepted target, Safety
envelope, PLC cycle, actuator command/state and measured state. Numerical behavior, gains, periods,
thresholds and actuator dynamics are unchanged. Phase 5.1R was explicitly restarted, but its
plant-only scan found no registered load that brackets the frozen 305 K target; it stopped before
nominal closed-loop execution with `NO_FEASIBLE_REGULATION_REGION`.

Phase 5R2 pre-registered and reproduced the 120 W/device plant-only authority endpoints, then derived
the full-precision midpoint target `313.71072595542387 K`. The original candidate grid selected
`inner_b + outer_b`; because the outer candidate changed from frozen R1 `outer_c`, R2 stopped for
user review at that stage. Its candidate baseline was not a final one.

Phase 5R2.1 completed all 36 registered candidate/mesh/training runs. `outer_b` had the lowest raw
thermal IAE at every mesh, but all candidate IAE differences fell within the pre-registered combined
fine-mesh sensitivity. The next frozen priority, control total variation, selected `outer_a`.
Because this differed from the coarse R2 result, R2.1 withheld finalization under
`FINAL_SELECTION_CHANGED_AFTER_MESH_ROBUSTNESS`; later phases continued after review.

Phase 5R2.2 applies the user's explicit acceptance of `outer_a`, completes stress, numerical
convergence, ownership and ten-run stability gates, and freezes `phase5_r2_feedback_baseline.json`
as `inner_b + outer_a` at `313.71072595542387 K`. This is a historical generic R2 baseline only;
Phase 5.1R2 subsequently ran and was blocked, while Phase 6 remains not started. R5 later selected a
directional PI candidate, but R5.1/R5.2 remain diagnostic audits and do not freeze a final R5 baseline.

The registered generic baseline, holdout and figures are reproduced by:

```powershell
.venv/Scripts/python.exe -m v0_2.examples.phase5_evidence
.venv/Scripts/python.exe -m v0_2.tools.generate_docs_figures
.venv/Scripts/python.exe -m v0_2.examples.phase5_r1_ownership_audit
.venv/Scripts/python.exe -m v0_2.examples.phase5_r1_evidence
.venv/Scripts/python.exe -m v0_2.examples.phase5_r2_evidence
.venv/Scripts/python.exe -m v0_2.examples.phase5_r2_figures
.venv/Scripts/python.exe -m v0_2.examples.phase5_r2_1_robustness
.venv/Scripts/python.exe -m v0_2.examples.phase5_r2_2_finalization
.venv/Scripts/python.exe -m v0_2.examples.phase5_r3_bidirectional_selection
.venv/Scripts/python.exe -m v0_2.examples.phase5_r4_outer_tuning
.venv/Scripts/python.exe -m v0_2.examples.phase5_r4_1_local_pi_refinement
.venv/Scripts/python.exe -m v0_2.examples.phase5_r4_2_pi_boundary_search
.venv/Scripts/python.exe -m v0_2.examples.phase5_r5_directional_pi
.venv/Scripts/python.exe -m v0_2.examples.phase5_r5_1_safety_handoff_audit
.venv/Scripts/python.exe -m v0_2.examples.phase5_r5_2_silent_tracking_fault
```

The resulting gains, thresholds, delays and actuator limits are numerical test fixtures, not OEM PLC
settings or safety limits. Phase 6 feedforward is not present; `ff_component` must remain zero.

```powershell
.venv/Scripts/python.exe -m pytest -c v0_2/pyproject.toml v0_2/tests/plant -W error
.venv/Scripts/python.exe -m v0_2.examples.phase4_validation
```
