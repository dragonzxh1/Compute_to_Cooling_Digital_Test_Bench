# Phase 5R5.2.1R4.3D — P15 fixture freeze report

## 1. Purpose and user approval

The user approved freezing **only P15** as a deterministically reconstructed historical fixture. This does not approve a full P1–P20 validation claim, production readiness, a production Safety change, or invented replacements for missing inputs.

## 2. Evidence chain and reconstruction method

The R4 preregistered P-history matrix says `P15 = C9R A-to-B-to-C`. The R1a registration supplies the complete command schedule, actuator and sampling parameters; `c9r_source` uses deterministic `run_open_loop` and transforms its rows into released observations. The existing P15 file's 31 records match both ten regenerations and the older R1a evidence's serialized `c9r_case.input_trace` record for record. The historical acceptance oracle is the R1a registration plus its 13 positive C9R acceptance checks, **not** a new expectation inferred from R4.3B's output.

The input's canonical full-object SHA-256 is `9bc270330f79d1692a3ba5ec47501624d747136ff383fadb82de345bf6e5f279`; its physical-file SHA-256 is `bbf2145b4347630d6e78ff51a5569002a6d5d6fc75f128ea0377e72691bc7fd1`. Generator source SHA-256 is `238a03cef6b7b0c25a05ef71c4f699c75a91626c716f978a452ac23bc27d4ef1`; underlying generator SHA-256 is `110ce80946f1ca118dfa7b062e3fa998c04b65cc26afda1cfce799dbbdc744dd`. No randomness is used. The precise parameters and generation procedure are preserved in the [freeze artifact](phase5_r5_2_1_p15_reconstructed_history_freeze.json). `P15_RECOVERY_CLASS = RECONSTRUCTED_DETERMINISTICALLY`, **not** `RECOVERED_EXACT`: no original P15 capture was independently found.

## 3. Frozen historical intent and normativity

P15 requires two-stage upward motion response; qualified actuator progress in both stages; A→B→C command-anchor resolution; eventual `STEADY_TRACKING`; and no erroneous `TRACKING_FAULT_CONFIRMED`. The R4 P15 registration is a C9R alias, not an unrelated test.

| Property | Normativity | Frozen expectation |
| --- | --- | --- |
| P15→C9R identity, complete 31-record input | Exact | R4 alias; canonical input hash above |
| Material-demand epoch starts | Exact | 0.6 s, 3.4 s |
| Epoch directions and command anchors | Exact | Up, up; 0.35→0.51→0.67 |
| Qualified progress, corresponding resolved anchor, eventual steady | Order | Each stage progresses before/at its resolution; second follows first |
| Confirmed tracking fault | Exact prohibition | None |
| Old B/C resolution timestamps | Non-normative | 1.2/4.0 s were older implementation observations |
| Current R4.3B B/C resolution timestamps | Non-normative | 1.0/3.8 s are diagnostic observations, not newly frozen limits |

R4.3A recorded `TIMING_SHIFT_ACCEPTABLE_BUT_SPEC_UPDATE_REQUIRED`. This freeze preserves that adjudication and does not rewrite R4, R4.1, R4.1A, R4.3A, R4.3B or R4.3C historical conclusions.

## 4. Formal P15 execution, repeatability and prefix causality

The input was hash-checked, reconstructed and compared to historical serialized evidence **before** formal execution. A pre-freeze R4.3B confirmation had the same snapshot hash as the later formal run. After fixing P15's input and expectation identity, 10/10 executions against the unchanged R4.3B candidate produced identical snapshot SHA-256 `d85a5dd067c2df9c69a6f84597a13ed4343dd518f0c796b9f1e0dac12c2a33f0`. Prefix causality passed. Formal assertions passed for both exact triggers and directions, anchor values/provenance, progress and resolution order, final steady state and no confirmed fault. Thus `P15_HISTORICAL_REGRESSION_STATUS = PASS` **for P15 only**.

Existing separate regression checks passed: startup **50/50**, valid C **11/11**, S **17/17**. The R4.3B engine SHA-256 before and after was `52b4ddd46401c16793a3602f49f02a5e9ca78906178390f9934c3453ed7b065e`. The frozen input, generator, Production Safety, controller, plant, tracking profile and Contract15A remained unchanged. See [machine evidence](phase5_r5_2_1r4_3d_p15_freeze_evidence.json) for all before/after hashes and assertions.

## 5. Freeze status, remaining coverage and production boundary

The previous [R4.3C candidate manifest](phase5_r5_2_1_p_history_frozen_candidate_manifest.json) was preserved unchanged. The new [final P15 freeze manifest](phase5_r5_2_1_p15_reconstructed_history_freeze.json) has SHA-256 `ad407cbbeefeba436b8d54a7474e48b33a68a13f9598848e33510679e09f5965`. A separate [human-readable freeze record](PHASE5_R5_2_1_P15_RECONSTRUCTED_HISTORICAL_FIXTURE_FREEZE.md) summarizes the fixture. `P15_HISTORY_FIXTURE_STATUS = FROZEN_RECONSTRUCTED_HISTORICAL_FIXTURE` and `P15_FORMAL_HISTORICAL_GATE_ELIGIBLE = YES`.

The other 19 P cases remain `NOT_RECOVERABLE_FROM_CURRENT_EVIDENCE`. They were **not executed**; `FULL_P_HISTORY_VALIDATION_PASSED = NOT_EVALUABLE`, not FAIL. Formal historical source coverage is **1/20**, not an overall pass score. `FULL_P_HISTORY_VALIDATION_AVAILABLE = NO`; a complete historical validation cannot be claimed; `CAN_PRODUCTION_PORT_START = NO`. No replacement P cases, production port, Phase 6, commit or push were created.

`R4_3D_GATE = P15_RECONSTRUCTED_HISTORICAL_FIXTURE_FROZEN_AND_VALIDATED`.

## 6. Next recommendation

For user review: consider a separate **Phase 5R5.2.1R4.4 independent tracking qualification suite design**. Any future cases must be newly preregistered, hashed and executable, explicitly labeled new qualification—not recovered P1–P20 historical regression. Do not implement that suite as part of R4.3D.
