$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskFolder='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskBinding=Get-Content -Raw (Join-Path $taskRoot 'v0_2/tests/tools/memphis_r12_solver_pressure_safety_v1/design_basis.json')|ConvertFrom-Json
$documents=@()
foreach($source in $taskBinding.final_design_sources){
 $path=Join-Path $taskFolder $source.filename
 $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($hash -cne $source.raw_sha256){throw ('FINAL_SOURCE_DRIFT '+$source.id)}
 $archive=[IO.Compression.ZipFile]::OpenRead($path)
 try{
  $reader=[IO.StreamReader]::new($archive.GetEntry('word/document.xml').Open())
  try{[xml]$xml=$reader.ReadToEnd()}finally{$reader.Dispose()}
  $nsm=[Xml.XmlNamespaceManager]::new($xml.NameTable)
  $nsm.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
  $body=$xml.SelectSingleNode('//w:body',$nsm);$rows=@();$i=0
  foreach($child in $body.ChildNodes){
   $i++
   $text=if($child.LocalName -eq 'tbl'){
    @($child.SelectNodes('./w:tr',$nsm)|ForEach-Object{
     @($_.SelectNodes('./w:tc',$nsm)|ForEach-Object{($_.SelectNodes('.//w:t',$nsm)|ForEach-Object{$_.InnerText}) -join ''}) -join ' | '
    }) -join ([Environment]::NewLine)
   }else{($child.SelectNodes('.//w:t',$nsm)|ForEach-Object{$_.InnerText}) -join ''}
   $rows+=@{locator=('B{0:D3}' -f $i);kind=$child.LocalName;text=$text}
  }
  $documents+=@{id=$source.id;filename=$source.filename;raw_sha256=$hash;blocks=$rows;
    locator_definition='1-based direct child of word/document.xml w:body, not a rendered page';
    tracked_insertions=$xml.SelectNodes('//w:ins',$nsm).Count;
    tracked_deletions=$xml.SelectNodes('//w:del',$nsm).Count}
 }finally{$archive.Dispose()}
}
$dest=Join-Path $PSScriptRoot 'final_basis_extracted.local.json'
New-Item -ItemType Directory -Path (Split-Path $dest) -Force|Out-Null
[IO.File]::WriteAllText($dest,(@{documents=$documents;method='READ_ONLY_OOXML_EXTRACTION_NO_MODEL_EXECUTION'}|ConvertTo-Json -Depth 25),[Text.UTF8Encoding]::new($false))
$documents|ForEach-Object{
 $id=$_.id
 $_.blocks|Where-Object {$_.text -match '压差|差压|板换|二次泵|备用|回充|补冷|定压|膨胀|5秒|5s|30秒|30s|10kPa|10 kPa|1100|1,100|50kPa|371.81|172.18|115|34m'}|ForEach-Object{[PSCustomObject]@{source=$id;locator=$_.locator;text=$_.text}}
}|ConvertTo-Json -Depth 8
