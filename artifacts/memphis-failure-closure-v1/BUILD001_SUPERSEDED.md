# Build001 — superseded before engineering evaluation

Source: cf4b5661a1ff3de5ac8ca10ae4bc24b6c3cb58cd

Manifest RAW SHA256: d74e0d5463a85bdfdda808debc20a8a72260902feefa31e0ee6a3c964c573e66

Run: https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39146509431

Code review identified a new-adapter readiness deadlock: after source selection,
the observation used zero main-loop flow instead of still-running measured
preconditioning-loop flow, preventing main-loop start. Cancellation requested
while the original ZIP download step was active. No engineering PASS claimed.
Source, workflow and run history remain immutable on GitHub. Build002 uses an
explicit measurement-path handoff, not future flow, relaxed thresholds or a
change to frozen M1/customer requirements. No results from Build001 reused.
