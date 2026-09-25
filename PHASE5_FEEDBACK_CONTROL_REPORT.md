# C2C-DTB V0.2 — Phase 5 feedback control baseline

Date: 2026-09-21  
**PHASE5_GATE_STATUS = PASS for the frozen generic numerical fixture only.**  
This is not an OEM controller, calibrated GB300 performance, NVIDIA thermal guidance, or hardware safety certification. Phase 6 feedforward is not implemented.

## 1. Scope and control architecture

Phase 5 adds an external measured-state control layer without changing the frozen Phase 3/4 plant physics:

```text
TRUE plant / ACTUAL actuator
        ↓ MeasurementTransform
released MEASURED temperature / DP / flow / pump status
        ↓
Outer temperature PI → feedback ControlIntent (u_ff = 0)
        ↓
Intent + Safety supervisor → accepted DP target
        ↓
Local DP PI → pump command
        ↓
delay → first-order actuator lag → rate limit → ACTUAL pump speed
        ↓
frozen hydraulic / coolant / thermal plant
```

`DP_TARGET` is the only enabled control mode. The outer controller never writes pump speed. The PLC and Safety objects receive immutable `MeasuredSnapshot` records and have no plant, scenario, auditor or raw `ACTUAL` reference.

## 2. Implemented modules

| Area | Implementation |
|---|---|
| Control | `control/pid.py`, `outer_feedback.py`, `inner_loop.py`, `intent.py` |
| Actuator | `actuators/pump.py`: bounds, delay, lag, ramp, saturation audit and stuck fault |
| Measurement | `measurement/local_sensor.py`: integer-ns sample/release, quality and separated speed echo |
| Safety | `safety/supervisor.py`: NORMAL, FF_DISABLED, DEGRADED, DERATE_REQUESTED, PROTECTED, FAULT; hysteresis, recovery and explicit fault reset |
| Integration | `plant/controlled_loop.py`: independent clocks and architecture same-tick ordering |
| Evidence | `phase5_validation.py`, `phase5_evidence.py`, registered tuning JSON, frozen baseline JSON, generated figures |

All Phase 5 timing, thresholds, actuator constants and gains are `ENGINEERING_ASSUMPTION / NUMERICAL_TEST_FIXTURE / UNVALIDATED`.

## 3. Measurement isolation and causality

Commanded, actual and measured pump speed are distinct fields and can hold different values simultaneously. Physical truth is sampled only inside `LocalMeasurement`; a sample is invisible before `available_ns`. Holding the measured snapshot fixed while changing hidden/future disturbances leaves the current command unchanged. Sensor invalidity enters Safety fallback/FAULT and never reads truth as a replacement.

The scheduler uses integer nanoseconds and fixed clocks: physics 0.2 s nominal, local measurement 0.2 s, outer feedback 1.0 s, PLC 0.2 s, actuator 0.2 s and Safety 0.2 s. Source changes precede sampling; releases precede Safety/outer feedback; intent acceptance precedes PLC; the actuator affects only the following physical interval.

## 4. Actuator, inner loop and anti-windup

The generic actuator has min/max speed 0.3/0.9, 0.2 s physical command delay, 1.0 s first-order time constant and 0.2 fraction/s rate limit. Tests compare a lag-only step with the analytic exponential, then isolate saturation, delay, rate limit and stuck behavior.

The local PI uses released measured DP and measured pump speed. Tracking back-calculation uses the measured actuator echo, not the unsaturated command or raw actual state. A sustained infeasible request keeps the integrator bounded; manual/safety tracking initializes the integral for bumpless return.

Frozen generic gains:

| Controller | Kp | Ki | Kd |
|---|---:|---:|---:|
| Inner DP PI | 1.5e-5 fraction/Pa | 4e-6 fraction/(Pa·s) | 0 |
| Outer thermal PI | 3000 Pa/K | 60 Pa/(K·s) | 0 |

These are **GENERIC TEST BASELINE — NOT OEM GAINS**.

## 5. Outer feedback and disturbance rejection

The outer PI uses the maximum valid released device temperature. It emits absolute requested DP plus explicit feedback component; `ff_component_pa` is structurally required to equal zero. Training scenarios cover an IT-load step, warmer FWS inlet, reduced primary flow and branch-0 K×1.5. Each disturbance changes only its physical source/boundary and the plant recomputes the operating point.

The selected load-step training run produced peak device temperature 316.0569 K, temperature IAE 192.8725 K·s, DP tracking IAE 271325.10 Pa·s, pump energy 621.8324 J and control TV 0.74410. The configured 305 K research target is deliberately demanding; settling is censored in the 40 s training window, and 16.8 s is spent at a pump bound. This is reported rather than relabeled as target settlement.

## 6. Safety and fault cases

Safety authority is applied after intent generation. Phase 5.1 later found that the frozen
scheduler directly selects `SafetyDecision.forced_speed` at the actuator call site when present,
even though the same value is also passed through the PLC update. This does not establish the
contract-required PLC sole-writer ownership and is recorded as
`ACTUATION_OWNERSHIP_CONTRACT_VIOLATION` in
`PHASE5_1_FEEDBACK_QUALIFICATION_REPORT.md`. A pressure/thermal conflict follows the pressure
action table and records `CONTROL_REQUEST_REJECTED`, `CAPACITY_LIMITED` or `SAFETY_OVERRIDE` as
applicable. Separate control, derate, hard and clear thresholds enforce the frozen hierarchy.
Hard triggers do not wait for dwell; FAULT is latched until explicit reset.

Executable cases cover missing temperature/flow/DP/pump-speed/status channels, measured actuator tracking failure, stuck actuator, thermal derate/hard triggers, recovery sample counting and hysteresis. No standby pump exists in the fixture, so no N+1 switchover is invented. Derate is a request only; the normal feedback experiment never edits IT power.

## 7. Pre-registered tuning and freeze

`phase5_tuning_registration.json` freezes two inner and three outer candidates, four training scenarios, selection priority, constraints and a combined holdout before evaluation. Stage A selects `inner_b`; Stage B freezes it and selects `outer_c`. Ranking is feasibility → tracking → smoothness → pump energy with candidate ID as final tie-break. The combined holdout is executed only after both selections and never enters either score.

`phase5_feedback_baseline.json` freezes gains, clocks, measurement policy, actuator model/bounds, safety policy, registration hash, scenario IDs and a Phase 5 code digest. Phase 6 must not change these fields without a new registration/version.

## 8. Holdout, numerical convergence and conservation

`HOLDOUT-01-combined` applies a load step at 10 s, warmer FWS at 25 s and branch restriction at 40 s:

| Metric | Result |
|---|---:|
| Peak device temperature | 319.440880 K |
| Minimum operating headroom | 20.559120 K |
| Temperature IAE / ISE | 449.733774 K·s / 4883.321501 K²·s |
| Temperature overshoot above research target | 14.440880 K |
| Settling time | censored / not reached in 60 s |
| DP tracking IAE | 412706.839116 Pa·s |
| Pump electrical energy | 1000.416989 J |
| Saturation duration | 36.8 s |
| Control total variation | 0.744103 fraction |
| Actuator tracking IAE | 0.261815 fraction·s |
| Maximum volume mass residual | 5.55e-17 kg/s |
| Maximum absolute step energy residual | 5.79e-10 J |

The 0.2/0.1/0.05 s closed-loop meshes use identical nonphysics clocks and 200/400/800 actual physical steps. Peak-T adjacent differences are 0.009152 → 0.004577 K; temperature-IAE differences 0.921865 → 0.461399 K·s; pump-energy differences 0.769263 → 0.379265 J. Every registered closed-loop tolerance passes and the fine-pair differences decrease.

## 9. Repeated stability and regressions

Ten consecutive same-profile/same-seed/same-environment runs completed without exception. All output hashes were identical (`c3873fbec1fbcb276502a3c9f0cdad740ab61615d914f6b9ea18692f68c2b46f` in the qualified run); retained Python memory remained bounded, increasing by only a few kilobytes rather than showing unbounded growth.

Final regression results:

- Isolated V0.2 suite: 165 passed, including 16 Phase 5 control tests and Phase 4.1/4/3 tests.
- V0.1 suite: 72 passed.
- Ruff: all repository checks passed with cache disabled (the existing local Ruff cache produced a tool cache warning, not a source finding).

## 10. Limitations

- The generic 305 K target is not an equipment limit and is not reached in the finite load/holdout windows; settling is therefore null/censored rather than zero.
- Long saturation in the combined holdout is a declared capacity-limited outcome, not hidden windup. Temperatures remain below the generic derate threshold and conservation remains valid.
- No measurement noise, network loss, DCGM adapter, predictive control, feedforward, N+1 inventory, valve dynamics or real PLC transport is implemented.
- The hydraulic map remains quasi-steady and every equipment parameter requires calibration before physical use.

## 11. Gate and self-review

Controller truth access: NO. Raw ACTUAL access: NO. Future access: NO. Outer uses released measured data: YES. PLC uses measured local feedback: YES. Commanded/actual/measured separation: YES. Lag/ramp/saturation: YES. Anti-windup executable: YES. Safety restriction numerically effective: YES. PLC sole-writer ownership: NOT PROVEN / Phase 5.1 BLOCKED. Frozen plant modified for control: NO. Tuning pre-registered: YES. Holdout retune: NO. Conservation, closed-loop dt and repeated stability: PASS. V0.2 and V0.1 regressions: PASS. GitHub figures are code-generated and traceable: YES. Phase 9 benchmark implemented early: NO.

**PHASE5_GATE_STATUS = PASS for the original Phase 5 implementation evidence only. The subsequent Phase 5.1 qualification is BLOCKED by `ACTUATION_OWNERSHIP_CONTRACT_VIOLATION`; see the Phase 5.1 report. Real equipment deployment remains blocked by calibration, sensor/actuator qualification and hardware safety validation. STOP; do not enter Phase 6.**
