# Six-rack V2: bounded physical-credibility DEVELOPMENT

Preserves V1 and the qualified M1 engine; no inherited integrated-system
qualification. Run only on the hosted Windows Job with externally verified
actual Python PID, CPU 25%, process/Job 1024/2048 MiB and 480 s per stage.
Never launch a numerical worker on the previously unstable local machine.

`study.json` registers 21 cases: seven one-factor settings each for LOAD_STEP
and PUMP_STUCK, five bounded faults, and two finer-step PUMP_STUCK runs.
The separate NEGATIVE stage runs unchanged V1/hydraulic tests plus V2 tests.
BASE executes unchanged V1 freshly and must match eight official output hashes
per case. No earlier PASS is substituted for this execution.

## Inputs and interpretation

- BASE: V1 fixed 37 C primary inlet, UA 220 kW/K, secondary inventory 1.3 m3,
  quadratic pump/network derived from one 68.37 m3/h, 371.81 kPa design point.
  These are document design points plus uncalibrated assumptions, not an OEM map.
- UA factors 0.5/1.5; liquid inventories 0.5/2.0; pump shutoff-head factors
  0.8/1.2 with curve K and network fixed. These are exploratory OAT points,
  not manufacturer uncertainty ranges, joint envelopes or probabilities.
- Sensor loss/staleness 40--45 s; slow actuator from 10 s; synthetic network
  resistance 100x from 40 s; silent stuck 10--45 s then physical release.
  No fault flag or forcing schedule enters M1 or the controller. Recovery
  never grants Safety reset authority. Slow response is not forced to confirm.
- Customer 45 C is RACK_SECONDARY_INLET protection (`bound_project.json`,
  secondary_hard_limit, source 02.docx B012). V1 max-rack-return 45 C is only
  an engineering control assumption. RETURN45=NOT_REGISTERED_NOT_SCORED.

The independent auditor imports no plant/solver. It reconstructs all eight
local liquid-volume balances, total energy, mass, counterflow HX and pump-loss
partition, plus persisted measurement/command phase causality. Numerical
closure does not establish calibration. 120 s endpoints are not steady state.
Sensitivity execution PASS means a valid experiment, not all behavior PASS;
contrary behavior remains in the unmodified payload and consolidated report.

## Remote reproduction

Use the dedicated `codex/gb300-m1-six-rack-v2` branch and workflow
`gb300-m1-six-rack-v2.yml`. For a registered workflow, dispatch with exact
`expected_commit` and raw `source_manifest.json` SHA256. Do not merge/release
or rerun formal C3-C. The source guard binds V1 and all 836 frozen sources.

Four controlled groups run baseline first, then three independent study groups.
Raw artifacts contain complete compressed M1 transaction journals. Compact
artifacts omit only `.zlib`, record their exact hashes and location, and are
not represented as complete raw archives. `report.ps1` verifies compact file
hashes and Job cleanup before creating one HTML/JSON report with plots.

Not modeled: physical dual-CDU failover, primary A/B network, source pumps,
dry/wet towers, stratified 15 m3 tank, 18-rack common failures, annual weather,
GPU die/coldplate behavior, OEM calibration or production control.

Formal C3-C/production/hardware/Phase6: NOT AUTHORIZED by this task.
