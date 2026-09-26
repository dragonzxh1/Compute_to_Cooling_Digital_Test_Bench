# Phase 5R5.3R — Production Safety Tracking Port: blocked trial

## Outcome

`PHASE5_R5_3R_GATE_STATUS = PRODUCTION_TRACKING_FALSE_POSITIVE_REMAINS`

R1a, R3 and R2R source gates and required hashes matched before production modification. A [pre-change registration](phase5_r5_3r_production_safety_tracking_port_registration.json) recorded the exact authorized files and frozen semantics. The pre-change V0.2 test baseline passed.

Registration SHA-256: `4ff6a7df8228400c9a2f3d8d584a94208c17e995ceef644deabc41dd971d1b7c`.

The trial mechanically ported the frozen offline tracking epoch/watch/cumulative-anchor semantics into a narrowly scoped production qualifier, removed the legacy raw `0.15` tracking branch as authority, passed the released PLC command/timestamp and measured speed into Safety, and aggregated independent channel reasons under Contract 15A. No controller, physical plant, pump actuator, sensor, profile, Contract 14/15/15A, or scheduler timing source was edited.

The first focused regression exposed a blocking false positive in the legacy `TUNE-01-load` scenario. It reported tracking `DEGRADED / ACTUATOR_TRACKING_SUSPECTED` at 29.6 s and `FAULT / ACTUATOR_TRACKING_CONFIRMED` at 31.0 s. The existing scenario asserts that Safety never enters FAULT. At 29.6 s the released command and measured speed were approximately 0.852986 and 0.846774, respectively, yet the tracking channel had already degraded. The later FAULT forced the generic fallback command to 0.5 while measured speed was approximately 0.854502. This is not acceptable production behavior. Whether the underlying cause is a frozen qualifier applicability gap for continuous command evolution or a subtle integration mismatch has not been established; do not resolve it by changing a threshold or timer without a separate authorized contract revision.

Two other focused failures were compatibility signals, not the primary blocker: a historical test expected the superseded 2.1-second raw-mismatch FAULT, while the frozen qualifier returned FF_DISABLED at that instant; a historical R5.1 integrity test compares the *current* Safety source against its pre-port SHA, which necessarily fails during an authorized production port. Historical evidence and gates were not rewritten.

Following the task's stop-on-failure rule, the incomplete production changes were reverted. `v0_2/safety/supervisor.py` and `v0_2/plant/controlled_loop.py` again match their pre-change SHA-256 values (`370920424bf9d1c1006c7bd800871d24737523004d6664f5b67155ab1948b036` and `5c5c5ef3cba14f9e51eb469a1a6a65229c1ab082dc0d6fef72de56eaf1776db8`). The trial-only production qualifier file was removed. The [blocker evidence](phase5_r5_3r_production_safety_tracking_evidence.json) retains exact observations and hashes.

No completed six-state production qualifier, M1–M16 production equivalence, S/C/C9R golden trace comparison, warm/cold 0.2/0.1/0.05 mesh, causality, conservation, 10-repeat suite, figure, or candidate baseline is claimed. R5.4, final baseline freeze, Phase 6, and Git commit/push were not started. This is a generic numerical development finding, not OEM/NVIDIA/GB300 hardware validation.
