# liquid-recovery-v1：恢复准备，不是已完成液冷验证

当前开发机 HIPPO 多次整机硬挂。本版本不在这里启动 Python、压力循环、prefix 或 campaign；旧 isolation/v014.1 入口保持历史身份，**不要再运行**。不修改旧 candidate、物理、控制器、Safety、profile、合同或冻结判据。无布尔压力前置步骤。

## 已可安全验证的部分

`batch.ps1` 是新执行链的整批首错停止**控制层**，不是远端执行器。阶段 adapter 必须先验证源/环境、限制资源、清理自己拥有的进程、持久化并核验 raw 证据，再提交一个结果 dictionary。控制层拒绝 `passed=false`（即便 cleanup 成功）、非零 exit、crash、FAIL/INVALID/INCOMPLETE、缺字段、错误类型、drift、未完成清理或持久化失败。STOP 之后不调用下一项，不重试。结果和 BEGIN/END/STOP 均 CreateNew + flush-to-disk + hash 回读；旧目录不续跑。宿主突然断电可能只留下 BEGIN，不能推断 PASS 或确定死机指令。

本机只允许这两个有限的合成/静态检查；第二项使用第一项实际返回的目录，不从旧成绩借 PASS：

```powershell
& .\v0_2\tests\tools\liquid_recovery_v1\verify_batch.ps1
& .\v0_2\tests\tools\liquid_recovery_v1\verify_prepared.ps1 -SyntheticEvidence '上一步目录\synthetic_evidence.json'
```

合成检查不创建进程、不执行模拟、不证明 Windows/Python/native/硬件已稳定。`Scope=SYNTHETIC_CONTROL_PLANE` 仅用于上面的假结果回调，不能装入真实 workload。

## 独立执行环境：还没接通

优先 GitHub **托管** Windows runner，不在本机装 self-hosted runner，不把本机 VM 当独立硬件。CLI 已登录，仓库公开；没有推送、新增活动 workflow 或触发 CI。上传/触发需单独明确授权。

后续 remote adapter 应先在独立环境完成启动/退出/日志/owned cleanup 验证，登记 Python 3.11.9 + 原 exact dependency lock、host/OS/image/version/路径、源 inventory RAW hash；核验前后身份。然后才批准新环境的 `GENERIC_LIQUID_COOLING_DEVELOPMENT_SMOKE`。`admission.py` 默认拒绝缺少经审阅注册的执行，支持的独立位置只有 GITHUB_HOSTED_WINDOWS。注册是实际环境的独立记录，不能修改旧 M1 environment lock 去绕 guard。

**本包不包含获批的远端注册、不包含实际 process-launch adapter，也没有完整远端 ready/PASS。** 环境变量不是安全沙箱；trusted runner 仍须实现限额、所有权清理、raw stdout/stderr 先持久化和完整记录解析，不得只凭 pytest exit=0 或 progress END 判 PASS。移植到独立环境不等于已找到死机唯一根因。

## 已准备的液冷 smoke

`plan.json` 引用 12 个原 test functions（计划展开 20 项），分热节点、水力/运输/CDU、短反馈三层。所有输入和断言来自原测试，不新造物理阈值、tracking timer、延迟或判据。`pytest_plugin.py` 为明确选中的现有函数记录 setup/call/teardown，核验收集数量，skip/缺项也 STOP。未来仅在获批环境中使用 `-x -p v0_2.tests.tools.liquid_recovery_v1.pytest_plugin`，禁止宽泛 collect 整个历史 tools 树。禁用第三方 plugin 自动加载并限制 BLAS 线程；这些是新执行环境策略，不改控制语义。

`physical_probe.py` 是额外诊断：原 branch=2 / 5 s / dt=0.1 s 输入，直接调用未改的 `plant.loop.step` 50 次。普通 `mark()` 记录每个物理步、账本读取和聚合，报告能量残差、质量残差、泵压差、流量和换热功率；按原 PlantRun 能量/质量 gate 检查。与原未加日志 harness 的完整状态和账本相等是**instrumentation equivalence**，不是用 candidate 输出生成 golden 预期。原 test bodies 仍独立执行。Python 文件尚未在安全环境做语法/运行验证，不能宣称已工作的 smoke PASS。

薄日志独立 JSONL，单文件 2 MiB、单记录 8 KiB；每条 fsync。无 decorator/context-manager tracing、Python FFI、watchdog thread、bool-call tracing、未知对象 repr。它不读取 PRE future command、不生成 PLC receipt、不给 tracking 加 evidence。`PHYSICAL_STEP` 内包含水力/热力/HX 求解；若只看到它的 BEGIN，**只能定位到这个调用边界，不能判定内部哪条 native 指令出错**。反馈 smoke 当前只记录原 test call 边界，不宣称已具备每个 PRE/PLC tick 的薄日志。

## 后两步仍未执行

独立 smoke 和 M1 新环境/adapter 均通过后，再 fresh REFERENCE→冻结 SELECT→SPLIT→短 selected prefix→全部 selected prefixes / repeats，重点 descriptor 65/66/92。每个 prefix 从 t0 完整重放；可按每个 prefix 独立子进程，不把长 prefix 切断后续算。不能变更 selection/expectations。

之后从新起点跑完整 development campaign（全部库存、Startup 原结果与版本化结果分开、C/S/P15、因果性/repeats/PF 分域）。PF06、异步 P1 来源缺口或其他 scoped incompleteness 不能因迁移执行就抹掉。现有 v014.1 guard 与日志形态不在这里绕过；新 adapter 还需独立身份、source snapshot 和验证。

任何首错 STOP，保存失败，下一任务再修。formal C3-C、production port、Phase 6、硬件控制和 Git 发布均不由本包自动授权。Full P history unavailable；real hardware CALIBRATION_REQUIRED。
