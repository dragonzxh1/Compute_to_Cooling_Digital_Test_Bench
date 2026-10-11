# 完整 M1 远端准备 v1 与短 prefix pilot（2026-10-12）

## 当前结论

从 GitHub main `2f26815` 新建独立 worktree/分支 `codex/m1-remote-development-20261012`。
541 项 M1 原文件约 12.4 MB：101 descriptors / 56 观察字段 / 71 个历史输入源，
222 规范源码 + 5 规范 artifact。原 raw hash 全匹配；Python canonical/实际运行核验
在独立 Windows pilot 进行。本机无 Python/压力/model execution。

完整 M1 文件准备不等于全量 M1 行为通过。当前只准备 10 stage pilot，不借已有 smoke
或历史 PASS；长 prefix / full campaign 尚未执行。

## 不变的工程语义

- 新 `m1_engine_v1` 的九个核心文件与 v014.1 原 exact bytes 相同：engine、codec、
  comparator、scheduler、state_copy、pre_oracle、projection、pf16、schemas。
- 外围 observer/replay 采用 v011 无 decorator 基础，加普通 BEGIN/END mark。
  已只读核验 v011/v014.1 engine 除首行说明外全文一致；仍用 v014.1 原核心文件。
- qualifier/合同/Production Safety/controller/physics/profile/ITQ inputs/expectations
  与旧 v005-v008/v011/v014.1 文件均不改。新 namespace 的 host/path/I/O adapter 独立登记。
- 原 frozen binding 的五份历史技术授权附件用 exact-byte portable store 映射。
  原名字、正文、raw/canonical/aggregate 校验不删；不在云端创建伪造本机用户目录。
  附件作为冻结技术来源，不执行旧 Prompt，不借其过时授权拓宽现在的权限。

## 静态准备证据

source_inventory RAW `02d336b2c5217ef279ced4f9ebefafc7ec2b9110ec567da7341052f0b073fa39`。
bundle 601 entries（M1 closure + 既有 smoke/native dependencies），2,094,360 bytes。
逐 entry SHA 回读匹配；41 个新 adapter/workflow source bindings；PS 两入口语法 PASS；
九个核心源字节一致。外部附件 credential-pattern 检查未发现 credentials。
`prepare_snapshot.ps1` 的 secret regexp 本身被 scanner 命中，属检查代码 literal，不是 token。
这些是静态准备，不是 candidate behavioral PASS 或主机稳定性认证。

Execution manifest RAW `8d9e75762a4f2fff14f46fd3ec708218b1fe3075c0d16df1130ec25dc4571b58`。
Remote runner RAW `409d8a39a9d31db313f24fddf8198df49eadf24044911d774f4cf1b0c4c4aae5`。
JSON/压缩包为程序生成的输入清单/精确源快照；冻结原文件不重写、不重新取预期。

## 初始执行计划

Environment → INPUT_INTEGRITY（101 materialized inputs、23 cases/51 variants、
原 canonical guards）→ CORE_SELF_CHECK（原 unit + 9-file identity）→ CMP_NEGATIVE
（原 18 rule negative coverage/selfchecks）→ ST-01 index=1 / 3 rows：
fresh REFERENCE → 原 SELECT → SPLIT 与原 repeats → prefix 1/2/3 各独立从 t0 完整重放。

比较保留全 PRE/Safety/PLC/POST 与 56 fields，不 final-state-only、不 wildcard。
PREFIX_ONE 单独 artifact 明确记录 replayed subset；完整 PREFIX 原 schema 不增字段。
整套 selection 仍由 fresh reference 与 frozen policy 机械产生；不能因为长而删 selected。

继承已实际核验的 owned native Job 与外部 verifier；实际 Python 归属 proof 在 release 前，
CPU rate 100/10000、256/512 MiB、120 s/child，raw fsync/hash/readback 再 gate。
新 remote environment registration 绑定 Server2022/Python 3.11.9/exact deps/source bytes，
旧本机 environment guard 原样保留，不无条件返回 True。源/env 每阶段前后核验。
薄日志 32 MiB/child 是新诊断预算，不是 tracking 阈值/timer；无 Python FFI/timer thread/
context-manager/decorator tracing/布尔压力前置。首错整批 STOP，失败与快照保留。

只在 GitHub **托管** Windows；publish/dispatch GitHub CLI，提交 `[skip ci]`；
不启动旧 broad CI，不在本机或 self-hosted runner 运行。DSX/Twin 不进入 M1 snapshot。

## 后续不能跳过的边界

Pilot PASS 后再准备 65/66/92 长 selected prefixes。每个 prefix 从 t0 完整 replay，
可按 prefix 独立 child，但不把单个 prefix 分段续算。预计完整 prefix 库不适合一次
塞进 25 分钟 smoke job；需 hash-bound deterministic shard/receipt 汇总与完整性 gate，
不能通过放宽仿真时间/减少病例冒充 complete campaign。

最终仍需 fresh 101-case/ref/selection/split/prefix/repeat/Startup/C/S/P15/PF/schema scope。
PF06 来源扩展未偷偷接受；历史 async P1 来源缺口仍显式；T09 IMPLEMENTATION_HOLD；
原 Startup 49/50 与 versioned compatibility 分开；full P history unavailable；
hardware CALIBRATION_REQUIRED。即便工程运行全过，也不自动宣布原 full-scope ready。

Formal C3-C / production port / Phase 6 / real control 未授权。本文件为执行前准备，
实际 pilot 状态与 artifact hashes 后续单独记录，不修改本文件的既有静态事实。
