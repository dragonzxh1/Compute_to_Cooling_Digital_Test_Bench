# M1 远端长轨迹 / 最长 prefix 开发验证 v2

## 执行前范围

独立 GitHub hosted Windows，16 个阶段：环境、全部 101 输入完整性、原基础检查和负向检查，
然后 descriptor 65 / 66 / 92 各自 fresh REFERENCE → SELECT → SPLIT/repeats → 最长 prefix。
ITQ-49/50 各 161 rows，S-history/S4 为 51 rows；S4 保留原 eleven snapshots。
ITQ-49/50 原描述符输入 hash 相同，但保持两份案例身份，分别重新执行。

这不是 full campaign，不是完整 selected-prefix coverage，更不是正式资格测试。
先验证此前未完成的长案例及 longest prefix，再从新鲜证据机械生成所有 selected 的分片清单。
每条 prefix 均独立 child 从 t0 重放；所有 56 字段与完整 phase records 精确比较。

## 不变与新版本

v1 已交付身份不改；v2 使用新 namespace。九个数学核心文件与冻结 v014.1 exact bytes 一致；
qualifier、合同、profile、ITQ、Production Safety、控制器和 plant 均不变。
新增 host/执行/证据协调器，不修改响应阈值、故障时钟或预期。

68 项本地静态/合成检查 PASS，含 PS parse、九核心 identity、列表缺项/重序/重复/类型错误拒绝、
实际 Python 归属及退出清理 guard 保留、41 项 v1 source/workflow hashes 未变。
本地验证未启动 Python、native helper 或 candidate；Python syntax/import 及行为检查在远端执行。

Execution manifest RAW：`e24f4230bfead0c3307d78abf1dfb7ba589fc4ef0c008b37796c8b55c0c25594`。
Runner RAW：`1cc5818f1f16f688ad905b2157edc4b3e76ba7c47cb7e0428e408f419156fefa`。
40 新 source/workflow bindings，继承原 bundle 601 exact-byte entries。

## 安全执行与证据

原 1% CPU / 256+512 MiB / 120 s child / active limit 4 / kill-on-close 均不改。
外部 verifier 在 release 前核对实际 Python Job；每阶段前后核验 source/env，raw fsync/hash/readback
先于 acceptance。出现 timeout、资源、来源、测量、比较或证据错误均停止；不在同一轮改代码重跑。
原短 prefix 本轮耗时只用来评估执行规模，不借其 PASS 作为新案例结果。

全部 16 stages PASS 后才生成 fresh selected plan：inputs + reference records 重建 exact
mandatory/progress/confirmed union，原 ITQ conditional / support all-prefix policy 不删项，
全 base artifacts raw hash 绑定，再机械分为每片最多 6 条。分片为新执行预算，不是物理校准参数。
当前 workflow 只运行 BASE，不执行这些分片；部分测试不能报成 aggregate complete PASS。

大白话：先完整跑三道长题和它们最长的重放，再决定分几批跑剩下的重放。
不会继续用本机冒险，也不会拿三道长题通过冒充整套考试通过。

M1 full-scope readiness 未提升；PF06 / 历史 async P1 缺口仍显式；T09 IMPLEMENTATION_HOLD；
FULL_P_HISTORY_VALIDATION_AVAILABLE = NO；硬件 CALIBRATION_REQUIRED。
Formal C3-C / production / Phase 6 均未开始。实际结果另存新文件，不改本执行前报告。
