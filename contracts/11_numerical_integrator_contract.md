Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 11 — Numerical Integrator Contract

## Inputs / Outputs

ThermalIntegrator.step(state,source,boundary,conductance,flow,t,dt):
inputs immutable node E/T, electrical W, boundary T/enthalpy, link conductance model, signed mass flow, integer-ns start/duration and validity/provenance.
outputs next_state, integrated_interface_energy (J by unique ID including advective transfers), energy_residual (J by CV), validity, solver_status, iterations, accepted_substeps, error diagnostics.
Only accepted interval results may commit state. Failed step leaves original state untouched. Contract does not implement numerical solving.

## Algorithm selection / ownership

Candidates: Explicit Euler (reference with RC positivity/stability and advection CFL checks); Conservative Backward Euler (default candidate for stiff RC, consistent implicit shared fluxes); Exact linear RC discretization (constant coefficient, piecewise-held source reference only).
PHASE 3 must verify before accepting default. Conservative means interface energy used by adjacent nodes is exactly one equal/opposite quantity, not separately recomputed estimates. Variable Cp uses enthalpy E(T), never C(T)×T.
Nonlinear backward Euler uses coupled residual solve; convergence requires max normalized state residual<=1 and energy gates below; max iterations25, max step halvings10, minimum dt1 microsecond. Failure beyond either bound -> FAILED/MODEL_INVALID, no silent Euler fallback. These are frozen numerical policies, not physical parameters. State residual scale=max(1e-6J,1e-9×max(abs(E_change),abs(interval_sources_and_fluxes))); zero reference energy cannot relax it. Constitutive validity checked on iterate and accepted state; no continued extrapolation.

## Frozen numerical gates (Generic policy, not calibration)

Per-step and accumulated energy residual: abs(r)<=1e-6J+1e-6×S, S=sum absolute EXTERNAL input/output energy for that CV plus abs(storage change). Accumulated S=sum interval S, accumulated residual is signed sum AND sum(abs(step residual)) must pass same accumulated bound. Also report max/P95 instantaneous-equivalent W; never divide by total IT minus water to infer numerical conservation. See12.
Power arithmetic tolerance from01/05 and mass from13 remain separate.

dt qualification: nominal physics_dt=0.2,0.1,0.05s, fixed other clocks/initial states/source/noise. Compare adjacent pairs and report0.2vs0.05; controller modes tested independently before gains compared.
Frozen maximum adjacent differences:

| Quantity | Tolerance |
|---|---|
| Peak T, minimum headroom | 0.1K each |
| Pump electrical energy | max(1J,0.01×abs(E_finer)) |
| Flow trajectory L-infinity | max(1e-9kg/s,0.01×flow_scale_kg_s) |
| ΔP trajectory L-infinity | max(1e-3Pa,0.01×dp_scale_pa) |
| Normalized actuator command | 0.01 fraction (=1 percentage point) |
| Requested/accepted ΔP or flow target | 1% of corresponding frozen scale |
| Supply-T target | 0.1K |
| Energy residual | each run passes per-step/cumulative energy rule above, no relaxation by dt |

flow_scale and dp_scale are strictly positive declared model qualification ranges (e.g. rated flow/pressure), fixed before runs with provenance; absence blocks execution, not filled from observed maximum. No actual GB300 scales invented.
Compare trajectories at shared physical t using specified dense output (linear within accepted thermal steps, held commands with right-side event convention); avoid numerical step-count averaging. Peak and constraints additionally evaluated at all solver accepted endpoints/events, not only shared coarse grid. Halve actual substeps if events otherwise make meshes equal. Require distinct effective meshes for qualification; nominal labels alone yield NOT_EVALUABLE, not PASS.

Fine pair difference must be <=coarse pair difference OR both <=10% of corresponding tolerance (numerical floor). Every required metric must pass, not a weighted average. Switching/time alignment diagnostics recorded; discontinuous control chattering is a convergence failure needing design review, not hidden by smoothing results. Final closed-loop PHASE 8 requalification required in addition to PHASE 3 open-loop.

## Failure / acceptance specifications

NUM-01: insulated constant-source node and linear RC exact reference checks.
NUM-02: failed nonlinear step leaves state/ledger unchanged; retries recorded with bounded termination.
NUM-03: conservative transfers close at device/rack/loop levels.
NUM-04: three dt profiles with fixed other clocks pass or FAIL explicitly; identical actual meshes do not count.
NUM-05: unknown scale/tolerance or result-driven tolerance change -> registration invalid.

