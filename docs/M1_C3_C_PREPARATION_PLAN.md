# C3-C 独立执行包准备（未冻结、未开考）

2026-10-14，用户明确要求先开发完成，再C3-C正式测试及冻结包审签。开发前提已满足：V4 full campaign run38423165745及安装后完整101输入run38493762797均有独立文件证据；不能借这些分数作为正式C3-C结果。

## 精确、独立的下一阶段

1. 在新版本路径创建formal admission/runner/证据schema及GitHub专用入口。现有m1_engine_v3/package_guard.py、旧DEVELOPMENT MODE/guard、已交付engine/SDK/manifest一律不改；封存测试数学、expectations、selector和比较器。
2. 先对新执行基础设施做静态及合成开发检查。不得在基础设施调试时宣称正式资格；任何失败保留。准确枚举执行source closure、101输入、原50Startup、PF16和补充、prefix/repeat/schema/stages/STOP，再形成一份可执行提案。
3. 提案绑定唯一candidate engine SHA70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce；frozen reference/source bytes、56 observer字段、18CMP规则、approved六state mapping、原输入/预期/时序不放宽。Reference先持久化核验，再selector、SUT、prefix；非历史每项2snapshot、C/S/P15原repeat policy；逐样本比较完整帧，不仅最终state。
4. 用户签署确切新freeze manifest/source commit及scope后，单独hash-bound正式authorization启动fresh执行。结果区分PASS、有效behavioral FAIL及INVALID；发生preregistered FAIL不得原执行修后重跑。GitHub绿色必须再独立下载核验官方artifact/日志、actualPID/Job、before/after环境、selected union、repeat和schema。

## 必须一并交付、不能伪装关闭的事项

| 登记事项 | 需要签署的确切边界 |
| --- | --- |
| SEM01 versioned addendum | detached POST legacy view；真实PRE/Safety/PLC不回滚、不加样本credit；C2-R1 complete-only及C3-A CMP-C05不得豁免。V4实际登记的软件失败cuts已有修复证据；ARBITRARY_POST_EXCEPTION_ATOMICITY=NOT_PROVEN，任意OS中断/掉电不是已验证软件cut |
| SEM02五case | 使用docs/M1_V4_SEM02_PROPOSED_BINDING.json中的原nodeIDs/source/input typed hashes：一条async reconstructed trace及四条invalid/rejected inputs；不伪造PLC receipts；strict P1 Lane B/C仍INCOMPLETE；原50 test和原49/50保持、versioned PASS单列 |
| PF06 supplemental | docs/M1_V4_PF06_PROPOSED_BINDING.json，C8_normal row4/800ms，源input独立expectations和PRE/Safety/PLC/POST cuts；两个原negative controls保留。Original scope仍INCOMPLETE，补充待批准，不回写原C3-A |
| Formal范围 | 限定已登记离线软件fixture domain；不叫完整runtime/hardware资格。若拟议范围触发不可排除的未满足mandatory义务，NOT_READY，不写豁免后取PASS |

正式提案必须带source/input/environment完整hash manifest和一次性签署页，不创建一串重复语义审计。当前本文件是实施计划，不是final freeze或签署请求；formal runner bytes尚未完成，不虚构最终package hash。

## 已完成：独立审批/完整性基础层

新namespace `v0_2/tests/tools/m1_c3c_v1/` 已实现严格RAW/canonical审批绑定、四项registration文件绑定、source/input metadata一致性、环境精确一致性及PASS/FAIL/INCOMPLETE/INVALID区分。31项合成开发检查在[run38495915226](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38495915226)全部通过，官方ZIP摘要、4份raw captures、actualPythonPID5260/256与512MiB Job/cleanup active0和before/after环境均独立核验。

该测试没有candidate/reference导入或行为运行；合成的approval对象不是批准记录。它证明新门禁检查路径能拒绝错误身份，不证明完整正式执行链路已经完成。机器证据见[M1_C3_C_PREFLIGHT_EVIDENCE.json](M1_C3_C_PREFLIGHT_EVIDENCE.json)。新workflow不在默认分支时GitHub拒绝dispatch，已通过现有调度入口的专用分支新版本处理；旧SDK执行commit、workflow与artifact身份仍原样留存，未merge main或重跑旧执行。

仍须完成的新文件：独立formal admission/worker/runner/batch、完整fresh分阶段workflow、exact environment与artifact schema/STOP规则、完整stage inventory和四份版本化scope registrations、最终freeze manifest及空白用户签署页。不能调用旧FINAL把DEVELOPMENT result改名为formal PASS；sealed库的中间记录保留原身份，正式结果须由新受控执行和新独立完整性/范围门禁裁决。

## 后续进展：正式编排代码已组装，未封存

source229ea624ec2638494ce28fc0a265bc45a246a6b0提供独立runtime admission、formal source lock、case driver、stage worker、batch/runner、final gate、环境锁、stage schema/STOP及完整分阶段workflow。旧development-only driver/guard均未修改；新driver只替换授权调用、保留原函数内数学/断言AST及legacy内部artifact metadata，不调用被禁用的development入口取得formal成绩。正式结果由新的签署身份与独立final gate产生，仍须fresh真实执行，不能使用已有development result。

[run38498863117](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38498863117)以development模式执行45/45静态/合成检查，formal job明确skipped。官方ZIP、4raw captures、actualPID7836/Job/cleanup、before/after环境和source身份已独立核验。没有candidate import/行为运行、没有自动审批。证据：[M1_C3_C_ASSEMBLY_EVIDENCE.json](M1_C3_C_ASSEMBLY_EVIDENCE.json)。

尚须验证PowerShell控制面及完整阶段/graph inventory，完成四项versioned登记文件和最终可执行hash manifest/空白签署页，才能提交确切冻结包。当前代码编译/合成PASS不表示完整formal路径已实际跑通，也不表示可审签包已经完成。正式开考前先把这些基础设施条件关闭，不再重复调tracking算法。

## 最终准备结果（优先于上文阶段性进度）

47项Python静态/合成检查和60项有限PowerShell控制/graph检查通过，并独立核验官方artifact、actual Job与原始日志。旧matrix checker假设及首次package culture-sort失败保留，修订没有改候选/冻结fixture/期待/数值规则。新PF06门禁只用本轮phase bytes自校验与独立预期/冻结CMP，不把历史SUT phase hashes当golden。

签署前[run38564672946](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38564672946)验证714 bindings、101inputs/3216rows、499planned full snapshots、FINAL前969静态stages，原始证据和actualPID7500/cleanup independently PASS。它没有执行候选或正式qualification。

确切提案在 `artifacts/m1-c3c-v1-freeze/`，active scope为limited_scope_v2.json，原scope及失败证据保留。统一签署页USER_APPROVAL_DECISION_SHEET.md列四项决定与所有边界。Proposal RAW=f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45；canonical=7d233befd38c85046bf8b52920660651ea839e41ad4e0070353b3174749e1e35。最终用户执行approval必须再绑定交付source commit，不从snapshot_parent_commit猜授权。

当前仅等待用户对该确切包/SEM01/SEM02/PF06补充统一审签并授权fresh正式执行。不自填批准或开考，不自动production/hardware/Phase6；fullP不可用与T09 hold不改变。完整目标仍未完成，下一项是实际C3-C正式fresh执行及最终独立证据审阅。

```text
DEVELOPMENT_PREREQUISITE = COMPLETE_WITH_INDEPENDENT_EVIDENCE
C3_C_EXECUTABLE_PACKAGE = PREPARATION_NOT_FINALIZED
C3_C_FORMAL_EXECUTION = NOT_STARTED
EXECUTABLE_FREEZE_USER_APPROVED = NO
PRODUCTION_IMPLEMENTATION_AUTHORIZED = NO
HARDWARE_CONTROL_AUTHORIZED = NO
FULL_P_HISTORY_VALIDATION_AVAILABLE = NO
T09 = IMPLEMENTATION_HOLD
REAL_HARDWARE = CALIBRATION_REQUIRED
PHASE6 = NO
```
