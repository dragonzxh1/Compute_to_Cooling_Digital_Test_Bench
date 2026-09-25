# C2C-DTB V0.2 — Phase 5.1 frozen feedback baseline qualification

Date: 2026-09-21  
**PHASE5_1_GATE_STATUS = BLOCKED — ACTUATION_OWNERSHIP_CONTRACT_VIOLATION**

This review qualifies the already-frozen Phase 5 generic numerical baseline. It does not
retune the controller, change the plant, claim GB300/OEM performance, or start Phase 6.

## 1. Baseline integrity

The mandatory pre-change hash check passed:

| Artifact | Expected | Actual | Result |
|---|---|---|---|
| `phase5_tuning_registration.json` | `9a937de41a8466f4a6f33a06de899929576a3653217901084a2fb7675f0fe00f` | same | PASS |
| Frozen control-core digest | `092b3ff035da69a95294543cdf716e4a025f506ab213543d1a640ed1d10db6d8` | same | PASS |
| `phase5_feedback_baseline.json` file digest | n/a | `b14281edc630b49de1ddcfbff1894cfe129f75e1c6b891786dbeae02de73b033` | recorded |

Neither frozen JSON file nor any file included in the control-core digest was modified.

## 2. Ownership audit and blocker

Contracts 14 and 15 assign Safety ownership of a restrictive envelope/derate request and
assign the PLC sole ownership of the final actuator command. The frozen implementation does
pass `decision.forced_speed` into `LocalDPPLC.update`, but the actuator call site does not use
the PLC return exclusively:

```python
held_plc_command = plc.update(..., forced_speed=decision.forced_speed)
actuator.command(
    decision.forced_speed if decision.forced_speed is not None else held_plc_command,
    now,
)
```

Therefore Safety's `forced_speed` is selected directly at the actuator boundary whenever it
is present. The numerical value may equal the PLC return, but value equality cannot prove the
required sole-writer ownership or provide the required `plc_cycle_id` → `actuator_command_id`
provenance. The current row schema also lacks the required identifiers
`fb_intent_id`, `accepted_target_id`, `safety_envelope_id`, `plc_cycle_id`,
`actuator_command_id`, and `actuator_state_id`.

The executable read-only audit is
`python -m v0_2.examples.phase5_1_ownership_audit`; its machine-readable result is
`docs/results/phase5_1_ownership_audit.json`.

## 3. Qualification disposition

Per the Phase 5.1 task contract, this is a frozen-baseline defect. It cannot be silently
refactored while retaining the Phase 5 control-core digest. Qualification stopped before:

- creating or freezing `phase5_1_qualification_registration.json`;
- selecting a nominal load from the open-loop feasibility grid;
- executing nominal closed-loop regulation or generating its six-panel figure;
- reusing the combined stress holdout as qualification evidence;
- running the Phase 5.1 closed-loop dt/conservation qualification matrix.

The existing `HOLDOUT-01-combined` result remains historical Phase 5 capacity-stress evidence.
It is not nominal-settling evidence and was not changed or rerun after this hard blocker.

## 4. Required resolution

A future, explicitly authorized baseline revision must replace the direct Safety speed command
with a restrictive Safety envelope/request, make the PLC the sole producer of the final
actuator command, add end-to-end command provenance, register the changed baseline, and then
restart Phase 5.1 from the hash gate. That work is intentionally outside this qualification.

**STOP. Phase 5 implementation evidence remains available, but Phase 5.1 qualification is
BLOCKED and not ready for freeze review. Phase 6 has not started.**
