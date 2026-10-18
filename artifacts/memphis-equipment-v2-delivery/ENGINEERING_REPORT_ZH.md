# 孟菲斯设备验证与故障接管V2：实际交付

软件执行及独立证据核验完成。工程审批状态：MEMPHIS_ENGINEERING_NOT_APPROVED。设计决策：DESIGN_INFORMATION_INSUFFICIENT；已有失败处另列MODIFICATION_RECOMMENDED。

运行：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39088951176
执行源码：`6031e0ef7d32bec0109f328f85ebd5dfef8fe048`；source manifest RAW SHA256：`5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16`。
本次50个实际受控阶段；960个独立源码文件、960项跨清单哈希核验；2795个raw文件；18696条阶段事务；18696个完成日志帧；镜像20261012.333.1。PID/Job、CPU25%、1024/2048MiB、480s、退出cleanup均已检查。

## 单柜与六柜实际结果

| 场景 | 最高入口°C | 末入口°C | 末机柜出口°C | 末总流量m³/h | 流量恢复时刻s | 温控/接管/连续性 |
|---|---:|---:|---:|---:|---:|---|
|SR_HOT|44.000|43.238|54.810|11.395||PASS/INCOMPLETE/PASS|
|SR_STUCK_BACKUP|44.000|43.243|54.827|11.395|29.300|PASS/PASS/PASS|
|SIX_NORMAL|40.000|38.122|54.183|49.190||PASS/INCOMPLETE/PASS|
|SIX_UA110|47.127|47.127|58.677|68.370|16.200|FAIL/FAIL/FAIL|
|SIX_UA18330|44.025|44.025|55.593|68.370||PASS/INCOMPLETE/PASS|
|SIX_UA20928|44.000|43.465|55.036|68.370||PASS/INCOMPLETE/PASS|
|SIX_UA220|44.000|43.275|54.847|68.370||PASS/INCOMPLETE/PASS|
|SIX_STEP|44.000|43.269|54.824|68.370||PASS/INCOMPLETE/PASS|
|SIX_STUCK_BACKUP|44.000|43.282|54.873|68.370|29.600|PASS/PASS/PASS|
|SIX_CDU_LOSS|44.046|43.299|54.933|68.370|25.600|PASS/PASS/PASS|
|SIX_RESTRICTION|44.000|43.286|54.885|68.370|25.600|PASS/PASS/PASS|
|SIX_SENSOR_LOSS|44.000|43.275|54.847|68.370||PASS/INCOMPLETE/PASS|
|SIX_SENSOR_DELAY|44.000|43.275|54.847|68.370||PASS/INCOMPLETE/PASS|
|SIX_BACKUP_FAIL|44.000|41.272|64.444|33.357||PASS/FAIL/FAIL|
|SIX_SECOND_FAILURE|44.000|43.325|84.213|0.000|29.600|PASS/FAIL/FAIL|
|SIX_UNBALANCED|44.000|43.247|56.767|67.871||PASS/INCOMPLETE/PASS|
|SIX_INVENTORY_HALF|44.693|43.275|54.845|68.370|25.600|PASS/PASS/PASS|
|SIX_INVENTORY_DOUBLE|44.000|43.404|55.306|68.370|25.600|PASS/PASS/PASS|
|SIX_VALVE_SLOW|44.681|43.369|55.181|68.370|45.400|PASS/PASS/PASS|
|SIX_PUMP_WEAK|44.000|42.848|55.770|61.152||PASS/INCOMPLETE/FAIL|
|SIX_UNEQUAL_LOAD|44.000|42.917|54.490|68.370||PASS/INCOMPLETE/INCOMPLETE|
|SIX_REPEAT|44.000|43.275|54.847|68.370||PASS/INCOMPLETE/PASS|
|SIX_REFINED|44.000|43.275|54.847|68.370||PASS/INCOMPLETE/PASS|

恢复时刻为绝对仿真时刻，故障在10s；流量/压差恢复需连续5s满足登记的99%设计参考。原运行泵M1与备用执行器分别保留身份。备用泵先启动并收到发布的转速反馈，再断开旧路、打开备用路径；独立快速低流量保护与M1分别记录。
单柜缩比一次边界、合成泵曲线、阀门5s/慢阀15s和备用0.2/s均为工程假设。备用CDU按相同HX与共享机柜液体库存建等效隔离路径，断开CDU内部液体/金属热容及零流量电机损耗未知；因此这些恢复时间不能作为厂家保证。
45°C仅约束机柜二次入口；正常40°C/高温44°C目标跟踪精度、OEM最高回温/最低流量、露点及GPU die安全仍未验证。FULL_LOAD_CONTINUITY的PASS仅是已登记模型窗口条件，不覆盖这些设备资格缺口。

## 18柜冷源、90秒及回充

| 场景 | 最高入口°C | 故障后90s最高°C | 冷水首返330m³/h延迟s | 原264指标延迟s | A/B实际切换 | 储备恢复时刻s |
|---|---:|---:|---:|---:|---|---:|
|G_CURRENT|44.000|43.544||||120.000|
|G_WET_LOSS|46.793|46.203|118.800|118.800|{"from_tank":"A","time_s":112.7,"to_tank":"B"}||
|G_B_WARM|47.904|47.130|148.000|148.000|||
|G_VALVE_STUCK|50.248|45.902|116.500|116.500|||
|G_MIXING|47.948|47.287|140.500|140.500|||
|G_WEATHER|47.036|46.214|||{"from_tank":"A","time_s":112.7,"to_tank":"B"}||
|G_HEADER_LOSS|50.287|43.978|||||
|G_BACKUP_SOURCE_FAIL|50.256|43.904|||||
|G_R10_COMPARISON|46.703|46.258|119.600|119.600|{"from_tank":"A","time_s":113.7,"to_tank":"B"}||
|G_REFINED|46.782|46.195|119.000|119.000|{"from_tank":"A","time_s":112.7,"to_tank":"B"}||
|G_LAYERS40|47.552|46.370|151.400|151.400|{"from_tank":"A","time_s":111.1,"to_tank":"B"}||
|G_LAYERS80|47.979|46.301|156.900|156.900|{"from_tank":"A","time_s":109.7,"to_tank":"B"}||
|G_UA18330|47.741|46.107|119.800|119.800|{"from_tank":"A","time_s":109.1,"to_tank":"B"}||
|RECHARGE_SHARED|44.000|43.544|||||
|RECHARGE_INDEPENDENT|44.000|43.544||||262.000|

每组2790kW IT，2650.50kW入液，泵热由实际模型工作点加入一次；模型排热不强钳为2716.15kW设计预算。330判据和旧264判据独立列示，空值表示窗口内未满足，不能给PASS。罐15m³保持完整热容量，70%只用于初始冷层。冷源/管路/分层由守恒方程推进，不固定一次41°C。
表中90秒窗口统一为30—120s；对有故障场景是故障后90s，对G_CURRENT/回充场景只是对照窗口，不代表这些场景发生了故障。无故障场景首返空值为不适用，不能解释为一次接管失败。
首返仅统计故障后的实际物理区间；故障前冷水不能算作0秒恢复，无故障场景不虚构接管通过。首次冷水达到不代表此后持续可用，末5秒恢复保持单独检查；旧Build4的错误首返统计保留为缺陷证据，不作为本次合格结论。
0—90s逐秒储热、排热、泵热、流量和冷量数据保存在每场景first90_energy_rows。检测1s、阀序、54s备用建冷、2.75m³源管热置换、热跃层扩散、44.5°C后触发及备用冷量构成解释链；这些假设不是厂家动作时间。没有修改触发点来追求通过。
各敏感性场景差值不是可直接相加的独立因果贡献。分层网格的数值扩散与真实混合必须区分；完整网格/步长差异见consolidated_report.json的resolution_study，不能挑选一个通过网格替代设备实测。

| 回充场景 | 最大实际回充m³/h | 330m³/h判据 | 双罐冷储备恢复时刻s |
|---|---:|---|---:|
|RECHARGE_SHARED|330.000|PASS||
|RECHARGE_INDEPENDENT|326.194|FAIL|262.000|
储备恢复时刻是登记冷量阈值的首次满足，不能替代完整330m³/h回充能力、下一故障连续性或长期稳定性。共用方案的源侧流量与独立方案的专用回充支路分别按其实际拓扑读取。

- BUFFER20：330m³/h持续90s，出液最大升温1.598K，判定FAIL。
- BUFFER40：330m³/h持续90s，出液最大升温0.879K，判定FAIL。
- BUFFER80：330m³/h持续90s，出液最大升温0.305K，判定PASS。
- BUFFER160：330m³/h持续90s，出液最大升温0.039K，判定PASS。
- BUFFER160_REFINED：330m³/h持续90s，出液最大升温0.047K，判定PASS。
- BUFFER_MIXED：330m³/h持续90s，出液最大升温2.176K，判定FAIL。

## 设备选型与采购阻塞

- 888.120kW，37→40°C供温条件，需有效UA约137.481kW/K；理想逆流、暂定PG25常物性，无污垢及制造裕量。
- 894.360kW，41→44°C供温条件，需有效UA约183.295kW/K；理想逆流、暂定PG25常物性，无污垢及制造裕量。
- 1100.000kW，41→44°C供温条件，需有效UA约209.284kW/K；理想逆流、暂定PG25常物性，无污垢及制造裕量。
厂家可用UA尚无完整项目保证点；110/183.30/209.28/220均为研究输入，不能提升为OEM_CONFIRMED。三花S200AL-246H的型号和引用压降已存在，缺的是完整原始热选型；Alfa Laval与三花参数不可混用。
137/183/209kW/K是所列板换四端温条件的理想反算值。板换二次出口与机柜入口之间的水力耗散/储热位置仍需区分；若仿真UA183.30时机柜入口略高于44°C，应保留该偏差，不能把理论需求数字当作端到端温控保证。六柜共用充分混合供液节点，支路入口同温是显式降阶假设；各柜回温与流量独立，未作供液支路空间温差或CFD验证。
CDU整机接口差压应与外部管路/机柜需求比较，不能将内部板换和过滤器损失再次计入外部需求。按原预算高温外部约295.21kPa，常态约152.81kPa；371.81kPa是整个二次泵路径预算。厂家目录额定流量与项目不同，须提供完整曲线再判适配。
- Custom CDU1100：CONDITIONALLY_SUITABLE。Require project thermal guarantee, external head, recovery and pressure proof; no final equipment PASS 来源：00/01 hash-bound final sources
- Alfa Laval plate HX option：NOT_VERIFIED。Component manufacturer/application evidence only; no exact selected model. Cannot inherit Sanhua DeltaP/MAWP 来源：https://www.alfalaval.com/en-us/industries/hvac/data-center-cooling/
- Sanhua S200AL-246H plate HX：NOT_VERIFIED。Exact project UA, fouling and original manufacturer selection sheet missing; not an entire CDU model 来源：00 model and embedded figures; prior Sanhua reaudit hashed inputs
- Vertiv XDU1350：NOT_VERIFIED。3K/PG25/external head/pump mode must be quoted; 1368kW alone cannot establish project suitability 来源：https://www.vertiv.com/48ef40/globalassets/products/thermal-management/high-density-solutions/liebert-xdu1350-coolant-distribution-unit-application-and-planning-guide-sl-70618.pdf
- Motivair MCDU40 / MCDU50 inquiry：NOT_VERIFIED。Catalog fluid labels mention25%PG but capacity footnote says100%water: seek written clarification. Do not treat as confirmed PG25 project rating or current orderable BOM 来源：https://www.motivaircorp.com/uploads/files/brochures/CDU_Brochure_2023.pdf

源泵34m是115m³/h候选工作点，≤18m是R10完整曲线约束，二者不是同一种数字。已分别计算2/3/4泵、五档转速和0.6/0.7/0.8效率假设。静压、NPSHr、真实最弱MAWP与瞬态缺失使采购阻塞；同标高条件绝压不能当现场验证。源侧96.52kPa和负荷侧155.92kPa经分层罐解耦，不相加选一台泵。

| 合成版本 | 运行泵数 | 转速比例 | 每泵m³/h | 总m³/h | 运行压差kPa | 关死压差kPa | 泵电耗kW（效率0.7） |
|---|---:|---:|---:|---:|---:|---:|---:|
|V9_34m|3|0.800|140.630|421.890|157.757|258.376|26.411|
|V9_34m|3|1.000|175.787|527.362|246.495|403.712|51.584|
|V9_34m|4|0.800|115.797|463.189|190.154|258.376|34.951|
|V9_34m|4|1.000|144.747|578.986|297.116|403.712|68.264|
|R10_18m|3|0.800|93.194|279.582|69.280|113.989|7.686|
|R10_18m|3|1.000|116.493|349.478|108.250|178.108|15.012|
|R10_18m|4|0.800|76.794|307.177|83.631|113.989|10.194|
|R10_18m|4|1.000|95.993|383.971|130.673|178.108|19.911|
这些是按显式二次曲线假设求交点的工程扫描，不是厂家的完整恒速Q–H图。不能将其中某个有利工作点作为订货参数。板换一次/二次入口表压差≤10kPa、泵吸入口≥50kPag的全工况压力链尚未闭合；单侧板换压降、循环扬程或同标高条件绝压均不能替代这两个要求。

## 工程决策及下一步

- 00/01 current plus shared segmented recharge：DESIGN_INFORMATION_INSUFFICIENT；Current final topology; thermal and restoration results separately evaluated
- R10 independent recharge：DESIGN_INFORMATION_INSUFFICIENT；Alternative: needs added pump/pipe/power, OEM curve,330m3/h proof and design approval
- Shared standby CDU across three units：DESIGN_INFORMATION_INSUFFICIENT；Not implemented customer topology; needs cross-tie manifold/valves, extra loss, failure-domain and maintenance review; no assumed reliability/cost advantage
- Hybrid dry/wet packaged source：DESIGN_INFORMATION_INSUFFICIENT；Conditional total reject2716.15kW; no actual common-condition map or cost
- Earlier measured reserve transfer：MODIFICATION_RECOMMENDED；Study new registered trigger/delay only after diagnosing existing trace; current44.5 trigger retained this run
共享备用CDU仅完成架构及失效域/水力/维护风险比较，未完成交叉管网动态验证；混合冷源无实际共同工况图谱。不得将这两项备选解释为已经验证的客户配置。风机功率、实际水耗及全年CAPEX/OPEX缺曲线/报价，不输出虚假数值排名；有限窗口泵耗可从账本读取。
2小时断水带载、10分钟UPS切换、现场压力瞬态、真实泄漏流量及设备全工作包络未由本次120/240/900秒窗口覆盖，保持NOT_VERIFIED；原有测量触发的漏液隔离逻辑不能替代泄漏质量损失试验。尚不能出采购合格证或完整客户验收结论。
最高优先级RFI：订货机柜允许回温/最小流量；准确CDU/BOM及1100kW项目保证点；完整PG25泵图与压力链；15m³罐90s温升和实际阀泵时序。其余见supplier_RFI.csv。

保持原Startup49/50与兼容性分开；SEM02五项strict P1 B/C不完整、PF06原域INCOMPLETE、任意POST/崩溃/断电原子性NOT_PROVEN、T09 HOLD、fullP历史不可用、硬件CALIBRATION_REQUIRED。该项目开发不继承正式C3-C资格，未授权生产、硬件、Phase6或采购实施。