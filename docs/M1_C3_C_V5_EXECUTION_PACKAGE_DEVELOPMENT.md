# C3-C v5 执行包集成（未冻结）

v4 run38675166533因FINAL超时而INVALID，原件不修改、不追补PASS。v5是新的执行基础设施版本，candidate仍为SHA-256 `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`。

新namespace为 `v0_2/tests/tools/m1_c3c_v5/`。从冻结v4机械派生入口、authority、runner、worker及workflow，再只将FINAL的包及环境锁加载提到单次审计循环外，增加11组BEGIN/END、逐batch/case进度。没有全局authority缓存；所有逐份Job/raw/schema/run/env判断保留，执行前后完整source guard保留，FINAL自身的退出后batch仍须独立delivery readback。

开发验收计划：原53项authority/assembly/environment合成测试，加4项FINAL静态回归；另执行有限PowerShell控制平面/101输入/50Startup矩阵/原native家族下载覆盖检查。只在GitHub实际Job中执行，不在本机运行Python/native/model，不启动formal或candidate行为。原969静态stage+FINAL、101 descriptors/3216 rows/499 snapshots和动态prefix selector不改。

新draft复制四项已登记规范的原始字节，不重新解释SEM01/SEM02/PF06，也不自行标记批准。旧v4的796项非router来源必须逐项保持，唯一新版本router在draft中明确记录旧/新SHA并重新绑定。旧固定ref、旧包、历史证据和所有冻结candidate/contract/profile/Safety不动。

包自检通过仍不等于正式资格。还需形成确切最终包、审签页和执行源码身份，单独获得新包冻结及fresh formal授权。旧v4的授权不能授权v5。生产、硬件及Phase6不授权。

大白话：把已经验证的“少重复查清单”修复接进真正的考试程序，再验证防错闸门；现在是在装配和检查新考场，不是擅自开考。
