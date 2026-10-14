# Installed SDK full-input development acceptance

This version preserves v1 and the tested SDK ZIP bytes/source. It downloads the
original run38458640545 artifact, verifies ZIP SHA2568e5496f21c948284dd262077456e17a96d70011bee098be3668b07861b57384c,
creates a new pinned venv, and unpacks outside checkout. No replacement package,
candidate, fixture, expected result, mathematical threshold or timer is created.

All101 input indices and full row counts are registered in delivery_control.json
before execution. The unchanged installed CLI independently computes the frozen
reference and applies its unchanged comparator. A PASS requires every full
input, exact source/input identity, verified package before/after, actual installed
SUT import, venv identity and externally verified Python PID/Job/cleanup.

Per-case BEGIN/END and STOP records are fsynced to events.jsonl. Raw CLI output is
saved before parsing/acceptance. Resource limits remain CPU25%,1024/2048MiB,
480seconds; resource failure is not a candidate behavioral verdict. On failure
preserve all evidence; never change the sealed SDK or retry within that execution.

This is installed-user-workflow development verification, not another full
qualification or permission to waive P1/PF06/T09/hardware limitations. The prior
full V4 campaign result keeps its separate identity. The registered dispatcher
workflow routes this new version; its old v1 bytes remain at source2f1bbdb.
