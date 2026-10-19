param([Parameter(Mandatory)][string]$RunId)
# Interpret existing bounded JSON outputs only; no new physics/model execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;$delivery=Join-Path $repo 'artifacts/memphis-failure-closure-v1-delivery';$utf8=[Text.UTF8Encoding]::new($false)
function Read-Bounded([string]$name){$p=Join-Path $delivery $name;if((Get-Item $p).Length -gt 8000000){throw ('BOUNDED_JSON_REQUIRED '+$name)};return Get-Content $p -Raw|ConvertFrom-Json}
$dynamic=Read-Bounded 'dynamic_results.json';$old=Read-Bounded 'original_five_failures.json';$summary=Read-Bounded 'closure_summary.json';$robust=Read-Bounded 'robustness_results.json';$post=Read-Bounded 'actual_postcharge_discharge.json';$convergence=Read-Bounded 'tank_convergence.json';$hold=Read-Bounded 'pipe_ready_hold.json';$standby=Read-Bounded 'standby_inventory_results.json'
function Get-Case([string]$id){$r=@($dynamic|Where-Object id -ceq $id);if($r.Count -ne 1){throw ('EXACT_CASE_REQUIRED '+$id)};return $r[0]}
function Num($v){if($null -eq $v){return '未达到/无值'};return ([double]$v).ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)}
function Grade($r){return ('热{0} / 流{1} / 90s{2} / 源{3} / 储{4}' -f $r.grades.THERMAL_COMPLIANCE,$r.grades.HYDRAULIC_COMPLIANCE,$r.grades.'90S_CONTINUITY',$r.grades.SOURCE_RECOVERY,$r.grades.RESERVE_RECOVERY)}
$reproductions=@();$axes=@{}
foreach($r in $old){
 $p=$r.parameters;$axis=if($p.PSObject.Properties['mixing_m3_s'] -and $p.mixing_m3_s){'joint'}elseif($p.PSObject.Properties['second_source_failure'] -and $p.second_source_failure){'second'}elseif($p.PSObject.Properties['sensor_delay_s'] -and $p.sensor_delay_s -gt 1){'measurement'}elseif($p.PSObject.Properties['source_head_factor'] -and $p.source_head_factor -lt 1){'pump'}else{'capacity'}
 $v=[int]$p.tank_volume_m3;$fresh=Get-Case ('cause_'+$axis+'__original'+$v)
 foreach($key in @('maximum_inlet_C','maximum90_inlet_C','minimum_load_m3_h','cold_return_delay_s')){
  $a=$r.$key;$b=$fresh.$key
  if($null -eq $a -or $null -eq $b){if(($null -eq $a) -ne ($null -eq $b)){throw ('REPRODUCTION_NULL_DIFFERENCE '+$r.id+' '+$key)}}
  elseif([Math]::Abs([double]$a-[double]$b) -gt 1e-9){throw ('REPRODUCTION_METRIC_DIFFERENCE '+$r.id+' '+$key)}
 }
 $reproductions+=@{old_id=$r.id;fresh_id=$fresh.id;old_raw_sha256=$r.raw_sha256;fresh_raw_sha256=$fresh.raw_sha256;status='FRESH_PHYSICAL_METRICS_REPRODUCED_NOT_PASS_REUSE'}
 $axes[$r.id]=$axis
}
if($reproductions.Count -ne 10){throw 'ALL10_ORIGINAL_FAILURES_REQUIRED'}
[IO.File]::WriteAllText((Join-Path $delivery 'original_failure_reproduction.json'),(@{run=[long]$RunId;source_commit=$summary.source_commit;cases=$reproductions}|ConvertTo-Json -Depth 20),$utf8)
$l=[Collections.Generic.List[string]]::new()
$l.Add('# 孟菲斯工程失败闭环决策表')
$l.Add('')
$l.Add('MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_NOT_VERIFIED；PROCUREMENT_RELEASE_STATUS=BLOCKED。仅90柜项目中一个18柜冷源组的离线、有界、未标定工程模型，不是90柜整体批准、Tier认证或新C3-C资格。')
$l.Add('')
$l.Add('本页整合实际数字及适用边界；自动原始中文报告、CSV/JSON、原始ZIP和事件均保留，不改写历史结果。')
$l.Add(('执行source：{0}；manifest RAW SHA256：{1}；run：{2}。本轮{3}次动态、{4}次独立罐放冷、40个受控阶段。原始两组各17项/各5失败按官方ZIP追溯，10个失败工况重新执行的关键物理指标复现一致。' -f $summary.source_commit,$summary.manifest_sha256,$RunId,$summary.dynamic_trials,$summary.tank_trials))
$l.Add('')
$l.Add('|原始失败（15/20m³各一项）|原峰温°C / 最小负荷流量m³/h|主要原因|新方案15m³的实际峰温 / 流量 / 冷返秒|分项结果|OEM保证与采购|')
$l.Add('|---|---|---|---|---|---|')
$reason=@{capacity='冷源能力20%下降→温升触发备用动作→后期停流；不是简单超过45°C才失败';pump='H0下降3%→源侧交点不足330→无合格冷返';measurement='1.2s链路超过1s有效期→正确锁存拒绝，不是可放宽的软件门槛';second='W1在30s失效、W2在60s再次失效→无冷源，库存耗尽';joint='湿球32/能力降20%/暖管/低H0/偏差与延迟同时存在'}
$guarantee=@{capacity='共同工况与模块退出性能面；BLOCKED';pump='Q-H/效率/NPSHr/静压/退化和转速包络；BLOCKED';measurement='独立快链延迟/时间戳/诊断与电源；BLOCKED';second='独立第三源与接口/供电，业主双故障基准；BLOCKED';joint='统一不利角点整体验证，不能拼单轴极值；BLOCKED'}
foreach($axis in @('capacity','pump','measurement','second','joint')){
 $a=@($old|Where-Object {$axes[$_.id] -ceq $axis -and $_.parameters.tank_volume_m3 -eq 15})[0];$b=@($old|Where-Object {$axes[$_.id] -ceq $axis -and $_.parameters.tank_volume_m3 -eq 20})[0];$n=Get-Case ('cause_'+$axis+'__physical_modified15')
 $l.Add(('|{0}; {1}|{2}/{3}; {4}/{5}|{6}|{7} / {8} / {9}|{10}|{11}|' -f $a.id,$b.id,(Num $a.maximum_inlet_C),(Num $a.minimum_load_m3_h),(Num $b.maximum_inlet_C),(Num $b.minimum_load_m3_h),$reason[$axis],(Num $n.maximum_inlet_C),(Num $n.minimum_load_m3_h),(Num $n.cold_return_delay_s),(Grade $n),$guarantee[$axis]))
}
$l.Add('')
$l.Add('原02项的首次停流发生在131.4s/133.6s（故障后90s窗口结束于120s），仍使完整240s工况不合格；不能缩短统计窗口藏掉。原06项从t0即有曲线退化。原11项1.2s首次出现陈旧度拒绝。原12项首次超45°C为172.0s/215.3s，20m³仅延后失效，不能替代可用冷源。原16联合角点不等于每个因素都从30s才注入。完整首次违规、次生事件和原始hash见original_five_failures.json。')
$joint=Get-Case 'cause_joint__physical_modified15';$registeredJoint=Get-Case 'robust_D__16'
$l.Add(('新联合修改点的直接失败另含控制配置不匹配：10s阀动作配默认7s动作超时，{0}s锁存VALVE_NOT_AT_REQUESTED_TARGET、源泵许可停止，随后峰温{1}°C。不能把它解释成增容后仍然单纯热能力不足。另一个完整注册的联合变体robust_D__16使用12s动作超时，实际峰温{2}°C、源流量{3}m³/h、冷返{4}s；初始备用管条件也不同，故不能冒称只改单一超时的反事实，更不能把其PASS搬到原7s配置。后续须协调厂家最大阀响应/反馈延迟与保护设定，保留全部90s/45°C/330要求；未自动放宽默认保护。' -f (Num $joint.first_violations_s.protected),(Num $joint.maximum_inlet_C),(Num $registeredJoint.maximum_inlet_C),(Num $registeredJoint.source_final_m3_h),(Num $registeredJoint.cold_return_delay_s)))
$l.Add('')
$l.Add('## 联合稳健性与三个最终候选')
$l.Add('')
$l.Add('|研究配置|名义峰温°C|最小负荷流量m³/h|冷返秒|17项不合格/不完整|')
$l.Add('|---|---|---|---|---|')
foreach($name in @('A','B','C','D','E')){
 $r=Get-Case ('option_'+$name+'__nominal');$rr=@($robust|Where-Object candidate -ceq $name);$scope=if($rr.Count){($rr[0].failed_ids.Count.ToString()+'/17；'+($rr[0].failed_ids -join ', '))}else{'17项未运行，不授予ROBUST'}
 $l.Add(('|{0}|{1}|{2}|{3}|{4}|' -f $name,(Num $r.maximum_inlet_C),(Num $r.minimum_load_m3_h),(Num $r.cold_return_delay_s),$scope))
}
$l.Add('')
$l.Add('最终OPTION A：尽量保留00/01和15m³；研究A/B及单变量对照用于确定最低补强，不能把无测量Ready的A判成可采购方案。最终OPTION B：研究D，预冷+90%初充/17TT+快链+能力15%与速度3%候选裕量/备用泵。最终OPTION C：研究E，再加独立W3源侧接口与20m³；独立RC500/1000kW回充另外列项，未拼接成已通过的一整套。')
$l.Add('三者都不自动具备采购资格。新17项和旧17项不是完全相同的注册：新包加入预冷丧失、真正A隔离卡阀；快链安装改变实际测量通路，另有快链故障负控。原17项身份与结果没有被改写。共因/接管中二次故障是否属于业主设计基准，需业主另行确认；不自动套TierIII，也不自行排除失败。')
$l.Add('')
$l.Add('## 预冷、保持与能源账本')
$l.Add('')
$pre=$hold.prelude
$l.Add(('独立小循环A与独立冷服务/HX方案C，在同样100kW热能力假设下，从2.75m³、48.29°C暖管实际起算，温度条件首次达到{0}s；1200s后W2近端{1}°C、远端{2}°C。热力结果相同不代表真实水力隔离、塔低负荷运行或现场可施工性等价。' -f $pre.ready_times_s.W2,(Num $pre.final_temperatures_C.W2[0]),(Num $pre.final_temperatures_C.W2[-1])))
$l.Add(('预冷泵90m³/h@20kPa，登记效率0.65，实际预冷段平均线功率{0}kW；1200s泵能{1}MJ、环境热增{2}MJ、排热{3}MJ。此为备用管组件预处理，不是把整站IT负荷设零20min。塔风机/喷淋/冷服务COP未知，不把0.769kW冒称全部预冷电耗。' -f (Num ($pre.pump_J/$pre.duration_s/1000)),(Num ($pre.pump_J/1e6)),(Num ($pre.ambient_J/1e6)),(Num ($pre.rejected_J/1e6))))
$l.Add(('停泵后仍计入UA500W/K、46°C环境热增；登记温度边界在{0}s失去。但流量为零时Ready已经失效，不能继续许可。该保持时间只适用于此集中参数管模型，真实保温/死角/壁热容/测点尚未标定。B专用旁通缺路由与隔离证据，NOT_RUN。' -f $hold.first_temperature_readiness_loss_s))
$l.Add('90m³/h和100kW是已计算的候选，不是全球最小值；A需要湿源低负荷map、独立小泵及隔离/止回/近远端TT/FT和电源。C另需独立换热/冷服务。不能凭空认为00/01已有这些设备或旁通。')
$energy=@();$wire=$pre.pump_J/$pre.duration_s/1000
foreach($hours in @(1000.,4000.,8760.)){$energy+=[PSCustomObject]@{assumed_standby_hours_h=$hours;one_loop_wire_kW=$wire;pump_only_kWh=$wire*$hours;electricity_price_USD_kWh=$null;annual_cost_USD=$null;fan_spray_cold_service_electricity_kWh=$null;basis='ASSUMED_HOURS_NOT_ANNUAL_FORECAST; model constant90m3h20kPa eta0.65; excludes all other equipment'}}
$energy|Export-Csv -LiteralPath (Join-Path $delivery 'bounded_energy_sensitivity.csv') -NoTypeInformation -Encoding utf8BOM
$l.Add(('有界能耗敏感性（不是年耗预测）：每条独立小循环按1000/4000/8760小时假定运行，泵本身约{0}/{1}/{2}kWh；一次1200s暖管预冷的泵能为{3}kWh。电价、CAPEX、塔风/喷淋和冷服务电耗留空，不能据此宣称整系统年节能率。参数表见bounded_energy_sensitivity.csv。' -f (Num $energy[0].pump_only_kWh),(Num $energy[1].pump_only_kWh),(Num $energy[2].pump_only_kWh),(Num ($pre.pump_J/3600000))))
$l.Add('')
$l.Add('## 储罐：已测参数区域，不是实物合格证')
$l.Add('')
$l.Add('|15m³/85%/40.9448°C，A/B分别计算|20层升温K|160层升温K|dt细化差K|全部网格≤0.5K|数值状态|')
$l.Add('|---|---|---|---|---|---|')
foreach($tank in @('A','B')){foreach($short in @(0.,.05)){
 $r=@($convergence|Where-Object {$_.tank -ceq $tank -and $_.parameters.volume -eq 15 -and $_.parameters.fraction -eq .85 -and $_.parameters.mixing -eq .005 -and $_.parameters.short -eq $short -and $_.parameters.profile -ceq 'SHARP'})
 if($r.Count -ne 1){throw 'TANK_EXACT_PARAMETER_POINT'};$r=$r[0]
 $l.Add(('|{0}；混合0.005m³/s，短路{1}|{2}|{3}|{4}|{5}|{6}|' -f $tank,$short,(Num $r.rise20_K),(Num $r.rise160_K),(Num $r.dt_error_K),$r.all_grids_pass,$r.numerical_status))
}}
$l.Add('固定每个相邻层界面的m³/s混合量，在不同层数下不自动等于同一连续轴向扩散系数。因此非零混合的比较还含物理离散定义变化；表内数值差小不能单独证明物理收敛，整体NUMERICALLY_INCOMPLETE。没有挑有利细网格、没有改原Tank参考数学。0.005或5%是测试点，不是厂商允许最大混合/短路率。全部可接受/拒绝点在tank_convergence.csv。')
$l.Add('85%真实冷液与17TT保守可证明85%不是同一件事。拟议90%初充配17TT和0.2K保护余量，在单调温层、有效体积–高度已标定的假设下评估；原4TT不能独自作85%证明。FAT须以流量积分/热量计和完整90s出口曲线校核，覆盖回充后的真实分布、不同初始A/B状态、混合/短路和最坏回液，而不只看平均罐温。')
foreach($r in $standby.cases){$l.Add(('15m³、90%初冷40.5°C、零取水、46°C环境、混合0.001m³/s待机2h：UA={0}W/K时最后阈值冷库存{1}m³、环境增热{2}MJ。此为未标定假设，不作现场维持时间保证。' -f $r.UA_W_K,(Num $r.final_cold_m3),(Num $r.gain_MJ)))}
$l.Add('')
$l.Add('## 回充后能不能再次承担90秒')
$l.Add('')
$l.Add('|独立RC实际计算|最终源泵数|冷库存恢复判定|A/B初始出口°C与真实冷库存m³|实际末态再放冷A/B升温K|再次90s资格|')
$l.Add('|---|---|---|---|---|---|')
$reserve=@()
foreach($cap in @('500.0','1000.0')){
 $r=Get-Case ('recharge_new__'+$cap);$rr=@($post|Where-Object case -ceq $r.id);$a=@($rr|Where-Object tank -ceq 'A')[0];$b=@($rr|Where-Object tank -ceq 'B')[0]
 $aStart=$r.final_tanks_k.A[0]-273.15;$bStart=$r.final_tanks_k.B[0]-273.15
 $aVolume=@($r.final_tanks_k.A|Where-Object {$_ -le 314.5948}).Count*15/$r.final_tanks_k.A.Count
 $bVolume=@($r.final_tanks_k.B|Where-Object {$_ -le 314.5948}).Count*15/$r.final_tanks_k.B.Count
 $state=if(@($rr|Where-Object {$_.outlet_rise_K -gt .5}).Count -or $aStart -gt 41.4448 -or $bStart -gt 41.4448 -or $aVolume -lt 12.75 -or $bVolume -lt 12.75){'FAIL'}else{'INCOMPLETE：只有实际末态80层，未完成回充全动态跨网格'}
 $l.Add(('|{0}kW；最大回充{1}m³/h|{2}|{3}|{4}°C,{5}m³ / {6}°C,{7}m³|{8} / {9}|{10}|' -f $cap,(Num $r.max_recharge_m3_h),$r.final_source_pumps,$r.grades.RESERVE_RECOVERY,(Num $aStart),(Num $aVolume),(Num $bStart),(Num $bVolume),(Num $a.outlet_rise_K),(Num $b.outlet_rise_K),$state))
 $reserve+=@{id=$r.id;threshold_inventory_grade=$r.grades.RESERVE_RECOVERY;initial_outlet_C=@{A=$aStart;B=$bStart};actual_cold_m3=@{A=$aVolume;B=$bVolume};required_each_cold_m3=12.75;next90s_status=$state;actual_discharge=$rr}
}
$l.Add('库存达到阈值不能覆盖实际再次放冷的FAIL。回充阶段四泵暂时并联的性能/电耗与恢复3+1均须看实际事件，备用泵启动/并泵在模型中未具备OEM逐泵VFD动态标定。RC是另一个独立泵/HX/500或1000kW热服务，不是在线W2重复提供免费冷量。共享回充与独立回充、原120kPa不足及115.82kPa降阻候选均保留。')
$l.Add('500kW例B罐0.076K相对升温不等于冷储备合格：其起始出口已达44.188°C、阈值冷库存为0。1000kW例B罐冷库存只有10.313m³且再次放冷升温0.676K；A罐0.509K同样超过0.5K，不作有利四舍五入。两例在600s内均未恢复可供下一次90s的双罐储备，不能承诺连续二次故障容错。')
$l.Add('')
$l.Add('## 模块、泵、阀与共因：看实际后果')
$l.Add('')
$l.Add('|场景|峰温°C|最小负荷流量m³/h|末段源流量m³/h|冷返秒|结论分项|')
$l.Add('|---|---|---|---|---|---|')
foreach($id in @('modules__1.0','modules__1.15','modules__remaining4_V9_margin15pct','modules__remaining4_R10_maxspeed','modules__measured_design_flow_takeover','pumps__H0minus3_margin0.0','pumps__H0minus3_margin0.0154','pumps__H0minus3_margin0.03','pumps__isolated_pump_out_False','pumps__isolated_pump_out_True','valves__A_demand_no_stuck','valves__A_demand_stuck','valves__false_open_feedback','common__third_E','common__source_header_E','common__load_header_E')){
 $r=Get-Case $id;$l.Add(('|{0}|{1}|{2}|{3}|{4}|{5}|' -f $id,(Num $r.maximum_inlet_C),(Num $r.minimum_load_m3_h),(Num $r.source_final_m3_h),(Num $r.cold_return_delay_s),(Grade $r)))
}
$l.Add('表中“流”为负荷330判据，源330另由SOURCE_RECOVERY及末段实际源流量约束；完整设备水力资格因静压/NPSH/水锤未知而仍为INCOMPLETE。')
$l.Add('湿模块退出同时移除水力并联支路和散热能力，不能只除以模块个数。四模块各82.5m³/h、每模块≥679.038kW只是2716.15kW参考预算的必要下界；实际泵热、四泵回充与预冷热服务须另按实际流量/温度计账。需要WB/DB/PG物性/风机/喷淋/盘管map，未证明增加风机转速必然有效。')
$l.Add('H0−3%速度补偿只对登记合成Q-H适用；V9约34m与R10整曲线≤18m保持分开。表内流量PASS不是静压、MAWP、NPSH、水锤或设备采购适配PASS；V9静压未知。孤立单泵退出与W1故障接管中二次泵退出分别留档，不混基准。')
$l.Add('即使不卡阀，单负荷选择器break-before-make也会产生停流；源侧已按隔离需求转B，不代表负荷侧无间断。真正卡阀有实际B命令及未响应证据，不能用正确锁存FAULT冒充90s供冷通过。共用负荷总管失效不能靠加W3解决；必须评估不非法并通的独立负荷供液/缓冲/隔离拓扑。E的预冷全丧失注册是全部预冷支路共同失效，不是自动宣称单台预冷泵故障使全部独立设备失效。')
$boundary=Read-Bounded 'independent_event_boundary_file_proof.json';$unstuck=@($boundary.cases|Where-Object id -ceq 'valves__A_demand_no_stuck')[0];$stuck=@($boundary.cases|Where-Object id -ceq 'valves__A_demand_stuck')[0]
$l.Add(('独立解码原始记录：无卡阀例在{0}s发B命令，{1}s观测到负荷选B、{2}s观测到源选B；完整物理步最低流量{3}，5Hz发布测量最低却是{4}m³/h，说明抽样可能漏掉瞬时零流量。真实卡阀例发B命令{5}帧，未响应{6}帧，物理最低{7}m³/h，实际负荷始终未选B；绝非未激发的PASS。事件增强HTML及critical_event_points.csv保留两例每0.1s物理步，不用1s抽样掩盖不利点。' -f (Num $unstuck.first_B_request_s),(Num $unstuck.first_actual_load_B_s),(Num $unstuck.first_actual_source_B_s),(Num $unstuck.minimum_all_physical_steps_load_m3_h),(Num $unstuck.minimum_published_load_m3_h),$stuck.issued_B_requests,$stuck.nonresponse_frames,(Num $stuck.minimum_all_physical_steps_load_m3_h)))
$plotProof=Read-Bounded 'critical_plot_provenance.json'
foreach($p in $plotProof.cases){$l.Add(('{0}：全步核对的B路径实际冷返为{1}s，即故障后{2}s；原cold_return_delay={3}s只表示任意仍可用源的首次流量/温度资格，不能冒充B新路恢复。增强图明确显示两种定义，不修改原始结果或借旧PASS。' -f $p.id,(Num $p.first_actual_B_path_cold_s),(Num $p.actual_B_path_cold_delay_s),(Num $p.original_any_path_cold_delay_s)))}
$drop=Get-Case 'readiness_negatives__source_publication_loss'
$l.Add(('源侧40s停止发布新样本，独立复核的保护首时刻{0}s；陈旧度锁存与PROTECTED_HOLD均已实际执行。时钟重评旧样本不制造新测量，也不增加M1样本信用。原13卡阀每组1200帧实际PLC请求B均为0，另附original_valve_excitation_file_proof.json；本轮真实卡阀见新场景，不借原PASS。' -f (Num $drop.first_violations_s.protected)))
$l.Add('')
$l.Add('## 厂家可立即接收的规格与16项决策答复')
$l.Add('')
$l.Add('1–2. 精确5失败是02/06/11/12/16，15m³与20m³各一套；身份、原始hash、致因、反事实、硬件修改与新实际值见首表和failure_closure_decisions.json。')
$l.Add('3–4. 测量Ready准入、时钟失联检查、源/负荷配套转B及回充后恢复备用可由新项目协调器改进；不能创造冷量、泵扬程或无间断负荷路径。快链、预冷回路、源能力、第三源/独立负荷通道属于真实硬件修改。')
$l.Add('5–6. 15m³仍是有条件候选，不等于可采购；85%须经有效容积/体积高度标定、热量计/流量积分、17TT保守估计及真实90s放冷共同证明。平均温度、细网格PASS或库存单项恢复不足以证明。')
$l.Add('7–8. 已计算A独立小循环和C独立HX/冷服务；A新增小泵/阀/TT/FT，C再新增热服务和电源边界。B旁通缺图纸NOT_RUN。A改动较少但依赖湿源和隔离，C独立性更强但不能声称现有数据已证明最经济或最可靠。')
$l.Add('9–10. 单模块退出同时约束每模块82.5m³/h及≥679.038kW必要下界、压降和风/喷淋map；泵−3%按表内实际补偿点验证，不靠额定电机kW替代Q-H。3+1切换瞬态和四泵回充的全工况由厂家/集成FAT保证，NPSH和静压未知不得放行。')
$l.Add('11–12. 接管中再故障、维修与共因由业主选设计基准。W3只在独立接口/电源假设下改善源侧冗余；负荷共管和卡阀仍会失败。真正卡阀已强制激发且保留失败；没有需求的一点明确INCOMPLETE，不计严格因果PASS。')
$l.Add('13–14. 少改动方案A/B并非已可行，较强D/E也未完成所有义务。仅可比较已测修改项、CAPEX/OPEX变化清单；没有报价、年性能map或故障概率，不虚构成本、节能率或风险最优排名。')
$l.Add('15–16. 发supplier_RFI_FAT.csv/JSON及VENDOR_COMPONENT_FAT_INTEGRATED_FAT_SITE_SAT_ZH.md索取保证：罐90s曲线/85%库存、暖管预冷与保持/远端Ready、湿源共同工况与N−1、泵全曲线/效率/NPSHr/启停、CDU四温两流量/污垢压降、阀真实响应/假反馈、仪表延迟/时钟/独立电源。单体归COMPONENT_FAT，整套90s连续性归INTEGRATED_FAT/SITE_SAT；所有厂家试验NOT_RUN、签章/保证空缺、REQUIRED_VENDOR_CONFIRMATION。')
$l.Add('')
$l.Add('## 不得被综合PASS覆盖的边界')
$l.Add('')
$l.Add('- 本轮主要是高温18柜全载工况。机柜入口45°C硬限与44°C设计目标分开；operating_target_met另列，正常37/40°C未由本轮全工况动态证明。历史正常/干冷负面结果不被覆盖，46°C干冷环境不能据此承诺41°C供水。冷源管回罐冷水、机柜入口和机柜回液是不同测点，不互相代替。')
$l.Add('- 额定UA240kW/K、初冷40.5°C、二次初温43.8°C、一次控制40.7°C、能力1.15等都是统一候选输入。改进相对G_WET_LOSS是组合效果，不能全部归因于单一预冷；单变量因果依据用专门counterfactual。')
$l.Add('- 罐非零混合的连续物理意义/网格缩放、真实布水器/短路、管路死角、预冷隔离阀动态、逐泵启动、静压/NPSH/水锤/PG物性、传感器共因与OEM电耗仍未闭环。FAT仪表精度/≥10Hz等为拟议协议，不能冒充本次模拟或厂家已执行。')
$l.Add('- 全部源码/输入/hash/官方ZIP/原始日志/实际Python Job及FINAL退出后cleanup在独立证据中。新工程验证不继承正式C3-C批准；不涉及真实泵阀PLC、生产、采购批准、Tier认证或Phase6。')
$l.Add('')
$l.Add('SOFTWARE_EXECUTION_STATUS=COMPLETED_SOURCE_BOUND_DEVELOPMENT；PHYSICAL_MODEL_VALIDITY=EQUATIONS_VERIFIED_WITH_UNCALIBRATED_AND_NUMERICALLY_INCOMPLETE_BOUNDARIES；FAILURE_CLOSURE_STATUS=PARTIAL_CONDITIONAL；ROBUSTNESS_STATUS=PER_REGISTERED_ENVELOPE_NOT_ALL_PASS；VENDOR_EVIDENCE_STATUS=OEM_NOT_VERIFIED；CUSTOMER_DESIGN_APPROVAL_STATUS=NOT_APPROVED；PROCUREMENT_RELEASE_STATUS=BLOCKED。')
$l.Add('')
$l.Add(('运行链接：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/'+$RunId))
[IO.File]::WriteAllText((Join-Path $delivery 'ENGINEERING_DECISION_ZH.md'),(($l -join "`n")+"`n"),$utf8)
[IO.File]::WriteAllText((Join-Path $delivery 'full_reserve_readiness.json'),(@{run=[long]$RunId;source_commit=$summary.source_commit;note='Threshold cold inventory is distinct from actual next90s discharge qualification; raw original grades retained';cases=$reserve}|ConvertTo-Json -Depth 20),$utf8)
@{report='ENGINEERING_DECISION_ZH.md';reproduced_legacy_failures=$reproductions.Count;dynamic_trials=$dynamic.Count;engineering='MEMPHIS_ENGINEERING_NOT_APPROVED'}|ConvertTo-Json
