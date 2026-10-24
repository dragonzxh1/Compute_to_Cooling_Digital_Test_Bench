param([int]$Port=8768,[string]$Python='D:/Github/c2c-itq-qualification-r3/Scripts/python.exe')
$ErrorActionPreference='Stop'
if($Port -lt 1024 -or $Port -gt 65535){throw 'Choose a local non-privileged port'}
if(-not(Test-Path -LiteralPath $Python -PathType Leaf)){throw 'Provide the path to a Python 3 standard-library runtime with -Python'}
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location -LiteralPath $taskRepo
try{
 Write-Host ('C2C workbench: http://127.0.0.1:'+ $Port + '/ (no local numerical model)')
 & $Python -B -m v0_2.tests.tools.engineering_design_mvp_v1.server --port $Port
 if($LASTEXITCODE -ne 0){throw 'Workbench service stopped with an error'}
}finally{Pop-Location}
