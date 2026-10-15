# C3-C v5 执行包集成（未冻结）

v4 run38675166533因FINAL超时而INVALID，原件不修改、不追补PASS。v5是新的执行基础设施版本，candidate仍为SHA-256 `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`。

新namespace为 `v0_2/tests/tools/m1_c3c_v5/`。从冻结v4机械派生入口、authority、runner、worker及workflow，再只将FINAL的包及环境锁加载提到单次审计循环外，增加11组BEGIN/END、逐batch/case进度。没有全局authority缓存；所有逐份Job/raw/schema/run/env判断保留，执行前后完整source guard保留，FINAL自身的退出后batch仍须独立delivery readback。

开发验收计划：原53项authority/assembly/environment合成测试，加4项FINAL静态回归；另执行有限PowerShell控制平面/101输入/50Startup矩阵/原native家族下载覆盖检查。只在GitHub实际Job中执行，不在本机运行Python/native/model，不启动formal或candidate行为。原969静态stage+FINAL、101 descriptors/3216 rows/499 snapshots和动态prefix selector不改。

新draft复制四项已登记规范的原始字节，不重新解释SEM01/SEM02/PF06，也不自行标记批准。旧v4的796项非router来源必须逐项保持，唯一新版本router在draft中明确记录旧/新SHA并重新绑定。旧固定ref、旧包、历史证据和所有冻结candidate/contract/profile/Safety不动。

包自检通过仍不等于正式资格。还需形成确切最终包、审签页和执行源码身份，单独获得新包冻结及fresh formal授权。旧v4的授权不能授权v5。生产、硬件及Phase6不授权。

大白话：把已经验证的“少重复查清单”修复接进真正的考试程序，再验证防错闸门；现在是在装配和检查新考场，不是擅自开考。

## 包级自检结果

[run38759498586](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38759498586) 在source `c5d9aa550d95357d8314a49d7a64017c229339a3` 上完成57/57 Python合成检查及62/62 PowerShell控制平面检查。包括新增FINAL四项回归：逐阶段require断言相同、package/lock只在循环外加载一次、最终require/classify/admit保持、11组日志边界与环境锁/schema/stop规则原字节保持。流程矩阵仍覆盖全部101输入和50个原Startup节点，完整native家族下载门禁保留。

本轮draft RAW为 `b7fc854301f12dec49496efdfc356888a755a8b22f779e872ae73dd0f564c41e`，assembly control为 `8f7472bc3bc63fd5c8f87f19e4908f72d93774ab693139ff0b5d74e9f4e24059`，832项来源绑定。状态仍 `PREPARATION_NOT_FINALIZED`；未生成用户批准或formal execution授权。

官方artifact11984019117（8303字节）SHA-256为 `6323d9994e8c0276d73850c296d618e49e6875f70a6c2c583930a623a2671ec9`。已独立核对16项ZIP文件、4份raw及stderr的57 tests/OK；实际PID7080在CPU25%、256/512MiB Job中，cleanup complete/active0，批准镜像20261012.333.1、前后环境一致。没有candidate导入或行为执行。原件和机器摘要在 `artifacts/m1-c3c-v5-assembly-evidence/run-38759498586/`。

还须完成最终交付包/审签页/源码闭包绑定及最终包只读核验。这些自检不是新的fresh完整candidate campaign，也不是正式C3-C或上线资格；原v4 INVALID、原Startup49/50和所有范围限制不变。
