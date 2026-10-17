# Memphis single-rack-first bounded DEVELOPMENT

New scope, final design00/01 precedence. No old simulation/evidence/policy is overwritten. No new formalC3C, production, hardware orPhase6 authority.

## Sequence

Workflow `memphis-rack-v1.yml` on branch `codex/memphis-single-rack-v1` runs **baseline -> component -> single -> six -> report**. `six` cannot start until the complete single group passes its registered numerical/behavior checks and nominal full-load thermal gates. A stage PASS means experiment/equation/behavior validation only. Low-UA, warm-source and stuck scenarios retain actual thermal results; protection success does not turn temperature into PASS. Never rerun failed jobs on a sealed identity; preserve failure and publish a new source snapshot for ordinary unsealed tool repairs.

Baseline re-executes the original integration tests and original LOAD_STEP/PUMP_STUCK, binding all eight original raw files per case. Component checks a single constant-inlet rack CV against a closed-form transient and step refinement, NOT an actual CDU. New single/six cases independently reconstruct every control-volume rate, heat ownership, pressure/flow solution, measurement-only controller and PRE/Safety/PLC/POST bindings from persisted evidence.

## Parameter meanings

- One rack155kW IT /147.25kW liquid; six930kW IT /883.5kW liquid. Air remainder is not re-injected into liquid. Electrical pump heat enters liquid exactly once under an explicit100%liquid-loss assumption.
-45C limit applies to rack SECONDARY INLET. Return is calculated, not forced to45C. Sensor supply reads the modeled supply manifold/common rack inlet; zero branch inlet temperature-gradient is an assumption.
- One-rack design branch11.395m3/h and171.63kPa are preliminary references, not OEM maps. The bench adds10kPa series allowance. Six HOT complete secondary68.37m3/h/371.81kPa and NORMAL49.19m3/h/219.73kPa are design budgets, not installed-pump certification.
- Single primary18.333m3/h and UA36.667kW/K are **scaled engineering bench boundaries**, not a selected single-rack CDU. Six primary110m3/h,37/41C is document design; HX UA220kW/K is uncalibrated sensitivity.1100kW is the six-rack CDU selection, not a heater input, UA derivation or cooling cap.
- Inventory, quadratic pump curve, efficiency, sensor dynamics and deltaT PI excitation are exact registered assumptions. 8K controller deltaT reference is not an approved return-water target. Actual pump state drives hydraulic flow and heat evolution; only arrived observations drive control. Frozen actuator profile/M1 are unchanged.
- Nominal full-load and step cases require inlet<=45C and no false tracking fault. Stuck requires actual speed hold, new issued demand, M1 confirmation, latched Safety and no fabricated fault bit. Missing/stale requires sensor FAULT, no truth fallback and no false tracking confirmation. Warm primary must retain inlet>45C and measured protection.

## Execution and evidence

No local Python, model, native or stress execution. Pure local hashes/JSON/PowerShell parsing only. Controlled hosted Windows worker requires exactPython3.11.9, numpy2.4.6, pytest9.1.1, jsonschema4.26.0 and approved image. Actual child assignment and external PID proof precede numerical imports;25%CPU,1024MiBprocess/2048MiBJob,480s/stage. Source hashes checked before/after every stage. Official raw ZIPs contain complete compressed M1 journals; compact ZIPs omit zlib only. Independent final download must verify rawZIPs, all file hashes, compressed frames, repeats, source/env and cleanup. GitHub green alone is not evidence acceptance.

The group18 tower/tank/recharge/90s scope is not executed. It retains final shared-source segmented recharge and candidate115m3/h/34m distinctions for later implementation, not the historical independentPID recharge/max18m default. Actual OEM thermal/Q-dP/pump maps, geometry and GPU die remain unavailable. No steady-state, equipment safety or hardware guarantee follows from a finite120s experiment. Original M1 historical exclusions and qualification limits remain intact.
