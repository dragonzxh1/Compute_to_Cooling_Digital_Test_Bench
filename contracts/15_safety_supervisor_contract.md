Revision: 1.1
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 15 — Safety Supervisor Contract

## Inputs / Outputs

Input: qualified measured/local protection channels, measured actuator/equipment feedback authorized by14, required channel health, estimator validity, proposed targets, explicit hardware inventory and protection policy. No hidden truth; ACTUAL actuator/status values reach Safety only through Measurement Pipeline.
Output: SafetyState, restrictive actuation envelope, FF enable, reason codes, DERATE_REQUESTED event and optional synthetic load cap request; PLC owns final commands.
States: NORMAL, FF_DISABLED, DEGRADED, DERATE_REQUESTED, PROTECTED, FAULT.
State record: entered_at, triggering_channels, request_id, ack_time, reason, latch, recovery_since. Severity precedence FAULT > PROTECTED > DERATE_REQUESTED > DEGRADED > FF_DISABLED > NORMAL; active reasons retained, so recovering one does not clear others.

## Required profile / frozen generic timing policy

Separate thermal operating/control, derate/hard thresholds and clear thresholds below, minimum branch flow, maximum pressure, fallback dp/T, actuator limits, safe-action table by fault type and optional standby inventory are REQUIRED provenance-bearing configuration. No real GB300 values guessed. Missing any applicable item -> CONFIG_INVALID before run. “Safe command” cannot mean always maximum pump: pressure fault can require reduction/shutdown.
Generic policy: stale if worst-case sample age>1.0s; max averaging window1.0s; FF confidence threshold0.8; coverage=1.0 for required domains; minimum dwell2s for FF_DISABLED/DEGRADED/DERATE_REQUESTED/PROTECTED; recovery requires5 DISTINCT consecutive valid samples spanning>=2s and all restrictive reasons cleared. Severe escalation never waits for dwell.
Flow hysteresis remains recovery>=1.05×min_flow; pressure recovery<=0.95×max_pressure. Thermal recovery uses independent configured derate/hard clear thresholds below, replacing the single limit−1K rule. These numerical policies are research assumptions, not OEM-safe settings. Profile must have feasible recovery region; otherwise CONFIG_INVALID.
Synthetic load response latency default0.2s, protected acknowledgment deadline1.0s; recovery cap ramp10% offered full-scale per second after safe recovery, per-leaf reference full-scale frozen at registration. No real IT command issued. Request cap uses registered per-leaf derate_fraction ∈[0,1] (required, not guessed), emergency hard-trip cap0 only where explicitly enabled in policy. Never compute derate from auditor truth.

## Thermal threshold hierarchy

Required per-device fields, each with ParameterRecord provenance, unit, temperature-definition/measurement-channel mapping and calibration_status:

| Field | Meaning |
|---|---|
| thermal_operating_limit | Performance/headroom reference only; legacy benchmark thermal_limit_i or limit_i in08–10 is an alias for this role, never a protection trigger |
| T_control_target / RequiredHeadroom | Normal thermal objective; when headroom-based, T_control_target=thermal_operating_limit−RequiredHeadroom |
| thermal_derate_threshold (T_derate) | Qualified measured T>=threshold triggers DERATE_REQUESTED |
| thermal_hard_protection_threshold (T_hard_protection) | Qualified measured T>=threshold or qualified mapped hardware protection signal triggers configured hard action |
| derate_clear_threshold | T<=this value clears thermal derate reason, subject to dwell/recovery; strictly below T_derate |
| hard_clear_threshold | T<=this value clears thermal hard reason, subject to signal deassertion/dwell/reset policy; strictly below T_hard_protection |

Preflight requires T_control_target < T_derate < T_hard_protection, finite values, consistent units and compatible temperature meanings. This is a per-device same-temperature-definition ordering; an unverified die/hotspot/package conversion cannot establish it. Required thresholds/clear values remain CALIBRATION_REQUIRED absent reviewed OFFICIAL/DATASHEET/MEASURED/CALIBRATED evidence. No numerical GB300 temperature or hysteresis is supplied.

RequiredHeadroom and thermal_operating_limit are performance quantities; changing a benchmark target does not assign or change either protection threshold/clear threshold. If a proposed target violates ordering, reject that profile, do not move protections to make it fit. Existing operating-limit violations in08 remain logged PERFORMANCE events; a thermal DERATE_REQUESTED trigger requires T_derate or a separately declared nonthermal protection cause. No automatic alias from operating limit to derate/hard.

Derate and hard latches clear independently using their respective channel-qualified clear thresholds and recovery windows. Clearing hard does not clear a still-active derate reason. PROTECTED remains restrictive while derate is active; FAULT still requires explicit reset. Target tracking deadband, if used, is a separate control parameter and does not clear protection latches. The previous Generic1K margin may be selected explicitly for an individual layer only with its own ENGINEERING_ASSUMPTION provenance; there is no shared implicit thermal-clear default.

Future Phase7 may map operating temperature target, thermal slowdown/derate indication, thermal violation counter and hardware protection/shutdown indication after validating target DCGM/NVIDIA version, entity, units and semantics. A cumulative violation counter is not a current hard-trip boolean or an inferred temperature threshold. Unknown field meaning cannot trigger a fabricated OEM interpretation; follow required-channel invalidity policy.

## Transitions (guards use measured signals)

| State / enter condition | Actions | Exit / recovery |
|---|---|---|
| NORMAL: all required conditions qualified at startup or recovered | FF allowed, local PLC active | any higher guard immediately |
| FF_DISABLED: IT stale/missing/low-confidence/incomplete or estimator MODEL_OUT_OF_RANGE | reject new FF, withdraw existing increment through PLC constraints; local FB continues | distinct valid recovery samples+dwell and no higher reason -> NORMAL |
| DEGRADED: local sensor fault with configured redundant measurement, unavailable pump capacity, absent standby, or infeasible target | FF off; named local fallback/valid alternate sensor; record CAPACITY_LIMITED as applicable | fault clears+recovery/dwell -> FF_DISABLED for qualification; persistent unsafe condition -> request/trip |
| DERATE_REQUESTED: qualified measured T>=T_derate and below hard threshold, or persistent insufficient flow/capacity while running | log request with ID; FF off; execute configured cooling restriction; PERFORMANCE suppresses IT actuation | SAFETY ack of cap -> PROTECTED; absent ack past deadline -> FAULT; PERFORMANCE no ack expected, remains until applicable derate_clear and other reasons/recovery clear |
| PROTECTED: SAFETY cap acknowledged, explicit interlock acknowledged, or T>=T_hard_protection / active hardware protection signal whose fault/action table selects PROTECTED | FF off; enter restrictive state immediately on qualified hard trigger; issue configured action and separately track action acknowledgment; do not claim action already succeeded | independent hard/derate clears, signal deassertion and dwell permit recovery; cap fully released -> DEGRADED/FF_DISABLED; missing required action ack -> FAULT |
| FAULT: no valid critical local measurement/alternate; hard thermal/signal trigger whose fault/action table selects FAULT; unsafe overpressure or measured actuator/ack failure | FF off; execute fault-specific safe action; request derate if applicable; PLC safety processing continues | latched; explicit reset, all applicable independent thermal clears, valid sensors and recovery/dwell>=2s -> FF_DISABLED; no automatic reset |

Startup without enough qualified IT samples begins FF_DISABLED. Without local critical sensors and no qualified alternate begins FAULT. FF validity recovery cannot override a persistent flow/pressure issue. FF out-of-range ESTIMATOR disables FF; PHYSICAL plant out-of-range ends valid simulation rather than pretending safety restored its validity.
Hard triggers take precedence over derate triggers at the same timestamp, without waiting for lower-state dwell. The required fault/action table selects exactly one hard destination PROTECTED or FAULT per cause, action, acknowledgment semantics/deadline and reset/latch policy; a missing/ambiguous entry is CONFIG_INVALID. Numeric hard triggers must refer to arrived qualified measurements. Hardware digital channels likewise use modeled availability and quality; Safety cannot inspect hidden equipment state.
No implicit N+1: switch only to inventory-declared standby with its startup/transfer delay; no standby -> DEGRADED/CAPACITY_LIMITED or FAULT according to remaining measured safety. Leak/cavitation not physically modeled here; hardware alarm can still impose a prescribed interlock without asserting simulated leak physics.

## Actuation and experiment isolation

Infeasible proposed setpoint: finite out-of-range clamp to explicit limits, nonfinite/incompatible target reject, reason logged. Command bounds/ramp enforce before actuation; actual physical flow/temperature not clipped. Pressure safety takes priority over thermal cooling request; simultaneous unsatisfiable requirements log capacity insufficiency and request derate.
FF failure never stops PLC. Local feedback continues when sensors valid; when invalid, PLC still runs configured interlock/safe-command processing, not a fictitious valid PID.
PERFORMANCE never executes load cap; request-only logged, no missing load-ack fault for deliberately suppressed requests. Cooling hardware interlocks still apply and can make thermal outcome worse. SAFETY_PROTECTION alone changes synthetic delivered IT. Both share exact state/threshold policy with experiment-type actuation gate08.
This suppression also applies to hard-protection IT shutdown/zero-cap requests in PERFORMANCE: log would-be action and selected protection state without changing applied IT power. Any actual required cooling-action acknowledgment is still checked. PROTECTED as a selected restrictive state does not assert a suppressed IT shutdown occurred. If physics leaves its valid domain, stop scoring INVALID rather than invent protected temperatures.

## Acceptance specifications

SAFE-01: stale repeated sample disables FF without stopping valid PLC feedback.
SAFE-02: recovery requires distinct samples/hysteresis/dwell; escalation immediate.
SAFE-03: no standby cannot magically switch pumps; capacity limitation explicit.
SAFE-04: pressure and thermal conflict uses fault table/derate, not fake safe true values.
SAFE-05: PERFORMANCE suppression never edits trace; SAFETY logs request/activation/duration/curtailed J/recovery; missing ack triggers FAULT.
SAFE-06: FAULT cannot silently auto-reset; control timing follows architecture same-tick priority.
SAFE-07: with other channels healthy and no independent fault, T_control_target<T<T_derate permits normal feedback without thermal derate.
SAFE-08: T>=T_derate and T<T_hard_protection triggers DERATE_REQUESTED, including equality; PERFORMANCE logs only, SAFETY applies08.
SAFE-09: T>=T_hard_protection or validated active hardware protection signal selects PROTECTED/FAULT per registered fault/action table; independent clear thresholds and latches are exercised on recovery.
SAFE-10: change RequiredHeadroom and verify protection/clear thresholds unchanged; inconsistent new control target fails preflight rather than modifying thresholds.

## Revision log

2026-09-18, 1.1: separate operating/control, derate and hard protection semantics; independent recovery thresholds; measured equipment feedback; hard-action priority and performance suppression; SAFE-07–10. Existing nonthermal numeric policies retained. Benchmark limit aliases are defined here so08–10 need no edits.
