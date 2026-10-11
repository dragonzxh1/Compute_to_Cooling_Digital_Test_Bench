# 恢复基线已合并 main，并完成新鲜复验（2026-10-12）

## 结论

用户本轮批准的第 1、2 步已完成：恢复基线合并到 GitHub main；合并后独立 Windows 小案例重新运行并通过。没有准备/执行完整 M1、长 prefix 或 campaign。

大白话：已跑通的恢复方案现在收进主线，而且主线自己重新考过一次；后面的 M1 可以从这个起点继续，但不能把这次小考试说成完整测试通过。

## 合并身份与范围

- Tested main merge commit：`57dba0b49ca4ee4d4b5aeaa1c26a4cd56e2fb8b4`。
- Parents：恢复交付 `13291b0b5e0b52417211e9adf89a47aca0fc11db` + 原 main `0f97c7a4081145bfa6d8f2a234be89b5a4021be8`。
- 唯一 add/add 冲突：`.github/workflows/liquid-cooling-recovery.yml`；保留已测试的 v1.1 两处 runner 路径。最终 workflow 和所有七项 adapter bindings 的 raw hash 与原已验证版本一致，合并文件树与之前交付 HEAD 完全相同。
- 未修改原 `.github/workflows/ci.yml`、旧失败、candidate、fixture、profile、Safety 或判据；未更新 DSX。合并保留父提交历史，不 squash/force-push，不修改旧 evidence。GitHub CLI 更新 main 使用 fast-forward 检查与 force=false。
- 合并与后续证据说明提交使用 `[skip ci]`，只有明确手动 dispatch 的 recovery smoke 执行；旧 broad 全量 CI 未触发，旧红色历史不删、不改判。

## main 独立新鲜成绩

[Main run 38168292744](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38168292744)，head branch=main，head SHA=上面的 merge commit。

| 检查 | 本轮结果 |
| --- | --- |
| Environment / 实际 Python Job / source/deps / 清理 | PASS |
| 日志数值适配回归 | 11/11 PASS |
| 原热节点测试 | 6/6 PASS |
| 原水力/运输/CDU/物理回路测试 | 11/11 PASS |
| 5 s / 50 step 物理账本、日志、unlogged 等价性 | PASS |
| 原短反馈测试 | 3/3 PASS |

原 pytest 合计 20/20，本次重新执行，不继承分支成绩。

## 下载后的权威证据核验

六个 stages 均 PASS，batch COMPLETE，没有 STOP；六个 stage raw SHA 与 receipts 匹配。六个实际 Python 专属 Job proofs 均有效，CPU rate=100/10000、process/job=256/512 MiB；exit=0、cleanup=true、active_after_cleanup=0。

24 个 raw stdout/stderr/验证器 receipts 本地下载回读匹配；本轮 source 与 environment 前后身份相同。物理日志 208 条、50 对 PHYSICAL_STEP BEGIN/END、tick 0..49、时间完整 0..5e9 ns，无 ERROR。原质量和能量门禁 PASS；未改变数值容差。

- Machine result：`v0_2/tests/tools/liquid_recovery_remote_v1_1/main_merge_smoke_result_20261012.json`。
- Batch COMPLETE RAW：`494ef48bc438795ec56640b169ad3a12db41b1032f8718a2746ccb8c6138c273`。
- Physical progress RAW：`2f0b8d7b90e52ff69fe8bcf12595bb574daed10bbe417d17ef171907f3101fbf`。
- Environment registration RAW：`de9a654aecf9b940cdcb17749b7045df894e7a48a0a093fa48115e9e6b65d129`。
- Adapter manifest RAW：`a8719f01574816bbd09f9553284a46b973c11f6c434faf95b45e98564a8ab42f`；原 source inventory RAW：`f1cdfa0c40945b6315baff794cf0ef2cd4d4afb3cc166f95655de2f2f74451e0`。

后续提交仅新增本报告、machine result 和 README 状态，不改变已测试代码或重新标注其 SHA。

## 本机保护与下一步

原开发目录 D:/Github/Compute_to_Cooling_Digital_Test_Bench 的 tracked 文件未修改，655 个旧保护源 hash 复核无漂移。本机无 Python、native pressure、VM 安装或系统设置变更。

GitHub main 已更新；原本地开发目录仍保持原 checkout，以保护大量未跟踪文件与冻结 bytes，**本轮没有在该目录直接 git pull 覆盖文件**。独立 worktree 与已合并基线一致。未来同步原目录应先审计 untracked 路径碰撞，不用强制覆盖。

下一阶段再从新的 main 准备完整 M1 源码、输入/判据/历史引用清单与独立 Windows 环境适配。不能把旧环境 guard 改成无条件通过；先短 prefix，再 65/66/92 的完整 selected prefix/repeats，最后 fresh development campaign，明确保留 PF06/P1/T09 等作用域缺口。

当前边界不变：完整 M1 准备/执行尚未完成；PREFIX=NOT_RUN；CAMPAIGN=NOT_RUN；FORMAL_C3_C=NOT_RUN；PRODUCTION=NO；PHASE6=NO；FULL_P_HISTORY_VALIDATION_AVAILABLE=NO；REAL_HARDWARE=CALIBRATION_REQUIRED。独立小案例通过不能证明原开发机死机根因已确认或本机已修好；本机 workload HOLD 保持。
