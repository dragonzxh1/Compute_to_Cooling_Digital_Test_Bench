# ADR-001: C2C-DTB V0.1 architecture

## Status

Accepted for V0.1 on 2026-09-15.

## Context

The test bench must correlate workload events with delayed thermal and hydraulic response, let virtual components be replaced by real telemetry/hardware, and preserve L0/L1 safety when L2 supervisory logic is absent. V0.1 must remain locally runnable and inspectable.

## Decision

Build a deterministic Python modular monolith with dependency-inverted ports and a single SI-unit simulation clock. Each model owns state and implements an explicit `step(inputs, dt)` boundary. Domain modules do not import FastAPI, Prometheus, DCGM, or FMU libraries.

```text
WorkloadSource -> ComputeTelemetry -> Power/Heat -> RC Thermal Plant
       -> Hydraulic Operating Point -> epsilon-NTU CDU -> Virtual PLC
       -> Shadow LCI recommendation -> Run artifacts
```

The V0.1 plant is a fast reduced-order model. Future FMU, real DCGM, and real CDU implementations replace adapters behind the same contracts. Supervisory output is intent; the PLC clamps/rate-limits it and remains independently operable.

## Alternatives

- **Fork ThermaLoop:** faster initial physics, but couples C2C to another project's composition/parameters and weakens provenance. Rejected.
- **Start from Modelica/FMU:** higher plant fidelity, but raises toolchain and iteration cost before parameters or validation anchors exist. Deferred as Level 2/3.
- **Microservices plus Prometheus:** realistic deployment topology, but introduces failure modes unrelated to the first physics question. Deferred.
- **RL/Gym first:** useful for later policy research, but cannot replace a validated deterministic baseline or PLC safety layer. Deferred.

## Consequences

V0.1 is easy to test, replay, calibrate, and run faster than real time. It cannot claim OEM accuracy, local hot-spot resolution, or production control readiness. Interface stability and parameter provenance are favored over early infrastructure realism.

## Interface contracts

- `WorkloadSource.next_step(t_s) -> ComputeTelemetry`
- `ComputeToHeatModel.step(telemetry) -> HeatLoad`
- `ThermalPlant.step(heat, coolant, dt_s) -> ThermalState`
- `HydraulicModel.operating_point(command) -> HydraulicState`
- `CDUModel.exchange(inlets, flows) -> CDUExchange`
- `VirtualPLC.step(measurements, intent, dt_s) -> ActuatorCommand`
- `SupervisoryController.recommend(compute, plant) -> SupervisoryIntent`

Adapters translate external schemas; they never leak external field names into core physics.
