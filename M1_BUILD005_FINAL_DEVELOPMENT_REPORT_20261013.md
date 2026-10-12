# M1 Build005 完整开发 campaign：执行与独立证据回读通过

本轮开发验证已完成。结论严格为 **M1_DEVELOPMENT_COMPLETE_FULL_SCOPE_PENDING**：
软件工程执行/对照/回放/证据检查通过，但不自动成为完整原始范围正式资格、production port、
Phase6 或硬件 qualification。大白话：这次整套软件考试跑完，保存的成绩和过程也核对过；
它不证明真实 GPU—CDU 散热性能，也不补造缺失的历史命令签发证明。

## 本轮身份与结果

[GitHub run38269665488](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38269665488)
共288 jobs成功：287实际执行 jobs +1纯 plan。执行源码固定为
`9b487ce88143b5bd8f6f537af9f7b2629fa4e27f`；后续文档提交不是新的执行源码身份。
全部成绩本轮 fresh 生成，没有拼接任何旧轮 PASS。

| 项目 | 本轮结果 |
| --- | --- |
| 输入案例 / schema | 101/101 |
| 精确 selected prefixes | 2,281/2,281 |
| 从 t0 回放的完整帧对 | 67,575，无差异 |
| 独立解压并重算的 reference/split canonical frames | 6,432 |
| Fresh split snapshots | 499，原定2/11次重复的完整文档一致 |
| 前置来源文件哈希 | 2,406，一致 |
| 三个长案例 ITQ-49/50/51 | 456/456 prefixes，34,911帧对一致 |
| C / S | reference与split分别11/11、17/17 |
| P15 | 冻结重建历史 fixture PASS，11次 snapshots |
| 原 Startup | 49/50，唯一合法 legacy failure 精确匹配 |
| 版本化 Startup compatibility | PASS，本轮 fresh U/v2及完整回放参与汇总 |

原 Startup line144 的 `startup_demand_suspended` / AssertionError / AST / semantic identifier
未修改、未回写为50/50。150 pytest阶段报告及附属RAW文件已独立回读。

## 完整执行证据：不能把 final 包的子集当总数

原 final 内嵌 execution_audit 为152 batches /467 stages，仅涵盖被下载到final机器的
prepare、Startup、schema。reference/select/split/prefix native logs 保留在各自 owned artifacts，
没有丢失；该内嵌结果原样保留，未改写或放宽 gate。

另外从119个已成功执行的来源 ZIP 核验官方 digest，选取native/job logs，
再与此前下载的6个根目录合并。重复路径必须字节一致；不重跑candidate、不改判据。
完整union独立核验 **287 primary jobs、715 batches、1,968 stages、7,872 raw captures**：
实际Python PID/Job membership、CPU2500、1024/2048 MiB、assigned-before-resume、
source/environment/evidence acceptance、EXITED child0、cleanup complete /active0均有效。
287个软件环境登记一致，逐stage after环境与批准软件身份一致。
外部5秒抽样记录的最大private commit约188.5 MiB；这是抽样最大值，不是精确峰值。

官方 final ZIP 原包保留，1,946,410,368 bytes，独立复算SHA-256与官方artifact digest一致：
`abf937de6800172749b9e0c2f46a80e6ad7d8771138501142a4a2b723418b992`。
原 development_result.json RAW SHA：
`a4a45ef25db935e5532780dfe57c562eb28f676b38768378e4938ea5f0e959c0`。
案例回读记录RAW SHA：`7a78a69023bb718b0d9f174ab9c480cc9df5ea2860d38e66e035b612b040abd8`。
完整native回读记录RAW SHA：`c2f8f6b00a77abeb1cced82542271c213ad9e014b30260593a704f1d51c29459`。

655个受保护源码重新核验0 drift。candidate仍为
`453f2f1d02c9aaa845d5222b3ef01da8c1a9db6580268c54674d374d76fa9300`。
Manifest仍为`6842d3bd57a73d883d724fe7352680f9dfd1ba9a2c420b9ec5fa0925b05ffe93`。
冻结math、Contract15A、profile、Production Safety、fixtures/expectations、原Startup均未变。
本机只下载/解压/哈希回读，不执行Python/native helper/model或布尔压力测试。

## 仍然保留的边界

- PF原注册路径15/16获开发证据；PF06原scope INCOMPLETE。
  C8-normal补充来源DEVELOPMENT_VALIDATED，但binding仍PENDING_USER_REVIEW，未自行批准。
- 5个历史异步/隔离输入域仍不具strict P1因果资格；compatibility PASS不等于causal PASS。
  full P history不可用，不宣称恢复P1–P20。
- T09 physical recovery仍IMPLEMENTATION_HOLD；真实硬件CALIBRATION_REQUIRED。
  original_frozen_full_scope_ready /formal qualification /production /Phase6均NO。
- 本机整机硬挂根因仍未证明。本地Git损坏对象已保留备份，未修复、删除或reset；
  远端PASS不证明本机已稳定。后续git提交只禁用该命令的auto-gc，不改全局配置。

## 证据位置与后续

`D:/Github/c2c-m1-remote-evidence/run-38269665488/` 保存original ZIP、final解压包、
native-union、逐artifact digest/提取receipts，以及完整case/native readback JSON。
临时重复ZIP在核验digest与native字节后仅删除各自精确临时文件；原final ZIP、提取日志、
已有历史证据均保留。大份数据不加入Git；官方artifacts仍有保留期，应保留本地原包。

本阶段完成后关闭自动跟进。下一步先审阅PF06补充来源和strict-P1历史输入分域边界，
再决定新的开发/冻结范围；不自动开启formal C3-C、production port、Phase6或硬件测试。
