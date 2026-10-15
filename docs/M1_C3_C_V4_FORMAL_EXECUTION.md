# C3-C v4：用户批准，fresh 正式测试已启动

2026-10-15（Asia/Singapore），用户分别批准“冻结 v4 审签页绑定的确切包及执行源码”和“单独授权该 v4 包进行全量 fresh C3-C 正式测试”。两项收据独立保存，未改 sealed manifest、原审签页或 candidate。

本轮 [正式 run 38675166533](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38675166533) 已且仅已 dispatch 一次，从 prepare 开始；当前是运行登记，不是资格 PASS。固定 ref 为 `codex/m1-c3c-v4-proposal-9012d6d`，执行/交付 commit 均为 `9012d6d9292a44226b0892332879de506812206d`。后续说明提交不改变执行身份。

| 身份 | SHA-256 |
| --- | --- |
| Proposal RAW | `759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357` |
| Proposal canonical | `91686c8394e7f3b085b9e9209fcc00381d55414edc9ba6a276a27affa35da41b` |
| Candidate | `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce` |
| Freeze receipt RAW | `57ab034c0e1497d0ad67bc573b810dabe6ff62ae431300eda1fcff04dd71e733` |
| Separate execution authorization RAW | `f280832e2ef0721d40d3b5076970dc86b0e362c6da2298bff812bd2de55c2b50` |

收据与机器运行登记在 `artifacts/m1-c3c-v4-authorization/`。启动前重新验证 797 项源码：793 项来自本地原始字节，4 项来自已冻结 ZIP entry；包 RAW/canonical、官方审签页和 attestation、runner、environment lock、remote pinned ref 全部一致。本机未运行 Python、native executor 或模型。

范围仍是 `M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN`：101 descriptors、3216 rows、499 planned snapshots、969 unique static stages 加 FINAL，原动态 prefix selector、repeat、schema、原 Startup、C/S/P15 及完整证据门禁。所有结果本轮 fresh，不继承开发或 v3 分数。任一预登记 FAIL 或完整性错误保存并 STOP，同一 execution 不修复重跑。

最终必须下载官方 artifact，独立核验 source/environment、raw captures、实际 Python Job 身份与 cleanup、全部 selected-prefix/repeat/schema 和最后 FINAL batch；GitHub 绿色本身不构成资格结论。

原 Startup 历史 49/50 与 versioned compatibility 分开；SEM02 五项严格 P1 B/C 仍 INCOMPLETE；PF06 original INCOMPLETE，补充单独判分；任意 POST 异常/OS crash/power loss 原子性 NOT_PROVEN；T09 IMPLEMENTATION_HOLD、full P history 不可用、hardware CALIBRATION_REQUIRED。原 v3 INVALID 不改判。生产/硬件/Phase6 均未授权。

大白话：用户已经批准了这份确切试卷和考试程序，现在重新正式开考。考试运行中不等于通过；还要收齐原始答卷和监考凭据再判定。

## 本轮终态（后续登记，不回写批准收据）

run38675166533已停止：`FINAL_ACCEPTANCE` native TIMEOUT / launcher124 / 480000ms，cleanup complete、active0。最终结果为 `INVALID_C3_C_EXECUTION`、行为判定 `NOT_MADE`；上游PASS不能替代未完成的最终资格验收，未在同轮修复或重跑。官方artifact、全部上游native覆盖和失败诊断已独立回读；见 [正式失败报告](M1_C3_C_V4_FORMAL_FAILURE_REPORT.md)。
