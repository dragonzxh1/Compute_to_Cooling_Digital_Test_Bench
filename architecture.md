# C2C-DTB V0.2 Architecture & Engineering Specification

Revision: 1.1
Date: 2026-09-18
Status: FROZEN PHASE 2 DESIGN — pending user review; no PHASE 3 implementation
Authority: approved V0.2_REFACTOR_PLAN Revision 1 plus PHASE 2 user task. This document and the 16 contracts form one normative set. Existing docs/architecture.md is legacy and is not overwritten.

## 1. System Boundary / ownership

V0.1 remains a GB300 Load-to-Cooling Feedforward Control Proof-of-Concept. V0.2 targets a GB300 Rack Liquid Cooling Physical + Control Digital Twin, initially Generic / CALIBRATION_REQUIRED. No vendor-calibrated GB300 performance or real-site safety is claimed.

| Owner | Responsibility / outputs | Cannot do |
|---|---|---|
| Scenario / Replay injector | offered electrical domain trace, hidden FWS/K events; isolated simulation inputs | provide future trace to controller |
| Physical Plant | allocated electrical sources, RC storage, fixed-volume coolant, hydraulic network, finite CDU/HX; TRUE state | read controller estimates as physical truth |
| Measurement System | sample/filter/noise/bias/delay/drop/quality; immutable MEASURED records | mutate plant or rejuvenate stale samples |
| Estimator | causal measured IT allocation and thermal demand; ESTIMATED state with uncertainty | use true temperatures or unarrived samples |
| Feedforward Controller | measured-disturbance cooling intent | predict future workload, actuate directly |
| Feedback Controller | measured thermal/flow/pressure corrections | use auditor truth |
| Intent Supervisor | unit-compatible composition, mode selection and feasibility rejection/clamp | override safety or change IT input |
| Safety Supervisor | independent measured/hardware-protection state machine; limits/derate request | read unmodeled perfect sensors |
| PLC | final local feedback, interlocks and accepted actuator command; independent watchdog | stop merely because FF fails |
| Actuator | delayed/ramped command-to-actual transition | instantly equate requested and actual |
| Metrics / Auditor | all layers, conservation/fairness/KPI and event ledger, read-only | feed truth or tuning hints into active controller |

No executable interfaces are created in this phase. All types below are normative language-neutral schemas. Future implementation resides in independently packaged v0_2/, never src/c2c; baseline manifest is the regression authority. No branch is necessary for these root document additions; a future implementation branch follows explicit user authorization.

## 2. Boundaries

| Boundary | Included / exchanges | Exclusions / required contract |
|---|---|---|
| Electrical Power Boundary | measured parent domains, nonoverlapping leaf allocation, immutable offered/delivered power | board != die; never sum parent plus contained child; 01 |
| Thermal Boundary | die/package/HBM/VRM/plate/coolant/optional rack air energy nodes, signed interface heat | no pre-split GPU liquid fraction; 02,03 |
| Hydraulic Boundary | closed secondary network, pump pressure rise, series elements/shared parallel pressure nodes | primary water not mixed into secondary; 13 |
| CDU Boundary | secondary pump and volume, HX, primary valve/flow, inlet/outlet ports | no infinite heat removal; 04,05,12 |
| FWS Boundary | independent primary inlet T, finite flow/pressure availability and capacity; outlet enthalpy | plant-only hidden schedule; no prediction handed to FF |
| Telemetry Boundary | four adapters, source time and availability, quality and coverage | scrape is not a new sample; 06,07 |
| Control Boundary | IT measured FF, measured-state outer FB, supervisor, local PLC | no true-state access; 14 |
| Safety Boundary | measured/local hardware channel, latched faults, derate request/ack | no assumed N+1, no performance load mutation; 15 |
| Simulation Boundary | event-time causality, independent clocks, deterministic streams and finite integration | no wall-clock scheduling dependency; 11 |
| Benchmark Boundary | immutable PERFORMANCE vs separate SAFETY_PROTECTION, A/B/C | no mixing curtailed-energy runs into efficiency ranking; 08–10,16 |
| Calibration Boundary | offline fits, train/holdout, candidate approval, validity range | no automatic live overwrite or validation promotion |
| Source / Provenance Boundary | parameter/source/version/hash/uncertainty registry | assumption is not official specification |
| Failure / Fallback Boundary | typed invalidity, FF withdrawal, local PLC and capacity-limited mode | no numeric clipping of true physics into safe range |

## 3. Data and control flow

```text
Scenario/Replay -> offered domain power -> allocation -> delivered leaf power -> Plant TRUE
                                              ^                                 |
                      safety load gate (SAFETY_PROTECTION only)                 v
IT measurement pipeline <----- source sampling              liquid/device sensors
          |                                                        |
measured IT -> causal estimator -> FF intent      measured T/flow/dP -> outer FB
                                    \               /
                                   Intent Supervisor
                                           |
measured/hardware protection -> Safety -> PLC final execution -> Actuator -> Plant
All layers -------------------------------------> Auditor (no return path)
```

Plant receives source-domain true power and a frozen allocation mapping independent of controller outputs in PERFORMANCE. Estimator uses a separate instance of that mapping on arrived measurements; its result cannot overwrite plant inputs. Calibration version may be shared, mutable state may not.

Measured-Disturbance Feedforward responds to already-changed electrical power before temperature has fully responded; advance over liquid sensing depends on actual delay and actuator dynamics and is not guaranteed. Predictive FF/ML/future jobs belong to V0.3 and are excluded.

Actuator feedback path: Actual Actuator -> Measurement Pipeline -> Measured Actuator / Equipment Status -> PLC / Safety (optional registered Outer FB). Pump speed, valve position, VFD/fault/ready signals and acknowledgments obey06 availability/quality. PLC/Safety never directly read raw ACTUAL. Contract14 defines legal measured-feedback tracking, anti-windup and command-age bookkeeping; Commanded, Actual and Measured remain separate.

## 4. Board Power Allocation Example (structural, not GB300 data)

Measured board = 1200 W; no separate die/HBM/VRM measurements.
BoardPowerAllocator uses f_die=0.75, f_HBM=0.15, f_other=0.10 solely as ENGINEERING_ASSUMPTION / CALIBRATION_REQUIRED illustrative fractions.
Output: die ESTIMATE=900 W, HBM ESTIMATE=180 W, VRM/board ESTIMATE=120 W; total=1200 W.
These fractions partition electrical subcomponents, NOT liquid/air heat. Each output is ALLOCATED_FROM_PARENT, never MEASURED_DIRECT die power. Numeric fractions are not default GB300 parameters.

If HBM=200 W is independently measured and included_in=board, board remains 1200 W: HBM receives 200 W and the residual 1000 W is allocated between die and board-other. If using the same residual ratio 0.75:0.10, outputs are approximately 882.352941 and 117.647059 W. Sum is 1200, not 1400 W. Simultaneous time windows and boundary coverage are required; inconsistent child measurements cause POWER_DOMAIN_BALANCE_FAIL, not a negative residual silently clipped to zero. See contracts 01/02.

## 5. Physical architecture (interfaces only)

### Thermal / Cooling

Allocated die power -> Die -> Package -> TIM -> Coldplate Solid -> Rcp(local flow) -> Local Bulk Coolant; separate HBM/VRM/CPU nodes receive their own source once. Generic Rcp endpoints are coldplate solid to local bulk coolant and exclude die/package/TIM; coolant inlet temperature is a separate boundary. TIM can be a resistance interface without added storage. Explicit positive-conductance links may connect package/board to air. Storage and signed heat links determine the liquid/air split. Capture ratio is a steady/calibration metric or explicitly separate generic residual-domain approximation, not core thermal physics. Full-node power does not mean full-board power at the die.

Manufacturer imported Rth must declare measurement endpoints, temperature meanings and included/excluded physical layer IDs. Each resistance layer instance has one owner. Composite device-to-coolant representation and detailed network are mutually exclusive on the same path; overlapping TIM/package/plate layers produce IMPORT_CONFLICT / THERMAL_RESISTANCE_OVERLAP -> CONFIG_INVALID. Contract04 also requires valid source/storage mapping when selecting a reduced composite path.

Coldplate local flow controls Rth/UA with conduction lower bound and explicit valid domain. Plate solid and local coolant each have one storage owner; coldplate constitutive interface returns exchange, not a second independent integration of those states. Flow=0 uses a qualified finite no-flow model or terminates physical validity, never fake flow. See 02–04,11.

### Hydraulic Architecture

```text
CDU secondary pump -> supply pipe -> supply manifold pressure node
                  -> parallel branches [pipe / valve / connector / coldplates / restriction]
                  -> return manifold pressure node -> return pipe -> CDU secondary volume/HX
```

Each edge has signed mass flow and pressure drop; each branch pressure drop is sum of series elements and shares endpoint pressures. All node balances must close. Pump operating point solves pump curve vs system curve; PHASE 4 owns implementation. Affinity transforms Q~N, head~N², shaft power~N³ apply only within qualified map similarity assumptions, not as a constant electrical efficiency law. Fluid density is fixed reference per incompressible experiment; Cp/μ/k may depend on T within qualified models. Thermal expansion/free surfaces/compressibility are out of scope.

### FWS/CDU Architecture

Secondary liquid never mixes with primary/FWS. HX port heat has equal/opposite energy transfers; finite epsilon-NTU with declared arrangement, UA(T,flow) validity, C_min and optional rated capacity bounds. Zero-side-flow needs a defined storage/no-transfer limit, not division by zero. Primary valve sets flow subject to available pressure/flow and actuator limits; inlet temperature alone is not cooling capacity. FWS 20→24°C and flow 100→70% and branch K×1.5 are scenario schedules visible only to plant. These are generic disturbance definitions, not vendor operating claims.

Secondary-only Full Loop CV includes secondary inventory, rack nodes, pipe/CDU storage, HX secondary side; excludes primary inventory/electrical pump drive. Heat to primary is external. Optional combined primary+secondary audit counts HX internally and FWS inlet/outlet externally instead, never both (12).

## 6. Control and thermal objectives

Default research control quantity is ΔP target in Pa:
requested = base + FF increment + outer-FB correction.
Alternative flow-target mode is exclusive, never two independent pump loops. Supply-T target has a separately unit-safe channel. Feedback uses measured GPU/coolant T, flow and ΔP; local PLC tracks pressure (or flow) and supply T with independently frozen gains. Supervisor records requested/accepted and reason; PLC records commanded; actuator records actual. Safety restrictions take priority over FF/FB.

Constrained objective: satisfy thermal limits/headroom, flow/pressure, CDU and actuator constraints; minimize pump electrical energy/control effort/unnecessary overcooling; increase safe supply T where feasible. Required limits, dewpoint margin, fallback targets and actuator values must be a complete provenance-bearing profile before any experiment runs; absent actual GB300 limits remain unknown, never guessed.

Headroom_i=limit_i−T_i. Excess_i=max(Headroom_i−RequiredHeadroom_i,0); integral of weighted excess has units K·s, weights fixed and sum to one. It is not itself an electrical waste measurement. Energy and thermal matched benchmarks and Pareto classification govern conclusions (09/10). No claim of PUE without a complete facility electrical boundary.

Thermal hierarchy: T_control_target < thermal_derate_threshold < thermal_hard_protection_threshold. Headroom limit_i / benchmark thermal_limit_i means thermal_operating_limit only. RequiredHeadroom may define T_control_target=thermal_operating_limit−RequiredHeadroom, but cannot change protection thresholds. Safety15 uses separate derate/hard triggers, independent derate_clear_threshold/hard_clear_threshold and a cause-specific PROTECTED/FAULT action table, all required with provenance and CALIBRATION_REQUIRED until supported by reviewed evidence. No GB300 numerical thresholds are supplied. Hard protection remains subject to PERFORMANCE immutable IT trace: suppressed shutdown requests are logged; actual cooling actions still apply.

## 7. Simulation Scheduler Contract

Use integer nanosecond event times. All input periods/delays must be representable as integer ns or CONFIG_INVALID; no int(period/dt) truncation. Five independent settings: physics_dt, telemetry_dt (per sensor possible), controller_dt, PLC_dt, actuator_dt. Schema requires positive periods, nonnegative delays. Generic scheduler test profile: 0.1, 0.5, 0.5, 0.2, 0.2 seconds respectively, all ENGINEERING_ASSUMPTION (not hardware timings). Equal values do not couple clocks.

At t=0 initialize source, state, actual actuators, then stages 2–8 below (no negative-time history without explicit prehistory).
For each next event or physics deadline t:

1. Advance plant and continuous actuator state from preceding t to t using already effective held inputs; split at source/FWS/K discontinuities. Account interval [previous,t).
2. Apply due scenario source/boundary changes at t for [t,next). Thermal state is continuous; algebraic hydraulic changes re-evaluate consistently at this boundary. No impulse heat from a boundary step.
3. Generate due measurements, taking post-source-change electrical sample and continuous thermal state; each sensor uses its own sample index.
4. Release due communication packets, then due processing-availability events. Newly sampled zero-delay packets are released in this stage, before controllers.
5. Update Safety from available measured/hardware channels (every event instant with new protection information); run due estimator/FF/outer FB using immutable snapshots; supervisor composes intents. Safety immediate trip can schedule an emergency PLC/actuator event at this t. Normal controller deadlines do not force normal PLC/actuator ticks.
6. Run due PLC with latest accepted intent and safety restriction; safety overrides normal output at the same t. Earlier PLC values remain held if not due.
7. At due actuator events (or modeled emergency trip), enqueue commands with declared latency. Zero-latency command becomes target at t but does not cause a speed jump where lag/ramp applies. Existing due commands are ordered by sequence; newest valid sequence wins, safety restriction dominates. No algebraic controller rerun in the same tick.
8. Apply effective targets to next interval, append audit/events. Hardware protection latency is modeled explicitly; simulated software priority does not imply instantaneous real hardware safety.

Within a stage stable order is (timestamp, priority, entity_id, sequence_id). Sensor/command event loops must be finite; negative latency or events scheduled into past fail. Scheduler advances to minimum independent deadline; irregular phases are handled without shifting clocks. Source values piecewise constant right-continuous; step metrics identify left/right convention. Replay availability times, not access to file contents, constrain controller visibility. Auditor may see the full replay but cannot feed back.

Convergence tests fix all nonphysics clocks and source/noise indices. If event subdivision makes all three actual meshes identical, test is NOT_EVALUABLE, not a convergence PASS: add an open-loop fixture with coarser events and refine the actual closed-loop substeps as needed (11). Independent periods must never be stretched to make a method pass.

## 8. Parameter Provenance Schema / calibration

ParameterRecord required: name (unique), value (typed finite or explicit unknown), unit (SI-compatible), source_type, source_ref, confidence (0..1 evidence confidence, not probability of safety), date (ISO8601), valid_range (bounds/domain), calibration_status.
source_type = OFFICIAL / DATASHEET / LITERATURE / ENGINEERING_ASSUMPTION / MEASURED / CALIBRATED.
calibration_status = UNVALIDATED / CALIBRATION_REQUIRED / CALIBRATED / VALIDATED.
Additional: version, dataset_hash, entity scope, test_conditions, uncertainty, approved_by, approved_at.
Unknown mandatory runtime parameter blocks profile validation; architecture can be frozen without supplying OEM constants. Every nonhardware design tolerance in contracts is an ENGINEERING_ASSUMPTION numerical/test policy, not an official limit.

Calibration interface consumes timestamped data+conditions+uncertainty, emits candidate parameters/bounds/fit and holdout residuals/version. Only explicit review promotes CALIBRATED; independent holdout evidence and recorded approval promote VALIDATED for the specified domain. Unit tests never promote provenance. Generic values remain labeled; actual R/C/limits/topology/pump curves absent, so no equipment profile is declared usable.

## 9. Shared schema and validation conventions

All IDs nonempty and unique in scope; references resolve. All numeric values finite with explicit units; NaN/Inf rejected except telemetry raw invalid samples retained outside numeric validated payload. Times are int ns in declared monotonic simulation epoch; source UTC mapping and uncertainty retained. Null means unavailable, never zero. Configuration is immutable within a run, except named scenario boundary events and predeclared safety actuation.

Common ControlIntent: id, issuer, created_time, expires_time, target_kind (DP_PA/FLOW_KG_S/SUPPLY_T_K), value, increment_or_absolute, provenance, quality, sequence_id. FF values are increments; base/FB units must match. ActuatorCommand: id, actuator_id, created_time, effective_time, target, unit, originating_intent_id, safety_state, reason, sequence_id. Inputs/outputs are read-only snapshots. SolverStatus = CONVERGED / RETRYABLE / FAILED; ValidityStatus = VALID / MODEL_OUT_OF_RANGE / MODEL_INVALID / CONFIG_INVALID. Nonvalid results cannot masquerade as successful physical samples.

Contracts carry Inputs/Outputs, invariants, failure policy and acceptance specifications. These are future tests, not implemented code. Common physical-run invalidity stops scoring and marks INVALID; safety policy may proceed only when plant physics remains valid. Estimator invalidity disables FF while valid plant and local PLC continue.

## 10. Contract index / freeze rules

| # | Normative document |
|---|---|
| 01 | [Power Domain](contracts/01_power_domain_contract.md) |
| 02 | [Thermal Domain](contracts/02_thermal_domain_contract.md) |
| 03 | [Cooling Path](contracts/03_cooling_path_contract.md) |
| 04 | [Coldplate](contracts/04_coldplate_contract.md) |
| 05 | [Pump Energy](contracts/05_pump_energy_contract.md) |
| 06 | [Telemetry](contracts/06_telemetry_contract.md) |
| 07 | [State Separation](contracts/07_state_separation_contract.md) |
| 08 | [Experiment](contracts/08_experiment_contract.md) |
| 09 | [Thermal Matched](contracts/09_thermal_matched_contract.md) |
| 10 | [Energy Matched](contracts/10_energy_matched_contract.md) |
| 11 | [Numerical Integrator](contracts/11_numerical_integrator_contract.md) |
| 12 | [Energy CV](contracts/12_energy_control_volume_contract.md) |
| 13 | [Mass CV](contracts/13_mass_control_volume_contract.md) |
| 14 | [Control Permissions](contracts/14_control_input_permission_contract.md) |
| 15 | [Safety Supervisor](contracts/15_safety_supervisor_contract.md) |
| 16 | [Fair Comparison](contracts/16_fair_comparison_contract.md) |

Architecture and contracts04/14/15 are revision1.1; the other13 contracts remain1.0. Change one normative boundary requires revision, affected-contract review, fresh content hashes and invalidation of incompatible experiment registration. No silent defaults, result-driven tolerance relaxation or migration of old outputs to new rules. PHASE2_REVIEW_SUMMARY.md records SHA-256 freeze fingerprints for architecture, contracts and baseline manifest.

Revision1.1 (2026-09-18): synchronized coldplate endpoint/layer ownership, measured actuator feedback path and thermal protection hierarchy only. State contract07 already permits MeasurementTransform of ACTUAL; no related contract wording changes required. Existing numerical/matching policies retained.

PHASE 2 gate checks definition completeness only, not physics implementation. Future phases: PHASE 3 thermal, PHASE 4 hydraulic/CDU, PHASE 5 PLC, PHASE 6 FF, PHASE 7 telemetry, PHASE 8 benchmark, PHASE 9 reports. Current STOP applies even if gate PASS; no PHASE 3 without user review.
