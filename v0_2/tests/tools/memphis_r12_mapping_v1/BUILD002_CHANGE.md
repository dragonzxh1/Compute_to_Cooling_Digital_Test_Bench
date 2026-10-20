# Build002 unsealed development iteration

Build001 commit b0916450c273ba9c68c7c5c3bbe5ccc90b5924cb / run39450623853 failed: 7/32 executed PASS,25/32 FAIL because the observation fixture passed provenance twice to dict(). No new physical conclusion or negative-control coverage is inferred from those failed tests.

Repair: copy the base fixture, then explicitly update released-measurement provenance. No R12 threshold, topology, source parameter, protected M1, original document or expectation weakened. Fresh complete unit suite is required for this new source. Build001 artifact and source snapshot remain immutable.
