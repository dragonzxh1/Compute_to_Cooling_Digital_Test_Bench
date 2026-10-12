# M1 v3 streamed evidence and distributed development campaign

No local Python/native workloads. Independent hosted Windows only; formal C3-C,
production, Phase 6 and hardware qualification are not authorized here.

Nine mathematical core files remain exact frozen v014.1 bytes. Streamed reference
and split loops retain original ordering and all 56 fields, histories and phase
records. Complete classic JSON documents still have exactly the original canonical
wire bytes. JSONL frame indices allow bounded reads without loading all frames.

Split _completed uses a durable immutable Record mapping rather than keeping every
completed full frame in memory. Reconciliation lookup returns identical Record bytes;
this is a development storage adapter, not proof of physical recovery/PLC durability.
Each lookup verifies bytes. No completed record or qualifier history is deleted.

The original comparator is unchanged. Its original independent OracleTrace receives
the exact three fields it reads, cached from verified full reference frames; the full
comparator still reads every complete frame. Regression checks compare old/new full
canonical bytes, every frame, old/new oracle context bytes, corruption rejection and
completed-record lookup. No expected ITQ outcome is generated from the candidate.

Each repeat is a fresh model in a separate owned child, with original 2/11 full
snapshots and exact full-document hashes. Each selected prefix is a fresh replay from
t0, compares all complete canonical frames to the full traces and persists row hashes
plus completed split bytes. The frozen conditional/all-prefix policy is unchanged.

Job CPU 1%, process/job memory 256/512 MiB, wall 120s per child and kill-on-close remain.
Source/environment guards and actual-Python membership proof precede release; native
errors/raw captures persist before acceptance. External memory sampling records private
commit and working set. A failed execution is preserved; repairs get a new source version.

Full campaign completion means fresh 101 cases, all selected prefixes, original repeats,
Startup historical guard + versioned compatibility, C/S/P15, PF witness and schema checks.
PF06 original gap/extension proposal, asynchronous P1 incompleteness, T09 hold and
unavailable full P history remain explicit; hardware CALIBRATION_REQUIRED. An engineering
execution PASS does not self-approve frozen full-scope readiness or production authority.
