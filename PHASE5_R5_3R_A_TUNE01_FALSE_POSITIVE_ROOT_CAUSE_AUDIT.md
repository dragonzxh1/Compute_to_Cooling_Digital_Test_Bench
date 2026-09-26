# Phase 5R5.3R-A — TUNE-01-load False-Positive Root-Cause Audit

## Decision

`ROOT_CAUSE_CLASS = FROZEN_SEMANTICS_FALSE_POSITIVE_ON_VALID_IN_DOMAIN_TRACE`

`PHASE5_R5_3R_A_GATE_STATUS = TUNE01_FALSE_POSITIVE_ROOT_CAUSE_IDENTIFIED`

R5.3R stopped because its attempted tracking port reported `DEGRADED / ACTUATOR_TRACKING_SUSPECTED` at 29.6 s and `FAULT / ACTUATOR_TRACKING_CONFIRMED` at 31.0 s during `TUNE-01-load`. The unchanged historical test [`test_closed_loop_load_and_conservation`](v0_2/tests/control/test_phase5_feedback.py) explicitly requires **no FAULT**; it does **not** explicitly forbid temporary DEGRADED. The audit did not modify production Safety, frozen tracking semantics, profile, controller, sensor, pump, plant, scheduler, scenario or Contract 15A.

## Sources and released trace

All R5.3R failed-gate, R2R gate, frozen-profile/Contract 15A and restored-production hashes matched the [preregistration](phase5_r5_3r_a_tune01_false_positive_audit_registration.json). The source-hash inventory is in [machine evidence](phase5_r5_3r_a_tune01_false_positive_audit_evidence.json). The unchanged scenario is `run_scenario("TUNE-01-load")`: fixed initial fixture, registered 10-second load increase, 0.2-second physical/PLC/Safety tick, 0.2-second sensor sampling, zero local sensor release delay, and frozen pump delay/lag/ramp.

The immutable [released-input trace](phase5_r5_3r_a_tune01_released_input_trace.json) has SHA-256 `a63c5a413e3a3b02d3f86a4f6c6d52bad615272916f664722a452ff5be25fd61`. It contains 155 causal Safety-tick records from 0.2 through 31.0 s. Each has the *previously issued* PLC command value/ID/timestamp; latest released measurement speed, ID, sample/release timestamps, age and quality; released DP/flow; and unchanged-baseline Safety state. It contains no raw ACTUAL or true plant state. **Provenance limitation:** this is a deterministic reconstruction from the unchanged baseline, not an archived byte-for-byte dump of the failed port. It covers only the pre-first-FAULT prefix; post-FAULT PLC commands necessarily diverge. Sparse failed-trial values recorded at 29.6 and 31.0 s agree, and the trial DEGRADED state added no envelope restriction before first FAULT. Command/envelope provenance IDs from the failed run were not archived, though IDs are not consumed by the qualifier.

The explicit frozen domain checks passed: command 0.7–0.86023 and released measured speed 0.7–0.85450 lie within the 0.3–0.9 profile speed domain; pump delay 0.2 s, lag 1.0 s, ramp 0.2/s, sensor period 0.2 s, release delay 0, max age 1.0 s and causal sample/release ordering match. The profile does not separately specify a continuous-command applicability bound or extra command-magnitude upper bound; those entries are `NOT_SPECIFIED`, not proven out-of-domain. No threshold sweep was performed.

## Same-trace replay and first-divergence audit

The frozen `CumulativeTrackingQualifier` replayed the trace unchanged. An in-memory *functional reconstruction* of the previously attempted mechanical production copy was built from the frozen R/R1 source using the recorded class/import transformations; its deleted source file is unavailable for a bytewise hash comparison. Across 155 ticks and 18 comparison fields (state, epoch/watch IDs and starts, qualified anchor, net demand/class, direction, response opening, progress, suspicion/confirmation and validity), the replay found **zero mismatches**. Consequently there is **no first divergent tick** in the comparable prefix; the table below is a bounded window around the first erroneous suspicion, not a fabricated divergence. The full 18-row window is in the evidence JSON.

| Time (s) | Released cmd | Qualified anchor | Net demand | Measured speed | Valid | Offline / reconstructed port | Response open | Qualified progress |
|---:|---:|---:|---:|---:|---|---|---|---|
| 29.0 | 0.84719 | 0.70000 | 0.14719 | 0.84157 | Yes | STEADY / STEADY | No epoch | No |
| 29.2 | 0.85621 | 0.70000 | 0.15621 | 0.84259 | Yes | HANDOFF_PENDING / same | No | No |
| 29.4 | 0.85451 | 0.70000 | 0.15451 | 0.84506 | Yes | HANDOFF_PENDING / same | Yes | No |
| 29.6 | 0.85258 | 0.70000 | 0.15258 | 0.84677 | Yes | SUSPECTED / same | Yes | No |
| 30.8 | 0.85913 | 0.70000 | 0.15913 | 0.85348 | Yes | SUSPECTED / same | Yes | No |
| 31.0 | 0.86023 | 0.70000 | 0.16023 | 0.85450 | Yes | CONFIRMED / same | Yes | No |

The replay's first `TRACKING_FAULT_SUSPECTED` is **29.6 s** and first `TRACKING_FAULT_CONFIRMED` is **31.0 s**, matching the recorded attempted-production Safety transitions. Contract 15A maps those states to DEGRADED and FAULT exactly; the false positive is therefore upstream of the Safety mapping. The historical raw `abs(command−measured)>0.15` branch was removed from authority in the attempted port; the causal gap at 29.6 s was only about **0.00581**, so that old branch cannot explain this event.

## Causal mechanism

The qualified command anchor initialized at **0.7** at 0.2 s and never advanced during smooth, healthy command following. Continuous PLC commands and measured speed rose together toward about 0.85. At 29.2 s the net command from the old anchor first exceeded the frozen materiality rule, opening epoch/watch 1. The epoch used command anchor **0.7** but measurement anchor **0.8425916**, the *current* speed at 29.2 s. That compares expected movement for the full ~0.156 command increase since 0.7 against measured movement only *after* the new 0.8426 measurement anchor. These are different reference intervals.

At 29.6 s the frozen expected displacement was **0.05030**, while measured directed progress after the epoch's measurement anchor was **0.00418** (ratio **0.083**, below the frozen 0.5 suspicion ratio). Yet the released command–measured gap was only **0.00581** and measured speed was rising in the commanded direction. At 30.8 s measured progress exceeded the 0.01 observability floor (**0.01089**), but the ratio remained **0.0857** because expected movement from the stale command anchor had grown to **0.12700**. At 31.0 s expected was **0.13375**, measured progress **0.01191**, ratio **0.0890**; the frozen confirmation rule counted the second qualifying deficient sample and latched CONFIRMED. The watch retained its 29.0 s start because this mismatched ratio never credited healthy motion. Response opened at 29.4 s as calculated by both engines; no one-tick command/sample/release shift was found in the reconstructed prefix.

This is a reference-frame/continuous-command applicability defect in the frozen semantic rules, not evidence of a stuck pump. The audit does not propose or implement a revised anchor rule.

## Forensic physical view and limits

**FORENSIC NON-CAUSAL VIEW — never supplied to either qualifier:** from 29.2 to 31.0 s raw actuator speed rose **0.01191**, released measured speed rose **0.01191**, flow rose **0.003262 kg/s**, and released DP rose **1061 Pa**. Thus pump, measurement, flow and pressure all moved in the expected direction. [The figure](docs/results/phase5_r5_3r_a_tune01_false_positive_audit.png) separates causal inputs from this true-state panel.

Ten replays of the immutable trace had identical result hashes and transitions; all 155 prefix replays matched the corresponding full-replay prefix. The deleted attempted-production file and original full failed-run trace cannot be bytewise recovered. The functional reconstruction, recorded source transformation and trial transition timestamps support the root class, but this evidence must not be described as a byte-for-byte production capture or hardware validation.

**Next phase:** Phase 5R5.2.1R4 (or equivalent) should explicitly revise and validate continuous-command tracking semantics and their applicability, with new preregistered nominal/stuck cases. Do **not** restart R5.3R against the current frozen semantics. No fix, recalibration, candidate baseline, R5.4, Phase 6, Git commit or push was performed here.
