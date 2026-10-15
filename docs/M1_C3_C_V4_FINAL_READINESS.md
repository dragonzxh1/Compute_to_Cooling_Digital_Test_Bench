# C3-C v4：可审签，正式测试尚未获授权

当前为 `READY_FOR_USER_SIGNATURE`，不是 `USER_APPROVED`，也不是 C3-C PASS。原v3无效运行保持原判。运输阻塞已修复并实证验证，v4开发及最终只读回读完成；完整目标尚待新包用户批准、fresh正式C3-C及最终行为证据验收。

## 唯一审签身份

Execution source / Delivery commit均为 `9012d6d9292a44226b0892332879de506812206d`。固定proposal ref：`codex/m1-c3c-v4-proposal-9012d6d`。之后的说明/证据提交不能替代这个执行身份；既有v3批准不自动覆盖新v4。

| 身份 | SHA-256 |
| --- | --- |
| Proposal RAW | `759cfca7b7b600f4a7c3faeb15a206f0c0c8188243ff15747e33a6457e76c357` |
| Proposal canonical | `91686c8394e7f3b085b9e9209fcc00381d55414edc9ba6a276a27affa35da41b` |
| Candidate（未改） | `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce` |
| Formal runner | `8b75b2a2ba4c391f219984497ac386bd986a9721711368637719b5f05493acdd` |
| 最终审签页 RAW | `fdf4df4b5172a971a61b1dbde23bc8cec00df6b97a3debe706e527877584fe83` |
| Source/delivery attestation RAW | `d4a58b973f9778b667996246ffb2a14e2320ca0e5a97addf31ed2060123707eb` |
| 最终回读结果 RAW | `811282c4e207c043ee5731076b1d53bd80571e8a9f4669ad7a425fe38998b177` |
| 最终官方ZIP | `a6641b5f413f6b0daef68136de424d6a97181aa403d368faf84850d948c7bedb` |

[最终只读回读run38673933017](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38673933017)的官方artifact ID11945890306，131453 bytes。完整交付14文件，全部797项source bindings、101inputs/3216rows/499计划快照/969静态stages+FINAL、9项拒绝检查及原登记已回读。实际Python PID988、CPU25%/256-512MiB、四份raw日志、release proof、cleanup active0及完整环境before/after均已核验（批准镜像20261012.333.1）。没有candidate import、模型行为执行或正式资格执行。签署页“9项”已与实际结果一致，原文案版本run38673547794原件保留。

## 修复及开发证据

大白话：v3各考场交来了答卷，但final漏收了上游监考记录。v4只补齐ref/reference-gate/select/split/prefix/plan的原始凭据下载；不改candidate、不改判卷要求。

- [只读运输验证38671417001](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38671417001)：18项正/负检查通过；旧802缺项精确复现，新汇集缺0项。原1969阶段Job及7876raw捕获验证；55773个导出文件SHA和716个completed batches另行独立回读。旧run38586777499仍INVALID，不事后补判。
- [基础设施开发验证38672641883](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38672641883)：53/53 Python合成检查、63/63 PowerShell控制检查；实际PID8008受限Job/cleanup与四raw哈希独立核验，无candidate行为。
- workflow除新增证据下载和namespace外与v3逐字相同，15项核心runtime/gate/schema/environment源码同样无语义变化；四份规范登记RAW完全不变。原snapshot601条物化后，原755项保护绑定未改。失败与准备版本均保留在Git和官方artifact。

## 使用说明和参数含义

软件入口、示例和接口见同一source commit内的 [M1使用说明](M1_SOFTWARE_USER_GUIDE.md)；物理参数逐项定义见 [v0.2参数表](V02_PHYSICS_PARAMETER_REFERENCE.md) 和 [旧场景参数表](LEGACY_SCENARIO_PARAMETER_REFERENCE.md)。覆盖记录为37类/259字段的静态参数文档覆盖，不是硬件校准证明。已有checkout外source SDK验证没有因本次纯执行链路修复改写或升级成绩。

| 执行/审签参数 | 含义 |
| --- | --- |
| expected_source_commit | 上述确切Git SHA；不是随时移动的branch HEAD |
| execution_manifest_sha256 | formal入口绑定Proposal RAW；只读入口另绑定自己的control RAW，不能混用 |
| runner_script_sha256 | 相应入口脚本原始字节hash；formal是run.ps1，只读是run_readback.ps1 |
| CPU25%、strict256/512MiB、campaign1024/2048MiB、480s | 测试执行机资源限制；不是泵速、GPU功率、液温阈值或模型时间参数 |

新formal入口为已注册 `m1-remote-long-probe-v2-1.yml`，`run_scope=formal_v4`，使用上述固定proposal ref；必须另提供精确绑定本包/源码/环境的freeze receipt及独立execution authorization。当前没有创建这两份v4授权，不会自动开考。获批后从prepare整轮fresh；原条件式prefix、repeat和schema全部保留，不能借开发/只读/旧v3 PASS。

## 仍明确保留的边界

原Startup历史49/50与versioned compatibility分开；SEM02五项严格P1 Lane B/C排除仍INCOMPLETE；PF06原域INCOMPLETE、补充需正式fresh证据；任意POST异常、OS崩溃或掉电原子性NOT_PROVEN；T09物理持久恢复HOLD、fullP历史不可用、hardware CALIBRATION_REQUIRED。生产、真实硬件控制和Phase6均未授权。本机历史整机硬挂根因没有被此软件资格证明解决，继续禁止在该机器运行Python/native/model压力或资格任务；隔离远程执行不等于证明本机已恢复稳定。

## 用户下一步

请阅读官方包内唯一 `USER_APPROVAL_DECISION_SHEET.md`，分别确认“冻结该v4确切包及执行源码”和“单独授权该v4全量fresh正式C3-C”。既有同hash语义/范围不重开政策裁决；新源码/manifest身份仍需明确批准。批准前 `EXECUTABLE_FREEZE_USER_APPROVED=NO`、`C3_C_FORMAL_EXECUTION_AUTHORIZED=NO`。

本地官方ZIP：`D:/Github/c2c-m1-remote-evidence/c3c-v4-final-closure-38673933017/official.zip`。完整机器审阅记录：`artifacts/m1-c3c-v4-review/independent_final_readiness.json`。
