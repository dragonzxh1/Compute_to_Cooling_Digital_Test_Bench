# C2C-DTB M1 软件使用说明与参数解释（草稿）

状态：使用说明正在完善；不是“版本已上线”证明。新 POST 修复仍未完成验证。
项目用途是离线液冷数字孪生与软件验证，不能把本说明中的数值用于真实 CDU 控制。
所有 fixture 数值是数值测试假设；真实 GPU/VFD/CDU 参数仍需 CALIBRATION_REQUIRED。

## 1. 先弄清三个入口

| 入口 | 做什么 | 不代表什么 |
| --- | --- | --- |
| `src/c2c` / `c2c-dtb` | 原 v0.1 计算-冷却仿真与报告 | 不是新 M1 split 事务资格入口 |
| `v0_2` | 固体热容、热阻、冷却液输运、水力、CDU、反馈控制数值模型 | 模型能运行不等于真实机柜校准或硬件保护认证 |
| `v0_2/tests/tools/m1_engine_v*` | 验证 tracking 的 PRE/Safety/模拟PLC/POST 命令与测量因果顺序 | 不测试真实 GPU→CDU 散热性能，不产生现场 PLC 指令 |

M1 full campaign 的 inputs 是已经冻结的外生命令/测量时间序列。它考的是“测量属于哪条命令、故障证据是否真实、该不该发布”，不是用 GPU 功率在线调泵。Phase6 feedforward 未启动。

## 2. 运行环境与安全

本机曾发生整机硬挂，因此当前禁止在这台电脑运行 Python/model/native 压力测试。以下 Python 命令仅供另行授权的独立 runner / 稳定执行机，不要在当前本机复制执行。

Build005 实际开发环境：GitHub hosted Windows2022、Python3.11.9、固定依赖锁
`v0_2/tests/tools/c3b_v14_1/requirements-development.lock`。发布包和新验证必须记录自己实际环境，不能借用旧环境 hash。

原 root 安装包和 `v0_2/pyproject.toml` 是两个独立包；不要混装或覆盖。M1 development tools 不在现有 v0.2 wheel package 列表中，当前需要完整、hash-bound repository snapshot。发布安装包可用性仍是待关闭项，不能把 `pip install v0_2` 描述成完整 M1 安装。

## 3. M1 执行参数

Build005 的 PowerShell入口为 `v0_2/tests/tools/m1_remote_control_v3/run.ps1`；它有 hosted-Windows、source commit 和 manifest guards，不是本机可直接执行的脚本，也不能用于尚未绑定的新 v4 修复。

| 参数 | 含义与要求 |
| --- | --- |
| `Python` | 目标解释器绝对路径；验的是实际运行 PID/Job，不是包装器名字 |
| `ExpectedCommit` | 本次执行源码的40位 Git SHA；不能填后来文档 HEAD |
| `ExpectedManifestSha256` | 执行 manifest 原字节64位 SHA256；不是历史 R4.6 result manifest |
| `Mode` | CHECKS=入口/单元检查；REFERENCE=新参考结果；REFERENCE_GATE=参考验收；SELECT=物化prefix；SPLIT=新被测结果；PREFIX=选中前缀回放；STARTUP=原测试；SCHEMA=证据结构；FINAL=总验收；LONG=单独长案例阶段 |
| `JobKey` | 本阶段 evidence identity；同一次失败不能覆写同名目录后拿 PASS |
| `IndicesCsv` | 明确的 descriptor 索引列表；不是随意改测试数量的参数 |
| `RuntimePlanPath` | 已保存的精确 prefix execution plan 路径 |
| `ExpectedPlanSha256` | 对上述 plan 的原字节 SHA256，必须在回放前核验 |
| `MemoryProfile` | STRICT 或 CAMPAIGN 资源档；不会修改数学参数或模型时间 |

资源参数：`cpu_rate_per_10000=2500` 表示 Job CPU 上限25%；STRICT process/job=256/512MiB，CAMPAIGN=1024/2048MiB；`child_wall_seconds=480` 为真实墙钟运行预算；`active_process_limit=4` 是子进程数量上限，不是并行 testcase 数或GPU数量。BLAS线程数固定1，避免一次任务创建大量数值线程。

CPU限额、内存和wall timeout改变运行资源，不得拿它们去延长故障响应模型 timer，或把 `dt` 从0.2s改成480s。wall timeout导致该阶段停止，不能自动得到模型 FAULT/PASS。

## 4. 时间、速度、温度与压差单位

`*_ns` 使用整数纳秒，1s=1,000,000,000ns。`time_ns` 是决策拍；`sample_ns` 是采样时刻；`release_ns/available_ns` 是该测量对控制器可见的时刻；`command_timestamp_ns/issue_ns` 是已经签发的命令时刻。相同timestamp仍按 PRE→Safety→PLC→POST 有序执行。

`speed`/command 是0～1归一化转速，不是RPM；0.15表示15个百分点，不是当前速度的15%。温度 `*_k` 是K，摄氏度=K−273.15；`*_pa` 是Pa，1kPa=1000Pa；流量`kg/s`与`m³/s`不能直接互换，需要声明密度。传感器、执行器和网络延迟是不同参数，不重复叠加或相互替代。

## 5. 完整 M1 frozen tracking profile 参数

来源：`phase5_r5_2_2_fixture_tracking_profile.json`。这些是已有冻结域的说明，不能为了新测试通过而改值。其来源记录中的 `value/unit/source_type/source_ref/method/valid_range/calibration_status` 必须一并保留。

### 5.1 ActuatorTrackingProfile（执行器）

| 参数 | fixture值 | 大白话 / 含义 |
| --- | --- | --- |
| `command_delay_s` | 0.2s | 命令排队到开始作用的物理响应延迟，不是传感器延迟 |
| `speed_min` / `speed_max` | 0.3 / 0.9 | 本数值域命令下限/上限；不能用1.0编造超域资格案例 |
| `speed_rate_limit_per_s` | 0.2 fraction/s | 每秒归一化转速最多改变0.2，约20个百分点 |
| `lag_time_constant_s` | 1.0s | 一阶响应快慢；还要受ramp与delay影响，不保证1s到目标 |
| `command_resolution` | null | 未模拟命令量化；null不是分辨率0、更不是无限硬件精度 |
| `directional_symmetry` | symmetric nominal lag/ramp | 此fixture上升/下降采用对称标称动力学；真实设备未验证 |

### 5.2 SensorObservationProfile（测量）

| 参数 | fixture值 | 含义 |
| --- | --- | --- |
| `measurement_period_s` | 0.2s | 采样周期；不是每个simulator积分步都产生新测量 |
| `measurement_release_delay_s` | 0s | 采样到可见的遥测延迟，独立于actuator delay |
| `measurement_validity_limit_s` | 1s | 最大样本年龄；age从sample算，不能用命令age或转发刷新 |
| `speed_measurement_resolution` | null | 未模拟转速量化，不等于硬件分辨率已知 |
| `speed_measurement_noise_bound` | 0 | 未加入随机测量扰动；不证明真实传感器无噪声 |
| `speed_measurement_stationary_variation` | 0 | 本fixture稳定窗口的峰峰波动，不是硬件零漂结论 |
| `timestamp_resolution_s` | 1e-9s | 整数ns表示精度，不是现场时钟同步准确度 |
| `quality_semantics` | VALID/MISSING且已release | 只有合法、已到达、未过期测量可赚证据；无TRUE/ACTUAL兜底 |

### 5.3 TrackingQualificationProfile（判定）

| 参数 | fixture值 | 含义 |
| --- | --- | --- |
| `material_command_delta` | 0.15 | 未解决命令变化达到可观察需求；小步累计仍可能变成material |
| `minimum_observable_speed_change` | 0.01 | 在要求方向上最小可观察运动量，约1个百分点 |
| `minimum_progress_margin` | 2.0 | 观测/网格floor的登记裕量倍数，不是容许任意两倍误差 |
| `tracking_error_tolerance` | 0.15 | 历史mismatch/tolerance来源；不能当成新的progress阈值 |
| `response_opening_rule` | 已release、delay后且期望位移足够 | 不在命令刚发出时就把正常等待算故障 |
| `progress_rule` | VALID、已release、未过期、方向位移达门槛 | command变化本身不能证明泵动了 |
| `suspected_rule_parameters.expected_min` | 0.03 | 合法响应机会中的最小期望运动量之一 |
| `suspected_rule_parameters.ratio_below` | 0.5 | 实测/期望进度比例的怀疑门槛；由冻结qualifier具体条件解释 |
| `confirmed_rule_parameters.expected_min` | 0.12 | 确认所需期望运动量门槛之一 |
| `confirmed_rule_parameters.ratio_below` | 0.35 | 确认条件的进度比例门槛之一 |
| `confirmed_rule_parameters.qualified_samples` | 2 | 合法不足响应证据计数，不是两个raw tick就自动confirmed |
| `measurement_quality_requirements` | VALID/released/age合法 | invalid sample既不赚正运动证据，也不赚负响应证据 |
| `reversal_observability_rule` | 新方向位移与测量anchor关联 | 瞬时command导数反向不必然等于净需求反向；direction与watch history分开 |
| `sensor_recovery_rule` | 第一条重新VALID且release的测量 | 恢复即可对保留参考检查，不要求先出现新命令；不假装outage期间观测到运动 |

这些profile中的历史diagnostic来源不意味着可直接写Production Safety。真正lifecycle/evidence按已冻结R4.5B/PolicyA/v2和reference qualifier执行，Safety按15A映射，不另加一个进度timer或改threshold。

## 6. 反馈控制 / 执行器 / 传感器公共配置

| 配置字段 | 意义与单位 |
| --- | --- |
| `PIDConfig.kp` | 比例增益；外环Pa/K，内环归一化转速/Pa，随输入输出定义变，不能跨环照抄 |
| `ki` / `kd` | 积分/微分增益，按代码sample秒单位计算；0可关闭对应项 |
| `sample_ns` | 控制器采样周期（ns），必须正整数 |
| `lower` / `upper` | PID输出上下界，单位随环路输出；outer是DP修正，不直接是泵转速 |
| `integral_limit` | 积分项绝对限幅，输出单位；不是故障门槛 |
| `tracking_gain` | 使用到达的measured applied output回算积分的增益；禁止用hidden actual反馈 |
| `OuterConfig.base_dp_pa` | 基础DP目标；PID生成的是增量，最终target=base+correction |
| `OuterConfig.target_k` | 温度控制目标；不是derate/hard保护温度 |
| `OuterConfig.mode` | 现有Phase5的DP_TARGET；Outer不直接签发ActuatorCommand |
| `InnerConfig.pid` | 本地measured-DP PLC的PID配置；只有PLC创建最终command |
| `PumpActuatorConfig.minimum/maximum` | 归一化命令域，必须0≤min<max≤1 |
| `tau_s` / `ramp_per_s` / `command_delay_ns` | 一阶惯性、速率限制、物理命令延迟；不代替sensor delay |
| `owner_id` / `meaning` / `source` / `provenance` | 参数身份和来源说明，不是数学增益；缺失不可假装硬件校准 |
| `SensorConfig.sample_ns` / `local_delay_ns` / `max_age_ns` | 采样周期、测量release延迟、最大可用年龄；都和积分dt不同 |
| Sensor `source` | 数值fixture或实测来源声明；不自动把ENGINEERING_ASSUMPTION升级CALIBRATED |

不要只改一个gain就认为完成热控调参：物理模型、单位、测量延迟、inner/outer周期、饱和、反向和Safety限制需要一致；本修复任务不修改任何冻结控制gain。

## 7. 六个tracking状态与结果怎么看

STEADY_TRACKING=无当前未完成方向；HANDOFF_PENDING=合法等待；TRACKING_PROGRESS=真实合格运动；TRACKING_FAULT_SUSPECTED=不足响应怀疑；TRACKING_FAULT_CONFIRMED=符合冻结确认规则；INSUFFICIENT_MEASUREMENT=测量不可用，不能自动指控泵故障。

前三者不增加tracking限制；SUSPECTED贡献DEGRADED；CONFIRMED贡献FAULT并保留latch；测量invalid的sensor原因由独立Safety处理。Safety输出限制和reasons，PLC才签命令。POST STEADY不抹掉同拍PRE/Safety事实。

PASS：该明确scope判据通过；FAIL：有效输入/证据下违反判据；INCOMPLETE：缺前提或因果证明；INVALID：来源/环境/结构/持久化不可信，不能裁决算法。GitHub绿色只是job退出状态，必须回读artifact/hash/Job身份。

原Startup49/50与versionedPASS必须分开。五个causal excluded案例仍保留原测试，只是不授strictP1 Lane B/C PASS。PF06原范围INCOMPLETE与C8补充DEVELOPMENT_VALIDATED_PENDING_APPROVAL也分开。

## 8. 当前不能省略的发布条件

`M1-DEF-POST-001` 的新v4失败路径测试需先在v3证明失败，再在修复版证明通过；序列化和completed-store错误也不能产生新成功publication。之后需要新源码identity、受影响回归和fresh完整开发验证，不能拼接Build005分数。

wheel/source安装、运行入口、完整参数文档和使用示例仍需验收。旧v0.2包0.2.0a5仍是alpha，不能仅改版本号就当已上线。正式C3-C/生产/硬件/Phase6权限仍需独立明确授权。

本草稿覆盖M1 tracking与公共feedback配置。热容/热源/冷板/液体焓/输运/水力/泵功耗/CDU/FWS/数值方法/场景/Safety参数见同目录 [v0.2物理参数参考](V02_PHYSICS_PARAMETER_REFERENCE.md)。这些说明按源码静态核对；实际安装和发布命令尚未验收，不能把说明文档当作软件已上线。
