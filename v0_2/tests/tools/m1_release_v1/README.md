# Offline source SDK delivery

`package.ps1` performs only file/hash operations. It gathers the complete owned
V4 campaign source closure and frozen dependency bundle, LICENSE, parameter
documentation and `sdk_cli.py`, never DSX/workbench. Packaging does not prove
execution, qualification or release acceptance.

All payload files are listed with exact RAW SHA256 and length. The manifest
cannot authenticate itself: users must check the ZIP against a trusted external
SHA from the versioned release report before trusting its contents. No self-signed
hash inventory is described as a security signature.

The default CLI describes parameters without running models. `--run` requires an
explicit opt-in and rejects the known HIPPO hard-hang host. A small prefix example
does not substitute for the full development campaign or historical qualification.

The planned install check uses a separately created environment and an unpacked
package outside the repository, with actual Python/Job admission before models.
It has NOT been executed yet. No source SDK or installation PASS is claimed now.
Existing v0.2 wheel and legacy package remain unchanged and distinct products.
