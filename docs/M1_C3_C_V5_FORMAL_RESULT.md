# C3-C v5 正式结果：限定软件资格通过

2026-10-16（新加坡）。独立官方证据回读后，判定：

`C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS`

只覆盖用户批准的 `M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN`。这次考试完整完成，不再是 v4 的 FINAL 超时，也不是用开发结果补正式成绩。它证明登记离线输入域内的 tracking / PRE / Safety / 模拟 PLC / POST 软件事务正确性，不证明真实 GPU→CDU 散热性能或现场控制安全。

## 1. 确切执行与证据

唯一 fresh [run38833878662](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38833878662)，attempt1，2026-10-16 01:12:43Z 创建，05:12:22Z 结束。没有重新 dispatch、重跑 failed jobs 或同 execution 修改后取 PASS。

| 对象 | SHA-256 / 身份 |
| --- | --- |
| Execution / delivery commit | `9ad4b9d1fdab261db9be09b91f261a927d529970` |
| Proposal RAW | `18d54940b672e4ec06b0c0c0a6691cf15219ee96e01b7864b31fe00a1adf23c8` |
| Candidate | `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce` |
| Runner | `78749fe78a6701ef2fb9157aa648f966bf088615bb39ab8ffb40f4dc02e51363` |
| 官方 final artifact12025669904 | 2,011,688,990字节；`bc8a49397e10415d157260c21e4d2869f3ace4065600a22aeb6da96a2140c293` |

两份独立用户收据、固定执行 ref 和 canonical proposal 身份保持原登记；不回写原空白审签页。说明分支 HEAD 不是 execution commit。

## 2. Fresh 成绩及独立核验

| 检查 | 本轮结果 |
| --- | --- |
| 登记案例 / 输入 | 101 / 3216行；全部 case checks、comparison PASS |
| ST / State U / ITQ | 16个 ST（含版本化 ST-12）+独立 State U +51 ITQ variants，均在本轮执行 |
| 完整快照 / repeat | 499份 SUT 快照；逐份 receipt、实际字节、trace index及压缩帧哈希一致 |
| Prefix | 2281个 selected prefixes；67575帧对照逐项匹配实际完整 reference / split 帧哈希 |
| Selector | 51 ITQ variants 的674 mandatory prefixes从冻结来源输入独立重算；2298 eligible universe；progress/confirmed triggers按本轮参考 records独立核对；support案例全部prefix |
| Schema | 101 case schema PASS；1970个外层 worker result另用冻结 JSON Schema独立验证 |
| 历史回归 | Fresh C 11/11、S 17/17、P15 PASS；C/S参考与split两侧均通过 |
| Startup | 原50个 node：49 PASS /1精确 legacy FAIL；版本化 compatibility另记PASS |

官方ZIP共96700文件已流式哈希，57495份native文件已核对。715 complete batches、1970阶段记录、1398 unique IDs（含动态prefix阶段），969 mandatory static IDs缺项0，另含 FINAL。7880份raw捕获及1970份实际Python Job/authority/环境/cleanup证明均匹配；2895份 SUT constructor receipts指向批准的 v4 SplitEngine。不要把 unique stage数量、实际重复阶段记录和 planned snapshots混为一谈。

836项保护来源复算匹配（832本地+4冻结bundle entry）；所有环境前后身份匹配批准锁，观测镜像均在批准列表。CPU25%、CAMPAIGN1024/2048MiB、480s及模型timer未放宽。本机仅进行PowerShell文件/ZIP/JSON/hash审阅，没有运行Python/native/model。

FINAL的11组BEGIN/END完整；外层阶段约137.1055s，未触发480s预算。独立回读覆盖 FINAL退出后的最终batch，不只相信子进程尚未退出时生成的PASS：actual PID7312、EXITED/exit0、cleanup_complete=true、active_after_cleanup=0。`semantic_crosscheck.json`中的91.281s是内部 FINAL_ADMISSION BEGIN到C3C_STAGE END的区间，不是完整外层阶段墙钟。

原 Startup唯一失败精确匹配冻结 node、源码hash、line144、assertion AST、AssertionError及 `LEGACY_STATE_C_STARTUP_SUSPENDED_TRUE_REPRESENTATION`；未改原test body、未改写成50/50。State U与v2、prefix/repeat均来自本轮，才允许单列versioned compatibility PASS。

## 3. 排除项没有被抹掉

SEM02精确五项和158个事件输入hash匹配登记：一个重建异步历史trace、四个非法/拒绝输入。strict P1 Lane B/C仍INCOMPLETE，没有伪造PLC issue或Safety receipt。

PF06 original scope仍INCOMPLETE；单独批准的C8_normal row4 /800ms补充域本轮formal通过，PRE/Safety/模拟PLC/POST、独立期望及两项原negative controls均匹配。旧library内的DEVELOPMENT/PENDING标签保留；新formal资格仅由已批准外层registration、真实执行和新结果赋予，不篡改旧身份。

任意POST异常、OS crash、断电原子性仍NOT_PROVEN；T09物理持久恢复仍IMPLEMENTATION_HOLD；FULL_P_HISTORY_VALIDATION_AVAILABLE=NO；真实硬件CALIBRATION_REQUIRED。本机硬挂根因没有被此次远程通过证明已修复。旧v3/v4 INVALID保留。

## 4. 审阅记录与使用入口

机器裁决：[independent_verdict.json](../artifacts/m1-c3c-v5-formal-result-38833878662/independent_verdict.json)。同目录保存case/native/schema/selector摘要、官方qualification原结果和FINAL原始证明。完整官方ZIP、GitHub日志和96700文件哈希清单保存在 `D:/Github/c2c-m1-remote-evidence/c3c-v5-formal-38833878662/`；精确hash登记在机器裁决中，可用两个新增纯文件审阅脚本复核，不执行候选。

第一次本地只读审阅在单元素JSON数组处被PowerShell管道自动解包，导致审阅器错误计数；实际原始证据明确为1元素数组。仅在新、未封存的只读审阅器使用 `-NoEnumerate`，保留最初观察，再重新读取同一官方ZIP。没有更改或重跑正式candidate、runner、fixture、expectation、job。另有一次本地提取命令因未设置目标路径变量而在写入前停止，补齐明确目录后继续提取原始字节；不涉及正式执行完整性。

使用说明见[软件使用指南](M1_SOFTWARE_USER_GUIDE.md)、[v0.2参数参考](V02_PHYSICS_PARAMETER_REFERENCE.md)、[旧场景参数参考](LEGACY_SCENARIO_PARAMETER_REFERENCE.md)。冻结指南的“未审签/未执行”是打包时点信息；最新结果以本报告为准，不修改冻结原件。37类来源hash及259字段说明重新核对，属于静态文档覆盖。已验证仓库外SDK安装仍是独立development验收，CLI额外文件不自动获得本轮formal资格。

## 5. 上线边界与下一步

当前可以提交用户验收的是“已通过限定资格的离线软件基线”，不是“全部系统阻塞已经解决”。生产移植、真实硬件控制、Phase6均未授权，不能自动启动。实际生产所需的物理恢复、校准及未证明的异常域需要各自定义与授权；本轮不能用缩小措辞代替这些工作。

下一步：用户确认本报告限定域结果，并确定下一阶段是离线软件发布审查，还是另行授权生产准备差距评审；不再重复本次已完成考试。
