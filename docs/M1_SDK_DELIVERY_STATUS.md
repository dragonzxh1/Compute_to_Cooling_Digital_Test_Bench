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

Model examples require an explicit --run option and reject HIPPO. Default
--describe/--verify reads parameters only. Delivery manifest authenticity requires
a trusted external ZIP SHA, not merely a self-authenticating hash claim.
