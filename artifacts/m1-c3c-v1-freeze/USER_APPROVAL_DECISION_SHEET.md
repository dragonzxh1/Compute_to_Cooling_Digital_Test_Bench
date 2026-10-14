# C3-C 限定软件域：统一冻结审签页

状态：PROPOSED_NOT_USER_APPROVED。本页不是批准记录，不自动开考。

## 签署对象和实际范围

签署对象是同目录 [executable_proposal.json](executable_proposal.json) 的确切RAW及canonical SHA-256，执行源码commit由最终交付明确列出。文件或源码身份变化必须重新签署，不能补写本页冒充已经批准。

本包拟考核完整101登记descriptor（含51 ITQ变体）、969项唯一静态stage＋FINAL、fresh原50 Startup、C11/S17/P15、原prefix/repeat策略、全部schema及actualPython/Job/source/environment/raw evidence。Prefix精确数量在fresh reference持久化后由原selector生成，不能预填旧2281或借旧PASS。ITQ/U/ST2快照、C/S/P15共11；总499full快照。

它考核冻结输入域内的离线tracking与PRE/Safety/模拟PLC/POST软件因果/发布行为，不是整套生产液冷控制器、真实PLC、完整durable runtime或硬件资格。原热/压/flow、FF、硬件envelope及T09缺口不能被此限定结果伪装关闭。

## 一次审签的四个决定

| 决定 | 精确登记及不能抹去的边界 | 用户决定 |
| --- | --- | --- |
| D1 限定范围 | limited_scope_v2.json；完整登记软件域，动态prefix union和post-cleanup独立回读不可省略；不是任意运行/硬件范围 | 待用户填写 |
| D2 SEM01 v3 | SEM01_addendum_v3.json；PRE/Safety/已issued PLC事实不可回滚、POST不得再赚样本；complete-only及CMP-C05必须成立。V4已测准备/序列化/store失败cuts有真实修复，arbitrary exception atomicity仍NOT_PROVEN | 待用户填写 |
| D3 SEM02 | SEM02_five_case_registry_v1.json；精确一条async重建trace＋四条invalid/rejected输入，node/source/158 typed-event hashes保留；严格P1 B/C仍INCOMPLETE，原50及49/50不改、versioned PASS单列，不伪造issue | 待用户填写 |
| D4 PF06补充 | PF06_C8_NORMAL_SUPPLEMENT_v1.json；C8_normal row4/800ms、独立PRE/POST/Safety规则及两个原负对照。原scope INCOMPLETE，补充仍DEVELOPMENT_VALIDATED_PENDING_APPROVAL；旧SUT phase hashes仅历史诊断，不是新golden | 待用户填写 |

## SEM01 是否阻塞这个范围

C2-R1 T09与C3-A CMP-C05的complete-only义务没有删除：projection、serialization及completed-store等登记软件失败路径必须fresh通过，不满足就STOP。旧Build005/V3 publication-before-projection缺陷不靠改措辞消除；V4源码和真实失败/修复开发证据分别保留。

C3-A第10节明确允许软件fixture core单独限定验证，完整runtime仍受durable/restart/hardware缺口阻塞。本提案只主张该有限域与登记cut，不主张任意异步OS异常原子性。若要求把任意POST异常或真实durable恢复纳入本次范围，本包NOT_READY，不能靠批准措辞豁免。T09=IMPLEMENTATION_HOLD始终保持。

## 当前身份及待完成的独立核验

Proposal RAW SHA-256：`f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45`

Proposal canonical SHA-256：`7d233befd38c85046bf8b52920660651ea839e41ad4e0070353b3174749e1e35`

签署前独立回读已通过：[run38564672946](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38564672946)，714 bindings/101inputs/3216rows/499planned snapshots/969static stages。官方artifact、4raw captures、actualPID7500/25%CPU/256与512MiB/cleanup active0及before/after环境均核验。没有candidate import/行为运行或自动审批。

Candidate SHA-256：`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`

具体registrations的RAW hashes由executable_proposal.json原样绑定。原limited_scope.json与前两次失败/旧Source身份保留，不使用它们替代新v2登记。

审阅人、日期/时区、保留意见：待用户填写。

```text
EXECUTABLE_FREEZE_USER_APPROVED = NO
C3_C_FORMAL_EXECUTION_STARTED = NO
PRODUCTION_IMPLEMENTATION_AUTHORIZED = NO
HARDWARE_CONTROL_AUTHORIZED = NO
FULL_P_HISTORY_VALIDATION_AVAILABLE = NO
REAL_HARDWARE = CALIBRATION_REQUIRED
PHASE6 = NO
```

用户随后明确批准上述确切包与执行source后，再单独保存hash-bound approval及execution authorization，不回填改变本提案字节。正式执行必须从prepare全量fresh开始；任何FAIL/INVALID保留，当次不得修改后重跑取PASS。正式final绿色还需下载并独立核验最后batch的真实cleanup/source/environment/原始日志，才能交付资格结论。
