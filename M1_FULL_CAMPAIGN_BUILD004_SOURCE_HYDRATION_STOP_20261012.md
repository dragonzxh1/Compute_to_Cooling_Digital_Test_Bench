# Build004：plan 缺少冻结来源文件，独立重跑

Run [38262581261](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38262581261)，source `73b0daa876f3d4ad107c75332b78d7c476f54be9`。
34 个前置 jobs 成功；plan 唯一失败于 campaign_plan.ps1:69，未找到冻结的
`phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json`。
尚未执行 prefixes、Startup、schema 或 final，不宣称完整 campaign PASS。

根因：每台 GitHub VM 独立 checkout；run.ps1 会解压冻结 source bundle，
但纯 PowerShell plan 没有调用 run.ps1，公共 runtime action 也未恢复 bundle。
本轮记为 `INVALID_SOURCE_HYDRATION_IN_PLAN`，不是 candidate behavioral FAIL。
原 run、日志、已上传 artifacts 与 commit 保留，不将其成绩拼接到下一轮。

Build005 仅新增公共启动入口的哈希绑定来源恢复。它先核验 manifest、adapter、
bundle、完整 ZIP inventory、每个 entry hash 与路径安全，再恢复并回读核验全部文件。
本地只做隔离目录中的纯文件测试，不执行 Python、native 或模型。
候选、冻结 ITQ、Startup、Contract15A、profile、Safety 与模型时间规则不变。
新轮从 prepare 开始重新执行全 DAG；formal qualification / production / Phase 6 不在范围内。

本地验证：verify_snapshot.ps1 六项纯文件回归全部通过；601 entries 恢复/回读与
重复恢复一致；错误 manifest、entry hash、inventory、路径越界均在写入前拒绝。
原工作区 655 个 protected source bindings 漂移数为 0；git diff --check 通过。
Build005 execution manifest raw SHA-256：
`6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93`。
原 runner raw SHA-256 仍为
`d0966ceee64f61df8b150fc3f50eb58b6c6b629e4ad0f6ec978b1c4c2e3e94f7`。
