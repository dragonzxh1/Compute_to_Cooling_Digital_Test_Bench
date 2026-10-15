# M1 v4 当前操作入口

更新于 2026-10-15。本页是当前状态索引，不修改冻结源码、包内说明或历史证据。

## 1. 当前能做什么

这是离线液冷数字孪生与 tracking 软件验证平台，不是可接管现场 CDU 的控制器。已完成的 V4 development campaign 和仓库外 source SDK 开发验收，与 formal C3-C 分开记账。

用户已批准并执行 v4 确切包的独立 fresh formal。[本轮 run 38675166533](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38675166533) 已结束为 INVALID。不能把“已开考”、开发 PASS 或 GitHub job 绿色写成正式通过，更不能据此宣布生产上线。

最新结果优先于上一段开考时点状态：本轮已因 `FINAL_ACCEPTANCE` 受控超时停止，`INVALID_C3_C_EXECUTION / behavioral_adjudication=NOT_MADE`。969项上游静态阶段缺项0，但最终验收没有完成；不改判candidate行为FAIL，不授正式PASS，不自动重跑。详见 [v4正式失败报告](M1_C3_C_V4_FORMAL_FAILURE_REPORT.md)。

后续仅做独立开发修复：[v5耗时定位和检查器验证](M1_C3_C_V5_READONLY_TIMING.md) 已测得重复包校验放大；新审计版本的17项合成检查通过，未改变candidate或判据。完整真实证据/FINAL开发复现仍待完成，新的正式包尚未冻结、未开考。不能将该检查器成绩升级为资格或上线结论。

[完整上游native回读](M1_C3_C_V5_ARCHIVED_NATIVE_READBACK.md) 已完成并独立核对：716批次、1969阶段记录、57107原始文件逐项匹配；失败FINAL仍单独保留。此项关闭了“优化只在小型合成输入上验证”的缺口，但case/Startup/PF/schema等剩余FINAL聚合开发复现还未完成，旧v4仍INVALID。

冻结旧说明中的“尚未审签/尚未授权”是打包时点的历史状态；本轮新授权以 [正式执行记录](M1_C3_C_V4_FORMAL_EXECUTION.md) 和 `artifacts/m1-c3c-v4-authorization/` 的独立收据为准。原件不回写。

## 2. 安装及示例从哪里开始

完整命令、输出解释、故障处理和平台限制见 [使用说明第 9 节](M1_SOFTWARE_USER_GUIDE.md#9-已验证的-source-sdk-安装与使用)。只在另行批准的稳定执行机使用；当前发生过硬挂的本机仍禁止 Python/native/model 执行。

| 对象 | 确切身份或限制 |
| --- | --- |
| 已验证 source SDK | 执行 commit `9f0b2e87a7c324a841274bc92303b009fbebbb63` 内的 `artifacts/m1-sdk-streaming-v3/source-sdk.zip` |
| SDK ZIP SHA-256 | `820baee49b3170dc07bc7bb6bfa3ffdc9732c9c79492ccc7df43699202e6bf78` |
| 安装开发证据 | [run 38493762797](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38493762797)，[独立回读记录](M1_SDK_STREAMING_READBACK.json)：仓库外安装，101 个完整登记输入、6432 帧、707 个 trace 文件 |
| 已验平台 | Windows Server 2022 / Python 3.11.9 / 锁定依赖；其他平台未获本证据覆盖 |
| root/v0.2 wheel | 不是此 M1 source SDK，不要用 `pip install v0_2` 冒充完整 M1 安装 |

SDK 的 `--describe` / `--verify` 用于说明与文件校验；`--run` 才执行离线模型。`--input-index` 是 0..100 登记输入索引，`--rows` 是从起点回放的行数，不是积分步长。CLI 自身不替任意用户进程施加 Windows Job 限制。安装开发验收不自动成为本轮 C3-C 成绩，也不保证任意用户工况。

本轮文件级交付核对记录见 `artifacts/m1-c3c-v4-authorization/sdk_formal_source_crossbinding.json`：675 个 SDK 文件长度/哈希已复核；与 formal 清单共有 671 个路径，其中 670 个原始字节完全相同，唯一差异为打包时的旧使用说明，candidate 与共有代码无差异。SDK 专用的 LICENSE、静态参数覆盖记录、`sdk_cli.py` 和 README-SDK 不在 formal source closure 中，不能据此宣称 SDK CLI 本身获得本轮正式资格。

## 3. 参数意义在哪里查

| 参数类别 | 说明入口 | 注意 |
| --- | --- | --- |
| tracking profile、六个公开状态、时间和单位、执行资源 | [M1 使用说明第 3～7 节](M1_SOFTWARE_USER_GUIDE.md) | 命令速度为归一化 fraction，不是 RPM；有效测量才赚证据 |
| 反馈 PID、执行器、传感器公共配置 | [M1 使用说明第 6 节](M1_SOFTWARE_USER_GUIDE.md#6-反馈控制--执行器--传感器公共配置) | 增益单位随环路输入/输出改变，不能跨环照抄 |
| 热容、热阻、液体输运、水力、泵、CDU/FWS、数值方法和保护字段 | [v0.2 参数参考](V02_PHYSICS_PARAMETER_REFERENCE.md) | 静态字段说明；数值假设不等于设备实测校准 |
| 旧版场景 YAML 和中英文报告入口 | [旧场景参数参考](LEGACY_SCENARIO_PARAMETER_REFERENCE.md) | 旧仿真不等于新 M1 PRE/Safety/PLC/POST 验证入口 |
| 字段覆盖证据 | [parameter_reference_coverage.json](parameter_reference_coverage.json) | 37 类 / 259 字段的静态覆盖，不是全部未来配置或硬件资格 |

CPU 25%、process/job 内存和 480 s 墙钟预算限制测试执行机资源，不是液冷参数，也不允许改变冻结模型 timer。温度 K 与摄氏度、Pa 与 kPa、kg/s 与 m³/s 必须按说明换算，不能混用。

## 4. 本轮正式考试的确切身份

| 对象 | 身份 |
| --- | --- |
| execution / delivery commit | `9012d6d9292a44226b0892332879de506812206d` |
| 固定执行 ref | `codex/m1-c3c-v4-proposal-9012d6d`；后续文档 HEAD 不能替代 |
| Proposal RAW SHA-256 | `759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357` |
| Candidate SHA-256 | `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce` |
| 限定范围 | `M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN`，101 descriptors / 3216 rows / 499 planned full snapshots / 969 static stages 加 FINAL |

动态计划来自本轮实际参考输出，已独立核验 2281 个选中前缀 / 67575 计划帧对；不是把旧测试成绩复制过来。最终还必须核验所有实际回放、repeat、schema、source/environment、原始日志、真实 Python Job 身份及 FINAL 退出后的 cleanup。

不要为了查看结果手工再次 dispatch、重跑 failed jobs 或修改本次考试程序。任何预登记 FAIL 或完整性问题保留证据并停止；后续修复必须独立版本和新授权，不能在同一次 execution 内修后重考取 PASS。

## 5. 上线结论仍有哪些边界

原 Startup 历史 49/50 与 versioned compatibility 单列；SEM02 精确五项严格 P1 Lane B/C 仍 INCOMPLETE；PF06 original scope 仍 INCOMPLETE，C8 补充独立登记判分。原 v3 无效运行不改判。

任意 POST 异常、操作系统崩溃或掉电原子性 NOT_PROVEN；T09 物理持久恢复 IMPLEMENTATION_HOLD；完整 P 历史不可用；真实硬件 CALIBRATION_REQUIRED。本机硬挂根因未获解决证明，远程隔离不是本机稳定性认证。

即使本轮限定软件正式资格通过，也不自动获得生产移植、真实硬件控制或 Phase 6 权限。本轮完整 C3-C 结果及独立证据验收完成前，不能宣布“全部阻塞解决”或“已达上线状态”。
