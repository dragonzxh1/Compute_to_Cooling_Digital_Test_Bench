param([Parameter(Mandatory)][string]$Delivery)
# Derived engineering presentation from immutable persisted evidence. No model runs.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest;$utf=[Text.UTF8Encoding]::new($false)
$graph=Get-Content (Join-Path $Delivery '04_TOPOLOGY_NETLIST.json') -Raw|ConvertFrom-Json
$actual=Get-Content (Join-Path $Delivery 'ACTUAL_AUDIT_RESULTS.json') -Raw|ConvertFrom-Json
$energy=Get-Content (Join-Path $Delivery 'PERSISTED_ENERGY_ATTRIBUTION.json') -Raw|ConvertFrom-Json
$customer=Get-Content (Join-Path $Delivery 'CUSTOMER_ORIGINAL_EXTRACTS.json') -Raw|ConvertFrom-Json
$doc=$customer.documents[0];$originalDoc=Join-Path 'C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010' $doc.document
if((Get-FileHash -LiteralPath $originalDoc).Hash.ToLowerInvariant() -cne $doc.raw_sha256){throw 'CUSTOMER_ORIGINAL_RECHECK'}
$zip=[IO.Compression.ZipFile]::OpenRead($originalDoc)
try{$rd=[IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open());try{[xml]$xml=$rd.ReadToEnd()}finally{$rd.Dispose()}}finally{$zip.Dispose()}
$ns=[Xml.XmlNamespaceManager]::new($xml.NameTable);$ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main');$pars=@($xml.SelectNodes('//w:body//w:p',$ns))
$extraText=($pars[765].SelectNodes('.//w:t',$ns)|ForEach-Object InnerText)-join ''
$doc.paragraphs+=@{xml_paragraph_zero_based=765;text=$extraText;status='ORIGINAL_REOPENED_POST_EXIT_FILE_REVIEW'}
[IO.File]::WriteAllText((Join-Path $Delivery 'CUSTOMER_ORIGINAL_EXTRACTS.json'),($customer|ConvertTo-Json -Depth 25),$utf)
$originalGraphHash=(Get-FileHash (Join-Path $Delivery '04_TOPOLOGY_NETLIST.json')).Hash.ToLowerInvariant()
# Expand two private standby pipe preconditioning loops that are already
# present in the unchanged physics and individually accounted in the CV CSV.
# They are NOT extra cooling of either tank while isolated.
$sourcePath=Join-Path $PSScriptRoot '../../v0_2/tests/tools/memphis_failure_closure_v1/group_model/sources.py'
$sourceLines=[IO.File]::ReadAllLines($sourcePath);$loopLine=0
for($i=0;$i -lt $sourceLines.Count;$i++){if($sourceLines[$i].Contains('def _loop(')){$loopLine=$i+1;break}}
$sourceHash=(Get-FileHash $sourcePath).Hash.ToLowerInvariant()
$auxEdges=@();$auxWitnesses=@();$times=@{};$pumpAt=@{}
foreach($f in $actual.BASELINE_EXACT.keyframes){$times[[double]$f.time_s]=$true}
Import-Csv -LiteralPath (Join-Path $Delivery '07_ALL_CONTROL_VOLUME_LEDGER.csv')|ForEach-Object{
 if($_.cv -in @('SOURCE_AND_PIPE_W2','SOURCE_AND_PIPE_RC') -and $times.ContainsKey([double]$_.time_s)){$pumpAt[$_.cv+'|'+[string]([double]$_.time_s)]=[double]$_.pump_direct_W}
}
foreach($path in @('W2','RC')){
 $pipe='PIPE_'+$path;$pump='PUMP_PRE_'+$path;$sink='PRECOOL_SINK_'+$path
 foreach($tag in @($pipe,$pump,$sink)){if($tag -notin $graph.nodes.tag){$graph.nodes+=@{tag=$tag;tag_authority='AUDIT_DERIVED_NOT_INSTALLED_TAG';alias_note='PIPE_W2 is the same selected W2 source pipe when online; no extra volume'}}}
 $sequence=@($pipe,$pump,$sink,$pipe)
 for($i=0;$i -lt 3;$i++){
  $e=[ordered]@{id=('PRELOOP_'+$path+'_'+$i);path=('PRELOOP_'+$path);source_component=$sequence[$i];source_port='OUT';destination_component=$sequence[$i+1];destination_port='IN';
   fluid_domain=('ISOLATED_STANDBY_PIPE_'+$path);nominal_flow_direction='SOURCE_TO_DESTINATION';actual_flow_direction='SEE_CV_BOUND_KEYFRAME';flow_m3_h=$null;temperature_C=$null;pressure_kPa=$null;pressure_status='NO_ABSOLUTE_PT';heat_transfer_kW=$null;pump_heat_kW=$null;sensor_id=$null;valve_id=$null;
   source_code_location=@{path='v0_2/tests/tools/memphis_failure_closure_v1/group_model/sources.py';line=$loopLine;raw_sha256=$sourceHash};
   design_provenance='ADDED_MODE_C_PRIVATE_PRECONDITIONING; NOT_CUSTOMER00_01; shares original pipe inventory';
   evidence=@('SOURCE_CONFIRMED_BY_CODE','CONFIRMED_BY_RUNTIME_CV_PUMP');derived_display_extension=$true}
  $auxEdges+=[pscustomobject]$e
 }
}
$graph.edges+=@($auxEdges)
$graph.instruments+=@{id='TRANSFER_FT_CONTROLLER_CHANNEL';location='A/B selected transfer loop';type='NOT_PRESENT_IN_SOURCE_OBSERVATION';installed='NOT_VERIFIED';evidence='NeutralBufferPlant sets last_load_q=main, source observer publishes that330main flow, not transfer414 physical truth'}
$graph.instruments+=@{id='NEW_TRANSFER_PUMP_M1_COVERAGE';location='A/B transfer pump';type='NOT_PROVEN_BY_THIS_AUDIT';installed='NOT_VERIFIED';evidence='Frozen M1 lanes supervise three secondary-unit actuators; no claim every added primary actuator is covered'}
$graph.thermal_edges+=@{id='SOURCE_COOLER_EXTERNAL_REJECTION';type='EXTERNAL_HEAT_ONLY_NO_MASS';hot_domain='SELECTED_SOURCE_PIPE';cold_domain='EXTERNAL_AMBIENT_REFERENCE';authority='Source capacity model, not an explicitly modeled basin liquid'}
$graph.thermal_edges+=@{id='RC_EXTERNAL_SERVICE';type='EXTERNAL_HEAT_ONLY_NO_MASS';hot_domain='B_PG25';cold_domain='EXTERNAL_RC_COLD_SERVICE';capacity_kW=1000;authority='Additional assumed service, not W2 counted twice'}
foreach($path in @('W2','RC')){$graph.thermal_edges+=@{id=('PRECOOL_EXTERNAL_'+$path);type='EXTERNAL_HEAT_ONLY_NO_MASS';hot_domain=('ISOLATED_STANDBY_PIPE_'+$path);cold_domain='ADDITIONAL_MODE_C_THERMAL_SERVICE';capacity_kW=100;authority='Registered cap only; actual heat is limited by temperature and recorded in CV external term'}}
foreach($f in $actual.BASELINE_EXACT.keyframes){
 foreach($path in @('W2','RC')){
  $online=if($path -eq 'W2'){$f.source_path -eq 'W2' -and $f.source_m3_h -gt 0}else{$f.recharge_m3_h -gt 0}
  $q=0.;$key='SOURCE_AND_PIPE_'+$path+'|'+[string]([double]$f.time_s)
  if(-not $online){if(-not $pumpAt.ContainsKey($key)){throw 'AUX_CV_WITNESS_MISSING'};$q=$pumpAt[$key]*.65/20000*3600;if([Math]::Abs($q-90) -gt 1e-7){throw 'AUX_QH_LEDGER_DIFFERENCE'}}
  $auxWitnesses+=@{time_s=$f.time_s;path=$path;online_main=$online;private_preloop_flow_m3_h=$q;runtime_CV_row=$key;private_pump_W=$(if($online){0}else{$pumpAt[$key]});method='Actual persisted CV pump heat / registered20000Pa/.65efficiency; compare source-loop quadratic QH=90'}
 }
}
$graph|Add-Member -NotePropertyName private_preconditioning_runtime_witnesses -NotePropertyValue $auxWitnesses
foreach($snapshot in @($graph)+@($graph.runtime_keyframes)){
 foreach($edge in $auxEdges){
  $copy=$edge|ConvertTo-Json -Depth 20|ConvertFrom-Json;$path=$copy.path.Substring(8)
  $when=if($snapshot.PSObject.Properties.Name -contains 'runtime_time_s'){$snapshot.runtime_time_s}else{1800.}
  $w=@($auxWitnesses|Where-Object {$_.path -ceq $path -and [Math]::Abs([double]$_.time_s-[double]$when) -lt 1e-8})
  if($w.Count -ne 1){throw 'AUX_FRAME_BINDING'}
  $copy.flow_m3_h=$w[0].private_preloop_flow_m3_h;$copy.actual_flow_direction=if($copy.flow_m3_h -gt 0){'SOURCE_TO_DESTINATION'}else{'STOPPED'}
  if($copy.source_component -like 'PUMP_PRE_*'){$copy.pump_heat_kW=$w[0].private_pump_W/1000}
  if($snapshot -eq $graph){
   $target=@($graph.edges|Where-Object id -ceq $copy.id)[0];$target.flow_m3_h=$copy.flow_m3_h;$target.actual_flow_direction=$copy.actual_flow_direction;$target.pump_heat_kW=$copy.pump_heat_kW
  }else{$snapshot.edges+=@($copy)}
 }
 $snapshot.nodes=$graph.nodes;$snapshot.thermal_edges=$graph.thermal_edges
 foreach($e in $snapshot.edges){
  $design=if($e.path -like 'SECONDARY_*'){68.37}elseif($e.path -like 'CDU_PRIMARY_*'){110}elseif($e.path -like 'PRELOOP_*'){90}else{330}
  $e|Add-Member -NotePropertyName design_flow_m3_h -NotePropertyValue $design -Force
 }
}
[IO.File]::WriteAllText((Join-Path $Delivery '04_TOPOLOGY_NETLIST.json'),($graph|ConvertTo-Json -Depth 35),$utf)
# Add netlist-identical private loops to the editable full drawing.
$auxSvg='<g font-family="Arial,Microsoft YaHei" font-size="14" fill="#172b3a">'
$y=0
foreach($path in @('W2','RC')){
 $auxSvg+='<text x="24" y="'+($y+25)+'">PRELOOP_'+$path+' · 私有备用管预冷，隔离于罐；与原管容积相同，不重复加储液</text>'
 $es=@($auxEdges|Where-Object path -eq ('PRELOOP_'+$path));$j=0
 $lastWitness=@($auxWitnesses|Where-Object {$_.path -ceq $path -and $_.time_s -eq 1800})[0]
 foreach($e in $es){$x=24+$j*450;$auxSvg+='<g data-edge-id="'+$e.id+'"><text x="'+$x+'" y="'+($y+55)+'">'+$e.source_component+' OUT → '+$e.destination_component+' IN</text><text x="'+$x+'" y="'+($y+82)+'">Q末态 '+$lastWitness.private_preloop_flow_m3_h.ToString('F3')+' m³/h；预冷100kW为上限非实际换热</text></g>';$j++}
 $y+=110
}
$auxSvg+='</g>'
foreach($file in @('01_MODEL_ACTUAL_PID.svg','02_MODEL_ACTUAL_PID_EDITABLE.svg')){
 $p=Join-Path $Delivery $file;$svg=[IO.File]::ReadAllText($p);$m=[regex]::Match($svg,'viewBox="0 0 (\d+) (\d+)"');$height=[int]$m.Groups[2].Value;$width=[int]$m.Groups[1].Value
 $svg=$svg.Replace($m.Value,('viewBox="0 0 '+$width+' '+($height+240)+'"')).Replace('</svg>',('<text x="24" y="83" font-family="Arial,Microsoft YaHei" font-size="14">登记设计点：主环/转移/源/RC 330m³/h；每CDU一次110，二次68.37；实际Q见各连接，不是厂家保证。</text><g transform="translate(0 '+$height+')">'+$auxSvg+'</g></svg>'))
 foreach($e in $graph.edges){if(-not $svg.Contains('data-edge-id="'+$e.id+'"')){throw 'DERIVED_DRAWING_NETLIST_MISSING_EDGE'}}
 [IO.File]::WriteAllText($p,$svg,$utf)
}
[IO.File]::WriteAllText((Join-Path $Delivery 'STANDBY_PRECONDITIONING.svg'),('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1460 250"><rect width="100%" height="100%" fill="white"/>'+$auxSvg+'</svg>'),$utf)
$htmlPath=Join-Path $Delivery '14_INTERACTIVE_ENGINEERING_REPORT.html';$originalHtml=(Get-FileHash $htmlPath).Hash.ToLowerInvariant()
$js=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'delivery_replay_patch.js'))
$net=@{edges=$graph.edges;precool_flow_m3_h=$actual.BASELINE_EXACT.parameters.precool_flow_m3_h;private_preconditioning_runtime_witnesses=$auxWitnesses}|ConvertTo-Json -Depth 20 -Compress
$html=[IO.File]::ReadAllText($htmlPath).Replace('</script>',("`nconst MODEL_NETLIST="+$net+";`n"+$js+"`n</script>"))
$html=$html.Replace('const w=600,h=235,','const w=Math.max(260,document.getElementById(id).clientWidth),h=260,')
$html=$html.Replace("(80+i*160)","(30+i*w/2)")
$html=$html.Replace("E(k)+'</text>'", "E(({A_cold_m3:'A罐',B_cold_m3:'B罐',rack_C:'机柜入口',source_return_C:'冷源回液',A_delta_U_MJ:'A储能',B_delta_U_MJ:'B储能',source_m3_h:'源侧',transfer_m3_h:'转移'})[k]||k)+'</text>'")
$html=$html.Replace('</style>','#pid{overflow-x:auto;max-width:100%}#pid>svg{min-width:1200px}#pid text[font-size="12"]{font-size:14px}#point{overflow-wrap:anywhere}.plots{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}@media(max-width:760px){.plots{grid-template-columns:minmax(0,1fr)}}</style>')
[IO.File]::WriteAllText($htmlPath,$html,$utf)
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'delivery_replay_patch.js') -Destination (Join-Path $Delivery 'DELIVERY_REPLAY_PATCH.js')
function X($v){[System.Net.WebUtility]::HtmlEncode([string]$v)}
$s=[Text.StringBuilder]::new()
$null=$s.Append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1120" role="img"><title>仿真测点位置与真实末态温层</title><rect width="100%" height="100%" fill="white"/><g font-family="Arial,Microsoft YaHei" fill="#172b3a"><text x="24" y="32" font-size="22">仿真测点与接口位置 · 不等于现场已安装仪表</text><text x="24" y="62" font-size="15">17TT来自源码层索引；以下温度是1800s物理真值，不伪称为已发布测量。真实安装高程及PT未确认。</text>')
foreach($item in @(@{name='A';x=80},@{name='B';x=650})){
 $name=$item.name;$x=$item.x;$p=$actual.BASELINE_EXACT.keyframes[-1].profile.PSObject.Properties[$name].Value
 $null=$s.Append('<rect x="'+$x+'" y="125" width="160" height="680" fill="#f1f5f9" stroke="#334155"/><text x="'+$x+'" y="110" font-size="20">TANK_'+$name+' 15 m³ / 80层</text>')
 for($i=0;$i -lt 17;$i++){
  $idx=[Math]::Round($i*($p.Count-1)/16);$y=790-$i*40;$tc=([double]$p[$idx]-273.15).ToString('F3',[Globalization.CultureInfo]::InvariantCulture)
  $null=$s.Append('<circle cx="'+($x+190)+'" cy="'+$y+'" r="13" fill="white" stroke="#334155"/><path d="M'+($x+160)+' '+$y+'H'+($x+177)+'" stroke="#334155"/><text x="'+($x+216)+'" y="'+($y+5)+'" font-size="15">TT_'+$name+'_'+$i+' · 层'+$idx+' · '+$tc+'°C</text>')
 }
 $null=$s.Append('<text x="'+$x+'" y="845" font-size="16">顶部：负载热入 / 源侧热出</text><text x="'+$x+'" y="875" font-size="16">底部：源侧冷入 / 负载冷出</text>')
}
$null=$s.Append('<text x="24" y="945" font-size="17">源侧：备用管近端TT、远端TT及FT进入冷就绪判断；阀位/转速反馈进入切换互锁。</text><text x="24" y="982" font-size="17">二次侧：各6柜单元的入口温度、回温、流量和泵速经延迟传感器进入M1。</text><text x="24" y="1019" font-size="17">压力：存在准稳态差压解；绝对PT、静压、NPSH及水锤未建模，不能填假值。</text><text x="24" y="1060" font-size="16">测点来源：ClosurePlant.observation；位置按17个round索引映射，不是罐厂家布点图。</text></g></svg>')
[IO.File]::WriteAllText((Join-Path $Delivery 'INSTRUMENT_LOCATIONS.svg'),$s.ToString(),$utf)
$frameA=$actual.BASELINE_EXACT.keyframes[-1];$ta=$frameA.tanks.A;$profileA=$frameA.profile.A
$coldCount=@($profileA|Where-Object {$_ -le 314.5948}).Count
$fmt={param($v)([double]$v).ToString('F3',[Globalization.CultureInfo]::InvariantCulture)}
$tankSvg=[Text.StringBuilder]::new('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 960" role="img"><title>A罐四接口与实际温层</title><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#334155"/></marker></defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial,Microsoft YaHei" fill="#172b3a"><text x="24" y="36" font-size="25">A罐四接口与温层 · BASELINE_EXACT · 1800s</text><text x="24" y="70" font-size="17">实际源码功能图，非施工图/CFD。温度为仿真物理真值；颜色按41.4448°C阈值区分，不是现场热像。</text>')
for($i=0;$i -lt $profileA.Count;$i++){
 $y=140+(1-($i+1)/$profileA.Count)*640;$color=if($profileA[$i] -le 314.5948){'#559ac0'}else{'#d9b58c'}
 $null=$tankSvg.Append('<rect x="465" y="'+$y+'" width="270" height="'+(640/$profileA.Count)+'" fill="'+$color+'"/>')
}
$null=$tankSvg.Append('<rect x="465" y="140" width="270" height="640" fill="none" stroke="#334155" stroke-width="2"/><text x="515" y="125" font-size="22">TANK_A · 15m³</text>')
$ports=@(
 @{x1=35;y1=180;x2=460;y2=180;label=('HX_A_TRANSFER热回液入罐 '+(& $fmt ($ta.load_m3_s*3600))+'m³/h');temp=(& $fmt ($ta.return_k-273.15));tx=35;ty=150},
 @{x1=740;y1=180;x2=1150;y2=180;label=('顶部去源泵 '+(& $fmt ($ta.source_m3_s*3600))+'m³/h');temp=(& $fmt ($ta.old_k[-1]-273.15));tx=760;ty=150},
 @{x1=1150;y1=735;x2=740;y2=735;label=('冷源返回底部 '+(& $fmt ($ta.source_m3_s*3600))+'m³/h');temp=(& $fmt ($ta.source_in_k-273.15));tx=760;ty=690},
 @{x1=460;y1=765;x2=35;y2=765;label=('底部去转移泵 '+(& $fmt ($ta.load_m3_s*3600))+'m³/h');temp=(& $fmt ($ta.old_k[0]-273.15));tx=35;ty=710}
)
foreach($p in $ports){$null=$tankSvg.Append('<path d="M'+$p.x1+' '+$p.y1+'L'+$p.x2+' '+$p.y2+'" stroke="#334155" stroke-width="2" fill="none" marker-end="url(#a)"/><text x="'+$p.tx+'" y="'+$p.ty+'" font-size="17">'+(X $p.label)+'</text><text x="'+$p.tx+'" y="'+($p.ty+25)+'" font-size="19">'+$p.temp+'°C</text>')}
$down=($ta.load_m3_s-$ta.source_m3_s)*3600
$null=$tankSvg.Append('<path d="M600 270V620" stroke="#334155" stroke-width="3" marker-end="url(#a)"/><text x="755" y="410" font-size="19">层间净向下 '+(& $fmt $down)+'m³/h</text><text x="755" y="445" font-size="17">各闭合回路进出质量相等，非漏水。</text><text x="35" y="420" font-size="19">上部主体约46°C</text><text x="35" y="455" font-size="17">底层仍可输出约40.4°C</text><text x="35" y="490" font-size="17">但大体积冷层没有恢复</text><text x="24" y="840" font-size="19">合格冷层 '+$coldCount+' / '+$profileA.Count+'；一格 '+(15/$profileA.Count)+'m³。这个体积随网格变化，不是真实罐可用冷量保证。</text><text x="24" y="880" font-size="18">A罐1800s净蓄热 '+(& $fmt $energy.tanks.A.stored_delta_MJ)+'MJ；独立RC只接B罐，不能替A罐恢复。</text><text x="24" y="920" font-size="17">接口角色依据00-P455/P724，但转移HX/第三回路是新增候选；绝对压力、真实布水器与OEM性能未验证。</text></g></svg>')
[IO.File]::WriteAllText((Join-Path $Delivery 'A_TANK_FOUR_PORTS.svg'),$tankSvg.ToString(),$utf)
$html=[IO.File]::ReadAllText($htmlPath).Replace('<p id="pidnote"></p>','<p id="pidnote"></p><p><a href="A_TANK_FOUR_PORTS.svg" target="_blank">基线1800s：A罐四接口与温层详图</a> · <a href="INSTRUMENT_LOCATIONS.svg" target="_blank">仿真测点位置</a> · <a href="01_MODEL_ACTUAL_PID.svg" target="_blank">完整可编辑功能图</a></p>')
[IO.File]::WriteAllText($htmlPath,$html,$utf)
$mdPath=Join-Path $Delivery '13_ENGINEERING_REPORT_ZH.md';$originalMd=(Get-FileHash $mdPath).Hash.ToLowerInvariant()
$b=$actual.BASELINE_EXACT;$diag=$actual.TRANSFER330_DIAGNOSTIC;$text=[Text.StringBuilder]::new()
$null=$text.AppendLine("`n## 独立官方核验后补充的账本解读`n")
$null=$text.AppendLine('本节是对已保存CSV/温层的文件级算术及显示增强，不是重新运行模型。原始执行版报告和HTML仍完整保存在官方raw ZIP；本包记录两版哈希。')
foreach($name in @('A','B')){$t=$energy.tanks.PSObject.Properties[$name].Value;$null=$text.AppendLine(($name+'罐：负载回路净输入 '+$t.load_loop_net_MJ.ToString('F6')+' MJ；源/回充回路净输入 '+$t.source_loop_net_MJ.ToString('F6')+' MJ；环境 '+$t.ambient_MJ.ToString('F6')+' MJ；储能净变化 '+$t.stored_delta_MJ.ToString('F6')+' MJ。正值为变暖，负值为变冷。泵热已在接口焓流，不再重复相加。'))}
$mix=$energy.bottom_cell_identity
$null=$text.AppendLine(('A底层瞬时端口零变化混合解约 '+$mix.zero_rate_mixing_temperature_C.ToString('F6')+'°C，实际底层 '+$mix.actual_start_C.ToString('F6')+'°C；这解释低温出口与上层热库存并存，不是未来温度预测。'))
$aa=@($diag.final_challenge|Where-Object tank -eq 'A')
$null=$text.AppendLine(('转移阻力单变量对照恢复A合格冷库存到 '+$diag.curves[-1].A_cold_m3+' m³，但A再次90s出液升温分别 '+$aa[0].rise_K.ToString('F6')+' K及'+$aa[1].rise_K.ToString('F6')+' K，仍超过0.5 K，完整双罐储备仍FAIL。库存量、绝对供温、出液温升必须分别判断，不能挑选通过项。'))
$null=$text.AppendLine('图纸/曲线界面已按所选案例及实际过去快照同步；未到达的详细快照不会用未来快照补齐。INSTRUMENT_LOCATIONS.svg明确区分虚拟测点位置、物理真值和未确认现场仪表。')
if($actual.PSObject.Properties.Name -contains 'TRANSFER330_SECOND650'){
 $second=$actual.TRANSFER330_SECOND650;$pre=@($second.second_fault_preconditions|Where-Object status -ne 'PASS')
 $null=$text.AppendLine(('650s真实连续末态二次故障：事前双罐组件资格 '+$(if($pre.Count -eq 0){'PASS'}else{'FAIL'})+'；随后90秒结果 '+$second.grades.SECOND_FAULT_90S+'；最高入口 '+$second.second_fault.maximum_inlet_C.ToString('F6')+'°C，最低负荷流量 '+$second.second_fault.minimum_load_m3_h.ToString('F6')+'m³/h。'))
 $null=$text.AppendLine('该二次试验保留第一次W1失效，再失去W2；没有虚构已修复W1或新增W3。第二90秒维持供冷与长期恢复可用冷源是不同义务；两个湿冷源均失效后不能声称冷源已恢复，长期源侧恢复仍未闭合。')
}
$null=$text.AppendLine('网格对照的精确冷体积随单层体积变化；实际再次放冷失败仍需单独保留。20/40/80/160及dt.05的数值只适用于注册的一维、常物性、未标定混合假设。')
$null=$text.AppendLine('另外还原了W2及RC备用输送管内部的90m³/h私有预冷循环。它们使用额外注册的100kW预冷服务，实际功率由温差限幅；原CV账本已经计入。在线主流建立时对应私有循环停止；RC主回充停止后，管内预冷不等于仍在给B罐补冷。两条路径已由逐控制体泵热记录绑定加入机器netlist及全图，不新增或重复计算管容积。')
$null=$text.AppendLine('控制可观察性也有边界：新增转移环的约414m³/h未作为独立FT字段进入源侧控制器；NeutralBufferPlant发布的last_load_q是中性主环330m³/h。A恢复逻辑根据17TT估计触发4源泵，但未核验源流量超过实际转移流量。冻结M1本轮监督的是三个二次单元执行器，不能据此宣称新增一次侧所有泵阀均已获得M1故障覆盖。建议先完成转移FT、温层就绪及联锁的设计绑定，不擅改冻结M1或现场控制。')
$null=$text.AppendLine("`n### 分项工程状态`n")
$qualified650=$false
if($actual.PSObject.Properties.Name -contains 'TRANSFER330_SECOND650'){$v=$actual.TRANSFER330_SECOND650;$qualified650=@($v.second_fault_preconditions|Where-Object status -ne 'PASS').Count -eq 0 -and $v.grades.SECOND_FAULT_90S -ceq 'PASS'}
$windowStatus=if($qualified650){'650秒登记窗口前置合格、第二90秒验证通过'}else{'未证实650秒前置合格的完整第二90秒'}
$null=$text.AppendLine(('软件验证：有界开发审计和官方证据独立核验完成，不是正式C3-C或硬件资格。模型拓扑：代码、运行及功能图已绑定，现场实装/ISA施工图未确认。双罐储备：'+$windowStatus+'；1800秒仍有温升不合格，持续恢复与长期源恢复未闭合。客户一致性：新增第三介质环、RC及预冷服务不属于00/01已确认原拓扑。OEM：CALIBRATION_REQUIRED。采购：NOT_APPROVED。总体：MEMPHIS_ENGINEERING_NOT_APPROVED。'))
$null=$text.AppendLine('归因：未发现罐四端口接反或离散质量/层间通量符号错误；一格冷体积属于MODEL_NUMERICAL_ISSUE的精度限制；原T2源流量低于实际转移，属于条件性PHYSICAL_DESIGN_LIMITATION及客户/候选拓扑不一致；独立转移FT和持续双罐Ready缺失属于CONTROL_LOGIC_GAP。不能将这些合并成客户00/01设计已被证明失败，也不能通过改名称将控制缺口当成代码修复。')
[IO.File]::WriteAllText($mdPath,([IO.File]::ReadAllText($mdPath)+$text.ToString()),$utf)
$prov=@{method='DERIVED_PERSISTED_EVIDENCE_PRESENTATION_ONLY';original_official_html_sha256=$originalHtml;original_official_report_sha256=$originalMd;
 original_official_netlist_sha256=$originalGraphHash;extended_netlist_sha256=(Get-FileHash (Join-Path $Delivery '04_TOPOLOGY_NETLIST.json')).Hash.ToLowerInvariant();private_preloop_witnesses=$auxWitnesses;
 derived_html_sha256=(Get-FileHash $htmlPath).Hash.ToLowerInvariant();derived_report_sha256=(Get-FileHash $mdPath).Hash.ToLowerInvariant();
 physical_outputs_changed=$false;M1_changed=$false;source_execution_changed=$false;diagram_scope='netlist and saved actual keyframes; derived instrument plot, not ISA construction drawing'}
[IO.File]::WriteAllText((Join-Path $Delivery 'DERIVED_PRESENTATION_PROVENANCE.json'),($prov|ConvertTo-Json -Depth 10),$utf)
