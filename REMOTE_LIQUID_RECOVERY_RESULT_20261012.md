# 独立远端液冷小案例：验证通过（2026-10-12）

## 当前结论

新鲜远端 run **38167232621** 全部六个 stage PASS：原液冷 pytest **20/20**、日志数值适配 **11/11**，额外 5 s / 50 个物理步诊断 PASS。完整 artifact 已下载、raw hash 和本地门禁逐项核验，不仅凭 Actions 绿色状态。

大白话：我们现在已经真正跑通热量、泵流量、冷却液运输、CDU 换热和短反馈测试；没有继续困在布尔压力循环。运算在 GitHub 的独立 Windows 机器上，本机没有启动 Python，也不需要在本机安装 VM。

[通过的远端运行](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38167232621)
使用代码 commit `6fef7849d18610df92849e7b60ec1eb3558c33f3`，分支 `codex/liquid-recovery-remote-20261012`。后续说明/结果提交不改变本次已测试代码身份。

## 本轮实际成绩（不继承前轮）

| Stage | 本轮结果 | 验证内容 |
| --- | --- | --- |
| ENVIRONMENT | PASS | 实际 Python 专属 Job 身份、限额、启动退出与清理；源码和 exact deps；独立环境登记 |
| LOG_SCALAR_ADAPTER | 11/11 PASS | 明确 NumPy 标量转换、整数精度、finite、未知 hooks/数组/complex/string 拒绝 |
| THERMAL | 6/6 PASS | 三种原 Method 的平衡/恒功率解析解和能量一致性 |
| HYDRAULICS_TRANSPORT_CDU | 11/11 PASS | 分支质量/压差、泵能量账、冷却液指数解/mesh、CDU 解析解、完整回路守恒 |
| PHYSICAL_PROBE | PASS | 50 个原物理步与日志；原能量/质量门禁；与原 unlogged harness 完整状态/账本等价 |
| SHORT_FEEDBACK | 3/3 PASS | 执行器滞后、测量释放/no truth、5 s 反馈与未来负载因果性 |

本轮逐项 fresh execution；没有借用首轮 6/6 或 11/11 分数。未执行完整旧 CI、长 prefix、M1 campaign 或正式资格。

## 证据核验

- 六个 stage 结果与 `batch_complete.json` receipts raw SHA 匹配，全部 PASS；无 batch_stop。
- 六个实际 Python 外部 Job proofs 全部有效：CPU rate 100/10000、process/job 256/512 MiB；native exit 0，cleanup=true，active_after_cleanup=0。
- 24 个 stdout/stderr/验证器 raw evidence receipts 下载回读全部匹配；前后 environment identity 在本轮完全一致。
- 物理薄日志 208 条记录；50 个 PHYSICAL_STEP BEGIN/END，tick=0..49，物理时间完整从 0 到 5,000,000,000 ns，没有 ERROR；账本和 instrumentation equivalence 的 END 均存在。
- 完整机器结果：`v0_2/tests/tools/liquid_recovery_remote_v1_1/remote_smoke_result_20261012.json`。其包含环境、所有 stage receipts 和 authority 边界。

Batch COMPLETE RAW：`560e02cc23d4884cc717d95701367f6950f3b6ad6590c3ff47d73b864690d433`。
Physical progress RAW：`451b3d258fb49b0f73d15b1c5dbfd3450eb3d3a202f82b28c77f898355ebde85`。
Environment registration RAW：`6cc924a52f619302753dc18a3404015ad8f114cae96e7334e8fbda3d436ed7a4`。
环境为 GitHub 托管 Windows Server 2022，Python 3.11.9，image `20261004.326.1`，原 exact declared dependency lock；不是旧本机 26H2 身份替换。

## 5 秒物理账本

| 指标 | 本轮值 |
| --- | --- |
| 输入热量 | 1200 J |
| 总能量残差 | -6.880043201817898e-10 J |
| 节点/容积最大质量残差 | 0 kg/s / 0 kg/s |
| 最终总流量 | 0.24647515087732474 kg/s |
| 泵压差 | 42525 Pa |
| CDU 供液温度 | 299.584598853581 K |

使用既有 generic fixture/门禁，不是 OEM/GB300/现场标定结果。stored_j 为负是原初温高于 FWS、回路净降温的能量变化；本轮输入、泵热、外排与储能账按原门禁守恒，不人为剪裁结果。

## 首轮失败和修复没有抹掉

[首轮停止 run 38166700254](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38166700254) 保持失败。环境/前两类已通过，PHYSICAL_PROBE 在第 0 步已完成后、LEDGER_READ 的写日志处抛 `ValueError: PROGRESS_PRIMITIVE_METADATA_ONLY`；child exit=1，owned cleanup complete，下一项 NOT_RUN。这次首错停止按预期工作，不是硬挂，也不是守恒断言失败。

NumPy 求解/HX/账本链保留 NumPy 数值，strict primitive logger 不接受该类型。
新增 remote v1.1，仅在诊断日志/JSON 出口转换显式允许的 NumPy scalar；新 11 项回归通过。原 v1、原 profile、Physics/Safety/controller、fixture 与断言保留，source bundle SHA 不变；没有同一 execution 修改后重跑，也没有对原失败改判。

## 发布和未覆盖范围

GitHub CLI 完成入口登记/dispatch/artifact 下载，GitHub CLI credential helper 认证上传独立分支。默认 main 仅新增 manual workflow 入口（commit `0f97c7a4081145bfa6d8f2a234be89b5a4021be8`）；新源码包、版本化修复和说明在独立 worktree 分支。提交均 `[skip ci]`，旧 broad push/PR CI 未触发、旧失败未删；没有 PR/merge、DSX 更新或临时日志批量入库。

原开发目录的 655 个保护源复核无漂移，tracked 用户文件未改。本次完整上传是完整恢复测试包及所需依赖，不是全部历史 M1 未跟踪文件的大包；原目录/证据保持原样。

**这证明独立环境中这一小范围计算能完整执行，不证明本机死机根因已找出或本机已修好。** 不可据此定性为确定的 26H2/Python 冲突，也不在本机恢复压力测试。

下一步是准备新的独立 Windows M1 环境/执行适配器，先 short prefix，再研究 65/66/92 的完整 selected prefix 重放，最后 fresh development campaign。不能直接绕旧 environment guard 或用 20 个 smoke PASS 代替完整 M1/历史/因果性成绩。

当前保持：PREFIX=NOT_RUN；CAMPAIGN=NOT_RUN；FORMAL_C3_C=NOT_RUN；PRODUCTION=NO；PHASE6=NO；FULL_P_HISTORY_VALIDATION_AVAILABLE=NO；REAL_HARDWARE=CALIBRATION_REQUIRED。
