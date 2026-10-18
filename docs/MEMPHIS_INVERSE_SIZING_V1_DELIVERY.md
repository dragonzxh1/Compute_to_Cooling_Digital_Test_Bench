# 孟菲斯18柜设备最低性能反求 V1 — 使用与交付边界

仅离线工程开发计算。00/01 V9为客户最终方案；R10为单独曲线/系统方案比较，不覆盖V9。`MEMPHIS_ENGINEERING_NOT_APPROVED`；不构成采购、施工、生产、真实控制或原M1资格的自动扩展。

## 看哪里

交互入口：`artifacts/memphis-inverse-sizing-v1-delivery/engineering_report.html`。设备矩阵为同目录`minimum_equipment_parameters.csv`，询价表为`supplier_RFI.csv`。完整15项回答在`MEMPHIS_MINIMUM_EQUIPMENT_REQUIREMENTS_ZH.md`；量化选型归纳及缺口在`ENGINEERING_DECISION_ZH.md`。

图上点来自保存的正向试验，不是在浏览器里临时生成结论。场景下拉可查看实际温度、源/负载流量、阈值冷库存以及阀门与控制事件。A/B罐全部20/40/80/160层及步长复核必须一起看；不能挑一条通过的曲线当设备保证。阈值冷库存不等于真实厂家保证的有效冷量，也不是控制器获准访问全部罐层。

## 身份与重现

- 计算源码：`840e813dbc6ef0840c7e26850bc4ba6276dd4ffb`，模型run39136524640。
- manifest RAW：`33fd9504baaf6bb92c24b07e4a47cfa6d0debd3c985253b132de692a716ad36f`。
- 冻结M1 candidate：`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`，未修改。
- 专用分支：`codex/memphis-inverse-sizing-v1`。后续只读水力复算和说明提交与实际计算源码身份分开，不用新说明commit冒充原计算commit。
- 原失败/取消run39134808524、39134995538、39135290316保留；不借部分PASS。Build004拆分CDU受控Job、修复独立复核器过期空值处理及消去误差界，未改物理演化、冻结期望或客户硬限。

交付清单RAW SHA256：`03c950746c7ec6d7354f2f71a2ad4c4960434ae1764e30fc2e5e538aaa9741a2`。源/输入/环境清单RAW SHA256：`e9639462eea25397620be25bdf2b935cbbf32d5bf80adfec2492d5c2b1ef1263`。清单逐文件绑定26个交付文件；GitHub说明提交回执在包外，避免自引用哈希。

计算：[run39136524640](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39136524640)。独立一次回路纯文件复算：[run39141542985](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39141542985)。49实际受控阶段、133动态+460罐+30预冷+10CDU边界、23见证；20官方ZIP/5373原始文件SHA核验。补充25个实际纯文件Job复算133工况350400步，均有外部PID与退出cleanup证据。它们是开发计算完成，不是工程总PASS。

代码在`v0_2/tests/tools/memphis_inverse_sizing_v1/`。`registration.json`登记测试点与边界。`stages.py`复用正向求解器，对每个观测到的成败边界进行四分点细化；不假设状态机单调、不保证连续全局最优。`report.py`只汇总源绑定的已保存结果。

本机不提供模型运行指令。确需改变参数时，在新的源身份下修改登记，通过现有GitHub Windows受控workflow进行开发验证；每阶段480秒、CPU25%、进程1024MiB/Job2048MiB，先核实际Python PID再释放，退出后验证cleanup。交互HTML只读浏览无需跑模型。不能重新dispatch本轮已完成身份来补一个PASS。

## 参数含义

|参数|含义与限制|
|---|---|
|tank_volume_m3 / cold_fraction|每罐几何容积与初始冷液比例，后者为未标定假设，不缩减总热容|
|layers / dt_s|数值网格/步长，非真实混合系数；收敛仅针对匹配参数点|
|mixing_m3_s / short_circuit|相邻层交换流量/顶部到底部短路假设，须由布水器试验标定|
|standby_initial_c / header_volume_m3|静置备用源管初温/容积，决定热库存；不是现场测量保证|
|startup_s / valve_s|建冷假设时间/完整阀行程，RUN不等于冷水已到；须供应商提供实际冷返曲线|
|capacity_scale / wet_bulb_c|合成冷源能力倍率/湿球；并非OEM性能图谱，风机喷淋和实际空气侧UA未知|
|source_head_factor / recharge_head_factor|假设泵曲线H0倍率，增加可能违反R10≤18m关死要求，不能直接批准|
|recharge_dp_kpa / primary_efficiency|回充总管阻设计点/线到液体效率；实际流量由泵-管网交点求，不强塞330|
|sensor_bias_K / sensor_delay_s|已释放观测偏差/延迟，不授予未来数据；过期测量仍必须拒绝和保护|

## 如何用结论

必要下界不是充分条件；有限参数点可行不是概率可靠性保证。Pareto只比较所执行的离散点，没有真实成本、概率或完整连续不确定性证明。单干冷不能在46°C空气下无制冷地产41°C液体；湿冷必须同时满足实际WB、PG25流量、进出口温度和启动条件，不能只看铭牌kW。

预冷独立回路是新增的有界热模型；集成故障试验使用预冷后的初始管温，尚未实现现场预冷PLC、远端测点与Ready撤销联锁的端到端控制。正常49.19m³/h二次边界由原单/六柜模块重新运行；18柜正常干冷整合保留68.37m³/h热工网络，不能宣称完整正常49.19水力资格。

设备RFI必须补齐泵全曲线/效率/NPSHr、弱件MAWP/静压/水锤、实际塔曲面与风机喷淋/补水、罐布水器/混合、保温管容与现场时延误差。OEM保证值保持空缺。原SEM02/PF06缺口、T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED继续保留；无正式C3-C、生产、硬件或Phase6授权。
