# C2C-DTB V0.2 — Phase 5 Revision 1 actuation ownership report

Date: 2026-09-21  
**PHASE5_R1_GATE_STATUS = PASS — awaiting user freeze review**

This revision corrects command ownership and adds deterministic provenance. It does not optimize
control performance, change plant/actuator physics, change gains or thresholds, restart Phase 5.1,
or implement Phase 6/feedforward.

## 1. Reason for revision and original defect

Phase 5.1 found that the original scheduler passed `SafetyDecision.forced_speed` into the PLC but
then selected that Safety value again at the actuator boundary. Equal numerical values did not
establish PLC sole-writer ownership. The original baseline and the historical BLOCKED evidence are
retained unchanged as the reviewed history.

## 2. Frozen contract requirement and pre-change integrity

Contracts 14 and 15 require Safety to own restrictive constraints and the PLC to own the final
actuator command. The mandatory pre-change verification passed:

| Artifact | SHA-256 | Result |
|---|---|---|
| Original tuning registration | `9a937de41a8466f4a6f33a06de899929576a3653217901084a2fb7675f0fe00f` | PASS |
| Original baseline file | `b14281edc630b49de1ddcfbff1894cfe129f75e1c6b891786dbeae02de73b033` | preserved |
| Original control core | `092b3ff035da69a95294543cdf716e4a025f506ab213543d1a640ed1d10db6d8` | PASS before revision |

`phase5_r1_revision_registration.json` was created before code modification. Frozen contracts were
not changed.

## 3. Files changed by Revision 1

| Classification | Files |
|---|---|
| EXPECTED_R1_CHANGE | `control/intent.py`, `control/inner_loop.py`, `safety/supervisor.py`, `plant/controlled_loop.py`, `actuators/pump.py`, `measurement/local_sensor.py` |
| TEST/EVIDENCE | Phase 5R1 audit/evidence scripts, ownership tests, historical defect fixture, R1 JSON artifacts |
| DOCUMENTATION | This report, root/V0.2 READMEs, GitHub audit |
| UNEXPECTED | none; no thermal, hydraulic, coolant, CDU/HX/FWS or frozen-contract file changed |

## 4. Before and after flow

```text
BEFORE                                      AFTER
SafetyDecision                             SafetyEnvelope
      ↓                                          ↓
PLC                                         PLC cycle
      ↓                                          ↓
scheduler chooses forced_speed again       PLC ActuatorCommand
      ↓                                          ↓
Actuator                                    Actuator
```

Exact safe-speed policies are expressed as equal minimum/maximum speed bounds. Hard events may
trigger a same-timestamp emergency PLC cycle, but Safety never constructs or submits an actuator
command.

## 5. Ownership table

| Object | Producer | Consumer | Sole write owner |
|---|---|---|---|
| FB intent | Outer FB | Supervisor | Outer FB |
| Accepted target | Supervisor | Safety/PLC | Supervisor |
| Safety envelope | Safety | PLC | Safety |
| PLC cycle | PLC | Audit | PLC |
| Actuator command | PLC | Actuator | PLC |
| Actual actuator state | Actuator | Plant/Measurement | Actuator |
| Measured actuator state | Measurement | PLC/Safety | Measurement |

## 6. SafetyEnvelope and PLC command ownership

`SafetyEnvelope` records ID/time/state, DP and speed bounds, fallback DP, shutdown flag, reasons,
source measurement IDs, derate request ID, validity and accepted-target ID. The PLC applies this
envelope to the supervisor-owned target and creates both `PLCCycle` and `ActuatorCommand`.

The actuator accepts a typed `ActuatorCommand` only and asserts `producer_module == "PLC"` plus a
non-empty PLC cycle ID. A float, Safety-produced command or missing lineage fails with
`ACTUATION_OWNERSHIP_VIOLATION` or `CONFIG_INVALID`.

## 7. End-to-end runtime provenance

The trace now carries:

`fb_intent_id → accepted_target_id → safety_envelope_id → plc_cycle_id → actuator_command_id → actuator_state_id → measurement_record_id`, with `hydraulic_solution_id` on the measurement.

Every typed record includes timestamp, producer and source IDs. Not-applicable startup links are
explicit rather than fabricated.

## 8. Static and runtime ownership audits

The AST audit found exactly one production constructor for `ActuatorCommand`:
`v0_2/control/inner_loop.py`. The sole actuator call argument is
`held_plc_result.actuator_command`; Safety, Supervisor and Outer FB construct no actuator command,
and the actuator imports no `SafetyDecision`.

Runtime audits exercised normal, pressure restriction, PROTECTED and FAULT paths. All normal and
fault-run commands reported `producer_module = PLC`; provenance links resolved completely. Sensor
FAULT issued the Safety envelope, emergency PLC cycle and command at the same timestamp, with no
direct Safety write and no one-tick gap.

## 9. Numerical behavior preservation

| Scenario | Metric | Original Phase 5 | R1 | Difference | Expected |
|---|---|---:|---:|---:|---|
| Historical combined holdout | Peak T (K) | 319.440880113 | 319.440880113 | 0 | precision-equivalent |
| Historical combined holdout | Temperature IAE (K·s) | 449.733773533 | 449.733773533 | 0 | precision-equivalent |
| Historical combined holdout | DP IAE (Pa·s) | 412706.839116 | 412706.839116 | 0 | precision-equivalent |
| Historical combined holdout | Pump energy (J) | 1000.416989441 | 1000.416989441 | 0 | precision-equivalent |
| Historical combined holdout | Saturation (s) | 36.8 | 36.8 | 0 | precision-equivalent |
| Pressure conflict | Final speed | 0.5 | 0.5, producer PLC | 0 | ownership-only change |
| PROTECTED | Final speed | 0.5 | 0.5, producer PLC | 0 | ownership-only change |
| Sensor FAULT | Final speed | 0.5 | 0.5, producer PLC | 0 | ownership-only change |

All compared historical holdout temperature, DP, flow, commanded/actual speed, pump-energy,
mass/energy residual and Safety-state samples matched exactly on the same time grid. FWS and branch
training metrics also remained unchanged. PID equations and measured-feedback anti-windup were not
changed and their regression remains passing.

## 10. Candidate re-selection

The original training scenarios, candidates and selection priority were reused without holdout
input:

| Stage | Candidate | Feasibility failed | Primary aggregate | Control TV | Pump energy (J) |
|---|---|---:|---:|---:|---:|
| Inner | `inner_a` | false | 445959.536646 | 0.703230 | 1661.728306 |
| Inner | `inner_b` | false | 303030.139505 | 1.116001 | 1743.514536 |
| Outer | `outer_a` | false | 349.690238 | 1.116001 | 1743.514536 |
| Outer | `outer_b` | false | 349.543686 | 1.997534 | 2045.887924 |
| Outer | `outer_c` | false | 349.420824 | 2.576807 | 2302.041321 |

Selection remains `inner_b + outer_c`; it did not change after the ownership correction.

## 11. Historical holdout, convergence and stability

`HOLDOUT-01-combined` is explicitly a **HISTORICAL HOLDOUT REGRESSION**, not a new blind holdout and
not nominal-settling evidence. Every reported metric and every selected physical trace sample has
zero difference from the original Phase 5 evidence.

The 0.2/0.1/0.05 s convergence gate remains PASS. Fine-pair differences are 0.004577 K peak
temperature, 0.461399 K·s IAE, 95.626188 Pa·s DP IAE and 0.379265 J pump energy. Ten consecutive
runs produced the identical hash `58e730a8ab64fb33b716fbe12ab43a4d7b2b5682e72b85ea8a0d6e6d97acb75d`;
retained memory remained bounded.

## 12. Full regressions

- V0.2 Phase 5R1/5/4.1/4/3 combined suite: 178 passed.
- V0.1 suite: 72 passed.
- Ruff: all checks passed with cache disabled.
- Original Phase 5 registration/baseline byte hashes: unchanged after revision.

## 13. New baseline and limitations

The new artifact is `phase5_r1_feedback_baseline.json`:

- new control-core SHA-256: `b79eaf9c7cdc2665856db87bd6a59b900eb2f31efb0b3a94112bbbe476152579`
- selection evidence SHA-256: `fe9f5e78cbf27197ffbe61ea68f7b5ab76264ae6f864fa0494b6fdc6d5c1c6d5`
- new baseline file SHA-256: `24a0198daf1e823bc6e8ff087e9a2d0491391afa3d5a4aed7b75a8a39800920d`
- supersedes original baseline SHA-256: `b14281edc630b49de1ddcfbff1894cfe129f75e1c6b891786dbeae02de73b033`

This PASS certifies only ownership correction, provenance and generic numerical preservation. It
does not qualify nominal settling, GB300/OEM behavior, production PLC safety or hardware.

## 14. Final self-review and gate

Old files byte-identical: YES. Historical BLOCKED evidence preserved: YES. Safety constructs or
writes ActuatorCommand: NO. PLC sole producer: YES. Actuator accepts PLC command only: YES. Safety
priority preserved: YES. Hard/fault path through same-tick PLC: YES. Provenance complete: YES. Gains,
actuator physics, plant physics, candidate grid and selection policy changed: NO. Selection remains
inner_b/outer_c: YES. Historical holdout used for tuning: NO. Truth/raw-ACTUAL/future access added:
NO. Phase 5.1 restarted: NO. Phase 6/feedforward started: NO.

**PHASE5_R1_GATE_STATUS = PASS. Blocking issues: none within Revision 1 scope. STOP; await user
freeze review. Phase 5.1 remains BLOCKED/pending an explicit restart authorization.**
