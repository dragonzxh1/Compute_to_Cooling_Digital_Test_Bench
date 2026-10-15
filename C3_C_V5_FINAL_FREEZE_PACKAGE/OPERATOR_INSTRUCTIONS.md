# C3-C v5：待审签软件资格执行包

本包只提议冻结登记的离线软件 fixture 资格范围，不是生产控制器、硬件部署包或正式 PASS。三个独立决定为：范围/登记接受、确切包与源码冻结、随后单独授权 fresh formal C3-C。所有签署栏保持空白；任何旧 v4 授权不得替代本包授权。

## 包和执行身份

`EXECUTABLE_FREEZE_MANIFEST.json` 与仓库 `artifacts/m1-c3c-v5-freeze/executable_proposal.json` 原始字节相同。`EXACT_HASH_INVENTORY.json` 绑定所有静态包文件、来源和四项登记。确切 execution/delivery commit 在不可变提交之后，由只读 GitHub Job 核验，写入独立 `EXECUTION_DELIVERY_IDENTITY_ATTESTATION.json` 和 `USER_APPROVAL_DECISION_SHEET.md`；不使用后来的 branch HEAD，不循环计算自己的 hash。

本包应核对 101 descriptors、3216 rows、499 planned snapshots、969 static stages + FINAL。动态 prefix 继续使用冻结 selector：mandatory 674 加本轮 progress/confirmed 的精确 union，以及原登记支持案例前缀；不预填旧运行的 2281 个 prefix，也不借旧 PASS。原 Startup 50 个节点全部保留，历史 49/50 与 versioned compatibility 分开。

## 与 v4 的差别

候选 SHA-256 保持 `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`。新增执行 namespace；FINAL 在一次审计内只加载一次不变的包/环境锁，保留逐记录 Job/raw/schema/run/env 核验和执行前后 source guard，并记录 11 组阶段边界及 batch/case 进度。不降低任何门禁、不增加资源预算、不改模型 timer。完整上游 native artifact 家族仍须到达 FINAL。

旧 v3 漏收证据、旧 v4 FINAL 超时均保持 INVALID。只读旧档案回读及 57/62 项执行包检查是开发证据，不是新 full fresh formal PASS，不证明任意未来平台性能。

## 参数与使用入口

| 参数 | 意义 |
| --- | --- |
| expected source commit | 精确 40 位执行源码 commit，不接受 latest HEAD |
| package RAW / canonical SHA-256 | 绑定原文件字节及规范 JSON；不能互换 |
| approval / authorization SHA 与记录 | 分别证明确切包冻结和独立正式执行许可；缺一拒绝 |
| CPU rate 2500 | Windows Job CPU 25%，不是泵速 |
| STRICT process/job 256/512 MiB | 小阶段资源上限；CAMPAIGN 为 1024/2048 MiB |
| wall budget 480000 ms | 每受控阶段真实执行预算，不是模型响应 timer |

只读封包核验由 `v0_2/tests/tools/m1_c3c_v5_closure/run_readback.ps1` 执行，独立控制文件绑定哈希；不导入或运行候选。正式入口为 manifest 中的 v5 workflow/runner，仅在用户单独批准后从 prepare 全量 fresh 开始。任一 FAIL/INVALID 保存并 STOP，不在同 execution 修改重跑取 PASS。GitHub 绿色还须独立核验官方 ZIP、原始日志、全阶段/动态 prefix/repeat/schema、实际 Python Job 和 FINAL 退出后 cleanup。

稳定隔离环境中的 SDK 安装/CLI 操作和液冷参数解释见仓库 `docs/M1_SOFTWARE_USER_GUIDE.md`、`docs/V02_PHYSICS_PARAMETER_REFERENCE.md`、`docs/LEGACY_SCENARIO_PARAMETER_REFERENCE.md`；SDK 开发安装验收不等于 SDK CLI 正式资格。本机禁止 Python/native/model/压力测试。

## 必须保留的限制

SEM02 精确五项 strict P1 Lane B/C 仍 INCOMPLETE，不伪造 PLC issue；PF06 original scope INCOMPLETE、C8_normal row4/800ms supplement 独立登记，两原 negative controls 保留。complete-only publication 及已登记失败 cuts 不可豁免；任意 POST 异常/OS crash/power-loss 原子性 NOT_PROVEN。T09 physical durable recovery IMPLEMENTATION_HOLD，full P history 不可用，hardware CALIBRATION_REQUIRED。production/hardware/Phase6 未授权。原件与冻结候选、math、fixture、expectation、合同、profile、Safety 不修改。
