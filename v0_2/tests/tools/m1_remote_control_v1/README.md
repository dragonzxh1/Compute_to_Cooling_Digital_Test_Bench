# M1 remote development v1 — input closure + short-prefix pilot

从 main 2f26815 开始的新 worktree，原开发机不启动 Python。当前只预登记 pilot，
不是 formal C3-C/production/Phase 6，也不是完整 campaign PASS。

完整源码/输入 closure：541 项文件，101 descriptors、56 observed fields、71 个历史输入源，
222 normative sources + 5 artifact bindings。历史 structured_result 只供 input pointer 和
source integrity 使用，不借它的 checks/snapshot/旧成绩生成 expected output。

原 v005-v008 / v011 / v014.1 / 合同 / qualifier / fixtures / expectations 均不改。
新 m1_engine_v1 的 engine/codec/comparator/scheduler/state_copy/pre_oracle/projection/pf16/schemas
九个文件与 v014.1 exact bytes 相同。外围 unlogged adapter 基于 v011，增加普通 boundary mark，
无 logging decorators/context-manager wrappers/Python FFI/watchdog/布尔压力。

五份历史技术授权附件通过绝对路径参与 hash。新 common 只将这些明确绑定的名字映射到
exact-byte portable store；不删绑定、不修改正文/hash、不在云端伪造本机用户目录。
旧 common/environment guard 原文件保留；新 remote registration 独立记录实际 Server2022
环境、Python 3.11.9、同 exact deps，以及 owned Job/source identity。

pilot：Environment → 所有 inputs/JSON/hash/canonical guards → 原 unit checks + 9-file equality
→ original CMP negative selfchecks → ST-01 3-row fresh REFERENCE → original SELECT → SPLIT /
original repeats → selected prefix 1/2/3 each from t0 independently. 全 phase records/56 fields
精确比较，不用 final-state-only 或字段忽略。每个 prefix 的 PASS 只代表该 prefix，不能伪装
全 inventory prefix PASS；原 all-prefix schema 保持不变，PREFIX_ONE 是单独版本化 artifact。

owned native helper与外部验证器沿用已检查 exact binaries，实际 Python 必须先证明归属，
CPU 1%、256/512 MiB、120 s；raw fsync/readback 后 gate，首错整批 STOP，保留失误。
Progress 32 MiB 是执行诊断预算，不是 tracking timer。日志 namespace 清楚包含 stage/tick/phase，
不记录任意对象 repr；MODEL time 不随进程隔离变化。环境/源码每阶段前后核对。

长目标 65/66/92、完整 development campaign 还需后续执行适配与独立 evidence，
不能把 pilot 三个 prefix 当完整 M1。PF06/P1/T09 缺口、原 Startup 49/50 身份、
Full P history unavailable 和硬件 CALIBRATION_REQUIRED 始终保留。

GitHub 只 manual workflow，所有发布 commit [skip ci]。不得 broad collect 整个 old tools
或运行旧 runner，禁止在本机/ self-hosted runner 复现压力。DSX 不在包里。
