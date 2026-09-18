Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 12 — Energy Control Volume Contract

## Inputs / Outputs

Input: stored energy by unique owner, interval source receipts, interface ledger, pump loss/dissipation receiver map and primary/secondary ports.
FluxRecord: interface_id, from_cv, to_cv (or EXTERNAL), start/end_ns, energy_j signed along orientation, mechanism (CONDUCTION/CONVECTION/ADVECTION/ELECTRICAL/HYDRAULIC_DISSIPATION), owner_id, validity.
Output: ΔE, inputs, outputs, residual_j and normalized residual per nested CV, interval and cumulative; auditor-only.

## Boundaries

| CV | Storage / external terms | Internal cancellation |
|---|---|---|
| Device CV | die/package/HBM/VRM as declared entity; leaf electrical inputs, heat to plate/coolant and air outside this device | within-device thermal links |
| Rack CV | all rack device solids, coldplates/local coolant, rack pipe/manifold inventory, optional dynamic rack air | chip/plate/liquid and internal air exchanges |
| Full Loop CV (secondary thermal) | Rack plus secondary piping/CDU volume and declared HX wall/secondary storage | rack inlet/outlet, all secondary links cancel |

Rack external terms: IT electrical sources; pump heat only at explicit inside-rack receivers; air/ambient export; secondary supply/return enthalpy flow; change of total owned stored energy.
Full Loop external terms: IT power; declared pump loss and hydraulic dissipation deposited inside; signed ambient exchange; heat exported to primary via HX; total storage.
Default full loop EXCLUDES VFD/motor/shaft mechanical/electrical storage and primary inventory, so Pelec is not injected in addition to pump thermal contributions. HX wall storage if modeled assigned once; Q_secondary and Q_primary can differ by wall storage rate. No-wall default exchanges equal/opposite.

Optional combined primary+secondary CV includes primary inventory; HX then internal, FWS inlet/outlet enthalpy external. This is a separate audit aggregation, never add HX export and FWS enthalpy export for same CV. Electrical facility meter is a separate accounting boundary from either thermal CV.

## Sign / residual

r=ΔE−(ΣE_in−ΣE_out). Source positive entering; signed flux reversal retained. Interface calculated once by owner; adjacent CVs take opposite signs. Parent residual reconstructed by summing children plus uncovered sources/storage, not summing both parent and child heat. Every storage_owner appears exactly once in chosen CV union.
Advective flux = signed m_dot × specific enthalpy of UPSTREAM donor, integrated over interval. Common enthalpy reference and fluid properties mandatory; temperature alone without mass flow not a heat rate. Stored coolant enthalpy M×h(T) with fixed M. h(T) integral Cp from shared reference.
Pump shaft/hydraulic energy follows05. Dissipation deposits once at resistance receivers, not pump hydraulic and resistance heat together.
Generic conservation tolerances exactly11. IT-water gap is a physical diagnostic including air/storage, not this residual. Steady capture validation requires low storage change and stable qualified window, never force transient heat equality.

## Failure / acceptance specifications

ECV-01: partition and recombine device/rack/full-loop residuals; internal flux cancels exactly by ID.
ECV-02: finite temperature storage transient yields nonzero IT-water gap but small numerical residual.
ECV-03: pump100W example from05 + liquid80/ambient20 closes appropriate CV; no duplicatePelec.
ECV-04: dynamic rack air internal links not also external loss; combined-primary boundary does not duplicate HX.
ECV-05: missing flux owner/storage duplicate -> ENERGY_TOPOLOGY_FAIL; numeric violation -> ENERGY_BALANCE_FAIL, INVALID qualified scoring.

