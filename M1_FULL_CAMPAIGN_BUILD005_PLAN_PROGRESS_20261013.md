# Build005：plan 通过，进入全量 prefix 与原 Startup

执行：[run 38269665488](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38269665488)。
执行源码身份：`9b487ce88143b5bd8f6f537af9f7b2629fa4e27f`，不是本进度文档的后续提交。
Manifest RAW SHA-256：`6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93`。

本轮 fresh prepare、101 reference、C/S reference gate、101 selectors、101 split/repeat/seal
与独立 plan 共 35 个前置 jobs 通过，未继承任何旧轮成绩。
Build004 的 source hydration 失败保留，Build005 plan 已成功读取恢复后的冻结规范。

## 精确计划

- 101 cases；2,281 selected prefixes；2,406 prerequisite source hashes。
- 长案例 ITQ-49/50/51（indices 65/66/67）各 152 selected prefixes。
- prefix_plan.json RAW SHA-256：`42ade981e457119e07ebb8930e2c746201f6f54ea4afb7c1a9a7fa081f4fadf0`。
- 下载后核验 run/source/manifest 身份、0..100 inventory、selected count 与唯一有序长度。
  对已下载的 split-6 prerequisite 文件另做哈希回读及 10 cases 的冻结 selected-union 对照。

## 已独立回读的长案例证据

ITQ-49/50/51 各 161 rows、两次 fresh snapshots、完整 comparator 与 repeat PASS。
对应 split-6 下载证据的 59 native stages、236 raw captures、9 个完整轨迹文件
大小/RAW hash 回读通过；actual Python PID/Job、CPU2500、1024/2048 MiB 与 EXITED/cleanup0 核验通过。
Batch RAW SHA-256：`21237d8f638a59ca9564778dfec6d8ab7c32f95f6f2d3de68e8abe7e9b83c50f`。
本地只做文件/哈希检查，未运行 Python/native/model。

## 尚未完成

全量 prefixes 与 50 原 Startup nodes 已开始；仍须全部 prefix、Startup、101 schema 和 final。
`FULL_DEVELOPMENT_CAMPAIGN = INCOMPLETE`，本报告不是全量 PASS 或正式 qualification。
原 Startup 49/50 必须与 versioned compatibility 分开；PF06 原 scope INCOMPLETE、
补充来源待审、历史异步 P1 因果缺口、T09 IMPLEMENTATION_HOLD、full P history 不可用、
hardware CALIBRATION_REQUIRED 均不因前置 jobs 通过而消失。
Production / Phase6 / DSX 修改未授权且未执行。
