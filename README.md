# C2C-DTB / 算力到冷却数字测试台

Compute-to-Cooling Digital Test Bench is a deterministic, reduced-order simulator for developing and validating the chain from AI workload to GPU power, liquid heat capture, rack thermal response, coolant transport, CDU heat rejection, PLC control, and supervisory cooling intent.

V0.1 is a local engineering model, not CFD, SCADA, a production PLC, or an OEM/NVIDIA performance claim. All GB300-class and CDU values are labeled assumptions until replaced by measured, OEM, literature, or calibrated data.

V0.1 是本地工程模型，不是 CFD、SCADA、生产 PLC，也不构成 OEM/NVIDIA 性能声明。所有 GB300 级与 CDU 参数在被实测、OEM、文献或标定数据替换前，均明确标记为假设值。

## V0.2 phase baselines / V0.2 阶段基线

V0.2 is built as an isolated tree (`v0_2/`) with its own distribution and test paths. It neither imports from nor modifies the V0.1 `src/c2c` package. Every phase stops for review and is frozen as an annotated tag whose message carries that phase's gate status verbatim from its report.

V0.2 以隔离目录 `v0_2/` 构建，拥有独立的发行包与测试路径，既不导入、也不修改 V0.1 的 `src/c2c` 包。每个阶段都停止待审，并以 annotated tag 冻结，tag message 原样引用该阶段报告中的 gate 状态。

| Phase | Tag | Commit | Deliverable | Report | Gate |
|---|---|---|---|---|---|
| 1 + 2 | `v0.2-phase1-2` | `020f681` | Refactor plan, V0.1 manifest, architecture, 16 contracts | [PHASE2_REVIEW_SUMMARY.md](PHASE2_REVIEW_SUMMARY.md) | `PHASE2_GATE_STATUS = PASS` |
| 3 | `v0.2-phase3` | `9aa8cc0` | Isolated constant-C thermal core and integrator | [PHASE3_THERMAL_REPORT.md](PHASE3_THERMAL_REPORT.md) | `PHASE3_GATE_STATUS = PASS` |
| 4 | `v0.2-phase4` | `5588915` | Physical coolant loop, pump network, finite CDU/FWS | [PHASE4_PHYSICAL_PLANT_REPORT.md](PHASE4_PHYSICAL_PLANT_REPORT.md) | `PHASE4_GATE_STATUS = PASS` (generic fixture only) |

Phase 1 and Phase 2 share a single commit; no separate Phase 1 commit exists. Phase 4.1 and Phases 5–9 are not published.

阶段 1 与阶段 2 共用一个 commit，不存在单独的 Phase 1 commit。Phase 4.1 与 Phase 5–9 尚未发布。

A phase gate covers only the evidence in its own report. No PASS above means GB300/OEM calibration, equipment safety, or an authorized controller. Every V0.2 fixture parameter stays `ENGINEERING_ASSUMPTION / NUMERICAL_TEST_FIXTURE / UNVALIDATED` until replaced by measured or vendor data. The published evidence reproduces directly from the repository root:

每个阶段门禁只覆盖其报告中的证据范围。以上任何 PASS 都不代表 GB300/OEM 标定、设备安全或可授权的控制器。在替换为实测或厂家数据前，V0.2 的全部夹具参数保持 `ENGINEERING_ASSUMPTION / NUMERICAL_TEST_FIXTURE / UNVALIDATED`。已发布的证据可从仓库根目录直接复现：

```powershell
.venv\Scripts\python -m pytest -c v0_2/pyproject.toml v0_2/tests -W error
.venv\Scripts\python -m v0_2.examples.phase3_validation
.venv\Scripts\python -m v0_2.examples.phase4_validation
```

## Run the benchmark

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m c2c.simulation.runner configs/scenarios/workload_step.yaml
.venv\Scripts\python -m c2c.simulation.runner configs/scenarios/workload_step.yaml --locale zh-CN
.venv\Scripts\python -m pytest
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/c2c-dtb --locale zh-CN
.venv/bin/python -m pytest
```

The benchmark writes `config.yaml`, `metadata.json`, `timeseries.csv`, `summary.json`, plots, and a self-contained `report.html` under `results/<run-id>/`. Machine-readable field names remain stable in English; `--locale en` and `--locale zh-CN` localize human-facing report copy, case names, threshold labels, and plots.

基准测试会在 `results/<run-id>/` 下生成配置、元数据、时序 CSV、摘要 JSON、图表和自包含 HTML 报告。机器可读字段名保持英文稳定；`--locale en` 与 `--locale zh-CN` 用于切换报告文字、工况名称、阈值标签和图表语言。

## Threshold interpretation / 阈值解释

`summary.json` and `report.html` now separate commanded safety limits from process response. A coolant temperature temporarily above its setpoint is a control deviation, not automatically a guardrail violation. The `threshold_checks` array reports the measured value, comparator, configured limit, unit, and pass/fail result for each case.

`summary.json` 与 `report.html` 会区分“控制指令安全限值”和“被控过程响应”。冷却液温度短时高于设定值属于控制偏差，并不自动等于安全限值被突破。每个工况的 `threshold_checks` 都会列出实测值、比较符、配置阈值、单位及通过/超限状态。

Both cases use identical feedback control before the first load step. Feedforward is enabled at that step; `controller_response_delay_s` measures valve movement by 2 percentage points in both cases, while `setpoint_response_delay_s` separately measures a 0.25 K setpoint change. These delays measure control outputs, not physical cooling completion. Startup and post-step supply deviations are reported separately. Missing/non-finite samples produce `INVALID`, suppressing comparisons; a zero baseline pump energy gives a null percentage change.

The report also embeds `response_timeline.png`: matched feedback/feedforward panels show GPU power, accepted/ramped temperature targets, pressure targets, pump/valve commands and the temperature/pressure inputs actually read by the PLC. `response_events.json` records first threshold crossings relative to the first load step over its high-load window, using the preceding 60 s mean as baseline. No crossing is null, not zero. The chart zooms to -30..180 s. These are simulated signal departures, not sensor detection delays: feedforward itself changes the fluid signals; static hydraulic resistance does not depend on heat. No future-load prediction or junction-temperature-driven control is claimed.

报告新增“控制响应时间线”和事件表：左右对照仅反馈与功率前馈，展示 GPU 功率、温度/压差目标、泵阀动作及 PLC 动作前读取的温度/压差。PNG 可单独导出，JSON 保留事件时间、变化阈值和基线窗口。未达到阈值显示“高负载窗口内未达到”。当前默认场景前馈泵速达到 2 个百分点变化的延迟为 0 秒，阀位为 5 秒；仅反馈阀位为 104 秒。这些是仿真阈值事件，不是硬件传感器感知延迟。

两组在首次负载阶跃前采用完全相同的反馈控制，阶跃时才启用前馈。`controller_response_delay_s` 统一表示阀位变化 2 个百分点所需时间；`setpoint_response_delay_s` 单独记录设定值变化 0.25K 的延迟。这些指标衡量控制输出，不能解释为物理降温完成时间。启动阶段与阶跃后的供液偏差分别报告；数据缺失或非有限数值标为 `INVALID` 并停止工况比较，基准泵能耗为零时百分比变化记为 null。

The default temperature setpoint now slews at 0.1 K/s (`controls.temp_setpoint_ramp_k_s`, also the default for older configs). Both cases pass the configured checks. The 3 K criterion evaluates tracking of the actual ramped control setpoint: feedforward post-step error is about 1.838 K; whole-run maximum is 2.909 K from startup. Deviation from the final accepted target is separately reported and still reaches about 3.261 K. PASS therefore does not mean the final target is reached immediately. Relative to an abrupt setpoint, hotspot peak increases about 0.077°C and illustrative facility cooling energy about 0.15%; pump energy is unchanged.

默认温度设定值以 0.1K/s 渐变（`controls.temp_setpoint_ramp_k_s`，旧配置缺省值也为此值），两工况通过配置检查。3K 阈值检验相对实际渐变控制设定值的跟踪偏差：前馈阶跃后约 1.838K，全程最大值来自启动阶段，为 2.909K。相对最终接受目标的偏差单独报告，仍可达约 3.261K；PASS 不表示已经立即达到最终目标。相对设定值突变，热点峰值增加约 0.077°C，示意性设施冷却能耗增加约 0.15%，泵能耗不变。

The legacy `gpu_temperature_c` field represents an aggregate equivalent hotspot, with CPU/other liquid heat traversing the same RC path. It is not a calibrated GPU junction temperature. See [model boundaries and review corrections](docs/review-corrections.md).

保留的 `gpu_temperature_c` 机器字段代表聚合等效热点，CPU 等液冷热仍经过同一 RC 路径；它不是已标定的 GPU 结温。参见[模型边界及审查修正](docs/review-corrections.md)。

## Safety boundary

L0 physical protection remains outside this simulator. L1 is a deterministic virtual PLC with clamps, ramps, timeout behavior, and local fallback. L2 LCI produces setpoint intent and cannot bypass L1. The default case logs LCI in shadow mode; the comparison case explicitly enables guarded feedforward for research comparison.

L0 物理保护不在本仿真器范围内。L1 是具有限幅、斜率限制、超时与本地回退能力的确定性虚拟 PLC。L2 LCI 只产生设定值意图，不能绕过 L1。默认工况仅以影子模式记录 LCI；对比工况明确启用受保护前馈，仅用于研究比较。

See [the architecture decision](docs/c2c-architecture-decision.md), [physics](docs/physics.md), [assumptions](docs/assumptions.md), and [validation plan](docs/validation.md).

## GitHub readiness / GitHub 上传准备

GitHub Actions runs Ruff and Pytest on Python 3.11–3.13 for every push and pull request. The isolated V0.2 tree is a separate distribution with its own test paths, so it is gated by its own job, which additionally builds the `v0_2` wheel and reproduces the Phase 4 evidence from outside the checkout. Generated results, local environments, caches, and downloaded references are excluded by `.gitignore`. The project is released under the [Apache License 2.0](LICENSE).

GitHub Actions 会在每次推送和拉取请求中使用 Python 3.11–3.13 执行 Ruff 与 Pytest。隔离的 V0.2 目录是独立发行包，拥有自己的测试路径，因此由单独的 job 把关，该 job 还会构建 `v0_2` wheel 并在仓库外复现 Phase 4 证据。生成结果、本地虚拟环境、缓存及下载的参考资料均已通过 `.gitignore` 排除。本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
