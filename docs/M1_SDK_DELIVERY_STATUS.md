# Offline SDK delivery status

2026-10-16 current entry: the unchanged streaming SDK completed outside-checkout 101-input development validation (run38493762797). v5 formal C3-C separately passed its limited software domain (run38833878662); SDK-only CLI files are not thereby formally qualified. The new [RC1 delivery bundle](../artifacts/m1-offline-delivery-rc1/README_FIRST.zh-CN.md) packages that exact SDK, current verdict, manuals and limits without editing sealed bytes. See [current readiness and remaining blockers](M1_RELEASE_READINESS.md). Older paragraphs below retain their historical build identities.

The original V0.2 wheel does not include the M1 driver/source-bound fixtures.
The new source SDK is a distinct offline-development delivery, never hardware
control or formal C3-C. Installation is now independently validated; complete
campaign independent evidence acceptance remains in progress.

Packaging Build001 stopped on a missing local historical ControlledJob.exe.
The file exists in the frozen source bundle; this was a hydration assumption,
not permission to fabricate a hash or repair Git objects. The partial directory
`D:/Github/c2c-m1-remote-evidence/sdk-delivery-v4-source-9122210-build001` remains
preserved. The revised packager reads/hash-verifies frozen archive members and
copies current runtime sources separately, without restoring over user files.
Next builds use new directories; failed partial deliveries are not overwritten.

Build002 pure-file packaging completed:674 listed payload files. Source commit
b95c03f is distinct from full campaign execution717a98d; the campaign-bound
67 runtime files still match exactly, including the same V4 driver. Delivery is
`D:/Github/c2c-m1-remote-evidence/sdk-delivery-v4-build002.zip` with RAW SHA256
d60fd8ceb9b93e5ca5e6c74aab2881d430ea755b1d9bb7d98151f3048ba6702e;
manifest RAW SHA2566a6a6b4d498820b6c12afd7aff1b4816e0b7af711e1a7da9ce88db10bcc33cd0.
This is SOURCE_SDK_PACKAGED_NOT_INSTALLATION_VALIDATED; no Python/model ran
locally. Outside-checkout, clean-environment model use still requires a separate
verified hosted-job smoke test before delivery acceptance.

Model examples require an explicit --run option and reject HIPPO. Default
--describe/--verify reads parameters only. Delivery manifest authenticity requires
a trusted external ZIP SHA, not merely a self-authenticating hash claim.

## Verified installation build (2026-10-14)

Run38458640545 completed on a separately created Python3.11.9 venv. Source
2f1bbdbb5197a60d1dabac7ce8ca687e0285a932 and installation control
e66e32dfce74f962ee8ed25eee228e4bc41070f4efb255f4375eb4197c1ce825 are
distinct from full campaign717a98d. The same campaign-bound V4 runtime bytes
remain unchanged. Official artifact SHA256:
9f0d4770b45687919ef43ca9b63477bcea42b457896d3472a5d358fe13ddfbff.
The tested source-sdk.zip SHA256 is
8e5496f21c948284dd262077456e17a96d70011bee098be3668b07861b57384c.

Independent local file readback verified all674 payload hashes,4 original raw
captures, actual Python PID2588 admitted to CPU25%/1024/2048MiB Job, release
proof, exit0 and cleanup-active0. SUT was imported from the unpacked SDK outside
checkout. Parameter description and a3-row independent-reference example passed.
The example ends TRACKING_FAULT_SUSPECTED by its registered fault fixture; it is
not a nominal-cooling or full-campaign result. No local Python/model was run.
See M1_SDK_INSTALL_READBACK.json and M1_SOFTWARE_USER_GUIDE.md for evidence/use.
The original Build001 failure and untested Build002 identities are preserved.
