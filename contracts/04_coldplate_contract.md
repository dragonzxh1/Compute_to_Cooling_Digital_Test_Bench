Revision: 1.1
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 04 — Coldplate Contract

## Inputs / Outputs

ColdPlateModel.evaluate constitutive interface (not an implemented solver):
inputs: hot_endpoint_temperature_k, cold_endpoint_temperature_k, coolant_inlet_temperature_k (separate transport boundary), local_mass_flow_kg_s, coolant_properties, model_parameters, current solid/local coolant state where dynamic.
outputs: heat_transfer_w (signed hot->cold endpoint), endpoint_resistance_k_w, coolant_side_state (evaluated port/constitutive quantities, not a separately advanced duplicate inventory), validity_status, range_violations, model_version. Ambiguous device_side names are replaced by endpoint names in this revision.
ThermalIntegrator alone advances owned coldplate/local coolant storage (02/11); a steady submodel may return outlet enthalpy consistently with Q, but cannot replace dynamic storage without a declared mutually exclusive topology choice.

## Endpoint and resistance ownership

Required model metadata: thermal_hot_endpoint_id, thermal_cold_endpoint_id, hot_side_temperature_definition, cold_side_temperature_definition, rth_definition, included_layers, excluded_layers, manufacturer_rth_definition, manufacturer_measurement_hot_endpoint, manufacturer_measurement_cold_endpoint. Manufacturer fields are explicitly NOT_APPLICABLE for Generic models; imported models require supported definitions, never unspecified endpoints.

Generic default: Coldplate Solid -> R_cp(local flow) -> Local Bulk Coolant. Hot temperature is the declared representative plate-solid node temperature; cold temperature is the local well-mixed coolant cell temperature. Inlet temperature is not automatically this bulk temperature. A manufacturer inlet/mean/outlet reference cannot be substituted without an explicit validated endpoint conversion.

Upstream chain: GPU Die -> Package -> TIM -> Coldplate Solid. Generic R_cp excludes GPU die, package, TIM and their contact resistances. Its R_conduction covers only the unresolved plate-solid-to-wetted-surface conduction from the declared hot node, and 1/(hA) covers plate convection to the local bulk node. Neither may also exist as an independently active resistance for the same physical layer.

Every physical resistance layer instance has exactly one owner: key=(device/path instance, physical layer ID), e.g. DIE_PACKAGE, PACKAGE_TIM, TIM_CONTACT, PLATE_CONDUCTION, PLATE_CONVECTION. Included/excluded lists resolve these canonical instance IDs; independent devices may share layer type names, not ownership IDs. Preflight compares explicit interfaces and imported composite layers. Any overlap -> THERMAL_RESISTANCE_OVERLAP -> CONFIG_INVALID; missing/ambiguous ownership or endpoints also blocks running.

Manufacturer junction-to-coolant/device-to-coolant Rth is not coldplate-to-coolant Rth. Import requires original temperature measurement endpoints, rth_definition and complete included layers. An endpoint mismatch or overlap is IMPORT_CONFLICT. Select exactly one registered representation:

- Detailed network: import only a matching coldplate-specific curve with matching endpoints/layers; retain upstream interfaces.
- Composite manufacturer path: use the full lumped Rth at its declared endpoints and deactivate all duplicated internal resistance interfaces on that path. Register the corresponding reduced topology and source/storage mapping under02/12; do not leave orphaned powered or storage nodes. A steady lumped Rth does not establish a transient capacitance model. If a consistent reduced dynamic mapping is unavailable, import fails.

The two representations are mutually exclusive for that path. No silent subtraction of assumed TIM/package resistance from manufacturer data. Layer ownership and representation selection belong to the frozen topology/config already hashed by16.

## Model / valid domain

Generic h=h_ref×(abs(m_dot)/m_ref)^n; Rcp=R_conduction+1/(h×A).
h_ref>0, m_ref>0, A>0, R_conduction>0, 0<n<=1 for this generic family; parameters ENGINEERING_ASSUMPTION until calibrated. No actual GB300 numeric values supplied. Factory interpolation curves have priority only after endpoint/ownership preflight, preserving qualified monotonic behavior and uncertainty. R and 1/UA are interchangeable only for identical endpoints and included layers; never double add TIM.

Mandatory parameter profile: valid_flow_min/max (kg/s magnitude), valid_temperature_range (both ports), valid_coolant (formulation/concentration), valid_heat_load_range (W), flow_direction_support, test_conditions and uncertainty. Out-of-range -> MODEL_OUT_OF_RANGE with offending values; no silent extrapolation or post-hoc clamp of actual flow.

At zero flow: preselect ZERO_FLOW_VALID_MODEL (finite conduction/natural-convection link into stored coolant, named calibrated/generic submodel and valid range) or MODEL_INVALID. Default is MODEL_INVALID if no zero-flow submodel supplied. Do not evaluate the power law at zero, return infinite R/UA, or impose fictional minimum flow. Reverse flow allowed only by a declared validated/generic bidirectional law with correct upstream selection.

## Failure / fallback

Estimator coldplate estimate invalid -> FF_DISABLED. Plant coldplate invalid -> stop physical run, INVALID scoring; continue only via predeclared valid no-flow/subrange model, never label arbitrary continuation valid. Physical zero flow can be an expected safety fault while model must still be qualified to simulate its thermal aftermath.

## Acceptance specifications

CPL-01: at same conditions in domain, increased flow lowers thermal R toward positive conduction bound, never zero/infinite.
CPL-02: each range edge/just outside returns expected validity; coolant mismatch fails.
CPL-03: zero flow executes chosen explicit policy without divide-by-zero/fake mass flux.
CPL-04: plate/coolant integrated exchange is equal/opposite; same storage advanced once.
CPL-05: manufacturer Rth/UA/ΔP conditions and TIM endpoints preserved on import.
CPL-06: imported Rth includes TIM while an independent TIM interface is active on that path -> IMPORT_CONFLICT / THERMAL_RESISTANCE_OVERLAP, CONFIG_INVALID; must FAIL preflight.
CPL-07: Generic coldplate_solid -> local_bulk_coolant with uniquely owned plate layers and separate upstream TIM passes ownership preflight (not a claim of implemented test PASS).

## Revision log

2026-09-18, 1.1: explicit endpoints and temperature meanings; manufacturer import representations; per-instance resistance ownership; CPL-06/07. Existing flow/validity/zero-flow policies retained.
