# Copy only the already-tested read-only launcher, not the formal runner.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$dest=Join-Path $PSScriptRoot 'run_readback.ps1'
if(Test-Path -LiteralPath $dest){throw 'NO_OVERWRITE'}
$text=[IO.File]::ReadAllText((Join-Path $repo 'v0_2/tests/tools/m1_c3c_v3/run_pre_sign_v2.ps1'))
$text=$text.Replace("'pre_sign_v2_control.json'","'control.json'").Replace('artifacts/m1-c3c-pre-sign/','artifacts/m1-c3c-v3-closure/').Replace('v0_2.tests.tools.m1_c3c_v3.pre_sign_v2_worker','v0_2.tests.tools.m1_c3c_v3_closure.readback_worker').Replace('C3C_PRE_SIGN_READBACK_PASS','C3C_V3_FINAL_PACKAGE_READBACK_PASS')
[IO.File]::WriteAllText($dest,$text,[Text.UTF8Encoding]::new($false))
