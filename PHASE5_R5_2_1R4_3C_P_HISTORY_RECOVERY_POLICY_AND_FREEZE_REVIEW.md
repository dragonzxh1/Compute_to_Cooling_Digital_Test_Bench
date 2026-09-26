# Phase 5R5.2.1R4.3C — P-history recovery policy and candidate freeze review

## 1. Purpose and current status

This is a historical-evidence governance review, not a tracking-semantics revision. R4.3B remains `OBSERVABLE_PROGRESS_COMPATIBILITY_RESTORED`: its prior startup-focused 50/50, valid-C 11/11 and S 17/17 results are not rerun or promoted here. The old R4.1 R41-7 failure remains historical fact; the R4.3B candidate's R41-7 pass does not erase it. This review does not reopen S3, S14 or C9R.

The review asks which P1–P20 inputs and independent historical expectations are actually available before any P case becomes a formal regression gate. The answer is **P15 only, as a deterministic reconstruction candidate**. The other 19 have recorded intent but no recovered executable timeline. Thus `FULL_P_HISTORY_VALIDATION_AVAILABLE = NO`, and production port eligibility is `NO`.

## 2. Recovery policy and formal-gate rule

| Class | Required evidence | Formal historical gate? |
| --- | --- | --- |
| `RECOVERED_EXACT` | Complete original executable/serialized input, parameters, event ordering, command and measurement-validity timeline, historical expected behavior, and provenance proving it is the actual fixture. A matching historical hash is strong provenance. | Yes, if the expectation is independently supported. |
| `RECONSTRUCTED_DETERMINISTICALLY` | Identified historical generator and version/hash, all parameters, controlled randomness/seed, deterministic event ordering, reproducible full timeline, independent historical confirmation of key characteristics, and historical expected behavior. It is **not** a recovered original capture. | Yes, if the expectation is independently supported. |
| `PARTIALLY_RECOVERED` | Some actual historical input/parameters/timeline are available, but at least one necessary element is missing. A narrative purpose alone is not a partial executable input. | No; diagnostic/design use only. |
| `NOT_RECOVERABLE` | Available local evidence cannot produce a defensible historical executable input and expectation; state exactly what is missing. New evidence may reopen this finding. | No. |
| `NEW_EQUIVALENCE_TEST` | A future newly preregistered test with its own input hash, expectation, and explicit mapping to historical intent. **It does not reconstruct the original historical fixture.** | No as an original-history gate; it may be a separate new-qualification gate. |

`FORMAL_HISTORICAL_GATE_ELIGIBLE = YES` only for an exact recovery or deterministic reconstruction **and** an independently supported historical acceptance oracle. Input reconstruction alone is insufficient. A candidate manifest is not a final freeze, and even an eligible fixture has no formal PASS/FAIL before user-approved freeze and execution. `FULL_P_HISTORY_VALIDATION_AVAILABLE = YES` requires all 20 required P cases to be eligible.

If two historical sources conflict, executable/preregistered machine evidence has priority over later narrative summaries, but both sources and the conflict must be recorded. A mere historical hash reference without recoverable matching content cannot reconstruct an input.

## 3. P15 evidence and freeze decision

`P15_FREEZE_DECISION = APPROVE_RECONSTRUCTED_HISTORICAL_FIXTURE` as a **candidate for user-approved freeze**, not an approved final baseline.

The R4 preregistered matrix explicitly maps P15 to `C9R A-to-B-to-C`. The R1a registration fixes the generator parameters; `phase5_r5_2_1r1a_validation.py::c9r_source` and its open-loop fixture generator are deterministic. All 31 records in the existing P15 candidate equal both (a) ten independent regenerations and (b) the older R1a evidence's serialized `c9r_case.input_trace`. The R1a historical evidence separately records all 13 C9R acceptance criteria as true, including both upward demand epochs, directional progress, A→B→C resolution and no false confirmed fault. The generator and expectation therefore do not depend on today's R4.3B result.

Provenance chain: [R4 registration](phase5_r5_2_1r4_paired_reference_tracking_registration.json) → [R1a registration](phase5_r5_2_1r1a_in_domain_anchor_revalidation_registration.json) → [R1a generator](v0_2/examples/phase5_r5_2_1r1a_validation.py) → [old serialized input and acceptance](phase5_r5_2_1r1a_in_domain_anchor_revalidation_evidence.json) → [P15 candidate](v0_2/tests/data/tracking_history/P15_C9R_candidate.json). The candidate's canonical JSON SHA-256 is `9bc270330f79d1692a3ba5ec47501624d747136ff383fadb82de345bf6e5f279`; generator file SHA-256 is `238a03cef6b7b0c25a05ef71c4f699c75a91626c716f978a452ac23bc27d4ef1`. Full parameters, source hashes and expectations are in the candidate manifest and machine evidence.

The historical normative trigger times are 0.6 s and 3.4 s, with A/B/C command anchors 0.35/0.51/0.67. Both stages require qualified directional progress and eventual resolution, without a confirmed tracking fault. The **old** 1.2/4.0 s anchor resolution timestamps are observations of an older implementation, **not** normative thresholds. No original R4 P15 capture is claimed; the eligible identity is the preregistered C9R alias reconstructed from its historical generator and serialized input.

## 4. Deep repository and Git recovery search

Searched the current tree, including hidden/ignored local evidence, registrations, JSON reports, tests, fixtures, `docs/results`, generator names, case descriptions, serialized traces and hash references. Read-only Git review covered all 16 commits and locally available `main`/`origin/main` refs, relevant diff text, and deleted/renamed-file history. No other P-specific executable fixture, generator payload, serialized timeline or recoverable matching historical hash was found. A `caf8807` text hit is unrelated Phase 4 rendered HTML/base64, not a P-history source. No relevant deleted or renamed files were found in the inspected paths. This conclusion is limited to the locally available repository/history; it does not prove that no external archive exists.

R4.3A called P1–P14 and P16–P20 `PARTIALLY_RECOVERED` because their **narrative intent** survived. Under the stricter R4.3C definition above, intent without any partial executable input is not partial input recovery. Those 19 are therefore `NOT_RECOVERABLE` **from presently available evidence**, not silently converted into new tests. For every such case the missing elements are an original command/measurement/validity timeline, frozen case-specific parameters or generator/input hash, and an independent case-specific acceptance oracle.

## 5. P1–P20 case record and historical-intent matrix

For P1–P14 and P16–P20, the best available source is the R4 preregistered narrative matrix. In each of those rows: complete input = No; expected behavior = No; timing normativity = Unknown; generator/hash = None; candidate input hash = None; formal gate = No. These shared fields and case-specific intents are expanded in the [machine evidence](phase5_r5_2_1r4_3c_p_history_recovery_evidence.json).

| Case | Historical intent / behavior class supported by R4 narrative | Input | Independent expectation | Formal gate |
| --- | --- | --- | --- | --- |
| P1 | Normal continuous increase | Not recoverable | No | No |
| P2 | Normal continuous decrease | Not recoverable | No | No |
| P3 | Normal variable-slope command | Not recoverable | No | No |
| P4 | Continuous-command silent stuck | Not recoverable | No | No |
| P5 | Normal response then stuck | Not recoverable | No | No |
| P6 | Intermittent qualified progress then stuck | Not recoverable | No | No |
| P7 | Cumulative small-step normal response | Not recoverable | No | No |
| P8 | Cumulative small-step stuck response | Not recoverable | No | No |
| P9 | Harmless chatter | Not recoverable | No | No |
| P10 | Reversal stuck attack | Not recoverable | No | No |
| P11 | Normal reversal | Not recoverable | No | No |
| P12 | Invalid sensor measurement | Not recoverable | No | No |
| P13 | Sensor recovery | Not recoverable | No | No |
| P14 | Matched-pair baseline offset | Not recoverable | No | No |
| P15 | C9R A→B→C; two cumulative upward demand stages | Deterministically reconstructed | Yes, R1a evidence | Yes, pending freeze |
| P16 | Moving command then plateau | Not recoverable | No | No |
| P17 | Plateau then true stuck | Not recoverable | No | No |
| P18 | Checkpoint at command update | Not recoverable | No | No |
| P19 | Command update without progress | Not recoverable | No | No |
| P20 | Measured progress without new command | Not recoverable | No | No |

These class labels describe only the recorded historical **intent** for unrecovered rows; they do not assert executable behavior or a PASS/FAIL result.

## 6. Eligible fixture, candidate manifest and coverage gaps

Counts: `RECOVERED_EXACT = 0`; `RECONSTRUCTED_DETERMINISTICALLY = 1`; `PARTIALLY_RECOVERED = 0` under the R4.3C policy; `NOT_RECOVERABLE = 19`; formal-gate eligible candidates = `1/20` (5% **descriptive source coverage**, not a pass score).

Only P15 appears in the [candidate freeze manifest](phase5_r5_2_1_p_history_frozen_candidate_manifest.json), status `CANDIDATE_FOR_USER_APPROVED_FREEZE`, `final_frozen_baseline = false`. Manifest file SHA-256: `c485debbaf7af75be8208884012b036f02ab8dd01cd97b46d6b829bdbd4cb22c`. Canonical SHA-256 of the ordered eligible-record list: `6d8a0d2055708ff75003cd221c24da42657a3827dfbb373bcc21e5e76bfc5285`. Canonicalization is UTF-8 JSON with sorted keys, compact separators, `ensure_ascii=False`, `allow_nan=False`, no trailing newline.

The missing **formal historical executable** coverage spans continuous increase/decrease, slope variation, stuck and transition-to-stuck, intermittent response, small-step accumulation, jitter/chatter, reversal (normal and stuck), sensor invalidity/recovery, baseline offset, plateau, checkpoint timing, command without progress, and measured progress without a new command. P15 supplies only the two-stage C9R cumulative-upward case. Existing S/C and R41-7 checks are separate evidence; they do not transform missing P fixtures into recovered historical P gates. A future *new tracking qualification suite* may cover these hazards with freshly preregistered `NEW_EQUIVALENCE_TEST` cases, but new qualification coverage is **not** original historical regression coverage.

## 7. Source conflicts, diagnostic execution and limitations

No new historical source contradicts the R4.3A/B C9R or S conclusions; `HISTORICAL_SOURCE_CONFLICT` was not raised. The R4.3A-to-R4.3C count change is an **evidence-classification policy correction**, not a newly found conflicting input. The old R4.1 R41-7 failure and current R4.3B pass remain distinct facts.

`DIAGNOSTIC_PRE_FREEZE`: P15's reconstructed input run against unchanged R4.3B reaches command anchors A/B/C at 0/1.0/3.8 s, qualified progress at 1.0/3.8 s, returns to `STEADY_TRACKING` after each handoff and has no confirmed fault. The R4.3B engine SHA-256 is `52b4ddd46401c16793a3602f49f02a5e9ca78906178390f9934c3453ed7b065e`, matching prior R4.3B evidence. This is **not a formal historical P15 PASS**: user-approved fixture freeze and formal execution have not occurred. The diagnostic does not make the old 1.2/4.0 s resolution timestamps normative.

The [machine evidence](phase5_r5_2_1r4_3c_p_history_recovery_evidence.json) records P15 comparison checks, all 20 case fields, source/production hashes, Git commits inspected, diagnostic output and gate. Production source hashes, Contract15A and tracking profile match their registered baselines. No R4.3B engine, production Safety, controller, plant, Contract15A, profile or behavioral tests were edited. No production port, Phase 6, Git commit or push occurred.

## 8. Freeze recommendation and next action

Recommend user review of the **P15-only candidate** manifest, then an explicit approval/rejection of its freeze. After approval, P15 may be run as a formal historical gate; a full P1–P20 historical-validation claim remains unavailable until the other 19 originals are recovered and frozen. Separately, seek any external historical archive for those 19; if none exists, preregister a new qualification suite without calling it original P history.

`FULL_P_HISTORY_VALIDATION_AVAILABLE = NO`

`CAN_FULL_HISTORICAL_VALIDATION_BE_CLAIMED = NO`

`PRODUCTION_PORT_ELIGIBLE = NO`
`R4_3C_GATE = P15_RECOVERABLE_BUT_P_HISTORY_REMAINS_INCOMPLETE`
