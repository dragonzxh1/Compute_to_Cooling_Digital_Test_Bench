# Export only owned runtime evidence, not DSX or frozen input bundles.
param([Parameter(Mandatory)][string]$JobKey,[string]$IndicesCsv,[switch]$All)
$ErrorActionPreference='Stop'
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$taskRun='stream-'+$env:GITHUB_RUN_ID+'-'+$env:GITHUB_RUN_ATTEMPT
$taskExport=Join-Path $taskRepo ('artifacts/export/'+$JobKey)
if(Test-Path -LiteralPath $taskExport){throw 'FRESH_EXPORT_REQUIRED'}
New-Item -ItemType Directory -Path $taskExport|Out-Null
$taskPaths=@(
    ('liquid-recovery-v1/'+$taskRun+'/'+$JobKey)
    ('m1-autonomous-development/'+$taskRun+'/jobs/'+$JobKey)
)
if($All){$taskPaths=@(
    ('liquid-recovery-v1/'+$taskRun)
    ('m1-autonomous-development/'+$taskRun)
)}
elseif($IndicesCsv){foreach($i in $IndicesCsv.Split(',')){$taskPaths+=('m1-autonomous-development/'+$taskRun+('/cases/{0:d3}' -f [int]$i))}}
foreach($p in @('startup_inventory.json','prefix_plan.json')){
    $taskPaths+=('m1-autonomous-development/'+$taskRun+'/'+$p)
}
$taskPrefix='liquid-recovery-v1/'+$taskRun
if(Test-Path -LiteralPath (Join-Path $taskRepo ('artifacts/'+$taskPrefix))){
    $taskPaths+=@(Get-ChildItem -LiteralPath (Join-Path $taskRepo ('artifacts/'+$taskPrefix)) -Directory|Where-Object{$_.Name.StartsWith($JobKey+'-batch-')}|ForEach-Object{$taskPrefix+'/'+$_.Name})
}
if($JobKey -like 'startup-*'){$taskPaths+=('m1-autonomous-development/'+$taskRun+('/startup/{0:d3}' -f [int]($JobKey.Split('-')[-1])))}
foreach($p in ($taskPaths|Select-Object -Unique)){
    $taskSource=Join-Path $taskRepo ('artifacts/'+$p)
    if(-not(Test-Path -LiteralPath $taskSource)){continue}
    $taskDest=Join-Path $taskExport $p
    New-Item -ItemType Directory -Path (Split-Path $taskDest) -Force|Out-Null
    Copy-Item -LiteralPath $taskSource -Destination $taskDest -Recurse
}
if(-not(Test-Path -LiteralPath (Join-Path $taskExport ('liquid-recovery-v1/'+$taskRun+'/'+$JobKey)))){
    # Pure planning job has no native child; every real execution job must export it.
    if($JobKey -cne 'plan'){throw 'NATIVE_EVIDENCE_EXPORT_MISSING'}
}
