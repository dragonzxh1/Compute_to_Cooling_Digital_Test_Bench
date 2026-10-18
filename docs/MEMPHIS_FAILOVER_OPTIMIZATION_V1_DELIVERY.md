# 孟菲斯故障切换因果与受控优化 v1 使用说明

结果：28个受控阶段（26个动态场景、17项拒绝/正例见证及FINAL）完成。数值/软件执行有效，不批准客户工程设计、采购或硬件。

- [中文设计决定报告](../artifacts/memphis-failover-optimization-v1-delivery/DESIGN_DECISION_REPORT_ZH.md)：先看“先给设计决定”和“四项不能省略的限定”。
- [图表与事件报告](../artifacts/memphis-failover-optimization-v1-delivery/engineering_report.html)：下载后离线浏览器打开；展开各场景查看温度、源/负载流量、冷库存和实际控制事件。原始诊断默认折叠，不是实时控制面板。
- [GitHub实际开发运行](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39129984525)：只读原记录，不重跑failed jobs或重复启动。
- [预登记参数](../v0_2/tests/tools/memphis_failover_optimization_v1/registration.json)：startup_s=假设启动等待；valve_s=行程；header_volume_m3=管热容；standby_line_precooled=初始冷管假设；strategy=测量驱动项目规划策略；layers/dt_s=空间/时间离散。均不是OEM能力证明。

确切执行源码a07e5fba7d78f34ab907ce209399068f9c92c760，manifest715d8d9cd7a5d99ddccff2373754ee6f32e3084e48e3deffecf8b91702421bef。原V2、冻结M1及00/01均未改。交付报告v1.1只是对官方数值的范围释义和事件可读性修订，原ZIP及comparisons.json保留原样。

复核工具：artifacts/memphis-failover-optimization-v1/verify_official.ps1；仅下载/流式校验ZIP、SHA256、实际Python Job及退出清理，不执行本机Python或模型。独立核验收据和package_manifest.json位于交付目录。27个计算/拒绝阶段及FINAL共28个实际PID均核验；FINAL自己的退出后cleanup也为0。

下一设计证据是备用管/塔出口温度与ready信号、维持预冷的真实方案与功耗、罐分层/混合试验、OEM泵和换热器性能。不要由20层预冷条件PASS释放采购。预冷跨网格/混合/天气组合、同泵曲线共享/独立回充因果比较、罐单体90秒验收仍INCOMPLETE。

保持：MEMPHIS_ENGINEERING_NOT_APPROVED；硬件CALIBRATION_REQUIRED；无正式C3-C、production、真实控制或Phase6授权。所有仿真阶段只在登记的隔离Windows Job运行；本机不运行Python/native/model/压力负载。
