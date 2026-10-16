# Memphis Project V1 — offline bounded DEVELOPMENT

This new scenario reuses the existing hydraulic solver, fluid/HX/pump library,
V1 actuator/sensor/PLC adapters and unchanged qualified M1 engine. Upstream JS
files are exact source snapshots; `NODE_PORT` executes their original functions
and verifies the new tank-rate port. V1/V2 are fresh regression baselines, not
evidence borrowed to qualify this new integrated plant.

Six racks: each155kW IT,95%liquid,883.5kW liquid total. Three units:2650.5kW.
UA110/220kW/K, pump curves/efficiencies,14-volume inventories, tank mixing and
short circuit, timing and controller gains are explicit engineering assumptions.
Default actual equipment UA is null and MUST refuse execution. No manufacturer
performance/MAWP/NPSHr or GPU die safety is fabricated.

`registration.json` binds all cases and parameter provenance; `upstream/project.json`
retains detailed document locators. CDU requirements are derived by ORIGINAL JS
`assessInputs` in `baseline/NODE_PORT/upstream_actual_output.json`, not supplied UA.
V9 pump115m³/h34m and PID110m³/h/fullcurve18m remain separate UNSELECTED alternatives.

Three units share modeled primary load/source headers; A/B tanks never mix.
D1/D2 and W1/W2 have separate actual availability. Dry/wet capacities are original
document-rating reductions, NOT actual manufacturer maps. Dry cases use DB29°C;
wet HOT uses DB46/WB30. Load follows actual pump/valve flow and tank temperature.
Source startup54s, detection1s, each valve stroke5s and transport2.75m³/10cells
are additive assumptions, NOT a registered guarantee of90s continuity.

Shared recharge uses measured four-TT reserve permission and bounded60s diversion.
Independent recharge has a separate pump; W2 cannot be online and recharging at
once. Four-TT conservative10m³ restore permission is not the original physical
10.5m³ cold fraction. Both alternatives remain unapproved. A_LEAK_SIGNAL checks
isolation logic only; actual fluid loss and refill/pressure dynamics NOT_VERIFIED.
Zero-flow motor/deadhead losses remain uncalibrated. Equal CDU primary branches
are synthetic reduction, not actual field balancing.

Iteration3 retains the valid overspeed failure from run38937189134. The required
independent-recharge speed1.011666 exceeds the unchanged physical1.0 curve limit.
Actual drive now saturates at1.0 and solves the resulting deficient flow; this is
NOT permission to demand330m³/h or to accept this pump. Startup-state readiness
and actual cold-water return are separately reported. Cold-return first arrival
requires available source,actual flow≥264m³/h,return≤41.4448°C; not a stability
or calibrated recovery guarantee. These observation criteria are assumptions.

## Execution and evidence

Do not run locally on HIPPO. Authorized branch workflow `memphis-project-v1.yml`
runs on hosted Windows, exactPython3.11.9/locked dependencies,25%CPU,1024MiB
process/2048MiBJob and480s/stage. Actual Python and upstream Node PID are externally
checked in the Job BEFORE numerical work. Stage source is hash-bound before/after.
Raw output includes actual observations, commands, PRE/Safety/PLC/POST, every
physical interval, completed compressed M1 journals and cleanup proofs. Compact
copies omit only zlib and identify the separate full raw archive.

Seven engineering grades are independent. Stage PASS means the experiment ran
and equation/evidence checks succeeded; it never means equipment suitability.
90s continuity uses maximum actual rack secondary-inlet temperature AND source
takeover latency;45°C is NOT return, primary-side or GPU die temperature.
M1 schedule1s(unit)/5s(group) is NEW integration scheduling, no inherited timing
qualification. Project protection has no duplicate tracking timer. No IT power
reduction is applied by a derate request; full offered load remains explicit.

No formalC3-C, release, merge, hardware, production or project Phase6 authority.
OriginalStartup49/50, compatibility separately; SEM02five strictP1B/C INCOMPLETE;
PF06originalINCOMPLETE; arbitraryPOST/crash/powerlossatomicityNOT_PROVEN;
T09HOLD;fullPhistoryunavailable;hardwareCALIBRATION_REQUIRED remain unchanged.
