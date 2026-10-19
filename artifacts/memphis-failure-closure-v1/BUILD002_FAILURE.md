# Build002 preserved — robustness batch stopped on unexcited valve

Execution c23bbc8ecf7a6dd64426e491484443d57d8c72ba; manifest RAW
8c0edf942e037dc5fdd7df4574c9b5b882e7addf588a6a135943dd3c21160ed1.

Run https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39146681509

Official failed raw artifact12143459017, ZIP SHA256
4f342cb1a495291e2f4cbcb4b77787087c88fdad1d022e67572ce474c3dbcee8.
ROBUST_B stage exited1, cleanup_complete=true, active_after_cleanup=0.
Exact failure: STUCK_VALVE_NOT_EXCITED in robust_B__13. The85pct true
reserve could not satisfy the17TT conservative85pct proof; no B command issued.
Original failure and raw evidence preserved. No valve PASS awarded.

Build003 changes only batch classification: this point is explicitly
INCOMPLETE_STUCK_VALVE_NOT_EXCITED and cannot qualify for robustness.
Dedicated valves__A_demand_stuck still MUST issue B and prove nonresponse;
FINAL independently requires this witness. No controller threshold or physical
input is relaxed; original customer limits/frozen M1/historical sources unchanged.
Fresh full development campaign, no Build002 PASS reuse.
