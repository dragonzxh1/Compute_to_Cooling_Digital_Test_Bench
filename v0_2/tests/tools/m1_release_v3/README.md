# Streaming installed SDK repair candidate

The old SDK ZIP8e5496f21c948284dd262077456e17a96d70011bee098be3668b07861b57384c
is preserved. Its extended-use run38492275799 passed indices0..64 but stopped
with MemoryError at full index65(161rows), during result serialization under the
approved1024/2048MiB Job. Actual venv Python PID7860 was proven in the target
Job; native launcher PID6380 is a separate process identity. Cleanup active0.
This is SDK usability/resource failure, not a new candidate behavioral verdict.

SDK v1 retained every reference/SUT frame and completed record in RAM. This new
entry selects the already validated streaming/immutable CompletedJournal backend
used by full V4 campaign. No math, inputs, thresholds, timers, source expectations
or comparator rules change. Complete canonical documents, indexed frames and
journal remain on disk; no history is discarded to get PASS. Observer-interference
check, full trace verification and independent oracle/comparison are retained.

Tick/phase progress is fsynced to each new SDK artifact directory. The SDK needs
write permission and disk capacity for complete traces; it does not overwrite
prior outputs. UUID identifies output storage only, not fixture/model randomness.
All source bytes and a new package must be bound before a fresh hosted install
validation. No repair/retry inside run38492275799. This code is not yet executed
or accepted as a working SDK. The original full campaign evidence is unchanged.
