# GitHub 专用资源与长轨迹重跑

新 remote-only 原生执行器 CPU=25%，严格内存 256/512 MiB，campaign=1024/2048 MiB，
采用原项目已有的 480 秒 development wall budget。模型采样/延迟/故障计时、profile、
Contract15A、九核心数学文件、原测试/期望不变。旧本机 C# / binary / guard 全部保持原样。

独立 GitHub run [38259509212](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38259509212)
source `e5d3f031f11d10f79d0df619509ff1741e155138`：39/39 stages PASS。
新 native compiler/ABI selftest、actual Python PID Job membership、CPU2500 readback、256/512 MiB
readback、child exit0、cleanup complete/active0 均实际核验。下载后 156 raw receipt hashes 匹配。
外部采样最大 private commit `72318976` bytes（约 69 MiB），这是采样最大值，不是精确峰值。

本轮 fresh 原 27 units / 18 CMP checks / 四组 old-vs-stream 完整字节与 oracle context 等价检查
PASS；65/66/92 三长轨迹、原 2/11 repeats、完整 56 fields/all phase comparison，以及最长
161/161/51 prefixes PASS。不是全部 selected prefixes 或 full campaign PASS。
batch complete RAW `e83620b060b8f384624ed8c133bed06c70677c9bce11755199b1f903fd63bb1d`。

build003 单独启动完整 fresh campaign：所有 reference → C/S reference gate → 所有 selected
inventories → 所有 split/repeats → hash-bound prefix plan → 每个 selected prefix → 原 Startup
50 bodies（分节点执行、精确合并、原 49/50 与 versioned compatibility 分开）→ schema / PF / 总验收。
只允许在完整 prefix 之间按资源预算 yield，公开 remaining set；最终必须 exact inventory equality。
全部 native/source/env/raw evidence 另做完整性审核。不借本轮 pilot 的任何成绩作为 full campaign 分数。

大白话：云端不再像之前被限速到 1%；内存爆涨通过完整证据逐帧写盘解决，不删记录。
三道长题及最长重放已经实际通过，现在重考整套材料。所有执行仍在 GitHub，不启动本机 Python。

M1 engineering completion 不等于 frozen full-scope readiness。PF06 original gap、补充源待审、
historical async P1 incompleteness、T09 IMPLEMENTATION_HOLD、full P history unavailable 和
hardware CALIBRATION_REQUIRED 保留；不开始正式 C3-C、production、Phase 6 或真实硬件控制。
