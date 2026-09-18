Revision: 1.1
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 14 — Control Input Permission Contract

## Inputs / Outputs

Input: immutable typed state views, module role and available_time. Output: authorized view or STATE_ACCESS_DENIED. Deny-by-default, allow only matrix entries.
R=read; W=sole production/actuation ownership; —=forbidden. “Measured” always means available and quality-qualified, not raw future packets.

| Module | True/actual plant | Measured IT/age/quality | Measured T/flow/ΔP | Measured Actuator / Equipment Status | Static topology/calibration | Future workload/FWS/K schedules | Intent/commands | IT trace mutation |
|---|---|---|---|---|---|---|---|---|
| Physical Plant | R/W own state | — | — | — (owns ACTUAL, not measured view) | R | R current forcing via injector, not controller | R actual actuator input | — (consumes delivered trace) |
| Measurement Pipeline | R whitelisted fields at sample time | W | W | W | R sensor config | — | R commanded echo if sensor modeled | — |
| FF Estimator / FF | — | R | — | — | R | — | W FF intent; R own prior output bookkeeping | — |
| Outer FB | — | — | R | R OPTIONAL, registered channels only | R | — | W FB intent; R own history | — |
| Intent Supervisor | — | R quality/age only | R constraints where declared | — (Safety supplies restrictive envelope) | R | — | R intents/W accepted targets | — |
| PLC | — | R FF validity only | R local sensors | R | R | — | R accepted targets/W actuator command | — |
| Safety | — | R quality flags | R protection channels | R | R | — | W restrictive envelope/derate request | — |
| Synthetic Protection Load Gate | — | — | — | — | R load policy | R current offered power only | R safety request/ack | W delivered only in SAFETY_PROTECTION |
| Metrics / Auditor | R | R | R | R | R | R audit only | R | — |

Scenario/replay injector owns offered trace/current FWS/K events; no references to it in controller views. Hardware interlock digital signals permitted to safety/PLC are modeled measured channels, not direct hidden truth.

## Enforcement invariants

Measured actuator/equipment channels include pump_speed_measured, pump_running, pump_ready, pump_fault; valve_position_measured, valve_ready, valve_fault; VFD_running, VFD_fault, VFD_speed_feedback; actuator_tracking_error, command_acknowledged, command_age. All physical status channels pass through Measurement Pipeline with06 timestamps/quality/latency. An acknowledgment carries command ID and states whether it means receipt, acceptance or execution; receipt alone does not prove motion.

Path: ACTUAL Pump Speed -> Measurement Pipeline -> pump_speed_measured -> PLC / Safety. Commanded, Actual and Measured are distinct layers even when values happen to coincide. PLC/Safety never read raw pump_speed_actual. FF remains IT-driven and has no actuator-status input here.

PLC/PID may use qualified measured feedback for anti-windup, bumpless transfer, tracking back-calculation, saturation/stall detection. Tracking error uses a declared time-aligned command from command history and an available measured feedback sample; it cannot contain hidden ACTUAL. Measurement Pipeline publishes equipment-reported tracking errors or derived channel records with origin/time/quality; a PLC may also compute its internal error from the same authorized inputs. command_age is clock-derived command bookkeeping, not a physical sensor or proof of execution; it must not refresh the sensor sample age. Timeout detection may use command history and absence of an acknowledgment, while a claim of measured stall requires arrived measured feedback/fault evidence. Stale/missing feedback invokes15 rather than a truth lookup.

FF allowed measured IT power, topology, static calibration, quality and age; banned future workload, true GPU temp, future FWS/blockage and hidden state. Deterministic causal estimated state is permitted only from authorized origins. GPU temperature correction belongs to FB.
All command effects go through supervisor/safety/PLC, including FF-only diagnostic. PLC actual speed feedback must be measured07, not read ACTUAL directly. Auditor data is a sink, never used for live gain/target tuning.
ControlIntent expires_time uses simulation time; expired/unavailable/replayed-old sequence rejected, not renewed merely on forwarding.

## Failure / acceptance specifications

PERM-01: access true/future data throws/flags access violation -> comparison INVALID.
PERM-02: hold measured snapshots fixed while mutating hidden future schedules: current FF/FB commands unchanged.
PERM-03: metrics receive truth but toggling metrics cannot alter commands.
PERM-04: direct FF actuator write rejected; IT edits forbidden except dedicated SAFETY load gate.
PERM-05: source adapter/replay exposes only read_available view, not raw file/repository.
PERM-06: command80%, actual60%, measured60% delayed; before available_time PLC sees only previous measured value, after release may apply tracking correction. Hidden actual60% cannot advance correction.
PERM-07: command80%, actual stuck20%; Safety detects physical tracking failure only after measured actuator/fault channel arrives, never from hidden ACTUAL. A separately configured acknowledgment timeout may flag communication uncertainty but must not assert an observed stall.

## Revision log

2026-09-18, 1.1: added measured actuator/equipment permissions and channel meanings; legal tracking/anti-windup path; PERM-06/07. Contract07 remains unchanged because its MeasurementTransform rule already supports this path.
