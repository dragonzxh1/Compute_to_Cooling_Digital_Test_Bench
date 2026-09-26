# P15 reconstructed historical fixture — freeze record

`P15_HISTORY_FIXTURE_STATUS = FROZEN_RECONSTRUCTED_HISTORICAL_FIXTURE`

`P15_HISTORICAL_REGRESSION_STATUS = PASS`

P15 is a **deterministically reconstructed historical fixture**, not an exact recovery of an original captured P15 file. The user's R4.3D approval freezes **P15 only**. The R4 registration explicitly maps P15 to C9R A-to-B-to-C; these names are not two independent historical captures.

The unchanged [31-record input](v0_2/tests/data/tracking_history/P15_C9R_candidate.json) has full-object canonical SHA-256 `9bc270330f79d1692a3ba5ec47501624d747136ff383fadb82de345bf6e5f279` and file SHA-256 `bbf2145b4347630d6e78ff51a5569002a6d5d6fc75f128ea0377e72691bc7fd1`. Every record equals both the old R1a serialized C9R input and regenerated output. Ten generator regenerations match. The generator is `v0_2/examples/phase5_r5_2_1r1a_validation.py::c9r_source` (source SHA-256 `238a03cef6b7b0c25a05ef71c4f699c75a91626c716f978a452ac23bc27d4ef1`), backed by deterministic `run_open_loop` (source SHA-256 `110ce80946f1ca118dfa7b062e3fa998c04b65cc26afda1cfce799dbbdc744dd`). Its complete parameters, no-randomness behavior, generation and canonical-serialization procedures are in the [final freeze manifest](phase5_r5_2_1_p15_reconstructed_history_freeze.json).

The historical expectation comes independently from the R1a registration and evidence: two upward net-demand stages, qualified progress, A→B→C resolved command anchors, eventual stable tracking and no erroneous confirmed tracking fault. Epoch trigger times 0.6/3.4 s and command-anchor values 0.35/0.51/0.67 are exact preregistered requirements. Progress-before-resolution and eventual steady state are **order-normative**. The old B/C resolution times 1.2/4.0 s are **non-normative** implementation observations; R4.3A's timing verdict permits the R4.3B 1.0/3.8 s resolution. No old incidental timestamp was added as a formal assertion.

Following this freeze, the unchanged R4.3B candidate passed P15's historical assertions in **10/10 identical executions**. Full snapshot SHA-256 was `d85a5dd067c2df9c69a6f84597a13ed4343dd518f0c796b9f1e0dac12c2a33f0` in every repetition. Prefix causality passed. Both progress milestones appeared at 1.0/3.8 s; final public state was `STEADY_TRACKING`; no fault was confirmed. Separate existing regressions also passed: startup 50/50, C 11/11, S 17/17. These are not substitutes for missing P cases.

The frozen artifact's SHA-256 is `ad407cbbeefeba436b8d54a7474e48b33a68a13f9598848e33510679e09f5965`. The [R4.3C candidate manifest](phase5_r5_2_1_p_history_frozen_candidate_manifest.json) remains unchanged at SHA-256 `c485debbaf7af75be8208884012b036f02ab8dd01cd97b46d6b829bdbd4cb22c`; it is preserved as prior evidence. [R4.3D machine evidence](phase5_r5_2_1r4_3d_p15_freeze_evidence.json) records all checks, hashes, repeats, source immutability and Git status.

Remaining P1–P14 and P16–P20 are `NOT_RECOVERABLE_FROM_CURRENT_EVIDENCE`, not failed tests and not necessarily never recoverable. Formal historical coverage is **1/20**, descriptive only. `FULL_P_HISTORY_VALIDATION_AVAILABLE = NO`; `FULL_P_HISTORY_VALIDATION_PASSED = NOT_EVALUABLE`; production port cannot start. R4.3B engine, Production Safety, controller, plant, tracking profile and Contract15A remained unchanged. No Phase 6, Git commit or push.
