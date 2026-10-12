# M1 远端短 prefix pilot：通过，尚非全量开发完成

## 本轮新鲜执行

[GitHub run 38201224984](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38201224984)
使用 source commit `c3db1418a1b64dc8fd2842b9e5f93d6054da1d09`，独立 GitHub hosted
Windows Server 2022 / Python 3.11.9。本机没有启动 Python 测试。

| 验证范围 | 本轮结果 |
| --- | --- |
| 10 个独立阶段及实际 Python Job 归属 | 10/10 PASS；退出码 0，清理完成、存活进程 0 |
| 输入完整性 | 101 descriptors 的 raw/canonical 校验通过；23 ITQ cases / 51 variants 仅为输入定义校验 |
| 基础检查 | 27 unit tests PASS；9 个核心文件与冻结 v014.1 exact bytes 相同；18 CMP self-checks PASS |
| ST-01 行为 | fresh reference、split、两个原规定 snapshots/repeats PASS；全部 phase records / 56 fields 精确比较 |
| ST-01 因果 prefix | selected = [1,2,3]，各自独立 child 从 t0 重放，完整覆盖并全部 PASS |

下载后核对 40 份 raw stdout/stderr/verifier receipt 的 hash，以及 101 份 materialized
input raw 回读；环境身份在本轮执行前后相同。结果不是只依据 Actions 绿色状态推断，
没有拼接历史 PASS。阶段证据见
[`pilot_result_20261012.json`](v0_2/tests/tools/m1_remote_control_v1/pilot_result_20261012.json)。

## 证据身份

- Execution manifest RAW：`8d9e75762a4f2fff14f46fd3ec708218b1fe3075c0d16df1130ec25dc4571b58`
- Batch complete RAW：`0e884ec65d2b89f77ed3cf1b2f2cc0c9b63fd2f3503583d56c0afbc19b9bfa5d`
- Environment registration RAW：`09d6aefdb09c37295888e52c0cb183ed237de54b3ac8c7bb921055ee59ba6452`
- Selected inventory RAW：`24de9a11b38c2382e17da4300563ab3f0f5c0264e4c1ebe00e57e539c8c04a21`

原 run artifacts 保存在 GitHub（保留期 7 天）及本地 worktree 的
`artifacts/m1-remote-results/run-38201224984/`。本报告与结果摘要提交 Git；不把大型原日志
或本机临时文件混入源码提交。交付的 v1 manifest/source bytes 保持原样。

## 结论与下一步

`M1_FULL_INPUT_PREPARATION_AND_SHORT_PREFIX_PILOT_PASS_NOT_FULL_CAMPAIGN`。

大白话：完整考试材料已搬到独立机器，短题和判卷、日志、进程限制都跑通了。
这不等于 101 个案例都考过，也不等于本机死机原因已查明。

下一步建立新版本的长案例执行 adapter，针对 indices 65、66、92 重新生成 reference、
selected inventory、split/repeats，然后按确定性分片执行全部 selected prefixes。
每个 prefix 必须独立从 t0 重放；不能丢 selected、续算半条 prefix 或放宽比较。
本轮未运行长 prefix、完整 development campaign 或正式 qualification。

M1 full-scope readiness 未提升。PF06 来源扩展、历史 async P1 缺口继续显式；
T09 = IMPLEMENTATION_HOLD；FULL_P_HISTORY_VALIDATION_AVAILABLE = NO；
REAL_HARDWARE = CALIBRATION_REQUIRED。Production port / Phase 6 未开始。
