param([Parameter(Mandatory)][string]$Original,[Parameter(Mandatory)][string]$Output)
# Presentation-only derivative. Original official HTML/ZIP remain untouched.
$ErrorActionPreference='Stop'
$originalHash=(Get-FileHash -LiteralPath $Original -Algorithm SHA256).Hash.ToLowerInvariant()
$html=Get-Content -LiteralPath $Original -Raw
$css='body{box-sizing:border-box;width:100%;overflow-wrap:anywhere}table{table-layout:fixed}td,th,pre{overflow-wrap:anywhere;word-break:break-word}td:last-child,th:last-child{width:44%}svg{display:block}h2{margin-top:2em}'
$html=$html.Replace('</style>',$css+'</style>')
$html=[regex]::Replace($html,'<td>(\{&quot;CHANGEOVER_CONTINUITY.*?\})</td>',{
 param($match)
 $d=[Net.WebUtility]::HtmlDecode($match.Groups[1].Value)|ConvertFrom-Json
 $items=@($d.PSObject.Properties|ForEach-Object {'<div style="margin-bottom:7px"><code>'+[Net.WebUtility]::HtmlEncode($_.Name)+'</code><br>'+[Net.WebUtility]::HtmlEncode([string]$_.Value)+'</div>'})
 return '<td>'+($items -join '')+'</td>'
})
# All registered plots use the same30..55C range in this completed run.
# Add units/ticks only; actual polyline points and45C threshold are untouched.
$html=$html.Replace('<rect width="760" height="240" fill="#fafafa"/>','<rect width="760" height="240" fill="#fafafa"/><text x="3" y="18" font-size="12">°C</text><text x="3" y="34" font-size="12">55</text><text x="3" y="106" font-size="12">45</text><text x="3" y="212" font-size="12">30</text>')
$html=$html.Replace('<h1>','<p>展示副本：只调整长字段换行和表格排版，数值/评分/曲线不改。官方HTML SHA-256：'+$originalHash+'。</p><h1>')
$raw=[Text.Encoding]::UTF8.GetBytes($html)
$stream=[IO.File]::Open($Output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
if((Get-FileHash -LiteralPath $Original -Algorithm SHA256).Hash.ToLowerInvariant() -cne $originalHash){throw 'ORIGINAL_HTML_CHANGED'}
