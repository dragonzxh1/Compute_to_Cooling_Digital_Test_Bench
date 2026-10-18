param([Parameter(Mandatory)][string]$Root)
# Package-only clarification after remote evidence verification. No model or data edit.
$ErrorActionPreference='Stop'
$d=Join-Path $Root 'delivery';$p=Join-Path $d 'delivery_manifest.json'
if((Get-FileHash $p).Hash.ToLowerInvariant() -cne 'a00aff9a0a57403a51f39d3657f18ce54bfd7b11a12bf771567f9ef08a1075e2'){throw 'EXACT_REMOTE_DELIVERY_MANIFEST'}
$m=Get-Content $p -Raw|ConvertFrom-Json
foreach($r in $m.records){if($r.file -ceq 'engineering_report.html'){continue};if((Get-FileHash (Join-Path $d $r.file)).Hash.ToLowerInvariant() -cne $r.sha256){throw ('VERIFIED_DATA_CHANGED '+$r.file)}}
$m.presentation_overlay_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'delivery_view.js')).Hash.ToLowerInvariant()
$m|Add-Member -NotePropertyName presentation_revision -NotePropertyValue 'UI-clarity-v1.1: source versus secondary flow labels and actual cold-return event only; verified numerical evidence unchanged'
$m|Add-Member -NotePropertyName official_base_delivery_artifact_sha256 -NotePropertyValue '5a55750e34d1f51326e73cb99cf124608b18f71012c65d40fd47c39d8055af39'
$m.records=@(Get-ChildItem $d -File|Where-Object Name -cne 'delivery_manifest.json'|Sort-Object Name|ForEach-Object {@{file=$_.Name;bytes=$_.Length;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant()}})
[IO.File]::WriteAllText($p,($m|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
Get-FileHash $p
