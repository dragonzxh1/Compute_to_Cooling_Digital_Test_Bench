# Reference architecture review

## ThermaLoop

1. **Problem:** transparent single-server direct-to-chip thermal simulation and fault exploration.
2. **Overlap:** closest match to the V0.1 physical chain.
3. **Models:** workload/power states, lumped five-node RC heat path, 1-D finite-volume coolant transport, epsilon-NTU CDU, pump affinity laws, temperature-dependent water/PG properties, parametric uncertainty.
4. **Adopt:** explicit assumptions, YAML scenarios, conservation tests, portable reports, simple validated layers.
5. **Do not adopt:** source code, its H100 parameter set, single-server composition, or its single published anchor as proof for GB300/CDU behavior.
6. **Limits:** one validation anchor, no PLC/BMS, no GPU telemetry adapter, no multi-rack plant, representative rather than measured RC parameters.
7. **Integration:** its mathematical categories map to C2C-DTB `thermal`, `fluids`, `hydraulics`, and `cdu` ports, but are reimplemented independently.

## HPE Sustain-LC

1. **Problem:** benchmark traditional, RL, multi-agent, and LLM control against a Frontier-derived liquid-cooling digital twin.
2. **Overlap:** separation of high-fidelity plant from the control environment and CDU actions.
3. **Models:** Modelica plant compiled as FMI 2.0 co-simulation FMU; PyFMI stepping; Gymnasium observation/action spaces; ASHRAE-style controllers and learned policies.
4. **Adopt:** a narrow plant step contract, explicit action/observation variables, repeatable reset, separate plant timestep and controller step.
5. **Do not adopt:** RL-first structure, trained policies, Frontier-specific FMU, scaled opaque action encoding, or reward functions as safety logic.
6. **Limits:** heavyweight environment, external FMU/toolchain, research-oriented controller evaluation, limited direct path to DCGM schemas.
7. **Integration:** a future `FmuPlantAdapter` can implement the same C2C plant protocol used by the fast ROM.

## ExaDigiT RAPS

1. **Problem:** schedule or replay HPC workloads and estimate system power at configured intervals.
2. **Overlap:** compute-to-cooling co-simulation, replay, deterministic timebase, aggregated CDU power input.
3. **Models:** synthetic/replayed jobs, system-specific power models, discrete simulation, optional FMU cooling models and post-run plots.
4. **Adopt:** source adapters, one simulation clock, power aggregation at physical boundaries, replay modifications as configuration.
5. **Do not adopt:** scheduler scope, supercomputer-specific schemas, full system configuration catalog, dashboard/server coupling.
6. **Limits:** focuses on scheduling/power rather than cold-plate dynamics and PLC safety architecture; cooling depends on external FMUs.
7. **Integration:** a later RAPS adapter can emit canonical `ComputeTelemetry` without changing downstream physics.

## Data Center Cooling Simulation Framework

1. **Problem:** join SimAI workloads, AlphaDataCenterCooling, telemetry, APIs, and dashboards.
2. **Overlap:** workload/cooling adapters and external controller access.
3. **Models:** SimAI workloads; FMU/MLP cooling environment; REST disturbances/actions; Prometheus telemetry; Gym interface.
4. **Adopt:** explicit anti-corruption adapters and schema boundaries between compute and cooling.
5. **Do not adopt:** Docker microservice topology, bundled dashboards, SimAI subtree, credentials defaults, or RL environment as the domain core.
6. **Limits:** large operational footprint, multiple embedded licenses, infrastructure complexity obscures the minimum physics chain.
7. **Integration:** use its adapter lesson, not its deployment stack; C2C exposes in-process ports first and FastAPI later.

## NVIDIA DCGM

1. **Problem:** collect GPU inventory, health, utilization, power, clocks, and thermal telemetry.
2. **Overlap:** future real compute source.
3. **Models:** not a cooling model; versioned field identifiers and sampled device values keyed by GPU identity.
4. **Adopt:** GPU UUID as stable identity; distinguish instantaneous/sampled metrics; tolerate unsupported fields.
5. **Do not adopt:** DCGM headers/bindings in the domain model or a requirement that every GPU exposes every field.
6. **Limits:** hardware/driver/version-dependent availability and sampling semantics; telemetry is observation, not workload intent.
7. **Integration:** `DCGMSource` maps fields such as power usage, GPU temperature, utilization, SM activity, clocks, and limits into optional canonical fields.

## NVIDIA DCGM Exporter

1. **Problem:** expose selected DCGM fields as Prometheus metrics with GPU/container/job labels.
2. **Overlap:** infrastructure-friendly future telemetry ingestion.
3. **Models:** collector configuration, polling, Prometheus exposition and labeling.
4. **Adopt:** configurable metric mapping, UUID label preference, missing/sentinel-value rejection, scrape timestamp recording.
5. **Do not adopt:** Go exporter internals, Kubernetes assumptions, or metric names inside thermal models.
6. **Limits:** scrape delay and loss of some sampling semantics; available metrics depend on collector configuration.
7. **Integration:** `DCGMExporterSource` parses exposition text into the same `ComputeTelemetry` contract.

## RWTH HPC Digital Twin

1. **Problem:** replay measured facility data, run simulations/predictions/optimization, and visualize results.
2. **Overlap:** replay, coordinator, swappable physical models, scenario analysis.
3. **Models:** FMU for one site, Julia for another, ML IT-load model, time-series platform and FastAPI coordinator.
4. **Adopt:** coordinator/model separation, deployment-specific model selection, explicit timestep, model state save concept.
5. **Do not adopt:** FIWARE/NGSI-LD, multiple databases, Docker Compose, or frontend in V0.1.
6. **Limits:** facility-level platform overhead and less focus on GPU-to-cold-plate transients.
7. **Integration:** later persistence and fleet services consume C2C run artifacts without entering the domain solver.

## NVIDIA Omniverse DSX Blueprint

1. **Problem:** demonstrate AI-factory design/configuration and simulation visualization using Omniverse/OpenUSD.
2. **Overlap:** future AI-factory configuration and DSX-style interoperability.
3. **Models:** geometry/configuration composition, sample CFD/electrical scenarios, streaming Kit application and web portal; not the V0.1 ROM.
4. **Adopt:** interface philosophy, configuration identity, read/request/accepted/actual state separation.
5. **Do not adopt:** source, USD assets, sample data, frontend/streaming stack, proprietary message assumptions.
6. **Limits:** demonstration blueprint, large hardware/software footprint, license-specific restrictions, no turnkey supervisory controller.
7. **Integration:** a future `DSXAdapter` translates versioned external messages at the boundary only.

## Frontier Co-Design Optimization

1. **Problem:** optimize CDU subloop layout, total flow, flow split, and supply temperature over a year of Frontier data.
2. **Overlap:** ROM-based supervisory optimization, ramp constraints, pump/cooling energy.
3. **Models:** per-subloop energy balance, pump/cooling-tower ROMs, constrained per-timestep optimization calibrated to a Modelica twin.
4. **Adopt:** high-fidelity-to-ROM calibration pattern, explicit actuator constraints, native-timestep ramp semantics.
5. **Do not adopt:** any code/parameters because of CC BY-NC-SA; facility layout optimization is outside V0.1.
6. **Limits:** plant/fleet scale rather than GPU thermal response; calibration is Frontier-specific.
7. **Integration:** future Level-1 optimizer consumes calibrated C2C plant models, never the research code.

## Cross-reference conclusion

The references converge on five useful ideas: adapters around workload sources, deterministic co-simulation clocks, reduced-order physics for fast studies, FMI as a high-fidelity boundary, and separate control environments. None combines canonical GPU telemetry, transient chip-to-liquid physics, deterministic PLC safety, shadow supervisory intent, parameter provenance, and later real-CDU substitution. That combination is C2C-DTB's distinct boundary.
