# PHASE 3 Thermal Plant Core Report

Date: 2026-09-19 (implementation/verification started 2026-09-18)
PHASE3_GATE_STATUS = PASS

Scope: isolated constant-C generic open-loop thermal implementation only.
PASS certifies the Phase 3 numerical fixtures and software checks below, **not GB300/OEM calibration,
equipment safety, rack performance or readiness for Phase 4**. STOP for user review.

## 1. Delivery and implementation boundary

| Location under v0_2/ | Implemented responsibility |
|---|---|
| thermal/source_mapping.py | PowerLeaf, parent residual allocation, single ThermalSourceReceipt audit |
| thermal/nodes.py, state.py | Nine node types, immutable state, constant-C storage and future EnthalpyLaw interface |
| thermal/topology.py, interfaces.py | Endpoints, unique storage/interface/layer ownership, signed shared transfers |
| thermal/coldplate.py | Generic Rth(flow), endpoint/layer preflight, explicit zero-flow policy; manufacturer schema only |
| thermal/integrator.py | Explicit Euler, conservative backward Euler, exact linear RC; transactional step/retry |
| thermal/energy_ledger.py | Node/device/subsystem CV balances and signed/absolute cumulative residual gates |
| thermal/validity.py, provenance.py | Typed domain errors, provenance records and SI-unit checks |
| thermal/harness.py, fixtures.py | Prescribed-flow open-loop fixtures, held events, distinct-mesh qualification |
| tests/thermal/ | 100 passing tests including all 12 mandatory categories |
| examples/ | Single-node, GPU step and reproducible validation tables |
| pyproject.toml, README.md | Separate distribution and execution/scope instructions |

No V0.1 Python/config/test/packaging files or frozen contracts changed.
The prior PHASE 1/2 documents were committed at user request as
`020f6817dd5739024acde7f81467eb8d797e471a` before continuing.
Phase 3 code/report remain separate working-tree additions pending review; no GitHub push performed.

There is no hydraulic solver, pump operating-point solve, CDU/HX/FWS dynamics, PLC/PID/feedforward,
safety state machine, DCGM/exporter adapter, full FAIR_COMPARISON, or 72-GPU calibrated rack model.

## 2. Thermal topology and generic configuration

```text
GPU die -- R_die/package --> package -- TIM resistance --> coldplate solid
                                 |                              |
                                 R_air                          Rcp(prescribed flow)
                                 |                              |
                         fixed air boundary              local coolant storage
                                                               |
                                                        R_test_bath
                                                               |
                                                   fixed test bath boundary
```

GPU+HBM fixture adds HBM → plate and VRM/board → air. A small independent GPU+CPU topology is tested.
TIM is an interface, not a second hidden storage owner. Device CV contains die/package and optional
HBM/VRM; subsystem includes all owned solid/coolant storage. Internal transfers cancel by interface ID.

All values below are NUMERICAL_TEST_FIXTURE / ENGINEERING_ASSUMPTION / UNVALIDATED:
die/package/plate/coolant C = 200/400/800/2000 J/K; coolant mass = 0.5 kg,
cp = 4000 J/(kg K); initial/reference/boundary T = 300 K;
R_die/package = 0.05, R_TIM = 0.03, R_air = 0.8, R_test_bath = 0.02 K/W.
Coldplate h_ref = 1000 W/(m² K), m_ref = 0.1 kg/s, exponent = 0.7,
R_conduction = 0.02 K/W, area = 0.02 m²; flow domain 0.01–0.5 kg/s,
temperature domain 250–500 K, heat magnitude domain 0–10000 W.
The 400 K headroom reference is explicitly NUMERICAL_TEST_REFERENCE, **not a GB300 limit**.

The test bath is a prescribed temperature connected by a resistor, not a physical coolant
inlet/return advection model or implemented FWS/CDU. Flow affects the coldplate constitutive R only.
Plate-to-coolant internal heat and liquid boundary export are separately reported; adding both as
subsystem outputs would double count. Finite storage makes electrical input differ from liquid export.

Parameters are supplied via public dataclasses and external fixture builders, not hardcoded OEM
constants in the solver. Variable-C enthalpy is an interface extension point only; nonlinear material
integration, real manufacturer curve evaluation and hardware parameter validation are not implemented.

## 3. Numerical methods and failure policy

- EE: explicit Euler with RC positivity bound; invalid large steps use recorded bounded subdivisions.
- BE: default constant-coefficient coupled backward Euler solve. Each edge produces one interval energy
  using implicit endpoint temperatures; adjacent nodes consume the same value with opposite signs.
- EXACT: independent capacitance-weighted symmetric eigensystem; exponential solution and analytic
  integrated temperature give exact linear RC references for piecewise-held sources/boundaries/flow.

Solves are linear: one direct solve per attempt. Frozen max nonlinear iterations = 25 is retained as
policy, not a claim that a nonlinear solver exists. StepResult.iterations counts total linear attempts
including retries. Halving is limited to 10 levels and minimum dt to 1000 ns. Forced solver failure
exhausts at 11 attempted depths; first-failure recovery stays BE. Failure after one tentative accepted
half rolls back the **whole** step. No fallback to Euler, clipping, fake flow or source modification.

Frozen state residual scale is max(1e-6 J, 1e-9 × max(abs(storage change), abs(sources)+abs(fluxes))).
Each CV interval and cumulative energy tolerance is 1e-6 J + 1e-6 × S, with S the absolute external
CV exchanges plus absolute stored change. Both signed cumulative and sum(abs(interval residual))
must pass. Equivalent residual W is interval residual divided by that interval's duration.

## 4. Analytic reference results

EE/BE/EXACT below use the same declared models:
insulated C=100 J/K, P=100 W, T0=300 K, duration 10 s, exact final 310 K;
boundary RC C=100 J/K, R=0.5 K/W, T0=320 K, Tb=300 K, duration 100 s,
exact final 300+20 exp(-2) K;
two-node C1=100/C2=200 J/K, R=0.5 K/W, initial 320/290 K, duration 200 s,
equilibrium 300 K and exact final 300+20 exp(-6), 300-10 exp(-6) K.

| Fixture | Method | dt (s) | Peak T (K) | Final first-node T (K) | Signed residual (J) | Max final node error vs closed form (K) |
|---|---|---|---|---|---|---|
| insulated | EE | 0.200000000 | 310.000000000 | 310.000000000 | -5.684342e-11 | 5.684342e-13 |
| insulated | EE | 0.100000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| insulated | EE | 0.050000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| insulated | BE | 0.200000000 | 310.000000000 | 310.000000000 | -5.684342e-11 | 5.684342e-13 |
| insulated | BE | 0.100000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| insulated | BE | 0.050000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| insulated | EXACT | 0.200000000 | 310.000000000 | 310.000000000 | -5.684342e-11 | 5.684342e-13 |
| insulated | EXACT | 0.100000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| insulated | EXACT | 0.050000000 | 310.000000000 | 310.000000000 | 2.273737e-10 | 2.273737e-12 |
| boundary_rc | EE | 0.200000000 | 320.000000000 | 302.695871624 | -3.251621e-12 | 0.010834041 |
| boundary_rc | EE | 0.100000000 | 320.000000000 | 302.701290449 | -7.389667e-11 | 0.005415216 |
| boundary_rc | EE | 0.050000000 | 320.000000000 | 302.703998508 | 8.100898e-11 | 0.002707157 |
| boundary_rc | BE | 0.200000000 | 320.000000000 | 302.717525270 | -4.668466e-11 | 0.010819605 |
| boundary_rc | BE | 0.100000000 | 320.000000000 | 302.712117272 | 2.590661e-11 | 0.005411607 |
| boundary_rc | BE | 0.050000000 | 320.000000000 | 302.709411919 | 2.826589e-11 | 0.002706255 |
| boundary_rc | EXACT | 0.200000000 | 320.000000000 | 302.706705665 | -6.533352e-11 | 1.705303e-13 |
| boundary_rc | EXACT | 0.100000000 | 320.000000000 | 302.706705665 | -1.191580e-11 | 0 |
| boundary_rc | EXACT | 0.050000000 | 320.000000000 | 302.706705665 | 1.213392e-10 | 6.252776e-13 |
| two_node_rc | EE | 0.200000000 | 320.000000000 | 300.048687154 | 1.193712e-10 | 0.000887889 |
| two_node_rc | EE | 0.100000000 | 320.000000000 | 300.049129984 | -9.663381e-11 | 0.000445060 |
| two_node_rc | EE | 0.050000000 | 320.000000000 | 300.049352235 | -4.888534e-10 | 0.000222809 |
| two_node_rc | BE | 0.200000000 | 320.000000000 | 300.050471856 | 3.979039e-11 | 0.000896813 |
| two_node_rc | BE | 0.100000000 | 320.000000000 | 300.050022334 | -1.648459e-10 | 0.000447291 |
| two_node_rc | BE | 0.050000000 | 320.000000000 | 300.049798410 | 3.410605e-11 | 0.000223367 |
| two_node_rc | EXACT | 0.200000000 | 320.000000000 | 300.049575044 | -3.069545e-10 | 1.136868e-12 |
| two_node_rc | EXACT | 0.100000000 | 320.000000000 | 300.049575044 | -5.798029e-10 | 1.932676e-12 |
| two_node_rc | EXACT | 0.050000000 | 320.000000000 | 300.049575044 | -9.492851e-10 | 3.240075e-12 |

Maximum EXACT-vs-closed-form error over these rows is 3.240075e-12 K.
Both EE and BE errors decrease with refinement for the two nontrivial RC references.
Zero-input/same-temperature invariance is separately tested for all three methods.
Analytic and energy assertions are independent: matching energy alone is not used as temperature proof.

## 5. dt convergence: actual 0.2 / 0.1 / 0.05 s meshes

All cases run to 100 s using BE. Linear is the boundary RC above; chain is constant 120 W;
step is 30 W until exactly 20 s, then 120 W. All other inputs/events/initial conditions are identical.
The comparison rejects changed qualification inputs; event-aligned but identical effective meshes
return NOT_EVALUABLE. A 73 ms event test independently checks exact split energy (92.7 J).

Peaks/headroom evaluate all accepted endpoints; trajectories use linear interpolation at the union
of physical sample times. Same method is used within each refinement group.
Each thermal run passes per-interval and signed/absolute accumulated energy gates.

| Fixture | dt (s) | Accepted substeps | Peak T (K) | Min headroom (K) | Final node max error vs EXACT (K) | Gate |
|---|---|---|---|---|---|---|
| linear | 0.200000000 | 500.000000000 | 320.000000000 | 80.000000000 | 0.010819605 | PASS |
| linear | 0.100000000 | 1000.000000000 | 320.000000000 | 80.000000000 | 0.005411607 | PASS |
| linear | 0.050000000 | 2000.000000000 | 320.000000000 | 80.000000000 | 0.002706255 | PASS |
| chain | 0.200000000 | 500.000000000 | 312.511127803 | 87.488872197 | 0.004053602 | PASS |
| chain | 0.100000000 | 1000.000000000 | 312.513154503 | 87.486845497 | 0.002026902 | PASS |
| chain | 0.050000000 | 2000.000000000 | 312.514167928 | 87.485832072 | 0.001013477 | PASS |
| step | 0.200000000 | 500.000000000 | 311.733098986 | 88.266901014 | 0.004231120 | PASS |
| step | 0.100000000 | 1000.000000000 | 311.735214927 | 88.264785073 | 0.002115180 | PASS |
| step | 0.050000000 | 2000.000000000 | 311.736272611 | 88.263727389 | 0.001057495 | PASS |

Adjacent differences:

| Fixture | Pair (s) | Peak/headroom diff (K) | Node trajectory Linf (K) | Air diff (J) | Liquid export diff (J) | Plate-to-liquid diff (J) |
|---|---|---|---|---|---|---|
| linear | 0.2 vs 0.1 | 0 | 0.007353916 | 0.540799794 | 0 | 0 |
| linear | 0.1 vs 0.05 | 0 | 0.003677875 | 0.270535231 | 0 | 0 |
| chain | 0.2 vs 0.1 | 0.002026700 | 0.008362821 | 0.270851563 | 2.402119350 | 2.045152173 |
| chain | 0.1 vs 0.05 | 0.001013425 | 0.004181755 | 0.135495436 | 1.201967115 | 1.023080146 |
| step | 0.2 vs 0.1 | 0.002115940 | 0.007560444 | 0.260057666 | 2.108455038 | 1.994435658 |
| step | 0.1 vs 0.05 | 0.001057685 | 0.003779630 | 0.130099287 | 1.055003655 | 0.997806480 |

Required coarse-versus-finest diagnostic (not substituted for adjacent gates):

| Fixture | 0.2 vs 0.05 peak/headroom (K) | Air diff (J) | Liquid export diff (J) | Plate-to-liquid diff (J) |
|---|---|---|---|---|
| linear | 0 | 0.811335025 | 0 | 0 |
| chain | 0.003040125 | 0.406346999 | 3.604086465 | 3.068232320 |
| step | 0.003173625 | 0.390156953 | 3.163458693 | 2.992242138 |

Frozen peak and headroom tolerance: 0.1 K each. Additional predeclared fixture-only criteria:
node trajectory Linf <= 0.1 K; each heat integral difference <= max(1 J, 1% of finest integral).
These heat criteria are extra thermal checks, **not** a claim that Contract 11's pump-energy row is
a liquid-heat tolerance. Fine-pair difference must decrease, or both pairs must be below 10% of
the corresponding tolerance. All applicable comparisons pass; pump/pressure/actuator/control target
criteria are out of this Phase 3 scope, not silently declared passed.
The worst adjacent peak difference is 0.002115940 K; worst node trajectory difference 0.008362821 K.
Final node errors toward EXACT decrease for all three cases, not just agreement between coarse runs.

## 6. Energy conservation

Signed residual r = stored change - (input - external air - external liquid), computed from full
precision interval ledgers; the rounded printed columns need not close to the displayed residual.

| Fixture | dt (s) | Input (J) | Stored change (J) | Air export (J) | Liquid boundary export (J) | Signed residual (J) |
|---|---|---|---|---|---|---|
| linear | 0.200000000 | 0 | -1728.247473047 | 1728.247473047 | 0 | -4.668466e-11 |
| linear | 0.100000000 | 0 | -1728.788272841 | 1728.788272841 | 0 | 2.590661e-11 |
| linear | 0.050000000 | 0 | -1729.058808072 | 1729.058808072 | 0 | 2.826589e-11 |
| chain | 0.200000000 | 12000.000000000 | 10240.995380341 | 495.766404900 | 1263.238214759 | -2.528804e-10 |
| chain | 0.100000000 | 12000.000000000 | 10243.668351254 | 495.495553337 | 1260.836095409 | -3.877778e-10 |
| chain | 0.050000000 | 12000.000000000 | 10245.005813806 | 495.360057901 | 1259.634128294 | 8.827010e-10 |
| step | 0.200000000 | 10200.000000000 | 9008.653633939 | 373.296227173 | 818.050138888 | -6.367475e-10 |
| step | 0.100000000 | 10200.000000000 | 9011.022146642 | 373.036169507 | 815.941683850 | -1.284976e-9 |
| step | 0.050000000 | 10200.000000000 | 9012.207249586 | 372.906070220 | 814.886680195 | 1.357722e-9 |

Residual details across all node/device/subsystem CVs (W percentile uses interval/CV samples):

| Fixture | dt (s) | Max interval/CV residual abs (J) | Subsystem sum abs residual (J) | Max equivalent residual (W) | P95 equivalent residual (W) |
|---|---|---|---|---|---|
| linear | 0.200000000 | 2.830847e-12 | 7.269165e-10 | 1.415423e-11 | 1.358696e-11 |
| linear | 0.100000000 | 2.836509e-12 | 1.455954e-9 | 2.836509e-11 | 2.700073e-11 |
| linear | 0.050000000 | 2.839506e-12 | 2.831592e-9 | 5.679013e-11 | 5.428769e-11 |
| chain | 0.200000000 | 8.713386e-11 | 1.539562e-8 | 4.356693e-10 | 2.519478e-10 |
| chain | 0.100000000 | 8.431300e-11 | 2.985208e-8 | 8.431300e-10 | 4.916779e-10 |
| chain | 0.050000000 | 8.740209e-11 | 6.074129e-8 | 1.748042e-9 | 9.988292e-10 |
| step | 0.200000000 | 8.589396e-11 | 1.543612e-8 | 4.294698e-10 | 2.527663e-10 |
| step | 0.100000000 | 8.874501e-11 | 2.921447e-8 | 8.874501e-10 | 4.896202e-10 |
| step | 0.050000000 | 8.895973e-11 | 6.006788e-8 | 1.779195e-9 | 9.932359e-10 |

Across the reported analytic/refinement/split matrix:
max interval/CV abs residual = 8.895973e-11 J;
max absolute subsystem signed cumulative residual = 1.357722e-9 J;
max subsystem sum of absolute interval residuals = 6.074129e-8 J;
max equivalent residual = 1.779195e-9 W;
largest per-run P95 = 9.988292e-10 W.
These maxima describe the listed matrix, not every conceivable input or hardware accuracy.

All internal InterfaceEnergy.node_postings are tested for exact equal/opposite cancellation.
Separate tests partition/recombine device and uncovered node balances and reject duplicate storage,
duplicate interfaces, duplicate source receipts and dynamic-boundary ownership. Internal edges cannot
be labeled as external AIR/LIQUID losses. Smaller dt can increase accumulated roundoff while decreasing
temperature truncation error; both energy criteria still have to pass without relaxed tolerance.

## 7. Coldplate Rth(flow), endpoints and zero flow

Rcp = R_conduction + 1 / (h_ref (abs(m)/m_ref)^n A). Scan holds endpoints at 320/300 K:

| Flow (kg/s) | Rth (K/W) | Q at 320/300 K (W) | Model domain |
|---|---|---|---|
| 0.010000000 | 0.270593617 | 73.911573508 | VALID |
| 0.050000000 | 0.101225240 | 197.579181556 | VALID |
| 0.100000000 | 0.070000000 | 285.714285714 | VALID |
| 0.200000000 | 0.050778610 | 393.866627476 | VALID |
| 0.500000000 | 0.036206566 | 552.385995907 | VALID |

Rcp is non-increasing and >= R_conduction; Q increases with flow over the declared domain.
Reversed thermal gradient preserves signed Q; no max(Q,0) clipping.
Generic endpoints must be coldplate solid → local bulk coolant, never die → coolant.
Included plate-conduction/convection layer names normalize their contract/example aliases before
ownership checks. Imported composite TIM plus an existing TIM interface fails
THERMAL_RESISTANCE_OVERLAP / CONFIG_INVALID. Imported endpoint mismatch fails IMPORT_CONFLICT.
Manufacturer import is schema validation only, not an executable invented performance curve.

Default zero flow => MODEL_INVALID. An explicitly configured finite numerical no-flow fixture
(R=2 K/W) gives Q=10 W at 320/300 K; no minimum-flow substitution. That fixture remains UNVALIDATED
and does not qualify a real zero-flow device model. Coldplate evaluation leaves coolant state unchanged;
only ThermalIntegrator advances its one storage owner.

## 8. Air/liquid split from the network

Same immutable 120 W electrical leaves, 100 s, BE dt=0.1 s in all cases.
A: base chain. B: plate R_conduction increased from 0.02 to 0.2 K/W.
C: package R_air reduced from 0.8 to 0.2 K/W. These A/B/C labels are **local split-test cases**,
not the prohibited full benchmark A/B/C or FAIR_COMPARISON.

| Case | Input (J) | Stored (J) | Air export (J) | Liquid boundary export (J) | Plate → coolant internal (J) | Signed residual (J) |
|---|---|---|---|---|---|---|
| A | 12000.000000000 | 10243.668351254 | 495.495553337 | 1260.836095409 | 2642.520292710 | -3.877778e-10 |
| B_higher_liquid_R | 12000.000000000 | 11014.520762087 | 531.242703166 | 454.236534747 | 987.859333546 | -7.055512e-11 |
| C_lower_air_R | 12000.000000000 | 9073.854853158 | 1773.922758850 | 1152.222387993 | 2383.790250476 | 1.227919e-9 |

Greater liquid resistance decreases plate-to-liquid transfer and increases stored heat/air export.
Lower air resistance increases air export. No fixed capture fraction changes electrical allocation
or determines core GPU heat routing. Internal coolant heat minus bath export equals coolant storage
change rather than disappearing as a spurious numerical residual.

## 9. Tests and invalid-domain handling

Final independent Phase 3 test run: **100 passed, 0 failed**, 15.99 s, warnings as errors.
V0.1 regression run: **72 passed, 0 failed**, 26.94 s, warnings as errors.
Total: 172 tests passed in the two explicitly scoped suites. No tests skipped.

During the final added-test pass, a misplaced boundary-test fragment caused a NameError in
test_invalid_domains.py. It was separated into its own test; the final 100-test rerun above passed.
This was a test-assembly error, not a suppressed numerical failure.

| Mandatory category | Result / executable evidence under v0_2/tests/thermal/ |
|---|---|
| 1 Zero input | PASS: test_single_node.py, all integrators |
| 2 Insulated constant power | PASS: test_single_node.py, analytical P dt / C |
| 3 Two-node RC | PASS: test_rc_pair.py, equilibrium/closed form/energy |
| 4 Boundary RC | PASS: test_integrator_reference.py, EE/BE/EXACT |
| 5 Single source receipt | PASS: test_power_mapping.py, 1200 W parent including 200 W child; not 1400 W |
| 6 Coldplate monotonicity | PASS: test_coldplate.py, scan and conduction floor |
| 7 Endpoint/layer ownership | PASS: test_coldplate.py, valid topology and rejected TIM/alias conflicts |
| 8 Zero flow | PASS: test_coldplate.py, default invalid/explicit finite model |
| 9 Network air/liquid split | PASS: test_air_liquid_split.py |
| 10 Internal cancellation | PASS: test_energy_conservation.py |
| 11 Storage ownership | PASS: test_energy_conservation.py, duplicate storage rejected |
| 12 Invalid domains | PASS: test_invalid_domains.py and test_coldplate.py |

Additional tests reject missing/extra source maps, parent/child coexistence, component overlap,
negative/nonfinite C or R, illegal bounds, missing/incorrect-unit boundaries, duplicate node IDs,
unknown endpoints, flow below/above domain, unqualified reverse flow, coolant mismatch,
material/coldplate temperatures outside domain, excessive coldplate heat, invalid timestamps and
future source timestamps. They also cover retry recovery, full rollback, immutable node properties,
source allocation provenance and no calibration promotion. Failures are explicit; no silent extrapolation.

## 10. Frozen baseline and package verification

- Approved V0.1 base remains `62c0220e8e8b7edffc5ef59c8dfaa282f4d1c812`; never rewritten.
- Current committed HEAD `020f6817dd5739024acde7f81467eb8d797e471a` is its docs-only descendant.
- All **64** baseline source/config/test/packaging byte hashes match; all **18** registered frozen
  document hashes match. Total 82 checks, zero mismatches.
- Source subtree object unchanged: `7c4372a65b569aabf3fc3f2c1dfa2b22a35d9c48`.
- Baseline-vs-working diff on src/c2c, configs, tests and root pyproject.toml is empty.
- Python 3.11.9, NumPy 2.4.6, pytest 9.1.1; Ruff checks passed and 28 Python files formatted.
- Independent wheel built successfully with pip build isolation. Legacy environment lacked bdist_wheel
  for the first no-isolation attempt; isolated build dependencies resolved that without upgrading
  or installing into V0.1. Final wheel: c2c_dtb_thermal_v02-0.2.0a3-py3-none-any.whl,
  SHA-256 `9b2e0093d12a0f3502513f0d4a32355412e9c3fa1dcca0a5bf49f6a9da0665c7`.
  Build artifacts stay ignored under .tmp-phase3-wheel/ and build/egg-info paths.
- Isolated-interpreter import from the wheel executes the insulated example without importing c2c.
  This is packaging/smoke verification, not a separate hardware test.

Reproduce from repository root:

```powershell
.venv/Scripts/python.exe -m pytest -c v0_2/pyproject.toml v0_2/tests -W error
.venv/Scripts/python.exe -m pytest tests -W error
.venv/Scripts/ruff.exe check .
.venv/Scripts/ruff.exe format v0_2 --check
.venv/Scripts/python.exe -m v0_2.examples.phase3_validation
.venv/Scripts/python.exe -m pip wheel ./v0_2 --no-deps --wheel-dir .tmp-phase3-wheel
```

The validation example emits the underlying numeric tables as stdout JSON, without editing frozen
files. Wheel bytes may vary across builds; the above hash identifies this build, not a universal lock.

## 11. Required self-review

| # | Question | Answer / evidence |
|---|---|---|
| 1 | Electrical power injected twice? | No in accepted tested inputs: IDs, coverage and mapping audited before integration. |
| 2 | BOARD_POWER directly into die? | Rejected; parent budget must first resolve to typed component leaves. |
| 3 | Coldplate crosses correct endpoints? | Yes; generic plate-solid/local-bulk types and definition match enforced. |
| 4 | TIM double counted? | Declared duplicate physical layers, including aliases, rejected before solving. |
| 5 | One plate/coolant storage owner? | Unique storage IDs; immutable state; only integrator advances T. |
| 6 | Internal Q equal/opposite? | Exactly one stored signed energy with opposite node postings. |
| 7 | Air/liquid split network-derived? | Yes; same-source three-network test changes transfers/storage. |
| 8 | Fixed capture fraction in core? | None. Electrical allocation is separate from thermal heat routing. |
| 9 | Fake flow at zero? | None; invalid unless explicitly configured finite no-flow model. |
| 10 | Silent extrapolation? | No; declared flow/T/heat/coolant domains checked at old and accepted states. |
| 11 | BE conservative? | Shared implicit fluxes pass each CV interval/cumulative gates and rollback tests. |
| 12 | Analytic references? | Insulated, boundary RC, two-node closed forms plus independent exact linear chain. |
| 13 | Refinement toward correct solution? | EE/BE RC errors decrease; all BE chain/step final errors toward EXACT decrease. |
| 14 | Residuals pass? | Yes; signed and sum-absolute criteria, with max/P95 W reported above. |
| 15 | Generic values presented as GB300 official? | No; provenance remains assumptions/unvalidated after passing tests. |
| 16 | V0.1 unchanged? | Yes; 64 fingerprints, unchanged subtree and 72 passing legacy tests. |

Self-review corrections before gate: normalized thermal layer aliases; rejected incomplete generic
layer declarations; reserved node CV names; required identical inputs for dt qualification; rejected
internal-external interface misclassification. Frozen contracts were not altered to accommodate code.

## 12. Phase 3 gate checklist

| Required item | Status |
|---|---|
| Power source mapping | PASS |
| No duplicate thermal receipt | PASS |
| Node energy definition | PASS |
| Internal interface cancellation | PASS |
| Coldplate endpoint ownership | PASS |
| Rth(flow) monotonicity | PASS |
| Zero-flow policy | PASS |
| Air/liquid dynamic split | PASS |
| Energy conservation | PASS |
| Analytic reference | PASS |
| Backward Euler | PASS |
| dt convergence | PASS |
| Invalid-domain handling | PASS |
| Provenance | PASS |
| V0.1 regression | PASS |

**PHASE3_GATE_STATUS = PASS. Blocking issues in the requested Phase 3 scope: NONE.**

## 13. Open limitations and missing OEM/GB300 data

This release is a generic software/numerical validation core. It has no calibrated hardware profile,
variable-C runtime solver, executable manufacturer import, coolant advection, hydraulic network,
closed-loop controller, comprehensive rack benchmark or real-time telemetry validation.
Accepted endpoint checks do not constitute a proof of all continuous-time extrema for arbitrary
future nonlinear models. A larger N-device model will need independent performance/scalability tests.

Still needed before hardware claims:
1. GPU/CPU die, package, HBM and VRM thermal capacities/resistances, TIM/contact conditions, physical
   node/storage definitions and measured electrical coverage/allocation evidence.
2. Manufacturer Rth–flow curves with exact hot/cold temperature definitions and layer ownership,
   heat distribution, inlet/bulk temperature convention, qualified flow/T/heat domain and uncertainty.
3. Actual fluid formulation/Cp/enthalpy, local coolant inventories and measured flow distribution;
   qualified finite zero-flow behavior where continued zero-flow operation is modeled.
4. Device-specific operating/derate/hard limits and synchronized power/temperature transient traces
   for calibration; no use of this fixture's 400 K reference as a safety limit.
5. Later-phase tray/rack hydraulics, pump/CDU/HX/FWS and measurement/actuator characteristics,
   with identified hardware/firmware and validated sensor timing.

STOP here. No Phase 4 work or GitHub publication follows without user review/authorization.
