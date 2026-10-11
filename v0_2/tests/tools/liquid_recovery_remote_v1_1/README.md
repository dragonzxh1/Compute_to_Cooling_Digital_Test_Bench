# Remote recovery v1.1：仅日志数值适配

首轮 run 38166700254 的环境/Job/热节点 6/6/水力运输 CDU 11/11 均 PASS。
PHYSICAL_PROBE tick=0 的物理步已返回，写 LEDGER_READ 时 strict primitive logger
拒绝 NumPy 数值标量；raw traceback、job child exit=1、cleanup=true/active=0 保存。
SHORT_FEEDBACK 被首错停止阻断，NOT_RUN；整轮不是 PASS，没有主机硬挂证据。

源码中 np.linalg.solve -> new_t -> HX -> ledger residual 会保留 NumPy scalar。
v1.1 只在新 diagnostic adapter 的日志/JSON 出口显式转换已知 numpy.float32/float64、
int32/int64、bool_，拒绝 nonfinite/array/complex/string/未知对象，不调用任意对象 hooks。
模型对象、原 metrics 门禁、输入、expectations、v1 logger 与其 source inventory 不改。
旧 v1 delivery/manifest/bundle 和 failed execution 保留。执行前增加 11 项适配回归；
整个六 stage 新鲜重跑，不借前轮 17 个 PASS，仍不跑 prefix/campaign/formal。

source_bundle.zip 与 v1 完全相同；新 adapter 每个 source 都单独 hash-bound。
新环境在每次 fresh runner 独立登记，前后身份一致。并不证明原开发机恢复稳定。
