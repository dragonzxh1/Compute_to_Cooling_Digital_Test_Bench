# First unsealed Memphis development execution — preserved FAIL

Run38936957083, source08bbb05f8536e94fda4b26a4a886bc4c2002484d.
Manifest28e79360d32ee5d807791409f821ef83ec9b6136eff53814589b1e42826b2047.
Official baseline ZIP digest ea461fca2e9ee7700200d50fa9b25fef69f54d4b7b45322cfadfc8a7ff042754.

NEGATIVE passed. NODE_PORT actual child had verified Job identity and exited0,
but Python's default Windows cp1252 pipe decoder rejected the upstream UTF-8
Chinese text. Reader thread raised UnicodeDecodeError, so communicate returned
no parsed output; outer result retained FAIL. No project dynamic cases ran.

Repair is explicit strict UTF-8 on the subprocess pipe; original upstream JS,
frozen M1, numerical expectations, resource guard and failed evidence unchanged.
New source commit/manifest required. No old PASS credit.
