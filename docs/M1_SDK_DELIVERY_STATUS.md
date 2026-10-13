# Offline SDK delivery status

The original V0.2 wheel does not include the M1 driver/source-bound fixtures.
The new source SDK is a distinct offline-development delivery, never hardware
control or formal C3-C. Full campaign result and installation acceptance remain
required; no SDK acceptance PASS is claimed by writing packaging code.

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
