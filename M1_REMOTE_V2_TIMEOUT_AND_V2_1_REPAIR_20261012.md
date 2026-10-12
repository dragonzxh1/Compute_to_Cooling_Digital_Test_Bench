# M1 v2 停止与 v2.1 执行分组修复

## v2 结果：INVALID，不是候选行为 FAIL

[原 run 38203137214](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38203137214)
在 `CORE_SELF_CHECK` 被 native 120 秒保护终止。
Environment / 101 输入完整性 PASS；27 个基础测试中前 26 个 `ok`，最后的
`test_split_requires_presealed_inventory` 尚未回传完成。三条长案例全部 NOT_RUN。
native = TIMEOUT、cleanup_complete = true、active_after_cleanup = 0。
Python result.json 未生成；这不构成断言 FAIL，也不是远端整机无响应。

下载后 12 份 raw receipts 的 fsync/hash 回读身份匹配。原 STOP、原代码、未完成阶段和日志
全部保留；证据摘要见 `v0_2/tests/tools/m1_remote_control_v2/invalid_result_20261012.json`。
STOP RAW `59775a7492fb07245735473307c738c81a40eec3ef8ccca40049264b99676a1c`。

## 原因与修复边界

使用 `/investigate` 的证据→调用链→最小修复流程：旧 pilot 原 27 tests 耗时 107.469 秒，
日志区间 116.265 秒，接近包含启动/归属证明的 120 秒 child 总预算。本轮最后日志仍在
正常 reference/observe 返回，无断言错误；native 记录明确 TIMEOUT。
确认的是**整个基础套件合在一个限速 child 的预算边界问题**；不能据此解释本机旧硬挂，
也不能断定 Windows/Python 冲突或只由 fsync 引起。

另一个已定位的错误：runner 先读可选 Python result，再检查 native outcome，导致 timeout
被 `ItemNotFoundException` 遮住。v2.1 先保存 native_failure_audit 再处理 Python result。

v2.1 是独立新 execution，不重跑/回写原失败 run。数学 engine v2 原 bytes 保持原样，
原测试 body / 断言不变：分成 12 projection、3 state copy、8 infrastructure、4 protocol
四个 child，总数仍为 27；schema / 九核心 identity 另一个 child。
增加 test-level BEGIN/END；不省测试，不放宽 expected，不提高 CPU / memory / 120 秒 child。

## 身份与新鲜验证计划

原 v2 engine/source manifest：
`e24f4230bfead0c3307d78abf1dfb7ba589fc4ef0c008b37796c8b55c0c25594`，由原 engine guard 继续真实验证。
新 external control manifest：
`0767acfeda3af76c25f431cf97eb7e313bee4aea73182c66d934221c96493960`。
新 runner：`174f2d8cf415fcb5c5da4bbb71b20a6d8bb0f81c4309f8a1597e356132d2f511`。
日志/环境记录分别标明两种身份；external coordinator 每阶段额外检查新控制源，不绕原 guard。

静态核验：PS parse、40 个已交付 v2 bindings 未变、原测试定义 12+3+8+4=27、20 个阶段清单、
native outcome 检查顺序先于 result.json，全部通过。本机未启动 Python/native/candidate。
新远端运行必须从头开始重做基础、负向、三长轨迹、原 repeats 和 terminal prefixes；
本文件是执行前修复记录，实际 PASS/FAIL 另存，不在这里预判。

大白话：不是液冷算法被证明错了，而是把一大包检查塞进同一个“慢速且限时”的进程太紧。
把同一份检查分几包执行，安全上限不变；同时让超时原因直接显示出来。

长 selected-prefix 全覆盖、全 campaign、正式资格测试仍未完成；硬件 CALIBRATION_REQUIRED，
full P history 不可用，T09 IMPLEMENTATION_HOLD；production / Phase 6 不开始。
