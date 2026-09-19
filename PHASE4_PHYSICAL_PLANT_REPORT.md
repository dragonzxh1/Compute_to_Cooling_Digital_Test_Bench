# C2C-DTB V0.2 Phase 4 physical-plant verification

Status: **PHASE4_GATE_STATUS = PASS for the declared generic numerical fixture only.** This is not an OEM-calibrated GB300 model, a safety claim, or an authorized controller. Phase 5–7 are not started. Reproduce the numerical evidence with `python -m v0_2.examples.phase4_validation`; all tabulated values below are from that module, not GB300 measurements. The fixture parameters are marked `ENGINEERING_ASSUMPTION / NUMERICAL_TEST_FIXTURE / UNVALIDATED`.

## Scope and compatibility

The isolated `v0_2` implementation now has: `fluids/` (constant-Cp density/enthalpy), `coolant/` (finite-volume inventory and signed upwind transport), `hydraulics/` (junction/edge graph, quadratic resistance, parallel common-manifold solution and pump drive), `cdu/` (finite heat-transfer effectiveness), and `plant/` (coupled solids/liquids, physical loop, FWS input and signed ledgers). The fixture models 1, 2, or 4 coldplate branches, supply/return cells, manifolds, a finite CDU tank, pump, and an isolated primary FWS side. It reuses Phase 3 solid nodes, power mapping, coldplate conductance, provenance and validity semantics. No controls, PLC, safety supervisor, feedforward, DCGM or actuator dynamics were added.

The physical fixture contains **no `R_test_bath`**. The Phase 3 validation bath remains available only in its standalone topology. Adding a liquid bath to an advective plant raises `THERMAL_PATH_DOUBLE_COUNT` with `CONFIG_INVALID`; enabling legacy FIFO raises `TRANSPORT_DOUBLE_COUNT`; posting pump hydraulic work at the pump and at passive edges raises `PUMP_HEAT_DOUBLE_COUNT`. These are constructor/preflight tests, not merely documentation conventions. A local coolant inventory has one storage owner: its Phase 3-style thermal node is replaced by one fluid volume, not duplicated.

## Model and independent references

Fluid cells carry fixed mass `M`, specific enthalpy `h = Cp (T−Tref)`, stored energy `Mh`, and residence time `M/m_dot`. A shared signed flux `m_dot h_donor` is posted once as a debit to the donor and a credit to the receiver. The implicit finite-volume solve preserves each cell's mass; reversible links change the donor when flow changes sign. At zero flow a cell retains mass, enthalpy and temperature. The analytic one-cell reference is `T(t)=Tin+(T0−Tin)exp(−m_dot t/M)`; the two-cell cascade has the independent Erlang-form reference tested in `test_coolant_transport.py`. These boundaries are numerical fixtures, not an unmodelled physical bath in the full loop.

Each passive hydraulic edge uses signed `ΔP=K Q|Q|`. All parallel paths share actual supply/return pressure junctions. The quadratic pump curve `H=H0·speed²−Kpump Q²` intersects the series-plus-parallel system curve directly; branch flows are computed from the common pressure drop with **no after-the-fact normalization**. There is no commanded-pressure shortcut. This exact closed-form solver for the declared graph reports one solve iteration, pressure, node mass, and pump-curve residuals; arbitrary non-quadratic networks would require a different solver. Negative/impossible maps, unsupported reverse flow, out-of-range speed/flow and invalid K fail rather than clip or reuse a prior state.

The drive separates `P_electrical`, `P_hydraulic=ΔP·Q`, VFD/motor/internal losses, liquid vs ambient destinations, and explicitly parameterized zero-flow standby power. Hydraulic work becomes heat only through passive resistance receivers; it is not also deposited at the pump. The secondary CDU volume stores energy, while HX transfer uses both sides' `m_dot Cp`, UA and counterflow/parallel ε-NTU effectiveness; the FWS primary is a distinct fluid identity, has no secondary mass transfer, and has a declared inlet temperature and flow, not an infinite-temperature bath. No HX wall storage or valve dynamics is claimed. The coupled step is transactional: a failed validation/solve returns the old state and no committed ledger.

## Raw hydraulic and pump results

Generic fixture uses `H0=60,000 Pa`, `Kpump=1e11 Pa/(m³/s)²`, two equal branch path K of `2e12 Pa/(m³/s)²`, and four series pipe K of `5e10 Pa/(m³/s)²` each. All these values require calibration. `branch ΔP` below is the shared manifold pressure drop; flows are mass flows at fixture `ρ=1000 kg/m³`.

| Branches / branch-0 K multiplier | Speed | Total kg/s | Pump ΔP Pa | Branch kg/s | Branch ΔP Pa | Solver residual norm | Max node mass kg/s | Max pressure Pa | Pump-curve Pa |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 1 / 1 | 0.9 | 0.145363114 | 46486.9565 | 0.145363114 | 42260.8696 | 7.28e-12 | 0 | 2.27e-12 | 7.28e-12 |
| 2 / 1 | 0.6 | 0.164316767 | 18900.0000 | 0.082158384, 0.082158384 | 13500.0000 | 3.64e-12 | 0 | 4.55e-13 | 3.64e-12 |
| 2 / 1 | 0.9 | 0.246475151 | 42525.0000 | 0.123237575, 0.123237575 | 30375.0000 | 0 | 0 | 0 | 0 |
| 2 / 2 | 0.9 | 0.231592524 | 43236.4903 | 0.104098464, 0.127494060 | 32509.4708 | 1.09e-11 | 2.78e-17 | 1.09e-11 | 0 |
| 4 / 1 | 0.9 | 0.338161117 | 37164.7059 | 0.084540279 each | 14294.1176 | 7.28e-12 | 2.78e-17 | 1.82e-12 | 7.28e-12 |

Each listed solve used **1 iteration**. The independent equal-branch intersection gives `Q=sqrt((60000·0.9²)/(2e11+2e12/4+1e11))=0.000246475150877 m³/s`, matching the third row. In the unequal case the higher-resistance branch gets less flow, the other branch gets more, and the pump/network intersection moves. The test suite additionally uses a 1.5× restriction. A constructed 100 W electrical reference splits into 60 W hydraulic, 10 W VFD, 20 W motor and 10 W internal losses; 80 W reaches liquid after passive hydraulic dissipation and selected drive losses, 20 W reaches ambient. With zero speed/flow, only the explicit standby parameter can consume power. The full-loop 2-branch 5 s case has 97.049591 J pump electrical and 52.406779 J pump hydraulic; 78.610168 J is deposited in liquid, 18.439422 J in ambient. All passive-edge `ΔP·Q` sums equal pump hydraulic power.

## Raw transport, HX and FWS results

One-cell fixture: volume `0.001 m³`, mass `1 kg`, initial `300 K / 0 J/kg`, inlet `310 K / 40000 J/kg`, `m_dot=0.2 kg/s`, residence `5 s`, duration `5 s`. Outlet denotes the mixed cell/outflow at the end of the run; stored change uses the 300 K enthalpy reference.

| dt s | Outlet K | Outlet h J/kg | Stored change J | Analytic K | Absolute error K |
|---:|---:|---:|---:|---:|---:|
| 0.20 | 306.248832 | 24995.327910 | 24995.327910 | 306.321206 | 0.072374 |
| 0.10 | 306.284721 | 25138.884715 | 25138.884715 | 306.321206 | 0.036484 |
| 0.05 | 306.302888 | 25211.551507 | 25211.551507 | 306.321206 | 0.018318 |

HX equal-capacity analytic reference: `UA=100 W/K`, primary/secondary flow each `0.2 kg/s`, `Cp=4000 J/(kg·K)`, secondary inlet `320 K`, primary inlet `300 K`, `NTU=0.125`, effectiveness `1/9=0.111111111`, secondary outlet `317.777778 K`, primary outlet `302.222222 K`, heat `1777.777778 W` out of secondary and into primary. The independent counterflow and parallel unequal-capacity formulas, rated-capacity rejection and zero-flow result are tested. Primary and secondary masses never mix.

At 10 s in the two-branch fixture, a disturbance is applied at 5 s:

| FWS condition | CDU supply K | Final HX secondary export W |
|---|---:|---:|
| Baseline, inlet 290 K / flow 0.4 kg/s | 299.373197 | 866.211253 |
| Inlet 290→294 K | 299.539719 | 511.945589 |
| Primary flow 0.4→0.28 kg/s | 299.377969 | 856.146091 |

The CDU does not jump to a new steady state: its 2 kg finite inventory changes gradually. Warmer FWS and reduced FWS flow reduce heat removal in this fixture. No primary-fluid inventory is added to the secondary mass ledger.

## Full-loop mass and energy ledgers

For the equal two-branch 5 s run at 0.2 s mesh, supply manifold **in** is 0.246475151 kg/s, branch **out** is 0.123237575 + 0.123237575 kg/s, residual 0. The same two branches enter the return manifold and its outlet is 0.246475151 kg/s, residual 0. Every fluid volume has the same summed incoming/outgoing mass at steady hydraulic flow; no cell mass changes. Across all four 0.2/0.1/0.05 s qualification scenarios, maximum single-step hydraulic-node or volume mass residual is **2.78e-17 kg/s**. Signed and absolute cumulative mass audits both pass their declared `1e-9 kg + 1e-8·incident mass` tolerance.

The full-loop energy equation is `ΔE = E_IT + E_pump_to_liquid − E_air − E_HX`; pump electrical consumption is separately reported, not added in full a second time. Values below are the two-branch 5 s run at dt 0.2 s:

| IT J | Pump electrical J | Pump hydraulic J | Pump to liquid J | Air J | HX export J | Stored change J | Signed residual J | Sum abs step residual J |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1200.000000 | 97.049591 | 52.406779 | 78.610168 | 1.293080 | 4510.801204 | -3233.484115 | -2.81e-10 | 3.62e-9 |

The maximum signed full-loop residual magnitude among the twelve qualified runs is **4.18e-9 J**; maximum sum of absolute step residuals is **2.24e-8 J**; maximum per-step node energy residual is **2.38e-10 J**. Maximum single-step residual rate is **1.31e-8 W**. Per-node, per-step, cumulative signed and cumulative absolute energy checks pass. The negative stored change is physical for this deliberately cold FWS transient: heat export exceeds IT plus pump heat over the initial 5 s; it is not an energy-balance violation.

## dt refinement and validity

All four scenarios use **identical topology, initial state, speed, source trace and FWS events** across real 0.2/0.1/0.05 s meshes (25/50/100 steps in 5 s). The last row contains a 2 s IT source plus FWS inlet step. The maximum trajectory, enthalpy, branch/total flow, ΔP, HX energy, stored energy and pump electrical/hydraulic energy differences are evaluated by the harness, not just endpoint comparison. Declared generic acceptance uses 0.1 K peak/node, 400 J/kg enthalpy, 1% of declared map ranges for flow/pressure, and max(1 J, 1% finest energy) for energy measures. These are fixture criteria, not OEM tolerances.

| Scenario | Peak K at dt .2/.1/.05 | Adjacent peak error K (.2→.1 / .1→.05) | Adjacent max node error K | Adjacent HX J | Adjacent stored J | Max mass kg/s | Energy + mass gate |
|---|---|---|---|---|---|---:|---|
| 1 branch | 302.387751 / 302.395109 / 302.398820 | .007358 / .003711 | .007451 / .003735 | 1.6130 / .8122 | 1.5859 / .7987 | 0 | PASS |
| 2 branches | 302.387748 / 302.395106 / 302.398817 | .007358 / .003711 | .007452 / .003735 | 1.3221 / .6676 | 1.2678 / .6406 | 0 | PASS |
| 4 branches | 302.387746 / 302.395104 / 302.398816 | .007358 / .003711 | .007452 / .003735 | 1.0701 / .5412 | .9615 / .4871 | 2.78e-17 | PASS |
| Source + FWS event | 301.762516 / 301.768651 / 301.771750 | .006135 / .003099 | .006217 / .003120 | .9042 / .4563 | .8721 / .4404 | 0 | PASS |

All adjacent temperature, enthalpy, HX and storage errors decrease toward the finer reference. Flow, branch flow, pressure and pump energies have zero mesh error here because the hydraulic map and held speed are static within intervals; the independent analytic operating-point comparison establishes their value. The separate one-cell transport errors above also decrease against an exact continuous reference. A 0.025 s fourth-mesh check confirms CDU endpoint error decreases for 1/2/4 branches. The harness rejects three nominal dt values if events make their *effective* meshes identical (`NOT_EVALUABLE`).

Invalid-domain tests cover bath/advection, FIFO/finite-volume, pump work duplicate, invalid/zero/negative resistance, out-of-range pump speed/flow, negative pump map, unsupported reverse advection, unbalanced cell mass, duplicate storage owner/flux, missing endpoints, HX capacity/flow, primary/secondary identity and transactional failed steps. There is no clipping or fabricated fallback solution. Unsupported pressure/FWS/thermal operating domains are rejected under the declared generic ranges; this is not validation of real hardware limits.

## Regression, gate, and limitations

| Gate item | Evidence | Result |
|---|---|---|
| Phase 3 frozen thermal behavior | 100 Phase 3 tests, Phase 3 bath runs independently | PASS |
| V0.1 baseline | 72 legacy tests; no legacy source/config/test edits | PASS |
| Bath mutual exclusion; FIFO/pump heat uniqueness | Constructor/preflight negative tests | PASS |
| Finite volume, residence, analytic/reference, reversal | 6 coolant test cases plus three real meshes | PASS |
| Graph, parallel pressure, operating point, energy | 10 hydraulic test cases; raw table and independent equation | PASS |
| Finite CDU/HX, FWS, primary isolation | 5 HX/FWS cases; analytic ε-NTU and disturbance table | PASS |
| Mass/energy, dt, invalid-domain | 14 coupled-plant cases plus node/loop ledgers | PASS |
| Provenance | All fixture physical parameters unvalidated; no GB300 official designation | PASS |

Test totals: **35 Phase 4**, **100 Phase 3**, **72 V0.1**. The generic graph formulation is intentionally a single pump, common supply/return manifolds and quadratic path resistance. It is not a universal hydraulic graph solver. Fluid properties are constant, no viscosity/temperature feedback, compressibility, cavitation, two-phase behavior, water hammer, FWS inventory, HX wall capacity, valve dynamics, or actuator transients. An all-off pump can be audited by the pump component, but a powered IT coldplate loop with zero flow is rejected by the coldplate model rather than assigned a fake cooling coefficient. These are explicit model limitations, not silently satisfied GB300 requirements. There are **no known failing numerical gate items** for the declared generic fixture; real-machine qualification is blocked by missing data.

## 24-point self-review

1. Physical topology contains `R_test_bath`? **No.**
2. Bath plus advection allowed? **No, CONFIG_INVALID.**
3. Local coolant storage duplicated? **No.**
4. Fixed FIFO applied with finite volumes? **No, CONFIG_INVALID.**
5. Each advective edge has one donor/receiver posting? **Yes.**
6. Zero-flow inventory erased? **No.**
7. Residence time flow-dependent? **Yes.**
8. Reversal changes enthalpy donor or rejects unsupported reversal? **Yes.**
9. Parallel branches share actual pressure endpoints? **Yes.**
10. Branch flow post-normalized? **No.**
11. Pump operating point solved at intersection? **Yes.**
12. Commanded pressure used as physical pressure? **No.**
13. Electrical/hydraulic/pump heat double counted? **No.**
14. Hydraulic dissipation posted twice? **No.**
15. CDU has finite thermal inventory? **Yes.**
16. HX limited by both flows and UA? **Yes.**
17. FWS treated as infinite cold bath? **No; finite flow/capacity and declared inlet temperature.**
18. Primary/secondary mass mixed? **No.**
19. Secondary mass ledger closed? **Yes, max 2.78e-17 kg/s.**
20. Full-loop energy ledger closed? **Yes, max signed 4.18e-9 J.**
21. dt refinement tends to reference? **Yes.**
22. Generic value claimed as true GB300 parameter? **No.**
23. Phase 3 standalone thermal behavior damaged? **No; 100 tests pass.**
24. V0.1 baseline modified? **No; 72 tests pass and legacy tree unchanged.**

## OEM / GB300 data still required

Every item remains **CALIBRATION_REQUIRED** before physical comparison: pump H–Q–speed–efficiency map, VFD/motor efficiency, loss destinations, minimum speed and dynamic behavior; pipe dimensions, branch K, connectors/coldplate ΔP, manifold geometry and actual liquid volumes; CDU secondary inventory, HX UA map/rated capacity, valve Cv and primary pressure/flow limits; FWS inlet temperature range, flow range, available pressure and disturbance envelope; actual fluid formulation, density, Cp, viscosity, conductivity and enthalpy relation. No current generic numerical value should be quoted as OEM data.

**PHASE4_GATE_STATUS = PASS (generic numerical implementation only). STOP for user review; do not enter Phase 5, 6 or 7.**
