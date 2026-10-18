# Pure file hashes only; no document execution or model. Do not upload originals.
$ErrorActionPreference='Stop'
$dir='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
$expected=@{'00'='f366d8001fdb785c5b41cf149886eefac1ad9e79d1b498f0244cc2cdffd915b7';'01'='5c52fec8ad34b675cc6294d699754fb896f2e31abc120c4a6bc8dfac29b9e73c'}
$records=@{}
foreach($id in @('00','01')){$f=@(Get-ChildItem -LiteralPath $dir -Filter ($id+'*.docx'));if($f.Count -ne 1){throw 'EXACT_CUSTOMER_DOCUMENT'};$hash=(Get-FileHash -LiteralPath $f[0].FullName).Hash.ToLowerInvariant();if($hash -cne $expected[$id]){throw 'CUSTOMER_ORIGINAL_DRIFT'};$records[$id]=@{name=$f[0].Name;bytes=$f[0].Length;sha256=$hash}}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'local_original_hashes.json'),(@{method='LOCAL_POWERSHELL_PURE_FILE_SHA256_NO_MODEL';records=$records;originals_uploaded=$false;design_authority='00/01 FINAL; R10 NOT APPROVED REPLACEMENT'}|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$records|ConvertTo-Json -Depth 4
