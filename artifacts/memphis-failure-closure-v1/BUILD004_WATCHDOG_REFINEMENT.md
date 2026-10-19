# Build004 — superseded by publication-loss watchdog coverage

Source8accb6fdb263dfe5bf7a9f7d2058451b6cdcb172; manifest RAW
630e85a72ffedad66b890ab7a726dfd980f0893f3ff1c66b40c034a1cedcc15f.
Run https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39179142841

Coverage review identified a new-project source-loop integration defect:
protection was invoked only on arrival of a new observation. Its existing
stale-sample guard worked for delayed publications but would not be reevaluated
when publication completely stopped. Build005 adds a200ms clock watchdog over
already released observations and an actual40s source-publication dropout case.
No new/future observation, hidden model state or extra M1 sample credit is used.
The independent persisted-evidence check requires publication actually stop,
SOURCE_SENSOR_STALE latch and source_enable=false in PROTECTED_HOLD after loss.

Build004 source/results remain immutable and are not represented as covering
complete publication loss. Frozen M1/expectations/contracts are unchanged.
Build005 uses a fresh complete40-stage development campaign; no old PASS reuse.
