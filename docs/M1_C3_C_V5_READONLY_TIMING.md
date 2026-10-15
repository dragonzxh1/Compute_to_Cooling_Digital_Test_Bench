# C3-C v5：只读开发耗时定位

本阶段不是新的 C3-C 正式执行，也不是已修复结论。v4 run38675166533 保持 `INVALID_C3_C_EXECUTION`，不重跑、不改判。

具体假设：v4 `final_gate.py` 在 1969 份阶段记录循环中反复调用 `package()`，每次解析并检查 797 项路径，放大了最终审计耗时。先量化，再决定是否需要单独版本的执行基础设施优化。

新探针在 GitHub hosted Windows 上运行，沿用原依赖及环境身份检查和实际 Python PID/Job 验证；CPU25%、256/512MiB、480秒。它只读取绑定文件，计时一次带调用计数的包校验、10次未插桩包校验和10次环境锁读取/比较。每次开始/结束持久化时间日志。输出按1969次折算的估计，但明确**估计不等于完整 FINAL 复现，也不能证明其他阶段耗时**。

源码仅新增 `v0_2/tests/tools/m1_c3c_v5_profile/` 和现有开发 router 的独立 `readonly_profile_v5` 入口。新 control 用原始 SHA-256 绑定所有探针、参考失败证据和依赖。原 v4 797 项来源中，只有 router 使用单独声明的新开发版本，其余796项字节在执行前后保持不变；固定9012d6d正式源码不变。探针还要求旧正式授权明确拒绝当前新开发commit，不能把原授权挪给新包。

不导入 candidate、不回放输入、不调用 FINAL、不修改模型、合同、fixtures、expectations、profile或Safety，不生成资格结果。正式 v5 包及其执行尚未授权。任一来源/环境/Job/持久化问题立即停止，失败保留。

大白话：先测“监考程序是不是反复查同一张清单查得太慢”，不重新让控制器答题，也不放宽考试要求。

## 独立回读结果：重复校验放大已量化

[只读开发 run38702318462](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38702318462) 的 source 为 `10ae80369bb5a86aa5186b9a6d199a5f780e59b6`，control RAW 为 `a61b0bb77b3a5e00ca333f34586008283c1ede49678e4f376d525c3db4206a24`。官方 artifact11956269889（7788字节）的 SHA-256 为 `6d4a309ff4aae8293eb1bc3d00f318541cc70191e4e391e38c9918b52f09434a`。18项ZIP文件、4项raw capture、23项时间事件已独立逐项回读。

10次未插桩包校验平均0.35139688秒；按1969次投影为691.90046秒，超过480秒。一次插桩校验确有797次路径调用，路径部分占该次总墙钟时间约97.2%。环境锁读取/比较约0.000079～0.000242秒/次，量级明显不同。

实际Python PID6720已在目标Job中验证，CPU2500/flags5、256/512MiB、active4；EXITED/child0、cleanup complete/active0，四份raw哈希一致。环境前后相同，批准镜像20261004.326.1。旧正式授权对新开发source明确拒绝。未导入candidate或执行行为测试。

结论：已测得一个足以使总审计超过预算的重复工作放大点，但不是旧run每个内部步骤的耗时复原。修复方向是在新版本单次审计内只解析/验证一次不可变包及环境锁，逐份证据的Job、raw、schema、身份和环境检查保持。还需对新版本做等价性与损坏证据拒绝测试，不能仅凭本计时宣布FINAL已修复。

原始官方ZIP及raw保存在 `artifacts/m1-c3c-v5-profile-evidence/run-38702318462/`。v4正式INVALID不改判；新正式考试未启动，生产、硬件和Phase6未授权。

## 后续新开发版本：审计检查器等价验证

`m1_c3c_v5_audit/audit.py` 将包及环境锁的加载移到单次审计调用的循环外，不使用跨调用全局缓存。所有逐阶段 require 断言保留，源码字节仍由独立开发 worker 在执行前后验证。并发恶意修改后再恢复文件的通用防护不在本优化声明内，不能把边界检查描述成连续不可变性的数学证明。

另建 GitHub DEVELOPMENT 检查入口：先比较新旧逐阶段断言的 AST，再用明确标记的临时合成检查器输入，验证正例返回值完全相同、3次包校验降为1次；16类独立损坏必须由两版以相同异常拒绝，包括authority、receipt、TIMEOUT、cleanup、PID、CPU/memory、release、raw、schema、fresh run identity、环境漂移。合成记录不是任何实际Python/PLC执行证据，实际探针Job证明单独保留。

这只能验证检查器变更，不能代替完整真实证据回读、完整FINAL开发复现或新的fresh正式考试。只在这些后续步骤完成后才能提交新的确切包供审签；当前不宣称已上线。
