# Memphis equipment validation & failover V2

New offline development identity, using 00/01 final design. Customer limits and frozen M1 remain unchanged. All parameters are CUSTOMER_DESIGN, DERIVED_REQUIREMENT, ENGINEERING_ASSUMPTION, OEM_CONFIRMED (only cited exact vendor conditions), or UNKNOWN. R10 is comparison, not replacement approval.

`registration.json` preregisters every execution stage and engineering gate. `unit.py` reuses the single-rack hydraulic/HX/finite-volume solver with isolated duty/standby paths; `group_model/` is a versioned copy of Memphis Project V2 with explicit paired-valve evidence extensions. `audit.py` reads persisted outputs independently of the plant. `engineering.py` computes UA requirements, pump conflicts and equipment/RFI matrix. `worker.py` requires an externally verified hosted Windows Job before importing numerical modules. CPU25%, process1024MiB/Job2048MiB,480s per stage. Local model/native/Python execution prohibited.

Standby pump and CDU dynamics are explicitly assumed ramp/delay and isolation travel; no manufacturer recovery or hardware PLC proof is claimed. Unit paths share rack liquid inventory; disconnected CDU internal fluid/metal storage is unknown and omitted, preventing final equipment qualification. No load reduction is applied. Existing faults and old PASS evidence are preserved, with fresh regression stages and byte comparisons.

The hosted workflow produces raw JSON, completed M1 journals, source/environment hashes, actual PID/Job proof, stdout/stderr/exit/cleanup, independent audit and HTML report. Engineering FAILs are results, not execution failure. Integrity/numerical/audit failures stop the affected job and require a new source identity after repairs.
