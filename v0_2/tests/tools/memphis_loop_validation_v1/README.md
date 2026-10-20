# MEMPHIS ORIGINAL TOPOLOGY RECOVERY VALIDATION V1

孟菲斯原拓扑储冷恢复验证；内部模块memphis_loop_validation_v1。

新版本、新分支：`codex/memphis-loop-validation-v1`。仅GitHub隔离Windows runner执行，不在本机运行Python/native/model。

先ASSERTIONS与原T2历史六原始文件精确复现，再原共享回路80/160/0.05s，之后相同输入RC80/160、A支路实际服务，再RC冷量损失、源泵损失及明确W1维修返回后的第二故障。阶段数以registration为准；工程FAIL照实报告，不改客户45°C/330m³/h/90秒/0.5K。

共用源侧补B时不同时供A，A由储冷供负载；回A恢复完成才能下一轮。RC最小性能只能对绑定恢复时限及假设冷源求条件性界限，未确认期限时无唯一选型值。方案C仅在A/B实际失败且有明确缺口后触发，不先验新增第三中性循环。

`registration.json`为输入、时序、假设、任务授权及排除项登记。首次失W1在30s；维修类900s恢复W1、1800s失W2是独立研究场景，不是客户恢复时限或实际维修证据。控制器仅拿显式白名单和已释放17TT/FT/阀位，不读取故障未来或离线挑战。额外RC1MW为假设外部冷源，不借正在运行的W2重复供冷。

当前原拓扑仅恢复源/罐/负荷主路径，完整3用3备CDU接管、绝对压力/NPSH/水锤、实体阀门泄漏、布水器及OEM性能尚不覆盖。登记保留MEMPHIS_ENGINEERING_NOT_APPROVED；RC改变00/01不新增回充泵的约束，未获客户设计变更批准。

本轮新增代码包括独立控制器、物理RC选择阀、实际冷源建冷过程、逐罐FV审计、末态/事前90s挑战；不改冻结M1、旧physics/control、00/01及历史结果。`source_manifest.json`绑定新增、全部旧开发依赖及836个保护来源；ControlledJob/外部VerifyTarget后才导入工作负载。CPU25%/1024+2048MiB/480s逐阶段；精确Python依赖与镜像守卫保持。

远程原始轨迹、PLC/PRE/Safety/POST、数值账本和失败证据全部保存。最终必须独立下载官方ZIP、核验文件hash、源/环境、实际PID和退出cleanup，不能仅凭GitHub绿色判工程通过。
