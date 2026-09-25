# C2C-DTB V0.2 — Phase 4.1 coupled-plant control authority

**PHASE4_1_GATE_STATUS = PASS for the generic numerical fixture.** Phase 4 is ready for **user freeze review**, not for an OEM/GB300 performance or safety claim. Phase 5–7 have not been started. Reproduce the raw data with `python -m v0_2.examples.phase4_1_validation` and run the executable assertions in `v0_2/tests/plant/test_control_authority.py`.

## Purpose, boundaries and pre-registered policy

This is a verification stage, not a new controller or a new plant model. `pump_speed_actual` is still a prescribed physical input; the hydraulic map remains quasi-steady and there is no actuator lag. The test exercises the **full secondary loop**: pump → common pressure manifold → two coldplate branches → return volumes → finite CDU → HX/FWS → supply. No Phase 3 `R_test_bath` appears in the physical topology; bath plus advection remains `CONFIG_INVALID`.

All values are `NUMERICAL_TEST_FIXTURE / ENGINEERING_ASSUMPTION / UNVALIDATED`, not GB300/OEM parameters. Registered before evaluating outcomes: two identical 240 W device sources, 120 s duration, 0.2 s nominal step, fixed final 20% assessment window **[96,120] s**, speeds **0.50/0.70/0.90**, branch-0 hydraulic K multiplier **1.5**, and a speed step at **40 s** from 0.50 to 0.90. The fixed terminal window is a reproducible quasi-steady *assessment convention*, not a demonstrated mathematical equilibrium. Practical minimum changes: flow/Rth exceed both 10× numerical audit tolerance and 0.1% relative; Q difference exceeds 0.01 W; temperature effect exceeds `max(0.05 K, 5× fine-pair mesh difference)`. These are test policies, not hardware requirements. Pump speed is the only changed input in the sweep; branch-0 K is the only changed plant parameter in the restriction test.

## Hydraulic → coldplate wiring and audit

The accepted `HydraulicSolution.branch_flows_m3_s[branch] × ρ` is the **sole authoritative** local coldplate mass flow. The same flow object is passed to the Phase 3 coldplate conductance evaluation, and the resulting `g=1/Rcp` is entered into the coupled thermal matrix. A runtime assertion checks that the actual flow supplied to that evaluation matches the current branch solution within the existing mass-flow numerical tolerance. An accepted step exposes a read-only `ColdplateUse` record of the **matrix-used** flow, Rth and conductance. `ControlAuthorityTrace` combines that record with the accepted shared interface heat ledger and resulting temperatures; it does not evaluate a second physics state.

Each interval records start/end ns, actual speed, pump ΔP, total and branch flows, Rth, plate/local-coolant/device/package/branch-return temperatures, plate→coolant W, HX W, pump electrical W, and a chain of `pump_state_id → hydraulic_solution_id → branch_flow_record_id → coldplate_evaluation_id → thermal_step_id`. The hydraulic ID is a deterministic digest of this interval's time, speed, pressure and flows. These are audit links, **not security signatures**. Tests confirm same-interval and right-side event timing, branch mapping, independent Phase 3 Rth(flow), and the ledger equality `Qplate = g_matrix(Tplate,new−Tbulk,new)`. Mocked stale, future and wrong-branch flows produce `CONTROL_AUTHORITY_PATH_INVALID`, failed transactional steps and no ledger. A forged old matrix-conductance claim is likewise rejected by the audit. No physical heating or cooling outcome is manually injected.

## A. Pump-speed control authority

Both branches have the same figures in this equal-K fixture; each is separately emitted and asserted in the evidence JSON. `Q` and device/plate K are averages over the fixed [96,120] s window; peaks/finals cover the full 120 s. Pressure, total/branch flow, Rth and pump W are interval values from the final accepted hydraulic solution.

| Speed | Pump ΔP Pa | Total kg/s | Branch b0 / b1 kg/s | Rcp b0 / b1 K/W | Plate→liquid W avg, each | Device peak / final K | Plate peak / final K | Return K | Pump electrical W |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 13125.000 | 0.136931 | 0.068465 / 0.068465 | 0.085184 / 0.085184 | 128.072 | 326.296703 / 326.296703 | 309.568749 / 309.568749 | 297.904170 | 3.328175 |
| 0.70 | 25725.000 | 0.191703 | 0.095851 / 0.095851 | 0.071505 / 0.071505 | 142.689 | 325.688223 / 325.688223 | 308.665673 / 308.665673 | 297.804657 | 9.132513 |
| 0.90 | 42525.000 | 0.246475 | 0.123238 / 0.123238 | 0.063197 / 0.063197 | 152.817 | 325.245169 / 325.245169 | 308.017726 / 308.017726 | 297.774306 | 19.409918 |

Window-average device temperature follows **325.375722 → 324.878016 → 324.512947 K** and plate temperature **308.868477 → 308.087744 → 307.522911 K** as speed rises. Thus the measured chain is speed ↑ → pump operating pressure/total flow ↑ → branch flow ↑ → Phase 3 coldplate Rth ↓ → the actual matrix/ledger plate-to-liquid Q changes → stored-device temperature decreases. The low-to-high device window change is **0.862775 K**, far above the 0.05 K policy threshold. The result is not inferred from a flow number alone. Every speed remains within the declared coldplate valid-flow range; a separate 0.02 speed case falls below it and fails `MODEL_OUT_OF_RANGE` without flow clamping. Mass, full-loop energy and pump-energy closure pass at all three speeds.

## B. Branch restriction propagation

Both simulations have identical source traces, FWS, speed 0.9, initial thermal state, thermal interfaces, other hydraulic edges, duration and dt. Only the first hydraulic edge of branch 0 changes K by 1.5×. Window columns use [96,120] s.

| Case | Branch | K multiplier | Pump ΔP Pa | Flow kg/s | Rcp K/W | Plate→liquid W avg | Device window K | Device final K | Plate final K |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | b0 | 1.0 | 42525.000 | 0.123238 | 0.063197 | 152.817 | 324.512947 | 325.245169 | 308.017726 |
| Baseline | b1 | 1.0 | 42525.000 | 0.123238 | 0.063197 | 152.817 | 324.512947 | 325.245169 | 308.017726 |
| Restricted | b0 | 1.5 | 42930.913 | 0.112415 | 0.066067 | 149.057 | 324.649481 | 325.410705 | 308.259361 |
| Restricted | b1 | 1.0 | 42930.913 | 0.125684 | 0.062606 | 153.678 | 324.482431 | 325.208045 | 307.963201 |

The restriction changes the pump operating point: total flow falls from **0.246475** to **0.238098 kg/s**; it is not artificially held constant. Branch 0 flow falls by **0.010823 kg/s**, Rth rises by **0.002871 K/W**, window-average Q falls by **3.760 W**, and window-average device temperature rises by **0.136534 K** (final rise **0.165535 K**). The unrestricted branch gains flow and cools slightly, consistent with redistribution. No device power, FWS boundary, Rth parameter, or temperature was adjusted to manufacture this consequence.

## C. Dynamic prescribed-speed step

The event at exactly 40 s changes the *held physical speed input* for `[40 s,next)`. The event does not assign a new thermal state. Temperature at the event is the pre-event accepted state; the first post-event thermal advance ends at 40.2 s.

| Observation | Time interval s | Speed | Pump ΔP Pa | Branch flow kg/s | Rcp K/W | Plate→liquid W | Device K |
|---|---|---:|---:|---:|---:|---:|---:|
| Before | [39.8,40.0) | 0.50 | 13125 | 0.068465 | 0.085184 | 47.060 | 317.179318 |
| Event instant, unchanged state | 40.0 | 0.50→0.90 | — | — | — | — | 317.179318 |
| First hydraulic/thermal interval | [40.0,40.2) | 0.90 | 42525 | 0.123238 | 0.063197 | 63.860 | 317.216814 |
| Late | [119.8,120.0) | 0.90 | 42525 | 0.123238 | 0.063197 | 163.699 | 325.344071 |

The hydraulic solution and Rth update at the right-side event, while device temperature is continuous at 40 s; its first 0.2 s change is **0.037496 K**, not an instantaneous jump to the late temperature. No future/stale flow is accepted and no actuator delay is simulated.

## Mass/energy and three-mesh qualification

For the speed step, restriction baseline and restricted plant, the same event/topology/source/FWS and initial state were run on **actual 0.2/0.1/0.05 s meshes** (600/1200/2400 steps). The established Phase 4 trajectory/energy gate is PASS for all three groups. Additional Phase 4.1 comparisons include branch flow, matrix-used Rth, plate→coolant heat integral, final device and branch-return temperature, HX export, plus each run's mass and energy ledger.

| Group | dt s | Branch flow kg/s | Rcp K/W | Plate→liquid J | Final device K | Final return K | HX export J | Mass/energy gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Speed step | .20 | .123238 | .063197 | 10409.772 | 325.344071 | 297.804773 | 90372.082 | PASS |
| Speed step | .10 | .123238 | .063197 | 10405.533 | 325.348289 | 297.804266 | 90378.571 | PASS |
| Speed step | .05 | .123238 | .063197 | 10403.412 | 325.350398 | 297.804013 | 90381.816 | PASS |
| Restriction baseline | .20 | .123238 | .063197 | 10545.280 | 325.245169 | 297.774306 | 91988.337 | PASS |
| Restriction baseline | .10 | .123238 | .063197 | 10540.700 | 325.249641 | 297.773769 | 91994.865 | PASS |
| Restriction baseline | .05 | .123238 | .063197 | 10538.409 | 325.251878 | 297.773500 | 91998.131 | PASS |
| Restriction ×1.5 | .20 | .112415 | .066067 | 10232.845 | 325.410705 | 297.799378 | 91745.373 | PASS |
| Restriction ×1.5 | .10 | .112415 | .066067 | 10228.240 | 325.415172 | 297.798842 | 91751.915 | PASS |
| Restriction ×1.5 | .05 | .112415 | .066067 | 10225.936 | 325.417407 | 297.798574 | 91755.187 | PASS |

Flow and Rth mesh differences are **zero** because the quasi-steady hydraulic solution uses the same held speed/K per interval. Adjacent errors decrease for every varying quantity: step plate heat **4.239→2.121 J**, device final **0.004217→0.002109 K**, return **0.000507→0.000253 K**, HX **6.489→3.246 J**; baseline/restricted show the same decreasing pattern. The worst fine-pair device difference for the restriction comparison is **0.002237 K**, making `5× uncertainty = 0.011184 K`; the pre-registered practical threshold remains **0.05 K**. Restricted branch final effect on the fine mesh is **0.165529 K**, clearly above both. Max hydraulic-node/volume mass residual among these runs is **2.78e-17 kg/s**; max signed full-loop energy residual absolute magnitude **7.79e-9 J**. All per-step and cumulative signed/absolute mass and energy gates pass; pump electrical = hydraulic + VFD + motor + internal losses in every sweep/step/restriction case.

## Regression, coupling-bug review and gate

The existing plant coupling was already correct: current hydraulic branch flow reached the current Phase 3 coldplate model and its conductance entered the coupled matrix. **No pre-existing coupling bug was found or physical law changed.** The minimal code addition is an explicit runtime wiring guard plus read-only used-flow/Rth/trace records. Negative tests demonstrate that stale, future or wrong-branch input, or a falsely reported matrix conductance, cannot pass the audit. Phase 3 thermal physics, Phase 4 hydraulic architecture, frozen contracts and V0.1 files were not changed for this stage.

Verification result: Phase 4.1 new tests **12 PASS**; Phase 4 existing tests **37 PASS** (including two rendered-report checks added after the original 35-test Phase 4 report); Phase 3 existing tests **100 PASS**; V0.1 tests **72 PASS**. The isolated V0.2 suite totals **149 PASS**, with no skipped or failing tests in the final run. All 82 frozen/baseline hashes match, and no V0.1 source/config/test/packaging diff exists. Physical bath/advection mutual exclusion remains PASS. One earlier long qualification run raised a nonreproducible Python object-type exception inside the existing statistics traversal; the isolated case and three subsequent full V0.2 runs passed. The validation script now releases each three-mesh group before creating the next to reduce peak memory. Its error's exact cause was not proven; this is a test-stability observation, **not** an observed conservation or coupling failure. No numerical gate item is blocked for this generic fixture; all actual GB300 pump/branch/coldplate/CDU/FWS/fluid data remain `CALIBRATION_REQUIRED` as listed in `PHASE4_PHYSICAL_PLANT_REPORT.md`. There is no controller implementation or real-hardware control-authority claim.

Self-review: pump speed affects operating point and branch flow; the branch solution is the only coldplate flow source; Rth is evaluated at runtime from that flow; matrix conductance and heat ledger match that Rth; speed and branch K each produce a device-temperature effect exceeding the registered numerical threshold; no thermal outcome was manually injected; no bath, future, stale or wrong-branch flow is accepted; thermal state is continuous at the speed event; mass/energy and all three regression suites pass.

**PHASE4_1_GATE_STATUS = PASS. PHASE 4 VERIFIED AND READY FOR USER FREEZE REVIEW. STOP; await user review before any Phase 5 work.**
