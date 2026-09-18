Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 03 — Cooling Path Contract

## Inputs / Outputs

Input: ThermalNodes, explicit interfaces and external temperature/enthalpy boundaries.
CoolingPath fields: path_id, originating_thermal_domain, cooling_path (LIQUID / AIR / MIXED), ordered interface_ids, endpoint_cv, constitutive_model_ref, validity/provenance.
Output: signed heat flow and interval energy per interface; liquid/air rollups and capture metrics.

## Invariants

GPU die -> package/TIM -> cold plate -> local coolant; CPU analogous. HBM/VRM/board paths reflect declared geometry, not inferred from device count. Explicit parallel package/board->air link may coexist. MIXED injects power once into node; resistance network determines resulting split. Never preallocate 70/30 liquid/air and simultaneously integrate that full-power network.

Each interface ID has one owner, two endpoints (or one external reservoir). ThermalResistance>0 or qualified constitutive law; Q=(T_a−T_b)/R is signed and may reverse. A prescribed ambient temperature denotes an external reservoir; a dynamic rack-air node remains internal until its external outlet/convection boundary. Do not count package->rack air and rack-air->room twice as external loss of same CV.

Liquid Capture Ratio is reporting/calibration: stable-window integral liquid export / electrical input with stated storage correction and boundary. Zero input -> N/A; transient release may exceed one or reverse, never clip. Optional Generic approximation permitted only on explicitly separate residual noncore domains without an overlapping physical network; qualify as approximation and conserve complementary air/liquid allocation. It cannot replace core GPU/CPU network.

## Failure / fallback

Missing liquid endpoint, duplicate heat interface, zero/negative R without qualified ideal-link handling, or unknown cooling topology -> configuration fails. Plant cannot invent liquid cooling for missing hardware. Estimator topology failure disables FF; valid local PLC remains active. Disconnected adiabatic nodes must be declared as such.

## Acceptance specifications

CPATH-01: mixed node heat/storage/electrical balance closes.
CPATH-02: same electrical power, different air/liquid R -> different computed capture ratio.
CPATH-03: exchange sign reverses with reversed gradient, sum cancels internally.
CPATH-04: selecting both generic fixed split and full network for same source is rejected.

