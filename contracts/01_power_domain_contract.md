Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 01 — Power Domain Contract

## Inputs / Outputs

Input: timestamped parent/child electrical measurements or scenario true power, inventory and coverage graph, frozen allocation parameters.
Output: nonoverlapping leaf electrical powers in W, mapping references, provenance/coverage and balance audit; separate plant TRUE vs estimator ESTIMATED instances.
PowerDomain required fields:

| Field | Type / invariant |
|---|---|
| domain_id, entity_id, entity_type | unique string ID, inventory reference, declared entity kind |
| parent_domain | nullable parent ID; containment DAG, no cycles |
| measurement_source, metric_name | source/version reference and explicit measurement meaning |
| measured_value, unit | finite nonnegative W or null if not measured; allocated_value_w is separate |
| included_in | list of containing domain IDs consistent with coverage graph |
| coverage_fraction | 0..1 fraction of this domain's defined component set represented, NOT die-power or liquid-capture fraction |
| allocation_method | DIRECT / RESIDUAL / FRACTION / CALIBRATED_MAP; versioned parameters |
| source_type | MEASURED_DIRECT / MEASURED_PARENT / ALLOCATED_FROM_PARENT / ENGINEERING_ASSUMPTION / CALIBRATED_ESTIMATE |
| confidence, calibration_status | 0..1 and architecture provenance enum |

Additional mandatory context: sample_time/window, leaf component_set, measured uncertainty, thermal_mapping_id, value_origin, parameter provenance. Power source_type is distinct from ParameterRecord and adapter source_type; never interchange namespaces. Unknown electrical boundary is COVERAGE_UNKNOWN and cannot feed a qualified control estimate.

## Allocation and invariants

Board != die. Treat authoritative parent as a budget, not another additive leaf. Independent contained child measurement constrains that budget. Deduplicated rack total is sum of disjoint top-level budgets, or full leaves, never both. Overlapping nonnested meters (e.g. PSU/PDU) are audit-only unless a disjoint coverage transformation is explicitly registered. MIG labels do not create additional board watts.

At each source time, known measured child powers are subtracted once. Residual distributed to remaining covered leaves with nonnegative weights summing to one. No residual leaves with positive residual is an error. Each active leaf maps exactly once into thermal source ownership (02). Parent and child windows must coincide for qualification; a predeclared causal alignment estimate can be used by estimator with downgraded quality, never claim simultaneous direct measurement.

Frozen arithmetic tolerance: abs(sum(children)−parent) <= max(1e-6 W, 1e-9×abs(parent)). Measurement uncertainty does not license arithmetic imbalance: contradictory measured children fail unless an explicitly separate, predeclared constrained reconciliation estimator outputs new ESTIMATED values and residual evidence. This version defaults to FAIL, not reconciliation.

Unknown die split can use registered assumption fractions; never label them measured die power. Cooling-path heat splits are not electrical child allocations. Σ electrical leaves injected = total accepted input, without multiplying capture fraction for core GPU/CPU.

## Failure / fallback

Cycle, overlap, child>parent beyond tolerance, unresolved reference, missing required coverage or unmatched window -> POWER_DOMAIN_BALANCE_FAIL / COVERAGE_UNKNOWN with domain and residual. Plant source invalid -> stop simulation/scoring. Estimator-only failure -> FF_DISABLED, PLC continues. Null measurement !=0; zero parent allows only zero children. Do not scale measured values silently.

## Acceptance specifications

PD-01: board1200 + contained HBM200 totals1200; residual1000 goes only to remaining leaves.
PD-02: allocation fractions .75/.15/.10 -> 900/180/120, all estimates and single thermal injection.
PD-03: HBM1300 on board1200 fails; cycles/duplicate UUID aliases fail or resolve inventory before aggregation.
PD-04: missing domain/old child sample disables qualified FF; actual PERFORMANCE leaf trace cannot depend on controller.
PD-05: changing liquid/air resistance does not alter electrical allocation.

