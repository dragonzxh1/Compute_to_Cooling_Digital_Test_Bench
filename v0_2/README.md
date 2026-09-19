# V0.2 Phase 3 — isolated thermal core

Generic numerical fixtures only; no calibrated GB300 model. Apache-2.0, as in the repository license.
No imports from or changes to the V0.1 `src/c2c` package are required.

## Run from the repository root

```powershell
.venv/Scripts/python.exe -m pytest -c v0_2/pyproject.toml v0_2/tests -W error
.venv/Scripts/python.exe -m v0_2.examples.phase3_single_device
.venv/Scripts/python.exe -m v0_2.examples.phase3_gpu_coldplate_step
.venv/Scripts/python.exe -m v0_2.examples.phase3_validation
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

```powershell
.venv/Scripts/python.exe -m pytest -c v0_2/pyproject.toml v0_2/tests/plant -W error
.venv/Scripts/python.exe -m v0_2.examples.phase4_validation
```
