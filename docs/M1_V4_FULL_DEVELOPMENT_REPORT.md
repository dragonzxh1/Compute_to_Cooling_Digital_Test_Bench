# M1 V4 完整开发验收与独立证据回读

状态：FULL_DEVELOPMENT_AND_INDEPENDENT_FILE_READBACK_PASS。

已修复M1-DEF-POST-001的登记软件失败路径，并完成fresh完整开发campaign与仓库外SDK安装检查。未开始正式C3-C、production、硬件控制或Phase6；没有自批可执行冻结。它是可继续准备交付的开发版本，不是现场CDU控制器资格证明。

## 1. 精确版本身份

完整campaign：[run38423165745](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38423165745)，执行source717a98dd89ece8d3b6944a80727b32f20a311b8b。后续文档提交不能替换该source。

| 对象 | RAW SHA-256 |
| --- | --- |
| 执行manifest | eef95f5ace0e33e862b098087cc7030718f73c2099b60695251f8feaf4682446 |
| run.ps1 | 138ad299058888d59500416150f7ff0228f04944e7830f35f5db8d0b4e774aef |
| V4 engine.py | 70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce |
| 最终官方artifact ZIP | 7fc702a3597915ab06b72bf997b410aae9e374e14ab11fe87c85ef3e6eb3d206 |
| development_result.json | 1d9473004f9b0c2e439b50a216c0526c26e81a3d34a58c72d1a1a273705ed547 |
| plan | 78644eea430211ccc2423862f93160ac5e5e42829167df5e6401161da3baa9e8 |
| 全案例独立回读 | 0be61372fac5f73bbf12a98c01d8d1b812e5d34826b305b17695c258536a1cb0 |
| 全原生Job/日志独立回读 | 8282128c3bf016b0e377eb5c683ad4a0dc438081fab314f976146ac7e5f1c344 |
| 原Startup独立回读 | 4c9be8b7140eef659078bd259bf6b24c3070250aa1494753c2a4e28e720b369b |

原始证据保存在D:/Github/c2c-m1-remote-evidence/v4-full-38423165745，含官方最终ZIP、计划ZIP、134个补充native任务ZIP、官方workflow日志和完整解压记录。官方artifact摘要逐一匹配GitHub API；本地补充回读文件的hash不是自签资格证书。

## 2. 新鲜执行范围与独立检查

| 项目 | 本轮结果 |
| --- | --- |
| 101登记descriptor，含51ITQ变体及U/ST/C/S/P15 | 101/101 PASS，全部新运行；不是正式qualification |
| selected-prefix精确集合 | 2281/2281，mandatory/progress/confirmed union和原selector不变 |
| 前缀从t0回放、完整帧回读 | 67575对；6432份full reference/SUT帧逐一解压hash，未只比较最后state |
| 确定性full快照 | 499份；非历史类2份、C/S/P15每个descriptor11份，原字节/规范hash一致 |
| schema与计划绑定 | 101组，2406个case前提文件hash全部核对 |
| 原Startup | 原test body50项保持不变；49pass/1fail，唯一line144 legacy identity精确匹配 |
| 版本化Startup兼容 | PASS，fresh U/v2及其repeat/prefix通过；不是原Startup50/50 |
| C/S/P15 | fresh C11/11、S17/17、P15在冻结重建域PASS |
| 受控执行原始证据 | 287个真实执行任务＋1个纯计划任务；715批、1969阶段、7876 raw captures |
| 真正V4构造器 | 2895次实际构造身份正确，SUT阶段不可空身份；未把V3字节审计冒充V4行为 |

长案例65/66/67均161拍、各152个选中prefix、11637对完整帧；S-history92为51拍、11份确定性快照与51个prefix。没有借用Build005或先前27项开发回归成绩拼接本轮。

## 3. 环境和资源身份

Python3.11.9，GitHub Windows2022、Windows10.0.20348、win22 image20261004.326.1，完整依赖见[M1_V4_FULL_DEVELOPMENT_EVIDENCE.json](M1_V4_FULL_DEVELOPMENT_EVIDENCE.json)。每个阶段before/after身份一致；分布式host名字允许不同，不伪装一台物理机器。

逐阶段核对ready/release PID、目标Job名称及proof hash、实际python.exe模块、CPU hard-cap25%、process1024MiB/job2048MiB、480s墙钟、active-process4、kill-on-close、赋予Job后才resume、exit0、清理后active0；原始stdout/stderr及核验器日志逐一核对。外部采样最大private bytes=202100736，不是精确峰值或本机稳定性证明。模型时间、threshold/timer、physics/controller/Safety均未因此改变。

## 4. POST修复证明边界

V3基线同一4个故障路径测试3FAIL/1PASS；新V4同一4测试PASS，原受影响23测试亦PASS。本轮fresh prepare再次执行4/4及原单元测试。

V4把projection/观察/解码/结果序列化/completed-store准备放在公开赋值之前。已登记的projection拒绝、Record序列化失败和completed-store失败不能产生fake fresh publication；真实PRE/Safety/PLC事实不回滚，不重签命令，不给POST额外证据。不以报告措辞冒充代码修复。

ARBITRARY_POST_EXCEPTION_ATOMICITY=NOT_PROVEN。任意OS进程中断、掉电、真实外部设备durable reconciliation仍未证明；T09=IMPLEMENTATION_HOLD。complete-only义务不被删去或豁免，只有实际登记测试切点获得开发验证。

## 5. SDK和使用说明

[独立安装run38458640545](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38458640545) source2f1bbdbb5197a60d1dabac7ce8ca687e0285a932；实际导入SUT路径在解压SDK下，不依赖checkout。674包内文件、4raw captures、actualPID2588/Job/cleanup核验通过；describe/verify和3拍示例comparison PASS。SDK ZIP SHA256=8e5496f21c948284dd262077456e17a96d70011bee098be3668b07861b57384c。

[使用说明](M1_SOFTWARE_USER_GUIDE.md)、[V0.2物理参数](V02_PHYSICS_PARAMETER_REFERENCE.md)、[旧YAML参数](LEGACY_SCENARIO_PARAMETER_REFERENCE.md)分域说明。37类/259字段的静态覆盖与源码hash重新一致。SDK3拍是安装/小例子证明，不替代长工况或完整campaign；仍需扩展安装后实际用户用法验收与最终发布范围签署，不能以小示例宣称全平台上线。

## 6. 未被掩盖的范围缺口与下一步

原Startup5个精确历史/invalid输入仍strict P1 Lane B/C INCOMPLETE，不伪造PLC issue；原Startup49/50保持。PF06原scope INCOMPLETE，C8_normal row4/800ms补充DEVELOPMENT_VALIDATED_PENDING_APPROVAL，两个原负对照保留。Full P history unavailable，真实硬件CALIBRATION_REQUIRED。

下一步：扩展SDK安装后长输入/可用性检查，汇总准确的限定软件发布/冻结签署包。正式C3-C和生产/硬件/Phase6均仍需明确独立授权，不在本轮顺便运行。主工作区tracked文件未改；冻结旧版本、失败证据和DSX/Twin/workbench保留；没有本机Python/native/model压力执行。

