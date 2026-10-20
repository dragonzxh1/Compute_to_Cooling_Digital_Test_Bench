# Build003 — pressure-zone numerical isolation

Build002 source `2f1fd25346625cfb7414c5c08ff39fcbb2172c67`, run39492422095 failed at t34.8s, after old pump zero speed and during old path isolation. Official ZIP SHA256 `a85201f17b7dba1dbc8f86e3ec410990cdf9e834afd8bf4cb4342c604567b9e6`; raw logs `550b88aad9d1ea43a0f06885e293d95711d61e341e477cae18c3b747236fa787`. Actual Python6392, same25%/256/512 limits, cleanup=true and active0. Failed source and PRE/POST records retained unchanged.

The remaining numerical failure occurred when all old primary isolation valves finished closing, leaving the old HX as an isolated, unforced passive pressure zone. Its correct quasi-steady relative-pressure/flow solution is zero. Build003 explicitly sets unforced passive zones to that solution and solves driven pressure zones in independent rank-revealing blocks. No artificial reservoir leak, topology bypass, hard-limit change or relaxed KCL tolerance.

Absolute trapped pressure, compliance, thermal expansion and waterhammer are not modeled. The isolated zone's configured gauge reference must NOT be interpreted as physical proof of trapped-pressure relief. Construction/safety and HX gauge-pressure approval remain withheld.

Add numerical-failure diagnostics for any further failure. This is the third candidate; if it still fails, stop automatic repairs and report the questionable solver assumption. No same-commit failed-job retry.
