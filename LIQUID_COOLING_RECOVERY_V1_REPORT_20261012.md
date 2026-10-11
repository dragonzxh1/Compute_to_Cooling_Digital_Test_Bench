# 五步恢复实施状态（2026-10-12）

## 当前结论

第 1 步的新版首错停止控制层已完成并经过有限合成验证；第 3 步的真实液冷小案例/薄日志已准备。第 2 步尚无独立执行环境授权/登记，所以第 3 步行为验证、第 4 步长 prefix、第 5 步完整 development campaign **均未执行**。本轮没有启动 Python、native helper 或布尔压力循环；也没有找到或宣称找到整机死机的唯一根因。

大白话：先把“已失败还继续跑”的缺口堵上，把真正的液冷试题和日志准备好；接下来换到独立机器做题，不让这台反复死机的电脑再冒险。

| 五步 | 本轮实际状态 | 继续条件 |
| --- | --- | --- |
| 1 首错整批停止 | 新控制层 `liquid_recovery_v1/batch.ps1`，29/29 合成检查 PASS；未做真实进程集成验证 | 独立环境的 trusted process adapter 还须验证启动/退出/限额/raw persistence/owned cleanup；控制层 PASS 不等于 native executor PASS |
| 2 稳定执行环境 | CLI 登录和公开仓库只读检查通过；建议 GitHub 托管 Windows runner；未提交/推送/触发 | 明确外部上传/触发授权，建立独立环境身份和受控 executor；不能改旧 M1 env lock 来绕 guard |
| 3 液冷小案例 | 12 个原测试函数，计划展开 20 项；另有 5 s、50 步物理账本诊断；输入/原断言不改 | 独立环境运行前后源/env 核验；Python syntax/runtime 与日志实际验证尚未执行 |
| 4 长 prefix | 重点 indices 65/66/92 的 fresh reference/selection/replay/repeat 顺序已写进 plan；NOT_RUN | 所选每个 prefix 从 t0 完整重放；不分段续算、不降低因果性/重复要求；新 M1 环境/adapter 尚未准备完成 |
| 5 完整 development | fresh 全套库存/Startup/C/S/P15/PF/prefix/repeat 范围已登记；NOT_RUN | 前序通过后新起点执行；保留 PF06/异步来源等作用域缺口，不拿旧分数拼接 PASS |

## 已修的自身缺陷

旧 `runtime_isolation_v5/isolate.ps1` 最后只在 cleanup 不完整时 throw；此前记录 `passed=false`、child 非零退出，仍可能以成功脚本状态返回。外围仅看 `$?`，导致已失败后继续下一案例。此缺口是已确认的执行策略问题，**不是已证明的硬挂唯一根因**。

旧脚本、旧故障和中断证据保持不变，不能再使用旧诊断入口。新增的控制层要求 source/env/evidence/primitive/cleanup 均明确 true、native EXITED、launcher/child exit 与清理后活跃数为整数 0、capture COMPLETE、result PASS、passed 为真正 boolean true。错误类型、数组冒充状态、缺字段和 `passed=false + cleanup=true` 都被拒绝。证据 CreateNew、fsync/回读后再判门禁；首错 STOP，之后项 NOT_RUN，不同轮失败不回写。

控制层是 trusted adapter 的下游，不会凭空证明其提交的 Job receipt/限制参数真实。本包尚无实际进程启动 adapter。当前 HIPPO development scope 默认拒绝，Python smoke admission 也拒绝本机或未登记执行；旧归档入口未被偷偷改写，不代表所有旧脚本都已物理禁用。

## 液冷与日志范围

`plan.json` 按热节点 → 水力/运输/CDU → 短反馈排序。采用原 Method、分支数、流量、温度、功率、dt、解析解和数值判据；没有 retuning、profile/timer 或生产策略变更。短反馈使用原 5 s 控制案例及 4 s 负载事件，第一轮不以 120 s sweep 或整套历史 pytest 为启动 smoke。

`pytest_plugin.py` 只记录明确选中测试的 setup/call/teardown，检查 collection 数量，skip/缺项不算 PASS。额外 `physical_probe.py` 重放原 branch=2、5 s、dt=0.1 s 物理输入，每步记录 `PHYSICAL_STEP` 和 `LEDGER_READ`，最后沿用 PlantRun 能量/质量 gate。与原 harness 状态/账本完全相等用于检查日志适配是否干扰模型，不生成 candidate golden expectation。

`progress.py` 使用普通 mark，没有 Python FFI、contextmanager/decorator tracing、timer thread、sys.settrace 或逐 bool 日志。单文件 2 MiB、单记录 8 KiB，单线程 fsync；未知对象不 repr，日志独立于 stdout，identity 字段不能被 metadata 覆盖。读取的是离线物理诊断账本，不作为 tracking 的 TRUE fallback。

局限如实保留：这些 Python 文件未在本机执行，语法/实际 hook 行为/动态 collection/物理等价性仍需独立环境验证。物理步内部尚未逐一拆出水力、热矩阵和 HX native 指令；反馈仅有 test call 边界。缺少 END 只定位到未返回的调用边界，不证明该函数是整机故障原因。

## 新鲜本地证据（仅静态/合成）

- 合成：`artifacts/liquid-recovery-v1/synthetic-18e42f3fa5db40769b5ea51195daa015/synthetic_evidence.json`，29/29 PASS。RAW `0a8a44d1057bd517f665a8152a5e39d7a52716cd9a4678669b84af7cf3c08a5a`。
- 准备包：`artifacts/liquid-recovery-v1/preparation-55b3c48942154621bc85c884fbc67c3b/preparation_evidence.json`，177 个静态检查 PASS；68 个 smoke source bindings。RAW `039501dc7dae1e4c0ec1e4f02fe8b072a158b0da1c7699766b01d3d42135c1a4`。
- `v0_2/tests/tools/liquid_recovery_v1/source_inventory.json` RAW `f1cdfa0c40945b6315baff794cf0ef2cd4d4afb3cc166f95655de2f2f74451e0`。后续环境登记需绑定此 inventory hash，不能只有口头“同一代码”。
- 原 655 个保护源全部匹配旧 registration，before/after 无漂移；`git diff --exit-code` 通过。只新增本阶段工具/报告/独占 evidence，不改 tracked 文件。早先 25 项合成/177 项静态输出也保留，但最终结果使用本轮与最终源码匹配的证据，不借旧成绩。

这里的 177 项主要是路径、已有函数、JSON 计划、PowerShell 语法和 hash 校验；不是 177 次液冷行为测试。

## 虚拟机和 GitHub 建议

不需要先在这台开发机安装 VM。它依然共用宿主硬件/驱动，不能保证避免宿主硬挂。优先把执行搬到独立机器。GitHub 官方说明标准托管 Windows runner 使用 GitHub 提供的远端 VM；其 image 会更新，因此实际 OS/image/version 必须独立登记，不能宣称复用了旧 Windows 身份。[GitHub-hosted runners](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners)

已只读核验 `dragonzxh1/Compute_to_Cooling_Digital_Test_Bench` 为公开仓库。标准托管 runner 的公开仓库运行分钟按官方政策免费；artifact 存储另有配额/费用规则，不承诺所有存储永久免费。[Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

本轮无新增 active workflow、无 commit/push、无 dispatch、无 VM/系统/Python 安装。后续授权应只上传必要非 DSX 源和恢复包，用独立 Windows runner 先做环境 preflight 和 small smoke；不要因 push 自动触发现有 broad 历史全量 CI。在 small smoke 和独立 M1 adapter 准备完成前，不启动长 prefix/campaign。

## 边界和下一动作

行为测试执行数 0；liquid smoke / prefix / campaign 均 NOT_RUN；host stability NOT_PROVEN；正式 C3-C/production/硬件/Phase 6/Git 发布均未执行。原 Startup 成绩不改写，full P history unavailable，real hardware CALIBRATION_REQUIRED。

下一动作：请求明确授权上传必要恢复包并使用 GitHub **托管** Windows runner；第一批仅独立环境 preflight + 小案例，不触发旧全量 CI。无此授权时保留准备包，停止本机 workload，不用更多 bool 压力绕过环境缺口。
