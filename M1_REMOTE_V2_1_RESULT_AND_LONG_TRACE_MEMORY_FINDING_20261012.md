# M1 v2.1：基础检查修复通过，长轨迹因 MemoryError 停止

## 本轮新鲜执行

[Run 38203955762](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38203955762)
使用 source `5ba7d238ee1c7dbe5e513714a3323f922ce1ec3f`；只在独立 GitHub hosted Windows 执行。
本机未启动 Python / native / 压力任务。

| 范围 | 本轮结果 |
| --- | --- |
| 环境、101 输入、九核心 byte identity | PASS |
| 原 27 基础测试 | 12+3+8+4，全部 fresh PASS，原 body / assertions 未改 |
| 原比较器负向/selfchecks | 18/18 fresh PASS |
| index 65 / ITQ-49 的 161 点 reference | INCOMPLETE：tick index 116、仿真 23.2 秒出现 MemoryError |
| index 66/92、long prefix、full campaign | NOT_RUN，不继承旧成绩 |

基础单进程预算修复已实跑验证。长轨迹遇到的是新的内存错误，不是该修复失败，
也不是已确认 tracking behavioral FAIL。整体仍为 INVALID / INCOMPLETE，不能报 M1 complete。

## 精确失败位置与证据

Traceback：worker.REFERENCE → observer.reference_rows → pre_oracle.derive → observer.observe
→ codec.encode，在 list/dict 历史数据 typed encoding 中抛 MemoryError。
tick 115 已完成；tick 116 的 before observation 已完成，derived PRE observation 未完成。
没有温度/压力越阈值断言失败，没有最终 reference / comparison / prefix 判定。

native = EXITED、Python exit 1、cleanup_complete = true、active_after_cleanup = 0；实际 PID 7408
归属目标 Job。不是 TIMEOUT、不是 native crash、不是远端整机无响应。新 native audit 保留了
非零退出，Python error/result 也落盘，没有再被 result.json 缺失遮蔽。

下载后 9 个已启动 child 的 36 份 raw receipts hash 回读匹配，8 个已完成阶段 PASS。
各阶段 source/environment guard 未报告漂移；失败 child 缺正常 after identity，不能声称
完整执行前后环境认证完成。逐阶段 hashes / 状态见
`v0_2/tests/tools/m1_remote_control_v2_1/invalid_result_20261012.json`。
STOP RAW `173244d31784dd8146224758578eab74325b877872fec3776f37d167fcdf9b4c`。

## 事实与推断分开

已确认：在 process 256 MiB / Job 512 MiB 的受控环境，观察数据编码发生分配失败。
未采集 peak commit，不能给出精确触限 MiB 的测量结论。

代码结构显示：56 字段包含不断增长的 records、response_history 和 event histories。
每个采样点完整编码 before / derived PRE core / after，frames 又保留所有旧编码结果。
单帧历史 O(n)，累计完整帧至少 O(n²)，不是仅 161 个标量；derive 还保留独立旧义务副本，
不能删除它省内存。这是明确的资源扩展风险，下一步应修证据存储层，不是 retune controller。

不能由此倒推旧本机整机硬挂的根因，也不能归咎于 Windows 26H2 / Python 冲突。
当前隔离将错误限制成可记录的 Python 失败和干净退出。

## 下一版边界

新版本实现流式 trace 存储与有界读取：每帧完成后 durable 写出、hash，保留全部 56 字段、
全部历史和 PRE/Safety/PLC/POST。比较与 prefix 必须精确检查全部内容；reader 不能再把全部
磁盘 frames 装回一个大列表。原 oracle 前缀索引与独立 retained-fault ledger 必须保留。
增加 coarse external commit / working-set 测量，不给 Python 加 FFI/watchdog。

不能截断 histories、只比终态、减少 selected、修改期望或提高内存上限。先用 unchanged
小轨迹证明 streaming round-trip 与原表示完整相等，再 fresh 跑原 27/18、三长轨迹和全部
selected prefixes。原 v1/v2/v2.1 和失败证据保留，不拼不同轮成绩。

大白话：每走一步，就把“从开始到现在的整本记录”复制几份，副本一直堆在内存。
下一步逐页写磁盘、按需逐页读，检查内容一项不减，不靠加大内存掩盖问题。

T09 IMPLEMENTATION_HOLD；full P history 不可用；硬件 CALIBRATION_REQUIRED。
完整 development campaign / 正式资格 / production / Phase 6 未完成或未开始。
