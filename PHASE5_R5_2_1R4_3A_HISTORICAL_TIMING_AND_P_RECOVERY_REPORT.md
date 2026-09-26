# Phase 5R5.2.1R4.3A — historical timing and P-input recovery

## 1. Purpose and scope

Evidence adjudication only. No R4.3 engine, production Safety, controller,
plant, profile, Contract 15A, or historical expectation was changed. No Git
commit/push and no Phase 6. Numerical fixtures are development evidence, not
hardware/OEM/GB300 validation.

## 2. Source inventory and integrity

The executable S input source is `build_cases()` in
`v0_2/examples/phase5_r5_2_1r_validation.py`, using frozen R5.2 and R5.2.2
evidence. It yields S1–S16 plus S16 variant (some IDs have normal/stuck or
bidirectional variants). The old exact S acceptance is `acceptance()` in that
file. The cumulative historical replay uses
`v0_2/examples/phase5_r5_2_1r1_validation.py`. The C9R generator and expected
anchor conditions are in `phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json`
and `v0_2/examples/phase5_r5_2_1r1a_validation.py`. The R4 preregistration
lists P1–P20 purposes but has no P-specific executable fixture payloads.
R4 evidence explicitly says the P matrix was **not executed** after the early
stop. A repository-wide source/artifact search, available attachment prompts,
and available Git history did not locate a separate P1–P20 capture or generator.
Git history on this checkout only reaches the older Phase 4.1 publication;
later local files are not in a historical Git commit.

Machine evidence records all audited source hashes. The R4.3 engine hash equals
the preceding full-history evidence hash:
`04b460267a2fc665b2f600ffc8ec4eaa0bda857d87f7ba83706a4f9ca9be3cbb`.
All R4-registered production-source hashes match. Contract 15A remains at
`b741a05925a043706dbdc93351faf37fdbd6f1d41ad22360143c8184dd08e280`.

## 3–5. S3/S14: original intent, complete timeline, same-sample collapse

S3 and S14 use the **same frozen `DELAY_0_6` input trace**. Their old acceptance
requires an ordered `TRACKING_FAULT_SUSPECTED → TRACKING_PROGRESS` public state
sequence and no confirmed fault. This is explicit executable acceptance, not
merely a prose example. Neither case prescribes an exact nanosecond for the
progress state: the sequence is order-normative, not exact-time-normative.

| Time (s) | Command | Released speed | Valid | Old public state | R4.3 public state | Old progress | R4.3 qualified progress | Watch/evidence |
|---:|---:|---:|:---:|---|---|:---:|:---:|---|
| 0.0 | 0.648 | 0.9000 | yes | HANDOFF_PENDING | HANDOFF_PENDING | no | no | watch starts at 0; evidence 0 |
| 0.2 | 0.648 | 0.9000 | yes | HANDOFF_PENDING | HANDOFF_PENDING | no | no | same watch |
| 0.4 | 0.648 | 0.9000 | yes | TRACKING_FAULT_SUSPECTED | TRACKING_FAULT_SUSPECTED | no | no | same watch; evidence 0 |
| 0.6 | 0.648 | 0.9000 | yes | TRACKING_FAULT_SUSPECTED | TRACKING_FAULT_SUSPECTED | no | no | same watch; evidence 0 |
| 0.8 | 0.70344 | 0.8600 | yes | TRACKING_FAULT_SUSPECTED | TRACKING_FAULT_SUSPECTED | no | no | same watch; evidence 0 |
| 1.0 | 0.752777 | 0.821571 | yes | TRACKING_PROGRESS | STEADY_TRACKING | yes | yes | both resolve the watch; no fault |
| 1.2 | 0.792710 | 0.790108 | yes | STEADY_TRACKING | STEADY_TRACKING | prior | prior | no unresolved watch |

Both old and R4.3 begin with an unresolved downward obligation from the first
valid command/speed pair. Neither has a resolved command anchor before the
response. At 1.0 s, R4.3 compares valid measured displacement against its
matched startup checkpoint, sets `qualified_progress=true`, resolves the watch,
and atomically establishes the resolved command/measurement pair. No later
sample is consulted, no qualified fault evidence is erased (the count is 0),
and no grace is reset. The old engine exposes `TRACKING_PROGRESS` at 1.0 s and
waits until 1.2 s to expose `STEADY_TRACKING`. The R4.3 decision is a causally
valid **same-sample progress + resolution**, but it omits a public temporal
milestone required by the frozen acceptance. `TRACKING_PROGRESS` is not merely
an invisible implementation event: Contract 15A maps it as an internal state
consumed by Safety, and the old S acceptance checks its sampled presence.
On these traces, both `TRACKING_PROGRESS` and `STEADY_TRACKING` map to NORMAL,
so this is not evidence of a different Safety severity; it is still an exact
historical state-sequence regression.

| Case | Historical source | Exact expected sequence | Timing normative? | R4.3 sequence | Verdict |
|---|---|---|---|---|---|
| S3 | `build_cases()` → `DELAY_0_6`; old `acceptance()` | SUSPECTED → PROGRESS (the old trace subsequently reaches STEADY) | order only | SUSPECTED → STEADY, with qualified progress on the steady sample | `HISTORICAL_REGRESSION` |
| S14 | same frozen trace and acceptance | SUSPECTED → PROGRESS (the old trace subsequently reaches STEADY) | order only | SUSPECTED → STEADY, with qualified progress on the steady sample | `HISTORICAL_REGRESSION` |

`S3_TIMING_VERDICT = HISTORICAL_REGRESSION` and
`S14_TIMING_VERDICT = HISTORICAL_REGRESSION` for the *existing formal gate*.
The narrower mechanism is `VALID_SAME_SAMPLE_STATE_COLLAPSE`; that does not
authorize relaxing the historical public-state oracle. No tests or candidate
semantics were changed to make these pass.

## 6–8. C9R anchor timing, suffix, and normativity

C9R is a separate in-domain replacement for invalid original C9. Its frozen
generator is deterministic: command stages 0.35→0.51 and 0.51→0.67, sampled
every 0.2 s. The registration makes first and second *demand trigger* times
0.6 and 3.4 s exact. Its anchor criteria require a qualified epoch, no premature
advance, correct A→B→C values, and advancement after each trigger; they do
**not** require resolution at exactly 1.2 or 4.0 s. Those times appear in the
old R1a output and are incidental to its two-sample progress/steady sequence.

| Anchor | R1a time, command | R4 time, paired measurement | R4.1 time | R4.3 time, paired measurement | Delta | Cause | Observed effect |
|---|---|---|---|---|---:|---|---|
| A | 0.0 s, 0.35 | 0.0 s, 0.35 | 0.0 s | 0.0 s, 0.35 | 0 | directly observed initial steady pair | same command baseline |
| B | 1.2 s, 0.51 | 1.0 s, 0.399920 | 1.0 s | 1.0 s, 0.399920 | −0.2 s | `SAME_SAMPLE_RESOLUTION` | old PROGRESS vs new STEADY at 1.0 s |
| C | 4.0 s, 0.67 | 3.8 s, 0.553226 | 3.8 s | 3.8 s, 0.553226 | −0.2 s | `SAME_SAMPLE_RESOLUTION` | old PROGRESS vs new STEADY at 3.8 s |

R1a has no stored paired measurement anchor; its measured speeds at the old
anchor events are 0.419874 and 0.574393. They must **not** be mistaken for an
old paired-reference field. At 1.0 and 3.8 s, the first valid sample satisfying
the old progress condition also satisfies R4's frozen tracking-error tolerance.
R1a publishes PROGRESS on that sample and resolves one sample later. R4's
paired engine resolves immediately in the qualified branch; R4.1 and R4.3
inherit that behavior. This is neither scheduler ordering, recovery, nor a new
R4.3 startup change. The paired reference is advanced atomically; its new
measurement component is from the same valid tick as the command component.

For the unchanged C9R trace, no version confirms a tracking fault. Watch age
starts at the same 0.6/3.4 s demands, and the watch is resolved at 1.0/3.8 s
when real qualified progress is observed. The public state differs at each
early resolution tick (old PROGRESS, R4.3 STEADY), but both map to NORMAL under
Contract 15A. From 4.0 s to the trace end, public state, no-fault outcome,
absence of an unresolved watch, and directional context agree. The R4.3 paired
measurement anchors and checkpoint history necessarily differ from R1a's
single-anchor representation. Thus this trace proves **suffix outcome agreement
after 4.0 s**, not universal equivalence for every future command or fault.
Earlier anchor advancement can change later reference math in other traces;
general fault sensitivity and downstream directional behavior are not proven
unchanged by this one normal fixture.

`C9R_TIMING_VERDICT = TIMING_SHIFT_ACCEPTABLE_BUT_SPEC_UPDATE_REQUIRED`:
the exact old anchor times were not normative, and the recorded trace shows no
Safety-severity change, evidence erasure, or stuck masking; nevertheless the
public milestone and paired-reference lifecycle must be explicitly specified
before changing an old expectation or claiming broad equivalence. No blanket
±0.2 s tolerance is proposed.

## 9–10. P1–P20 source recovery and candidate manifest

The R4 registration is the only located P-specific source. It records purpose
names, not complete command/measurement/validity/fault timelines, public-state
oracles, or P-specific input hashes. The R4 evidence says P1–P20 were not run.
P15 is the one exception: its registered purpose explicitly names C9R A→B→C,
whose frozen generator, all inputs, deterministic output, and expected anchor
behavior exist. We reconstructed a **candidate**, not an exact archived R4 P15
capture. This alias still needs user review before a formal gate.

| Case | Recovery status | Input source | Expected source | Formal gate eligible? | Missing evidence |
|---|---|---|---|:---:|---|
| P1 | PARTIALLY_RECOVERED | R4 purpose: normal continuous up | R4 intent only | no | full trace, timing, oracle |
| P2 | PARTIALLY_RECOVERED | normal continuous down | R4 intent only | no | full trace, timing, oracle |
| P3 | PARTIALLY_RECOVERED | normal variable-slope command | R4 intent only | no | slopes, trace, oracle |
| P4 | PARTIALLY_RECOVERED | continuous-command silent stuck | R4 intent only | no | command trace, fault onset, oracle |
| P5 | PARTIALLY_RECOVERED | normal then stuck | R4 intent only | no | switch tick, trace, oracle |
| P6 | PARTIALLY_RECOVERED | intermittent progress then stuck | R4 intent only | no | progress schedule, stop tick, oracle |
| P7 | PARTIALLY_RECOVERED | cumulative small-step normal | R4 intent only | no | steps, measurements, oracle |
| P8 | PARTIALLY_RECOVERED | cumulative small-step stuck | R4 intent only | no | steps, fault fixture, oracle |
| P9 | PARTIALLY_RECOVERED | harmless chatter | R4 intent only | no | chatter sequence, oracle |
| P10 | PARTIALLY_RECOVERED | reversal stuck attack | R4 intent only | no | reversals, fault onset, oracle |
| P11 | PARTIALLY_RECOVERED | normal reversal | R4 intent only | no | reversal schedule, oracle |
| P12 | PARTIALLY_RECOVERED | sensor invalid | R4 intent only | no | invalid interval/quality, oracle |
| P13 | PARTIALLY_RECOVERED | sensor recovery | R4 intent only | no | outage/recovery trace, oracle |
| P14 | PARTIALLY_RECOVERED | baseline offset matched pair | R4 intent only | no | offset values, trace, oracle |
| P15 | RECONSTRUCTED_DETERMINISTICALLY | frozen C9R generator + R1a registration | C9R A→B→C anchor criteria | no, pending review/freeze | independent original R4 P15 capture |
| P16 | PARTIALLY_RECOVERED | moving command then plateau | R4 intent only | no | plateau onset, trace, oracle |
| P17 | PARTIALLY_RECOVERED | plateau then true stuck | R4 intent only | no | transition tick, trace, oracle |
| P18 | PARTIALLY_RECOVERED | checkpoint at command update | R4 intent only | no | same-tick ordering/input, oracle |
| P19 | PARTIALLY_RECOVERED | command update without progress | R4 intent only | no | command/measurement sequence, oracle |
| P20 | PARTIALLY_RECOVERED | measured progress without new command | R4 intent only | no | measurement sequence, oracle |

Count: **0 RECOVERED_EXACT, 1 RECONSTRUCTED_DETERMINISTICALLY, 19
PARTIALLY_RECOVERED, 0 NOT_RECOVERABLE**. The partial cases have useful intent
but cannot be promoted to formal historical gates. The P15 candidate is
`v0_2/tests/data/tracking_history/P15_C9R_candidate.json`, labeled
`P_HISTORY_RECOVERY_CANDIDATE`. Canonical input SHA-256 is
`9bc270330f79d1692a3ba5ec47501624d747136ff383fadb82de345bf6e5f279`.
The manifest `phase5_r5_2_1_p_history_input_recovery_manifest.json` has
canonical SHA-256
`840d55f61b32c6486485892aa9002388449675e2647a924567206da60c62af8f`.
The manifest spells out canonicalization, every status, evidence source,
ambiguity, expected-behavior source, and formal eligibility. No P case was
declared PASS/FAIL as a historical gate.

## 11–14. Diagnostic-only execution, causality, watch, fresh grace

R4.3 prefix-causality holds for S3, S14, and the recovered P15/C9R trace:
running every prefix never changes earlier records. P15 was **not** run as a
formal historical P gate. The machine evidence includes full per-tick S3/S14
side-by-side records and four-version C9R records, plus diagnostic-only
withdrawal/reissue traces. On S3/S14 and C9R, no watch age is reset before
qualified progress, no fault evidence is lost, and no future sample is used.

Three synthetic withdrawal diagnostics were run, not registered historical
gates. Withdrawal before fault evidence cancels the old watch and a later
sustained stuck demand confirms at 2.8 s. Withdrawal after one valid evidence
sample retains a single watch with start 0.0 s; reissue at 1.6 s does **not**
confirm on that same tick, but the continued stuck demand confirms at 2.8 s.
Repeated short withdrawals/reissues also keep that evidence and eventually
confirm at 4.0 s after the last sustained demand. These probes support the
no-immediate-false-fault and no-evidence-erasure properties. They do **not**
prove a universal no-fresh-grace property against indefinitely short demand
pulses: a rule for whether intermittent, physically unobservable demand should
accumulate time remains a policy question. No new timer or semantic rule was
introduced in this audit.

## 15–17. Limitations, gate, and next recommendation

`R4_3A_GATE = R4_3A_HISTORICAL_TIMING_REGRESSION_FOUND` because S3 and S14
violate the frozen public-state sequence. P-input recovery is independently
incomplete. **Full historical validation cannot be claimed. Production port
cannot start.** No P expectation, R4.3 engine, Safety source, or Contract 15A
was edited. If this audit motivates changing the state-sequence contract,
`CONTRACT15A_CLARIFICATION_NEEDED` should be raised; this report does not amend it.

Recommended regression policy is **BOTH, with different classifications**:
preserve exact sampled public-state sequence where the historical acceptance
explicitly requires it (S3/S14), and separately test causal milestones
(qualified response, watch resolution, no fault, no future input). For C9R,
exact trigger times are normative; anchor order and qualified resolution are
normative; the old anchor timestamp is not. Do not add a generic timing
tolerance. Next, obtain a reviewed decision on whether same-sample collapse may
replace the historical S3/S14 public milestone, and locate or explicitly
preregister new P1–P14/P16–P20 fixtures without calling them historical captures.
