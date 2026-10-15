# v5：FINAL剩余聚合开发复现

只用原v4官方ZIP测试最终聚合程序，不重跑candidate，不重判原v4，不是新的fresh开发campaign或正式C3-C。旧run38675166533始终INVALID。正式v5包尚未批准。

新开发worker绑定同一2011635439字节官方原件，先重新执行完整native回读，再按原字节恢复39199项case/Startup输入（共6671458232字节）。只在GitHub实际验证的Python Job中执行，CPU25%、1024/2048MiB、480秒；本机不运行Python/native/model。

冻结case/prefix/repeat、C/S、原Startup guard、SEM02、PF06和schema判据保留。版本化Startup及PF聚合包装函数只把派生输出改写到新开发目录；在运行时以AST比较确认除输出目标以外函数体相同。结束后逐项重新哈希全部输入，确认未被聚合器修改。旧官方ZIP保持原样。

分别持久化native审计、输入恢复、101案例元数据、C/S reference/split、Startup、PF、eligibility、输入schema、派生schema、登记比较和输入后检查的BEGIN/END/FAIL与耗时。数据检查函数可能导入历史模型的类定义，但不调用模型构造、replay或update。

只有全部开发检查完成才输出 `AGGREGATION_DEVELOPMENT_REPLAY_COMPLETE`，不生成正式qualification结果。原Startup49/50与versioned compatibility分开，SEM02五项strict P1 B/C仍INCOMPLETE，PF06原范围仍INCOMPLETE、补充按独立登记检查；T09 HOLD、完整P历史不可用、硬件CALIBRATION_REQUIRED、生产及Phase6均未授权。

大白话：把旧答卷复制成只读输入，测试“最后汇总判卷”能否做完。输出写到新目录，既不篡改旧答卷，也不把旧考试变成通过。

## 开发复现完成及独立核验

[run38756839568](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38756839568) 使用source `3937ec6f6a345922a0d61df0bd84fef770b64051`，control RAW为 `672a039f93bb71f9fde51cf254f5ad97320e79d35d681997fe6e46ba38a40a9d`。13个聚合阶段全部完成，合计墙钟137.92492秒，仍在原480秒预算内；其中恢复输入51.93秒、输入schema53.84秒、PF矩阵6.58秒、输入后哈希9.53秒。native部分为ZIP访问，不把它宣称为原磁盘FINAL的同机提速倍数。

101案例元数据、2281 selected-prefix、499快照检查完成；reference/split的C各11/11、S各17/17。原Startup仍49/50，versioned compatibility单独PASS。输入schema覆盖各101份stage_result/prefix_inventory/prefix_result，派生schema覆盖PF矩阵和eligibility。这里验证的是旧答卷的聚合逻辑，不是本轮新模型考试。

P15在原登记descriptor100：归档的9项检查、comparison和repeat均为PASS，已独立核对原ZIP元数据。这不属于新fresh P15执行，更不能恢复缺失的完整P历史。

官方输出artifact11984031722（2814211字节）的SHA-256为 `42a03d8d2ff07b8dbd8599de3f2f4e64dc7d8f21deb565d74134b4f0ac82c36a`。153项输出ZIP文件及4份raw逐项核验，实际PID7940的1024/2048MiB Job、CPU2500、cleanup和前后环境已复核；镜像20261012.333.1。13组BEGIN/END、无FAIL，101个case进度完整。

独立PowerShell文件回读又把39199项输入的名称、长度、SHA逐一与原v4官方ZIP比对，共6671458232字节，全部一致、无缺项重复；manifest SHA为 `7cf32204667e034e79229bdedfb6c1edb6c85e1ef4da43b0b0bce635c9252d02`。SEM02的5个精确node/input hashes及零PLC/Safety伪造记录、原Startup50节点/150报告/唯一legacy failure身份、PF06 row4/800ms及两个原negative controls另行核对通过。

原始ZIP、raw、派生输出和机器摘要保存在 `artifacts/m1-c3c-v5-aggregate-evidence/run-38756839568/`。聚合器只导入历史数据检查所需的类定义，没有调用candidate行为；输入后检查也确认旧输入字节未改。

当前结论仅为 `AGGREGATION_DEVELOPMENT_REPLAY_COMPLETE`。下一步把已验证的优化集成到新的实际C3-C执行包，做包级开发验证与身份自检，再提交确切包审签；未把旧v4改为PASS，没有沿用v4授权开新考试。SEM02严格P1缺口、PF06原INCOMPLETE、任意POST异常原子性NOT_PROVEN、T09 HOLD、完整P历史不可用和硬件校准限制不变。
