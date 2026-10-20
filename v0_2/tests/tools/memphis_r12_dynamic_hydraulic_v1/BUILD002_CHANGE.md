# Build002 — preserve Build001, new source and fresh remote run

Build001 source `8e5535afa77f9a7b0beaa96f244d66e4c74e4495`, run39491851591: FAIL / numerical nonconvergence after t49.5s. Official ZIP SHA256 `c0b2d749e10b3f77e5813d325dcbfc3c82e3f1618ba1f29d3ca2c746a8a9b117`; raw logs `8f9e3aabb90bdaa2d53f02ae7b31c22f968dc852ec3a1142897edbc54553fbc8`. Actual Python PID4456, CPU25%/256/512MiB, cleanup=true, active0. Failed trace and source snapshot retained unchanged. Not a thermal/hydraulic PASS.

Controller command-reference defect: incremental pressure and follower speed targets were repeatedly based on lagged speed feedback. They now integrate their own past command references while pressure/permission checks still consume released measurements. No future measurements or commands are read.

Numerical defect: direct solve on a pressure Laplacian with closed-check-valve dead-leg null modes could produce unstable pressure directions. Use rank-revealing least squares; keep the original KCL residual tolerance. Do not add numerical reservoir leaks, bypasses or increase tolerances.

Begin timeout closure early by the registered 2s valve-travel plus0.2s release/sample allowance, rather than issue close after the30s actual overlap limit. Raw PRE now includes the complete released measurement frame for independent stability reconstruction.

No changes to graph, hard flow/temperature/pressure limits, pump/HX data, frozen M1, CPU/memory/480s budgets. New immutable source snapshot and fresh workflow, never rerun the failed job under the same identity.
