# v5：FINAL剩余聚合开发复现

只用原v4官方ZIP测试最终聚合程序，不重跑candidate，不重判原v4，不是新的fresh开发campaign或正式C3-C。旧run38675166533始终INVALID。正式v5包尚未批准。

新开发worker绑定同一2011635439字节官方原件，先重新执行完整native回读，再按原字节恢复39199项case/Startup输入（共6671458232字节）。只在GitHub实际验证的Python Job中执行，CPU25%、1024/2048MiB、480秒；本机不运行Python/native/model。

冻结case/prefix/repeat、C/S、原Startup guard、SEM02、PF06和schema判据保留。版本化Startup及PF聚合包装函数只把派生输出改写到新开发目录；在运行时以AST比较确认除输出目标以外函数体相同。结束后逐项重新哈希全部输入，确认未被聚合器修改。旧官方ZIP保持原样。

分别持久化native审计、输入恢复、101案例元数据、C/S reference/split、Startup、PF、eligibility、输入schema、派生schema、登记比较和输入后检查的BEGIN/END/FAIL与耗时。数据检查函数可能导入历史模型的类定义，但不调用模型构造、replay或update。

只有全部开发检查完成才输出 `AGGREGATION_DEVELOPMENT_REPLAY_COMPLETE`，不生成正式qualification结果。原Startup49/50与versioned compatibility分开，SEM02五项strict P1 B/C仍INCOMPLETE，PF06原范围仍INCOMPLETE、补充按独立登记检查；T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED、生产及Phase6均未授权。

大白话：把旧答卷复制成只读输入，测试“最后汇总判卷”能否做完。输出写到新目录，既不篡改旧答卷，也不把旧考试变成通过。
