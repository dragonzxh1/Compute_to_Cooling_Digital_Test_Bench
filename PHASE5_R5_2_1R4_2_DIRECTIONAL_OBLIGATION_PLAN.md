# R4.2 directional obligation candidate: registered implementation plan

Scope: offline tracking candidate following the completed R4.1A audit. Historical
R4/R4.1 engines, fixtures, thresholds, production Safety and Contract 15A remain
frozen. This plan is written before candidate execution. No production acceptance
is implied by passing this candidate's tests.

1. A material, model-observable net demand with the opposite sign relative to the
   resolved command anchor supersedes directional context during sensor outage.
   A negative command derivative alone, or retreat without crossing that anchor,
   does not establish a reversal. Retire the obsolete epoch; retain the paired
   references, unresolved watch start, credited progress and valid suspicion.
2. Keep a separate directional-demand timestamp. Expected motion cannot predate
   the command that actually established that direction. Recovery uses that
   original timestamp; it does not restart the response grace at recovery.
   The unresolved watch's age remains independent and unchanged.
3. First valid recovery evaluates the current obligation with the preserved pair
   before refreshing a checkpoint. Invalid samples earn no motion or fault credit.
   Multiple material reversals update direction without erasing watch evidence.
4. Re-run R41-1..8 against the candidate. Add controls for partial retreat, healthy
   reversal, a reversal immediately before recovery, repeated outage reversals,
   retained prior suspicion, and repeatability/prefix causality. Record C9R only
   as a non-gate historical comparison. Full historical qualification is a later
   gate, required before any production-port conclusion.

Acceptance for this bounded repair: stuck R41-7 reaches suspected and confirmed;
healthy controls never confirm; invalid intervals do not change evidence/pairs;
directional supersession does not reset watch age or fabricate sensor values.
Any failed control blocks acceptance and must be reported without changing its
input or numeric thresholds to obtain a pass.
