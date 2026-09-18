Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 16 — FAIR_COMPARISON Contract

## Inputs / Outputs

Input: frozen registration plus observed run manifest and actual applied leaf source ledger.
Output: FAIR_COMPARISON = PASS / FAIL; differing field paths/hashes and reason; comparison_status VALID / INVALID; B/C matching status separately.
Failing physical/numerical validity can invalidate a comparison even if hashes match. Hash PASS is not proof of control benefit or calibrated hardware.

## Canonical hash manifest

SHA-256 over UTF-8 canonical JSON: recursively sorted keys, no whitespace/BOM, ordered arrays preserved, IDs sorted where sets, explicit null, no NaN/Inf, times integer ns. Engineering numeric fields converted to canonical SI decimal STRINGS (no exponent, strip trailing fractional zeros, −0→0) before hash, never unit-ambiguous binary display. Hash precision does not permit rounding a differing input into equality; parsed source exact decimal representation retained. Array/schema version and units included. Source/code blobs separately SHA-256 of exact bytes.
Manifest contains:
experiment_type, benchmark_class, schema/contract versions and hashes; hardware config; topology including power allocation; FWS event schedule; branch disturbance schedule; full initial thermal/hydraulic/controller state; offered workload/domain and leaf traces; actual applied per-leaf trace; parameter/provenance/calibration versions; noise REALIZATION plus generator version; sampling/window; network/processing latency and loss realization; all five periods/event ordering; PLC inner-loop gains/anti-windup/interlocks; actuator limits/delay/ramp; integrator method/tolerance/effective policy; solver/code version; seeds; measurement/safety policies; warm-up/scoring windows; search whitelist/budget/candidates/selection rule; selected parameter values; matching tolerances/energy budget and registered meaningful-benefit thresholds.

Noise digest covers keyed per-sensor sample sequence, not measured T/flow themselves (these may differ due to strategy). Same principle for communication drops/latency. Physical operating trajectories are allowed to differ; physical configs are not.

## Allowed differences

A: only FF enable differs. Same implementation versions/algorithm definitions/initial non-FF state/targets/gains; disabled FF contribution0. Do not permit unrelated strategy parameter differences under mode label. FF internal state initialized identically although only enabled mode acts.
B/C: FF enable plus EXACT base_dp_fraction matching whitelist09/10; shared bounds/inner loop/hardware/safety still identical. Chosen values and all candidate hashes retained in full per-mode manifest; comparison equality projection excludes only these declared paths, not entire controller objects. Empty/unrecognized wildcard exclusions forbidden.
SAFETY_PROTECTION: same offered trace/protection config; delivered trace may differ as an outcome, still each run verifies offered->cap->delivered ledger. No performance efficiency rank.

## Actual input audit

PERFORMANCE applied source hashes must equal each other AND immutable planned trace for every domain/leaf, including allocation. Trace canonical form: piecewise-constant right-continuous list(time_ns,leaf_id,value_W), consecutive equal segments merged. Include initial value/t_end and all actual source mutation event boundaries, not only coarse logging times, so transient tampering is detectable. Integrator consumed-source receipts must reconcile these intervals; wrong mapping or skipped energy interval fails source audit.
Physics substeps need not produce identical serialization; compare normalized interval source function, not duplicated logging rows. Different mode hardware/source boundaries fail. Sum equality alone insufficient.

A fair run includes all initial states/noise realizations, not only seed. One difference outside allowlist -> FAIL with field diff; never auto-copy or delete it to “fix” evidence. Fingerprints are integrity checks, not cryptographic attestation that future code obeys permissions; runtime trace/forbidden-access tests still required.

## Failure / acceptance specifications

FAIR-01: change one sensor delay, PLC gain, actuator ramp, allocation or initial temperature -> FAIL.
FAIR-02: alter applied PERFORMANCE IT power in both modes identically -> FAIL vs immutable offered input.
FAIR-03: whitelist base_dp_fraction difference allowed only B/C with preregistration; extra supply target difference fails.
FAIR-04: same seed but different noise calls/realization -> FAIL; differing measured temperatures alone not FAIL.
FAIR-05: safety-delivered difference permitted only audited SAFETY_PROTECTION; cannot relabel as performance.
FAIR-06: reordered unordered ID sets canonicalize identically; changed numeric content cannot be rounded away.

