Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 07 — True / Measured State Contract

## Inputs / Outputs

StateEnvelope fields: variable_id, entity_id, layer, value, unit, timestamp, provenance_ref, quality, origin_refs.
layer = TRUE / MEASURED / ESTIMATED / COMMANDED / ACTUAL.
Examples: gpu_temp_true, gpu_temp_measured, gpu_temp_estimated; pump_speed_commanded vs pump_speed_actual.
ACTUAL denotes physical actuator outcome and is a truth subtype for permissions: controller only receives its measured speed echo, not raw ACTUAL. COMMANDED history is output bookkeeping; it is not a physical measurement. Estimator's prior commands/config are bookkeeping only, never an alternative sensor.

PlantStep input owns sources/boundaries/actual actuators; output TRUE snapshot.
MeasurementTransform consumes an allowed TRUE/ACTUAL field at its sample event and emits MEASURED.
Estimator consumes available measured snapshots and prior estimated state; output ESTIMATED.
Controller consumes permitted MEASURED/ESTIMATED and static configuration; its own command history is internal memory.
Auditor consumes append-only snapshots of all layers, produces no control inputs.

## Isolation invariants

Future implementation separates typed views/ownership; controller object never receives plant/scenario/auditor reference, callback or unrestricted storage. No shared mutable dict with hidden true fields. Separate estimator state even if initialized to same configured T as plant. Thermal estimates must carry estimator origin and uncertainty; cannot relabel TRUE as ESTIMATED.

Measurement noise, bias, sampling and delay only in Measurement System. Physical workload/FWS disturbances are explicit plant forcing, not sensor noise injected into truth. A hardware protection channel is itself a modeled independent measured channel with stated latency/accuracy, not a permission shortcut.

Initial controller state fixed or derived only from released startup measurements. Any prehistory/prefill is specified identically across modes; no optimizing initial integrator states from hidden future traces.

## Failure / fallback

Forbidden field access -> STATE_ACCESS_DENIED and invalid comparison, not silently ignore for benchmark. Missing measured input -> safety fallback15, not read truth. Metrics path is one-way and never updates target/gains mid-run. Offline training uses separate datasets and frozen controller parameters before holdout.

## Acceptance specifications

SS-01: controller input snapshot contains no true/future/actual-only fields.
SS-02: corrupt truth but hold measured snapshot fixed: current controller action unchanged; future actions may change only when measurement arrives.
SS-03: measurement noise changes measured but not true stored state directly.
SS-04: auditor enabled/disabled cannot change any plant/control trace.
SS-05: actuator actual lag cannot be replaced by commanded speed in sensor-independent control path.

