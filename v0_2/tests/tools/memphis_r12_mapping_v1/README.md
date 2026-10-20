# Memphis R12 topology mapping V1

Development adapter only. No frozen M1 imports, physical solver or 1800s run.

`topology.py`: separate Enum spaces, directed fluid graph and heat-only HX interfaces.
`control.py`: T2 unit sequence, T1 same-primary terminal guard, shared-source recharge unit sequence.
`tests.py`: independent assertions and explicitly synthetic observations, not PLC receipts.
`delivery.py`: the requested registries, consolidated Chinese report and full branch SVG atlas.

Run only with the dedicated GitHub workflow and `run_remote.ps1`. Do not execute Python on the unstable local machine. No external packages required. Python3.11.9, Windows-hosted isolated Job, CPU25%, process256MiB, Job512MiB,480s maximum. No old formal environment approval is inherited.

The actual graph remains `PARTIALLY_MAPPED_BLOCKED` for dynamics. PID005 disputed centreline is NOT a confirmed bypass; filter SERVICE keys are logical branch-availability abstractions, not invented field-valve tags. Per-CDU primary FT is a proposed required measurement interface, not claimed present on PID005. Pump follower control, measurement engineering limits, OEM pump curves/UA and M2 triggers remain OPEN.

Original R12 files are preserved by SHA256; the generated process-validation diagram is explicitly revisable. New approved design revisions must produce a new source-bound graph version. Never patch a sealed execution artifact.

No real hardware, production, procurement, Phase6, merge or formal C3-C. Old CDU/primary-B assumptions remain legacy evidence, not renamed R12 PASS.
