Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 13 — Mass Control Volume Contract

## Inputs / Outputs

Input: directed hydraulic graph (pressure nodes and edge connectivity), branch/pipe/manifold/CDU secondary volume inventories, reference density, signed mass flows and boundaries.
Output: node/volume continuity residuals in kg/s and interval/cumulative kg, flow_solution validity, branch totals; no implemented solver.
Volume fields: volume_id, volume_m3>0, rho_ref_kg_m3>0, stored_mass_kg=rho_ref×volume, inlet/outlet interface IDs, pressure_node refs, coolant_ref/provenance.

## Invariants

dM/dt=Σm_in−Σm_out. This version uses fixed incompressible inventories, so accepted dM/dt=0. Every branch, manifold with storage, pipe segment and CDU secondary volume must balance. Zero-storage pressure junction has continuity only, no energy/mass inventory.
Parallel branches share upstream/downstream pressure nodes; sum signed branch mass flows = total. For same reference density, Qsum also closes. Different fluid loops use their own density, never share a mass junction. Primary and secondary exchange heat only.
Each resistance edge pressure drop sums along branch; pump operating point and continuity solved together in PHASE 4. No post-solve scaling of branch flows to conceal solver errors without solving pressure consistency.
Changing flow changes residence time M/abs(m_dot) (undefined/infinite residence at0 only as diagnostic), not stored mass. No variable FIFO queue that creates/destroys inventory. Reverse flow uses actual donor enthalpy; unsupported reversal is MODEL_INVALID, not unsigned-flow substitution.
Temperature-dependent viscosity/Cp allowed; reference density remains fixed for continuity/storage under incompressible approximation. Thermal expansion/leaks/fill/drain/cavitation/two-phase flow require separate revised physics; a “leak” cannot be simulated by silently shrinking stock.

## Frozen tolerance

Node instantaneous abs(residual)<=1e-9kg/s+1e-8×sum(abs(incident mass flows)).
Volume interval abs(ΔM−integrated net mass)<=1e-9kg+1e-8×sum(abs(integrated incident mass)).
Cumulative signed and sum-absolute interval residual both checked against cumulative same-scale bound. Record worst node and full loop, not only total. Iterative solver tolerance must be at least this strict. These are numerical design tolerances, not sensor accuracy.

## Failure / acceptance specifications

MCV-01: equal/unequal branches satisfy common pressure endpoints and total continuity.
MCV-02: K_branch×1.5 redistributes flows from network solution; do not mandate constant total if operating point moves.
MCV-03: flow step leaves inventory unchanged; zero-flow volume retains finite energy/mass.
MCV-04: primary/secondary mass mixing or missing node balance fails preflight.
MCV-05: residual above threshold -> MASS_BALANCE_FAIL, invalid plant/scoring. Safety capacity shortage can be valid only if physical solution remains mass-conservative.

