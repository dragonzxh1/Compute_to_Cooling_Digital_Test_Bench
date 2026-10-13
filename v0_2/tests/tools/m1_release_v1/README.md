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

The installation check has now run in a separately created environment with the
unpacked SDK outside checkout and actual Python/Job admission before models.
Run38458640545 and docs/M1_SDK_INSTALL_READBACK.json establish parameter-query
and3-row example acceptance, not full campaign or formal release acceptance.
Existing v0.2 wheel and legacy package remain unchanged and distinct products.
