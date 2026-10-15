# v5：完整原生证据开发回读

这是新版本只读开发验证，不是fresh C3-C，不会给原v4补发资格。旧run38675166533始终为INVALID，candidate及冻结判据不动。

绑定官方final artifact11955188632，ZIP共2011635439字节，SHA-256为`b64e8509e255669328675ab0976eed0e45c6fbef294c4c6280171ff4885e91ad`。读取原始ZIP、不覆盖原件、不构造PLC issue或Safety记录。失败FINAL子树655项单独隔离并核对原停止/超时哈希，不能算PASS。

对其余716完成批次、1969阶段记录执行已验证的“单调用只解析一次包及环境锁”的审计。仍逐项核验原始receipt、actual PID/Job、raw captures、schema、原来源run及其环境，核对969静态阶段覆盖。再流式哈希全部57107个上游native文件，生成持久化逐文件清单。每批次、每1000文件及ZIP大块哈希有持久化进度。

原来源run/context作为明确登记的历史数据参数传入，不改新GitHub运行的环境变量，不冒用旧正式授权；旧授权必须拒绝新开发commit。其余796个旧来源字节保持，唯一另行登记的新router和开发reader用新control绑定。实际reader进程在GitHub隔离Job中执行：CPU25%、1024/2048MiB、480秒，与已批准campaign资源身份一致。

本步骤只覆盖原生证据审计。case/schema/Startup/PF聚合及整个FINAL开发复现尚未因此通过；case成绩不得凭这次历史回读变成fresh正式成绩。只有完成全部开发验证并形成新确切包后才请求新的正式冻结及开考授权。硬件、生产、Phase6均未授权。

大白话：用新程序重新清点旧考试的全部监考凭据，检查能否在预算内做完；不是重考，更不是把旧的未完成考试改成通过。

## 完整native回读结果

[run38754888400](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38754888400) source为 `e2a3e29f64fdf4556d47e9a4940db2fee5020f8f`，control RAW为 `4ef85d4b6e72388032f43470611a6524c0f54f3967bac2a75af3e517e722880a`。716批次、1969阶段记录、7876份raw和969项静态覆盖均满足登记的回读检查；57107文件共671761951字节逐一哈希。失败FINAL的655项原件单独核验，不算PASS。

原始ZIP摘要检查约1.96秒，优化后的ZIP native审计约2.21秒，全native文件哈希约3.12秒，总回读约8.49秒。**ZIP访问与原v4磁盘文件访问不同，不能宣称完整FINAL现在只要2秒或据此给出同机提速倍数。** 本结果证明完整真实native记录可以在预算内检查，但case/Startup/PF/schema聚合仍待开发复现。

官方输出artifact11982513125，2142676字节，SHA-256 `bb15f600450a9e035b7829fed1d30be6a2fc750d9103f02248716c7e13ee531c`。24项ZIP输出、4份raw、实际PID5328的1024/2048MiB Job、cleanup、前后环境及716项批次日志已独立核验。登记镜像20261012.333.1，source/formal授权分离。

另用PowerShell逐项读取**原v4官方ZIP**并与新reader清单比对：57107项名称、长度、SHA全匹配，无缺项、无重复、无将失败FINAL混入。清单SHA为 `15d6e561bc70d3d9accf535858fde31da386de4dde7ea70260bba2f17befb5ae`。原输出及机器摘要在 `artifacts/m1-c3c-v5-readback-evidence/run-38754888400/`。

仍保持v4 INVALID / behavioral NOT_MADE、新正式执行未授权，生产/硬件/Phase6未授权。下一步仅推进剩余FINAL聚合步骤的开发复现。
