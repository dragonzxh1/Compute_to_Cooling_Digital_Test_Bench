# C3-C v5：用户批准的 full fresh 正式执行

用户于2026-10-15（Asia/Singapore）明确批准：“批准冻结 v5 审签页绑定的确切包及执行源码；单独授权该 v5 包进行全量 fresh C3-C 正式测试。”两项决定分别保存为新收据，不修改sealed proposal、原空白审签页或历史证据。登记操作跨至2026-10-16，不回写批准日期。

| 绑定对象 | 身份 |
| --- | --- |
| Exact execution / delivery commit | `9ad4b9d1fdab261db9be09b91f261a927d529970` |
| 固定执行ref | `codex/m1-c3c-v5-proposal-9ad4b9d` |
| Proposal RAW | `18d54940b672e4ec06b0c0c0a6691cf15219ee96e01b7864b31fe00a1adf23c8` |
| Proposal canonical | `74bafde655de214ee02b39b1a9c9d23acd0219ce30309afb9ca810c58447246d` |
| Candidate | `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce` |
| Formal runner RAW | `78749fe78a6701ef2fb9157aa648f966bf088615bb39ab8ffb40f4dc02e51363` |
| Freeze approval receipt RAW | `1d5ac4f01fcc6f7a11b35d29c00e0241a31a2feeac038cac92f8abbfb3555def` |
| Separate execution authorization RAW | `76ad4f5817d625e05a5b9a9a96afde9c4ffb4375a699dc65a84fc14153b69493` |

启动前重核836来源：832本地文件+4冻结bundle entry均匹配，包RAW/canonical、runner、最终审签页/attestation不变。新固定ref准确指向已签身份，检查时该ref没有既往运行。不得使用后来的文档/授权提交作为execution commit。本机未运行Python/native/model。

正式范围为 `M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN`：101 descriptors、3216输入行、499 planned snapshots、969 static stages+FINAL，原冻结动态prefix selector和所有repeat/schema/Startup/C/S/P15要求。必须从prepare fresh执行一次，不借旧PASS；不重复dispatch、不在同execution改源码/adapter/判据后重跑。任何预登记FAIL或来源/环境/证据完整性问题保留并STOP。

已批准环境锁RAW `4a68d805046b6d7b6946274cabd2ba37b69b44d82587e4865bed89d9d77f6877`；镜像只允许20261004.326.1/20261012.333.1，Python3.11.9/Windows10.0.20348/AMD64/win22及全部锁定依赖精确匹配，每Job前后一致；未知环境拒绝，不绕guard。CPU25%、480000ms和STRICT256/512MiB、CAMPAIGN1024/2048MiB保持，模型timer不变。

FINAL增加11组durable BEGIN/END及batch/case进度；只优化重复包/环境锁加载，不减少证据验证。最终还必须下载官方artifact，独立核验source/environment、原始日志、全部selected-prefix/repeat/schema、实际Python Job身份及最后FINAL退出后的batch/cleanup；GitHub绿色不等于正式PASS。

原Startup历史49/50与versioned compatibility分开；SEM02精确五项strict P1 B/C INCOMPLETE，不伪造PLC issue；PF06 original scope INCOMPLETE，C8补充单独判。任意POST异常/OS crash/掉电原子性NOT_PROVEN；T09 IMPLEMENTATION_HOLD、full P history不可用、hardware CALIBRATION_REQUIRED。旧v3/v4 INVALID不改判。生产、硬件、Phase6未授权。

授权收据见 `artifacts/m1-c3c-v5-authorization/`。初始登记状态 `AUTHORIZED_PENDING_DISPATCH` 已在下列唯一dispatch后转为 `DISPATCHED_NOT_ADJUDICATED`，不是正式成绩。

## 唯一正式运行

[run38833878662](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38833878662)，attempt1；GitHub创建时间2026-10-16T01:12:43Z，即新加坡2026-10-16 09:12:43。API已核对headSha=`9ad4b9d1fdab261db9be09b91f261a927d529970`、固定ref准确，formal-v5/prepare开始。两收据先在说明提交`07ea0bd3d95df6465bbba21355daf383d0075016`保存并推送，再通过base64+独立RAW hash传入冻结workflow；说明提交不改变执行源码身份。

当前仅确认已开考，不宣称环境/prepare已PASS。机器登记为同目录`formal_run_registration.json`；不再dispatch或重跑failed Jobs。后续按已冻结门禁跟进，仅对有意义进展、失败、完成或需用户判断通知。

## Prepare fresh证据回读

后续实际状态：prepare已成功结束，reference分组开始。官方prepare artifact12017563767（2888066字节），ZIP SHA-256 `6093e4a5f3c6f8f7d600de5b95e589d82391f33b524753eaf4972e06adb2654c`独立匹配。335个native文件哈希、16阶段/16实际Python Job证明、64份raw、完整authority身份、ENV前后及锁定依赖、release PID链和全部cleanup active0已通过纯文件核验；镜像20261012.333.1，CPU25%/1024/2048MiB/480000ms不变。新运行authority单元31/31、已登记POST atomicity单元4/4通过，不扩大任意异常原子性证明。

机器记录为`artifacts/m1-c3c-v5-authorization/prepare_independent_readback.json`，原官方ZIP保存在`D:/Github/c2c-m1-remote-evidence/c3c-v5-formal-38833878662/prepare.official.zip`。这些只是prepare阶段和凭据通过，不是全部101案例或formal aggregate通过。已建立本聊天自动跟进`c3-c-v5`；正常运行保持安静，终态独立回读后裁决，不重复开考。

## 参考/选择阶段与State U

10/10 reference分组、reference_gate、11/11 select分组和split_u已成功结束，其余split执行中，尚无完整资格判定。对官方split-u artifact12019018411（1219631字节，SHA-256 `e70a46c8e1dce7eced0cd534d958f31460b3ce7c1d99da5f6f9b3b2434926ac9`）已另行独立核验：100个native文件、5份实际Job/authority/env/cleanup证明、20份raw、21行输入身份、ST12-U-01..12全部true、comparison21行PASS、2份snapshot重复hash相同，reference/split/repeat三份实际原始文件均匹配receipt。不重新执行候选。

机器摘要为`artifacts/m1-c3c-v5-authorization/state_u_independent_readback.json`。旧库内部`DEVELOPMENT_ONLY_NOT_QUALIFICATION`元数据保持原样；本轮formal authority来自新外层收据和执行证明，不篡改旧标签冒充资格。State U已核对不代表全量prefix/Startup/schema/FINAL通过，仍须终态独立组合验收。
