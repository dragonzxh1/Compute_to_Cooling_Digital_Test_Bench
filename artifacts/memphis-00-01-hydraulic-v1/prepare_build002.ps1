$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$taskRepo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$prefix='v0_2/tests/tools/memphis_00_01_hydraulic_v1'
$snapshot=Join-Path $PSScriptRoot 'source-7204410'
$old=Get-Content -LiteralPath (Join-Path $snapshot ($prefix+'/source_manifest.json')) -Raw|ConvertFrom-Json
$rows=@()
foreach($r in $old.source_files){
 if($r.path.StartsWith($prefix+'/') -or $r.path -ceq '.github/workflows/memphis-00-01-hydraulic-v1.yml'){continue}
 $local=if($r.path -ceq '.github/workflows/ci.yml'){$prefix+'/infra/ci-branch-only.yml'}else{$r.path}
 if((Get-FileHash -LiteralPath (Join-Path $taskRepo $local)).Hash.ToLowerInvariant() -cne $r.sha256){throw ('PROTECTED_DRIFT '+$r.path)}
 $rows+=$r
}
foreach($name in @('network.py','validation.py','basis.json','network_spec.json')){
 if((Get-FileHash (Join-Path $snapshot ($prefix+'/'+$name))).Hash -cne (Get-FileHash (Join-Path $taskRepo ($prefix+'/'+$name))).Hash){throw ('MODEL_CHANGED '+$name)}
}
$files=@(Get-ChildItem -LiteralPath (Join-Path $taskRepo $prefix) -Recurse -File|Where-Object {$_.Name -cne 'source_manifest.json'}|ForEach-Object{[IO.Path]::GetRelativePath($taskRepo,$_.FullName).Replace('\','/')})
$files+=@('.github/workflows/memphis-00-01-hydraulic-v1.yml')
foreach($p in $files){$rows+=@{path=$p;sha256=(Get-FileHash (Join-Path $taskRepo $p)).Hash.ToLowerInvariant()}}
$p=Get-Content -LiteralPath (Join-Path $taskRepo ($prefix+'/resource_environment.json')) -Raw|ConvertFrom-Json
$manifest=@{revision=$p.revision;cpu_rate=$p.cpu_rate;process_mb=$p.process_mb;job_mb=$p.job_mb;wall_seconds=$p.wall_seconds;
 source_files=@($rows|Sort-Object path);frozen_m1_modified=$false;solver_modified=$false;model_modified=$false;
 previous_execution_commit='0dd48316022ed1121d1dd94292a0c1080a5865ee';previous_manifest_sha256='6b2a9f282da9ca4824eea2fc41c6469f92450cb8ddbdbbf47ab7cedddeadb01c'}
[IO.File]::WriteAllText((Join-Path $taskRepo ($prefix+'/source_manifest.json')),($manifest|ConvertTo-Json -Depth 25),[Text.UTF8Encoding]::new($false))
# File parsing only. This does NOT launch Python, a model or any native program.
$tokens=$null;$parseErrors=$null
foreach($f in @(($prefix+'/run_remote.ps1'),($prefix+'/infra/build.ps1'))){
 $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $taskRepo $f),[ref]$tokens,[ref]$parseErrors)
 if($parseErrors.Count){throw ($parseErrors|Out-String)}
}
Get-FileHash -LiteralPath (Join-Path $taskRepo ($prefix+'/source_manifest.json'))
