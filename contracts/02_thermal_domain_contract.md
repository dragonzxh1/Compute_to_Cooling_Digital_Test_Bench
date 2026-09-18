Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 02 — Thermal Domain Contract

## Inputs / Outputs

Input: disjoint leaf source map from 01, thermal topology, valid material/geometry parameters, initial energy state, boundary temperatures and local flows.
Output: ThermalNode energies/temperatures, signed interface exchanges and source receipts for integrator/auditor.

ThermalDomain groups nodes without adding energy. ThermalNode required:
node_id, entity_id, node_type, thermal_capacitance (J/K or enthalpy law), temperature_state (K, TRUE), heat_source_mapping (leaf IDs), connections (interface IDs), boundary_type (DYNAMIC / PRESCRIBED_T), source (ParameterRecord reference), confidence, calibration_status.
Additional: energy_state_j, reference_temperature_k, storage_owner_id, fluid mass if coolant, valid_temperature_range. Supported types: GPU_DIE, GPU_PACKAGE, HBM, VRM_BOARD, CPU_DIE, CPU_PACKAGE, COLD_PLATE, LOCAL_COOLANT, RACK_AIR.

## Mapping / invariants

ElectricalPowerDomain != ThermalDomain. For every electrical leaf, injection weights over thermal nodes sum to 1 within 1e-12; default one leaf->one node, explicit distributed heat source allowed without duplicating watts. No parent board injection alongside its children. GPU die gets allocated/independently measured DIE power, not raw BOARD_POWER. Mapping is immutable within PERFORMANCE.

Every dynamic node C>0 and finite; E(T)=integral C(T)dT from common reference. Constant C uses C×(T−T_ref), not arbitrary inconsistent absolute stored energy. Prescribed boundary has no integrated storage; its reaction heat must enter external ledger. Zero-capacity algebraic connectors have no node storage and must be modeled as links, not divide by zero.

dE_i/dt=P_i + sum incoming interface heat − sum outgoing. Internal link heat is computed once, equal/opposite on endpoints. Node and domain rollups are alternative aggregates, not additional energy terms. Semiconductor-to-package, TIM, plate and coolant storages remain separate owners; do not include plate mass twice in a rack lump.

## Failure / fallback

Invalid C, duplicate injection, orphan energized node without declared adiabatic condition, invalid link endpoints or temperatures outside material validity -> CONFIG_INVALID / MODEL_INVALID; plant scoring stops. Adiabatic storage is allowed explicitly and may heat until physical model valid range exceeded; no temperature clipping to a safety limit. Measured temperature failure belongs to telemetry, not plant energy.

## Acceptance specifications

TD-01: board example from architecture injects 900/180/120 into distinct appropriate nodes, never1200+180+120.
TD-02: insulated single node with constant P changes energy by P×duration.
TD-03: no sources/boundary losses -> sum energy conserved despite redistribution.
TD-04: each source has one receipt; deliberately duplicate HBM fails preflight.
TD-05: vary air resistance: heat split changes without electrical input change.

