# C2C-DTB M1：离线交付候选 RC1

这是将**原封不动的已验证 source SDK**、当前 C3-C 正式结果、使用说明和参数参考放在一起的交付候选包。它不是新算法版本，不是生产控制器，也没有新增运行授权。

## 先看结论

- v5 fresh C3-C：`C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS`，run38833878662，执行源码9ad4b9d1fdab261db9be09b91f261a927d529970。101案例、499快照、2281个prefix及最终证据完整性已独立核验。
- SDK：保留原ZIP `820baee49b3170dc07bc7bb6bfa3ffdc9732c9c79492ccc7df43699202e6bf78`。仓库外安装后101个完整输入的**开发验证**通过。没有重新打包SDK内部文件，也不把SDK专用CLI的开发验证冒充正式资格。
- 本外层交付包：`PREPARED_FOR_USER_DELIVERY_REVIEW`。未自动创建GitHub Release、未签署生产发布、未授权硬件控制或Phase6。

原SDK、冻结指南与scope文件里的“尚未审签/尚未执行/PENDING”是各原件生成时的历史状态。它们不被回写；当前限定域授权见 `formal/user_freeze_approval.json`、`formal/formal_execution_authorization.json`，结果见 `evidence/independent_verdict.json` 和 `docs/M1_C3_C_V5_FORMAL_RESULT.md`。本说明不扩大这些收据的适用范围。

## 1. 先校验，后安装

先从可信的交付记录获得**外层ZIP SHA-256**，在解压前用 `Get-FileHash -Algorithm SHA256` 核对。包内清单只能证明一致性，不能自行证明来源可信。外层清单 `RELEASE_MANIFEST.json` 逐文件绑定全部载荷；再核对 `source-sdk.zip` 的上述固定SHA-256。

解压外层包到新目录，再将 `source-sdk.zip` 解压到另一个新目录；不要覆盖历史SDK、开发checkout或证据。完整步骤在 `docs/M1_SOFTWARE_USER_GUIDE.md` 第9节，所有参数导航在第10节。**当前发生过硬挂的HIPPO本机禁止运行Python、native/model或压力测试。** 以下步骤仅供另行批准、已受资源约束的稳定Windows执行机。

```powershell
# 仅在批准的稳定执行机；示例路径，不是当前主机的执行指令
python --version  # 要求 Python 3.11.9
python -m venv D:/C2C/offline-venv
& D:/C2C/offline-venv/Scripts/python.exe -m pip install -r D:/C2C/offline-sdk/v0_2/tests/tools/c3b_v14_1/requirements-development.lock
& D:/C2C/offline-venv/Scripts/python.exe D:/C2C/offline-sdk/sdk_cli.py --describe --verify
& D:/C2C/offline-venv/Scripts/python.exe D:/C2C/offline-sdk/sdk_cli.py --run --input-index 15 --rows 3
```

示例index15是故障/生命周期输入，不是正常液冷调泵场景；`TRACKING_FAULT_SUSPECTED`可能是登记预期，`comparison.status=PASS`只说明与参考一致。长例子是index65、rows161。stdout给出完整trace目录；保留日志和输入身份，不改预期取PASS。

CLI默认只读描述/校验；`--run`才运行离线模型。`--input-index`为0..100的登记输入索引；`--rows`是从t0回放的行数，不是积分dt。模型输出只写离线证据，不签发真实PLC命令。CLI本身**不为任意用户进程施加Windows Job限额**；CPU25%、1024/2048MiB、480s是原受控远程验收的执行条件，不是已安装CLI自动具备的保护。

## 2. 参数说明

| 需要查什么 | 文件 |
| --- | --- |
| 命令/测量时间、tracking profile、六状态、公共PID、执行器、传感器、CLI参数、错误解释 | `docs/M1_SOFTWARE_USER_GUIDE.md` |
| 固体热容、热阻、冷却液、液压、泵、CDU/FWS、数值与保护字段 | `docs/V02_PHYSICS_PARAMETER_REFERENCE.md` |
| 旧版YAML场景字段与报告入口 | `docs/LEGACY_SCENARIO_PARAMETER_REFERENCE.md` |
| 37类/259字段的静态来源覆盖 | `docs/parameter_reference_coverage.json` |

单位和fixture假设不能当成硬件校准：K/°C、Pa/kPa、kg/s/m³/s必须区分；归一化速度不是RPM。不得修改冻结profile、阈值、timer或Contract15A来让测试通过。

## 3. 仍然明确不具备什么

| 项目 | 真实状态 / 处理边界 |
| --- | --- |
| 原Startup与兼容性 | 原测试49/50；版本化compatibility另记PASS，不回写历史 |
| SEM02五项与原PF06 | 五项strict P1 Lane B/C仍INCOMPLETE；原PF06 scope仍INCOMPLETE，C8补充域独立formal通过；不制造历史PLC签发证据 |
| 异常与持久恢复 | 任意POST异常、OS crash、断电原子性NOT_PROVEN；T09物理持久恢复IMPLEMENTATION_HOLD |
| 历史与硬件 | 完整P历史不可用；真实设备CALIBRATION_REQUIRED；本机硬挂根因未获关闭证明 |
| 发布权限 | 本包尚待交付审阅；生产移植、真实控制、Phase6未授权 |

因此，限定离线软件资格通过**不等于原始完整M1范围或完整系统上线全部通过**。确切源码冻结/正式执行已经由独立收据授权，不必重复开考；分发本外层包、进入生产准备或扩大资格范围是不同决定。

## 4. 包含和不包含的证据

`formal/`保存v5 manifest、四份语义登记及两份授权收据；`evidence/`保存本轮独立裁决、逐case/Job/schema/prefix摘要和最终原始证明；`installation/`是SDK安装开发验证记录。2.01GB完整官方正式artifact不重复塞入此包，可从run38833878662下载，固定SHA在manifest和裁决中。

完整源码/运行环境由原SDK、v5正式manifest和锁文件各自绑定。SDK额外CLI、LICENSE、README及静态覆盖记录不是本轮正式source closure的一部分；不得声称整个外层ZIP、安装器或CLI已被该formal campaign逐字节执行认证。
