# 孟菲斯18柜设备最低性能要求

MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_CALIBRATION_REQUIRED。所有最低值是守恒必要下界或有限模型点，不是厂家保证。

执行commit `840e813dbc6ef0840c7e26850bc4ba6276dd4ffb`；manifest `33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f`；实际正向组模型133次、独立罐试验460次、预冷30次、设备边界10次。

## 孟菲斯18柜设备最低性能表

|设备|MODEL_REQUIRED_MINIMUM|CONDITIONAL_DESIGN_TARGET|OEM保证|采购|
|---|---|---|---|---|
|A储罐|ideal8.25m3;244.5731243999992MJ|{"ideal_necessary_cold_m3": 8.25, "ideal_necessary_energy_MJ": 244.5731243999992, "smallest_tested_total_volume_at70pct_all_grids_m3": 20.0, "smallest_tested_cold_fraction_in15_all_grids": 0.85, "minimum_added_volume_from15_on_tested_grid_m3": 5.0, "actual_OEM_minimum": null, "global_continuous_minimum": "NOT_VERIFIED", "condition": "constant48.29C return330m3/h90s, no source flow, stated mixing/wall; coarse diffusion retained; actual dynamic source trials separate"}|空缺|冻结|
|B储罐|ideal8.25m3;244.5731243999992MJ|{"ideal_necessary_cold_m3": 8.25, "ideal_necessary_energy_MJ": 244.5731243999992, "smallest_tested_total_volume_at70pct_all_grids_m3": 20.0, "smallest_tested_cold_fraction_in15_all_grids": 0.85, "minimum_added_volume_from15_on_tested_grid_m3": 5.0, "actual_OEM_minimum": null, "global_continuous_minimum": "NOT_VERIFIED", "condition": "constant48.29C return330m3/h90s, no source flow, stated mixing/wall; coarse diffusion retained; actual dynamic source trials separate"}|空缺|冻结|
|分层/布水器|No unique allowable mixing coefficient|Use all-grid passing fraction/mixing combinations only|空缺|冻结|
|备用管预冷|Max sampled joint-grid feasible initialC=41.6|81.524375MJ removal from48.29 to40.9448; ideal679.37kW/120s or90.58kW/900s BEFORE gains/pump|空缺|冻结|
|D1/D2干冷器|2716.15kW actual reject at required temperatures|normalDB29Tout37Tin44.341607;Nminus1 each>=1358.075kW|空缺|冻结|
|W1/W2湿冷源|2716.15kW at actual design fluids/weather plus actual pump reconciliation|5modules each>=543.23kW;one lost each of4>=679.0375kW|空缺|冻结|
|源泵组|3 pumps each110m3/h at loop96.52kPa; selection115.82kPa|V9/R10 separate synthetic Q-H envelopes; four-pump relief/transient check required|空缺|冻结|
|负荷泵组|330m3/h at155.92kPa loop|Electrical18--24kW pergroup at eta0.8--0.6, actual table controls|空缺|冻结|
|回充泵|120kPa at330 requires H0>=182.288377kPa with fixed K|or keep18m curve and reduce loopDP<=115.820000kPa|空缺|冻结|
|CDU板换|ideal UA137.481 normal/183.295 hot kW/K;1100kW guarantee209.284 ideal|Account actual pump heat and rack-vs-HX outlet offset; fresh forward UA scans do not inherit OEM|空缺|冻结|
|关键阀门与测点|Actual zero-speed/closed-valve interlocks; released paired TT/flow/pressure evidence|Separate tower-outlet/far-end/tank-cold/rack-inlet TT; flow>=330 and measured ready hold;stroke2/5/10s hypothetical|空缺|冻结|

## 15个明确回答

1. A罐：理想必要有效冷液8.25m³；相对48.29°C回水的可用显热244.573124MJ，预算2716.15kW×90s为244.453500MJ，两者是不同工况口径，不可相加。模型边界：{"ideal_necessary_cold_m3": 8.25, "ideal_necessary_energy_MJ": 244.5731243999992, "smallest_tested_total_volume_at70pct_all_grids_m3": 20.0, "smallest_tested_cold_fraction_in15_all_grids": 0.85, "minimum_added_volume_from15_on_tested_grid_m3": 5.0, "actual_OEM_minimum": null, "global_continuous_minimum": "NOT_VERIFIED", "condition": "constant48.29C return330m3/h90s, no source flow, stated mixing/wall; coarse diffusion retained; actual dynamic source trials separate"}。
2. B罐：相同理想必要量，独立B阶段实际重算；{"ideal_necessary_cold_m3": 8.25, "ideal_necessary_energy_MJ": 244.5731243999992, "smallest_tested_total_volume_at70pct_all_grids_m3": 20.0, "smallest_tested_cold_fraction_in15_all_grids": 0.85, "minimum_added_volume_from15_on_tested_grid_m3": 5.0, "actual_OEM_minimum": null, "global_continuous_minimum": "NOT_VERIFIED", "condition": "constant48.29C return330m3/h90s, no source flow, stated mixing/wall; coarse diffusion retained; actual dynamic source trials separate"}。对称结果来自相同登记几何和输入，不证明两台真实罐等效。
3. 15m³是否足够：只在具体冷液比例、初温、混合/短路和出口曲线下有条件满足；70%不是OEM事实。最低通过总容积/冷比例为上表有限样本，不是连续全局最小。见buffer_convergence.csv全部网格，不挑选通过层数。
4. 备用管最高允许温度：80/160层临界扫描[{"assumption": "No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven", "axis": "standby_initial_c", "global_minimum": "NOT_VERIFIED", "kind": "critical", "largest_tested_feasible": 41.6, "layers": 80, "observed_edges": [[41.6, 42.0]], "smallest_tested_infeasible": 41.7}, {"assumption": "No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven", "axis": "standby_initial_c", "global_minimum": "NOT_VERIFIED", "kind": "critical", "largest_tested_feasible": 41.6, "layers": 160, "observed_edges": [[41.6, 42.0]], "smallest_tested_infeasible": 41.7}]。两网格都得到可行点时共同最大采样值41.6°C，仅是测试点范围，不保证中间未测区或其他天气。暖水48.29°C管体积的独立扫描为[{"assumption": "No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven", "axis": "header_volume_m3", "global_minimum": "NOT_VERIFIED", "kind": "critical", "largest_tested_feasible": 0.3125, "layers": 80, "observed_edges": [[0.25, 0.5]], "smallest_tested_infeasible": 0.375}, {"assumption": "No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven", "axis": "header_volume_m3", "global_minimum": "NOT_VERIFIED", "kind": "critical", "largest_tested_feasible": 0.25, "layers": 160, "observed_edges": [[0.25, 0.5]], "smallest_tested_infeasible": 0.3125}]；阀门时间独立扫描为[{"assumption": "No global monotonicity. Finite samples and all observed edge refinements; gaps remain unproven", "axis": "valve_s", "global_minimum": "NOT_VERIFIED", "kind": "critical", "largest_tested_feasible": 15.0, "layers": 80, "observed_edges": [[15.0, 20.0]], "smallest_tested_infeasible": 16.25}]。不能只从热库存等式推断动态允许体积/时延。
5. 预冷能力：48.29→40.9448°C、2.75m³的必要降热81.524375MJ；120秒理想>=679.37kW且理想至少82.5m³/h置换，900秒理想>=90.58kW且至少11m³/h；真实混合、热增益和泵热增加需求。实际闭式预冷扫描5--90m³/h、25--750kW与UA0/0.5kW/K见precool_results.json。电功率缺COP/风机图谱，不能把热kW当电kW。
6. 单干冷：至少排出2716.15kW（须按实际泵热更新）；330m³/h、37°C出液时进液44.341607°C，在DB29工况保证。3模块各>=905.383kW；Nminus1剩余2模块各>=1358.075kW。有效流体-环境导热面不等于空气侧真实UA。
7. 单湿冷：330m³/h下2716.15kW、41°C出液要求进液48.341607°C；若要求35°C出液，则进液42.341607°C。5模块各>=543.23kW；Nminus1四模块各>=679.0375kW。WB30与PG25实际性能、喷淋和风机未OEM确认。
8. DB46/WB30：无制冷单干冷不能直接产41°C水；湿冷热力学上可行不等于设备已保证。实际HOT/HYBRID/模块失效试验结果见敏感性表，额外管阻与泵热已计入，未自动批准混合拓扑。
9. 一次源泵：3×110m³/h，源侧运行96.52kPa/选型115.82kPa；负荷泵330m³/h、155.92kPa独立回路。V9候选34m与R10关死<=18m是不同约束；不跨版本拼静压。实际并联交点/效率区间见analytic_requirements.json，NPSHr/静压/瞬态/弱件MAWP仍NOT_VERIFIED。
10. 回充：在原合成K不变时H0至少182.288377kPa才能330m³/h@120kPa；若保留18m曲线，系统330工况压降须<=115.820000kPa。增加H0可能违反18m，不能悄悄采用。四个实际回充试验分别保存。
11. 90秒需要联合满足：全IT2650.5kW入液+实际泵热、机柜入口<=45、负载侧连续330、备用源冷返时序和最终5秒稳定、罐单体出口<=0.5K、有效冷库存、禁止A/B非法并通及真实测量权限。源侧停流不能冒充负载侧停流或放宽330。
12. 最大瓶颈：暖备用管热库存/输送与冷罐储备、源启动和二次停流耦合；若源容量低于实际液体+泵热，短时缓冲通过也不能成为持续满载可行设计。
13. 最有效参数须看本次sensitivity_results.csv与临界曲线：预冷、启动时间、库存、冷源能力并非处处单调；记录每个状态机边界，不用单一点推全球结论。
14. 最小修改候选：优先实证备用管预冷及远端冷水ready测点，保留15m³前须证明有效比例/混合和初温。这个结论不是授权新增旁通、并罐或修改00/01；若扫描无可行点明确保留NO_FEASIBLE_DESIGN_IN_TESTED_GRID。
15. OEM必须提供：CDU/泵/塔共同工况图谱、分层罐与布水器出口试验、管路UA/容积、源预备与冷水到达时间、阀行程/Kv、实际仪表时延/误差、NPSHr/MAWP/水锤，以及2h补水含蒸发/排污/漂水/死水体积。实际OEM保证值全部为空。

## 联合可行域、Pareto与鲁棒性

有限联合点可行8个；非支配点1个。变量代价只是容积/合成容量倍率/预冷MJ/启动改进秒，不是经济最优或全球最优。

[
  {
    "stage": "ROBUST_B15",
    "status": "NOT_VERIFIED",
    "tested": 17,
    "failed": 5
  },
  {
    "stage": "ROBUST_C20",
    "status": "NOT_VERIFIED",
    "tested": 17,
    "failed": 5
  }
]

未给联合连续区间或概率分布；若任一已登记不确定性/故障不满足，不能声明ROBUST PASS。NUMERICALLY_CONVERGED只用于匹配参数网格/步长差<=0.05K的数值点，不是实际混合或全系统保证。

## OPTION A / B / C

- OPTION A：保持数量和15m³；必须同时达到表中冷比例/冷库存/混合条件、源实际工况排热和泵Q-H，以及临界预冷/建冷组合。缺数据或跨网格失败不算现方案已通过。
- OPTION B：候选15m³、85%初始冷液、备用管40.5°C、建冷20秒；只是受控假设点，17个单因素/联合角点含二次故障实测，失败保留。预冷设施和20秒能力需供应商证明。
- OPTION C：候选20m³、85%冷液、同预冷/启动目标；更大容积并非天然更可靠，独立回充需匹配泵曲线，Nminus2需独立供冷/电源域而非放宽指标；不能宣称硬件配置已经选定。

## 独立核算与不足

独立复核各机柜控制体、HX、质量、实际泵热一次归属、储能总账、源侧许可和M1 PRE/Safety/PLC/POST；每试验保存原始物理、传感器、事务/压缩日志、参数、哈希。解析预算不额外注热。
保持冻结M1、原C3-C和历史证据，不继承其集成资格。原SEM02/PF06缺口、任意POST/崩溃/断电原子性未证明、T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED原状保留。无正式C3-C、生产、硬件控制、Phase6或采购授权。

## 供应商正式RFI

|编号|待提供保证数据|共同工况|
|---|---|---|
|RFI-01|CDU effectiveUA/fouling/PG25/4temperatures/Q-DP|37/40,41/44;110/49.19/68.37;1100kW guarantee separate|
|RFI-02|Tank diffuser/thermocline/short-circuit/wall and initial cold inventory|A and B separately330m3/h90s<=0.5K;TT placement and worst inlet sequence|
|RFI-03|Standby preconditioning topology/pipe volume/insulation and measured ready|Temperature/flow/transport history;thermal kW vs COP/fan electric;outage holding time|
|RFI-04|Dry actualDB/flow/PG25/outlet map and Nminus1|DB29 supply37;DB46 cannot alone make41;finite airflow/UA/power|
|RFI-05|Wet actualWB/DB/PG25 map, module loss, startup and fan/spray|46DB/30WB at specified inlet/outlet330;water2h includingdrift/blowdown/sump|
|RFI-06|Pump full Q-H-eta-NPSHr/shutoff/speed/parallel map|V9 34m andR10<=18m adjudicated separately;source/load/recharge separate|
|RFI-07|Static elevations/expansion/relief/weakest MAWP/transient|Suction/gauge references;water hammer;forbiddenAB cross-connection|
|RFI-08|Valve Kv/stroke/zero-speed and source-ready measurement|Actual PLC receipts,release/sample latency,calibration uncertainty and independent fast protection|
|RFI-09|Design cost/reliability/uncertainty distributions|No monetary Pareto weights,probability orROBUST approval without field envelope|
