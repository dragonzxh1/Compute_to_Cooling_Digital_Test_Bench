# Build005 原 Startup 新鲜执行证据

执行：[run38269665488](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38269665488)，
source `9b487ce88143b5bd8f6f537af9f7b2629fa4e27f`。本报告为后续文档提交，不改变执行源码身份。

50 个原 Startup nodes 全部 fresh 执行。下载原始 artifacts 后做纯文件独立回读：
原 pytest 为 **49 pass / 1 fail**，不得改写为 50/50。
唯一失败精确对应冻结 node
`test_startup_demand_with_suspicion_suspends_then_reintroduces` 的 line144
`startup_demand_suspended` assertion、AssertionError、原 AST 和
`LEGACY_STATE_C_STARTUP_SUSPENDED_TRUE_REPRESENTATION`。
原测试文件身份：`6c2e67d2a9f75e5a8f46b0cce1f1741b6ec6ed34bc1323b02779862fa1293f08`。

核验记录：50 节点、150 setup/call/teardown 报告；无缺节点、skip、xfail、collection error，
setup/teardown 全部 passed；200 个附属报告文件的 bytes/RAW hash 回读一致。
原 pytest fail/exit1 保存在 node_result 中；受控 worker 在精确匹配已批准 legacy identity 后
返回执行 acceptance PASS，二者不是同一成绩。

独立核验 50 native batches、150 native stages、600 stdout/stderr/verifier raw captures，
actual Python PID/Job membership、CPU2500、1024/2048 MiB、EXITED child0、cleanup complete /
active-after-cleanup0 均有效。全部模型执行在 GitHub hosted Windows，不在本机。

5 个节点有 legacy/quarantine domain events。它们的历史测试成绩不等于输入因果 PASS；
历史异步 issue proof 缺口继续保留。`VERSIONED_STARTUP_COMPATIBILITY = PENDING_FINAL_AGGREGATE`，
须由本轮 U/v2、全部 prefix、schema 与 final 证据统一完成，不能借旧成绩。
`FULL_DEVELOPMENT_CAMPAIGN = INCOMPLETE`；prefix 仍在执行，非 formal qualification / production。

原始下载证据置于仓库外 `D:/Github/c2c-m1-remote-evidence/run-38269665488/startup/`；
回读记录 `startup-original-readback.json`、`startup-native-readback.json` 同目录上一级。
此路径选择只用于避免大份验证数据进入本地 Git 工作树；不证明 Git 损坏或整机硬挂的原因。
原仓库中的旧证据和损坏对象备份未移动、未删除。
