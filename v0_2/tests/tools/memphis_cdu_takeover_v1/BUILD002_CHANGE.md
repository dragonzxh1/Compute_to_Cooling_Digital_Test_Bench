# Build002 — measured failed-primary branch isolation

Build001 execution d05da9b198b7da7b330bf375cadbe9695c06a707 / run39440741985 is preserved, not patched or rerun in place.

Actual C_PRIMARY_NO_FLOW evidence: at42–57s the failed A CDU has primary0, secondary47.0917786421m³/h; its B spare has primary110, secondary47.0917786421m³/h. The two secondary pumps share the same rack circuit. Waiting for B alone to reach68.37 before isolating uncooled A leaves a stable parallel-flow deadlock. At57.1s the controller times out into STANDBY_FAILED. This is a new project candidate-control defect, not a frozen M1 or customer-design verdict.

Build002 isolates only the selected unit's failed A primary/secondary branch and stops that old secondary pump when the released primary measurement is below88m³/h after the existing1s persistence. It does not inspect hidden fault schedules. B still must earn measured110primary/68.37secondary and the original thermal checks. A/B primary separation, one local pair, all physical valve/pump dynamics, fault latches and hard limits are unchanged.

Any coastdown/valve/startup interruption remains a physical flow failure; no continuous-cooling claim follows from eventual takeover. This early isolation is a candidate implementation under00/01 architecture, subject to final customer/OEM isolation and fault matrix confirmation. No hardware or construction approval.

New source identity and a fresh bounded DEVELOPMENT campaign are required; do not borrow Build001 PASS. Build001 source-failure thermal FAIL and all evidence remain unchanged.
