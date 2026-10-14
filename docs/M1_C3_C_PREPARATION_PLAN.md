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
